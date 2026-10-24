import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from threading import BoundedSemaphore
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from .config import get_settings
from .models import LoginAttempt, Role, SessionRecord, User

_hasher = PasswordHasher()


@lru_cache
def _password_slots(limit: int) -> BoundedSemaphore:
    return BoundedSemaphore(limit)


class AuthError(Exception):
    pass


class AuthenticationError(AuthError):
    pass


class AuthorizationError(AuthError):
    pass


class RevisionConflict(Exception):
    pass


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Passwords must contain at least 12 characters")
    with _password_slots(get_settings().password_concurrency_limit):
        return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        with _password_slots(get_settings().password_concurrency_limit):
            return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _is_rate_limited(db: Session, subject: str) -> bool:
    settings = get_settings()
    cutoff = _now() - timedelta(seconds=settings.rate_limit_window_seconds)
    db.execute(delete(LoginAttempt).where(LoginAttempt.failed_at < cutoff))
    count = db.scalar(select(func.count(LoginAttempt.id)).where(LoginAttempt.subject == subject, LoginAttempt.failed_at >= cutoff))
    return count >= settings.rate_limit_failures


def authenticate(db: Session, username: str, password: str, ip_address: str | None = None) -> tuple[str, User]:
    subject = username.strip().lower()
    rate_subject = f"user:{subject}"
    if ip_address:
        rate_subject = f"{rate_subject}|ip:{ip_address}"
    if _is_rate_limited(db, rate_subject):
        raise AuthenticationError("Too many failed login attempts; try again later")
    user = db.scalar(select(User).where(User.username == subject))
    if user is None or not user.is_active or not verify_password(user.password_hash, password):
        db.add(LoginAttempt(subject=rate_subject))
        db.commit()
        raise AuthenticationError("Invalid credentials")
    db.execute(delete(LoginAttempt).where(LoginAttempt.subject == rate_subject))
    return issue_session(db, user), user


def issue_session(db: Session, user: User, ttl_hours: int | None = None) -> str:
    """Issue a normal cookie session after an authenticated login/local launch."""
    if not user.is_active:
        raise AuthenticationError("Account is inactive")
    raw_token = secrets.token_urlsafe(32)
    expires = _now() + timedelta(hours=ttl_hours or get_settings().session_ttl_hours)
    db.add(SessionRecord(token_hash=_digest(raw_token), user_id=user.id, expires_at=expires))
    db.commit()
    return raw_token


def get_authenticated_user(db: Session, raw_token: str | None) -> User:
    if not raw_token:
        raise AuthenticationError("Authentication required")
    result = db.execute(
        select(SessionRecord, User)
        .join(User, SessionRecord.user_id == User.id)
        .where(SessionRecord.token_hash == _digest(raw_token))
    ).one_or_none()
    now = _now()
    if result is None:
        raise AuthenticationError("Authentication required")
    record, user = result
    if record.revoked or _as_utc(record.expires_at) <= now or not user.is_active:
        raise AuthenticationError("Authentication required")
    cutoff = now - timedelta(seconds=get_settings().session_touch_interval_seconds)
    if record.last_seen_at is None or _as_utc(record.last_seen_at) <= cutoff:
        # Concurrent checks may have read the same timestamp. Only the first
        # updates it; expiry, revocation and account status are never cached.
        touched = db.execute(
            update(SessionRecord)
            .where(
                SessionRecord.id == record.id,
                or_(SessionRecord.last_seen_at <= cutoff, SessionRecord.last_seen_at.is_(None)),
            )
            .values(last_seen_at=now)
            .execution_options(synchronize_session=False)
        )
        if touched.rowcount:
            db.commit()
            set_committed_value(record, "last_seen_at", now)
    return user


def revoke_session(db: Session, raw_token: str | None) -> None:
    if raw_token:
        record = db.scalar(select(SessionRecord).where(SessionRecord.token_hash == _digest(raw_token)))
        if record:
            record.revoked = True
            db.commit()


def require_role(user: User, *roles: Role) -> None:
    if user.role not in {role.value for role in roles}:
        raise AuthorizationError("This action requires a different role")


def can_access_project(user: User, project_team_id: UUID) -> bool:
    return user.role == Role.INSTRUCTOR.value or user.team_id == project_team_id

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import LoginAttempt, Role, SessionRecord, User

_hasher = PasswordHasher()


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
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
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
    raw_token = secrets.token_urlsafe(32)
    expires = _now() + timedelta(hours=get_settings().session_ttl_hours)
    db.add(SessionRecord(token_hash=_digest(raw_token), user_id=user.id, expires_at=expires))
    db.commit()
    return raw_token, user


def get_authenticated_user(db: Session, raw_token: str | None) -> User:
    if not raw_token:
        raise AuthenticationError("Authentication required")
    record = db.scalar(select(SessionRecord).where(SessionRecord.token_hash == _digest(raw_token)))
    if record is None or record.revoked or _as_utc(record.expires_at) <= _now():
        raise AuthenticationError("Authentication required")
    record.last_seen_at = _now()
    db.commit()
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Authentication required")
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

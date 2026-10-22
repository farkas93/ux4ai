from datetime import timedelta

import pytest
from sqlalchemy import event, select

from aipm_toolkit.auth import (
    AuthenticationError,
    AuthorizationError,
    authenticate,
    can_access_project,
    get_authenticated_user,
    hash_password,
    require_role,
    revoke_session,
)
from aipm_toolkit.models import Course, Role, SessionRecord, Team, User

TEST_PASSWORD = "P" * 16


def create_user(db, username="team-a", password=TEST_PASSWORD, role=Role.TEAM.value, team_id=None):
    user = User(username=username, password_hash=hash_password(password), role=role, team_id=team_id)
    db.add(user)
    db.commit()
    return user


def test_passwords_are_hashed_and_verified(db):
    password = TEST_PASSWORD
    stored = hash_password(password)
    assert stored != password
    user = create_user(db)
    assert authenticate(db, user.username, password)[1].id == user.id


def test_invalid_credentials_and_rate_limit(db):
    create_user(db)
    for _ in range(5):
        with pytest.raises(AuthenticationError):
            authenticate(db, "team-a", "wrong")
    with pytest.raises(AuthenticationError, match="Too many"):
        authenticate(db, "team-a", TEST_PASSWORD)


def test_session_expiry_and_revocation(db):
    user = create_user(db)
    token, _ = authenticate(db, user.username, TEST_PASSWORD)
    assert get_authenticated_user(db, token).id == user.id
    revoke_session(db, token)
    with pytest.raises(AuthenticationError):
        get_authenticated_user(db, token)


def test_session_activity_is_throttled_without_caching_authorization(db):
    user = create_user(db)
    token, _ = authenticate(db, user.username, TEST_PASSWORD)
    record = db.scalar(select(SessionRecord).where(SessionRecord.user_id == user.id))
    record.last_seen_at -= timedelta(minutes=2)
    db.commit()
    updates = []

    def track_updates(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.startswith("UPDATE sessions "):
            updates.append(statement)

    event.listen(db.get_bind(), "before_cursor_execute", track_updates)
    try:
        for _ in range(20):
            assert get_authenticated_user(db, token).id == user.id
        assert len(updates) == 1
        user.is_active = False
        db.commit()
        with pytest.raises(AuthenticationError):
            get_authenticated_user(db, token)
        user.is_active = True
        record.expires_at -= timedelta(days=1)
        db.commit()
        with pytest.raises(AuthenticationError):
            get_authenticated_user(db, token)
    finally:
        event.remove(db.get_bind(), "before_cursor_execute", track_updates)


def test_roles_and_team_access(db):
    course = Course(name="Course")
    db.add(course)
    db.flush()
    team_a = Team(course_id=course.id, alias="a")
    team_b = Team(course_id=course.id, alias="b")
    db.add_all([team_a, team_b])
    db.flush()
    user_a = create_user(db, team_id=team_a.id)
    assert can_access_project(user_a, team_a.id)
    assert not can_access_project(user_a, team_b.id)
    with pytest.raises(AuthorizationError):
        require_role(user_a, Role.INSTRUCTOR)

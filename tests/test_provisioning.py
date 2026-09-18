import pytest

from aipm_toolkit.auth import AuthorizationError, hash_password, verify_password
from aipm_toolkit.instructor_services import provision_team_account
from aipm_toolkit.models import Role, User


def instructor(db):
    user = User(username="provision-instructor", password_hash=hash_password("P" * 16), role=Role.INSTRUCTOR.value)
    db.add(user)
    db.commit()
    return user


def test_instructor_can_provision_team_account(db):
    team = provision_team_account(db, instructor(db), "Course", "Team A", "Q" * 16)
    account = db.query(User).filter_by(username="team a").one()
    assert team.alias == "team a"
    assert account.role == Role.TEAM.value
    assert verify_password(account.password_hash, "Q" * 16)


def test_provisioning_rejects_short_and_duplicate_credentials(db):
    actor = instructor(db)
    with pytest.raises(ValueError):
        provision_team_account(db, actor, "Course", "team-a", "short")
    provision_team_account(db, actor, "Course", "team-a", "Q" * 16)
    with pytest.raises(ValueError, match="already"):
        provision_team_account(db, actor, "Course", "team-a", "R" * 16)


def test_team_cannot_provision_accounts(db):
    team_user = User(username="team", password_hash=hash_password("P" * 16), role=Role.TEAM.value)
    db.add(team_user)
    db.commit()
    with pytest.raises(AuthorizationError):
        provision_team_account(db, team_user, "Course", "another", "Q" * 16)

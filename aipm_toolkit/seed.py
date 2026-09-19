import argparse

from sqlalchemy import select

from .auth import hash_password
from .db import Base, SessionLocal, engine
from .models import Course, Role, Team, User


def seed_account(username: str, password: str, role: Role, course_name: str, team_alias: str | None = None) -> None:
    Base.metadata.create_all(engine)
    with SessionLocal.begin() as db:
        course = db.scalar(select(Course).where(Course.name == course_name))
        if course is None:
            course = Course(name=course_name)
            db.add(course)
            db.flush()
        team = None
        if role == Role.TEAM:
            if not team_alias:
                raise ValueError("team_alias is required for team accounts")
            team = db.scalar(select(Team).where(Team.course_id == course.id, Team.alias == team_alias))
            if team is None:
                team = Team(course_id=course.id, alias=team_alias)
                db.add(team)
                db.flush()
        existing = db.scalar(select(User).where(User.username == username.lower()))
        if existing is not None:
            raise ValueError("username already exists")
        db.add(User(username=username.lower(), password_hash=hash_password(password), role=role.value, team_id=team.id if team else None))


def bootstrap_instructor(username: str, password: str, course_name: str) -> bool:
    """Create the first instructor from deployment secrets without overwriting it."""
    Base.metadata.create_all(engine)
    with SessionLocal.begin() as db:
        existing = db.scalar(select(User).where(User.username == username.lower()))
        if existing is not None:
            if existing.role != Role.INSTRUCTOR.value:
                raise ValueError("Bootstrap username already belongs to a team account")
            return False
        course = db.scalar(select(Course).where(Course.name == course_name))
        if course is None:
            db.add(Course(name=course_name))
        db.add(User(username=username.lower(), password_hash=hash_password(password), role=Role.INSTRUCTOR.value))
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument("--role", choices=[role.value for role in Role], default=Role.TEAM.value)
    parser.add_argument("--course", default="AIPM Workshop")
    parser.add_argument("--team-alias")
    args = parser.parse_args()
    seed_account(args.username, args.password, Role(args.role), args.course, args.team_alias)

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Role(StrEnum):
    TEAM = "team"
    INSTRUCTOR = "instructor"


class HypothesisKind(StrEnum):
    MAIN = "main"
    SUPPORTING = "supporting"


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    teams: Mapped[list["Team"]] = relationship(back_populates="course")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), nullable=False)
    alias: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    course: Mapped[Course] = relationship(back_populates="teams")
    users: Mapped[list["User"]] = relationship(back_populates="team")
    projects: Mapped[list["Project"]] = relationship(back_populates="team")
    __table_args__ = (UniqueConstraint("course_id", "alias", name="uq_team_course_alias"),)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    team_id: Mapped[UUID | None] = mapped_column(ForeignKey("teams.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    team: Mapped[Team | None] = relationship(back_populates="users")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    team_id: Mapped[UUID] = mapped_column(ForeignKey("teams.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    short_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    target_user: Mapped[str] = mapped_column(Text, default="", nullable=False)
    job_to_be_done: Mapped[str] = mapped_column(Text, default="", nullable=False)
    current_problem: Mapped[str] = mapped_column(Text, default="", nullable=False)
    product_type: Mapped[str | None] = mapped_column(String(30))
    figma_url: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    team: Mapped[Team] = relationship(back_populates="projects")
    hypotheses: Mapped[list["Hypothesis"]] = relationship(back_populates="project")


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    statement: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    project: Mapped[Project] = relationship(back_populates="hypotheses")
    __table_args__ = (UniqueConstraint("project_id", "kind", name="uq_project_hypothesis_kind"),)


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    subject: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

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


class AssessmentStatus(StrEnum):
    UNASSESSED = "unassessed"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


class AssessmentBasis(StrEnum):
    INTENDED_DESIGN = "intended_design"
    PROTOTYPE_OBSERVED = "prototype_observed"
    MIXED = "mixed"


class NoteType(StrEnum):
    OBSERVATION = "observation"
    ASSUMPTION = "assumption"
    QUESTION = "question"
    DESIGN_DECISION = "design_decision"


class RelationshipType(StrEnum):
    CONTRIBUTES_TO = "contributes_to"
    DEPENDS_ON = "depends_on"
    ALTERNATIVE_TO = "alternative_to"
    IN_TENSION_WITH = "in_tension_with"


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
    dimension_estimates: Mapped[list["DimensionEstimate"]] = relationship(back_populates="project")


class ScaleDefinition(Base):
    __tablename__ = "scale_definitions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(40), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    low_anchor: Mapped[str] = mapped_column(String(200), nullable=False)
    high_anchor: Mapped[str] = mapped_column(String(200), nullable=False)
    midpoint: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (UniqueConstraint("key", "version", name="uq_scale_definition_key_version"),)


class DimensionEstimate(Base):
    __tablename__ = "dimension_estimates"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    dimension_key: Mapped[str] = mapped_column(String(40), nullable=False)
    scale_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AssessmentStatus.UNASSESSED.value)
    score: Mapped[float | None] = mapped_column(nullable=True)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    basis: Mapped[str | None] = mapped_column(String(30))
    evidence: Mapped[str] = mapped_column(Text, default="", nullable=False)
    uncertainty: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    project: Mapped[Project] = relationship(back_populates="dimension_estimates")
    __table_args__ = (UniqueConstraint("project_id", "dimension_key", name="uq_project_dimension_key"),)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(String(2048))
    aliases: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (UniqueConstraint("display_name", name="uq_product_display_name"),)


class BaselineDataset(Base):
    __tablename__ = "baseline_datasets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    cohort_label: Mapped[str] = mapped_column(String(200), nullable=False)
    scale_version: Mapped[int] = mapped_column(Integer, nullable=False)
    provenance_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (UniqueConstraint("product_id", "source_type", "cohort_label", name="uq_baseline_dataset_identity"),)


class BaselineAssessment(Base):
    __tablename__ = "baseline_assessments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("baseline_datasets.id"), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(300), nullable=False)
    dimension_key: Mapped[str] = mapped_column(String(40), nullable=False)
    score: Mapped[float | None] = mapped_column(nullable=True)
    original_value: Mapped[str | None] = mapped_column(String(100))
    raw_record: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (UniqueConstraint("dataset_id", "source_record_id", "dimension_key", name="uq_baseline_source_dimension"),)


class ComparisonSnapshot(Base):
    __tablename__ = "comparison_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("baseline_datasets.id"), nullable=False)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    frozen_profile: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    statement: Mapped[str] = mapped_column(Text, default="", nullable=False)
    value_link: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expected_tradeoff: Mapped[str] = mapped_column(Text, default="", nullable=False)
    impact_if_wrong: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    evidence_strength: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    evidence_rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    workflow_status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    review_conclusion: Mapped[str] = mapped_column(String(40), default="not_assessed", nullable=False)
    next_decision: Mapped[str] = mapped_column(String(20), default="undecided", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    project: Mapped[Project] = relationship(back_populates="hypotheses")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    note_type: Mapped[str] = mapped_column(String(30), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    comparator_snapshot_id: Mapped[UUID | None] = mapped_column(ForeignKey("comparison_snapshots.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class NoteDimension(Base):
    __tablename__ = "note_dimensions"

    note_id: Mapped[UUID] = mapped_column(ForeignKey("notes.id"), primary_key=True)
    dimension_key: Mapped[str] = mapped_column(String(40), primary_key=True)


class HypothesisDimension(Base):
    __tablename__ = "hypothesis_dimensions"

    hypothesis_id: Mapped[UUID] = mapped_column(ForeignKey("hypotheses.id"), primary_key=True)
    dimension_key: Mapped[str] = mapped_column(String(40), primary_key=True)


class HypothesisSource(Base):
    __tablename__ = "hypothesis_sources"

    hypothesis_id: Mapped[UUID] = mapped_column(ForeignKey("hypotheses.id"), primary_key=True)
    note_id: Mapped[UUID | None] = mapped_column(ForeignKey("notes.id"), primary_key=True, nullable=True)
    comparison_snapshot_id: Mapped[UUID | None] = mapped_column(ForeignKey("comparison_snapshots.id"), primary_key=True, nullable=True)


class HypothesisRelation(Base):
    __tablename__ = "hypothesis_relations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    from_hypothesis_id: Mapped[UUID] = mapped_column(ForeignKey("hypotheses.id"), nullable=False)
    to_hypothesis_id: Mapped[UUID] = mapped_column(ForeignKey("hypotheses.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (UniqueConstraint("project_id", "relation_type", "from_hypothesis_id", "to_hypothesis_id", name="uq_hypothesis_relation"),)


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    primary_hypothesis_id: Mapped[UUID] = mapped_column(ForeignKey("hypotheses.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    method: Mapped[str] = mapped_column(String(40), nullable=False)
    procedure: Mapped[str] = mapped_column(Text, default="", nullable=False)
    participants: Mapped[str] = mapped_column(Text, default="", nullable=False)
    comparison_baseline: Mapped[str] = mapped_column(Text, default="", nullable=False)
    metric: Mapped[str] = mapped_column(Text, default="", nullable=False)
    success_criterion: Mapped[str] = mapped_column(Text, default="", nullable=False)
    guardrail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    resources: Mapped[str] = mapped_column(Text, default="", nullable=False)
    owner: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    planned_date: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="planned", nullable=False)
    results: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_links: Mapped[str] = mapped_column(Text, default="", nullable=False)
    limitations: Mapped[str] = mapped_column(Text, default="", nullable=False)
    conclusion: Mapped[str] = mapped_column(Text, default="", nullable=False)
    resulting_decision: Mapped[str] = mapped_column(String(30), default="undecided", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class ProjectReflection(Base):
    __tablename__ = "project_reflections"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    reflection_type: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    subjective_score: Mapped[float | None] = mapped_column(nullable=True)
    attack_entry_point: Mapped[str] = mapped_column(Text, default="", nullable=False)
    unwanted_behavior: Mapped[str] = mapped_column(Text, default="", nullable=False)
    affected_data_action: Mapped[str] = mapped_column(Text, default="", nullable=False)
    consequence: Mapped[str] = mapped_column(Text, default="", nullable=False)
    proposed_safeguard: Mapped[str] = mapped_column(Text, default="", nullable=False)
    signal_to_collect: Mapped[str] = mapped_column(Text, default="", nullable=False)
    signal_meaning: Mapped[str] = mapped_column(Text, default="", nullable=False)
    possible_product_change: Mapped[str] = mapped_column(Text, default="", nullable=False)
    human_interpretation_needed: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evaluation_after_change: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (UniqueConstraint("project_id", "reflection_type", name="uq_project_reflection_type"),)


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

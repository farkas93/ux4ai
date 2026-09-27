"""Structured safety assessment and multiple improvement loops.

Revision ID: 0016_safety_improvement
Revises: 0015_project_history_and_archive
"""

import sqlalchemy as sa

from alembic import op

revision = "0016_safety_improvement"
down_revision = "0015_project_history_and_archive"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "safety_assessments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False, unique=True),
        sa.Column("critical_risk", sa.Text(), nullable=False, server_default=""),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "safety_checkpoints",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("assessment_id", sa.Uuid(), sa.ForeignKey("safety_assessments.id"), nullable=False),
        sa.Column("checkpoint_key", sa.String(30), nullable=False),
        sa.Column("coverage", sa.String(30)),
        sa.Column("maturity", sa.String(20)),
        sa.Column("evidence", sa.Text(), nullable=False, server_default=""),
        sa.UniqueConstraint("assessment_id", "checkpoint_key", name="uq_safety_checkpoint"),
    )
    op.create_table(
        "improvement_loops",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("capabilities_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="intended"),
        sa.Column("change_scopes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("recursion_scope", sa.String(30), nullable=False, server_default="product_behavior"),
        sa.Column("approval_boundary", sa.Text(), nullable=False, server_default=""),
        sa.Column("release_approval", sa.String(30), nullable=False, server_default="unspecified"),
        sa.Column("success_checks", sa.Text(), nullable=False, server_default=""),
        sa.Column("rollback", sa.Text(), nullable=False, server_default=""),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "safety_hypothesis_links",
        sa.Column("hypothesis_id", sa.Uuid(), sa.ForeignKey("hypotheses.id"), primary_key=True),
        sa.Column("checkpoint_key", sa.String(30), nullable=False),
    )


def downgrade():
    op.drop_table("safety_hypothesis_links")
    op.drop_table("improvement_loops")
    op.drop_table("safety_checkpoints")
    op.drop_table("safety_assessments")

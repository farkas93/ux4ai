"""add experiments and project reflections

Revision ID: 0005_experiments
Revises: 0004_notes_hypotheses
"""
import sqlalchemy as sa

from alembic import op

revision = "0005_experiments"
down_revision = "0004_notes_hypotheses"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("experiments", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("primary_hypothesis_id", sa.Uuid(), sa.ForeignKey("hypotheses.id"), nullable=False), sa.Column("title", sa.String(200), nullable=False), sa.Column("method", sa.String(40), nullable=False), sa.Column("procedure", sa.Text(), nullable=False, server_default=""), sa.Column("participants", sa.Text(), nullable=False, server_default=""), sa.Column("comparison_baseline", sa.Text(), nullable=False, server_default=""), sa.Column("metric", sa.Text(), nullable=False, server_default=""), sa.Column("success_criterion", sa.Text(), nullable=False, server_default=""), sa.Column("guardrail", sa.Text(), nullable=False, server_default=""), sa.Column("resources", sa.Text(), nullable=False, server_default=""), sa.Column("owner", sa.String(200), nullable=False, server_default=""), sa.Column("planned_date", sa.String(30)), sa.Column("status", sa.String(30), nullable=False, server_default="planned"), sa.Column("results", sa.Text(), nullable=False, server_default=""), sa.Column("evidence_links", sa.Text(), nullable=False, server_default=""), sa.Column("limitations", sa.Text(), nullable=False, server_default=""), sa.Column("conclusion", sa.Text(), nullable=False, server_default=""), sa.Column("resulting_decision", sa.String(30), nullable=False, server_default="undecided"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"))
    op.create_table("project_reflections", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("reflection_type", sa.String(30), nullable=False), sa.Column("content", sa.Text(), nullable=False, server_default=""), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"), sa.UniqueConstraint("project_id", "reflection_type", name="uq_project_reflection_type"))


def downgrade():
    op.drop_table("project_reflections")
    op.drop_table("experiments")

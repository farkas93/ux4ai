"""add versioned dimensions and estimates

Revision ID: 0002_dimensions
Revises: 0001_foundation
"""
import sqlalchemy as sa

from alembic import op

revision = "0002_dimensions"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scale_definitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("key", sa.String(40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("low_anchor", sa.String(200), nullable=False),
        sa.Column("high_anchor", sa.String(200), nullable=False),
        sa.Column("midpoint", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("key", "version", name="uq_scale_definition_key_version"),
    )
    op.create_table(
        "dimension_estimates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("dimension_key", sa.String(40), nullable=False),
        sa.Column("scale_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="unassessed"),
        sa.Column("score", sa.Float()),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("basis", sa.String(30)),
        sa.Column("evidence", sa.Text(), nullable=False, server_default=""),
        sa.Column("uncertainty", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("project_id", "dimension_key", name="uq_project_dimension_key"),
    )


def downgrade():
    op.drop_table("dimension_estimates")
    op.drop_table("scale_definitions")

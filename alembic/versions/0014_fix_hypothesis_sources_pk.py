"""fix hypothesis_sources primary key constraint for PostgreSQL

Revision ID: 0014_fix_hypothesis_sources_pk
Revises: 0013_import_batches
"""

import sqlalchemy as sa
from alembic import op

revision = "0014_fix_hypothesis_sources_pk"
down_revision = "0013_import_batches"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("hypothesis_sources")
    op.create_table(
        "hypothesis_sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("hypothesis_id", sa.Uuid(), sa.ForeignKey("hypotheses.id"), nullable=False),
        sa.Column("note_id", sa.Uuid(), sa.ForeignKey("notes.id"), nullable=True),
        sa.Column("comparison_snapshot_id", sa.Uuid(), sa.ForeignKey("comparison_snapshots.id"), nullable=True),
    )


def downgrade():
    op.drop_table("hypothesis_sources")
    op.create_table(
        "hypothesis_sources",
        sa.Column("hypothesis_id", sa.Uuid(), sa.ForeignKey("hypotheses.id"), primary_key=True),
        sa.Column("note_id", sa.Uuid(), sa.ForeignKey("notes.id"), primary_key=True, nullable=True),
        sa.Column("comparison_snapshot_id", sa.Uuid(), sa.ForeignKey("comparison_snapshots.id"), primary_key=True, nullable=True),
    )

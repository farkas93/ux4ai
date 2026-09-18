"""add per-dimension baseline scale metadata

Revision ID: 0008_scale_compatibility
Revises: 0007_frozen_comparison
"""
import sqlalchemy as sa

from alembic import op

revision = "0008_scale_compatibility"
down_revision = "0007_frozen_comparison"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("baseline_datasets") as batch:
        batch.add_column(sa.Column("scale_versions", sa.Text(), nullable=False, server_default="{}"))


def downgrade():
    with op.batch_alter_table("baseline_datasets") as batch:
        batch.drop_column("scale_versions")

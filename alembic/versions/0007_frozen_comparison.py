"""freeze comparator profiles in snapshots

Revision ID: 0007_frozen_comparison
Revises: 0006_reflection_fields
"""
import sqlalchemy as sa

from alembic import op

revision = "0007_frozen_comparison"
down_revision = "0006_reflection_fields"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("comparison_snapshots") as batch:
        batch.add_column(sa.Column("frozen_profile", sa.Text(), nullable=False, server_default="{}"))


def downgrade():
    with op.batch_alter_table("comparison_snapshots") as batch:
        batch.drop_column("frozen_profile")

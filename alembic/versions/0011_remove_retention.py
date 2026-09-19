"""remove retention settings

Revision ID: 0011_remove_retention
Revises: 0010_baseline_versions
"""

import sqlalchemy as sa

from alembic import op

revision = "0011_remove_retention"
down_revision = "0010_baseline_versions"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("courses") as batch:
        batch.drop_column("deletion_policy")
        batch.drop_column("retention_days")


def downgrade():
    with op.batch_alter_table("courses") as batch:
        batch.add_column(sa.Column("retention_days", sa.Integer(), nullable=False, server_default="180"))
        batch.add_column(sa.Column("deletion_policy", sa.Text(), nullable=False, server_default="Delete course data after the configured retention period."))

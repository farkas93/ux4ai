"""add baseline replacement versions

Revision ID: 0010_baseline_versions
Revises: 0009_retention
"""
import sqlalchemy as sa

from alembic import op

revision = "0010_baseline_versions"
down_revision = "0009_retention"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("baseline_datasets") as batch:
        batch.drop_constraint("uq_baseline_dataset_identity", type_="unique")
        batch.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("replacement_reason", sa.Text(), nullable=False, server_default=""))
        batch.create_unique_constraint("uq_baseline_dataset_identity", ["product_id", "source_type", "cohort_label", "version"])


def downgrade():
    with op.batch_alter_table("baseline_datasets") as batch:
        batch.drop_constraint("uq_baseline_dataset_identity", type_="unique")
        batch.drop_column("replacement_reason")
        batch.drop_column("version")
        batch.create_unique_constraint("uq_baseline_dataset_identity", ["product_id", "source_type", "cohort_label"])

"""add hypothesis placement scores

Revision ID: 0012_priority_placement
Revises: 0011_remove_retention
"""

import sqlalchemy as sa
from alembic import op

revision = "0012_priority_placement"
down_revision = "0011_remove_retention"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("hypotheses") as batch:
        batch.add_column(sa.Column("priority_risk", sa.Float(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("priority_evidence", sa.Float(), nullable=False, server_default="0"))


def downgrade():
    with op.batch_alter_table("hypotheses") as batch:
        batch.drop_column("priority_evidence")
        batch.drop_column("priority_risk")

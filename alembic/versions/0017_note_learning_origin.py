"""Track the learning section that prompted a question or assumption.

Revision ID: 0017_note_learning_origin
Revises: 0016_safety_improvement
"""

import sqlalchemy as sa

from alembic import op

revision = "0017_note_learning_origin"
down_revision = "0016_safety_improvement"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("notes", sa.Column("origin_section", sa.String(30), nullable=True))
    op.add_column("notes", sa.Column("origin_key", sa.String(30), nullable=True))


def downgrade():
    op.drop_column("notes", "origin_key")
    op.drop_column("notes", "origin_section")

"""add instructor import batches

Revision ID: 0013_import_batches
Revises: 0012_priority_placement
"""
import sqlalchemy as sa

from alembic import op

revision = "0013_import_batches"
down_revision = "0012_priority_placement"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("import_batches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source_directory", sa.Text(), nullable=False),
        sa.Column("manifest_json", sa.Text(), nullable=False),
        sa.Column("preview_report_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="preview"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )

def downgrade():
    op.drop_table("import_batches")

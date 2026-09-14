"""add historical baseline catalog

Revision ID: 0003_baselines
Revises: 0002_dimensions
"""
import sqlalchemy as sa

from alembic import op

revision = "0003_baselines"
down_revision = "0002_dimensions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("products", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("display_name", sa.String(200), nullable=False), sa.Column("description", sa.Text(), nullable=False, server_default=""), sa.Column("canonical_url", sa.String(2048)), sa.Column("aliases", sa.Text(), nullable=False, server_default=""), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"), sa.UniqueConstraint("display_name", name="uq_product_display_name"))
    op.create_table("baseline_datasets", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id"), nullable=False), sa.Column("source_type", sa.String(30), nullable=False), sa.Column("cohort_label", sa.String(200), nullable=False), sa.Column("scale_version", sa.Integer(), nullable=False), sa.Column("provenance_notes", sa.Text(), nullable=False, server_default=""), sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"), sa.UniqueConstraint("product_id", "source_type", "cohort_label", name="uq_baseline_dataset_identity"))
    op.create_table("baseline_assessments", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("dataset_id", sa.Uuid(), sa.ForeignKey("baseline_datasets.id"), nullable=False), sa.Column("source_record_id", sa.String(300), nullable=False), sa.Column("dimension_key", sa.String(40), nullable=False), sa.Column("score", sa.Float()), sa.Column("original_value", sa.String(100)), sa.Column("raw_record", sa.Text(), nullable=False, server_default=""), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"), sa.UniqueConstraint("dataset_id", "source_record_id", "dimension_key", name="uq_baseline_source_dimension"))
    op.create_table("comparison_snapshots", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id"), nullable=False), sa.Column("dataset_id", sa.Uuid(), sa.ForeignKey("baseline_datasets.id"), nullable=False), sa.Column("purpose", sa.String(30), nullable=False), sa.Column("scope_explanation", sa.Text(), nullable=False, server_default=""), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"))


def downgrade():
    op.drop_table("comparison_snapshots")
    op.drop_table("baseline_assessments")
    op.drop_table("baseline_datasets")
    op.drop_table("products")

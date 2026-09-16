"""add structured notes and hypothesis relationships

Revision ID: 0004_notes_hypotheses
Revises: 0003_baselines
"""
import sqlalchemy as sa

from alembic import op

revision = "0004_notes_hypotheses"
down_revision = "0003_baselines"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("hypotheses") as batch:
        batch.drop_constraint("uq_project_hypothesis_kind", type_="unique")
        batch.add_column(sa.Column("value_link", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("expected_tradeoff", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("impact_if_wrong", sa.String(20), nullable=False, server_default="unknown"))
        batch.add_column(sa.Column("evidence_strength", sa.String(20), nullable=False, server_default="unknown"))
        batch.add_column(sa.Column("evidence_rationale", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("workflow_status", sa.String(30), nullable=False, server_default="draft"))
        batch.add_column(sa.Column("review_conclusion", sa.String(40), nullable=False, server_default="not_assessed"))
        batch.add_column(sa.Column("next_decision", sa.String(20), nullable=False, server_default="undecided"))
    op.create_table("notes", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("note_type", sa.String(30), nullable=False), sa.Column("text", sa.Text(), nullable=False), sa.Column("comparator_snapshot_id", sa.Uuid(), sa.ForeignKey("comparison_snapshots.id")), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"))
    op.create_table("note_dimensions", sa.Column("note_id", sa.Uuid(), sa.ForeignKey("notes.id"), primary_key=True), sa.Column("dimension_key", sa.String(40), primary_key=True))
    op.create_table("hypothesis_dimensions", sa.Column("hypothesis_id", sa.Uuid(), sa.ForeignKey("hypotheses.id"), primary_key=True), sa.Column("dimension_key", sa.String(40), primary_key=True))
    op.create_table("hypothesis_sources", sa.Column("hypothesis_id", sa.Uuid(), sa.ForeignKey("hypotheses.id"), primary_key=True), sa.Column("note_id", sa.Uuid(), sa.ForeignKey("notes.id"), primary_key=True, nullable=True), sa.Column("comparison_snapshot_id", sa.Uuid(), sa.ForeignKey("comparison_snapshots.id"), primary_key=True, nullable=True))
    op.create_table("hypothesis_relations", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("relation_type", sa.String(30), nullable=False), sa.Column("from_hypothesis_id", sa.Uuid(), sa.ForeignKey("hypotheses.id"), nullable=False), sa.Column("to_hypothesis_id", sa.Uuid(), sa.ForeignKey("hypotheses.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"), sa.UniqueConstraint("project_id", "relation_type", "from_hypothesis_id", "to_hypothesis_id", name="uq_hypothesis_relation"))


def downgrade():
    for table in ["hypothesis_relations", "hypothesis_sources", "hypothesis_dimensions", "note_dimensions", "notes"]:
        op.drop_table(table)

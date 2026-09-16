"""add structured reflection fields

Revision ID: 0006_reflection_fields
Revises: 0005_experiments
"""
import sqlalchemy as sa

from alembic import op

revision = "0006_reflection_fields"
down_revision = "0005_experiments"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("project_reflections") as batch:
        batch.add_column(sa.Column("subjective_score", sa.Float()))
        for name in ["attack_entry_point", "unwanted_behavior", "affected_data_action", "consequence", "proposed_safeguard", "signal_to_collect", "signal_meaning", "possible_product_change", "human_interpretation_needed", "evaluation_after_change"]:
            batch.add_column(sa.Column(name, sa.Text(), nullable=False, server_default=""))


def downgrade():
    with op.batch_alter_table("project_reflections") as batch:
        for name in ["evaluation_after_change", "human_interpretation_needed", "possible_product_change", "signal_meaning", "signal_to_collect", "proposed_safeguard", "consequence", "affected_data_action", "unwanted_behavior", "attack_entry_point", "subjective_score"]:
            batch.drop_column(name)

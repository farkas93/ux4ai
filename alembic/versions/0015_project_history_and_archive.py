"""add project event history and archive flags

Revision ID: 0015_project_history_and_archive
Revises: 0014_fix_hypothesis_sources_pk
"""

import json
from uuid import UUID, uuid4

import sqlalchemy as sa

from alembic import op

revision = "0015_project_history_and_archive"
down_revision = "0014_fix_hypothesis_sources_pk"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("notes", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("hypotheses", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "project_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_project_events_project_created", "project_events", ["project_id", "created_at"])

    connection = op.get_bind()
    metadata = sa.MetaData()
    event_table = sa.Table(
        "project_events",
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid()),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.String(36)),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False),
    )
    dimension_order = {key: index for index, key in enumerate(("conversational", "specialization", "autonomy", "accessibility", "explainability"))}
    for link_table, id_column, owner_table, entity_type in (
        ("note_dimensions", "note_id", "notes", "note"),
        ("hypothesis_dimensions", "hypothesis_id", "hypotheses", "hypothesis"),
    ):
        association_table = sa.Table(
            link_table,
            metadata,
            sa.Column(id_column, sa.Uuid()),
            sa.Column("dimension_key", sa.String(40)),
        )
        entity_table = sa.Table(
            owner_table,
            metadata,
            sa.Column("id", sa.Uuid()),
            sa.Column("project_id", sa.Uuid()),
        )
        links = connection.execute(sa.select(association_table.c[id_column], association_table.c.dimension_key)).all()
        grouped = {}
        for entity_id, dimension_key in links:
            grouped.setdefault(entity_id, set()).add(dimension_key)
        for entity_id, dimensions in grouped.items():
            if len(dimensions) < 2:
                continue
            ordered_dimensions = sorted(dimensions, key=lambda key: dimension_order.get(key, len(dimension_order)))
            kept_dimension = ordered_dimensions[0]
            connection.execute(
                sa.delete(association_table).where(
                    association_table.c[id_column] == entity_id,
                    association_table.c.dimension_key != kept_dimension,
                )
            )
            project_id = connection.execute(sa.select(entity_table.c.project_id).where(entity_table.c.id == entity_id)).scalar_one()
            connection.execute(
                event_table.insert().values(
                    id=uuid4(),
                    project_id=UUID(str(project_id)),
                    actor_user_id=None,
                    event_type="dimension.assignment_normalized",
                    entity_type=entity_type,
                    entity_id=str(entity_id),
                    summary=f"Kept one dimension assignment for a legacy {entity_type}",
                    details_json=json.dumps({"before": ordered_dimensions, "after": [kept_dimension]}),
                )
            )
        constraint_name = "uq_note_single_dimension" if entity_type == "note" else "uq_hypothesis_single_dimension"
        with op.batch_alter_table(link_table) as batch:
            batch.create_unique_constraint(constraint_name, [id_column])


def downgrade():
    with op.batch_alter_table("hypothesis_dimensions") as batch:
        batch.drop_constraint("uq_hypothesis_single_dimension", type_="unique")
    with op.batch_alter_table("note_dimensions") as batch:
        batch.drop_constraint("uq_note_single_dimension", type_="unique")
    op.drop_index("ix_project_events_project_created", table_name="project_events")
    op.drop_table("project_events")
    op.drop_column("hypotheses", "archived_at")
    op.drop_column("notes", "archived_at")

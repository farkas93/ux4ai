"""create foundation tables

Revision ID: 0001_foundation
"""
import sqlalchemy as sa

from alembic import op

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    for table, columns in [
        ("courses", [sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("name", sa.String(200), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("revision", sa.Integer(), nullable=False, server_default="1")]),
        ("teams", [sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("course_id", sa.Uuid(), sa.ForeignKey("courses.id"), nullable=False), sa.Column("alias", sa.String(100), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"), sa.UniqueConstraint("course_id", "alias", name="uq_team_course_alias")]),
        ("users", [sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("username", sa.String(100), unique=True, nullable=False), sa.Column("password_hash", sa.String(500), nullable=False), sa.Column("role", sa.String(20), nullable=False), sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id")), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("revision", sa.Integer(), nullable=False, server_default="1")]),
        ("projects", [sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id"), nullable=False), sa.Column("product_name", sa.String(200), nullable=False), sa.Column("short_description", sa.Text(), nullable=False, server_default=""), sa.Column("target_user", sa.Text(), nullable=False, server_default=""), sa.Column("job_to_be_done", sa.Text(), nullable=False, server_default=""), sa.Column("current_problem", sa.Text(), nullable=False, server_default=""), sa.Column("product_type", sa.String(30)), sa.Column("figma_url", sa.String(2048)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("revision", sa.Integer(), nullable=False, server_default="1")]),
        ("hypotheses", [sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("kind", sa.String(20), nullable=False), sa.Column("statement", sa.Text(), nullable=False, server_default=""), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"), sa.UniqueConstraint("project_id", "kind", name="uq_project_hypothesis_kind")]),
        ("sessions", [sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("token_hash", sa.String(128), unique=True, nullable=False), sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false())]),
        ("login_attempts", [sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("subject", sa.String(200), nullable=False), sa.Column("failed_at", sa.DateTime(timezone=True), server_default=sa.func.now())]),
    ]:
        op.create_table(table, *columns)
    op.create_index("ix_login_attempts_subject", "login_attempts", ["subject"])


def downgrade():
    for table in ["login_attempts", "sessions", "hypotheses", "projects", "users", "teams", "courses"]:
        op.drop_table(table)

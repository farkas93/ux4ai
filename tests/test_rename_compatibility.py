from types import SimpleNamespace

from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from aipm_toolkit import config
from aipm_toolkit.baseline_services import aggregate_dataset
from aipm_toolkit.models import (
    BaselineAssessment,
    BaselineDataset,
    Course,
    Note,
    Product,
    Project,
    Role,
    SafetyAssessment,
    SafetyCheckpoint,
    Team,
    User,
)
from aipm_toolkit.services import get_project
from aipm_toolkit.ui import callbacks
from alembic import command


def test_renamed_navigation_keeps_original_migrated_schema_and_saved_origins(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'existing-schema.db'}"
    monkeypatch.setattr(config, "get_settings", lambda: SimpleNamespace(database_url=database_url))
    migration_config = Config("alembic.ini")
    command.upgrade(migration_config, "head")
    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert "baseline_assessments" in inspector.get_table_names()
        assert "safety_assessments" in inspector.get_table_names()
        assert "assessment_id" in {column["name"] for column in inspector.get_columns("safety_checkpoints")}
        assert not any("Explore" in name for name in inspector.get_table_names())
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        with factory() as db:
            course = Course(name="Existing course")
            db.add(course)
            db.flush()
            team = Team(course_id=course.id, alias="existing-team")
            db.add(team)
            db.flush()
            actor = User(username="existing-team", password_hash="not-used", role=Role.TEAM.value, team_id=team.id)
            db.add(actor)
            project = Project(team_id=team.id, product_name="Existing product")
            reference = Product(display_name="Existing comparator")
            db.add_all([project, reference])
            db.flush()
            db.add(Note(project_id=project.id, note_type="question", text="Existing assessment question", origin_section="assessment"))
            dataset = BaselineDataset(product_id=reference.id, source_type="instructor_reference", cohort_label="Existing cohort", scale_version=1, published=True)
            safety = SafetyAssessment(project_id=project.id, critical_risk="Existing backend record")
            db.add_all([dataset, safety])
            db.flush()
            db.add_all([
                BaselineAssessment(dataset_id=dataset.id, source_record_id="original.json", dimension_key="autonomy", score=2.5, raw_record="{}"),
                SafetyCheckpoint(assessment_id=safety.id, checkpoint_key="scope", evidence="Existing backend checkpoint"),
            ])
            db.commit()
            actor_id, project_id, dataset_id, safety_id = actor.id, project.id, dataset.id, safety.id
        # A deployment's normal migration check must retain those records.
        command.upgrade(migration_config, "head")
        monkeypatch.setattr(callbacks, "SessionLocal", factory)
        monkeypatch.setattr(callbacks, "get_authenticated_user", lambda db, _token: db.get(User, actor_id))
        with factory() as db:
            assert get_project(db, db.get(User, actor_id), project_id).product_name == "Existing product"
            assert aggregate_dataset(db, dataset_id)["autonomy"]["median"] == 2.5
            assert db.get(SafetyAssessment, safety_id).critical_risk == "Existing backend record"
        loaded = callbacks.load_backlog_table_from_ui("token", str(project_id))
        assert loaded[1] == "Explore Dimensions"
        assert loaded[4] == "Existing assessment question"
    finally:
        engine.dispose()

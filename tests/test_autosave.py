from aipm_toolkit.ui import callbacks as app_module


def test_autosave_keeps_dirty_state_after_conflict(monkeypatch):
    monkeypatch.setattr(app_module, "save_project_from_ui", lambda *args: ("The project changed since it was loaded", 3))
    status, revision, dirty = app_module.autosave_project_from_ui("token", "project", 2, True, "Product", None, "", "", "", "", "", "")
    assert status.startswith("Save failed")
    assert revision == 3
    assert dirty is True


def test_autosave_does_not_write_when_clean(monkeypatch):
    def fail_if_called(*args):
        raise AssertionError("clean autosave must not write")

    monkeypatch.setattr(app_module, "save_project_from_ui", fail_if_called)
    _status, revision, dirty = app_module.autosave_project_from_ui("token", "project", 2, False, "Product", None, "", "", "", "", "", "")
    assert revision == 2
    assert dirty is False


def test_assessment_save_returns_new_revisions(monkeypatch):
    monkeypatch.setattr(app_module, "save_estimates_from_ui", lambda *args: ("Dimension assessments saved.", [2, 2, 2, 2, 2]))
    status, revisions, dirty = app_module.save_assessments_action("token", "project", [1] * 5, *([2.5, ""] * 5))
    assert status.endswith("saved.")
    assert revisions == [2, 2, 2, 2, 2]
    assert dirty is False


def test_experiment_autosave_preserves_dirty_state_after_failure(monkeypatch):
    monkeypatch.setattr(app_module, "save_experiment_details", lambda *args, **kwargs: ("The experiment changed since it was loaded", 4))
    status, revision, dirty = app_module.autosave_experiment_from_ui("token", "project", "experiment", 3, True, "", "", "", "", "", "", "", "", "", "planned", "", "", "", "", "undecided")
    assert status.startswith("Save failed")
    assert revision == 4
    assert dirty is True

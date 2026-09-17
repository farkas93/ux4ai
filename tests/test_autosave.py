from aipm_toolkit import app as app_module


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

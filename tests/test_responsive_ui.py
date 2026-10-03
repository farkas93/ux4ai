from aipm_toolkit.ui.shell import build_app


def test_responsive_navigation_targets_sections_without_duplicating_forms():
    app = build_app()
    config = app.get_config_file()
    components = config["components"]
    assert not any(item["type"] in {"tabs", "tabitem"} for item in components)
    pages = [item for item in components if (item["props"].get("elem_id") or "").startswith("page-")]
    assert len(pages) == 8
    assert sum(item["props"]["visible"] for item in pages) == 1
    assert not any(item["props"].get("elem_id") == "toolkit-mobile-section" for item in components)
    desktop = next(item for item in components if item["props"].get("elem_id") == "toolkit-desktop-section")
    assert desktop["type"] == "radio"
    assert desktop["props"]["value"] == "Project Setup"
    drawer = next(item for item in components if item["props"].get("elem_id") == "toolkit-sidebar")
    assert drawer["type"] == "sidebar"
    assert drawer["props"]["open"] is False
    assert drawer["props"]["width"] == 240
    switch = next(fn for fn in app.fns.values() if fn.fn and fn.fn.__name__ == "select_section")
    updates = switch.fn("AI Safety")
    assert [item["visible"] for item in updates] == [False, False, True, False, False, False, False, False]
    assert config["title"] == "AI Product Toolkit"
    assert app.theme.to_dict()["theme"]["block_label_background_fill_dark"] == "transparent"
    assert app.theme.to_dict()["theme"]["input_text_size"] == "14px"


def test_backlog_uses_labeled_cards_and_keeps_deferred_controls_absent():
    app = build_app()
    components = app.get_config_file()["components"]
    entries = [item for item in components if "backlog-entry" in (item["props"].get("elem_classes") or [])]
    assert entries and all(item["type"] == "column" for item in entries)
    labels = [item["props"].get("label", "") for item in components]
    assert "Hypothesis" in labels and "Assumption" in labels and "Question" in labels
    assert "Maturity (team claim)" not in labels
    assert "Release approval" not in labels

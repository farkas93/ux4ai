from aipm_toolkit.dimensions import DEFAULT_DIMENSIONS
from aipm_toolkit.ui.shell import build_app
from aipm_toolkit.ui.workspace_style import WORKSPACE_CSS


def test_responsive_navigation_targets_sections_without_duplicating_forms():
    app = build_app()
    config = app.get_config_file()
    expected_sections = [
        "Value Hypothesis",
        "Explore Dimensions",
        "Explore Backlog",
        "Explore Priority",
        "Build Self-Improvement",
        "Summary & Export",
    ]
    components = config["components"]
    assert not any(item["type"] in {"tabs", "tabitem"} for item in components)
    pages = [item for item in components if (item["props"].get("elem_id") or "").startswith("page-")]
    assert len(pages) == len(expected_sections)
    desktop = next(item for item in components if item["props"].get("elem_id") == "toolkit-desktop-section")
    assert [choice[0] for choice in desktop["props"]["choices"]] == expected_sections
    assert not any("AI Safety" in str(item["props"]) for item in components)
    assert not any(item["props"].get("elem_id") in {"page-ai-safety", "page-project-history"} for item in components)
    assert sum(item["props"]["visible"] for item in pages) == 1
    assert not any(item["props"].get("elem_id") == "toolkit-mobile-section" for item in components)
    assert desktop["type"] == "radio"
    assert desktop["props"]["value"] == "Value Hypothesis"
    indicator = next(item for item in components if item["props"].get("elem_id") == "toolkit-current-section")
    assert indicator["props"]["value"] == "Value Hypothesis"
    drawer = next(item for item in components if item["props"].get("elem_id") == "toolkit-sidebar")
    assert drawer["type"] == "sidebar"
    assert drawer["props"]["open"] is True
    assert drawer["props"]["width"] == 240
    assert not any(item["props"].get("elem_id") == "toolkit-menu" for item in components)
    switch = next(fn for fn in app.fns.values() if fn.fn and fn.fn.__name__ == "select_section")
    updates = switch.fn("Explore Backlog")
    assert [item["visible"] for item in updates] == [False, False, True, False, False, False]
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


def test_setup_has_explicit_stacking_layout_and_header_moves_settings_to_drawer():
    components = build_app().get_config_file()["components"]
    setup_row = next(item for item in components if item["props"].get("elem_id") == "toolkit-setup-cards")
    assert "toolkit-two-column" in setup_row["props"]["elem_classes"]
    setup_headings = [item["props"].get("value", "") for item in components if item["type"] == "markdown" and ("The user and their problem" in item["props"].get("value", "") or "Role of AI in the Product" in item["props"].get("value", ""))]
    assert setup_headings == ["#### 1 · The user and their problem", "#### 2 · Role of AI in the Product"]
    add = next(item for item in components if item["props"].get("elem_id") == "toolkit-new-product")
    assert add["props"]["value"] == "+ New"
    assert add["props"]["size"] == "sm"


def test_comparison_label_dimension_order_and_summary_controls():
    app = build_app()
    components = app.get_config_file()["components"]
    labels = [item["props"].get("label") for item in components]
    assert "Compare to Product" in labels
    assert [definition["title"] for definition in DEFAULT_DIMENSIONS][-2:] == ["Explainability", "Accessibility"]
    accessibility = next(definition for definition in DEFAULT_DIMENSIONS if definition["key"] == "accessibility")
    assert accessibility["title"] == "Accessibility"
    assert "target demographics" not in accessibility["title"].lower()
    ids = [item["props"].get("elem_id") for item in components]
    assert ids.index("toolkit-summary-sections") > ids.index("toolkit-summary-export")
    summary_controls = next(index for index, item in enumerate(components) if item["props"].get("label") == "PDF export (includes both graphs)")
    summary_content = next(index for index, item in enumerate(components) if item["props"].get("elem_id") == "toolkit-summary-sections")
    assert summary_controls < summary_content
    assert "overflow-y: auto !important" in WORKSPACE_CSS
    assert "resize: vertical !important" in WORKSPACE_CSS

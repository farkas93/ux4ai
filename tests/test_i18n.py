
from aipm_toolkit.i18n import SUPPORTED_LANGUAGES, load_catalog


def test_supported_catalogs_have_all_sections():
    for language in SUPPORTED_LANGUAGES:
        catalog = load_catalog(language)
        assert catalog["language_name"]
        assert set(catalog["sections"]) == {"Project Brief", "Dimension Explorer", "Notes", "Hypothesis Backlog", "Experiments", "Summary & Export"}


def test_unknown_language_falls_back_to_english_without_changing_content():
    assert load_catalog("fr")["language_name"] == "English"
    assert "Project Brief" in load_catalog("de")["sections"]

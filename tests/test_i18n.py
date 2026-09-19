
from aipm_toolkit.i18n import SUPPORTED_LANGUAGES, load_catalog

SECTION_KEYS = {"Project Setup", "Assessment", "Backlog creator", "Prioritization", "Summary & Export"}


def test_supported_catalogs_have_all_sections():
    for language in SUPPORTED_LANGUAGES:
        catalog = load_catalog(language)
        assert catalog["language_name"]
        assert set(catalog["sections"]) == SECTION_KEYS


def test_unknown_language_falls_back_to_english_without_changing_content():
    assert load_catalog("fr")["language_name"] == "English"
    assert "Project Setup" in load_catalog("de")["sections"]


def test_labels_use_product_terminology_consistently():
    for language in SUPPORTED_LANGUAGES:
        labels = load_catalog(language)["labels"]
        assert "Produkt" in labels["projects"] or "product" in labels["projects"].lower()

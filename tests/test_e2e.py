import os

import pytest

pytest.importorskip("pytest_playwright")
pytestmark = pytest.mark.e2e

if not all(os.getenv(name) for name in ("AIPM_E2E_URL", "AIPM_E2E_USERNAME", "AIPM_E2E_PASSWORD")):
    pytest.skip("Set AIPM_E2E_URL, AIPM_E2E_USERNAME, and AIPM_E2E_PASSWORD", allow_module_level=True)


def test_authenticated_workspace_smoke(page):
    base_url = os.getenv("AIPM_E2E_URL")
    username = os.getenv("AIPM_E2E_USERNAME")
    password = os.getenv("AIPM_E2E_PASSWORD")
    page.goto(f"{base_url.rstrip('/')}/auth/login")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_url("**/app**")
    assert page.get_by_text("Project Brief", exact=False).count() > 0
    assert page.get_by_text("Dimension Explorer", exact=False).count() > 0

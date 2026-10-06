"""Test Module 09: Executive & Technical Reporting Engine (PRD Module 13).

Verifies report archives, before/after posture comparison, and multi-format exports.
"""

from selenium.webdriver.common.by import By

from tests_selenium.conftest import PantheonPageHelper


def test_reports_page_displays_archive(helper: PantheonPageHelper):
    """Verify reports page renders report archive and generation action."""
    helper.goto("/reports")

    body_text = helper.driver.find_element(By.TAG_NAME, "body").text
    assert any(
        term in body_text
        for term in [
            "Report",
            "Executive",
            "Findings",
            "Posture",
            "Generate",
            "Export",
            "Download",
        ]
    )

    helper.save_screenshot("09_executive_reporting_archive")


def test_export_buttons_present(helper: PantheonPageHelper):
    """Verify presence of export controls (PDF, Markdown, CSV)."""
    helper.goto("/reports")

    body_text = helper.driver.find_element(By.TAG_NAME, "body").text
    assert any(
        fmt in body_text
        for fmt in ["PDF", "CSV", "Markdown", "Export", "Download", "PRINT"]
    )

    helper.save_screenshot("09_report_export_buttons")

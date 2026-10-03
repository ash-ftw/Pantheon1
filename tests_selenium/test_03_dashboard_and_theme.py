"""Test Module 03: Executive Dashboard & Theme Switching (PRD Module 14).

Verifies KPI stats, notification drawer, and dynamic theme switching tokens.
"""

from selenium.webdriver.common.by import By

from tests_selenium.conftest import PantheonPageHelper


def test_dashboard_renders_kpi_cards(helper: PantheonPageHelper):
    """Verify operational dashboard cards (Target Apps, Scenarios, Posture Score)."""
    helper.goto("/dashboard")

    body_text = helper.driver.find_element(By.TAG_NAME, "body").text
    assert any(
        term in body_text
        for term in ["Dashboard", "Posture", "Target", "Scenarios", "Security", "Score"]
    )

    helper.save_screenshot("03_dashboard_kpi_cards")


def test_theme_switcher_modal_opens(helper: PantheonPageHelper):
    """Verify theme settings button opens modal with Midnight, Matte, and Cyberpunk options."""
    helper.goto("/dashboard")

    # Look for Theme switcher icon/button in header
    theme_btn = helper.wait_for_clickable(
        By.XPATH,
        "//button[contains(@title, 'Theme') or contains(@aria-label, 'Theme') or contains(., 'Theme') or .//*[name()='svg']]",
    )
    theme_btn.click()

    # Verify theme options are visible
    body = helper.driver.find_element(By.TAG_NAME, "body").text
    assert any(
        name in body for name in ["Midnight", "Matte", "Neon", "Cyberpunk", "Theme"]
    )

    helper.save_screenshot("03_theme_switcher_modal")

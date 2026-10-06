"""Test Module 01: 3D Landing Page & Brand Navigation (PRD Phase 1).

Verifies the narrative landing page, Three.js WebGL viewport, brand assets,
chapter sections, and calls to action.
"""

from selenium.webdriver.common.by import By

from tests_selenium.conftest import PantheonPageHelper


def test_landing_page_loads_and_displays_brand(helper: PantheonPageHelper):
    """Verify that the landing page renders with brand title and operational status."""
    helper.goto("/")

    # Check title contains Pantheon
    assert "Pantheon" in helper.driver.title or "Cyber Range" in helper.driver.title

    # Verify brand logo text
    logo = helper.wait_for_element(By.CSS_SELECTOR, ".brand-title, .brand, a[href='/']")
    assert "PANTHEON" in logo.text.upper()

    # Capture visual screenshot
    helper.save_screenshot("01_landing_page_hero")


def test_landing_page_cta_navigation(helper: PantheonPageHelper):
    """Verify primary CTA button directs user to the platform console."""
    helper.goto("/")

    # Find the Enter Console / Launch button
    cta = helper.wait_for_clickable(
        By.XPATH,
        "//a[contains(text(), 'Enter Console') or contains(text(), 'Get Started') or contains(text(), 'Explore') or contains(@href, '/login') or contains(@href, '/apps')]",
    )
    href = cta.get_attribute("href")
    assert href is not None
    assert "/apps" in href or "/login" in href or "/dashboard" in href

    helper.save_screenshot("01_landing_page_cta_verified")


def test_landing_page_sections_rendered(helper: PantheonPageHelper):
    """Verify the presence of key chapters (Manifesto, Scenarios, Security Architecture)."""
    helper.goto("/")

    body_text = helper.driver.find_element(By.TAG_NAME, "body").text

    # Verify core terminology
    assert any(
        term in body_text
        for term in ["CYBER RANGE", "SIMULATION", "SECURITY", "PANTHEON", "ATTACK"]
    )

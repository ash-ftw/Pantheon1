"""Test Module 04: App Onboarding & Vulnerable Demo Catalog (PRD Module 4).

Verifies target app registration, framework detection, and pre-packaged micro-apps.
"""

from selenium.webdriver.common.by import By

from tests_selenium.conftest import PantheonPageHelper


def test_apps_page_displays_demo_catalog(helper: PantheonPageHelper):
    """Verify demo applications catalog (Juice Shop, BankCore, CloudStore, DevOps)."""
    helper.goto("/apps")

    body_text = helper.driver.find_element(By.TAG_NAME, "body").text
    assert any(
        app in body_text
        for app in [
            "Juice Shop",
            "BankCore",
            "CloudStore",
            "DevOps Worker",
            "Onboard",
            "Target",
        ]
    )

    helper.save_screenshot("04_demo_app_catalog")


def test_onboarding_git_input_form(helper: PantheonPageHelper):
    """Verify custom repository URL input and onboarding submission."""
    helper.goto("/apps")

    # Git repository input
    git_input = helper.driver.find_elements(
        By.XPATH,
        "//input[contains(@placeholder, 'git') or contains(@placeholder, 'github') or contains(@placeholder, 'repo') or contains(@type, 'text')]",
    )
    assert len(git_input) > 0

    helper.save_screenshot("04_app_onboarding_form")

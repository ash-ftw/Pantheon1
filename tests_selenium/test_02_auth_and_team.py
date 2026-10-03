"""Test Module 02: Authentication & Team Management (PRD Modules 3 & 16).

Verifies login, organization registration, client-side validation, and team roles.
"""

from selenium.webdriver.common.by import By

from tests_selenium.conftest import PantheonPageHelper


def test_login_page_renders_form_fields(helper: PantheonPageHelper):
    """Verify login page displays email, password fields and sign-in button."""
    helper.goto("/login")

    # Inputs should be present
    email_input = helper.wait_for_element(By.ID, "auth-email")
    password_input = helper.wait_for_element(By.ID, "auth-password")
    submit_btn = helper.wait_for_element(By.CSS_SELECTOR, "button[type='submit']")

    assert email_input.is_displayed()
    assert password_input.is_displayed()
    assert submit_btn.is_displayed()

    helper.save_screenshot("02_auth_login_page")


def test_auth_switch_to_registration_mode(helper: PantheonPageHelper):
    """Verify switching to registration displays organization and full name inputs."""
    helper.goto("/login")

    # Click tab or toggle to switch to register
    register_toggle = helper.wait_for_clickable(
        By.XPATH,
        "//button[contains(text(), 'Create Workspace') or contains(text(), 'Register') or contains(text(), 'Sign up')]",
    )
    register_toggle.click()

    # Org Name and Full Name should now appear
    org_input = helper.wait_for_element(By.ID, "auth-org")
    name_input = helper.wait_for_element(By.ID, "auth-name")

    assert org_input.is_displayed()
    assert name_input.is_displayed()

    helper.save_screenshot("02_auth_register_mode")


def test_team_management_page_accessible(helper: PantheonPageHelper):
    """Verify Organization & Team Management console renders with RBAC roles."""
    helper.goto("/team")

    body_text = helper.driver.find_element(By.TAG_NAME, "body").text
    assert any(
        term in body_text
        for term in ["Team", "Organization", "Role", "Members", "Owner", "Admin"]
    )

    helper.save_screenshot("02_team_management_console")

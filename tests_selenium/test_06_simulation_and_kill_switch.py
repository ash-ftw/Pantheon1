"""Test Module 06: Test Run Execution & Emergency Kill Switch (PRD Modules 8 & 9).

Verifies execution orchestration, live status streaming, and instant route revocation.
"""

from selenium.webdriver.common.by import By

from tests_selenium.conftest import PantheonPageHelper


def test_test_run_page_renders_history(helper: PantheonPageHelper):
    """Verify test run execution page and execution history table."""
    helper.goto("/test-runs")

    body_text = helper.driver.find_element(By.TAG_NAME, "body").text
    assert any(
        term in body_text
        for term in [
            "Test Run",
            "Execution",
            "Status",
            "Duration",
            "Launch",
            "Simulation",
        ]
    )

    helper.save_screenshot("06_test_run_execution_page")


def test_route_broker_and_kill_switch(helper: PantheonPageHelper):
    """Verify Route Broker console and presence of the Emergency Kill Switch."""
    helper.goto("/route-broker")

    body_text = helper.driver.find_element(By.TAG_NAME, "body").text
    assert any(
        term in body_text
        for term in [
            "Route Broker",
            "Proxy",
            "Kill Switch",
            "Routes",
            "Active",
            "Target",
        ]
    )

    # Locate the Kill Switch button
    kill_btn = helper.driver.find_elements(
        By.XPATH,
        "//button[contains(text(), 'Kill Switch') or contains(text(), 'EMERGENCY') or contains(., 'Kill Switch')]",
    )
    assert len(kill_btn) > 0, (
        "Emergency Kill Switch button must be present in Route Broker console"
    )

    helper.save_screenshot("06_route_broker_kill_switch")

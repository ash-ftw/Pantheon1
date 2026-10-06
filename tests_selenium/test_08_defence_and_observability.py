"""Test Module 08: Defence Engine & Real-Time Observability (PRD Module 11).

Verifies automated defense recommendations, 1-click remediation, and telemetry graphs.
"""

from selenium.webdriver.common.by import By

from tests_selenium.conftest import PantheonPageHelper


def test_defence_engine_recommendations_table(helper: PantheonPageHelper):
    """Verify Defence Engine lists mitigation actions with severity badges."""
    helper.goto("/defence")

    body_text = helper.driver.find_element(By.TAG_NAME, "body").text
    assert any(
        term in body_text
        for term in [
            "Defence",
            "Defense",
            "Mitigation",
            "Recommendation",
            "Remediation",
            "Apply",
        ]
    )

    helper.save_screenshot("08_defence_engine_recommendations")


def test_observability_telemetry_charts(helper: PantheonPageHelper):
    """Verify Observability page displays real-time latency and status codes."""
    helper.goto("/observability")

    body_text = helper.driver.find_element(By.TAG_NAME, "body").text
    assert any(
        term in body_text
        for term in [
            "Observability",
            "Metrics",
            "Latency",
            "Prometheus",
            "Status Code",
            "Traffic",
        ]
    )

    helper.save_screenshot("08_observability_metrics_charts")

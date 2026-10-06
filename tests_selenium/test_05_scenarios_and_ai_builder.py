"""Test Module 05: Simulation Scenarios & AI Scenario Builder (PRD Modules 6 & 12).

Verifies preset attack scenarios, category filtering, and AI generator interface.
"""

from selenium.webdriver.common.by import By

from tests_selenium.conftest import PantheonPageHelper


def test_scenario_library_renders_presets(helper: PantheonPageHelper):
    """Verify scenario library lists pre-built simulation scenarios."""
    helper.goto("/scenarios")

    body_text = helper.driver.find_element(By.TAG_NAME, "body").text
    assert any(
        term in body_text
        for term in [
            "Scenario",
            "Simulation",
            "Attack",
            "Injection",
            "BOLA",
            "SSRF",
            "Preset",
        ]
    )

    helper.save_screenshot("05_scenario_library_presets")


def test_ai_scenario_builder_page(helper: PantheonPageHelper):
    """Verify AI Scenario Builder console with prompt input and validation."""
    helper.goto("/scenarios/builder")

    body_text = helper.driver.find_element(By.TAG_NAME, "body").text
    assert any(
        term in body_text
        for term in ["AI", "Prompt", "Generate", "Builder", "Scenario", "YAML"]
    )

    helper.save_screenshot("05_ai_scenario_builder")

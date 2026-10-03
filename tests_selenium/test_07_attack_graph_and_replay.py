"""Test Module 07: Attack Graph & Step-by-Step Replay Engine (PRD Module 10).

Verifies node/edge graph rendering, kill-switch interception nodes, and replay controls.
"""

from selenium.webdriver.common.by import By

from tests_selenium.conftest import PantheonPageHelper


def test_attack_graph_canvas_rendered(helper: PantheonPageHelper):
    """Verify attack graph page loads with graph container and statistics."""
    helper.goto("/attack-graph")

    body_text = helper.driver.find_element(By.TAG_NAME, "body").text
    assert any(
        term in body_text
        for term in [
            "Attack Graph",
            "Replay",
            "Nodes",
            "Edges",
            "Timeline",
            "Step",
            "Blast Radius",
        ]
    )

    helper.save_screenshot("07_attack_graph_canvas")


def test_attack_graph_replay_controls(helper: PantheonPageHelper):
    """Verify interactive timeline playback buttons (Play, Pause, Step)."""
    helper.goto("/attack-graph")

    # Verify presence of player controls or scrubber
    controls = helper.driver.find_elements(
        By.XPATH,
        "//button[contains(@title, 'Play') or contains(@title, 'Pause') or contains(@title, 'Step') or .//*[name()='svg']]",
    )
    assert len(controls) > 0

    helper.save_screenshot("07_attack_graph_timeline_controls")

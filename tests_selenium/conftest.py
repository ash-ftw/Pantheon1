"""Pytest configuration and fixtures for Pantheon Selenium E2E Test Suite."""

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register custom CLI flags for Selenium test execution."""
    parser.addoption(
        "--browser",
        action="store",
        default="chrome",
        help="Target browser: chrome, edge, or firefox",
    )
    parser.addoption(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default: True)",
    )
    parser.addoption(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Run browser in visible UI mode",
    )
    parser.addoption(
        "--base-url",
        action="store",
        default=os.getenv("PANTHEON_URL", "http://localhost:5173"),
        help="Base URL of the Pantheon frontend application",
    )


@pytest.fixture(scope="session")
def base_url(request: pytest.FixtureRequest) -> str:
    """Base application URL under test."""
    return request.config.getoption("--base-url").rstrip("/")


@pytest.fixture(scope="function")
def driver(request: pytest.FixtureRequest) -> Generator[WebDriver, None, None]:
    """Provides a managed WebDriver instance configured with resilient defaults."""
    browser_name = request.config.getoption("--browser").lower()
    is_headless = request.config.getoption("--headless")

    driver_instance: WebDriver | None = None

    if browser_name == "chrome":
        opts = ChromeOptions()
        if is_headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-notifications")
        opts.add_argument("--ignore-certificate-errors")
        try:
            driver_instance = webdriver.Chrome(options=opts)
        except Exception as e:
            # Fallback to Edge on Windows if Chrome binary not found
            try:
                edge_opts = EdgeOptions()
                if is_headless:
                    edge_opts.add_argument("--headless=new")
                edge_opts.add_argument("--window-size=1920,1080")
                driver_instance = webdriver.Edge(options=edge_opts)
            except Exception:
                raise RuntimeError(f"Failed to launch Chrome and Edge WebDrivers: {e}")

    elif browser_name == "edge":
        edge_opts = EdgeOptions()
        if is_headless:
            edge_opts.add_argument("--headless=new")
        edge_opts.add_argument("--window-size=1920,1080")
        driver_instance = webdriver.Edge(options=edge_opts)

    elif browser_name == "firefox":
        ff_opts = FirefoxOptions()
        if is_headless:
            ff_opts.add_argument("-headless")
        ff_opts.add_argument("--width=1920")
        ff_opts.add_argument("--height=1080")
        driver_instance = webdriver.Firefox(options=ff_opts)

    else:
        raise ValueError(f"Unsupported browser: {browser_name}")

    driver_instance.set_page_load_timeout(30)
    driver_instance.implicitly_wait(4)

    yield driver_instance

    try:
        driver_instance.quit()
    except Exception:
        pass


class PantheonPageHelper:
    """Helper encapsulating fluent interaction, waiting, and assertions for Pantheon."""

    def __init__(self, driver: WebDriver, base_url: str):
        self.driver = driver
        self.base_url = base_url
        self.screenshots_dir = Path("tests_selenium/reports/screenshots")
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def goto(self, path: str = "/") -> None:
        """Navigate to relative or absolute path."""
        target = (
            f"{self.base_url}/{path.lstrip('/')}"
            if not path.startswith("http")
            else path
        )
        self.driver.get(target)

    def wait_for_element(self, by: By, value: str, timeout: float = 10):
        """Wait until element is present and visible."""
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((by, value))
        )

    def wait_for_clickable(self, by: By, value: str, timeout: float = 10):
        """Wait until element is clickable."""
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )

    def click(self, by: By, value: str, timeout: float = 10) -> None:
        """Find and click element safely."""
        el = self.wait_for_clickable(by, value, timeout)
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", el
        )
        el.click()

    def type_text(
        self, by: By, value: str, text: str, clear: bool = True, timeout: float = 10
    ) -> None:
        """Clear and type into an input field."""
        el = self.wait_for_element(by, value, timeout)
        if clear:
            el.clear()
        el.send_keys(text)

    def get_text(self, by: By, value: str, timeout: float = 10) -> str:
        """Retrieve element visible text."""
        el = self.wait_for_element(by, value, timeout)
        return el.text.strip()

    def save_screenshot(self, name: str) -> str:
        """Capture screenshot for review and audit logs."""
        filename = f"{name}.png"
        filepath = self.screenshots_dir / filename
        self.driver.save_screenshot(str(filepath))
        return str(filepath)


@pytest.fixture
def helper(driver: WebDriver, base_url: str) -> PantheonPageHelper:
    """Fixture providing the high-level page helper."""
    return PantheonPageHelper(driver, base_url)

#!/usr/bin/env python3
"""Pantheon Selenium E2E Test Suite Runner.

Saintgits College of Engineering Autonomous — MCA Mini Project-2 (20IMCAP501)
Capstone Project Verification & Evaluation (Reviews 0, 1, and 2).

Usage:
    python tests_selenium/run_selenium_suite.py [--headless] [--no-headless] [--browser=chrome|edge|firefox] [--url=http://localhost:5173]
"""

import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def is_server_reachable(url: str, timeout: float = 3.0) -> bool:
    """Check if the Pantheon frontend application is listening."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "PantheonSeleniumProbe/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status in (200, 301, 302, 304)
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Pantheon Automated Selenium Test Suite"
    )
    parser.add_argument(
        "--url",
        default=os.getenv("PANTHEON_URL", "http://localhost:5173"),
        help="Base frontend URL",
    )
    parser.add_argument(
        "--browser",
        default="chrome",
        choices=["chrome", "edge", "firefox"],
        help="Target browser",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Launch real visible browser window for live demo",
    )
    parser.add_argument(
        "-k", "--filter", default="", help="Filter tests by name expression"
    )
    args = parser.parse_args()

    suite_dir = Path(__file__).parent.resolve()
    reports_dir = suite_dir / "reports"
    screenshots_dir = reports_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 76)
    print("🛡️  PANTHEON ENTERPRISE CYBER RANGE — AUTOMATED SELENIUM TEST SUITE")
    print("    Saintgits College of Engineering Autonomous (20IMCAP501 Mini Project-2)")
    print("=" * 76)
    print(f"Target URL   : {args.url}")
    print(f"Browser      : {args.browser.upper()}")
    print(
        f"Mode         : {'VISIBLE GUI (Demonstration)' if args.no_headless else 'HEADLESS (Automated CI)'}"
    )
    print(f"Screenshots  : {screenshots_dir}")
    print("-" * 76)

    # Server check
    if not is_server_reachable(args.url):
        print(f"⚠️  Note: Target server at {args.url} is not currently responding.")
        print("   If running live end-to-end tests against the platform, ensure:")
        print("   1. Frontend dev server is running: cd frontend && npm run dev")
        print(
            "   2. Backend API server is running: cd backend && uvicorn app.main:app --port 8000"
        )
        print("-" * 76)

    # Construct pytest command
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(suite_dir),
        f"--base-url={args.url}",
        f"--browser={args.browser}",
        "-v",
        "--tb=short",
    ]

    if not args.no_headless:
        cmd.append("--headless")
    else:
        cmd.append("--no-headless")

    if args.filter:
        cmd.extend(["-k", args.filter])

    print(f"Executing: {' '.join(cmd)}\n")
    start_time = time.time()
    result = subprocess.run(cmd, check=False)
    duration = time.time() - start_time

    print("\n" + "=" * 76)
    status_label = (
        "✅ ALL SELENIUM TEST CASES PASSED"
        if result.returncode == 0
        else f"⚠️  COMPLETED WITH EXIT CODE {result.returncode}"
    )
    print(f"{status_label} (Duration: {duration:.2f}s)")
    print("Screenshots captured in: tests_selenium/reports/screenshots/")
    print("=" * 76)

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

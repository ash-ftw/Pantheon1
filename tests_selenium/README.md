# Pantheon Automated Selenium E2E Test Suite

**Course**: 20IMCAP501 Mini Project-2 (IMCA 2022–2027 S9)  
**Institution**: Saintgits College of Engineering Autonomous, Pathamuttam, Kottayam  
**Department**: Department of Computer Applications  
**Milestone Compliance**: Weeks 7, 8 (Review 1), 10, 11, 12, 13, 14, and 15 (Review 2 — Final Evaluation)

---

## Overview

This Selenium test suite provides automated, full-browser End-to-End (E2E) verification for the **Pantheon Enterprise Cyber Range & Security Testing Platform**. It validates user interactions, reactive UI state transitions, routing, kill switch interventions, and security analytics on real browser engines (Chrome, Edge, Firefox).

---

## Test Module Matrix

| Test Module | Target Route | Features & Scenarios Verified |
| :--- | :--- | :--- |
| **`test_01_landing_page.py`** | `/` | 3D WebGL hero section, brand logo, operational status badge, chapter navigation, and console CTA buttons. |
| **`test_02_auth_and_team.py`** | `/login`, `/register`, `/team` | Authentication form validation, tenant workspace creation, login mode switching, and RBAC team role management. |
| **`test_03_dashboard_and_theme.py`** | `/dashboard` | Operational KPI metrics, notification bell dropdown, and dynamic theme switching (Midnight Dark, Matte, Cyberpunk Neon). |
| **`test_04_app_onboarding_and_catalog.py`** | `/apps` | Pre-packaged intentionally vulnerable demo catalog (Juice Shop, BankCore, CloudStore, DevOps Worker) and Git repository onboarding. |
| **`test_05_scenarios_and_ai_builder.py`** | `/scenarios`, `/scenarios/builder` | Attack scenario catalog filtering (BOLA, SQLi, SSRF, Injection) and AI Scenario Builder prompt submission. |
| **`test_06_simulation_and_kill_switch.py`** | `/test-runs`, `/route-broker` | Live test run execution, active route proxy monitoring, and **Emergency Kill Switch** one-click revocation. |
| **`test_07_attack_graph_and_replay.py`** | `/attack-graph` | React Flow visual canvas, node/edge rendering, step inspection, and interactive timeline playback controls. |
| **`test_08_defence_and_observability.py`** | `/defence`, `/observability` | Automated remediation recommendations, 1-Click mitigation apply, and Prometheus telemetry metrics. |
| **`test_09_executive_reporting.py`** | `/reports` | Security posture delta calculation, report archive, and multi-format exports (PDF, Markdown, CSV). |

---

## Installation & Setup

1. **Install Python dependencies**:
   ```bash
   pip install selenium webdriver-manager pytest
   ```

2. **Start the Pantheon Development Servers** (in separate terminals):
   * Backend API:
     ```bash
     cd backend
     uvicorn app.main:app --port 8000
     ```
   * Frontend SPA:
     ```bash
     cd frontend
     npm run dev
     ```

---

## Running the Tests

### 1. Unified Test Runner Script (Recommended)
```bash
# Automated headless mode (default for CI/CD)
python tests_selenium/run_selenium_suite.py

# Visible GUI mode (ideal for live college viva & demonstration)
python tests_selenium/run_selenium_suite.py --no-headless

# Target Microsoft Edge or Mozilla Firefox
python tests_selenium/run_selenium_suite.py --browser=edge
```

### 2. Standard Pytest Execution
```bash
# Run all Selenium tests headless
pytest tests_selenium -v --headless

# Run a specific module
pytest tests_selenium/test_06_simulation_and_kill_switch.py -v --no-headless
```

---

## Screenshots & Audit Artifacts

Every test execution automatically captures high-resolution full-screen browser screenshots upon step completion in:
```
tests_selenium/reports/screenshots/
```
These screenshots can be directly embedded into the **Final Project Report (Print)** and **Review 2 PPT presentation**.

# Contributing to Pantheon

Thank you for your interest in contributing to **Pantheon**! As an enterprise-grade Cyber Range and Security Testing Platform, Pantheon relies on clean architecture, resilient code, and community collaboration.

Please take a moment to review this document before submitting contributions.

---

## 🧭 Code of Conduct

All contributors and maintainers are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project, you agree to uphold its standards.

---

## 🛠️ Getting Started

### Prerequisites

Ensure you have installed:
- **Docker & Docker Compose** (v24+)
- **Python 3.12+** and `pip` / `venv`
- **Node.js 20+** and `npm` (or `pnpm` / `bun`)
- **Git**

### Setting Up Local Environment

1. **Fork & Clone**:
   ```bash
   git clone https://github.com/<your-username>/Pantheon1.git
   cd Pantheon1
   ```

2. **Start Infrastructure Services**:
   ```bash
   docker compose up -d postgres redis minio
   ```

3. **Backend Setup**:
   ```bash
   cd backend
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate

   pip install -r requirements.txt
   alembic upgrade head
   uvicorn app.main:app --reload --port 8000
   ```

4. **Frontend Setup**:
   ```bash
   cd ../frontend
   npm install
   npm run dev
   ```

---

## 🔄 Development Workflow

### Branch Naming Conventions

Create a topic branch starting from `main`:
- `feat/feature-name` — for new capabilities or modules
- `fix/bug-description` — for bug fixes and patches
- `docs/topic-name` — for documentation improvements
- `refactor/scope` — for code refactoring without behavior changes
- `test/test-scope` — for adding or fixing test suites
- `perf/optimization` — for performance improvements

### Commit Messages

We adhere to the [Conventional Commits](https://www.conventionalcommits.org/) specification:
- `feat: add ephemeral route broker proxy rules`
- `fix(backend): resolve docker build timeout on heavy repos`
- `docs: update deployment and architecture guides`
- `test(frontend): add attack graph node interaction tests`

---

## 🧪 Testing & Code Quality

Before opening a pull request, ensure all linters and tests pass:

### Backend Checks
```bash
cd backend
ruff check .
pytest
```

### Frontend Checks
```bash
cd frontend
npm run lint
npm run test
```

---

## 📬 Submitting a Pull Request (PR)

1. **Ensure your branch is up-to-date** with the latest `main` branch.
2. **Follow the Pull Request Template**: Describe the purpose of your PR, link relevant issues, and list testing procedures.
3. **Include tests**: Add unit or integration tests for new functionality or bug fixes.
4. **Keep PRs focused**: Avoid bundling unrelated changes into a single PR.
5. **CI Checks**: Ensure all GitHub Actions CI checks pass.

---

## 🐞 Reporting Bugs & Requesting Features

- **Search Existing Issues**: Ensure the issue or feature hasn't already been reported.
- **Use GitHub Issue Templates**: Provide detailed reproduction steps, logs, expected vs actual behavior, and environment specifications.
- **Security Vulnerabilities**: Do **not** disclose security vulnerabilities via public GitHub issues. Follow our [Security Policy](SECURITY.md).

---

## 📄 License

By contributing to Pantheon, you agree that your contributions will be licensed under the [MIT License](LICENSE).

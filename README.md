# Pantheon — B2B Security Testing Platform & Cyber Range

[![Backend CI](https://github.com/ash-ftw/Pantheon1/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/ash-ftw/Pantheon1/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/ash-ftw/Pantheon1/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/ash-ftw/Pantheon1/actions/workflows/frontend-ci.yml)

Pantheon is an enterprise B2B Cyber Range and Security Testing Platform. It enables organizations to securely deploy target applications into isolated Kubernetes environments, execute controlled security attack scenarios via ephemeral route brokers, visualize real-time attack graphs, observe system behavior, and generate actionable defense recommendations and reports.

---

## Table of Contents

- [System Architecture & Stack](#system-architecture--stack)
- [Requirements & Prerequisites](#requirements--prerequisites)
- [Local Infrastructure (Docker Compose)](#local-infrastructure-docker-compose)
- [Step-by-Step Setup Guide](#step-by-step-setup-guide)
  - [1. Infrastructure Services](#1-infrastructure-services)
  - [2. Backend Setup](#2-backend-setup)
  - [3. Frontend Setup](#3-frontend-setup)
- [Running Tests & Code Quality Checks](#running-tests--code-quality-checks)
- [Environment Variables Reference](#environment-variables-reference)
- [CI/CD Pipelines](#cicd-pipelines)
- [Project Directory Structure](#project-directory-structure)
- [Troubleshooting](#troubleshooting)

---

## System Architecture & Stack

### Architecture Overview
Pantheon utilizes a tenant-isolated control plane and execution model:
- **Control Plane**: FastAPI backend + React frontend managing organizations, applications, attack scenarios, safety allowlists, and execution jobs.
- **Tenant Environment**: Isolated namespaces containing customer applications, default-deny network policies, resource quotas, and Chaos Mesh fault-injection hooks.
- **Attack Engine & Ephemeral Route Broker**: Ephemeral attacker workloads executing HTTP/load/security scenarios across temporary, TTL-managed access routes without exposing tenant credentials.

### Tech Stack
- **Frontend**: React 19, TypeScript 5.9, Vite 8, Tailwind CSS v4, Zustand 5, TanStack Query 5, React Router 7, Monaco Editor, XYFlow (React Flow), Recharts, Lucide Icons, Vitest.
- **Backend**: Python 3.11+ / 3.12, FastAPI 0.115, Uvicorn, SQLAlchemy 2.0 (asyncpg), Alembic, Pydantic v2, Celery 5.4, PyJWT (RS256), Structlog, Pytest, Ruff, Pyright.
- **Databases & Infrastructure**: PostgreSQL 16, Redis 7, MinIO (S3 API), Docker Registry v2 (S3-backed), Docker / BuildKit / Paketo Buildpacks, k3s / Kubernetes API.

---

## Requirements & Prerequisites

Ensure the following system tools and dependencies are installed on your environment before starting:

### Required Software & Runtimes

| Component | Minimum Version | Recommended Version | Purpose |
|---|---|---|---|
| **OS** | Linux, macOS, or Windows 10/11 (WSL2/PowerShell) | Ubuntu 22.04+ / macOS 14+ / Windows 11 WSL2 | Operating System |
| **Python** | `3.11.0` | `3.12.x` | Backend API & Celery Task Worker |
| **Node.js** | `20.0.0` | `22.x` (LTS) | Frontend Web Application |
| **npm** | `10.0.0` | `10.x+` | Frontend Dependency Management |
| **Docker Engine / Desktop** | `24.0.0` | `27.x+` | Container builds & local infrastructure |
| **Docker Compose** | `v2.20.0` | `v2.27.x+` | Orchestrating local stateful services |
| **OpenSSL** | `1.1.1` | `3.x` | Generating RS256 JWT key pairs |

### Optional / Advanced Infrastructure Prerequisites (Production / Full Cluster Testing)
- **k3s / Kubernetes Cluster**: `v1.30.x`
- **Helm**: `v3.16+` (For installing Prometheus, Loki, Chaos Mesh)
- **pack CLI**: `v0.35+` (For Cloud Native Buildpacks compilation)
- **Trivy**: `v0.56+` (Container vulnerability scanning)

---

## Local Infrastructure (Docker Compose)

The local development environment uses `docker-compose.yml` to run all necessary stateful supporting services:

- **PostgreSQL 16**: Port `5432` (`pantheon` user, database `pantheon`)
- **Redis 7**: Port `6379` (Celery broker, result backend, and caching)
- **MinIO S3 Storage**: Port `9000` (API) & Port `9001` (Console) (`minioadmin:minioadmin`)
- **MinIO Bucket Auto-Init**: Creates `pantheon-artifacts` and `pantheon-registry` buckets automatically.
- **Docker Registry v2**: Port `5000` (backed by MinIO S3 storage)

---

## Step-by-Step Setup Guide

Follow these steps sequentially to set up and run Pantheon locally.

### 1. Infrastructure Services

1. Open a terminal in the root directory (`Pantheon1`).
2. Start all containerized local services in detached mode:
   ```bash
   docker compose up -d
   ```
3. Verify that all container services are healthy:
   ```bash
   docker compose ps
   ```
   *Expected containers*: `pantheon-postgres`, `pantheon-redis`, `pantheon-minio`, `pantheon-minio-init`, `pantheon-registry`.

---

### 2. Backend Setup

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   - **Linux / macOS**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. Upgrade `pip` and install backend dependencies in editable mode (including development tools):
   ```bash
   python -m pip install --upgrade pip
   pip install -e ".[dev]"
   ```

4. Create the environment configuration file:
   ```bash
   cp .env.example .env
   ```

5. Generate the JWT RS256 key pair:
   ```bash
   mkdir -p keys
   openssl genrsa -out keys/jwt_private.pem 2048
   openssl rsa -in keys/jwt_private.pem -pubout -out keys/jwt_public.pem
   ```

6. Run Database Migrations using Alembic:
   ```bash
   alembic upgrade head
   ```

7. Start the FastAPI Development Server:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   - API Docs will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)
   - OpenAPI Spec JSON: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
   - Health Check: [http://localhost:8000/health](http://localhost:8000/health)

8. In a separate terminal (with virtualenv activated), start the Celery Worker:
   ```bash
   cd backend
   celery -A app.worker.celery_app worker --loglevel=info
   ```

---

### 3. Frontend Setup

1. Open a new terminal and navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Start the Vite Development Server:
   ```bash
   npm run dev
   ```

4. Open your browser and navigate to:
   - Frontend UI: [http://localhost:5173](http://localhost:5173)

---

## Running Tests & Code Quality Checks

### Backend Quality Assurance

Run code checks from the `backend` directory with the virtualenv active:

- **Run Unit & Integration Tests (Pytest)**:
  ```bash
  pytest -v
  ```
- **Lint & Format Checks (Ruff)**:
  ```bash
  ruff check .
  ruff format --check .
  ```
- **Apply Automatic Fixes**:
  ```bash
  ruff check --fix .
  ruff format .
  ```
- **Type Checking (Pyright)**:
  ```bash
  pyright
  ```

### Frontend Quality Assurance

Run code checks from the `frontend` directory:

- **Run Frontend Tests (Vitest)**:
  ```bash
  npm run test
  ```
- **Lint Code (ESLint)**:
  ```bash
  npm run lint
  ```
- **Check Code Formatting (Prettier)**:
  ```bash
  npm run format:check
  ```
- **Apply Code Formatting**:
  ```bash
  npm run format
  ```
- **Type Check & Production Build Verification**:
  ```bash
  npm run build
  ```

---

## Environment Variables Reference

Backend configuration parameters are defined in `backend/.env`.

| Variable | Default Value | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://pantheon:pantheon_dev@localhost:5432/pantheon` | Async PostgreSQL database connection URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis broker and cache endpoint |
| `MINIO_ENDPOINT` | `localhost:9000` | S3-compatible object storage endpoint |
| `MINIO_ACCESS_KEY` | `minioadmin` | S3 access key |
| `MINIO_SECRET_KEY` | `minioadmin` | S3 secret key |
| `MINIO_BUCKET` | `pantheon-artifacts` | Default bucket for storage artifacts |
| `REGISTRY_URL` | `localhost:5000` | Internal container registry endpoint |
| `JWT_PRIVATE_KEY_PATH` | `./keys/jwt_private.pem` | Path to RS256 private key |
| `JWT_PUBLIC_KEY_PATH` | `./keys/jwt_public.pem` | Path to RS256 public key |
| `JWT_ALGORITHM` | `RS256` | JWT signing algorithm |
| `APP_ENV` | `development` | Application environment (`development` / `production`) |
| `APP_DEBUG` | `true` | Enable debug mode |
| `LOG_LEVEL` | `DEBUG` | Application logging verbosity (`DEBUG`, `INFO`, `WARN`, `ERROR`) |

---

## CI/CD Pipelines

Pantheon runs automated GitHub Actions workflows on every push and pull request targeting the `main` branch:

- **Backend Pipeline** (`.github/workflows/backend-ci.yml`):
  - Sets up Python 3.12 with Postgres & Redis service containers.
  - Installs dependencies (`pip install -e ".[dev]"`).
  - Verifies code style (`ruff check`, `ruff format`).
  - Performs static type checking (`pyright`).
  - Applies database migrations (`alembic upgrade head`).
  - Runs full test suite (`pytest -v`).

- **Frontend Pipeline** (`.github/workflows/frontend-ci.yml`):
  - Sets up Node.js 22 with dependency caching.
  - Installs dependencies (`npm ci`).
  - Lints codebase (`npm run lint`).
  - Verifies code formatting (`npm run format:check`).
  - Executes type check and production bundle build (`npm run build`).
  - Executes test suite (`npm run test`).

---

## Project Directory Structure

```
Pantheon1/
├── .github/
│   └── workflows/
│       ├── backend-ci.yml         # GitHub Actions workflow for backend
│       └── frontend-ci.yml        # GitHub Actions workflow for frontend
├── backend/
│   ├── alembic/                   # Database migration scripts
│   ├── app/
│   │   ├── config.py              # Pydantic settings configuration
│   │   ├── database.py            # Async SQLAlchemy engine & session
│   │   ├── main.py                # FastAPI app entry point
│   │   ├── models.py              # SQLAlchemy ORM models
│   │   ├── schemas.py             # Pydantic data schemas
│   │   ├── worker.py              # Celery task application definition
│   │   ├── routers/               # API endpoint routers
│   │   ├── services/              # Core business & infrastructure logic
│   │   └── tasks/                 # Background Celery tasks
│   ├── tests/                     # Backend pytest suite
│   ├── .env.example               # Template environment configuration
│   ├── pyproject.toml             # Python package & tool configuration
│   └── pytest.ini                 # Pytest configuration
├── frontend/
│   ├── public/                    # Static assets
│   ├── src/
│   │   ├── components/            # Reusable UI components & primitives
│   │   ├── layouts/               # Application layouts
│   │   ├── pages/                 # Route page components
│   │   ├── stores/                # Zustand client state stores
│   │   ├── index.css              # Global styles & design system tokens
│   │   └── main.tsx               # Application entry point
│   ├── package.json               # Node.js dependencies & scripts
│   ├── tsconfig.json              # TypeScript root configuration
│   └── vite.config.ts             # Vite build configuration
├── infra/                         # Infrastructure & Terraform modules
├── docker-compose.yml             # Local stateful services (Postgres, Redis, MinIO, Registry)
└── README.md                      # Project setup & documentation guide
```

---

## Troubleshooting

### 1. Database Connection Refused (`asyncpg.exceptions.CannotConnectNowError`)
- Ensure PostgreSQL container is up and running: `docker compose ps`
- Confirm port `5432` is not occupied by a host PostgreSQL instance.

### 2. JWT Key File Not Found
- Ensure you ran the `openssl` key generation commands in `backend/keys/`.
- Check `.env` paths: `JWT_PRIVATE_KEY_PATH=./keys/jwt_private.pem`.

### 3. Celery Tasks Pending / Not Processing
- Check if Redis container is active: `docker compose logs redis`
- Verify the Celery worker process is running: `celery -A app.worker.celery_app worker -l info`

### 4. Vite Frontend Port Conflicts
- Default dev port is `5173`. If occupied, Vite will automatically try `5174`. Adjust backend CORS origins in `backend/app/main.py` if needed.

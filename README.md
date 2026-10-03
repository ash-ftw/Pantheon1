# Pantheon — Enterprise Cyber Range & Security Testing Platform

[![Backend CI](https://github.com/ash-ftw/Pantheon1/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/ash-ftw/Pantheon1/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/ash-ftw/Pantheon1/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/ash-ftw/Pantheon1/actions/workflows/frontend-ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![React 19](https://img.shields.io/badge/react-19-61dafb.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Pantheon** is a modern, enterprise-grade B2B Cyber Range and Security Testing Platform. It allows security teams and developers to deploy target web applications into sandboxed environments, execute simulated attack scenarios through ephemeral route brokers, visualize real-time attack graphs, observe system telemetry, and generate actionable defense remediations powered by AI.

---

## 📑 Table of Contents

- [Core Capabilities & Features](#-core-capabilities--features)
- [System Architecture & Stack](#-system-architecture--stack)
- [Requirements & Prerequisites](#-requirements--prerequisites)
- [Local Infrastructure (Docker Compose)](#-local-infrastructure-docker-compose)
- [Step-by-Step Setup Guide](#-step-by-step-setup-guide)
  - [1. Infrastructure Services](#1-infrastructure-services)
  - [2. Backend Setup](#2-backend-setup)
  - [3. Frontend Setup](#3-frontend-setup)
- [Application Onboarding & Ingestion Pipeline](#-application-onboarding--ingestion-pipeline)
  - [Automated Language & Framework Detection](#automated-language--framework-detection)
  - [AI Dockerfile Generation](#ai-dockerfile-generation)
  - [Dual-Mode Sandbox & Live Preview Proxy](#dual-mode-sandbox--live-preview-proxy)
- [End-to-End Workflow Guide](#-end-to-end-workflow-guide)
- [Running Tests & Quality Assurance](#-running-tests--quality-assurance)
- [Environment Variables Reference](#-environment-variables-reference)
- [API Endpoints Overview](#-api-endpoints-overview)
- [Project Directory Structure](#-project-directory-structure)
- [Troubleshooting & FAQ](#-troubleshooting--faq)

---

## ⚡ Core Capabilities & Features

- **Automated App Onboarding**: Ingest source code via Git repository URL or ZIP bundle upload.
- **Deep Language & Framework Detection**: Automatic zero-config detection for Node.js (React, Next.js, Express), Python (FastAPI, Flask, Django), Go (Gin), Rust, Java (Spring Boot), Ruby (Rails), PHP (Laravel), and .NET.
- **AI-Powered Dockerfile Engine**: Synthesizes multi-stage, secure container specifications on the fly using NVIDIA NIM / Nemotron or Groq LLMs with intelligent heuristic fallbacks.
- **Dual-Mode Sandboxing**: Run target applications inside isolated local Docker containers with dynamic port allocation (`8085-8199`) or Kubernetes/k3s tenant namespaces with default-deny network policies.
- **In-App Live Preview & Reverse Proxy**: Seamless iframe application previewing (`/api/apps/{app_id}/preview`) with automatic HTML base rewriting, root-relative asset proxying, and CORS stripping.
- **Controlled Attack Scenarios**: Execute load, endpoint fuzzing, SQLi, and OWASP Top 10 attack patterns against target applications via ephemeral route brokers.
- **Interactive Attack Graph Visualization**: Real-time XYFlow (React Flow) attack surface graphs mapping discovered routes, sensitive parameters, and attack pathways.
- **AI Defense Recommendations**: Automated remediation guides, WAF rule generation, and security patch suggestions powered by LLM threat analysis.
- **Comprehensive Executive Reporting**: Generate and export audit-ready security assessment reports and vulnerability metrics.

---

## 🏛 System Architecture & Stack

```mermaid
flowchart TD
    User([User / Browser]) <--> FE[Frontend: React 19 + Vite]
    FE <-->|REST API + WebSockets| BE[Control Plane: FastAPI Backend]
    
    subgraph Storage & Infrastructure
        BE <--> PG[(PostgreSQL 16)]
        BE <--> Redis[(Redis 7 / Celery Broker)]
        BE <--> MinIO[(MinIO S3 Object Storage)]
        BE <--> Reg[Private Docker Registry:2]
    end

    subgraph Ingestion & AI Engine
        BE --> Det[Language & Framework Detector]
        BE --> AIDocker[AI Dockerfile Generator\nNVIDIA NIM / Groq / Fallbacks]
        BE --> Build[Docker / BuildKit Engine]
        Build --> Reg
    end

    subgraph Runtime Sandbox
        BE <--> Runtime[App Runtime Service\nDocker Engine / k3s API]
        Runtime --> TargetApp[Target Application Instance\nPorts 8085-8199]
    end

    subgraph Live Preview Proxy
        User -->|/api/apps/:id/preview| BE
        BE <-->|Proxies & Rewrites Assets| TargetApp
    end
```

### Tech Stack

| Domain | Technologies |
|---|---|
| **Frontend** | React 19, TypeScript 5.9, Vite 8, Tailwind CSS v4, Zustand 5, TanStack Query 5, React Router 7, Monaco Editor, XYFlow (React Flow), Recharts, Lucide Icons, Vitest |
| **Backend** | Python 3.12+, FastAPI 0.115, Uvicorn, SQLAlchemy 2.0 (asyncpg), Alembic, Pydantic v2, Celery 5.4, PyJWT (RS256), Structlog, Pytest, Ruff, Pyright |
| **AI Layer** | NVIDIA NIM (Nemotron 3.5 Lightning 30B), Groq (OpenAI-compatible client), Custom Heuristics |
| **Stateful Services** | PostgreSQL 16, Redis 7, MinIO S3 Object Store, Docker Registry v2 |
| **Runtime & Isolation** | Docker Engine / BuildKit, Local Container Sandboxes, k3s / Kubernetes API, Ephemeral Route Broker |

---

## 📋 Requirements & Prerequisites

Ensure the following system tools are installed on your environment before starting:

| Tool | Minimum Version | Recommended Version | Purpose |
|---|---|---|---|
| **Operating System** | Linux, macOS, or Windows 10/11 | Ubuntu 22.04+ / macOS 14+ / Windows 11 | Host OS |
| **Python** | `3.11.0` | `3.12.x` | Backend API & Celery Task Worker |
| **Node.js** | `20.0.0` | `22.x` (LTS) | Frontend Web Application |
| **npm** | `10.0.0` | `10.x+` | Frontend Dependency Management |
| **Docker Engine / Desktop** | `24.0.0` | `27.x+` | Container builds & local infrastructure |
| **Docker Compose** | `v2.20.0` | `v2.27.x+` | Orchestrating local stateful services |
| **OpenSSL** | `1.1.1` | `3.x` | Generating RS256 JWT key pairs |

---

## 🐳 Local Infrastructure (Docker Compose)

The local development environment uses `docker-compose.yml` to spin up supporting stateful services:

```bash
docker compose up -d
```

| Service | Container Name | Host Port | Credentials / Purpose |
|---|---|---|---|
| **PostgreSQL 16** | `pantheon-postgres` | `5432` | `pantheon:pantheon_dev` / Main DB `pantheon` |
| **Redis 7** | `pantheon-redis` | `6379` | Celery broker, cache, and pub/sub |
| **MinIO S3** | `pantheon-minio` | `9000` (API), `9001` (Console) | `minioadmin:minioadmin` / Bucket storage |
| **MinIO Bucket Init**| `pantheon-minio-init` | — | Automatically provisions buckets |
| **Docker Registry** | `pantheon-registry` | `5000` | Local container image registry (S3-backed) |

Verify that all services are healthy:
```bash
docker compose ps
```

---

## 🚀 Step-by-Step Setup Guide

### 1. Infrastructure Services

From the project root:
```bash
docker compose up -d
```

---

### 2. Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a Python virtual environment**:
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

3. **Install dependencies**:
   ```bash
   python -m pip install --upgrade pip
   pip install -e ".[dev]"
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   *(Optionally add your `NVIDIA_NIM_API_KEY` or `GROQ_API_KEY` in `backend/.env` for AI-assisted features).*

5. **Generate JWT RS256 Key Pair**:
   ```bash
   mkdir -p keys
   openssl genrsa -out keys/jwt_private.pem 2048
   openssl rsa -in keys/jwt_private.pem -pubout -out keys/jwt_public.pem
   ```

6. **Run Database Migrations**:
   ```bash
   alembic upgrade head
   ```

7. **Start the Backend API Server**:
   - **Using PowerShell Helper (Windows)**:
     ```powershell
     .\run.ps1
     ```
   - **Or directly via Uvicorn**:
     ```bash
     uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
     ```

   - **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

8. **Start the Celery Background Worker** *(in a separate terminal)*:
   ```bash
   cd backend
   # Activate virtualenv first
   celery -A app.worker.celery_app worker --loglevel=info
   ```

---

### 3. Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install Node dependencies**:
   ```bash
   npm install
   ```

3. **Start the Vite development server**:
   ```bash
   npm run dev
   ```

4. **Access the application**:
   - Web UI: [http://localhost:5173](http://localhost:5173)

---

## 📦 Application Onboarding & Ingestion Pipeline

Pantheon makes target application deployment effortless through automated code analysis and container synthesis:

```
Source Code (Git / ZIP)
       │
       ▼
Language & Framework Detection (Node.js, Python, Go, Rust, Java, etc.)
       │
       ├─► Has Dockerfile? ────► [Use Existing Dockerfile]
       │
       └─► No Dockerfile?  ────► [AI Dockerfile Generation (NVIDIA NIM / Groq / Fallbacks)]
                                         │
                                         ▼
                               Container Build & Push (localhost:5000)
                                         │
                                         ▼
                               Sandbox Deployment (Docker / k3s)
                                         │
                                         ▼
                        Live Preview Proxy & Route Discovery (/api/apps/:id/preview)
```

### Automated Language & Framework Detection
- Analyzes configuration files (`package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, etc.).
- Automatically infers application frameworks (FastAPI, Flask, Next.js, Express, Spring Boot), default execution ports (e.g., `3000`, `8000`, `8080`), and appropriate start commands.

### AI Dockerfile Generation
- Ingested repositories without a Dockerfile are dynamically synthesized with optimized multi-stage build files.
- Uses **NVIDIA NIM** (`nvidia/nemotron-3.5-lightning-30b-a3b`) or **Groq** (`gpt-oss-120b`).
- Falls back to built-in, hardened multi-stage Dockerfile templates if LLM providers are offline.

### Dual-Mode Sandbox & Live Preview Proxy
- **Local Container Sandbox**: Starts target apps inside isolated Docker containers on dedicated ports (`8085-8199`).
- **Live Preview Proxy (`/api/apps/{app_id}/preview`)**:
  - Automatically rewrites HTML `<base>` and root-relative URLs (`href="/..."`, `src="/..."`).
  - Strips restrictive headers (`X-Frame-Options`, `Content-Security-Policy`) for seamless iframe previews in the dashboard.
  - Transparently proxies APIs, assets, and routes.
- **Direct Access**: Applications can also be accessed directly via `http://localhost:<assigned_port>`.

---

## 🔄 End-to-End Workflow Guide

1. **Register Organization & Login**: Create an organization and log in to obtain JWT authentication.
2. **Onboard an Application**: Navigate to **App Onboarding**, select **Upload ZIP** or **Git Repository**, and trigger analysis.
3. **Review & Deploy**: Review detected framework, port settings, and generated Dockerfile. Click **Build & Deploy**.
4. **Interactive Preview**: Preview the live running application inside the dashboard using the embedded proxy.
5. **Run Security Discovery**: Automatically scan target application routes and detect parameters.
6. **Execute Scenarios**: Select an attack scenario (Fuzzing, SQLi, Auth bypass, Denial of Service) and trigger execution.
7. **Inspect Attack Graph**: View the live XYFlow graph showing exploited pathways and vulnerability nodes.
8. **Generate Defense Plan**: Use AI-assisted recommendations to generate patch instructions and export reports.

---

## 🧪 Running Tests & Quality Assurance

### Backend Quality Assurance

Run these checks from the `backend/` directory with `.venv` active:

- **Run Pytest Suite**:
  ```bash
  pytest -v
  ```
- **Lint Code (Ruff)**:
  ```bash
  ruff check .
  ```
- **Verify Formatting (Ruff)**:
  ```bash
  ruff format --check .
  ```
- **Auto-Fix Formatting & Lint Issues**:
  ```bash
  ruff check --fix .
  ruff format .
  ```
- **Static Type Checking (Pyright)**:
  ```bash
  pyright
  ```

### Frontend Quality Assurance

Run these checks from the `frontend/` directory:

- **Run Vitest Suite**:
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
- **Auto-Fix Formatting**:
  ```bash
  npm run format
  ```
- **Type Check & Production Build**:
  ```bash
  npm run build
  ```

---

## ⚙️ Environment Variables Reference

Defined in `backend/.env` (modeled via `backend/app/config.py`):

| Variable | Default Value | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://pantheon:pantheon_dev@localhost:5432/pantheon` | Async PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis broker and cache endpoint |
| `MINIO_ENDPOINT` | `localhost:9000` | S3 object store host endpoint |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `MINIO_BUCKET` | `pantheon-artifacts` | Bucket for storage artifacts |
| `REGISTRY_URL` | `localhost:5000` | Container registry endpoint for built images |
| `JWT_PRIVATE_KEY_PATH` | `./keys/jwt_private.pem` | RS256 private key file path |
| `JWT_PUBLIC_KEY_PATH` | `./keys/jwt_public.pem` | RS256 public key file path |
| `JWT_ALGORITHM` | `RS256` | JWT signing algorithm |
| `APP_ENV` | `development` | Environment mode (`development` / `production`) |
| `APP_DEBUG` | `true` | Debug mode toggle |
| `LOG_LEVEL` | `DEBUG` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `AI_PROVIDER` | `nvidia_nim` | Primary AI provider (`nvidia_nim` or `groq`) |
| `NVIDIA_NIM_API_KEY` | `""` | API key for NVIDIA NIM Nemotron LLM |
| `NVIDIA_NIM_BASE_URL`| `https://integrate.api.nvidia.com/v1` | NVIDIA NIM API base URL |
| `NVIDIA_NIM_MODEL` | `nvidia/nemotron-3.5-lightning-30b-a3b` | Target NIM model identifier |
| `GROQ_API_KEY` | `""` | Groq API key for fallback inference |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | Groq API base URL |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Groq model identifier |
| `PANTHEON_TARGET_HOST`| `localhost` | Host address for target application probing and proxying |

---

## 🌐 API Endpoints Overview

| Category | Endpoint Prefix | Key Capabilities |
|---|---|---|
| **System** | `/health` | Service health status |
| **Auth & Orgs** | `/api/auth`, `/api/orgs` | User registration, login, JWT token issue, tenant org management |
| **Apps & Ingestion**| `/api/apps` | App creation, ZIP/Git onboarding, language detection, AI Dockerfile generation, build streaming, start/stop/restart |
| **Live Preview** | `/api/apps/{id}/preview` | Reverse proxy for running target applications with asset rewriting |
| **Discovery** | `/api/discovery` | Route mapping, endpoint discovery, parameter inspection |
| **Scenarios** | `/api/scenarios` | Security attack scenarios catalog and customized run configs |
| **Safety** | `/api/safety` | CIDR allowlists, sensitive endpoint guards, rate-limit safety checks |
| **Route Proxy** | `/api/routes`, `/api/proxy` | Ephemeral route broker management and secure target forwarding |
| **Attack Graph** | `/api/attack-graph` | Node-link attack surface graph models and topology endpoints |
| **Defense & AI** | `/api/defence`, `/api/ai` | Remediation strategies, WAF rule generation, AI threat assistant |
| **Reports** | `/api/reports` | Executive summaries, vulnerability exports, security audits |
| **Dashboard** | `/api/dashboard` | Aggregated security metrics, runtime counts, scenario statuses |

---

## 📁 Project Directory Structure

```
Pantheon1/
├── .github/
│   └── workflows/
│       ├── backend-ci.yml             # GitHub Actions backend CI pipeline
│       └── frontend-ci.yml            # GitHub Actions frontend CI pipeline
├── backend/
│   ├── alembic/                       # Database migration versions
│   ├── app/
│   │   ├── config.py                  # Pydantic v2 settings & environment variables
│   │   ├── database.py                # Async SQLAlchemy engine & session factory
│   │   ├── main.py                    # FastAPI application initialization & routing
│   │   ├── models.py                  # SQLAlchemy ORM database models
│   │   ├── schemas.py                 # Pydantic validation schemas
│   │   ├── worker.py                  # Celery application configuration
│   │   ├── routers/                   # Modular API routers
│   │   │   ├── ai.py                  # AI assistant & remediation router
│   │   │   ├── apps.py                # App onboarding & preview reverse proxy router
│   │   │   ├── attack_graph.py        # Attack surface graph router
│   │   │   ├── auth.py                # JWT authentication router
│   │   │   ├── dashboard.py           # Metrics aggregation router
│   │   │   ├── defence.py             # Defense & mitigation router
│   │   │   ├── discovery.py           # Route & API discovery router
│   │   │   ├── reports.py             # Security reporting router
│   │   │   └── scenarios.py           # Attack scenario definition router
│   │   ├── services/                  # Business & infrastructure logic
│   │   │   ├── ai_dockerfile_generator.py # AI & heuristic Dockerfile generator
│   │   │   ├── app_runtime_service.py # Container sandboxing & port management
│   │   │   ├── docker_builder.py      # Docker BuildKit client & registry pusher
│   │   │   └── language_detector.py   # Multi-language & framework detector
│   │   └── tasks/
│   │       ├── ingestion.py           # Celery tasks for app cloning, build & deploy
│   │       └── scenarios.py           # Celery tasks for attack scenario execution
│   ├── tests/                         # Pytest unit and integration test suite
│   ├── run.ps1                        # PowerShell development server launch script
│   ├── .env.example                   # Environment configuration template
│   └── pyproject.toml                 # Backend dependencies & tool configs
├── frontend/
│   ├── src/
│   │   ├── components/                # Reusable UI primitives & components
│   │   ├── layouts/                   # Global page layouts & navigation
│   │   ├── pages/                     # Route views (Onboarding, Dashboard, Scenarios, etc.)
│   │   ├── stores/                    # Zustand client state stores
│   │   ├── styles/                    # Global CSS & Tailwind design tokens
│   │   └── main.tsx                   # Frontend entry point
│   ├── package.json                   # Frontend dependencies & npm scripts
│   └── vite.config.ts                 # Vite bundler configuration
├── infra/                             # Infrastructure definitions & Kubernetes manifests
├── docker-compose.yml                 # Local stateful services (Postgres, Redis, MinIO, Registry)
└── README.md                          # Project documentation and setup guide
```

---

## ❓ Troubleshooting & FAQ

### 1. Target App Preview Shows "Connection Refused"
- Ensure the container runtime is running: check `docker ps` for your target container.
- Confirm the target application binds to `0.0.0.0` (not `127.0.0.1` inside the container).
- Check the assigned host port in the Pantheon Dashboard (e.g. `8085`) and ensure no host firewall blocks it.

### 2. Missing JWT Private / Public Key
- Generate keys using OpenSSL before starting Uvicorn:
  ```bash
  mkdir -p backend/keys
  openssl genrsa -out backend/keys/jwt_private.pem 2048
  openssl rsa -in backend/keys/jwt_private.pem -pubout -out backend/keys/jwt_public.pem
  ```

### 3. Database Connection Failure
- Verify the PostgreSQL container is active: `docker compose ps`
- Confirm `DATABASE_URL` in `backend/.env` points to `localhost:5432`.

### 4. Celery Tasks Pending or Failing
- Ensure Redis is running: `docker compose logs redis`
- Make sure the Celery worker is active in a separate terminal:
  ```bash
  celery -A app.worker.celery_app worker --loglevel=info
  ```

### 5. AI Dockerfile Generation Fallback
- If `NVIDIA_NIM_API_KEY` or `GROQ_API_KEY` is not provided, Pantheon automatically falls back to hardened deterministic Dockerfile templates matching the detected language and framework without interrupting the onboarding flow.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

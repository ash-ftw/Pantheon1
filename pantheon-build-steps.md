# Pantheon — Build Steps

A phased implementation plan combining the PRD, the exact tech stack, and the UI design system into one ordered build guide. Each phase produces something runnable before moving to the next — no phase depends on a module that hasn't been built yet.

---

## Phase 0 — Environment & Scaffolding

Get local infrastructure and empty-but-wired-up apps running before writing feature code.

1. **Provision local Kubernetes**
   - Install k3s (1.30.x), two-node topology: server on the larger machine, agent joined via `K3S_URL` + `K3S_TOKEN` over LAN.
   - Install Docker Engine 27.x + Docker Desktop (or `containerd` directly) for image builds.
   - Confirm two clusters conceptually exist even if physically the same k3s for now: **tenant cluster context** and **range cluster context** — keep kubeconfig contexts separate from day one so the app code never accidentally shares a client.

2. **Install cluster add-ons via Helm (3.16+)**
   - `cert-manager` 1.16+ (self-signed CA for local).
   - `kube-prometheus-stack` (Prometheus 2.54+, Grafana 11.x) — one instance per cluster.
   - `loki-stack` (Loki 3.x + Promtail 3.x).
   - Chaos Mesh 2.7+ — tenant cluster only.
   - Traefik ships bundled with k3s — confirm it's running (`IngressRoute` CRDs available).

3. **Stand up stateful services**
   - PostgreSQL 16.x — one database, no per-tenant schemas.
   - Redis 7.x — logical db 0 (Celery), db 1 (query cache), db 2 (rate limits).
   - MinIO (latest) — S3-compatible object storage for build artifacts and reports.
   - `registry:2` (Phase 0) or Harbor 2.11+ later — image registry, namespaced per org.

4. **Scaffold the backend**
   - Python 3.12 project, FastAPI 0.115+, Uvicorn 0.32+ (uvloop, httptools).
   - `pydantic-settings` 2.x `Settings` class reading from `.env` (never committed).
   - SQLAlchemy 2.0 async engine + Alembic 1.13+ migrations, empty initial migration.
   - structlog 24.x configured (JSON in prod, pretty console in dev), `org_id`/`request_id` context vars wired even before they're used.
   - Ruff 0.7+ and pyright configured; empty CI check passes.

5. **Scaffold the frontend**
   - Vite 6.x + React 19 + TypeScript 5.6 (`strict: true`).
   - Tailwind CSS 4.x, CSS-first config.
   - React Router 7.x data router skeleton with placeholder routes for each module in §6 below.
   - Zustand 5.x — create empty `authStore`, `tenantStore`, `testRunStore` shells.
   - TanStack Query 5.x provider wired, no queries yet.
   - ESLint 9 flat config + Prettier 3.x.
   - **Apply the design token system now** (see Phase 1) so every component built afterward is styled correctly the first time.

6. **CI/CD skeleton**
   - GitHub Actions: separate workflows for frontend (`vitest` + `eslint`), backend (`pytest` + `ruff` + `pyright`), and Terraform (`validate` + `plan` on PR).

**Exit criteria:** empty FastAPI app responds on `/health`, empty React app loads, Postgres/Redis/MinIO reachable, k3s cluster contexts both resolve.

---

## Phase 1 — Design System Foundation

Wire in the extracted color/typography/token system before building any real screens, so nothing gets rebuilt later.

1. Add font imports and `:root` CSS variables to `src/index.css`:
   - Fonts: Rajdhani (500/600/700 — display/headings), Inter (300–600 — body), JetBrains Mono (400/500 — badges, code, metrics, timestamps).
   - Color tokens: background `#07090d`, sidebar `#050709`, card `#0d1117` / border `#1a2332`, secondary `#0f1923`, muted `#111827`, foreground `#e2e8f0`, secondary-foreground `#94a3b8`, muted-foreground `#4b5a6e`.
   - Accents: primary cyan `#00d4aa` (+ `--primary-foreground: #07090d`), accent orange `#ff6b35`, info blue `#3b82f6`, success green `#10b981`, warning gold `#f59e0b`, danger red `#ef4444`.
   - `--radius: 4px`, `--sidebar-width: 220px`.
2. Base body styles: `font-family: var(--font-body)`, `font-size: 13px`, `line-height: 1.5`, antialiased.
3. Utility classes: `.font-display`, `.font-mono`.
4. Map the same tokens into Tailwind's theme (v4 `@theme` block, or `tailwind.config.js` if not fully CSS-first) so `bg-card`, `text-primary`, `border-card-border` etc. work as utilities, not just inline styles.
5. Build the shared component primitives once, reused everywhere afterward:
   - **Primary button** (solid `--primary` bg, `--primary-foreground` text, mono font, uppercase, letter-spacing).
   - **Secondary/outline button** (`--secondary` bg, `--card-border` border).
   - **Status badge** (mono font, small, colored per status: success/warning/danger/info/primary — background at ~12% alpha, border at ~25–30% alpha, solid text).
   - **Card container** (`--card` bg, `--card-border` border, `0 4px 14px rgba(0,0,0,0.6)` shadow, display-font uppercase title).
   - Severity color mapping used everywhere findings/status appear: critical/danger → red, high → orange, medium → gold, low/info → blue, resolved/active → green.

**Exit criteria:** a Storybook-style or throwaway `/design-preview` route renders every primitive so the whole team can sanity-check the look before feature work starts.

---

## Phase 2 — Auth, Orgs & Team Management (PRD §7.1)

The account model everything else is scoped under.

1. **Backend**
   - FastAPI-Users 13.x, extend base user model with `org_id`.
   - PyJWT 2.9+, RS256 (not HS256).
   - Password hashing via bundled passlib[bcrypt], default rounds.
   - Tables: `orgs`, `org_members` (role: Admin/Tester/Viewer), `invitations`.
   - Every tenant-owned table gets an `org_id` column from the start; add Postgres Row-Level Security policies as defense-in-depth alongside the application-layer `WHERE org_id = :org_id` base repository method.
   - Invite-by-email endpoint; invited user sets password on first login.
   - Audit log table (`audit_log`, append-only) — start writing to it from this phase onward for every mutating action.
2. **Frontend**
   - Signup / login / invite-accept flows.
   - `authStore` (Zustand) holds current user + org context.
   - TanStack Query keys namespaced by org from day one: `['org', orgId, ...]`.
   - Org admin screen: member list, role management, pending invitations.
3. **Rate limiting** — slowapi wired onto auth endpoints (won't be the main use, but establishes the pattern before Phase 4's ingestion limits).

**Exit criteria:** a user can sign up, create an org, invite a teammate, and role-based access is enforced on at least one protected endpoint.

---

## Phase 3 — Infrastructure & Provisioning (PRD Module 3)

Get a real tenant Kubernetes namespace provisioned per org before anything can be deployed into it.

1. **Terraform** — `infra/modules/k3s-local/` module: inputs `org_id` + size tier, outputs kubeconfig/cluster endpoint. Local backend for now; never commit `.tfstate`.
2. **Provisioning Celery task** (`provision_tenant_cluster`) — async, org signup triggers this in the background; user isn't blocked waiting.
3. **Namespace defaults applied immediately on creation, before any workload is allowed in:**
   - Default-deny `NetworkPolicy`.
   - `ResourceQuota`.
   - `LimitRange`.
4. **Infrastructure View (read-mostly)** — backend exposes read + scoped-write endpoints over the `kubernetes` Python client (Deployments, Services, ReplicaSets, Ingress, PV, ConfigMaps, Secrets, NetworkPolicies); no raw kubectl ever exposed to the customer.
5. One `ApiClient` per cluster context (tenant vs. range) — **never share a client instance between them.**
6. Frontend: tenant provisioning status shown on the dashboard/onboarding screen (provisioning → ready), Infrastructure View screen listing the org's K8s resources read-only.

**Exit criteria:** creating an org results in a real, isolated namespace with default-deny network policy applied, visible (read-only) in the UI, within the NFR-1.2 requirement.

---

## Phase 4 — Ingestion Pipeline (PRD Module 4 — core new capability)

The path from "I have an app" to "it's running."

1. **Git ingestion** — GitPython, shallow clone (`depth=1`) to ephemeral scratch dir under `/tmp`; full clone only if shallow fails to find expected files; delete scratch dir after image push regardless of outcome.
2. **Compose ingestion** — manual parser (`compose_translator.py`) against the Compose Spec using PyYAML (`safe_load` only) + own validator; extracts `services`, `depends_on`, `environment`, `ports`, `volumes`.
3. **Build path selection**
   - Dockerfile present → Docker BuildKit via `docker-py` (`DOCKER_BUILDKIT=1`), multi-stage respected as-is.
   - No Dockerfile → Paketo Buildpacks via `pack` CLI 0.35+, `builder-jammy-base`, invoked as subprocess.
   - `.dockerignore` respected on both paths.
4. **Secrets extraction** — any `environment:`/`.env` value matching `*_KEY`, `*_SECRET`, `*_PASSWORD`, `*_TOKEN` patterns → K8s `Secret`, referenced via `envFrom`/`valueFrom`, never a literal in the generated `Deployment` spec or visible in the UI.
5. **Manifest generation** — hand-written Python builder using `kubernetes` client's typed models (`V1Deployment`, `V1Service`) directly, not a templating engine. Each Compose `service:` → one `Deployment` + `Service` pair, `depends_on` preserved as startup ordering.
6. **Registry push** — `registry.local/org-<uuid>/app-<name>:tag`, Harbor RBAC or `registry:2` + htpasswd per org.
7. **Image scanning** — Trivy 0.56+ against every built image before deploy; surfaced to the customer as informational, non-blocking.
8. **Celery task** (`ingest_app`) drives: queued → building → pushing → deploying → running, with live log tail streamed via the same Redis pub/sub → WebSocket pattern used later for test runs (build it once here, reuse in Phase 6).
9. **Failure handling** — specific human-readable error (never a bare stack trace) as primary message, with a "view full logs" option; failed builds clean up scratch dirs and any partial resources (NFR-2.2).
10. **Language/framework detection** — Buildpacks' own detection phase + `enry` (or extension heuristics) to fill in "what we found" metadata for the UI even on the Dockerfile-present path.
11. **Version history** — `app_versions`/`app_deployments` tables retain every deploy: what, when, build log reference. Redeploy reuses the same flow, doesn't overwrite history.
12. **Frontend**
   - Onboarding flow: Git URL input or compose upload/paste.
   - Live build progress panel (stage indicator + streaming log tail via WebSocket store with auto-reconnect/backoff).
   - Redeploy button on an existing app, version history list.

**Exit criteria:** submitting a public Git repo with a Dockerfile results in a running pod in the tenant namespace in under 3 minutes (NFR-3.2), with live progress visible and secrets never shown in plaintext.

---

## Phase 5 — AI Target Analysis & Endpoint Discovery (PRD Module 5–6)

Runs automatically right after Phase 4 completes — no user action required.

1. Post-deploy profiling: language, framework, exposed ports, detected DB, detected auth mechanism (where inferable), env var **names** only (never values) for anything secret-like.
2. OpenAPI/Swagger discovery: `prance` (`ResolvingParser`) + `openapi-spec-validator`, probing common paths (`/openapi.json`, `/swagger.json`, `/api-docs`) via a safe internal HTTP call **from inside the tenant cluster**, not the range cluster.
3. Endpoint classification (public / likely-admin / likely-auth / upload / search), each with a confidence basis shown in the UI.
4. Explicitly log/label this activity as discovery, not an attack — it must never appear in attack-graph or test-run history (FR-3.4).
5. Frontend: a target-analysis panel on the app detail screen showing the discovered profile and endpoint list with classifications.

**Exit criteria:** after any successful deploy, the app detail page automatically populates with a language/framework/endpoint profile with zero manual steps.

---

## Phase 6 — Scenario System (PRD Modules 7–9)

Build the scenario schema and all three authoring paths (preset, AI, custom) against the same validation gate — this ordering matters because the safety allowlist (Phase 7) must exist before any scenario can run, but the schema needs to exist before the allowlist can validate against it.

1. **Shared Pydantic schema** — `{target, method, payload_category, concurrency, duration, expected_signals}`. This is the *only* representation a scenario can take; no arbitrary code path exists anywhere.
2. **Preset library** — one Pydantic definition file per category under `app/scenarios/`: brute force, credential guessing, SQLi resilience, XSS reflection, auth abuse, BOLA, API abuse, cache pressure, traffic flood, service/dependency/DB failure, network partition, resource exhaustion, multi-stage chains. Each includes a description, what it checks for, and estimated duration/impact for display before running.
3. **AI Scenario Builder** — LLM call (see Phase 12 for provider setup) constrained to emit the same schema via JSON-mode prompting; response is **re-validated** against the Pydantic model before it's ever shown as runnable — raw LLM output is never trusted directly.
4. **Custom Scenario Authoring** — structured form/editor (Monaco Editor in read/edit JSON mode is fine; explicitly not free-form code), same schema as AI-generated, same validation path.
5. Frontend: scenario library browser (cards per preset, showing name/description/impact estimate), AI Scenario Builder chat-style input (react-markdown + remark-gfm for the response), custom scenario form with Zod validation mirroring the backend Pydantic shape.

**Exit criteria:** a scenario built via any of the three paths produces an identical validated JSON object in the database, indistinguishable in the schema from any other source.

---

## Phase 7 — Safety Model / Simulation Guard (PRD §7.6 — build before Phase 8)

This must exist and be wired in *before* any scenario is allowed to execute — no exceptions, no bypass path, including for scenarios already built in Phase 6.

1. `app/safety/simulation_guard.py` — explicit allowlist of permitted scenario "kinds," checked in code, not just policy text.
2. Hard-coded, permanently disallowed with no config path to enable: real malware, persistence mechanisms, credential theft against real external accounts, reverse shells, botnet behavior, ransomware, privilege escalation against real systems, data exfiltration, internet-wide scanning, enumeration of public/external targets, unrestricted/real exploit chains.
3. Scope validation — any scenario/custom target resolving outside the customer's own tenant environment is rejected before execution.
4. Every rejection logged with reason and surfaced to the user, never a silent failure.
5. Wire this gate into the "start run" endpoint for **all** scenario sources (preset, AI, custom) — verify preset scenarios pass it too, so there's genuinely no special-cased path.

**Exit criteria:** attempting to start a run with a hand-crafted out-of-scope target or a disallowed scenario kind is rejected with a visible, specific reason, and the rejection is in the audit log.

---

## Phase 8 — Route Broker (PRD §7.5 — safety-critical, build before Phase 9)

The mechanism that makes cross-cluster attack execution safe. Must exist before any real attacker pod runs.

1. Route object = one rule: range-cluster attacker pod → tenant-namespace/target-service:port, nothing else. Implemented as K8s `Ingress` or Traefik `IngressRoute`.
2. **Dual-URL Architecture**:
   - `internal_url`: `http://route-{id}.{namespace}.svc.cluster.local:{port}` used exclusively by range attacker pods.
   - `public_url`: `http://<host>:8000/r/{route_id}` (or `/r/{route_id}`) host-accessible reverse proxy endpoint for UI/Human testing without exposing Kubernetes services directly.
3. **Controlled Destination-Locked Reverse Proxy**:
   - Reverse proxy mounted at `/r/{route_id}` strictly resolves destination from database (zero SSRF).
   - Validates route active state and server-side TTL expiration on every request (HTTP 410 on expired, 403 on revoked).
4. **Critical safety property**: the range cluster never holds tenant credentials — the *tenant cluster* exposes the route; the range cluster only ever has a URL it's permitted to hit (NFR-1.3). Verify this holds at the code level, not just by convention.
5. **TTL enforcement**: route carries an `expires-at` annotation; Celery beat periodic task sweeps every 30s and deletes anything expired, independent of whether the run finished cleanly (NFR-2.1).
6. **Multi-Tier Kill switch**:
   - Tier 1: Immediate in-memory/DB deny on proxy requests (0ms block).
   - Tier 2: Synchronous direct API call deleting the K8s object immediately (sub-5s SLA, NFR-3.1).
7. **Route status & UI**: Human `public_url` shown with Live Preview, internal `.cluster.local` attack URL available in Technical Details, live countdown timer (FR-5.4).
8. No route may ever grant L3/L4 access — application-layer (HTTP/HTTPS) to the declared target service/port only (FR-5.5).
9. Every route create/delete written to `audit_log` in the same transaction as the K8s API call; if the K8s call fails, the audit entry still records the attempt.

**Exit criteria:** a route can be opened with both `internal_url` and `public_url`, is human-testable via the reverse proxy, shows live countdown to expiry with server-side 410 enforcement, and a kill-switch click revokes proxy access instantly and deletes the Kubernetes Ingress in under 5 seconds. Confirm zero cross-tenant network path exists even under a simulated backend crash mid-run (NFR-1.1, NFR-2.1).

---

## Phase 9 — Simulation Engine / Test Run Execution (PRD Module 10)

Now that scenarios (Phase 6), the safety gate (Phase 7), and the route broker (Phase 8) all exist, wire them into an actual run.

1. **Attack orchestration by scenario type:**
   - HTTP-based (brute force, SQLi resilience, XSS reflection, API abuse): async httpx worker in the attacker pod.
   - Load/traffic (traffic flood, cache pressure): Locust used as a library (not its own web UI), invoked programmatically as `LocustRunner`.
   - Failure injection (service/dependency/DB failure, network partition, resource exhaustion): Chaos Mesh CRDs (`PodChaos`, `NetworkChaos`, `StressChaos`) applied **directly in the tenant namespace** — this bypasses the route broker deliberately, since it's the customer's own platform triggering a controlled fault on their own workloads, not a cross-cluster attack.
2. **Run lifecycle:** validate against Simulation Guard (Phase 7) → open route (Phase 8, HTTP/load scenarios only) → execute → stream progress → on completion or manual stop, revoke route + terminate attacker workload → generate findings → finalize attack graph.
3. **Real-time streaming:** attacker pod publishes to Redis pub/sub → FastAPI WebSocket endpoint subscribes and forwards to frontend. Pod never talks to the frontend directly. Sub-second latency target (NFR-3.3).
4. **Stop button:** immediately calls the Route Broker kill switch (Phase 8) and terminates the pod — same guarantee, under 5 seconds.
5. Findings generated per scenario result, feeding into Phase 11 (Defence Engine).
6. Frontend: live run view — steps attempted, success/blocked per step, resource metrics on the target, prominent Stop button, route status panel from Phase 8 always visible during a run.

**Exit criteria:** a preset scenario can be started against a Phase-4-deployed app, runs live with visible progress, can be stopped instantly, and produces at least one finding.

---

## Phase 10 — Attack Graph (PRD Module 9 in stack doc)

1. Data model: `attack_graph_nodes`, `attack_graph_edges` in Postgres, built **incrementally** as the attacker pod publishes step events — each WebSocket event both updates the live UI and writes a graph row, not computed after the fact.
2. Frontend: React Flow (`@xyflow/react` 12.x), separate `AttackNode`/`AttackEdge` types from the Lab Builder's node types (even though Lab Builder itself is deferred post-v1, keep the type namespaces distinct now to avoid a rename later).
3. Node color-coding by status: compromised/blocked/safe, using the severity/status palette from Phase 1.
4. Replay mode: user can step through a completed run's timeline after the fact, not just watch it live once.

**Exit criteria:** after a test run completes, its attack graph is viewable and replayable step-by-step with correct status coloring.

---

## Phase 11 — Observability & Defence Engine (PRD Modules 10–11)

1. **Observability**
   - `prometheus-fastapi-instrumentator` on the FastAPI backend for auto-instrumented request metrics; custom metrics (active test runs, open route count) added via `prometheus_client`.
   - Grafana dashboards, embedded via panel-embed iframes initially.
   - Promtail ships logs from both clusters into Loki, every line labeled `org_id`/`namespace` for tenant-scoped queries.
   - K8s Events API (pod restarts, readiness/liveness) via the `kubernetes` client's `watch` module in a dedicated long-running backend process (not a request handler), forwarded through the same Redis pub/sub → WebSocket path.
   - Metrics queryable **per test run**, not just globally (FR-8.2).
2. **Defence Engine**
   - `defence_recommendations` table: hand-authored, deterministic `finding_type` → mitigation template mapping. This is the source of truth, not LLM output.
   - Optional LLM layer prompted with the finding + the deterministic template, asked only to add contextual explanation — never to invent or alter the recommendation itself (FR-9.2).
   - Where mechanically applicable (e.g. a `NetworkPolicy`), the user can apply the mitigation directly through the same `kubernetes` client; code-level recommendations remain guidance-only — Pantheon never touches customer source code (FR-9.3).
3. Frontend: findings list (severity-ranked, badge-styled per Phase 1 tokens) with linked recommendation, "Apply" button shown only for infra-mechanically-applicable fixes, metrics/log panels scoped to the current test run.

**Exit criteria:** every finding from Phase 9 has a visible, concrete recommendation; at least one infra-level mitigation (e.g. NetworkPolicy) can be applied with one click and verified in the cluster.

---

## Phase 12 — AI Assistant Layer (cross-cutting — underpins Phases 5, 6, 11)

Build this as a shared service, not duplicated per feature. Can technically start any time after Phase 0, but real usage begins in Phase 6.

1. `app/services/ai_service.py` — provider-agnostic interface: `generate(prompt, schema) -> dict`.
2. Implementations: Google Gemini API (free tier, 15 RPM/1M tokens/day) for dev/default; Ollama (local sidecar container) for offline/self-hosted/data-residency cases. **Resolve the PRD's open question here** (Gemini vs. Ollama default) before wiring consumers.
3. Structured output enforcement: JSON-mode prompting, response always re-validated against the relevant Pydantic model — never trust raw LLM text as final output, anywhere it's used (Scenario Builder, Defence Engine explanation layer).
4. System prompt adapted from the PRD's own "Pantheon Assistant" persona, updated for the B2B ingestion/route-broker model rather than the original "everything in one lab" framing.

**Exit criteria:** swapping the provider (Gemini ↔ Ollama) via config requires no changes to any calling code in Phases 5/6/11.

---

## Phase 13 — Reporting (PRD Module 12)

1. Single source of truth: backend-composed Markdown from templates + run data, stored in Postgres/MinIO. PDF and other formats are always *derived*, never separately authored.
2. PDF generation: Markdown → HTML (via `markdown`/`mistune`) → styled HTML → WeasyPrint 62.x → PDF.
3. Charts embedded in PDFs: server-side via matplotlib (Agg backend, headless) — Recharts is browser-only and can't be reused server-side; keep the visual palette manually consistent with Phase 1's tokens.
4. CSV export via stdlib `csv` — no extra dependency.
5. Storage: MinIO, `reports/{org_id}/{report_id}.pdf`, signed expiring URLs for download.
6. Report scope: per test run or aggregated per app history; contents per FR-10.2 (executive summary, technical findings with severity, evidence, attack graph snapshot, metrics, before/after comparison when a prior run exists).
7. Org/app-scoped organization to support the consultancy persona keeping client work separated (FR-10.4).
8. Frontend: report generation trigger (per-run or org-level), report list/download screen, client-side jsPDF+html2canvas fallback only for quick exports — server-side WeasyPrint remains primary.

**Exit criteria:** a completed test run can be exported as both PDF and Markdown, with a before/after section populated when a prior run exists for the same app.

---

## Phase 14 — Dashboard & Polish (PRD Module 1)

Build last since it aggregates everything above.

1. Org-level dashboard: test run history, findings trends, improvement-over-time charts (Recharts line/area for time-series, bar for findings-by-severity).
2. Preset demo app catalog surfaced as the "explore while your tenant provisions" path from PRD §6.1 — reuses Phase 4's ingestion pipeline against known-vulnerable demo apps instead of a customer repo.
3. Notifications (`notifications` table) for build completion, run completion, invitations.
4. Audit log viewer (Admin-only, per FR-11.2) — append-only, filterable by action type/user/date.
5. Full pass on NFR-4.1/4.2: confirm a non-K8s-expert can complete deploy → test → report unassisted, and every error surfaced anywhere in the app is specific and human-readable, never a bare code or trace.

**Exit criteria:** the full v1 user journey (§6.1–§6.5 of the PRD) is walkable end to end by a new user with no prior context, matching the §9 success metrics.

---

## Sequencing Summary

```
Phase 0  Environment & scaffolding
Phase 1  Design system foundation
Phase 2  Auth, orgs, teams
Phase 3  Infra & provisioning
Phase 4  Ingestion pipeline
Phase 5  AI target analysis & endpoint discovery
Phase 6  Scenario system (preset / AI / custom)
Phase 7  Safety model — MUST precede Phase 9
Phase 8  Route broker — MUST precede Phase 9
Phase 9  Test run execution
Phase 10 Attack graph
Phase 11 Observability & defence engine
Phase 12 AI assistant layer (cross-cutting, feeds 5/6/11)
Phase 13 Reporting
Phase 14 Dashboard & polish
```

**Non-negotiable ordering constraint:** Phases 7 (Safety Model) and 8 (Route Broker) must both be complete and tested — including the audit-log and kill-switch guarantees — before Phase 9 ever executes a real attacker pod against a tenant environment. This is the one dependency in the plan that isn't just "convenient," it's the actual safety boundary the whole product's non-negotiable success metric (§9: zero cross-tenant access incidents) rests on.

## Deferred / Out of Scope for v1 (do not build in this pass)

- Lab Builder visual topology canvas.
- Classroom/instructor-student features.
- Multi-cloud provisioning backends (AWS/GCP/Azure) — only keep the Terraform module interface abstract enough to add later.
- Auto-remediation (Pantheon opening a PR with a code fix).
- White-label/branded reporting.

## Open Decisions to Resolve Before/During the Relevant Phase

- **Phase 2/4:** private repo auth mechanism (deploy key vs. OAuth app vs. PAT).
- **Phase 4:** UX for compose services that only need pulling vs. building.
- **Phase 12:** Gemini vs. Ollama as the *default* provider (affects offline/self-hosted claims).
- **Business, not engineering:** pricing/plan gating, data retention windows — needed before billing work, not before v1 engineering starts.

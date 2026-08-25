# Product Requirements Document: Pantheon

**A B2B Security Testing Platform — Deploy Your App, Attack It Safely, Fix What's Found**

Version 1.0 · Status: Draft · Owner: [you]

---

## 1. Problem Statement

Development teams and security teams need to test how their applications behave under attack — SQL injection, auth abuse, traffic floods, dependency failures — before shipping to production. Today this requires either:

- Standing up their own isolated infrastructure and attack tooling (slow, requires security expertise most dev teams don't have in-house), or
- Hiring external pentesters (expensive, slow turnaround, one-off engagements rather than continuous testing), or
- Testing in production or shared staging environments (risky, no real isolation, findings are hard to reproduce)

Pantheon removes the infrastructure and expertise barrier: a customer connects a Git repo or Docker Compose file, Pantheon deploys it into an isolated environment automatically, runs a library of safe preset attacks (or AI-generated / custom ones) against it, and returns findings with concrete defensive recommendations — repeatable on every iteration, without the customer ever touching Kubernetes.

---

## 2. Goals & Non-Goals

### Goals
- Let a customer go from "I have an app" to "here's what's vulnerable and how to fix it" with minimal manual setup.
- Guarantee that testing a customer's app can never affect any other customer's environment or any system outside Pantheon.
- Give the customer full control over when and how attacks run against their environment, including the ability to stop instantly.
- Make findings actionable, not just descriptive — every finding ships with a concrete recommended fix.
- Support iterative use: deploy, test, fix, redeploy, retest — not a one-shot engagement.

### Non-Goals (v1)
- Pantheon is **not** a general-purpose penetration testing tool against real, live, external systems. It only ever attacks applications the customer has explicitly deployed into their own Pantheon-managed environment.
- Pantheon does **not** execute real malware, ransomware, persistence mechanisms, credential theft against real accounts, reverse shells, or exploit chains intended for use outside the platform. All simulations are non-destructive and schema-constrained (see §7.6).
- Classroom/instructor-student features (present in the original internal-tool concept) are **out of scope for v1** — this is a company-to-company product, not an education platform. May be revisited as a separate offering later.
- Multi-cloud provisioning (AWS/GCP/Azure) is out of scope for v1 — self-hosted only, with the provisioning layer built to make cloud support an additive change later, not a rewrite.
- Source code modification / auto-remediation is out of scope — Pantheon recommends fixes, it does not push commits or alter the customer's code.

---

## 3. Target Users & Personas

| Persona | Who they are | What they want from Pantheon |
|---|---|---|
| **Dev team lead** | Owns a small-to-mid app, ships regularly, no dedicated security engineer on the team | Fast, automatic testing on every significant release; plain-language findings they can act on without a security background |
| **Security engineer / AppSec** | Works inside a company with several internal apps, evaluates risk before release | Deeper control — custom scenarios, full attack graphs, exportable reports for compliance/audit trail |
| **Independent pentester / security consultancy** | Tests client applications as a service | Needs to onboard multiple client apps under one account, keep findings organized per client, export white-labelable reports |

All three share one account model (org-based), differentiated by role (see §7.1) rather than separate products.

---

## 4. User Stories

**Onboarding & deployment**
- As a dev team lead, I can sign up, create an org, and invite my teammates, so we share one workspace for all our apps.
- As a user, I can give Pantheon a Git repo URL and have my app running in an isolated environment within minutes, without writing any Kubernetes YAML.
- As a user, I can instead upload/point to a `docker-compose.yml`, and Pantheon deploys each service correctly, respecting service dependencies.
- As a user, if my app has no Dockerfile, I still want it built and deployed automatically based on detecting my language/framework.
- As a user, I want my built images to be as small as reasonably possible, so builds and deploys are fast.

**Testing**
- As a user, I can browse a library of preset attack scenarios (SQLi resilience, auth abuse, traffic flood, etc.) and pick which to run against my deployed app.
- As a user, I can describe what I want tested in plain language and have Pantheon generate an appropriate attack scenario.
- As a security engineer, I can author a fully custom scenario (target endpoint, method, payload category, concurrency) when presets don't cover my case.
- As a user, I can watch a test run happen in real time — what's being tried, what succeeded, what got blocked.
- As a user, I can stop a running test immediately if something looks wrong, and know my app is safe the instant I do.

**Results & remediation**
- As a user, I can see a visual attack graph showing how an attack moved through my app's services.
- As a user, I can see live resource metrics (CPU, memory, network, latency) during a test run, so I understand impact, not just outcome.
- As a user, for every finding, I get a concrete recommended fix, not just "this is vulnerable."
- As a user, I can generate a report (PDF and Markdown) summarizing a test run for my team or my client.
- As a security consultancy, I can export a report that's clearly organized per client app, suitable to hand to that client.

**Ongoing use**
- As a user, I can redeploy an updated version of my app and rerun the same tests to confirm a fix worked.
- As a user, I can see my org's history of test runs, findings trends, and improvement over time on a dashboard.
- As an org admin, I can manage who on my team has access to which apps and what they're allowed to do (view-only vs. can-run-tests vs. admin).

---

## 5. Scope Summary (Module List)

Carried over from the original module concept, reframed for B2B. "Status" reflects intended v1 scope.

| # | Module | v1 Scope |
|---|---|---|
| 1 | Dashboard | Full |
| 2 | App Onboarding (was "Cyber Range") | Full — replaces template-based lab creation with customer-app ingestion as primary path; preset demo apps retained as secondary/learning path |
| 3 | Infrastructure View (was "Infrastructure Manager") | Full, read-mostly (no raw kubectl access exposed) |
| 4 | Ingestion Pipeline (was "Application Import") | Full — this is the core new capability |
| 5 | AI Target Analysis | Full |
| 6 | Endpoint Discovery | Full |
| 7 | Simulation Library | Full |
| 8 | AI Scenario Builder | Full |
| 9 | Custom Scenario Authoring | Full (new — not explicit in original doc, needed for AppSec persona) |
| 10 | Simulation Engine / Test Run Execution | Full |
| 11 | Route Broker & Kill Switch | Full (new — safety-critical, no equivalent in original doc) |
| 12 | Attack Graph | Full |
| 13 | Observability | Full |
| 14 | Defence Engine | Full |
| 15 | Reporting | Full |
| 16 | Org & Team Management | Full (new — required for B2B multi-user accounts) |
| 17 | Classroom Management | **Out of scope v1** |
| 18 | Lab Builder (visual topology canvas) | **Deferred** — useful for customers building a *new* app to test, but not required for core "bring your existing app" flow; revisit post-v1 |

---

## 6. User Flows

### 6.1 First-time onboarding
1. User signs up → creates an org (or is invited into an existing one).
2. Org's tenant cluster begins provisioning in the background (async — user isn't blocked waiting on this).
3. User is prompted to either (a) connect their first app, or (b) explore a preset demo app to learn the platform while their tenant environment finishes provisioning.

### 6.2 Deploying an app
1. User provides a Git repo URL, or uploads/points to a `docker-compose.yml`.
2. Pantheon detects: Dockerfile present? Compose file? Multiple services?
3. Ingestion pipeline builds (Buildpacks if no Dockerfile, native Docker build if present), respecting `.dockerignore`.
4. Build progress streams live to the UI (log tail, current stage).
5. On success: image(s) pushed to the org's private registry namespace, K8s manifests generated, deployed into the org's tenant cluster namespace.
6. On failure: clear, specific error (not a stack trace) — e.g. "no Dockerfile found and language could not be auto-detected" — with a way to see full build logs.
7. Once running, Pantheon performs safe internal discovery (endpoint discovery, target analysis) automatically — no user action required.

### 6.3 Running a test
1. User selects a deployed app and either: picks a preset scenario, describes what they want in natural language (AI Scenario Builder), or authors a custom scenario.
2. System validates the scenario against the safety allowlist (§7.6) — this happens regardless of scenario source.
3. User confirms and starts the run.
4. Route Broker opens a scoped, time-boxed route from the range cluster to the specific target service.
5. Attacker/scanner pods execute in the range cluster; live progress streams to the UI (steps attempted, results, resource metrics on the target).
6. User may hit "Stop" at any time → Route Broker revokes the route immediately, attack pod is terminated.
7. On natural completion or stop: route auto-expires/is revoked, findings are generated, attack graph is finalized.

### 6.4 Reviewing results
1. User views the attack graph (step-by-step, replayable) and the findings list (severity-ranked).
2. Each finding links to a Defence Engine recommendation with a concrete fix.
3. User generates a report (PDF or Markdown) scoped to this run, or an org-level report across multiple runs.

### 6.5 Iterating
1. User fixes the issue in their own codebase, pushes a new version.
2. User redeploys (same ingestion flow, new version) — previous version's history is retained, not overwritten.
3. User reruns the same scenario(s) to confirm the fix; report can show before/after comparison.

---

## 7. Functional Requirements

### 7.1 Org & Team Management
- FR-1.1: Users belong to one or more orgs; all app/test-run data is scoped to an org.
- FR-1.2: Org roles: **Admin** (full control, billing, team management), **Tester** (can deploy apps, run tests, view everything), **Viewer** (read-only access to apps/results/reports).
- FR-1.3: Org admins can invite users by email; invited users choose a password on first login.
- FR-1.4: All actions are attributed to the acting user and org in the audit log (§7.11).

### 7.2 App Onboarding & Ingestion
- FR-2.1: User can provide a Git repository URL (public or, for private repos, via a deploy key/token the user supplies).
- FR-2.2: User can provide a `docker-compose.yml` (upload or paste).
- FR-2.3: If a Dockerfile is present (root or specified path), it is used as-is for the build.
- FR-2.4: If no Dockerfile is present, the system attempts automatic build via language/framework detection (Buildpacks).
- FR-2.5: If a `.dockerignore` is present, it is respected on every build path to minimize image size and avoid shipping unnecessary files (build artifacts, `.git`, `node_modules`, secrets files) into the image.
- FR-2.6: For Compose input, every `services:` entry is deployed as its own workload, with `depends_on` relationships preserved as startup ordering.
- FR-2.7: Environment variables that appear to be secrets (name-pattern matched, e.g. `*_KEY`, `*_SECRET`, `*_PASSWORD`, `*_TOKEN`) or that are sourced from a `.env` file are stored as platform-managed secrets, never as plaintext in any generated manifest visible to the UI.
- FR-2.8: Build progress (queued → building → pushing → deploying → running) is visible in real time, with a way to view full build logs.
- FR-2.9: Build/deploy failures produce a specific, actionable error message, not a raw stack trace, with an option to view underlying logs for debugging.
- FR-2.10: A previously deployed app can be redeployed with a new version; version history is retained (at minimum: what was deployed, when, and its build log).

### 7.3 AI Target Analysis & Endpoint Discovery
- FR-3.1: After successful deployment, the system automatically profiles the app: language, framework, exposed ports, detected database, detected auth mechanism (where inferable), environment variable names (not values, for secrets).
- FR-3.2: If an OpenAPI/Swagger spec is discoverable (common paths or declared in the repo), it is parsed and all endpoints, methods, and parameters are extracted.
- FR-3.3: Endpoints are classified where possible: public, likely-admin, likely-auth, upload, search — surfaced in the UI with the classification and its confidence basis.
- FR-3.4: Discovery actions against the customer's own newly-deployed app happen from within their own tenant environment, not from the range cluster, and are not logged/reported as "attacks."

### 7.4 Simulation Library & Scenario Authoring
- FR-4.1: A library of preset scenarios is available, covering at minimum: brute force, credential guessing, SQL injection resilience, XSS reflection, authentication abuse, broken access control (BOLA), API abuse, cache pressure, traffic flood, service/dependency/database failure, network partition, resource exhaustion, multi-stage chains.
- FR-4.2: Each preset scenario displays: what it does, what it's checking for, expected non-destructive behavior, and estimated duration/impact before the user runs it.
- FR-4.3: Users can describe a test in natural language; the AI Scenario Builder generates a structured scenario definition (target, method, endpoints, payload category, concurrency, duration) for user review before execution.
- FR-4.4: Users can author a fully custom scenario via a structured form/editor (not free-form code) — same schema as AI-generated scenarios.
- FR-4.5: Every scenario, regardless of source (preset, AI-generated, custom), is validated against the safety allowlist (§7.6) before it is permitted to run. There is no bypass path.

### 7.5 Test Run Execution & Route Broker
- FR-5.1: Starting a test run opens a route from the range cluster to exactly one target service in the customer's tenant environment, scoped to that run only.
- FR-5.2: The route is time-boxed (TTL) and automatically revoked on expiry regardless of run state.
- FR-5.3: The user can manually stop a run at any time; this immediately revokes the route and terminates the attacker workload. "Immediately" is defined as within a bounded time window (target: under 5 seconds from click to route revocation — see §9).
- FR-5.4: While a route is open, its status (open, target, opened-at, expires-at) is visible to the user in the UI at all times.
- FR-5.5: No route may grant network-level (L3/L4) access between clusters — only application-layer (HTTP/HTTPS) access to the specific declared target service and port.
- FR-5.6: Test run progress streams in real time: current step, request/response summary, resource impact on the target (CPU/memory/latency), success/blocked status per step.

### 7.6 Safety Model (Simulation Guard)
- FR-6.1: A fixed allowlist of permitted scenario "kinds" is enforced in code before any run — including AI-generated and custom scenarios.
- FR-6.2: The following are explicitly and permanently disallowed, with no configuration path to enable them: real malware, persistence mechanisms, credential theft against real external accounts, reverse shells, botnet behavior, ransomware, privilege escalation against real systems, data exfiltration, internet-wide scanning, enumeration of public/external targets, unrestricted/real exploit chains.
- FR-6.3: Any scenario or custom target that resolves outside the customer's own tenant environment is rejected before execution (scope validation).
- FR-6.4: All safety-guard rejections are logged with the reason, visible to the user (not a silent failure).

### 7.7 Attack Graph
- FR-7.1: A visual, step-by-step graph shows entry point, visited services, dependencies, which steps succeeded vs. were blocked, and where risk propagated.
- FR-7.2: The graph is replayable — user can step through the run's timeline after the fact, not just watch it live once.
- FR-7.3: Nodes are color-coded by status (compromised/blocked/safe) for at-a-glance risk reading.

### 7.8 Observability
- FR-8.1: During and after a test run, the user can view: application logs, container logs, pod events (restarts, readiness/liveness changes), CPU/memory/network usage, HTTP status code distribution, latency.
- FR-8.2: Metrics are queryable per test run (not just as a global dashboard), so impact can be attributed to a specific attack.

### 7.9 Defence Engine
- FR-9.1: Every finding maps to at least one concrete, explained mitigation recommendation (e.g. input validation, parameterized queries, rate limiting, NetworkPolicy tightening, RBAC adjustment).
- FR-9.2: Recommendations are deterministic (rule-based) for the core mapping; an optional LLM-generated explanation may add context but never replaces or alters the underlying recommendation.
- FR-9.3: Where a mitigation is mechanically applicable at the infrastructure level (e.g. a NetworkPolicy), the user may apply it directly through Pantheon; code-level recommendations are guidance only — Pantheon never modifies the customer's source code.

### 7.10 Reporting
- FR-10.1: Reports can be generated per test run or aggregated across an app's history.
- FR-10.2: Report contents: executive summary, technical findings with severity, evidence (logs/requests), attack graph snapshot, metrics, and before/after comparison when a prior run exists for the same app.
- FR-10.3: Export formats: PDF and Markdown at minimum; CSV export for raw findings data.
- FR-10.4: Reports are scoped per org and, within an org, filterable/organizable per app — supporting the consultancy persona's need to keep client work separated.

### 7.11 Audit & Access
- FR-11.1: Every provisioning action, route open/close event, test run start/stop, and finding-mitigation application is logged with user, org, and timestamp.
- FR-11.2: Audit log is append-only and viewable (at minimum by org Admins) within the product — not just in backend logs.

---

## 8. Non-Functional Requirements

### 8.1 Isolation & Security
- NFR-1.1: One org's tenant environment must have no network path to another org's tenant environment under any circumstance, including platform failure modes.
- NFR-1.2: Tenant environments default to fully closed network posture (default-deny) before any customer workload is deployed.
- NFR-1.3: The range cluster (shared across orgs, running attacker workloads) must never hold standing credentials or network reachability into any tenant cluster — access exists only as time-boxed, single-service routes created per test run.
- NFR-1.4: Secrets (customer app secrets, platform credentials) are never stored in plaintext at rest or displayed in the UI once entered.

### 8.2 Reliability
- NFR-2.1: A route created for a test run is guaranteed to be revoked — either by the TTL sweep or the kill switch — even if the backend process that created it crashes mid-run.
- NFR-2.2: Ingestion pipeline failures must not leave orphaned resources (partial deployments, dangling images) — failed builds clean up after themselves.

### 8.3 Performance
- NFR-3.1: Kill switch: route revocation completes within 5 seconds of user action, measured end to end (click → route deleted in cluster).
- NFR-3.2: Simple app deployment (single service, Dockerfile present, small image) completes in under 3 minutes from submission to running.
- NFR-3.3: Real-time test run progress (WebSocket) has sub-second latency from event occurring to UI update, under normal load.

### 8.4 Usability
- NFR-4.1: A user with no Kubernetes knowledge can deploy an app and run a preset scenario without needing to read documentation beyond in-app guidance.
- NFR-4.2: Every safety-guard rejection and build/deploy failure surfaces a specific, human-readable reason — never a bare error code or stack trace as the primary message.

### 8.5 Portability
- NFR-5.1: The provisioning layer is abstracted such that adding a new infrastructure backend (e.g. a cloud provider) requires changes only within the provisioning module, not the application/business logic layer.

---

## 9. Success Metrics

| Metric | v1 Target |
|---|---|
| Time from repo/compose submission to running app | < 3 minutes (simple single-service app) |
| Kill switch response time | < 5 seconds |
| False sense of safety incidents (cross-tenant access ever observed in testing) | Zero, non-negotiable |
| % of findings with an actionable recommendation | 100% |
| User can complete first deploy → test → report flow unassisted | Target: yes, in usability testing with a non-K8s-expert |

---

## 10. Data Model (Reference — Key Entities)

```
orgs, org_members (role-scoped), invitations
tenant_clusters (per org, provisioning status)
apps, app_versions, app_deployments
ingestion_jobs, build_logs
scenarios (preset library), custom_scenarios, ai_generated_scenarios
test_runs, test_run_routes (route broker records)
scenario_steps, scenario_results, findings
attack_graph_nodes, attack_graph_edges
defence_recommendations, applied_defences
reports, report_sections
notifications, audit_log
```

(Full backend/service architecture and exact tech stack are maintained separately — see companion documents: architecture plan and exact tech stack.)

---

## 11. Open Questions

> [!IMPORTANT]
> **Private repo auth**: exact mechanism for customer-supplied Git credentials (deploy key vs. OAuth app vs. PAT) — affects onboarding friction and security posture of stored credentials.

> [!IMPORTANT]
> **Pricing/plan gating**: not addressed in this PRD — number of apps, test runs, or concurrent tenant cluster resources per plan tier needs definition before billing work starts.

> [!IMPORTANT]
> **Data retention**: how long build logs, test run history, and reports are retained by default, and whether this is configurable per org.

> [!IMPORTANT]
> **Compose edge cases**: behavior when a compose file references external images from Docker Hub vs. requiring a build — both should be supported, but the UX for "this service doesn't need building, just pulling" needs a decision.

> [!IMPORTANT]
> **AI provider default**: Gemini (free tier, external) vs. Ollama (local, no external dependency) as the default — affects both cost and whether the platform can run fully offline/self-hosted with zero external calls.

---

## 12. Explicitly Deferred (Post-v1 Candidates)

- Lab Builder visual topology canvas (for building a *new* app to test, not importing an existing one)
- Classroom/instructor-student features, as a potentially separate education-focused offering
- Multi-cloud provisioning backends
- Auto-remediation (Pantheon opening a PR with a suggested code fix)
- White-label/branded reporting for the consultancy persona (mentioned in user stories, not committed to v1 scope)


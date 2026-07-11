# FORLAS CRQ — Beta Design Document

**Version:** 0.2.0
**Date:** 2026-07-11
**Author:** Michael Walker
**Status:** As-built, post Phase 9.

---

## 0 · Executive summary

FORLAS CRQ Beta productionises the Alpha HTML prototype (`E:\CRQ\FORLAS_FAIR_CRQ.html`,
3,136 lines, single file, localStorage) into a maintainable, local-first
multi-user analytical platform.

**Design tenets** — local-first, offline-first, no cloud, no SaaS, no telemetry,
no external services, no API dependencies. SMB hardware target.

**Stack** — Python 3.13+/FastAPI/SQLModel/Alembic/NumPy/SciPy backend; React 18/
TypeScript/Vite/Tailwind/ShadCN/Zustand/TanStack Query+Table/ECharts/Motion
frontend; SQLite (WAL) persistence; Tauri 2 (primary) + Docker (secondary)
delivery.

**Surface delivered** — 8 application screens, 53 backend tests, 12 ORM
tables, ~30 API endpoints, 4 plugin extension points, two deliverables (HTML
+ DOCX) for reports, full RBAC (Owner / Approver / Reviewer / ReadOnly),
audit log on every mutation.

---

## 1 · System architecture

```
                   ┌─────────────────────────────────────────────┐
                   │           Tauri 2 host (Rust)               │
                   │   ┌─────────────┐    ┌──────────────────┐   │
                   │   │  WebView    │◄──►│ Python sidecar   │   │
                   │   │  React SPA  │    │ (PyInstaller)    │   │
                   │   └─────────────┘    │ uvicorn + FastAPI│   │
                   │                      │ Engine · DB · IO │   │
                   │                      └──────────────────┘   │
                   └──────────────┬──────────────────────────────┘
                                  │ SQLite (WAL)
                                  ▼
                       <app data dir>/forlas_crq.db
                       <app data dir>/backups/*.db
                       <app data dir>/reports/

                   Alternative delivery: single Docker container
                   serving the SPA at /app and the API at /api on :8765.
```

**Key choices** —
1. **One process per install.** No microservices. The FastAPI app, the engine,
   the reporting renderer, and the static SPA bundle all live in one Python
   process. Tauri merely wraps it.
2. **SQLite (WAL) for everything.** No Postgres, no Redis. Concurrent reads
   during long simulations don't block writers; `synchronous=NORMAL` for
   low-latency writes; `busy_timeout=5000ms` for the rare contention case.
3. **Local accounts.** Argon2id password hashing, signed session cookies via
   `itsdangerous`. No JWTs, no OAuth, no remote IdP. The first account is
   created interactively on first run (a "Create your account" screen), or
   auto-created when an owner password is preset for server deployments.
4. **Plugin host via entry points.** Distributions, exporters, knowledge
   catalogues are pluggable through `importlib.metadata.entry_points`. The
   built-in distribution and knowledge sets are themselves the reference
   implementation of the contract.
5. **HTML print-to-PDF, not headless Chrome.** Same workflow as the Alpha;
   zero install-time dependencies.

---

## 2 · Folder structure

```
E:\FORLAS-CRQ-Beta\
├── README.md
├── LICENCE.md                # ULA v1.0
├── Dockerfile                # multi-stage: Node→Python
├── docker-compose.yml
├── .gitignore
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/              # migrations
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI app factory + lifespan
│   │   ├── config.py         # Pydantic settings
│   │   ├── db.py             # engine, session
│   │   ├── deps.py           # FastAPI dependencies + RBAC guards
│   │   ├── security.py       # Argon2 + signed cookies
│   │   ├── api/              # routers, one module per surface
│   │   ├── models/           # SQLModel ORM classes
│   │   ├── schemas/          # Pydantic DTOs (separate from ORM)
│   │   ├── engine/           # Monte Carlo + portfolio aggregation
│   │   ├── services/         # business logic (called from routers)
│   │   ├── reporting/        # Jinja2 templates + DOCX renderer
│   │   ├── jobs/             # in-process job runner placeholder
│   │   ├── knowledge/        # bundled threat/control/benchmark seed
│   │   └── plugins/          # entry-point host + registry
│   ├── scripts/              # PyInstaller entry point
│   └── tests/
│       ├── conftest.py       # isolated per-test temp data dir
│       └── test_*.py         # 53 tests
├── frontend/
│   ├── package.json
│   ├── vite.config.ts        # base path is env-driven
│   ├── tailwind.config.ts    # design tokens
│   └── src/
│       ├── main.tsx
│       ├── App.tsx           # session gate + ULA gate + router
│       ├── routes/router.tsx
│       ├── pages/            # one per screen
│       ├── components/
│       │   ├── common/       # AppShell, Sidebar, TopBar, LoginPanel, UlaGate
│       │   ├── dashboard/    # PortfolioLecChart, TopScenariosTable, …
│       │   ├── workspace/    # ModeSelector, DistributionParamCard, …
│       │   ├── reports/      # PresentationMode
│       │   └── ui/           # ShadCN-style primitives
│       ├── hooks/
│       ├── store/auth.ts     # Zustand
│       ├── lib/              # api, queries, format, cn, echarts
│       ├── styles/globals.css
│       └── types/api.ts
├── src-tauri/                # Tauri 2 wrapper (Rust)
│   ├── Cargo.toml
│   ├── build.rs
│   ├── tauri.conf.json
│   ├── src/main.rs           # spawns Python sidecar
│   └── binaries/             # PyInstaller-built sidecar lives here
├── scripts/
│   └── build_backend_sidecar.py
└── docs/
    ├── PACKAGING.md          # Docker + Tauri build recipes
    └── DESIGN.md             # this file
```

---

## 3 · Database schema

Twelve tables, all SQLite-friendly. JSON columns store the dynamic blobs
(distribution params, snapshots, audit before/after diffs) — SQLite stores them
as TEXT, queryable via JSON1.

| Table                  | Purpose                                                            |
|------------------------|--------------------------------------------------------------------|
| `users`                | Local accounts, Argon2 hashes, role, last login                    |
| `user_sessions`        | Server-side session records for revocation                         |
| `scenarios`            | Editable scenario state — inputs (JSON), tolerance, mode, metadata |
| `scenario_versions`    | Immutable per-save snapshots                                       |
| `simulation_runs`      | One row per Monte Carlo run with denormalised headline stats       |
| `simulation_artifacts` | 1:1 with `simulation_runs`; raw vectors (losses, LEC, histogram)   |
| `portfolios`           | Named portfolios with scenario_id lists, appetite, insurance       |
| `portfolio_snapshots`  | History points (ALE/P95/P99) for trend charts                      |
| `audit_log`            | Append-only every mutation; actor + entity + before/after diff     |
| `approval_requests`    | State-machine transition records                                   |
| `review_schedules`     | Cadence + next-due-date per scenario                               |
| `knowledge_threats`    | Threat library (FAIR + MITRE + custom)                             |
| `knowledge_controls`   | NIST CSF / CIS / ISO catalogues                                    |
| `knowledge_benchmarks` | Distribution reference ranges by industry × metric                 |
| `app_settings`         | Singleton row — defaults, ULA acknowledgement, theme               |

**Indexing strategy** — every `public_id` is unique-indexed; every foreign key
is indexed; `created_at`/`updated_at` are indexed on tables we time-query
(`scenarios`, `audit_log`, `simulation_runs`); `entity_type+entity_id`
composite isn't a B-tree index (SQLite limitation) but is queried with
indexed predicates.

**Public IDs** — every externally-referenced row carries a short `public_id`
(`sc_…`, `sim_…`, `pf_…`, `ap_…`) instead of exposing the int PK. Keeps export
round-trips stable.

**Migrations** — Alembic. Until a baseline revision is checked in, `_run_
migrations()` falls back to `SQLModel.metadata.create_all` + stamp head, so
dev installs always boot. The first stable baseline should be cut once the
schema settles.

---

## 4 · API specification

All routes prefixed `/api`. JSON in, JSON out (except HTML/DOCX report
downloads). Session-cookie authentication; role gates enforced at the
FastAPI dependency layer (`require_role(minimum)`).

### Auth (`/api/auth`)
| Method | Path                    | Role     | Notes                          |
|--------|-------------------------|----------|--------------------------------|
| GET    | `/session`              | (open)   | Current session status         |
| POST   | `/login`                | (open)   | Set session cookie             |
| POST   | `/logout`               | user     | Clear cookie                   |
| GET    | `/users`                | owner    | List local accounts            |
| POST   | `/users`                | owner    | Create user                    |
| PATCH  | `/users/{id}`           | owner    | Update / change password       |
| DELETE | `/users/{id}`           | owner    | Deactivate                     |

### System (`/api`)
| Method | Path                    | Role     | Notes                          |
|--------|-------------------------|----------|--------------------------------|
| GET    | `/health`               | (open)   | DB + version check             |
| GET    | `/settings`             | user     |                                |
| PATCH  | `/settings`             | user     | Default seed/iterations/theme  |
| POST   | `/ula/acknowledge`      | user     | Record ULA acceptance          |
| POST   | `/import/alpha`         | owner    | Import Alpha localStorage JSON |
| POST   | `/backup`               | owner    | SQLite online-backup           |
| GET    | `/backups`              | user     | List backup files              |

### Scenarios (`/api/scenarios`)
| Method | Path                       | Role     |
|--------|----------------------------|----------|
| GET    | ``                         | user     |
| POST   | ``                         | reviewer |
| GET    | `/{id}`                    | user     |
| PATCH  | `/{id}` (snapshot_note?)   | reviewer |
| DELETE | `/{id}` (soft)             | reviewer |
| POST   | `/{id}/clone`              | reviewer |

### Simulations
| Method | Path                                              | Role     |
|--------|---------------------------------------------------|----------|
| POST   | `/api/scenarios/{id}/simulations`                 | reviewer |
| GET    | `/api/scenarios/{id}/simulations/latest`          | user     |
| GET    | `/api/simulations/{run_id}/losses`                | user     |
| GET    | `/api/simulations/{run_id}/drivers`               | user     |

### Portfolio (`/api/portfolio`)
| Method | Path                                  | Role     |
|--------|---------------------------------------|----------|
| GET    | `/rollup?appetite=&insurance_*`       | user     |
| GET    | `/register`                           | user     |
| GET    | `/snapshots`                          | user     |
| POST   | `/snapshots`                          | reviewer |

### Reports (`/api/reports`)
| Method | Path        | Role  | Notes                                    |
|--------|-------------|-------|------------------------------------------|
| POST   | `/html`     | user  | Returns HTML for new-window print-to-PDF |
| POST   | `/docx`     | user  | Returns binary `.docx`                   |

### Knowledge (`/api/knowledge`)
| Method | Path                  | Role  |
|--------|-----------------------|-------|
| GET    | `/threats?q&category` | user  |
| GET    | `/controls?q&framework` | user |
| GET    | `/benchmarks?q&industry&metric` | user |
| POST   | `/import?kind&source` | owner |

### Governance (`/api/governance`)
| Method | Path                                                       | Role     |
|--------|------------------------------------------------------------|----------|
| GET    | `/audit?entity_type&entity_id`                             | user     |
| GET    | `/approvals`                                               | user     |
| POST   | `/scenarios/{id}/transition`                               | varies   |
| PUT    | `/scenarios/{id}/schedule`                                 | user     |
| POST   | `/scenarios/{id}/schedule/mark-reviewed`                   | user     |
| GET    | `/schedules` / `/schedules/overdue`                        | user     |
| GET    | `/scenarios/{id}/versions`                                 | user     |

### Plugins (`/api/plugins`)
| Method | Path | Role |
|--------|------|------|
| GET    | ``   | user |

FastAPI's `/docs` route exposes the full OpenAPI schema at runtime.

---

## 5 · UI component inventory

**Pages** (one per route, `frontend/src/pages/`):
`DashboardPage`, `WorkspacePage`, `SimDataPage`, `RegisterPage`, `ReportsPage`,
`KnowledgePage`, `GovernancePage`, `SettingsPage`, `PlaceholderPage`.

**Shell** (`components/common/`): `AppShell`, `Sidebar`, `TopBar`,
`LoginPanel`, `UlaGate`.

**Dashboard widgets**: `PortfolioLecChart`, `PortfolioTrendChart`,
`TopScenariosTable`.

**Workspace** (the largest surface): `ScenarioList`, `NewScenarioDialog`,
`ModeSelector`, `DistributionParamCard`, `MetadataPanel`, `RunControls`,
`SimulationResults`, plus three chart leaves under `workspace/charts/`:
`HistogramChart`, `LecChart`, `SensitivityTornado`.

**Reports**: `PresentationMode` (full-screen slide deck).

**UI primitives** (`components/ui/`, ShadCN-style, locally owned, no NPM lock-in
beyond Radix headless): `Button`, `Card` (`CardHeader`/`CardTitle`/`CardHint`/
`CardBody`), `Input`, `Label`, `Select`, `Textarea`, `Badge`, `Slider`,
`Dialog`, `Tabs`.

**State** — Zustand for the session/ULA gate only. Everything else lives in
TanStack Query cache keyed by `["scenarios"]`, `["scenarios", id]`,
`["portfolio", "rollup"]`, etc. Mutations invalidate the relevant prefixes.

**Animation** — Motion (`framer-motion` v11), used sparingly: simulation
results fade in on render, login panel slides up. 150ms standard.

**Charts** — ECharts via `echarts-for-react/lib/core` so we tree-shake to
just the components we use (`BarChart`, `LineChart`, `GridComponent`,
`TooltipComponent`, `LegendComponent`, `MarkLineComponent`). Theme registered
once at module load, palette mirrors the Tailwind tokens.

---

## 6 · Domain model

```
User                     (owner | approver | reviewer | readonly)
   └── owns ── Scenario
                 ├── mode (lef | tef-vuln | full)
                 ├── inputs (DistributionParam × N, mode-dependent)
                 ├── tolerance, reduction_pct
                 ├── reference_lines, prefs
                 ├── approval_state (draft → in_review → approved → archived)
                 └── ScenarioVersion[]  (immutable snapshots)
                       └── snapshot (JSON blob of scenario at save time)

Scenario ── triggers ── SimulationRun
                          ├── seed, iterations, status, headline stats
                          └── SimulationArtifact (losses, sorted, lefs,
                                                   histogram, LEC, drivers)

Portfolio (named) | "default" (= all active scenarios)
   ├── scenario_public_ids
   ├── appetite, insurance_offset, correlation_assumption
   └── PortfolioSnapshot[]  (trend history)

ApprovalRequest      — every state transition recorded
ReviewSchedule       — cadence + next_due per entity
AuditLog             — append-only; every mutation
ThreatEntry          — knowledge library
ControlEntry         —    "
BenchmarkEntry       —    "
AppSettings          — singleton; defaults + ULA acknowledgement
```

**Distribution param shape** (canonical):
```json
{ "type": "pert", "min": 1, "mode": 4, "max": 12 }
{ "type": "lognormal", "min": 200000, "max": 6000000 }   // min=P10, max=P90
{ "type": "uniform", "min": 0.1, "max": 0.9 }
{ "type": "beta", "min": 0, "max": 1, "alpha": 2, "beta": 5 }
{ "type": "gamma", "min": 0, "max": 100, "shape": 2 }
```

---

## 7 · Migration roadmap

The Alpha persisted to `localStorage` under key `forlas.fairCrq.v1`. The
Beta importer (`POST /api/import/alpha`) accepts the Alpha's own
`exportAll()` JSON and writes scenarios into the Beta DB.

| Alpha field         | Beta field                                         |
|---------------------|----------------------------------------------------|
| `name`              | `scenarios.name`                                   |
| `bu`                | `scenarios.business_unit`                          |
| `owner`             | `scenarios.owner_label` (text — link by hand)      |
| `type`              | `scenarios.scenario_type`                          |
| `tags`              | `scenarios.tags` (JSON)                            |
| `tolerance`         | `scenarios.tolerance`                              |
| `mode`              | `scenarios.mode` (enum-validated)                  |
| `inputs`            | `scenarios.inputs` (JSON, same shape)              |
| `refLines`          | `scenarios.reference_lines`                        |
| `prefs`             | `scenarios.prefs`                                  |
| `version`           | `scenarios.version_label`                          |
| `assessmentDate`    | `scenarios.assessment_date`                        |
| `reviewDate`        | `scenarios.review_date`                            |
| `notes`             | `scenarios.notes`                                  |

Items NOT brought across (regenerable):
- `cache` (simulation results) — re-run in the Beta engine
- `portfolioSnapshots` — start fresh
- `history` (legacy) — discarded
- `benchmarkGroup` — retired field; no longer stored or imported

---

## 8 · Alpha → Beta phases (as built)

| #  | Name                                | Outcome                                                              |
|----|-------------------------------------|----------------------------------------------------------------------|
| 1  | Foundation & scaffolding            | Repo, FastAPI app, 12 ORM tables, auth, Alpha importer, React shell  |
| 2  | Simulation engine (Python)          | NumPy/SciPy port, all 7 distributions, 3 modes, parity validation    |
| 3  | Workspace + Sim Data                | Three-col workspace, distribution wizard, ECharts results panel      |
| 4  | Dashboard + Register + Portfolio    | Element-wise sum aggregation, register table, snapshots              |
| 5  | Reporting engine                    | Jinja2 HTML + python-docx; presentation mode                         |
| 6  | Governance                          | Approval state machine, RBAC, review schedules, change history       |
| 7  | Knowledge library                   | FAIR/ATT&CK threats, NIST CSF/CIS/ISO controls, benchmarks           |
| 8  | Packaging (Tauri + Docker)          | Docker validated, Tauri sidecar scripted, backup endpoints           |
| 9  | Plugin architecture                 | Entry-points host, distribution/exporter/knowledge hooks, demo plugin |
| 10 | Design document                     | This file                                                            |

Phase boundaries were milestone check-ins; tests were added per phase, never
deleted (53 currently green).

---

## 9 · MVP milestone plan

MVP = Phases 1 – 5. That's the minimum that replicates the Alpha plus
multi-user persistence and proper exports. Phases 6 – 9 are governance,
knowledge, packaging, and extensibility — required for production SMB
deployment but not for "the original is now maintainable."

**MVP acceptance criteria (all met):**
- Users can log in to a local-only account.
- 6 Alpha-equivalent demo scenarios seed on first run.
- All 7 distributions and 3 modes produce numerically sane outputs.
- A simulation completes in <300ms at 50K iterations on the test box.
- Workspace UI matches the Alpha's spirit (tighter, no neon, no glass).
- Portfolio aggregation produces sum-of-means within 1e-6 of the analytical
  value.
- Executive + Board HTML reports render and print to PDF.
- DOCX downloads validate as proper Word documents.

---

## 10 · Detailed component specifications

The five most architecturally load-bearing components — those that the rest
of the app depends on for correctness.

### 10.1 `app.engine.simulation.run_simulation`

Pure function — no DB, no FastAPI dependency. Input: scenario dict + `RunOptions`.
Output: `RunResult` dataclass.

Vectorised path:
1. Draw `lef`, `tef`, `vuln` arrays of shape `(n,)` per mode.
2. `n_events = rng.poisson(lef)` (vector of Poisson counts).
3. Sample `total_events = sum(n_events)` flat draws of primary loss,
   secondary probability, secondary loss.
4. `event_loss = primary + where(uniform < sprob, secondary, 0)`.
5. Reduce per-iteration sums with `_segmented_sum` over cumulative starts.
6. Apply `reduction_factor = 1 - reduction_pct/100`.
7. Sort once; derive percentiles, CI, tail, histogram, LEC, sensitivity in
   single linear scans.

Determinism guarantee: identical seed + identical scenario JSON ⇒ identical
sorted_losses (bit-exact). Asserted by `test_simulation_deterministic_at_fixed_seed`.

### 10.2 `app.engine.portfolio.aggregate`

Element-wise sum of independent loss vectors, truncated to the shortest. Insurance
offset is `loss - clip(loss - deductible, 0, limit)`. Per-scenario rows include
share-of-ALE and over-tolerance booleans. Empty input returns a zeroed `PortfolioRollupResult`
so callers don't need null-checks.

### 10.3 `app.deps.require_role`

Dependency factory. Returns a callable that resolves the current user from
`Cookie(session_token)`, looks them up, and raises 401 if no user, 403 if
their `Role.rank` is below the minimum. Used as `Annotated[User, Depends(require_role(Role.REVIEWER))]`
on every mutating endpoint.

### 10.4 `app.services.audit.record`

Appends an `AuditLog` row. Always called inside the same transaction as the
business change so audit + change commit atomically. Stores `before`/`after`
JSON for `UPDATE` actions. The endpoint layer is responsible for calling it;
no global mutation hook (kept explicit so contributors can't accidentally
omit it).

### 10.5 `app.plugins.discover`

Idempotent. Walks `entry_points(group="forlas.plugins")`, loads each
manifest, registers it. Distribution collisions log a warning and keep the
first. The host runs once during the FastAPI lifespan, before bootstrap
seeding, so plugin knowledge entries surface in the same `/api/knowledge/*`
queries as built-ins.

---

## 11 · Docker deployment strategy

Multi-stage build, ~250 MB final image.

**Stage 1 — frontend** (`node:22-alpine`): npm install, `VITE_BASE_PATH=/app/`,
`npm run build` → `/app/dist`.

**Stage 2 — runtime** (`python:3.13-slim`): installs the backend via
`pip install .`, copies the SPA bundle into `/srv/static`, exposes 8765,
healthcheck on `/api/health`.

The FastAPI app auto-detects the `static/` directory at boot and mounts it at
`/app/`. SPA hits `/api/*` on the same origin → no CORS gymnastics.

**Data volume** at `/data` for the SQLite file + WAL + backups. Compose file
ships a named volume `forlas_data`.

**First-run owner credentials** print to container stdout once. Set
`FORLAS_BOOTSTRAP_OWNER_PASSWORD` to preset.

**Hardening defaults**: session cookies HttpOnly + SameSite=lax (no Secure flag
because local-only HTTP is assumed; flip if you put TLS in front). CORS
restricted to localhost + the bundled SPA origin.

---

## 12 · Tauri packaging strategy

Tauri 2 host (Rust), Python backend as a sidecar binary.

**Build pipeline:**
1. `python scripts/build_backend_sidecar.py` — PyInstaller bundles the backend
   into a single executable named `forlas-backend-<target-triple>[.exe]`,
   placed in `src-tauri/binaries/`. Tauri's sidecar convention requires the
   target-triple suffix.
2. `cargo tauri build` — Tauri builds the Rust host with the SPA frontend
   pre-built (its `beforeBuildCommand` runs `npm run build` for us), bundles
   the sidecar binary into the installer, signs with the configured key, and
   produces platform installers under `src-tauri/target/release/bundle/`.

**Runtime:** Tauri's `main.rs` spawns the sidecar in `setup()`, pointing
`FORLAS_DATA_DIR` at the platform-standard user data directory
(`%LOCALAPPDATA%\FORLAS\CRQ` on Windows etc.). On exit, the sidecar is
killed. The Rust process keeps a `Mutex<Option<CommandChild>>` so exit-on-quit
is clean.

**CSP** locked to `'self'` plus `http://127.0.0.1:8765` (the sidecar) and
`ipc:` (Tauri IPC). No external resources permitted.

**Code-signing** keys are operator-supplied per OS; see Tauri docs for
platform specifics.

---

## 13 · Simulation engine separation strategy

The engine (`app/engine/`) is dependency-only on NumPy, SciPy, and Python
stdlib. It does **not** import from `app.api`, `app.db`, or `app.services`.
This keeps three properties:

1. **Pure-Python validation.** Tests for engine correctness don't need a
   FastAPI client or a database fixture — they instantiate `RunResult` from
   plain dicts.
2. **Reusable from other hosts.** A future CLI, a notebook, or another
   plugin can `from app.engine import run_simulation` and get the full math
   without dragging in the web framework.
3. **Plugin-extensible.** `engine.distributions.sample()` lazily consults
   `plugins.registry.distributions`; this is the only dependency the engine
   has on the plugin host (lazy import to avoid a cycle).

Aggregation lives next to it (`engine/portfolio.py`) but is similarly framework-
free; `services/portfolio.py` is the thin database adapter that calls into
it after gathering loss vectors from `simulation_artifacts`.

---

## 14 · Reporting engine design

Two output paths:

**HTML report** (`reporting/html_report.py`) — Jinja2-rendered. Templates
live in `reporting/templates/` and inherit from `_base.html` which carries
the print styles (8mm margins, the soft palette, `@media print` overrides
that hide the floating "Print to PDF" button). The frontend opens the
returned HTML in a new window; user prints with Ctrl/Cmd+P.

**DOCX report** (`reporting/docx_report.py`) — python-docx. The board pack
walks the scenarios list and builds one section per scenario with a metrics
table and a sensitivity sub-table.

Both consume the same `context` dict produced by `reporting/data.py`. The
context shape is documented at the top of that module — adding a new format
is a one-file change (write a `Plugin.render(context) → (bytes, mime, name)`).

Server-rendered PDF (for example via WeasyPrint) was considered and dropped:
its GTK dependency on Windows outweighs the benefit while browser
print-to-PDF covers the same need. A future plugin can add it through the
same context contract.

---

## 15 · Import / export architecture

**Inbound:**
- `POST /api/import/alpha` — Alpha localStorage JSON → scenarios.
- `POST /api/knowledge/import?kind=threats|controls|benchmarks&source=…` —
  custom catalogues, idempotent on `public_id` collisions.
- (Tauri) `forlas-backup.db` files restored by stopping the app and
  swapping the file under `<data_dir>/`.

**Outbound:**
- `GET /api/portfolio/register` → frontend `Export CSV` button on Register page.
- `GET /api/simulations/{id}/losses` → Sim Data screen's CSV/JSON export.
- `POST /api/reports/html` → HTML for print-to-PDF.
- `POST /api/reports/docx` → binary `.docx` attachment.
- `POST /api/system/backup` → server-side SQLite snapshot to
  `<data_dir>/backups/forlas_crq_<timestamp>.db`.

**Round-trip stability** is guaranteed by `public_id` references — IDs never
change across export/import unless a user explicitly clones.

---

## 16 · Plugin architecture

Discovery via `importlib.metadata.entry_points(group="forlas.plugins")`.

A plugin is a Python package that registers a `PluginManifest` object under
that group. Example `pyproject.toml`:

```toml
[project]
name = "my-forlas-plugin"
version = "0.1.0"
dependencies = ["forlas-crq>=0.1"]

[project.entry-points."forlas.plugins"]
my_plugin = "my_pkg.forlas_plugin:plugin"
```

```python
# my_pkg/forlas_plugin.py
from app.plugins import PluginManifest, DistributionPlugin

def lognormal_p50_p95(rng, n, params): ...

plugin = PluginManifest(
    name="my-plugin",
    version="0.1.0",
    distributions=[
        DistributionPlugin(type_name="lognormal-p50-p95",
                           sampler=lognormal_p50_p95),
    ],
)
```

Three extension points are first-class today:
- `DistributionPlugin` — new distribution types reachable from any scenario.
- `ExporterPlugin` — new export formats; the contract returns
  `(bytes, media_type, filename)`. The reporting API gains them automatically
  once the API surface is extended (1 file change).
- `KnowledgePlugin` — extra threats / controls / benchmarks seeded with the
  plugin's source label.

The demo plugin (`backend/tests/fixtures/demo_plugin.py`) ships a
`weibull` distribution, an xlsx stub exporter and a contributed threat. It
doubles as a copy-able template.

`GET /api/plugins` lists all loaded manifests for the UI to surface.

---

## Appendix A — Test inventory (53 tests, all green)

| File                        | What it covers                                    |
|-----------------------------|---------------------------------------------------|
| `test_smoke.py` (7)         | Health, session, scenario CRUD, ULA, Alpha import |
| `test_engine.py` (16)       | Distributions, statistics, simulation invariants  |
| `test_simulation_api.py` (3)| End-to-end run + RBAC enforcement                 |
| `test_portfolio.py` (8)     | Aggregation engine + rollup/register/snapshot API |
| `test_reports.py` (4)       | HTML + DOCX rendering                             |
| `test_governance.py` (6)    | Approval state machine + RBAC + schedules + versions |
| `test_knowledge.py` (5)     | Seed presence, filters, search, custom import     |
| `test_plugins.py` (4)       | Distribution registration, knowledge seed, list   |

## Appendix B — Out-of-scope (intentional)

The following were considered and explicitly excluded to keep the local-first
discipline:

- Remote IdP / OAuth / SAML — local accounts only.
- Multi-tenant data isolation — single org per install.
- Real-time collaborative editing — last-write-wins with audit log.
- WebSocket push for long simulations — synchronous + in-process worker.
- Server-side PDF rendering by default — browser print-to-PDF works
  everywhere and zero install-time deps.
- Kubernetes / horizontal scaling — single process by design.

## Appendix C — Data we deliberately don't keep

- Per-iteration losses for runs older than the configurable retention window
  (future toggle; currently kept indefinitely).
- Telemetry of any kind. Period.
- Login IP addresses beyond what the user-session row optionally records.

---

**End of document.**

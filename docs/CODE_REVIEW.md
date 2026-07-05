# Code Review — Issues for Remediation

**Reviewer:** Claude (Fable 5) · **Date:** 2026-07-02
**Scope:** Full codebase at `E:\FORLAS-CRQ-Beta` (backend 82-test green, frontend tsc-clean at time of review).
**Verification:** Every Critical/High finding below was confirmed against the current source, not inferred. File:line references are to the state at review time.

---

## REMEDIATION STATUS (updated 2026-07-02, Opus 4.8)

All Critical + High + Medium findings addressed. Backend **108 tests green**, frontend **33 Vitest tests green**, `tsc` clean, ESLint 0 errors, production build OK.

| ID | Status | Notes |
|----|--------|-------|
| C1 | ✅ Fixed | `services/sessions.py`: `_resolve_user` checks live session; logout revokes; deactivate revokes all; startup+login purge. Tests in `test_auth_sessions.py`. |
| C2 | ✅ Fixed | `config.py` persists key to `<data_dir>/secret.key` (env var wins). Tested. |
| C3 | ✅ Fixed | Dropped `readme=../README.md` from pyproject; editable install verified. (Full `docker build` still needs a running daemon — wired into CI.) |
| C4 | ✅ Fixed | `engine/errors.py` + global 422 handler; Alpha import validates + skips invalid with count. Tests in `test_engine_errors.py`. |
| H1 | ✅ Fixed | Non-draft scenarios reject modelling edits (409); metadata still editable. |
| H2 | ✅ Fixed | Owner-or-Approver+ gate on update/delete; `transfer-ownership` endpoint added. |
| H3 | ✅ Fixed | Schedules → Reviewer+; settings → Owner. Tests in `test_rbac.py`. |
| H4 | ✅ Fixed | `api.ts` 401 handler → clears auth + QueryClient → LoginPanel. |
| H5 | ✅ Fixed | `max_iterations` lowered to 1M; sync ceiling enforced (422 above). |
| H6 | ✅ Partial | Retention (keep latest 5/scenario) + rollup cache done. Compressed-binary artifact storage deferred (perf-only, see debt). |
| H7 | ✅ Fixed | `eslint.config.js` added; 4 errors fixed; `npm run lint` green. |
| H8 | ✅ Fixed | Baseline revision cut; startup stamps legacy unstamped DBs. Three paths verified. |
| M1 | ✅ Fixed | Rollup endpoint takes `scenario_ids`; PresentationMode passes selection. |
| M2 | ✅ Fixed | Benchmarks tab fetches full list, filters client-side. |
| M3 | ✅ Fixed | Portfolio per-scenario percentiles now use engine floor-index method. |
| M4 | ✅ Fixed | Dead `_aggregate_event_losses` removed; `appetite` param dropped; `needs_rehash` called on login. |
| M5 | ✅ Fixed | Client-side theme store + toggle in TopBar; dark ECharts theme registered. |
| M6 | ✅ Fixed | Settings page: Users (owner CRUD), Backups, self password-change cards. |
| M7 | ✅ Fixed | `/losses` paginated; `/losses.csv` streams full vector. |
| M8 | ✅ Fixed | `restore` endpoint + `/deleted` list + "Show deleted" UI; delete copy corrected. |
| M9 | ✅ Fixed | Dirty detection uses `stableStringify` over the editable projection. |
| M10 | ⚠️ Deferred | Per-handler commits are consistent and work; dependency-level commit refactor left as debt (risk/reward). |
| L1–L3, L5–L9, L11 | ✅ Fixed | 401 handler, error boundary, 404 route, version constant, report iterations formatting, start-dev hint, Tabs keyboard nav, session UA/IP captured. |
| L4, L10, L12 | ⚠️ Deferred | TopBar per-run chips, commit refactor, `ScenarioVersion.diff` population — minor, see debt. |
| Frontend tests | ✅ Added | Vitest: `format`, `interpolate`, `stableStringify` (33 tests). |
| CI | ✅ Added | `.github/workflows/ci.yml` — backend pytest, frontend tsc/lint/vitest/build, docker build. |
| Mulberry32 | ✅ Removed | Unused, unverified "parity" RNG deleted per recommendation. |

**Remaining technical debt (intentional):** compressed-binary artifact storage (H6b), dependency-level commit standardisation (M10), TopBar per-run seed/iteration chips (L4), `ScenarioVersion.diff` computation (L12), route-level code-splitting for the 1.2 MB bundle, login rate-limiting, server-side WeasyPrint PDF endpoint.

---

---

## CRITICAL — must fix before any real deployment

### C1. Logout does not revoke sessions; `user_sessions` table is write-only
`backend/app/deps.py:20-28` verifies only the signed cookie (`verify_session`) and the user's `is_active` flag. The `UserSession` rows written at login (`api/auth.py:54`) are **never read** — not at auth time, not at logout. Consequences:
- Clicking "Sign out" clears the browser cookie but the token remains valid for the full 12-hour TTL. Anyone who captured it (shared machine, logs) can keep using it.
- `revoked_at` and `expires_at` columns are dead.
- The table grows forever (no cleanup job).

**Fix:** In `_resolve_user`, after signature verification, look up the token in `user_sessions` and reject if missing/revoked/expired. On logout, set `revoked_at`. Add a periodic (or login-time) purge of expired rows. Add tests: token invalid after logout; token invalid after user deactivation (already works — keep a regression test).

### C2. `secret_key` is regenerated on every process start — all sessions die on restart
`backend/app/config.py:57`: `secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(48))`. Unless `FORLAS_SECRET_KEY` is explicitly set (it never is in dev, Docker compose, or the Tauri sidecar), each backend restart mints a new key, silently invalidating every cookie. This also breaks any future multi-worker uvicorn setup (each worker gets a different key → random 401s).

**Fix:** Persist a generated key to `<data_dir>/secret.key` on first run (chmod 600 where applicable) and load it thereafter. Env var still wins if set.

### C3. Docker build will fail — `readme = "../README.md"` escapes the build context
`backend/pyproject.toml:5` points at `../README.md`. The Dockerfile copies `backend/pyproject.toml` to `/srv/pyproject.toml` and runs `pip install .` — hatchling will try to read `/README.md`, which doesn't exist in the image → build error. This was never caught because the Docker daemon was down when Phase 8 was "validated" (only `docker compose config` was run).

**Fix:** Either copy README into the image, or (cleaner) inline a short `readme` string / drop the field. Then actually run `docker build` end-to-end as verification.

### C4. Simulation failures return HTTP 500 with stack traces instead of 4xx
`backend/app/services/simulation.py` catches engine exceptions, marks the run FAILED, then **re-raises**; `api/simulations.py` has no handler, so a bad distribution (e.g. an Alpha-imported scenario missing `plm`, or `min > max` values that slipped past validation because `inputs` is stored as raw JSON) produces a 500. The Alpha importer (`services/import_alpha.py`) performs **no validation** of the `inputs` shape, so this is a realistic path, not a corner case.

**Fix:** Map `DistError`/`KeyError` from the engine to HTTP 422 with a human-readable message naming the offending variable. Validate imported scenarios against `ScenarioInputs` at import time; import invalid ones with a `needs_attention` flag or skip-with-count rather than storing unusable rows.

---

## HIGH — functional or governance gaps

### H1. Approved scenarios remain fully editable
`services/scenario.py:update_scenario` never checks `approval_state`. A scenario in `approved` (or `in_review`/`archived`) state can be freely modified by any Reviewer without transitioning back to draft — which defeats the entire approval workflow built in Phase 6.

**Fix:** Reject mutations (inputs/mode/tolerance — metadata like notes may be allowed) on non-draft scenarios with 409 + "reopen to draft first", or auto-transition to draft with an audit entry. Decide and test both paths.

### H2. Per-scenario ownership is not enforced
The Phase-1 decision record says "per-scenario ownership enforced", and `scenarios.owner_user_id` exists — but any Reviewer can edit/delete/clone **any** scenario. Ownership is currently decorative.

**Fix:** Enforce owner-or-Approver+ on update/delete, or explicitly descope with a note in DESIGN.md. If enforcing, add an ownership-transfer endpoint (was in the Phase 6 scope, never built).

### H3. Review schedules and ULA can be modified by ReadOnly users
`api/governance.py:upsert_schedule` and `mark_reviewed` take `user: CurrentUser` — a `readonly` user can create/modify review schedules and mark reviews done. Same for `api/system.py:update_settings` and `acknowledge_ula` (any authenticated user changes global iterations/seed/theme and acknowledges the ULA org-wide).

**Fix:** Schedules → Reviewer+. Settings → Owner (or Approver+). ULA acknowledge → arguably any user is fine for a local tool, but document the choice.

### H4. No 401 handling in the frontend — expired session leaves a zombie UI
`frontend/src/lib/api.ts` throws `ApiError` on 401 but nothing catches it globally: after the 12-h TTL (or backend restart per C2), every query silently fails, screens show stale/empty data, and the user is never returned to the login panel.

**Fix:** In the `request` helper (or a QueryClient `onError`), on 401 call `useAuth.getState().clear()` and invalidate the session query so `App.tsx` re-renders the `LoginPanel`.

### H5. Synchronous simulation endpoint will block at high iteration counts
`POST /scenarios/{id}/simulations` runs the engine inline. Fine at 100K (<300 ms), but `max_iterations` permits **5,000,000** — tens of seconds occupying a threadpool worker, no progress reporting (the `progress` column exists but never moves), no cancellation (`CANCELLED` status is unreachable). The `app/jobs/` package is still an empty placeholder.

**Fix:** Either cap the sync path at ~500K and route larger runs through the promised in-process worker (thread + polling endpoint, wiring the existing `progress`/`status` fields), or descope 5M and lower `max_iterations`.

### H6. Simulation artifacts stored as JSON arrays — ~2 MB text per 100K-iteration run, no retention
`models/simulation.py:SimulationArtifact` stores `losses`, `sorted_losses`, `lefs` as JSON lists. Every run adds ~2–6 MB of parsed-on-read TEXT; nothing ever prunes old runs. Compounding this, **every dashboard rollup request** (`services/portfolio.py:collect_latest_runs`) re-loads and JSON-parses the full loss vector for every scenario — that's the hot path for the Dashboard, Register, and Reports pages.

**Fix (staged):** (a) keep only the latest N artifacts per scenario, delete older on run completion; (b) store vectors as compressed binary (`np.float64.tobytes()` + zlib in a BLOB column) — ~8× smaller and ~20× faster to load; (c) cache the portfolio rollup keyed on latest-run IDs, invalidate on new run/snapshot.

### H7. `npm run lint` is broken — no ESLint config exists
`frontend/package.json` declares `"lint": "eslint src --max-warnings 0"` and devDependencies for eslint 9 + typescript-eslint, but there is **no `eslint.config.js`** in the frontend root. The script errors immediately. Nothing has ever been linted.

**Fix:** Add a flat config (typescript-eslint recommended + react-hooks + react-refresh), run it, and fix what it finds (there will be unused imports and `any`-typed ECharts formatters, both currently invisible).

### H8. No Alembic baseline — migrations can never start cleanly
`backend/alembic/versions/` is empty; startup falls back to `SQLModel.metadata.create_all`. This was an acknowledged Phase-1 stopgap, but every user DB created since is unstamped. The first real schema change now has no anchor: `alembic upgrade head` on an existing DB will try to create tables that already exist.

**Fix:** Cut revision 0001 as the current schema baseline; on startup, if DB exists but is unstamped, `alembic stamp 0001` before upgrading. Test the three paths: fresh DB, existing-unstamped DB, existing-stamped DB.

---

## MEDIUM — bugs and inconsistencies

### M1. PresentationMode portfolio slide ignores the scenario selection
`components/reports/PresentationMode.tsx:17` calls `usePortfolioRollup()` (all scenarios) even when the user selected a subset on the Reports page. Title + portfolio slides show all-scenario totals while the per-scenario slides honour the selection — internally inconsistent numbers in front of a board.

**Fix:** Pass `scenarioIds` through to a filtered rollup (backend `rollup` endpoint needs an optional `scenario_ids` param) or compute the subset totals client-side from the per-scenario data.

### M2. Knowledge → Benchmarks filter dropdowns collapse after filtering
`pages/KnowledgePage.tsx` (BenchmarksTab): `industries` and `metrics` option lists are derived from `data`, but `data` is the **already-filtered** query (queryKey includes `industry`/`metric`). Select "Manufacturing" and every other industry vanishes from the dropdown; you can't switch without selecting "All" first.

**Fix:** Fetch the unfiltered list once for options (separate query) or filter client-side from a single full fetch (the catalogue is small).

### M3. Percentile method inconsistent between engine and portfolio per-scenario stats
`engine/statistics.py:percentiles` uses index `floor(q·n)` (Alpha parity), while `engine/portfolio.py:aggregate` computes per-scenario `p95/p99` with `np.percentile` (linear interpolation). The same scenario can show slightly different P95 on the Workspace vs the Dashboard top-drivers table.

**Fix:** Pick one method (recommend the empirical `floor` for consistency with the headline stats) and use it everywhere; regression-test that Workspace P95 == Dashboard P95 for the same run.

### M4. Dead code and unused parameters in the engine
- `engine/simulation.py:_aggregate_event_losses` (~40 lines) is the superseded Python-loop version — never called.
- `engine/portfolio.py:aggregate(appetite=...)` accepts `appetite` but never uses it; appetite math happens in the serializer. Misleading signature.
- `security.py:needs_rehash` is exported but never called (password hashes never upgrade if Argon2 params change).

**Fix:** Delete the dead function; drop the unused param; call `needs_rehash` + rehash on successful login.

### M5. Theme setting exists but dark mode is unreachable
`.dark` token overrides exist in `globals.css`, `app_settings.theme` persists via the API, the spec says "Dark mode ready, switch for choice" — but nothing ever applies the `dark` class to `<html>`, and there is no toggle in Settings. Additionally the ECharts theme (`lib/echarts.ts`) hardcodes light-mode hex colours, so charts would stay light even if the class were applied.

**Fix:** Settings toggle → PATCH theme → apply/remove `document.documentElement.classList`; register a second ECharts theme (or use CSS-var-driven colours) for dark.

### M6. Backup/restore and user management have no UI
`POST /api/backup`, `GET /api/backups` (Phase 8) and the full user-management API (`/api/auth/users`, Phase 1) are backend-only. The Settings page doesn't surface backups; there is no screen to create/deactivate users or change passwords — the bootstrap Owner literally cannot change their own password from the UI.

**Fix:** Settings → "Backups" card (create + list) and "Users" card (Owner-only: list/create/edit/deactivate, self password change).

### M7. `GET /api/simulations/{id}/losses` returns the full raw vector with no cap
At 100K iterations that's a ~2 MB JSON response per Sim Data page view; at 5M (see H5) it's ~100 MB and will hang the browser tab. No pagination, no downsampling option.

**Fix:** Add `?limit=&offset=` or return a downsampled preview + streaming CSV endpoint for full export.

### M8. Scenario delete confirmation promises a restore that doesn't exist
`components/workspace/ScenarioList.tsx`: *"This is reversible from the audit log."* Soft-delete sets `deleted_at`, but there is **no restore endpoint and no UI** — the audit log just proves what you lost.

**Fix:** Either add `POST /scenarios/{id}/restore` (+ "Deleted scenarios" view) or change the copy to be honest.

### M9. Draft-dirty detection via `JSON.stringify` equality
`pages/WorkspacePage.tsx`: `isDirty` compares `JSON.stringify(draft) !== JSON.stringify(selected)`. Key-order-sensitive and fires false "Unsaved" states (e.g. server normalises `reference_lines`/`prefs` ordering, or float round-trips 0.6 → 0.6000000000000001). Also triggers save-before-run churn.

**Fix:** Deep-equal on a normalised projection of the editable fields (or track dirty via explicit change flags).

### M10. Session/system endpoints commit inconsistently
Some read-path handlers call `db.commit()` after `audit.record` (e.g. report HTML render); others `flush` only. `get_session` yields a Session with no commit-on-success wrapper, so any handler that forgets `commit()` silently loses its audit rows (the smoke tests would not catch this).

**Fix:** Standardise: dependency-level commit-on-success/rollback-on-error, and remove per-handler commits.

---

## LOW — polish, hygiene

- **L1.** `frontend/src/store/auth.ts` clear() is never triggered by API-level 401 (covered by H4) — also `logout` mutation in TopBar clears the QueryClient but not the router state; user lands back on login with the previous route lost. Consider preserving `redirect_to`.
- **L2.** No React error boundary — any render exception white-screens the app. Add one at the AppShell level with a "reload" affordance.
- **L3.** No 404/catch-all route in `routes/router.tsx` — unknown URLs render a blank outlet.
- **L4.** `TopBar` seed/iterations chips show the *global defaults*, not the values of the currently-viewed scenario's latest run — mildly misleading next to per-run charts.
- **L5.** `Sidebar` hardcodes "Build 0.1.0" — read from a single version constant (also drifts from `pyproject`/`package.json`).
- **L6.** HTML report template renders `{{ portfolio.iterations }}` unformatted (no thousands separator) while every money value is formatted.
- **L7.** `tests/conftest.py` mutates the `settings` singleton via `object.__setattr__` — works, but fragile against pydantic-settings upgrades; consider a `get_settings()` provider with dependency override instead.
- **L8.** `scripts/start-dev.ps1` login hint hardcodes the password `ChangeMe!1234` — fine for dev, but remove before sharing the repo.
- **L9.** Custom `Tabs` component: no arrow-key navigation, no `tabindex` roving — spec calls for keyboard navigation & accessibility. Charts also lack `aria-label`s.
- **L10.** `engine/distributions.py:sample` does `from app.plugins import registry` on **every call** (twice per event batch). Cheap after first import, but hoist to module level with a late-binding accessor for tidiness.
- **L11.** `UserSession.user_agent`/`ip_address` never populated (login handler doesn't pass them).
- **L12.** `ScenarioVersion.diff` column exists but is never computed/stored.

---

## TEST GAPS

| Area | Missing |
|---|---|
| Frontend | **Zero tests.** No Vitest setup. Highest-value first targets: `formatCurrencyAUD` breakpoints, ReportsPage selection model (select all/none/partial/re-select — required by fix.md §6 but only backend-tested), LEC `interpolateY`, Sim Data percentile/σ derivation. |
| Auth | Session revocation on logout (blocked by C1), cookie expiry, rehash-on-login (M4). |
| Governance | Editing an approved scenario (blocked by H1), ownership enforcement (H2), readonly-user schedule mutation (H3 — currently would *pass* wrongly, i.e. asserts the bug). |
| Engine | Mulberry32 compat class has no test (and `rng.py:Mulberry32` looks unfinished — its bit-twiddling doesn't match the Alpha JS closely; verify against known JS outputs before claiming parity anywhere). |
| Packaging | Docker build never executed (C3 proves the gap). Tauri build never executed. Add a CI job for at least `docker build`. |
| E2E | No Playwright/e2e smoke (login → run sim → see results). |

---

## STRUCTURAL / IMPROVEMENT SUGGESTIONS (non-blocking)

1. **CI pipeline** — no `.github/workflows/`. Minimum: backend pytest, frontend tsc + eslint (after H7) + build, `docker build`. All are fast (<3 min total).
2. **Bundle size** — single 1.18 MB JS chunk; Vite warns. Manual chunks for `echarts` (~500 KB) and route-level lazy imports would roughly halve first paint.
3. **`fmt.money` on log-axis ticks** produces steps like `A$31.6K` — consider snapping tick labels to decades for cleaner axes.
4. **`Mulberry32` in `rng.py`** — currently unused by any code path. Either finish + test it (for genuine Alpha parity demos) or delete it; shipping an untested "compat" RNG invites someone to trust it.
5. **`services/scenario.py:_to_read`** builds dicts by hand in three places; a single `Scenario → ScenarioRead` converter (pydantic `model_validate` with `from_attributes`) would remove drift risk between list/get/update payloads.
6. **DESIGN.md drift** — the design doc predates the AUD/currency work, knowledge CRUD, and AppShell changes. Refresh §5 (component inventory), §14 (reporting), and Appendix A test counts when the above fixes land.
7. **Rate-limit login** — no throttle on `POST /api/auth/login`; local app, but Argon2 at 64 MB/hash means a hostile LAN peer can also cheaply CPU-DoS. A simple per-IP token bucket suffices.
8. **`docs/PACKAGING.md`** promises WeasyPrint server-side PDF as opt-in but no endpoint exists — either add `POST /api/reports/pdf` behind a feature check or trim the doc.

---

## SUGGESTED FIX ORDER

1. **C1 + C2** (auth/session integrity — small, high value, testable together)
2. **C4** (error mapping + import validation — user-visible 500s)
3. **C3** (unblock Docker; run the build in CI while at it → also covers packaging test gap)
4. **H1 + H2 + H3** (governance RBAC batch — one review of every endpoint's role gate)
5. **H4** (frontend 401 → login)
6. **H7** (ESLint config, then fix findings)
7. **H8** (Alembic baseline before any further schema change)
8. **H5 + H6 + M7** (simulation scale/storage batch)
9. Mediums in listed order; Lows opportunistically.

# Contributing to FORLAS CRQ

Thanks for your interest in improving FORLAS CRQ. Contributions of all kinds —
bug reports, fixes, features, tests, and documentation — are welcome.

## Licensing of contributions (inbound = outbound)

FORLAS CRQ is released under the **MIT License**. By submitting a contribution
(a pull request, patch, or otherwise), **you agree that your contribution is
licensed under the same MIT License** and that you have the right to submit it.

We use the **Developer Certificate of Origin (DCO)** — a lightweight alternative
to a CLA. Sign off each commit:

```bash
git commit -s -m "your message"
```

This appends a `Signed-off-by: Your Name <you@example.com>` line certifying the
[DCO](https://developercertificate.org/). No separate CLA is required.

## Design principles (please preserve these)

FORLAS CRQ's identity is its architecture. Contributions must keep it:

- **Local-first and offline** — everything runs on the user's machine.
- **No telemetry, no cloud, no external network calls** in normal operation. Do
  not add analytics, crash reporters, auto-update pings, or third-party API calls.
- **Loopback-only backend** (`127.0.0.1`).
- **Quantitative integrity** — the Monte Carlo engine's correctness is paramount.
  Any change to the engine, statistics, or distributions must be backed by tests
  (see the analytical cases in [`docs/UAT.md`](./docs/UAT.md) §6).

## Reporting bugs and requesting features

Use **GitHub Issues**. For bugs, include: version/commit, OS, steps to reproduce,
expected vs actual behaviour, and any relevant output.

**Security issues: do not open a public issue — see [SECURITY.md](./SECURITY.md).**

## Development setup

Prerequisites: **Python 3.13+**, **Node 20+** (22 recommended), and — for desktop
builds only — **Rust** plus the [Tauri prerequisites](https://tauri.app/start/prerequisites/).

```bash
# Backend
cd backend
python -m venv .venv
. .venv/Scripts/Activate.ps1        # bash: source .venv/Scripts/activate
pip install -e .[dev]
uvicorn app.main:app --reload --port 8765   # DB initialises on first run

# Frontend (separate shell)
cd frontend
npm install
npm run dev
```

The frontend dev server runs on http://localhost:5173 and talks to the backend on
http://localhost:8765. Full installer/packaging instructions are in
[`docs/PACKAGING.md`](./docs/PACKAGING.md).

## Project layout

```
backend/    FastAPI service + Monte Carlo engine + reporting (Python)
frontend/   React + TypeScript UI
src-tauri/  Tauri desktop shell (Rust) + sidecar packaging
scripts/    Build and dev convenience scripts
docs/       Design, packaging, UAT, SBOM
```

## Quality gates (run before opening a PR)

All of these must pass — CI runs them too.

**Backend** (from `backend/`, with the venv active):

```bash
pytest                  # tests
ruff check .            # lint
ruff format --check .   # formatting
mypy app                # type checking
```

**Frontend** (from `frontend/`):

```bash
npm run build   # typecheck (tsc) + production build
npm run lint    # eslint
npm test        # vitest
npm run format  # prettier
```

## Pull request guidelines

- **One focused change per PR.** Keep diffs small and reviewable.
- **Add or update tests** for behaviour changes — especially anything touching the
  simulation engine, statistics, or the API.
- **Match the surrounding style** (naming, comments, structure). Don't reformat
  unrelated code or churn the diff.
- **Update the docs** when you change behaviour, configuration, or the build.
- Explain *what* changed and *why* in the PR description; link any related issue.
- Sign off your commits (`git commit -s`).

## Code of conduct

Be respectful and constructive. Harassment, personal attacks, and abusive
behaviour are not tolerated. Maintainers may edit or remove contributions that
violate this and may block repeat offenders.

## Questions

Open a GitHub Discussion or Issue. Thanks for contributing to FORLAS CRQ!

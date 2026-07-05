# FORLAS CRQ — Beta

[![CI](https://github.com/Dark-Pr0xy/forlas-crq/actions/workflows/ci.yml/badge.svg)](https://github.com/Dark-Pr0xy/forlas-crq/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENCE.md)

Production Beta of the FORLAS CRQ tool: a **local-first, offline, no-cloud, no-telemetry** quantitative cyber risk platform built on the FAIR methodology, Monte Carlo simulation, and portfolio aggregation.

> This Beta is the maintainable successor to an earlier single-file HTML prototype (the "Alpha").

## Stack

**Backend** — Python 3.13+, FastAPI, SQLModel, Alembic, Pydantic v2, NumPy/SciPy, WeasyPrint, python-docx, Argon2.

**Frontend** — React + TypeScript, Vite, Tailwind CSS, ShadCN, Zustand, TanStack Query, TanStack Table, ECharts, Motion.

**Persistence** — SQLite (WAL mode), single database file in the user's data directory.

**Packaging** — Tauri 2 desktop app (primary); Docker Compose alternative (secondary).

## Repository layout

```
backend/         FastAPI service + Monte Carlo engine + reporting
frontend/        React UI
scripts/         Dev convenience scripts (Windows-friendly)
docs/            Engineering design document (produced in Phase 10)
alembic/         Database migrations
```

## Quick start (development)

```powershell
# Backend
cd backend
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -e .[dev]
alembic upgrade head
uvicorn app.main:app --reload --port 8765

# Frontend (new shell)
cd frontend
npm install
npm run dev
```

Frontend opens on http://localhost:5173, talks to the backend on http://localhost:8765.

First-run: the backend seeds an initial **Owner** account (credentials printed to stdout once) and the 6 demo scenarios from the Alpha.

## Design philosophy

Local-first. Offline-first. No cloud. No SaaS. No telemetry. No external services. No API dependencies.

Everything runs locally. The Tauri build is a single self-contained executable.

## Licence

Released under the **MIT License** — see [LICENCE.md](./LICENCE.md). © 2026 Michael Walker.

This project bundles third-party open-source components under their own licences; see [THIRD-PARTY-NOTICES.md](./THIRD-PARTY-NOTICES.md) and the [SBOM](./SBOM.md).

The tool incorporates concepts from the **FAIR methodology** (a trademark of the FAIR Institute); this implementation is independent and is not endorsed, certified, or affiliated with the FAIR Institute.

**Not professional advice.** FORLAS CRQ is a modelling tool. Its outputs depend entirely on user-supplied inputs and assumptions and do not constitute legal, financial, insurance, actuarial, or regulatory advice. Validate all outputs with qualified practitioners before relying on them.

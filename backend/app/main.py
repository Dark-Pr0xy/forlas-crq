"""FastAPI application factory and entry point.

`make_app()` returns a fully wired app; the module-level `app` is used by
`uvicorn app.main:app`.

Lifespan:
    - on start: ensure data dirs, run pending migrations, seed app settings
      and (when an owner password is preset) the owner + demo scenarios.
    - on shutdown: checkpoint the database.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alembic import command
from app.config import settings
from app.db import get_engine
from app.models import register_all  # populates SQLModel.metadata

logger = logging.getLogger("forlas")
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def _run_migrations() -> None:
    """Apply Alembic migrations on startup so dev runs and Tauri bundles never
    boot against an outdated schema.

    Handles three DB states:
      - fresh (no file / no tables): `upgrade head` creates everything.
      - existing but unstamped (created by an older build's create_all): stamp
        the baseline first so `upgrade` doesn't try to re-create existing tables.
      - existing + stamped: normal `upgrade head`.

    If no revisions are checked in at all (should not happen post-baseline),
    fall back to `create_all`.

    Frozen (PyInstaller/Tauri) builds skip Alembic entirely: bundling the
    migrations tree is fragile, and `create_all` is idempotent — it creates
    only missing tables and is a no-op on an existing DB. Schema upgrades for
    shipped desktop builds are handled at release time, not on every launch.
    """
    from sqlalchemy import inspect
    from sqlmodel import SQLModel

    from app.runtime import is_frozen

    if is_frozen():
        SQLModel.metadata.create_all(get_engine())
        logger.info("Frozen build — schema ensured via create_all (Alembic skipped).")
        return

    here = Path(__file__).resolve().parent.parent
    cfg = AlembicConfig(str(here / "alembic.ini"))
    cfg.set_main_option("script_location", str(here / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)

    versions_dir = here / "alembic" / "versions"
    has_revisions = versions_dir.exists() and any(
        p.suffix == ".py" and p.name != "__init__.py" for p in versions_dir.iterdir()
    )
    if not has_revisions:
        SQLModel.metadata.create_all(get_engine())
        logger.info("No Alembic revisions present — created schema from models.")
        return

    engine = get_engine()
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    has_data_tables = bool(existing_tables - {"alembic_version"})
    is_stamped = "alembic_version" in existing_tables

    if has_data_tables and not is_stamped:
        # An older build created these tables via create_all. Anchor them to the
        # baseline so the upgrade below is a no-op for already-present objects.
        _stamp_baseline_revision(cfg)
        logger.info("Stamped pre-existing unstamped database to the baseline revision.")

    command.upgrade(cfg, "head")


def _stamp_baseline_revision(cfg: AlembicConfig) -> None:
    """Stamp the earliest (base) revision so a legacy create_all DB is treated
    as already at the baseline."""
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(cfg)
    bases = script.get_bases()
    if bases:
        command.stamp(cfg, bases[0])


def _bootstrap() -> None:
    """First-run seeding. Idempotent.

    On a fresh interactive install no owner is auto-created: the user creates
    the first account through the setup screen, and the demo scenarios are
    seeded at that point (see ``POST /api/auth/setup``). When an owner password
    is preset (server / Docker / CI), the owner and demos are seeded here.
    """
    from sqlmodel import Session

    from app.knowledge.seed import seed_knowledge
    from app.services import sessions as session_svc
    from app.services.seed import (
        ensure_app_settings,
        ensure_bootstrap_owner,
        seed_demo_scenarios,
    )

    with Session(get_engine()) as db:
        ensure_app_settings(db)
        owner = ensure_bootstrap_owner(db)
        seeded = (
            seed_demo_scenarios(db, owner)
            if owner is not None and settings.seed_demo_scenarios
            else 0
        )
        kn_counts = seed_knowledge(db)
        purged = session_svc.purge_expired(db)
        db.commit()

        if purged:
            logger.info("Purged %d expired session(s).", purged)

        if any(kn_counts.values()):
            logger.info(
                "Seeded knowledge: %d threats, %d controls, %d benchmarks.",
                kn_counts["threats"],
                kn_counts["controls"],
                kn_counts["benchmarks"],
            )

        if owner is None:
            logger.info("No accounts yet — awaiting first-run account creation.")
        if seeded:
            logger.info("Seeded %d demo scenarios.", seeded)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services import backup as backup_svc

    register_all()
    settings.ensure_dirs()
    _run_migrations()
    # Durability floor: snapshot the last-known-good DB before we take writes.
    # Skips itself if the DB is malformed, so it can never clobber good backups.
    backup_svc.startup_auto_backup(
        get_engine(), settings.database_path, settings.backups_dir
    )
    _discover_plugins()
    _bootstrap()
    logger.info(
        "FORLAS CRQ ready · db=%s · port=%d", settings.database_path, settings.port
    )
    yield
    # Clean stop: flush WAL into the main file so a later hard kill is survivable.
    backup_svc.checkpoint_and_close(get_engine())


def _discover_plugins() -> None:
    from app.plugins import discover

    reg = discover()
    if reg.manifests:
        logger.info("Loaded %d plugin(s) from entry-point group.", len(reg.manifests))


def make_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from fastapi import Request
    from fastapi.responses import JSONResponse

    from app.engine.errors import SimulationInputError

    @app.exception_handler(SimulationInputError)
    async def _handle_input_error(_request: Request, exc: SimulationInputError):
        # Bad scenario inputs are the caller's to fix — 422, not a 500 stack trace.
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    from app.api import (
        analysis,
        auth,
        governance,
        knowledge,
        plugins,
        portfolios,
        reports,
        scenarios,
        simulations,
        system,
    )

    app.include_router(system.router)
    app.include_router(auth.router)
    app.include_router(scenarios.router)
    app.include_router(analysis.router)
    app.include_router(simulations.router)
    app.include_router(portfolios.router)
    app.include_router(reports.router)
    app.include_router(knowledge.router)
    app.include_router(governance.router)
    app.include_router(plugins.router)

    # When a built frontend ships alongside the backend (Docker, Tauri sidecar),
    # serve it from the same process so the user has one URL to hit.
    static_dir = Path(__file__).resolve().parent.parent / "static"
    if static_dir.exists():
        from fastapi.staticfiles import StaticFiles

        app.mount("/app", StaticFiles(directory=str(static_dir), html=True), name="app")

        @app.get("/", include_in_schema=False)
        def root_with_ui():
            from fastapi.responses import RedirectResponse

            return RedirectResponse(url="/app/")
    else:

        @app.get("/", include_in_schema=False)
        def root():
            return {
                "name": settings.app_name,
                "version": settings.app_version,
                "docs": "/docs",
            }

    return app


app = make_app()

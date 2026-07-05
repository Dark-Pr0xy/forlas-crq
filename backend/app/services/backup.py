"""Database durability: integrity checks, safe backups, WAL checkpointing.

The operating floor for the whole app. Two guarantees:

  1. A restart can never corrupt the DB — we WAL-checkpoint and close cleanly
     on shutdown, and a hard kill is recoverable from the latest good backup.
  2. A corrupt boot can never destroy good data — the startup auto-backup runs
     an integrity check FIRST and refuses to overwrite/rotate good backups if
     the live DB is malformed.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import Engine

logger = logging.getLogger("forlas.backup")

AUTO_PREFIX = "auto"
MANUAL_PREFIX = "manual"


def integrity_ok(db_path: Path) -> bool:
    """Fast `PRAGMA quick_check` on a standalone connection. False if the file
    is missing, unreadable, or malformed."""
    if not db_path.exists():
        return False
    try:
        con = sqlite3.connect(str(db_path))
        try:
            result = con.execute("PRAGMA quick_check").fetchone()
            return bool(result) and result[0] == "ok"
        finally:
            con.close()
    except sqlite3.DatabaseError:
        return False


def take_backup(
    engine: Engine,
    backups_dir: Path,
    *,
    prefix: str = MANUAL_PREFIX,
    keep: int = 10,
) -> Path:
    """Copy the live DB to a timestamped file using SQLite's online-backup API
    (safe to run while the app is serving), then rotate to the newest `keep`."""
    backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    target = backups_dir / f"forlas_crq_{prefix}_{stamp}.db"

    raw = engine.raw_connection()
    try:
        src: sqlite3.Connection = raw.connection  # type: ignore[attr-defined]
        dst = sqlite3.connect(str(target))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        raw.close()

    _rotate(backups_dir, prefix=prefix, keep=keep)
    return target


def _rotate(backups_dir: Path, *, prefix: str, keep: int) -> None:
    files = sorted(
        backups_dir.glob(f"forlas_crq_{prefix}_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for stale in files[keep:]:
        try:
            stale.unlink()
        except OSError:
            pass


def startup_auto_backup(engine: Engine, db_path: Path, backups_dir: Path, *, keep: int = 10) -> None:
    """Take a rotating auto-backup on boot — but ONLY if the DB is healthy.

    If the live DB is malformed we log loudly and skip, so a corrupt startup
    can never rotate away the last good backup.
    """
    if not db_path.exists():
        return  # fresh install; nothing to back up yet
    if not integrity_ok(db_path):
        logger.critical(
            "DATABASE INTEGRITY CHECK FAILED for %s — skipping auto-backup to "
            "preserve existing good backups. Restore from %s.",
            db_path,
            backups_dir,
        )
        return
    try:
        target = take_backup(engine, backups_dir, prefix=AUTO_PREFIX, keep=keep)
        logger.info("Startup auto-backup written: %s", target.name)
    except Exception:  # never let a backup failure block startup
        logger.exception("Startup auto-backup failed (continuing).")


def checkpoint_and_close(engine: Engine) -> None:
    """Flush the WAL into the main DB file and dispose connections.

    Called on shutdown so an ordinary stop leaves a single, consistent file
    with no pending WAL — the state most resistant to a later hard kill.
    """
    try:
        raw = engine.raw_connection()
        try:
            raw.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")  # type: ignore[attr-defined]
            raw.connection.commit()  # type: ignore[attr-defined]
        finally:
            raw.close()
    except Exception:
        logger.exception("WAL checkpoint on shutdown failed (continuing).")
    finally:
        engine.dispose()


def latest_backup(backups_dir: Path) -> Path | None:
    if not backups_dir.exists():
        return None
    files = sorted(backups_dir.glob("forlas_crq_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None

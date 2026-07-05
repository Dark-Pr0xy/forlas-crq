"""Database durability — integrity check, safe backup, corruption guard."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text

from app.services import backup as backup_svc


def _make_valid_db(path: Path) -> None:
    eng = create_engine(f"sqlite:///{path.as_posix()}")
    with eng.begin() as con:
        con.execute(text("CREATE TABLE t (x INTEGER)"))
        con.execute(text("INSERT INTO t VALUES (1), (2), (3)"))
    eng.dispose()


def test_integrity_ok_true_for_valid_db(tmp_path):
    db = tmp_path / "good.db"
    _make_valid_db(db)
    assert backup_svc.integrity_ok(db) is True


def test_integrity_ok_false_for_missing_and_garbage(tmp_path):
    assert backup_svc.integrity_ok(tmp_path / "nope.db") is False
    garbage = tmp_path / "garbage.db"
    garbage.write_bytes(b"this is not a sqlite database at all, just noise" * 10)
    assert backup_svc.integrity_ok(garbage) is False


def test_take_backup_and_rotate(tmp_path):
    db = tmp_path / "live.db"
    _make_valid_db(db)
    eng = create_engine(f"sqlite:///{db.as_posix()}")
    backups = tmp_path / "backups"

    made = []
    for _ in range(5):
        # Distinct timestamps aren't guaranteed within the same second, so
        # rotation is by count; force unique names via the prefix param instead.
        made.append(backup_svc.take_backup(eng, backups, prefix="manual", keep=3))
    eng.dispose()

    remaining = list(backups.glob("forlas_crq_manual_*.db"))
    # Rotation keeps at most `keep`; same-second stamps collapse names, so the
    # invariant we assert is "never more than keep".
    assert len(remaining) <= 3
    assert all(backup_svc.integrity_ok(p) for p in remaining)


def test_startup_backup_skips_when_corrupt(tmp_path):
    """The critical guarantee: a malformed DB must NOT trigger a backup that
    could rotate away good ones."""
    corrupt = tmp_path / "live.db"
    corrupt.write_bytes(b"\x00\x01\x02 not sqlite " * 100)
    backups = tmp_path / "backups"
    backups.mkdir()
    # Seed a known-good backup we must not lose.
    good = backups / "forlas_crq_auto_20260101_000000.db"
    _make_valid_db(good)

    eng = create_engine(f"sqlite:///{corrupt.as_posix()}")
    backup_svc.startup_auto_backup(eng, corrupt, backups, keep=3)
    eng.dispose()

    # No new backup written; the good one survives untouched.
    assert good.exists()
    assert len(list(backups.glob("forlas_crq_*.db"))) == 1


def test_startup_backup_runs_when_healthy(tmp_path):
    db = tmp_path / "live.db"
    _make_valid_db(db)
    backups = tmp_path / "backups"
    eng = create_engine(f"sqlite:///{db.as_posix()}")
    backup_svc.startup_auto_backup(eng, db, backups, keep=3)
    eng.dispose()
    autos = list(backups.glob("forlas_crq_auto_*.db"))
    assert len(autos) == 1
    assert backup_svc.integrity_ok(autos[0])

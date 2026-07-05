"""Build the Tauri backend sidecar binary using PyInstaller.

Produces a single self-contained exe named with the Rust target-triple suffix
that Tauri's `externalBin` mechanism requires, placed in `src-tauri/binaries/`.
Uses the committed `backend/forlas-backend.spec` so hidden imports and
bundled data (report templates) stay in one place.

Run from the repo root with the backend venv active:

    python scripts/build_backend_sidecar.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKEND = REPO / "backend"
SPEC = BACKEND / "forlas-backend.spec"
BIN_DIR = REPO / "src-tauri" / "binaries"


def _target_triple() -> str:
    out = subprocess.check_output(["rustc", "-Vv"], text=True)
    for line in out.splitlines():
        if line.startswith("host:"):
            return line.split(":", 1)[1].strip()
    raise RuntimeError("Could not determine Rust target triple (is rustc installed?)")


def main() -> None:
    if not SPEC.exists():
        raise SystemExit(f"Missing spec: {SPEC}")

    print("Ensuring PyInstaller is installed…")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pyinstaller"])

    print("Building sidecar with PyInstaller…")
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            str(SPEC),
            "--noconfirm",
            "--distpath",
            str(BACKEND / "dist"),
            "--workpath",
            str(BACKEND / "build"),
        ],
        cwd=BACKEND,
    )

    built = BACKEND / "dist" / "forlas-backend.exe"
    if not built.exists():  # non-Windows: no .exe suffix
        built = BACKEND / "dist" / "forlas-backend"
    if not built.exists():
        raise SystemExit(f"Build did not produce {built}")

    triple = _target_triple()
    suffix = ".exe" if built.suffix == ".exe" else ""
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    target = BIN_DIR / f"forlas-backend-{triple}{suffix}"
    shutil.copy2(built, target)
    print(f"Sidecar placed: {target}")


if __name__ == "__main__":
    main()

"""Entry point for the PyInstaller-bundled backend.

Tauri spawns this executable with FORLAS_DATA_DIR / FORLAS_HOST / FORLAS_PORT
already set. We boot uvicorn in-process (single process, no reload/workers —
subprocess spawning breaks in a frozen bundle).
"""

from __future__ import annotations

import multiprocessing
import os


def main() -> None:
    # Required on Windows so a frozen exe doesn't re-launch itself when any
    # dependency (numpy/scipy) touches multiprocessing.
    multiprocessing.freeze_support()

    import uvicorn

    from app.main import app  # import the object directly — frozen-import safe

    host = os.environ.get("FORLAS_HOST", "127.0.0.1")
    port = int(os.environ.get("FORLAS_PORT", "8765"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()

"""Runtime-mode helpers for frozen (PyInstaller) vs source execution.

When the backend is bundled into a single executable and launched by the Tauri
host, `sys.frozen` is set and bundled data lives under `sys._MEIPASS`. Paths
that work relative to `__file__` in source mode don't survive freezing, so
resource lookups go through `resource_path()` instead.
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    """Directory that bundled data files were unpacked to.

    Frozen: PyInstaller's temp extraction dir (`sys._MEIPASS`).
    Source: the backend package root (`.../backend`).
    """
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    # backend/app/runtime.py -> backend/
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)

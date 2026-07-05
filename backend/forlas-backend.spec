# PyInstaller spec for the FORLAS CRQ backend sidecar.
#
# Build from the backend/ directory with the venv active:
#     pyinstaller forlas-backend.spec --noconfirm
#
# Produces dist/forlas-backend/ (one-dir bundle). The build orchestration
# script (scripts/build_backend_sidecar.py) copies + renames the exe with the
# Rust target-triple suffix Tauri requires.

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# uvicorn / starlette / fastapi pull a lot in dynamically; scipy needs its
# compiled submodules discovered explicitly.
hidden = []
for pkg in ("uvicorn", "scipy", "numpy", "sqlalchemy", "sqlmodel", "passlib"):
    hidden += collect_submodules(pkg)
hidden += [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan.on",
    "argon2",
    "argon2.low_level",
    "app.models.user",
    "app.models.session",
    "app.models.scenario",
    "app.models.simulation",
    "app.models.portfolio",
    "app.models.audit",
    "app.models.approval",
    "app.models.knowledge",
    "app.models.settings",
]

# Bundle the Jinja report templates as data (resolved via app.runtime at run time).
datas = [("app/reporting/templates", "app/reporting/templates")]
datas += collect_data_files("scipy")

a = Analysis(
    ["scripts/sidecar_entry.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pytest", "PIL"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# One-file: a single self-contained exe, which is what Tauri's `externalBin`
# sidecar mechanism expects. Startup unpacks to a temp dir (a few seconds cold);
# the frontend polls /api/health so the window waits for readiness.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="forlas-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,  # keep stdout/stderr so Tauri can read backend logs
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Packaging

Delivery paths for the Beta. All produce a self-contained app with no SaaS and
no telemetry.

## 0 · Desktop app (Windows, built & verified)

The primary end-user deliverable: a double-clickable Windows installer with the
Python backend bundled inside. **No terminal, no Python, no Node required by the
end user.**

**The installer:**
`src-tauri/target/release/bundle/nsis/FORLAS CRQ_0.1.0_x64-setup.exe` (~89 MB)

**To build it (developer machine):**
```powershell
# 1. Bundle the backend into a standalone exe (PyInstaller)
E:\FORLAS-CRQ-Beta\backend\.venv\Scripts\python.exe scripts\build_backend_sidecar.py

# 2. Build the frontend
npm --prefix frontend run build

# 3. Build the Tauri installer (needs Rust + tauri-cli, both installed here)
cd src-tauri
cargo tauri build
```

**How it runs:** launching the app spawns the bundled backend sidecar on
`127.0.0.1:8765`, which boots in ~5s (the window shows "Connecting to local
backend…" until it's ready). Per-user data lives in
`%APPDATA%\app.forlas.crq\` (database, WAL, backups, reports, secret key).

**First-run login:** because the desktop app has no console, the auto-generated
owner password is written to `%APPDATA%\app.forlas.crq\FIRST_RUN_LOGIN.txt`.
Open that file, log in as `owner@local`, change the password in
Settings → Change your password. The file is deleted automatically on first login.

**Auth in the desktop app:** the WebView talks to the backend cross-origin, so
the frontend authenticates with the `X-Session-Token` header (issued by /login)
instead of a SameSite cookie. Same server-side session, same revocation.

---

The alternatives below suit server / lab contexts.

## 1 · Docker (server / lab / kiosk)

The simplest path. Requires only Docker.

```bash
docker compose up -d --build
# Open http://localhost:8765/
```

What it does:

1. Multi-stage build: Node 22 builds the frontend with `VITE_BASE_PATH=/app/`,
   then Python 3.13-slim installs the backend, with the built SPA copied into
   `/srv/static` so FastAPI serves it at `/app/`.
2. SQLite + WAL data persisted to the `forlas_data` volume (mounted at
   `/data` inside the container).
3. First-run owner credentials are printed to container stdout —
   `docker compose logs forlas-crq` to grab them, then change the password
   immediately via Settings → Users.
4. To preset the owner password instead of using the random one, set
   `FORLAS_BOOTSTRAP_OWNER_PASSWORD` in `docker-compose.yml` before the first
   start.

## 2 · Tauri (single-executable desktop)

For the SMB end-user experience: a single signed installer per OS that
embeds the Python backend as a sidecar binary.

### Prerequisites

| Tool      | Why                            | Install                                                        |
|-----------|--------------------------------|----------------------------------------------------------------|
| Rust 1.77+| Tauri host                     | https://rustup.rs                                              |
| PyInstaller | Bundles the backend sidecar  | `pip install pyinstaller` (auto-installed by the build script) |
| Node 22+  | Builds the SPA                 | https://nodejs.org                                             |
| OS toolkit| Tauri build deps (per platform)| https://tauri.app/start/prerequisites/                         |

### Build flow

```powershell
# 1. Bundle the backend into a sidecar binary
#    (writes src-tauri/binaries/forlas-backend-<target-triple>[.exe])
cd backend
.venv\Scripts\Activate.ps1
python ..\scripts\build_backend_sidecar.py

# 2. Build the Tauri installer
cd ..\src-tauri
cargo install tauri-cli --version "^2"
cargo tauri build
# Installer artefacts land under src-tauri/target/release/bundle/
```

`cargo tauri dev` is supported for live-reload development — it spawns the
backend sidecar against your dev DB and serves the Vite dev server in the
window.

### What ships in the bundle

- `forlas-backend` (PyInstaller-bundled Python interpreter + the app)
- The compiled React SPA
- The Tauri-generated platform installer (NSIS/MSI for Windows, DMG for macOS,
  AppImage/DEB for Linux)

Per-user data lives in the OS-standard app data directory:

- Windows: `%LOCALAPPDATA%\FORLAS\CRQ\`
- macOS:   `~/Library/Application Support/FORLAS/CRQ/`
- Linux:   `~/.local/share/forlas-crq/`

Backups (created via Settings → Backups) land in the same directory under
`backups/`.

## 3 · Standalone backend (advanced)

For unit-test environments or when you want to drive the API from a custom
client:

```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8765
# In another shell, run the frontend dev server:
cd ..\frontend
npm run dev
```

## Notes

- WAL is enabled and `synchronous=NORMAL` for low-latency writes. Backups use
  the SQLite online-backup API and are safe to take while the app is running.
- No external services are contacted in any path. The CSP in
  `src-tauri/tauri.conf.json` is locked to localhost + Tauri IPC.
- WeasyPrint (PDF) is intentionally opt-in (`pip install ".[pdf]"`) because
  it requires GTK on Windows. The shipped reports flow uses
  browser-print-to-PDF instead, which works everywhere.

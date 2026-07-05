# Software Bill of Materials (SBOM)

**Product:** FORLAS CRQ (Cyber Risk Quantification)
**Version:** 0.1.0
**Supplier / Author:** Michael Walker
**Package identifier:** `app.forlas.crq`
**Document date:** 2026-07-04
**Document author:** Generated from committed dependency manifests and lockfiles
**Deployment model:** Local-first desktop application (Windows 10/11 x64). Offline. No telemetry. No cloud services.

---

## 1. Purpose & scope

This SBOM enumerates the third-party software components that comprise FORLAS CRQ, for the purpose of supply-chain transparency, licence compliance and vulnerability management. It covers:

- **Shipped components** — code that is packaged into the installer and executes on the end-user machine.
- **Build/development-only components** — tooling used to produce the installer that is **not** distributed to end users (listed separately in §7 for completeness).

The application is composed of three build artifacts:

| Artifact | Technology | Role |
|---|---|---|
| `forlas-backend.exe` | Python 3.13, frozen with PyInstaller | Local FastAPI engine — Monte Carlo simulation, persistence, auth |
| Frontend bundle (`frontend/dist`) | React / TypeScript, compiled by Vite | User interface (static HTML/JS/CSS) |
| `FORLAS CRQ.exe` + NSIS installer | Rust / Tauri 2 | Desktop shell, window, WebView host, sidecar lifecycle |

**Component totals (direct + transitive, resolved):**

| Ecosystem | Resolved packages | Notes |
|---|---|---|
| Python (PyPI) | 66 | Includes build-only (PyInstaller, pytest, ruff, mypy) — see §7 |
| JavaScript (npm) | 391 | Includes dev-only (Vite, Vitest, ESLint, types) — see §7 |
| Rust (crates.io) | 441 | Tauri and its transitive graph |

> **Verification note:** Versions below are the exact resolved versions from the project lockfiles / installed environment (`package-lock.json`, `Cargo.lock`, `pip freeze`). SPDX licence identifiers are the standard published licences for each well-known project. For a formal compliance audit, regenerate the machine-readable inventory with dedicated scanners (see §9); this document is the human-readable equivalent.

---

## 2. Application artifacts (first-party)

| Component | Version | Licence | Source |
|---|---|---|---|
| FORLAS CRQ (this application) | 0.1.0 | MIT — see `LICENCE.md` | First-party |

---

## 3. Shipped runtime dependencies — Backend engine (Python 3.13)

These are frozen into `forlas-backend.exe` and distributed with the app.

| Package | Version | SPDX Licence | Purpose |
|---|---|---|---|
| fastapi | 0.138.2 | MIT | Web/API framework |
| starlette | 1.3.1 | BSD-3-Clause | ASGI toolkit (FastAPI core) |
| uvicorn | 0.49.0 | BSD-3-Clause | ASGI server (loopback) |
| h11 | 0.16.0 | MIT | HTTP/1.1 for uvicorn |
| httptools | 0.8.0 | MIT | HTTP parsing |
| websockets | 16.0 | BSD-3-Clause | WebSocket protocol |
| watchfiles | 1.2.0 | MIT | (uvicorn[standard]) file watching |
| pydantic | 2.13.4 | MIT | Data validation |
| pydantic-core | 2.46.4 | MIT | Pydantic Rust core |
| pydantic-settings | 2.14.2 | MIT | Settings management |
| annotated-types | 0.7.0 | MIT | Pydantic typing support |
| typing-inspection | 0.4.2 | MIT | Pydantic typing support |
| sqlmodel | 0.0.39 | MIT | ORM models |
| SQLAlchemy | 2.0.51 | MIT | ORM / SQL toolkit |
| greenlet | 3.5.3 | MIT | SQLAlchemy async support |
| alembic | 1.18.5 | MIT | DB migrations |
| Mako | 1.3.12 | MIT | Alembic templating |
| numpy | 2.5.0 | BSD-3-Clause | Numerical arrays (Monte Carlo) |
| scipy | 1.18.0 | BSD-3-Clause | Statistical distributions |
| argon2-cffi | 25.1.0 | MIT | Password hashing (Argon2) |
| argon2-cffi-bindings | 25.1.0 | MIT | Argon2 native bindings |
| cffi | 2.0.0 | MIT | C FFI for argon2 |
| pycparser | 3.0 | BSD-3-Clause | cffi dependency |
| itsdangerous | 2.2.0 | BSD-3-Clause | Signed tokens |
| python-multipart | 0.0.32 | Apache-2.0 | Form/upload parsing |
| httpx | 0.28.1 | BSD-3-Clause | HTTP client (internal) |
| httpcore | 1.0.9 | BSD-3-Clause | httpx transport |
| anyio | 4.14.1 | MIT | Async compatibility layer |
| sniffio | (via anyio) | MIT / Apache-2.0 | Async lib detection |
| certifi | 2026.6.17 | MPL-2.0 | CA bundle (httpx) |
| idna | 3.18 | BSD-3-Clause | IDNA handling |
| Jinja2 | 3.1.6 | BSD-3-Clause | Report templating |
| MarkupSafe | 3.0.3 | BSD-3-Clause | Jinja2 escaping |
| orjson | 3.11.9 | Apache-2.0 OR MIT | Fast JSON serialisation |
| python-docx | 1.2.0 | MIT | DOCX report generation |
| lxml | 6.1.1 | BSD-3-Clause | XML backend for python-docx |
| Pillow | 12.3.0 | MIT-CMU (HPND) | Image handling for python-docx |
| email-validator | 2.3.0 | Unlicense | Email field validation (pydantic[email]) |
| dnspython | 2.8.0 | ISC | email-validator dependency |
| click | 8.4.2 | BSD-3-Clause | uvicorn CLI |
| colorama | 0.4.6 | BSD-3-Clause | Console colour (Windows) |
| python-dotenv | 1.2.2 | BSD-3-Clause | Env file loading |
| PyYAML | 6.0.3 | MIT | Config parsing |
| typing_extensions | 4.15.0 | PSF-2.0 | Backported typing |
| tzdata | 2026.2 | Apache-2.0 | Timezone DB (Windows) |

### Bundled language runtime & standard library (Backend)

| Component | Version | Licence | Notes |
|---|---|---|---|
| CPython runtime | 3.13.x | PSF-2.0 | Embedded by PyInstaller into the sidecar exe |
| SQLite | (bundled in CPython `sqlite3`) | Public Domain | Database engine; version tied to the CPython build |

---

## 4. Shipped runtime dependencies — Frontend UI (JavaScript / TypeScript)

Direct dependencies compiled into the static frontend bundle. All rendered client-side inside the WebView; no runtime npm install occurs on the user machine.

| Package | Version | SPDX Licence | Purpose |
|---|---|---|---|
| react | 18.3.1 | MIT | UI library |
| react-dom | 18.3.1 | MIT | React DOM renderer |
| @tanstack/react-query | 5.101.2 | MIT | Server-state / data fetching |
| @tanstack/react-router | 1.170.16 | MIT | Routing |
| @tanstack/react-table | 8.21.3 | MIT | Data tables |
| zustand | 5.0.14 | MIT | Client state store |
| echarts | 5.6.0 | Apache-2.0 | Charting (LEC, histograms) |
| echarts-for-react | 3.0.6 | MIT | React wrapper for ECharts |
| motion | 11.18.2 | MIT | Animation |
| lucide-react | 0.451.0 | ISC | Icon set |
| @radix-ui/react-dialog | 1.1.17 | MIT | Accessible dialog primitive |
| @radix-ui/react-dropdown-menu | 2.1.x | MIT | Dropdown primitive |
| @radix-ui/react-label | 2.1.x | MIT | Label primitive |
| @radix-ui/react-slot | 1.1.x | MIT | Slot primitive |
| @radix-ui/react-tooltip | 1.1.x | MIT | Tooltip primitive |
| class-variance-authority | 0.7.1 | Apache-2.0 | Variant styling |
| clsx | 2.1.1 | MIT | Class name utility |
| tailwind-merge | 2.6.1 | MIT | Tailwind class merging |
| tailwindcss-animate | 1.0.7 | MIT | Tailwind animation utilities |

> Tailwind CSS itself (see §7) is a build-time tool: it compiles to the static CSS shipped in the bundle, but the `tailwindcss` package is not distributed.

---

## 5. Shipped runtime dependencies — Desktop shell (Rust / Tauri)

Key direct crates compiled into `FORLAS CRQ.exe`. Full transitive graph = 441 crates (`Cargo.lock`); the load-bearing components are:

| Crate | Version | SPDX Licence | Purpose |
|---|---|---|---|
| tauri | 2.11.5 | Apache-2.0 OR MIT | Desktop app framework |
| tauri-build | 2.6.3 | Apache-2.0 OR MIT | Build-time codegen |
| tauri-runtime | 2.11.3 | Apache-2.0 OR MIT | Runtime abstraction |
| tauri-plugin-shell | 2.3.5 | Apache-2.0 OR MIT | Sidecar process spawning |
| wry | 0.55.1 | Apache-2.0 OR MIT | WebView abstraction |
| tao | 0.35.3 | Apache-2.0 | Windowing |
| webview2-com | 0.38.2 | Apache-2.0 OR MIT | WebView2 COM bindings |
| windows | 0.61.3 | Apache-2.0 OR MIT | Windows API bindings |
| tokio | 1.52.3 | MIT | Async runtime |
| serde | 1.0.228 | Apache-2.0 OR MIT | Serialisation |
| serde_json | 1.0.150 | Apache-2.0 OR MIT | JSON |

---

## 6. Platform / external runtime prerequisites (not bundled)

These are provided by the operating system and are **not** redistributed inside the installer.

| Component | Provider | Licence | Requirement |
|---|---|---|---|
| Windows 10 / 11 (x64) | Microsoft | Proprietary (OS EULA) | Required OS |
| Microsoft Edge WebView2 Runtime | Microsoft | Proprietary (MS distributable) | Renders the UI. Pre-installed on Windows 11 and current Windows 10. Installed separately if absent. |
| Microsoft Visual C++ runtime | Microsoft | Proprietary (redistributable) | Present on supported Windows versions |

---

## 7. Build & development-only components (NOT shipped)

Used to compile/test/package the product. These do **not** ship in the installer and do not execute on end-user machines. Listed for supply-chain completeness.

**Python (build/test):** pyinstaller 6.21.0, pyinstaller-hooks-contrib 2026.6, pefile 2024.8.26, altgraph 0.17.5, pywin32-ctypes 0.2.3, setuptools 82.0.1, packaging 26.2, pytest 9.1.1, pytest-asyncio 1.4.0, pytest-cov 7.1.0, coverage 7.14.3, pluggy 1.6.0, iniconfig 2.3.0, ruff 0.15.20, mypy 2.1.0, mypy_extensions 1.1.0, pathspec 1.1.1, Pygments 2.20.0.

**JavaScript (dev/build):** vite 5.4.21, vitest 2.1.9, typescript 5.9.3, typescript-eslint 8.10.x, eslint 9.13.x, eslint-plugin-react-hooks 5.0.x, eslint-plugin-react-refresh 0.4.x, @vitejs/plugin-react 4.3.x, tailwindcss 3.4.19, autoprefixer 10.4.x, postcss 8.4.x, prettier 3.3.x, @tanstack/router-devtools 1.79.x, @types/node, @types/react, @types/react-dom.

**Optional (not enabled in default build):** weasyprint (≥63) — PDF export; requires GTK on Windows and is intentionally opt-in. Not present in the shipped installer.

---

## 8. Licence summary

The distributed components are predominantly permissive open-source licences compatible with proprietary redistribution:

| Licence family | Representative components |
|---|---|
| MIT | React, FastAPI, SQLAlchemy, python-docx, tokio, most npm/PyPI packages |
| BSD-3-Clause | NumPy, SciPy, uvicorn, starlette, httpx, Jinja2 |
| Apache-2.0 | ECharts, orjson, python-multipart, tzdata |
| Apache-2.0 OR MIT (dual) | Tauri, wry, serde, Windows crates |
| ISC | lucide-react, dnspython |
| MPL-2.0 | certifi (CA bundle) |
| PSF-2.0 | CPython, typing_extensions |
| Public Domain | SQLite |
| Proprietary | FORLAS CRQ (first-party), WebView2 / Windows (platform) |

**Compliance observations:**
- No copyleft licences (GPL/AGPL/LGPL) are present in the shipped dependency set.
- **MPL-2.0** (certifi) and **Apache-2.0** are file/component-level and permit proprietary distribution provided notices are preserved.
- Attribution obligations (MIT/BSD/Apache/ISC) are satisfied by retaining licence texts; a consolidated `THIRD-PARTY-NOTICES` file is recommended for distribution (see §9).

---

## 9. Regenerating a machine-readable SBOM

For formal audit or ingestion into a vulnerability scanner, generate SPDX / CycloneDX documents directly from the toolchains:

```bash
# Python (CycloneDX)
pip install cyclonedx-bom
cd backend && cyclonedx-py environment --of json -o sbom-python.json

# JavaScript (CycloneDX)
npx @cyclonedx/cyclonedx-npm --output-file sbom-npm.json
# (run inside frontend/)

# Rust (CycloneDX)
cargo install cargo-cyclonedx
cd src-tauri && cargo cyclonedx --format json

# Consolidated third-party licence notices
pip install pip-licenses && pip-licenses --format=plain-vertical --with-license-file   # Python
npx license-checker --production --out THIRD-PARTY-JS.txt                              # JS
cargo install cargo-about && cargo about generate about.hbs > THIRD-PARTY-RUST.html    # Rust
```

---

## 10. Attestations

- **No telemetry / analytics** components are included. The application makes **no outbound network calls** in normal operation; the backend binds to loopback (`127.0.0.1:8765`) only.
- **No cloud SDKs** (AWS/Azure/GCP), tracking, crash-reporting, or advertising libraries are present in the shipped set.
- All data is stored locally in a SQLite database under the user's `%APPDATA%` directory.

---

*This SBOM reflects the dependency state at document date and version 0.1.0. Regenerate on each release. For discrepancies, the authoritative sources are `backend/pyproject.toml`, `frontend/package-lock.json`, and `src-tauri/Cargo.lock`.*

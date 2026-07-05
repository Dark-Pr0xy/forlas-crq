# Third-Party Notices

FORLAS CRQ is licensed under the MIT License (see `LICENCE.md`). The application
and its installer **bundle and redistribute third-party open-source components**,
each of which remains licensed under its own terms. Those terms, and the required
copyright and permission notices, are preserved and reproduced here and in the
per-package licence files produced by the regeneration commands in §5.

Nothing in FORLAS CRQ's MIT License limits your rights under the licences of the
bundled third-party components.

**Document date:** 2026-07-05 · Full machine-readable inventory: [`SBOM.md`](./SBOM.md)

---

## 1. What is bundled

| Layer | Contents | Where the inventory lives |
|---|---|---|
| Backend sidecar (`forlas-backend.exe`) | The CPython 3.13 runtime + Python packages (FastAPI, Starlette, Uvicorn, Pydantic, SQLAlchemy/SQLModel, Alembic, NumPy, SciPy, argon2-cffi, Jinja2, python-docx, orjson, and their dependencies), frozen with PyInstaller. Includes SQLite via CPython's `sqlite3`. | SBOM.md §3 |
| Frontend bundle | React, React-DOM, TanStack Query/Router/Table, ECharts, Radix UI, Zustand, Motion, Lucide, and build-time Tailwind output. | SBOM.md §4 |
| Desktop shell (`FORLAS CRQ.exe`) | Rust crates: Tauri, wry, tao, webview2-com, tokio, serde, and the transitive graph. | SBOM.md §5 |

Full resolved versions and SPDX identifiers for every component are in `SBOM.md`.

## 2. Licences present in the shipped build

The redistributed (shipped) components are under permissive licences:

- **MIT** — most Python and JavaScript packages (full text in §4).
- **BSD-3-Clause / BSD-2-Clause** — NumPy, SciPy, Uvicorn, Starlette, httpx, Jinja2, and others (full text in §4).
- **Apache-2.0** — ECharts, orjson, python-multipart, tzdata, the Tauri crates (dual Apache-2.0 OR MIT). Full text: https://www.apache.org/licenses/LICENSE-2.0
- **ISC** — lucide-react, dnspython (full text in §4).
- **MPL-2.0** — `certifi` (the CA bundle). MPL-2.0 is file-level copyleft and permits distribution within a larger MIT-licensed work provided the covered file's source remains available; certifi's source is published at https://github.com/certifi/python-certifi and its licence at https://www.mozilla.org/MPL/2.0/
- **PSF-2.0** — the bundled CPython runtime and `typing_extensions`. https://docs.python.org/3/license.html
- **Public Domain** — SQLite. https://www.sqlite.org/copyright.html

**No GPL/AGPL/LGPL copyleft is present in the shipped set**, so FORLAS CRQ's own MIT licensing is not affected by what it bundles.

### A note on PyInstaller (build tool, not shipped as a library)

PyInstaller is GPL-2.0‑licensed **but is a build tool**, not a distributed component. The only PyInstaller code embedded in the frozen backend is its *bootloader*, which carries an explicit **exception permitting the bundled application to be distributed under any licence of your choosing**. FORLAS CRQ's MIT licensing is therefore unaffected. See https://pyinstaller.org/en/stable/license.html

## 3. Attribution

Copyright in each bundled component remains with its respective authors. Their
copyright notices and licence texts are retained in the installed package
distributions and are reproduced by the regeneration commands in §5. This file,
together with `SBOM.md` and the generated per-package licence files, constitutes
the notice required by the MIT/BSD/Apache/ISC licences of the bundled components.

## 4. Canonical licence texts

The bundled MIT/BSD/ISC components are covered by the standard texts below.
Individual copyright lines for each component are preserved in that component's
own `LICENSE`/`METADATA` file within the distribution and in the generated output
of §5.

### MIT License

```
Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in the
Software without restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN
AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

### BSD 3-Clause License

```
Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice, this
   list of conditions and the following disclaimer in the documentation and/or
   other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors may
   be used to endorse or promote products derived from this software without
   specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

### ISC License

```
Permission to use, copy, modify, and/or distribute this software for any purpose
with or without fee is hereby granted, provided that the above copyright notice
and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT,
OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE,
DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS
SOFTWARE.
```

Apache-2.0 and MPL-2.0 full texts are at the URLs given in §2.

## 5. Regenerating authoritative per-package notices

Before each public release, regenerate the authoritative, per-package licence
files (which capture each component's individual copyright lines) and commit them:

```bash
# Python runtime components
pip install pip-licenses
cd backend && pip-licenses --format=plain-vertical --with-license-file --no-license-path --output-file ../THIRD-PARTY-python.txt

# JavaScript components (run in frontend/)
npx license-checker --production --out ../THIRD-PARTY-js.txt

# Rust crates (run in src-tauri/)
cargo install cargo-about
cargo about generate about.hbs > ../THIRD-PARTY-rust.html
```

Commit `THIRD-PARTY-python.txt`, `THIRD-PARTY-js.txt`, and `THIRD-PARTY-rust.html`
alongside this file. They are the machine-verified evidence of compliance; this
document is the human-readable summary.

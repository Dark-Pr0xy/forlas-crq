# User Acceptance Testing (UAT) Plan

**Product:** FORLAS CRQ — Local-first Quantitative Cyber Risk Platform
**Version under test:** 0.1.0
**Platform:** Windows 10 / 11 (x64), desktop installer
**Document date:** 2026-07-04
**Author:** Michael Walker

---

## Document control

| Field | Value |
|---|---|
| Installer under test | `FORLAS CRQ_0.1.0_x64-setup.exe` |
| Data location | `%APPDATA%\app.forlas.crq\` |
| Backend endpoint (internal) | `http://127.0.0.1:8765` (loopback only) |
| Test data policy | Use a throwaway install / user; math cases are self-contained |

### Sign-off

| Role | Name | Signature | Date | Result (Accept / Reject) |
|---|---|---|---|---|
| Tester | | | | |
| Reviewer | | | | |
| Product owner | Michael Walker | | | |

---

## 1. Purpose & scope

This plan verifies that FORLAS CRQ is fit for purpose from a user's perspective — that it installs, runs offline, quantifies cyber risk correctly, and produces trustworthy outputs.

**Special emphasis (Section 6):** because this is a quantitative risk tool, the **mathematics must be independently verifiable**, not merely "looks plausible". Section 6 provides a repeatable method to prove the Monte Carlo engine produces correct results using hand-computable analytical cases and an independent recomputation of the exported data.

**In scope:** installation, authentication, scenario modelling, simulation engine correctness, charts, register/portfolio aggregation, reporting/exports, governance, settings, durability, offline/no-telemetry behaviour, performance.

**Out of scope:** source-code review, load/stress testing beyond single-user desktop use, penetration testing.

---

## 2. Test environment & prerequisites

| Item | Requirement |
|---|---|
| Operating system | Windows 10 or 11, 64-bit |
| WebView2 Runtime | Present (default on Win 11 / current Win 10) |
| Disk | ~300 MB free for install + database |
| Spreadsheet tool | Microsoft Excel **or** Python/pandas — required for Section 6 math recomputation |
| Network | **Disconnect from the network** for Section 10 (offline verification) |

No Rust, Node, Python, or database engine needs to be installed — all are bundled (see `SBOM.md`).

---

## 3. Entry & exit criteria

**Entry criteria**
- Signed installer available and runs without SmartScreen block (or block acknowledged).
- Clean or known-good `%APPDATA%\app.forlas.crq\` state.

**Exit criteria (acceptance)**
- 100% of **Critical** test cases (marked 🔴) PASS.
- ≥ 95% of **High** (🟠) cases PASS with no open Critical defect.
- **All Section 6 math cases PASS** — this is a hard gate; any math failure blocks acceptance.
- All seven prior UAT regressions (Section 11) confirmed fixed.

---

## 4. How to record results

For each case record: **Actual result**, **Pass/Fail**, **Date/Tester**, and a **Defect ID** if failed. Log defects in Section 12.

Severity legend: 🔴 Critical · 🟠 High · 🟡 Medium · ⚪ Low.

---

## 5. Functional test cases

### 5.1 Installation & first run

| ID | Sev | Objective | Steps | Expected result | P/F |
|---|---|---|---|---|---|
| INST-01 | 🔴 | Clean install | Run the installer on a machine without a prior install | Installs; desktop/Start shortcut created; app launches | |
| INST-02 | 🔴 | First-run backend start | Launch app first time | Window shows "Connecting to local backend…", then loads the login/register screen within ~5–15s (no permanent hang) | |
| INST-03 | 🟠 | First-run credentials | On first run, retrieve `%APPDATA%\app.forlas.crq\FIRST_RUN_LOGIN.txt` | File contains the generated owner username + password | |
| INST-04 | 🟠 | Credential file cleanup | Log in successfully with those credentials | `FIRST_RUN_LOGIN.txt` is deleted after first successful login | |
| INST-05 | 🟡 | Upgrade over existing install | Install a new build over an existing one | App upgrades; existing database and users preserved | |

### 5.2 Authentication & users

| ID | Sev | Objective | Steps | Expected result | P/F |
|---|---|---|---|---|---|
| AUTH-01 | 🔴 | Valid login | Log in with owner credentials | Access granted; dashboard loads | |
| AUTH-02 | 🔴 | Invalid login | Wrong password | Rejected with a clear message; no internal server error | |
| AUTH-03 | 🟠 | Register additional user | Create a second user via Register | New user can log in | |
| AUTH-04 | 🟠 | Session persistence | Close and reopen the app | Session behaves per design (re-auth or resume); no crash | |
| AUTH-05 | 🟠 | Logout | Log out | Returned to login; protected pages inaccessible | |

### 5.3 Scenario / risk modelling (Workspace)

| ID | Sev | Objective | Steps | Expected result | P/F |
|---|---|---|---|---|---|
| WS-01 | 🔴 | Create blank scenario | Workspace → New → **Starting point = "Blank (unassigned)"** | Scenario created with **no forced template**; all inputs zero/empty | |
| WS-02 | 🟡 | Create from template | New → choose a template (e.g. Ransomware) | Fields pre-populated with that template | |
| WS-03 | 🔴 | Enter distributions | Set each input's distribution (PERT/Triangular/Uniform/etc.) + parameters | Inputs accept values; validation blocks impossible ones (e.g. min>max) with a clear message | |
| WS-04 | 🔴 | Zero-value inputs allowed | Set secondary loss (SLM) and secondary probability (SLP) anchors to 0 | Accepted (no "must be > 0" block); see MATH-11 | |
| WS-05 | 🟠 | Switch decomposition mode | Toggle LEF / TEF-Vuln / Full modes | Input set changes appropriately for each mode | |
| WS-06 | 🟠 | Page scrolls | On Workspace with results shown, scroll the page | Full page scrolls; nothing clipped | |
| WS-07 | 🟠 | Save & reopen scenario | Save, navigate away, reopen | All inputs persisted exactly | |

### 5.4 Simulation run controls

| ID | Sev | Objective | Steps | Expected result | P/F |
|---|---|---|---|---|---|
| SIM-01 | 🔴 | Run simulation | Set Iterations (e.g. 100,000) + Seed, click Run | Completes in a few seconds; results panel populates | |
| SIM-02 | 🟠 | Iteration count respected | Run at 10,000 then 200,000 | Reported iteration count matches; larger n = smoother charts | |
| SIM-03 | 🔴 | Seed is honoured | Run twice with the **same** seed, no input changes | Identical results (see MATH-07) | |

### 5.5 Charts & visualisation

| ID | Sev | Objective | Steps | Expected result | P/F |
|---|---|---|---|---|---|
| CHART-01 | 🟠 | LEC renders to the axis | View Loss Exceedance Curve | Curve starts at the left axis wall (no floating gap) | |
| CHART-02 | 🟠 | LEC cursor is smooth | Move cursor along the LEC, incl. 500k–1M region | Readout tracks continuously; **no snapping/jumping** | |
| CHART-03 | 🟡 | Histogram alignment | Hover histogram bars | Measuring line centres on each bucket | |
| CHART-04 | 🟠 | Reference lines editor | Toggle P5/P50/P90/P95/P99/Tolerance; add a **custom** line (label/value/colour); use preset buttons (Insurance retention/limit, Capital reserve) | Lines appear on the LEC at the correct x-values with correct colours/labels | |
| CHART-05 | 🟡 | Currency formatting | Inspect all monetary values | Displayed as **AUD** everywhere; no USD anywhere | |

### 5.6 Register & portfolio

| ID | Sev | Objective | Steps | Expected result | P/F |
|---|---|---|---|---|---|
| REG-01 | 🟠 | Register lists scenarios | Open Quantified Exposure Register | Saved scenarios listed with key stats | |
| REG-02 | 🟠 | Portfolio aggregation | Dashboard portfolio view across ≥2 scenarios | Aggregate LEC/metrics reflect all included scenarios | |
| REG-03 | 🟡 | Risk appetite line | Set an appetite value | Appetite marker shown on portfolio LEC | |

### 5.7 Reports & data export

| ID | Sev | Objective | Steps | Expected result | P/F |
|---|---|---|---|---|---|
| RPT-01 | 🔴 | DOCX report | Reports → download DOCX | File downloads; **opens in Word without "corrupt" prompt**; contains the scenario data | |
| RPT-02 | 🟠 | HTML report | Download/print HTML report | Renders correctly; print-to-PDF works | |
| RPT-03 | 🔴 | CSV export not empty | Sim Data → Export CSV | File contains header `iteration,loss,lef` + one row **per iteration** (not empty) | |
| RPT-04 | 🟠 | JSON export | Export JSON | Valid JSON with the simulation payload | |

### 5.8 Governance

| ID | Sev | Objective | Steps | Expected result | P/F |
|---|---|---|---|---|---|
| GOV-01 | 🟡 | Audit trail | Perform actions, open Audit & Approvals | Actions recorded with user + timestamp | |
| GOV-02 | 🟡 | Approvals workflow | Submit a scenario for approval | State transitions per design | |

### 5.9 Settings

| ID | Sev | Objective | Steps | Expected result | P/F |
|---|---|---|---|---|---|
| SET-01 | 🟡 | Default iterations/seed | Change defaults in Settings | New runs use the updated defaults | |
| SET-02 | ⚪ | Navigation | Confirm Threats/Controls/Benchmarks removed from sidebar | Those items are gone; remaining nav works | |

---

## 6. Mathematical validation (engine correctness) — **mandatory gate**

This section proves the Monte Carlo engine computes the correct answer. It does **not** rely on eyeballing charts.

### 6.1 The model being tested

Per iteration the engine draws a number of loss events from **Poisson(λ)**, where λ is the Loss Event Frequency, and sums each event's loss. Each event loss = Primary Loss Magnitude **plus** Secondary Loss (which occurs only when a random draw falls below the Secondary Loss Probability).

By the expectation of a compound-Poisson sum (Wald's identity), the **true mean annual loss** is:

> **E[Annual Loss] = E[LEF] × ( E[PLM] + E[SLP] × E[SLM] ) × (1 − reduction% / 100)**

For **TEF-Vuln** mode, `E[LEF] = E[TEF] × E[Vuln]` (they are sampled independently).

This closed form is the anchor: for chosen inputs we can compute the expected mean **by hand**, then confirm the simulation converges to it.

### 6.2 Distribution means (for hand-computing E[·])

| Distribution | Parameters | Mean |
|---|---|---|
| **Point** (degenerate) | min = mode = max = *v* | *v* |
| **PERT** | min *a*, mode *m*, max *b* | (a + 4m + b) / 6 |
| **Triangular** | min *a*, mode *m*, max *b* | (a + m + b) / 3 |
| **Uniform** | min *a*, max *b* | (a + b) / 2 |

> Use **Point values** (set min = mode = max) to make a scenario fully hand-computable; use **PERT** cases to prove the distribution sampling itself is correct.

### 6.3 Why "within a tolerance", not exact

A Monte Carlo mean is an estimate; its sampling error shrinks as iterations rise (≈ proportional to 1/√n). **Run all math cases at 100,000 iterations.** Expected pass band is stated per case (typically ±2%). If a case is marginal, raise iterations to 500,000 — a correct engine converges *toward* the analytical value; a wrong one does not.

### 6.4 Analytical test cases

> ⚠️ **Start every case from a FRESH scenario** — New → **Blank (unassigned)** — and set **only** the fields listed. Do **not** edit a previous case's scenario in place: leftover PLM / secondary values carry over and silently corrupt the result (this is the most common false failure). Every field the mode uses is listed explicitly below; anything shown as `0` **must be entered as 0**, not left at a default.

All distributions are **Point (min = mode = max)** unless the row says PERT. Iterations = 100,000, Reduction = 0% unless stated.

**Fields per mode** (set all of them):
- **LEF mode:** LEF · PLM · SLP (secondary probability) · SLM (secondary magnitude)
- **TEF-Vuln mode:** TEF · Vuln · PLM · SLP · SLM

| ID | Sev | Mode | Full inputs (set every field) | Hand calculation | Expected **Mean** | Band | Actual | P/F |
|---|---|---|---|---|---|---|---|---|
| **MATH-01** | 🔴 | LEF | LEF 2 · PLM 100,000 · **SLP 0** · **SLM 0** | 2 × 100,000 | **$200,000** | ±2% | | |
| **MATH-02** | 🔴 | LEF | LEF 1 · PLM 500,000 · SLP 1 · SLM 250,000 | 1 × (500,000 + 1×250,000) | **$750,000** | ±2% | | |
| **MATH-03** | 🔴 | TEF-Vuln | TEF 4 · Vuln 0.25 · PLM 300,000 · **SLP 0** · **SLM 0** | (4 × 0.25) × 300,000 | **$300,000** | ±2% | | |
| **MATH-04** | 🔴 | LEF | LEF = PERT(1,4,10) · PLM = PERT(100k,200k,300k) · **SLP 0** · **SLM 0** | mean LEF 4.5 × mean PLM 200,000 | **$900,000** | ±3% | | |
| **MATH-05** | 🟠 | LEF | LEF 1 · PLM 400,000 · SLP 0.5 · SLM 200,000 | 1 × (400,000 + 0.5×200,000) | **$500,000** | ±2% | | |
| **MATH-06** | 🔴 | LEF | MATH-01 inputs (LEF 2 · PLM 100,000 · SLP 0 · SLM 0) **+ Reduction 40%** | 200,000 × (1 − 0.40) | **$120,000** | ±2% | | |

> The mean is shown in the results panel as **ALE**. Compute the hand value, confirm it lands inside the band.
>
> **Cross-check the shape too:** for a point-value case with no secondary (e.g. MATH-03) the P95 should be ≈ 3× the mean (≈ A$900K for MATH-03) and roughly **37% of iterations should be zero-loss** (a Poisson(1) property). If your P95 is much higher or ALE ≈ a *different* case's answer, you have leftover fields — reset and re-enter from Blank.

### 6.5 Determinism & stability

| ID | Sev | Objective | Method | Expected | Actual | P/F |
|---|---|---|---|---|---|---|
| **MATH-07** | 🔴 | Reproducible | Run any scenario twice with **the same seed**, no changes | Mean, P50, P95, P99 identical to the cent | | |
| **MATH-08** | 🟠 | Seed-stable | Same scenario, seed 42 vs seed 7 | Means differ < 2%; distribution shape unchanged | | |

### 6.6 Independent recomputation of the exported data — **the key method** 🔴

This proves the displayed statistics faithfully summarise the underlying simulated data (no display/rounding bug between engine and UI).

**MATH-09 steps:**
1. Run any scenario at 100,000 iterations. **Record** the displayed **Mean** and **P95**.
2. Go to **Monte Carlo Simulation Data → Export CSV**. Open the file (columns: `iteration, loss, lef`).
3. **Mean check (exact):** compute `AVERAGE(loss column)`.
   - ✅ Must equal the displayed Mean (they are computed from the identical numbers — expect an exact match to displayed precision).
4. **P95 check:** the engine uses the nearest-rank method — the value at 0-indexed position `floor(0.95 × n)` of the ascending-sorted losses.
   - Quick check: `PERCENTILE.INC(loss range, 0.95)` should match within one data point.
   - Exact check: sort ascending, take the value at row `FLOOR(0.95 × count) + 1`. Must equal the displayed P95.
5. **Row-count check:** the CSV must contain exactly one data row per iteration (100,000).

| Check | Expected | Actual | P/F |
|---|---|---|---|
| CSV mean = displayed mean | Exact match | | |
| CSV P95 ≈ displayed P95 | Match within one rank | | |
| Row count = iterations | 100,000 | | |

> Python equivalent: `import pandas as pd; d = pd.read_csv('losses.csv'); d['loss'].mean(); d['loss'].quantile(0.95)`.

### 6.7 Internal-consistency & sanity checks

| ID | Sev | Objective | Method | Expected | Actual | P/F |
|---|---|---|---|---|---|---|
| **MATH-10** | 🟠 | Percentiles monotone | Inspect the stats panel | P5 ≤ P25 ≤ P50 ≤ P75 ≤ P90 ≤ P95 ≤ P99; Mean within [P5, P99]; Tail-mean(95) ≥ P95 | | |
| **MATH-11** | 🔴 | Zero secondary (regression) | Set SLP=0 and SLM=0 anchors, run | Runs cleanly; total loss driven by primary only; secondary contribution = 0 | | |
| **MATH-12** | 🟠 | Frequency monotonicity | Take MATH-01, double LEF to 4, re-run | Mean ≈ doubles → ~$400,000 (±3%) | | |
| **MATH-13** | 🟠 | Tolerance ↔ exceedance | Use a **continuous** loss scenario so the P90 doesn't land on a point mass: LEF = PERT(2, 4, 8) · **PLM = Lognormal (min 50,000, max 500,000)** · SLP 0 · SLM 0. Run once, note the displayed **P90**, set **Tolerance = that P90**, re-run (same seed). | "P(Loss > Tolerance)" reads ≈ **10%** (±1.5%) | | |

> ⚠️ **Do not run MATH-13 on a point-value scenario.** With point inputs the loss distribution is *discrete* (losses fall on exact multiples), so the P90 sits **on** a probability mass. The engine reports **strict** exceedance — P(Loss **>** Tolerance) — which correctly treats a loss sitting *exactly* at tolerance as "within tolerance", not a breach. On a point mass that makes the reading materially **below** 10% (e.g. LEF 4 / PLM 100k → P90 = A$700K carries a ~6% mass, so P(L>700K) ≈ 5% while P(L≥700K) ≈ 11%). This is correct behaviour, not a defect. The continuous scenario above avoids the mass and yields a clean ~10%.

**Section 6 acceptance:** every 🔴 math case must PASS. Any failure blocks release and is logged as Critical.

---

## 7. Data durability & recovery

| ID | Sev | Objective | Steps | Expected result | P/F |
|---|---|---|---|---|---|
| DUR-01 | 🔴 | Data persists across restart | Create data, fully close app, reopen | All data present | |
| DUR-02 | 🟠 | Graceful shutdown | Close app while idle | No corruption on next launch; login works | |
| DUR-03 | 🟠 | Auto-backup exists | After use, check the app data folder | A backup copy of the database is present | |
| DUR-04 | 🟡 | Abrupt termination | Kill the app process, relaunch | App recovers; if the live DB is damaged, backup preserves prior data | |

---

## 8. Concurrency (multi-user local)

| ID | Sev | Objective | Steps | Expected result | P/F |
|---|---|---|---|---|---|
| CON-01 | 🟡 | Two users, same install | Log in as user A, make changes; log in as user B | Each sees appropriate data; no cross-corruption | |

---

## 9. Performance

| ID | Sev | Objective | Target | Actual | P/F |
|---|---|---|---|---|---|
| PERF-01 | 🟠 | Backend cold start | Window usable within ~15s of first launch | | |
| PERF-02 | 🟠 | Simulation speed | 100,000 iterations completes in a few seconds | | |
| PERF-03 | 🟡 | UI responsiveness | Charts/tables interact without noticeable lag | | |

---

## 10. Offline & privacy (no telemetry) — **disconnect the network for this section**

| ID | Sev | Objective | Steps | Expected result | P/F |
|---|---|---|---|---|---|
| OFF-01 | 🔴 | Runs fully offline | Disable Wi-Fi/Ethernet, launch and use every feature incl. simulation + reports | All functionality works with no network | |
| OFF-02 | 🟠 | No outbound calls | (Optional) Watch a firewall/Resource Monitor while using the app | No outbound connections beyond loopback `127.0.0.1:8765` | |
| OFF-03 | 🟡 | Local storage only | Confirm data lives under `%APPDATA%\app.forlas.crq\` | Data is local; nothing sent externally | |

---

## 11. Regression checklist (previously reported issues)

Confirm each earlier fix still holds:

| # | Prior issue | Verify via | P/F |
|---|---|---|---|
| R1 | First-run hung at "Connecting to backend" | INST-02 | |
| R2 | New scenario forced a preset | WS-01 | |
| R3 | LEF/secondary fields couldn't be 0 | WS-04, MATH-11 | |
| R4 | CSV export was empty | RPT-03, MATH-09 | |
| R5 | Lost ability to add custom LEC markers | CHART-04 | |
| R6 | LEC jumped between 500k–1M (not smooth) | CHART-02 | |
| R7 | Removed Threats/Controls/Benchmarks | SET-02 | |
| R8 | DOCX reports were corrupt | RPT-01 | |

---

## 12. Defect log

| Defect ID | Test ID | Severity | Description | Steps to reproduce | Status |
|---|---|---|---|---|---|
| | | | | | |

---

## 13. Test summary

| Metric | Count |
|---|---|
| Total cases | |
| Passed | |
| Failed | |
| Blocked | |
| Critical (🔴) failures | |
| **Math (Section 6) failures** | |

**Recommendation:** ☐ Accept ☐ Accept with conditions ☐ Reject

---

*Re-run the full plan on each release. Section 6 (math) and Section 11 (regressions) are mandatory every time; the remaining sections may be risk-based on minor patches.*

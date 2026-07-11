# Changelog

All notable changes to FORLAS CRQ are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-07-11

### Added

- **Analysis & Evidence** area (new item under "Analyse"). Capture the reasoning
  behind each scenario's numbers: an analysis narrative and overall confidence,
  the data and evidence relied upon, the assumptions made, the gaps and
  limitations, and a short rationale for each FAIR input. Saves are recorded in
  the audit log, and the Workspace links straight to the selected scenario's
  analysis.
- **Customisable card layouts.** Dashboard cards and the workspace side panels
  can be dragged into any order using the grip handle on each card. Cards
  reorder live under the pointer while dragging, so the drop position is
  always visible. The arrangement is saved per machine, with a "Reset layout"
  control to restore the default. (Implemented with pointer tracking rather
  than native drag-and-drop, which the desktop WebView blocks.)
- **Segregation of duties on approvals.** The person who submits a scenario for
  review can no longer approve it; a separate approver is required. The control
  is on by default and can be turned off (Settings, Governance) for single-user
  installs.
- **Approval stage indicator.** A Draft, Submitted, Approved stepper on the
  approval panel.
- **Scenario type picker.** The scenario type is now a dropdown of pre-canned
  categories (Ransomware, Insider Threat, Cloud Misconfiguration, and more) with
  the ability to add and persist your own.
- **FORLAS branding** applied to the sign-in and first-run screens and to the
  executive and board report covers (HTML/PDF and Word), using the transparent
  FORLAS brand tile.

### Fixed

- Closing the app now shuts down the bundled backend process completely.
  Previously the server process could linger after exit, keeping port 8765
  occupied and blocking installer upgrades with an "error opening file for
  writing" message.
- Non-owner users can now change their own password from Settings (the
  backend previously rejected it).
- The last active owner can no longer be demoted or deactivated, which would
  have left the install without user management.
- Analysis & evidence writes now follow the same ownership rules as scenario
  edits, and are locked once a scenario is approved or archived.

### Changed

- "In review" now reads as "Submitted" throughout the approval UI.
- Approval errors now surface the exact reason (for example, the
  separation-of-duties conflict) instead of a generic message.

### Removed

- The unused **Benchmark group** scenario field has been retired. It was
  populated by the demo data but never drove any feature. Existing values are
  dropped by a database migration.

## [0.1.0] - 2026-07-05

### Added

- Initial public Beta of FORLAS CRQ: a local-first, offline, no-cloud,
  no-telemetry quantitative cyber risk platform built on FAIR and Monte Carlo
  simulation.
- Scenario workspace, Monte Carlo engine, portfolio aggregation, and Loss
  Exceedance Curves.
- Quantified exposure register, executive and board reporting (HTML/PDF and
  Word), governance (audit log, approvals, review scheduling), and a knowledge
  library of threats, controls, and benchmarks.
- First-run local account creation; Argon2-hashed local accounts with
  role-based access control.
- Tauri desktop packaging (primary) and a Docker Compose deployment option.

[Unreleased]: https://github.com/Dark-Pr0xy/forlas-crq/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Dark-Pr0xy/forlas-crq/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Dark-Pr0xy/forlas-crq/releases/tag/v0.1.0

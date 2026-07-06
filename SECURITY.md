# Security Policy

## Security model

FORLAS CRQ is a **local-first, offline desktop application**. Understanding the model sets expectations for what is — and isn't — a vulnerability:

- The backend binds to **loopback only** (`127.0.0.1:8765`) and runs as a child process of the desktop app. It is not exposed to the network.
- There is **no telemetry, no cloud, and no external network calls** in normal operation. Your data never leaves the machine.
- All data — user accounts (passwords hashed with Argon2), scenarios, reports, backups, and a persistent signing key — lives in a local SQLite database under the per-user application data directory (`%APPDATA%\app.forlas.crq\` on Windows).
- Multi-user support is **local** (accounts on a single machine), not a network service.

Because the app is local-first, some things are **by design, not vulnerabilities**:

- A person with operating-system access to the machine/user profile can read the SQLite database and the data directory. Protecting the host is the deployer's responsibility (OS account security, full-disk encryption).
- The loopback API trusts the authenticated local session; it is not hardened against other processes running as the *same* OS user.

## Supported versions

FORLAS CRQ is pre-1.0 and maintained on a best-effort basis. Security fixes are applied to the **latest release** only; there is no back-porting.

| Version | Supported |
|---|---|
| Latest release | ✅ |
| Older releases | ❌ |

## Reporting a vulnerability

**Please do not open a public issue for a security vulnerability.**

Report it privately via either:

1. **GitHub Private Vulnerability Reporting** (preferred) — use the **"Report a vulnerability"** button under this repository's **Security** tab. *(Maintainer: enable this in Settings → Code security and analysis.)*
2. **Email** — 48585753+RiskByDesign@users.noreply.github.com

3. Please include:
- A description of the issue and its impact.
- Steps to reproduce, ideally a minimal proof-of-concept.
- Affected version or commit, and platform.
- Any suggested remediation.

## What to expect

FORLAS CRQ is a small open-source project provided under the MIT License (**"as is", without warranty**), so responses are best-effort and without a guaranteed SLA. The intent is to:

- Acknowledge your report within a reasonable time.
- Investigate and, where confirmed, prepare a fix for the next release.
- Credit you in the release notes if you'd like — or keep you anonymous. Your choice.

## Coordinated disclosure & safe harbour

Please give a reasonable opportunity to fix the issue before disclosing it publicly; we're happy to agree a timeline with you. We will not pursue action against **good-faith** security research that:

- respects user privacy and data, avoids destruction of data, and does not degrade others' use of the software;
- does not exploit the issue beyond what is necessary to demonstrate it; and
- reports promptly and privately.

## Hardening notes for deployers

- Keep the OS and the Microsoft Edge WebView2 Runtime patched.
- Protect the machine and user account — FORLAS CRQ's data (including hashed credentials and the signing key) is only as safe as the host it runs on.
- Treat the data directory (`%APPDATA%\app.forlas.crq\`) as sensitive; it holds the database, backups, and `secret.key`.
- Change the auto-generated first-run owner password immediately (Settings → change password).

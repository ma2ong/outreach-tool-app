# Spec 42 — Dependency & Production Hardening

## Goal

Keep the autonomous local sales operator recoverable and observable while preserving its existing customer-send and commercial safety boundaries.

## 1. Dependency security

The frontend CI has two distinct security views:

- **production dependency gate** — `npm audit --omit=dev --audit-level=high` is blocking. A High/Critical vulnerability that can ship in the browser/runtime dependency tree blocks the PR.
- **full build-tool audit** — development and build tooling is audited as well. Findings are printed and remediated with the smallest compatible lockfile update; `npm audit fix --force` is not an acceptable default because it may introduce unrelated major upgrades.

The committed lockfile is the reproducible dependency truth used by `npm ci` in CI and deployment.

## 2. Verified daily database backups

The SQLite customer database is a business asset and must have a verified snapshot for every day that unattended sales work runs.

- backups use SQLite's backup API, not a raw file copy, so WAL-committed rows are included consistently;
- a snapshot is written to a temporary file and must pass `PRAGMA quick_check` before atomic rename;
- an existing daily snapshot is re-used only after verification;
- a corrupt daily snapshot is quarantined and replaced rather than silently trusted;
- normal snapshots are retained for the newest 14 days;
- the single-leader Worker performs this check before every unattended sales cycle. Because the operation is idempotent, only one daily snapshot is created;
- if today's backup cannot be created or verified, the unattended sales cycle is recorded as failed and does **not** proceed to mailbox, sequence, research or Agent execution.

Startup backup behavior remains compatible; the Worker verification is the durable daily safety boundary for machines that remain online for many days.

## 3. Production health

The authenticated runtime status includes a read-only production health section. It may expose operational metadata but never customer records, credentials, messages or commercial data.

Health checks cover:

- live SQLite `quick_check`; because the UI polls status every 15 seconds, file-backed DB integrity results are cached for 60 seconds so observability does not repeatedly scan a growing database;
- latest backup existence, age and integrity;
- database disk free space;
- existence of the built frontend entry point;
- most recent server crash/start markers;
- current Python version versus the CI-tested Python 3.14 baseline;
- existing Worker lease/cycle/mailbox health.

Severity:

- DB integrity failure, missing/corrupt backup, <256 MB free disk or missing frontend build are critical;
- stale backup, <1 GB free disk or unrecovered crash marker are degraded warnings;
- Python minor-version mismatch is shown as an explicit compatibility note, not by itself a service failure.

## 4. Windows service diagnostics

The Scheduled Task entry point keeps server logs bounded and leaves a small crash trail:

- daily `server-YYYY-MM-DD.log` files are retained for 30 days;
- `faulthandler` is enabled for fatal Python diagnostics;
- `last-start.txt` records the latest server start;
- an uncaught server failure writes `last-crash.txt` with timestamp and traceback before re-raising so Windows Task Scheduler can perform its existing restart policy.

## 5. Safety boundaries

This hardening does not grant the Agent any new authority to:

- bypass send caps, unsubscribe or bounce protections;
- initiate restricted social outreach automatically;
- choose price, discount, payment terms, warranty, delivery date or lead time;
- send a quotation without the existing human commercial decision path.

Production hardening may stop unattended work when recovery guarantees are missing; it must never weaken an existing safety gate to keep automation running.

## 6. Acceptance

- production npm dependency audit has zero High/Critical findings;
- full npm audit has no unresolved High/Critical finding after compatible remediation;
- a verified backup is created once per day and corrupt snapshots are quarantined/rebuilt;
- backup failure prevents the unattended sales cycle from executing;
- production health exposes backup/DB/disk/frontend/crash status through the authenticated runtime API without re-running DB integrity scans on every UI poll;
- server logs are bounded and crashes leave diagnostics;
- full backend tests and frontend production build pass.

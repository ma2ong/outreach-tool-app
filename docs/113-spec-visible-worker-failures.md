# 113 — Worker failures must be visible, and a second start must identify itself

## Goal

The unattended sales Worker must report a failed background stage instead of recording
the whole cycle as healthy. A second process must remain a safe standby under the
existing SQLite lease, while leaving an operator-visible diagnostic rather than looking
like it never started.

## Rules

- `capability_health` keeps one durable row per background capability with
  `last_attempt_at`, `last_success_at`, `last_output_at`, `last_error`,
  `consecutive_failures` and `processed_count`.
- Capability recording is best-effort and uses its own short connection. A telemetry
  write can never stop or change the customer-facing job it describes.
- Each background stage may continue after another stage fails, but its failure is part
  of the cycle result. The runtime record has `last_cycle_ok=0` and a bounded, named
  error summary.
- A standby process never runs a cycle or sends anything. Its declined lease acquisition
  records only a timestamp, owner and count; it does not overwrite the active leader.
- A sequence send background task opens the database path currently configured by
  `app.main_deps`, never a module-import-time copy of that value.
- Sequence routing is data: enabled rules match country/language/customer type by
  priority and point to a sequence. Existing segment/language behavior seeds the default
  rules, and current enrollments are never rewritten.
- CI builds the SPA, starts a locally isolated API with every autonomous capability off,
  then runs the read-only Playwright suite against that server.

## Acceptance

- An executing capability exposes `running_since` without claiming a completed
  attempt. After 20 minutes it is reported as `stalled` (observation only, not
  cancellation or permission to retry a potentially sending job). Completion clears
  that marker; skipped work preserves the previous attempt and failure history.

- A failing non-mail background stage makes runtime health fail with the stage name.
- Runtime status distinguishes process/lease health from each business capability.
- A second live owner remains standby and appears in runtime status.
- Sequence send writes only to the configured test database.
- Backend tests, frontend build and Playwright run in CI without live DB, messaging,
  browser-social or model access.

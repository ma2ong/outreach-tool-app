# Spec 43 — Autonomy Control Center

## Goal

Make the autonomous LED sales operator explainable at a glance: what it did, what is waiting for Allen, what is blocked, and what customer/deal should move next. This is an observability and control layer over existing safe execution paths, not a new send path.

## 1. Read-only control-center snapshot

`GET /api/agent/control-center` returns one deterministic snapshot built from the existing Agent proposal ledger, conversation ownership, Account Brain and Opportunity Coach.

The snapshot must expose:

- approval backlog, including age and high-risk count;
- recent Agent action ledger with proposal status and whether execution was automatic or explicitly approved;
- recent failed actions;
- conversations currently owned by Allen;
- due contacted accounts that have no owned next step;
- unhealthy open opportunities and their next-best action;
- explicit blockers with severity and a concrete next step;
- autonomy coverage: how many action kinds are Off / Propose / Auto.

No customer body, credentials, pricing, payment terms or other sensitive/commercial content is added to this aggregate endpoint.

## 2. Execution-mode attribution

The existing proposal row is the audit source of truth. Execution mode is derived without a new send path:

- executed/failed row with no `decided_at` = `auto`;
- row with `decided_at` = `approved`;
- open pending row = `awaiting_approval`;
- approved/edited-approved row = `executing`.

This keeps historic rows compatible and avoids a migration solely for presentation.

## 3. Blocker rules

The control center reports blockers instead of silently leaving work idle. At minimum:

- safety pause is critical;
- unclassified customer replies are high priority;
- high-risk approval backlog is high priority;
- failed Agent actions in the last 7 days are high priority;
- Allen-owned conversations are visible as human handoffs, not Agent failures;
- due Account Brain accounts are medium unless another owner already exists;
- Opportunity Coach critical/high rows are surfaced by urgency;
- action kinds set to `off` are informational so intentional shutdown is distinguishable from a broken Agent.

The snapshot is read-only. It may recommend changing autonomy, but must never change autonomy by itself.

## 4. UI

The Agent page gets an `Autonomy Control Center` card above the proposal tabs. It shows:

- one-line operating state;
- approval / autonomous action / failure / handoff / due-account counters;
- blocker list;
- top next-best actions for accounts and opportunities;
- recent action receipts with mode (`自动`, `你确认后`, `等待确认`, `执行中`).

The UI refreshes on a conservative interval and has a manual refresh button. Heavy portfolio computation must not be polled every few seconds.

## 5. Safe production updater

A manually invoked `scripts/update_production.ps1` packages the production rollout steps that were previously pasted by hand:

- require a clean working tree;
- switch to `main` and `git pull --ff-only`;
- install backend dependencies;
- `npm ci`, full High/Critical audit and production build;
- restart only the existing `Maxcolor Outreach Tool` scheduled task / port 8000 process;
- verify today's SQLite backup, production health, Worker lease and local port.

It does not auto-deploy on its own and does not reconfigure Cloudflare Tunnel.

## 6. Safety boundaries

This PR does not grant any new authority to:

- bypass send caps, unsubscribe, bounce or do-not-contact protections;
- initiate restricted social outreach automatically;
- choose or promise price, discount, payment terms, warranty, lead time or delivery date;
- send a quotation without the existing human commercial path.

## 7. Acceptance

- control-center snapshot works on an empty/new database;
- automatic vs approved execution mode is derived correctly from historic proposal fields;
- blocker counts do not mutate CRM state;
- Agent page builds with the new control-center card;
- production updater stops on a dirty git tree or failed audit/build rather than deploying partial code;
- full backend tests, npm audit and frontend production build remain green.

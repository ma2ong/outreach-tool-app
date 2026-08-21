# Spec 38 — Durable Sales Worker Runtime

**Status:** implementation wave / stacked PR #2
**Date:** 2026-08-21
**Depends on:** Specs 22, 24–27, 33–37

## Problem

The sales Agent can own customer attention, opportunities, replies, buying signals and
contact research, but none of that is truly continuous if its operating loop lives only
inside one FastAPI web process on Allen's PC.

Two production problems must be solved before calling the system 24×7:

1. **continuity** — web restarts, process crashes or a powered-off desktop must not be the
   architecture of record for scheduled sales work;
2. **single execution** — multiple web workers or a web process plus a dedicated worker
   must never run the same autonomous cycle/send scheduler concurrently.

## Goal

Separate the sales operator from the web lifecycle while preserving the existing local
zero-configuration mode and all existing action/send safety controls.

This phase provides the worker/lease foundation. It does not by itself deploy a cloud
service or claim multi-region distributed operation.

## Runtime modes

### Local / desktop default

No new setup is required. FastAPI starts one embedded daemon worker as before:

```text
OUTREACH_EMBEDDED_WORKER=1   # default
```

Every web process may attempt to start one, but only the process holding the shared
`sales-operator` lease may execute a cycle.

### Dedicated hosted worker

Run the web service with:

```text
OUTREACH_EMBEDDED_WORKER=0
```

and run a separately supervised process against the **same durable database**:

```text
python -m app.worker
```

A one-shot mode is also available for diagnostics or an external scheduler:

```text
python -m app.worker --once
```

One-shot mode releases its lease immediately after the cycle.

## Single-leader lease

`runtime_leases` holds one renewable `sales-operator` lease. Acquisition uses SQLite
`BEGIN IMMEDIATE`, so two processes sharing the same DB file cannot both win the same
lease race.

The lease stores:

- owner/process identity;
- runtime mode (`embedded` or `worker`);
- acquisition time;
- latest heartbeat;
- expiry time.

The current leader renews before/after cycles and a heartbeat thread renews while a slow
cycle is in progress. If the process dies, heartbeat stops and another process can take
over after lease expiry.

A graceful dedicated-worker shutdown releases immediately.

## One unattended execution spine

Before this spec, email-sequence autosend had its own daemon scheduler separate from the
main operating loop. That is unsafe in a multi-process deployment even if the Agent loop
itself has a lock.

Spec 38 moves daily email-sequence autosend into the leased operating cycle:

```text
poll replies
-> social inbox scan
-> website / buying-signal recheck
-> sequence eligibility hygiene
-> due email sequence autosend
-> Agent / Account Brain / Opportunity Coach / Decision Maker Radar
```

The ordering is intentional: a reply is ingested before an automatic follow-up is
considered, so a customer who already answered can be stopped first.

The old `OUTREACH_AUTOSEND_SCHEDULER` switch remains the compatibility control, but the
execution no longer comes from an independent scheduler thread.

## Observability

`runtime_state` stores:

- latest cycle start/finish;
- active owner and mode;
- last cycle success/failure;
- last runtime error;
- total cycle count.

`GET /api/runtime/status` exposes the lease, heartbeat age, state and whether the web
process expects an embedded or dedicated worker. It exposes no credentials.

This is the minimum needed to distinguish:

- Agent is healthy and active;
- Agent is healthy but this process is standby;
- lease expired / no worker is active;
- last cycle crashed.

## Failure semantics

- A transient email sync failure shortens the next retry cadence but does not stop other
  sales maintenance work.
- A cycle-level exception is recorded in runtime state rather than disappearing with a
  dead thread.
- A hard process crash relies on lease TTL failover; it does **not** immediately replay
  an action that may already have sent something.
- Agent proposal execution retains the existing interrupted-execution safety behavior.

## Deployment boundary: what this does and does not mean

### Supported by this phase

A continuously supervised worker on one durable host (or processes sharing the same
SQLite file on a reliable shared filesystem) can keep the sales operator alive
independently of the web UI.

Email/IMAP/SMTP and public website research are server-compatible when credentials,
network access and durable files are configured.

### Not yet equivalent to distributed cloud 24×7

SQLite file locking is **not** a multi-region/serverless distributed lock. Do not run
independent replicas with separate local copies of `outreach.db` and assume the lease
protects them.

A real horizontally distributed deployment should move CRM/runtime coordination to a
shared transactional database (for example PostgreSQL) or another explicit distributed
lease implementation.

Social-channel automation is a separate deployment concern. WhatsApp/Instagram browser
sessions may depend on a persistent logged-in Playwright profile; this spec does not
claim those sessions are automatically portable to an ephemeral cloud worker.

True off-PC 24×7 therefore additionally requires:

- a persistent host/process supervisor;
- durable DB/backups;
- server-side secrets/mailbox configuration;
- durable browser/session storage for any supported social reply channel;
- monitoring/alerting around `/api/runtime/status` or equivalent metrics.

## Safety boundaries

The runtime controls **who may execute**, not **what may be executed**.

All existing safety rules remain authoritative:

- pricing/discount/payment/delivery commitments stay human-controlled;
- DNC, bounce suppression, verification and quotas stay in the existing send paths;
- cold WhatsApp/Instagram/Facebook remains manual-only;
- conversation ownership still prevents the Agent from sending after Allen takes over;
- public-person research does not guess private contact data.

## Acceptance

- two live owners cannot hold the same sales-operator lease;
- an expired lease can be taken over;
- the same owner can renew without resetting acquisition history;
- a slow cycle is protected by an active heartbeat;
- cycle success/failure is recorded in runtime state;
- standby processes do not execute the cycle;
- one-shot worker releases immediately;
- sequence autosend executes inside the leased cycle rather than an independent thread;
- local embedded-worker behavior remains the default;
- hosted web can disable the embedded worker and use `python -m app.worker`;
- CI never starts a real embedded worker or external research task;
- full backend tests and frontend production build remain green.

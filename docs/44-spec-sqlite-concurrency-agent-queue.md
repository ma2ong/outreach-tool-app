# 44 — SQLite Concurrency & Agent Queue Reliability

## Goal
Keep the local FastAPI + embedded Sales Worker architecture reliable under concurrent reads/writes, while making Agent-owned backlog health observable and self-throttling.

## Invariants
- Customer sends still use the existing send/autosend paths and safety gates.
- Pricing, discount, payment, delivery, warranty and quote commitments remain human-owned.
- Sales-task GET endpoints remain read-oriented; queue maintenance is background work.
- SQLite remains the durable store. This change does not pretend a local SQLite lease is a distributed lock.

## Database connection policy
Every application connection must use the same local concurrency profile:
- foreign keys enabled;
- 30s SQLite busy timeout;
- WAL journal mode when the database is writable;
- synchronous=NORMAL for WAL connections;
- bounded WAL auto-checkpoint.

WAL setup is best-effort for special read-only/in-memory connections, but normal production file connections must converge to WAL.

## Agent work state
Routine Agent-owned activities get a durable execution state keyed by activity id:
- attempt_count;
- consecutive_failures;
- last_attempt_at;
- last_outcome;
- last_error;
- updated_at.

A successful or safe reschedule clears consecutive failure count. A failed automatic attempt increments it.

## Retry/backoff
A single dead site or transient dependency must not spin every cycle. Failed Agent work uses bounded exponential backoff based on consecutive failures: 3, 7, 14, then 30 days. It remains Agent-owned and never becomes human homework merely because automation failed.

## Queue health
The Autonomy Control Center exposes:
- open Agent-owned work;
- due Agent work;
- stale Agent work (overdue by at least 7 days);
- Agent work with repeated failures;
- last autonomous-work sweep summary.

Repeatedly failing work is a visible Agent blocker, not a hidden exception and not a human Sales Task.

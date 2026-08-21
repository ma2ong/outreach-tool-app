# Spec 33 — Always-on Account Brain

**Status:** implementation wave
**Date:** 2026-08-21
**Depends on:** Specs 20, 22, 24–32

## Audit finding

The repository already has a strong autonomous-sales foundation: mission planning,
qualified discovery/import, sequence handoff, reply classification/drafting, conversation
ownership, deliverability circuit breaking, learning and a durable run ledger. The main
remaining gap is not another chatbot. It is operational continuity and account-level
attention.

Three concrete defects keep the Agent from behaving like an experienced salesperson:

1. The background loop is coupled to email polling. Setting `OUTREACH_AUTO_POLL=0`
   returns from the loop entirely, which also stops social scanning, website rechecks,
   sequence hygiene and the Agent.
2. The normal plan window is 08:00–12:00. A PC that starts or wakes after noon can miss
   the day's plan even though the product is intended to be local-first and always-on
   while the machine is available.
3. Sales Intelligence already knows a lead's explainable score and next-best action,
   but the Agent world only feeds it untouched leads, replies, overdue tasks and stalled
   opportunities. A contacted account with no reply, no active sequence and no dated
   task can therefore disappear from the Agent's attention indefinitely.

A fourth correctness bug was found in plan deduplication: non-discovery plan actions all
share a per-day key. Because batch actions have no `lead_no`, two different outreach or
enrollment batches of the same kind can collide and the later proposal can disappear.

## Goal

Turn the existing Agent into an account operator that continuously answers:

- Which contacted customer is due for attention now?
- What happened last and how long ago was it?
- Is some other mechanism already responsible for the next step?
- What is the safest next action?
- Can the system schedule that action without Allen remembering the account?

Allen still owns price, discount, payment terms, delivery promises and strategic
negotiation. Cold social outreach remains manual.

## Required behavior

### A. Independent background cycle

Email polling is one capability, not the scheduler master switch. Disabling it must not
stop social scanning, website recheck, sequence cleanup or Agent runs. The cycle records
email polling as healthy when it is intentionally disabled so it does not enter the
one-minute failure retry loop.

### B. Late-start planning recovery

The normal 08:00–12:00 planning window remains the preferred behavior. If today's plan
has not completed and the service first becomes available after noon, the background
Agent may catch up until the daily reporting hour. Existing retry count and cooldown
still apply; recovery must not create an unbounded model-call loop.

### C. Account Brain: due follow-up portfolio

Add a deterministic account scanner for leads that:

- are contactable and not won/lost;
- have already been messaged but have not replied;
- have no unhandled inbound reply;
- have no open sales task;
- have no active sequence enrollment;
- have no pending/running Agent task proposal;
- have a trustworthy last-touch date.

Use a conservative cadence based on actual touch count:

- after touch 1: due after 5 days;
- after touch 2: due after 7 days;
- after touch 3+: due after 14 days.

The scanner reuses `sales_intelligence.score_lead()` for score and next-best action. It
does not create a second CRM truth or invent customer facts.

### D. Deterministic follow-up safety net

At every Agent cycle, convert the highest-priority due accounts into at most three
`create_task` proposals. The normal autonomy dial remains authoritative: at `propose`
Allen sees the suggested tasks; at `auto` the existing executor creates them. The
fingerprint is tied to the last touch and touch count so repeated 15-minute cycles do
not create duplicate reminders. No customer message is sent by this safety net.

### E. Planner awareness and LED sales discipline

Expose the remaining due-account portfolio in the planner world. Teach the planner that
real replies and active revenue opportunities outrank prospecting, and that an LED
project should progressively establish application, indoor/outdoor environment, screen
dimensions, viewing distance/pixel pitch, brightness/environment, quantity, destination,
installation/service constraints and timing before commercial commitment. Unknown facts
remain unknown.

The planner must not duplicate work already owned by tasks, sequences or Agent proposals.

### F. Correct proposal deduplication

Discovery may remain one proposal per market per day. Other plan actions must include a
stable digest of their validated payload in the dedupe key so different batches/tasks
on the same day are not silently collapsed while exact repeats remain idempotent.

### G. In-flight proposal visibility

The world state's `already_pending` and proposal summary must count approved/running
proposals as open work. Planning must not repeat an action merely because its executor
is still running.

## Safety boundaries

- No automatic quote, negotiated price, discount, payment term or delivery promise.
- No autonomous cold WhatsApp/Instagram/Facebook initiation.
- No bypass of do-not-contact, bounce suppression, email verification, daily caps or
  existing send paths.
- Account Brain schedules internal work only; external follow-up continues through
  existing sequence/reply/send mechanisms and their autonomy controls.
- Tests use temporary databases and mocks only.

## Acceptance tests

1. `OUTREACH_AUTO_POLL=0` skips only email polling while the rest of the background
   cycle still executes.
2. A due contacted lead with no owner for its next step appears in Account Brain; a lead
   with an open task or active sequence does not.
3. Repeated Account Brain passes do not duplicate the same follow-up proposal.
4. Different same-day batch payloads generate different plan dedupe keys; exact repeats
   generate the same key.
5. Approved/running proposals appear as already-open work and in the open proposal count.
6. Late-start planning respects the same daily attempt ceiling and retry cooldown.

## Follow-on roadmap from the audit

These are deliberately outside this small safety-focused implementation wave:

- source-specific automatic buying-signal collectors for tenders, exhibition lists,
  hiring, distributor pages and social evidence;
- contact enrichment beyond public website evidence, with provenance and confidence;
- persistent job queue / cloud worker for operation while the local PC is off;
- controlled copy experimentation and statistical winner promotion after sufficient
  sample size;
- account-level response-time, opportunity aging and forecast coaching;
- richer LED technical knowledge retrieval for routine engineering questions, while
  commercial commitments remain human-only.

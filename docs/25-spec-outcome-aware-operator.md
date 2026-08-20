# Spec 25 — Outcome-aware Sales Operator

**Status:** implemented and verified  
**Date:** 2026-08-20  
**Depends on:** Spec 24 / Autonomous Sales Agent D1

## Why this phase exists

D1 closes the mechanical loop from a daily goal to qualified imports and nurture.
That is still not a responsible digital salesperson: an operator must notice when the
system is hurting deliverability, stop feeding demonstrably weak campaigns, explain why
a daily goal was missed, and leave a durable run record rather than one mutable status
line.

The real database makes this urgent: the 30-day hard-bounce rate is above the existing
2% danger line and part of the sending window is unmeasured because a send-only mailbox
cannot receive bounce notices. More volume is the wrong response until that is fixed.

## Scope

### 1. Deliverability circuit breaker

- Evaluate the existing 30-day deliverability metric at the start of each Agent run.
- Require at least 25 distinct emailed leads before making an automatic stop decision.
- If the measured hard-bounce rate is above the existing danger line, disable email
  autosend and create one high-priority repair task with the evidence.
- If bounce measurement is blind after that sample size, also stop; an unknown risk is
  not treated as a healthy zero.
- Persist the pause reason and time. Explicitly re-enabling autosend clears the pause.
- Every later Agent run continues to record the persisted incident as paused; the run
  ledger must not look healthy merely because the breaker already fired earlier.
- Re-enabling through the API/UI requires a separate acknowledgement of the persisted
  risk; an ordinary toggle cannot accidentally clear the circuit breaker.
- Block both scheduled sequence sends and Agent-created first-touch email actions. The
  executor checks again so a proposal created before the pause cannot bypass the gate.
- Expose the pause in the planner's world state so it spends the day on prospecting,
  qualification and internal work instead of repeatedly proposing blocked email.
- Do not stop manual send controls, social channels, reply handling or quote work.

### 2. Weak-sequence quarantine

- A sequence campaign with at least 25 leads and zero replies is statistically weak.
- Autonomous imports must not be enrolled into that sequence.
- Existing enrollments are not silently deleted or rewritten; Allen sees the incident
  and decides whether to replace the copy or stop the backlog.
- Never put a Korean lead into English just because the Korean sequence is quarantined.

### 3. Evidence-based market allocation

- Below 25 touched accounts, favor the target market with the least evidence so the
  system learns rather than locking onto noise.
- Once all configured markets have at least 25 touched accounts, favor the best observed
  reply rate, then the smaller sample on ties.
- Allocation only picks where to search. The D1 quality gate still decides what enters.

### 4. Daily outcome diagnosis

- Agent status reports qualified leads achieved/target, completion percentage and a
  short ordered list of blockers.
- Blockers distinguish: safety pause, planning exhausted, no autonomous discovery,
  discovery found no qualified imports, and missing language sequence.
- The daily report includes this outcome, especially when the target was missed.

### 5. Durable run ledger

- Every full Agent run writes started/finished timestamps, success/failure and JSON
  result/incident evidence to `agent_runs`.
- Status exposes the latest five runs.
- A crash/failure must not overwrite the previous run as if nothing happened.

## Non-goals and hard boundaries

- No automatic quote, price, delivery promise or negotiation.
- No cold social auto-send.
- No automatic copy generation or sequence rewriting.
- No deletion of leads, send logs or enrollments.
- No automatic re-enable after a safety pause.

## Acceptance evidence

- Unit tests cover healthy/dangerous/blind deliverability, explicit resume, weak sequence
  exclusion, market exploration/exploitation, goal diagnosis and failed run ledger.
- Full backend test suite and frontend production build pass.
- A copied real database shows the circuit breaker would pause for the observed reason;
  the real database remains untouched during verification.

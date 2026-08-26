# Spec 51 — Autonomous Follow-up Decision Quality

## Goal

An enrolled sequence being due means "the calendar permits a follow-up", not "the customer deserves another message now". Autonomous email follow-up must decide whether to **continue, delay, change angle, or stop cold follow-up** using current evidence immediately before a sequence step is sent.

This layer applies to automatic email sequence sends. Manual sequence sends remain available for deliberate human judgment, while all existing language, deliverability, quota, do-not-contact and Rendered Message Guard controls stay authoritative.

## Evidence inputs

The deterministic decision reads only durable local facts:

1. Sales Truth / sales intelligence score, ICP completeness and source-backed buying signal.
2. Lead contactability and current CRM terminal flags.
3. Inbox/reply state and open opportunity ownership.
4. Sequence state: current step, sequence performance, prior unanswered touches and due date.
5. Latest actual send time across send_log/outreach.
6. Sourced Lead Memory: current live memory items may support context but silence is never interpreted as rejection.
7. The exact rendered sequence message still passes Rendered Message Guard.

## Outcomes

### continue
The due step can be sent automatically.

### delay
The sequence stays active but `next_due_date` moves forward to a deterministic date. Typical reasons:
- the last send is too recent;
- the account is still worth pursuing but has no fresh signal and should not be over-contacted.

Delay is machine-owned scheduling, not a CRM stage change.

### change_angle
The current sequence is parked because continuing the same angle is low quality. Triggers include:
- a sequence with enough history is classified weak by Oversight;
- repeated unanswered touches reach the configured threshold without a fresh buying signal.

The enrollment becomes `quality_hold`. No customer message is sent and no human sales task is created merely to clear the queue. Account Brain / discovery / recheck mechanisms can gather fresher evidence; a future explicit re-enrollment or safe automated recovery may start a better sequence.

### stop
Cold follow-up no longer owns the next action. Strong stop reasons include:
- customer replied;
- do-not-contact;
- terminal CRM state won/lost;
- an open opportunity now owns the account.

The enrollment is moved to a non-active terminal/parked state with a reason. This does not mutate the lead's CRM stage.

## Cadence policy

The minimum spacing is measured from the latest actual send, not merely enrollment date:
- after first touch: at least 3 days;
- after second unanswered touch: at least 5 days;
- after third+ unanswered touch: at least 8 days.

A source-backed buying signal with confidence >= 70 may use the sequence's own due date without adding an extra no-signal delay, but never bypasses reply/opportunity/DNC/terminal/message safety guards.

## Quality policy

- A follow-up may continue at a lower sales-score threshold than first touch because the relationship already consumed acquisition cost: minimum 50/100.
- `data_incomplete` alone does not stop an already-started sequence, but if score < 50 it is delayed rather than sent.
- A source-backed signal >= 60 is positive evidence.
- A weak sequence never auto-sends another due step.
- Repeated silence is not interpreted as "not interested". It only changes cadence/angle.

## Execution boundary

`autosend.run_once()` and automatic `sequence_send.send_due()` evaluate every due email enrollment immediately before send. Decisions are persisted in a small `followup_decisions` audit table and reflected in the run result:

- `sent`
- `delayed`
- `quality_held`
- `stopped`
- existing `held`, `deferred`, `failed`

Manual sequence sends can opt out of the worth-now policy but never bypass existing language, DNC, quota or Rendered Message Guard controls.

## Invariants

- No new external send path.
- No automatic pricing, payment, discount, delivery, warranty, certification or technical-spec promises.
- No automatic CRM-stage mutation.
- No automatic cold WhatsApp / Instagram / Facebook initiation.
- No interpretation of silence as rejection.
- No user-facing task spam from quality holds.
- Tests use temporary databases/mocks only.
# Spec 50 — Autonomous Send Decision Quality

## Goal

The Agent must distinguish **can send** from **worth sending now**. Existing channel, quota,
do-not-contact, bounce, and Rendered Message Guard controls remain authoritative. This spec
adds a deterministic decision layer before autonomous first-touch email so the Agent does not
spend reputation or attention on weak, stale, contradictory, or poorly evidenced accounts.

## Scope

This spec applies to `send_outreach` actions created/executed autonomously by the Agent.
Human-initiated Outreach-panel sends keep the existing controls and are not silently blocked by
this quality policy. A human can therefore deliberately contact an unusual account while the
Agent remains conservative.

## Decision inputs

For each proposed first-touch account, the decision layer reads only durable facts already in
the local sales system:

1. **Sales Truth** — `sales_intelligence.score_lead()` score/grade, ICP fit, data completeness,
   junk-name warnings, source-backed buying signals.
2. **Contactability** — a real email that has been verified/classified as `valid` or `role`, and
   a known decision-maker contact for the account.
3. **Pipeline ownership** — no unhandled reply, no open opportunity, no active sequence, no
   same-day send, and no existing messaged/replied status.
4. **Lead memory / next action** — an open due/overdue task means internal work currently owns
   the next action; autonomous cold outreach waits instead of racing it.
5. **Customer-facing evidence** — if the selected template makes a delivery/project-reference
   claim, the account may be auto-sent only when at least one explicitly shareable approved case
   exists. If it makes a product/catalog claim, at least one Agent-approved product row must exist.
   The decision layer does not invent a case/product or infer approval from quote/order history.
6. **Rendered message** — render the exact subject/body for that lead and run the existing
   Rendered Message Guard. A held final message is never proposed for autonomous execution.

## Conservative thresholds

- Minimum autonomous sales score: **65/100**.
- `data_incomplete=True` is a blocker.
- Missing decision maker is a blocker.
- Primary email status must be `valid` or `role`.
- A source-backed buying signal with confidence >= 60 is positive evidence, but is not required
  if the rest of the account evidence is strong.

These thresholds affect Agent autonomy only. They do not change CRM stage or manual sending.

## Planner behavior

`world.build()` exposes a compact `autonomous_send` assessment on each shortlisted untouched
account so the planner sees why an account is ready or not ready.

When validating `send_outreach`, the backend independently evaluates every proposed lead against
this spec and the selected template. Unsafe/unready leads are removed from the batch. If no lead
survives, the action is rejected with explicit reasons rather than creating an empty proposal.
The validated payload stores a compact decision snapshot for auditability.

The model cannot override this result by claiming an account is important.

## Execution-time recheck

When `send_outreach` executes in `auto` mode, re-run the decision on the current database state.
This protects the interval between planning and execution: a new reply, task, opportunity,
sequence enrollment, invalidated email, or missing evidence can stop the send.

Human-approved proposals are not re-scored for "worth it" at execution time because approval is
an explicit human timing decision; they still pass every existing send-path and rendered-message
safety control.

## Audit / UI contract

- `send_outreach` proposal reasoning remains the planner's explanation.
- `payload.autonomous_decision` records the accepted lead decisions and rejected lead reasons.
- Execution results say how many accounts were removed by a late autonomous recheck, if any.
- No new external send path is introduced.

## Non-goals / invariants

- No automatic pricing, discount, payment-term, delivery, MOQ, capacity, warranty, certification,
  or technical-spec promises.
- No automatic CRM-stage mutation to make a lead look more qualified.
- No auto-start of WhatsApp/Instagram/Facebook conversations.
- No use of private quote/order history as permission to cite a customer/project publicly.
- Unknown evidence is a reason to wait or create internal work, never a reason to guess.
- Tests use temporary databases/mocks only; no live email, browser, model, search, or production DB.

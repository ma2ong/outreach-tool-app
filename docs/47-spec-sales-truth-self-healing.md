# 47 — Sales Truth & Self-Healing

## Goal

Separate **human CRM judgement** from **machine-verifiable sales facts** so the Agent does not treat a stale `leads.stage` label as proof that a customer replied, accepted a quote, or progressed.

## Rules

1. `leads.stage` remains a human/CRM label. This feature never silently rewrites it.
2. Agent-facing truth is derived from durable evidence already in the database:
   - `send_log` / `outreach` for actual outbound contact;
   - `inbox_messages(kind='reply')` for human replies;
   - `inbox_messages(kind='auto')` for autoresponders;
   - active `sequence_enrollments` for follow-up ownership;
   - `quotes` and `orders` for commercial progress;
   - `opportunities` for project work.
3. A historical CRM stage mismatch is an anomaly, not permission to mutate the CRM stage.
4. Strong contradictions must be visible in Customer 360 and Autonomy Control Center.
5. Safe self-healing is limited to machine-owned/derived state. Human CRM stage, pricing, payment, delivery and negotiation state are never auto-rewritten.
6. Opening a page must remain read-only.

## Derived factual states

Per lead, compute:

- `never_contacted`
- `contacted`
- `human_replied`
- `quoted`
- `quote_accepted`
- `ordered`
- `won` / `lost` only when the explicit CRM stage says so

The most advanced evidence-backed state wins, except explicit `won/lost` remain terminal human decisions.

## Anomalies

At minimum detect:

- `stage_replied_without_human_reply`: CRM says replied but there is no stored human reply and no reply evidence in outreach.
- `outreach_replied_without_human_reply`: outreach says replied while no human reply exists.
- `human_reply_but_stage_behind`: a real human reply exists but CRM stage is still `new/contacted`.
- `accepted_quote_without_order`: accepted quote exists without an order.
- `order_but_stage_behind`: an order exists while CRM stage is not `won` (informational only; do not auto-win).
- `active_sequence_after_human_reply`: a live sequence still exists after a human reply.

## Self-healing policy

Only machine-owned derived state may be repaired automatically, and only with strong evidence:

- active email sequence after a verified human reply -> stop sequence through existing sequence logic;
- stale Agent-created reply task whose referenced inbox row is no longer `kind='reply'` -> cancel task.

Everything else is report-only unless a dedicated, preview-first maintenance tool already owns the migration.

## Agent use

Customer 360 exposes both:

- `account.stage` — human CRM label;
- `sales_truth` — evidence-backed factual state and anomalies.

Autonomy Control Center exposes aggregate anomaly counts and top anomalous accounts. Agent planning should prefer `sales_truth.factual_state` for communication/progression facts and use CRM stage only for explicit terminal/manual decisions.

## Safety acceptance

- No new customer-send path.
- No automatic price/discount/payment/delivery/warranty commitments.
- No automatic CRM stage rollback/advance from this module.
- Tests use temporary DBs only.

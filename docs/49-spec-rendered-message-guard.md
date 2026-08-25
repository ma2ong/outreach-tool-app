# 49 — Rendered Message Guard

## Goal

Stop an unsafe or obviously generic cold email at the last possible moment: after all template variables are rendered, but before the sender is called.

The guard is a safety boundary, not a copywriter. It may hold a message and explain why; it must never silently rewrite a customer-facing message after review.

## Rules

1. Guard the rendered subject + body, never only the stored template.
2. Cold-email commercial commitments are held when the final text contains an explicit price/currency amount. Technical numbers such as P2.5, 200 sqm, a year, or a phone number remain valid.
3. The first cold-email touch must contain at least one lead-specific term derived from the company name/domain, city, or sourced hook. Follow-up steps do not need to repeat the opening personalization.
4. A held message is not sent, does not mark outreach as messaged, does not advance a sequence, and does not consume a send quota.
5. Holds are returned as structured results (`held`, `holds[]`) so UI/Agent audit can explain what did not leave.
6. WhatsApp/Instagram/Facebook cold-start restrictions are unchanged. This PR does not create another send path.

## Safe default-copy migration

The existing seeded English/Korean first-touch defaults predate the personalization rule. On upgrade, only rows that still match the exact old system default subject + body may be changed to the new personalized default.

- Exact-match only.
- User-edited templates/sequence steps are never overwritten.
- Migration is idempotent and versioned through `settings`.
- A database backup still happens before application startup migrations.

The new defaults use `{company}` and, where available, `{hook}`. Missing hooks render away cleanly; company identity remains in the message.

## Send-path integration

- `outreach.send_campaign`: render once -> guard -> send the same rendered strings.
- `sequence_send.send_due`: render current step once -> guard -> send the same rendered strings.
- Autosend reports held counts in its durable last-run result.
- Manual Outreach / Sequence UI shows held leads and reasons.

## Non-goals

- No automatic price generation.
- No change to quote/order/payment/delivery authority.
- No automatic rewriting to force a message through the guard.
- No changes to CRM stage.
- No live sends/network access in tests.

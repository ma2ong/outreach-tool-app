# 127 — Three-segment sales copy

## Decision

Outbound copy has exactly three customer segments:

- `rental` — use only when the available evidence clearly says the company is primarily rental / staging / event-production work.
- `install` — use only when the available evidence clearly says the company is primarily fixed installation / AV integration / installation work.
- `general` — use when the customer cannot be classified confidently, when neither rental nor install is supported, **or when both rental and install are supported**.

`outdoor` is no longer a customer/copy segment. Outdoor can still be a project/application fact, but it must never select a separate outbound letter or DM family.

## R1 — Evidence is conservative

Segment selection keeps the existing evidence precedence:

1. Allen's explicit customer-type tags.
2. `target_fit` classification.
3. The company's own `business`, `hook`, and `brief` text.

At each level, collect rental and install evidence before deciding. Exactly one side -> that specialist segment. Both sides -> `general`. Neither side -> continue to the next evidence level; if no level resolves the company, use `general`.

A stronger explicit level may override weaker inferred evidence. For example, an explicit `租赁商` tag remains `rental` even if website text also mentions installation. But explicit tags containing both `租赁商` and `工程商` resolve to `general` rather than whichever word is checked first.

Outdoor/signage/billboard/facade words alone do not imply a customer type and therefore resolve to `general` unless the same evidence level also clearly identifies installation work.

## R2 — System copy has three families only

System-owned cold-email sequences and social-DM families exist only for Rental, Install, and General. No new Outdoor sequence/template/DM variant may be created.

Legacy Outdoor system sequences may retain historical send records, but they must not remain a routing target. Migration tooling must route their active enrollments according to the new three-segment classifier rather than starting those customers over.

Human-edited/custom sequences are not silently rewritten or deleted.

## R3 — Copy shape

The system copy should read like a salesperson, not a mail-merge brochure:

1. Use a specific public/customer hook when one is available.
2. State one short, relevant LED capability. A cold-email opener should include **one grounded product clue** (normally a real pitch/range already supported by the product library) so the reader has something concrete to react to; do not turn the message into a specification list.
3. Offer at most one concrete next resource, such as the matching spec sheet. This is a statement, not a second call-to-action question.
4. End with **one low-friction question** that advances qualification or reveals the relevant project.

For `general`, the best first question is normally the missing classification itself: rental, fixed install, or both.

Avoid generic closers such as `Worth a conversation?`, `whenever it's convenient`, and `Happy to be a spec-and-pricing contact`. Do not promise pricing, delivery, MOQ, payment terms, capacity, certification, warranty, or unsupported product facts.

Email and chat keep different registers: email may include greeting/signature; WhatsApp/Instagram/Facebook copy is materially shorter and has no email-style sign-off.

## R4 — Quality is not a send gate

This spec does **not** restore the removed first-touch quality gate. Existing compliance/truth/send guards remain authoritative and unchanged. Copy-quality expectations are enforced on system-owned seeded copy and drafting instructions, not by inventing a new runtime blocker for customer sends.

## R5 — Replies

A reply draft must answer the customer's latest message before selling again. It may ask at most one useful follow-up question; if a question would be forced, it may ask none. It must not reintroduce Allen or repeat the original cold pitch when the thread already provides that context.

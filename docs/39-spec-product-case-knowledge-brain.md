# Spec 39 — Product & Approved Case Knowledge Brain

**Status:** implementation wave / stacked PR #3
**Date:** 2026-08-21
**Depends on:** Specs 22, 33, 35, 38

## Problem

The Agent already knows how to qualify an LED project and decide what to ask next, but a
veteran LED salesperson also knows which real product can satisfy the known constraints
and which past projects are safe to reference.

Two shortcuts are unsafe:

1. giving the LLM the whole product/price table and asking it to recommend something;
2. treating quote/order history as permission to tell another customer about that project.

Both create unsupported claims and privacy/commercial risk.

## Goal

Create an evidence-first product and case knowledge layer with explicit human approval.
The layer must improve product judgment without widening autonomous pricing, delivery,
payment or customer-reference authority.

## Product knowledge source

The existing `products` table remains the single catalog source. It gains additive fields:

- `indoor_outdoor`;
- `refresh_rate_hz`;
- `maintenance_access`;
- `cabinet_size`;
- `control_system`;
- `notes`;
- `agent_approved`.

Existing rows and default P0.7–P10 reference ranges migrate with
`agent_approved = 0`. Loading a default catalog never silently grants the Agent authority
to state those values as facts.

The UI has an explicit **允许 Agent 使用** switch. New products are unapproved by
default.

`ref_price_sqm` is deliberately not part of the Agent-safe product fields.

## Deterministic Product Advisor

`app.agent.product_advisor` matches only approved products.

The matching order follows sales engineering evidence:

1. application;
2. indoor/outdoor environment;
3. pixel pitch;
4. brightness;
5. refresh rate;
6. maintenance access;
7. cabinet/control evidence.

Explicit contradictions are hard exclusions. Examples:

- Indoor-only product for an Outdoor opportunity;
- P3.9–P4.8 product for a specified P2.5 project;
- product brightness ceiling below the required brightness;
- 3840 Hz product where the recorded project requirement is 7680 Hz.

Missing product fields are evidence gaps, never guessed values.

Approval alone is not enough to recommend a vague product. A customer-facing
recommendation requires both:

- project qualification completeness of at least 45%; and
- a minimum deterministic product evidence score.

Before those gates pass, even the product model is withheld from the automatic reply
context.

## Internal history vs customer facts

Historical sent/accepted quotes and orders may improve **internal tie-breaking only**.
They do not become customer-facing evidence.

`customer_safe_context()` strips:

- reference price;
- quote/order history;
- internal rank/score;
- internal notes.

The customer-safe result contains only exact approved catalog fields.

## Opportunity Coach and Customer 360

Opportunity Coach evaluates product evidence alongside qualification, dated next action
and authority coverage.

When a sufficiently qualified opportunity has no approved/compatible product evidence,
the coach lowers health and instructs the salesperson to verify/add product facts rather
than letting the Agent guess.

Customer 360 exposes internal product advice per open opportunity, including reasons,
gaps and ranked matches. This remains a read model; it creates no duplicate opportunity
state.

`GET /api/opportunities/{id}/products` exposes the same deterministic internal advisor.

## Approved Case Library

Quote and order history is **never** auto-promoted into a case.

`approved_cases` is an explicit human-managed library. Important fields are:

- `internal_name` — private CRM label;
- `public_label` — wording allowed in external communication;
- application/environment/pixel pitch/dimensions/product model;
- `public_summary` — exact facts Allen permits the Agent to repeat;
- `source_url` — optional approved public/project-sheet source;
- `shareable` — explicit external-use permission.

Every new case defaults to `shareable = 0`.

Turning sharing on requires both `public_label` and `public_summary`. A private internal
name is never included in `customer_safe_matches()`, even for a shareable case.

The UI deliberately uses a second explicit action: add the case privately first, then
click **允许 Agent 对外引用**.

## Case matching

Case matching is deterministic and conservative:

- same application increases relevance;
- environment conflict excludes the case;
- specified pixel-pitch conflict excludes the case;
- only `shareable = 1` cases can enter reply context.

`GET /api/opportunities/{id}/cases` returns shareable case matches for internal review.

## Reply drafting

Reply drafting receives two new clearly separated sections:

- `APPROVED PRODUCT FACTS`;
- `APPROVED SHAREABLE CASES`.

The LLM is explicitly told:

- these are the only product/case facts it may state;
- missing fields remain unknown;
- no price/history/internal rank is present or allowed;
- no customer/order/CRM history may be turned into a past-project claim;
- when Product Advisor is not ready, do not recommend a product.

The previous generic P0.7–P10 statement is removed from the drafting fact list so it
cannot bypass the approval gate.

## Safety boundaries

This spec does **not** change:

- autonomous pricing/discount authority;
- payment-term authority;
- committed production or delivery dates;
- certifications/warranty claims without exact evidence;
- cold social initiation rules;
- DNC/bounce/quota controls;
- conversation takeover behavior.

Products and cases increase factual recall, not commercial authority.

## Acceptance

- legacy/default product rows remain unapproved after migration;
- only approved products are considered;
- explicit technical conflicts exclude a product;
- vague approved products cannot become customer recommendations without enough evidence;
- prices/history/internal notes do not enter customer-safe product context;
- Opportunity Coach and Customer 360 expose product evidence state;
- product match API returns deterministic advice;
- new cases are private by default;
- shareable cases require public label + public summary;
- internal case names never enter customer-safe context;
- private cases never enter automatic replies;
- approved product/case facts appear in reply context only after their gates pass;
- frontend offers explicit product and case approval controls;
- full backend tests and frontend production build remain green.

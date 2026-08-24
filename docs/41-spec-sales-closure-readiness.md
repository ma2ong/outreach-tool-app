# Spec 41 — Sales Closure & Quote Readiness

## Goal

Make the autonomous LED sales operator close its own internal loops instead of leaving stale tasks behind, and distinguish a technically calculable LED configuration from a commercially ready quotation.

## 1. Agent task lifecycle

Agent-created activities retain their proposal source reference. New Account Brain and Opportunity Coach task proposals carry a structured `completion_rule` inside the immutable proposal payload.

A deterministic reconciler runs before each Agent planning cycle and may only touch `source='agent'` activities whose `source_ref` resolves to a real Agent proposal.

Supported rules:

- `account_brain`: resolve when the factual condition that created the task is no longer true (ICP completed, decision maker found, invalid channel replaced, quote converted to order, quote status changed/reply arrived, or a newer touch/sequence now owns follow-up).
- `opportunity_coach`: resolve when the opportunity becomes healthy/closed; cancel and supersede the old task when the issue digest changes so a fresh coach task can own the new problem.

Historical manual/legacy/reply/opportunity tasks are never guessed or rewritten.

## 2. Engineering integrity

Before Solution Engineer math is considered usable, explicitly entered product engineering facts are cross-checked:

- cabinet width ÷ cabinet pixel width and cabinet height ÷ cabinet pixel height must describe a consistent effective pitch;
- when an exact nominal pitch is present, effective pitch must be within tolerance;
- average cabinet power cannot exceed maximum cabinet power;
- module dimensions cannot exceed cabinet dimensions.

Conflicting facts block engineering readiness and are shown as errors. No value is silently corrected.

## 3. Quote Readiness

`Quote Readiness` is an internal read model. It never sets a price or commits a term.

It combines:

- LED qualification completeness;
- Product Advisor approval/evidence;
- deterministic Solution Engineer output;
- contact/decision authority coverage;
- existing quote state for the opportunity.

It exposes:

- `technical_ready`: configuration is internally reproducible;
- `ready_for_human_pricing`: Allen can safely price the known configuration;
- exact quote starter line facts (model, pitch, actual width/height, quantity, area, cabinet count, exact resolution) **without unit price**;
- `human_decisions`: commercial fields Allen still owns: unit price, freight/shipping, Incoterm, payment terms, lead time, warranty, validity and any discount;
- blockers and warnings.

A sent/accepted quote is reported as an existing commercial artifact rather than encouraging duplicate quotation creation.

## 4. Safety

This spec does not grant the Agent authority to:

- choose or send a price;
- offer a discount;
- promise payment terms;
- commit a lead time or delivery date;
- invent warranty/certification facts;
- send a quotation automatically.

## 5. Acceptance

- stale Agent tasks close or supersede deterministically;
- non-Agent tasks are untouched;
- contradictory engineering facts cannot produce a ready solution;
- Quote Readiness never returns a unit price or calculated commercial total;
- full backend tests and frontend production build pass.

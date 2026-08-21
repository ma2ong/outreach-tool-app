# Spec 37 — Decision Maker Radar

**Status:** implemented in PR #1
**Date:** 2026-08-21
**Depends on:** Specs 33–36

## Problem

A strong account or a live LED project can still stall because the CRM knows the company
but not the person who can move the deal. Opportunity Coach can already identify missing
commercial authority (Owner / Purchasing / Procurement / Buyer) and project authority
(Project / AV / Technical). The missing capability is a safe way to research those gaps.

The system must not solve this by guessing personal email patterns, silently assigning
`decision_maker`, or scraping arbitrary private profiles.

## Goal

Research public company-owned pages for named business contacts, preserve the exact
source/evidence, stage uncertain findings in a candidate pool, and automatically add only
high-confidence contacts that are safe enough to become CRM records.

## Architecture

### 1. Public person detector

`people_detector.py` is deterministic and network-free. It accepts source URL + public
page text and looks for:

- a named person;
- a relevant commercial or project/technical title;
- an optional company-domain email in the same evidence window;
- an optional explicit personal LinkedIn URL in the same evidence window.

It does **not** infer a name from an email, manufacture an email pattern, or treat a job
title with no named person as a contact.

### 2. Candidate pool

`contact_candidates` is separate from `contacts` so weak evidence cannot pollute CRM.
Each candidate stores:

- lead/account;
- name and title;
- optional public company email / personal LinkedIn;
- inferred coverage kind (`commercial` or `project`);
- source URL;
- evidence excerpt;
- confidence;
- lifecycle (`new`, `promoted`, `dismissed`);
- promoted contact reference when applicable.

The candidate pool is evidence, not a second CRM truth.

### 3. Automatic promotion

Automatic promotion requires all of:

- confidence >= 90;
- source URL belongs to the customer's own public website;
- explicit public company email or personal LinkedIn;
- the candidate is not already represented by email, LinkedIn or exact name/title.

Even after promotion, CRM `role` remains `other`. The public title may be used by
Opportunity Coach as authority evidence, but the system does not silently rewrite an
inference into an explicit `decision_maker` role.

A project/technical candidate cannot become the company's first/default contact
automatically. If no contact exists yet, the candidate stays staged for review. This
prevents an engineer from accidentally becoming the default outbound recipient.

### 4. Targeted public search

The radar searches for exact **company-owned page URLs**, not arbitrary profiles. Search
queries are generated only for currently missing role kinds and results are restricted
to the customer's website domain before any page is fetched.

Research is bounded:

- maximum four result pages per account scan;
- maximum two accounts per autonomous sweep;
- 14-day cooldown for quoted/negotiation or high-risk opportunities;
- 30-day cooldown for lower-risk open opportunities.

Do-not-contact accounts are not researched further.

### 5. Agent integration

The background Agent cycle now closes four different attention loops:

`replies/planning -> Account Brain -> Opportunity Coach -> Decision Maker Radar`

If the radar finds a strong commercial contact, it may safely add the contact. If it
finds only staged candidates, it creates an internal `create_task` proposal containing
the names/titles and source-backed evidence. It never sends a customer-facing message.

Customer 360 exposes staged candidates and can prioritize reviewing the strongest one.

### 6. Manual review API

The API supports:

- list staged candidates by lead;
- manually run a bounded scan for an account;
- explicitly promote a staged candidate;
- dismiss a candidate.

Manual promotion is an explicit human override; the stored CRM role still remains
unconfirmed unless the user later changes it.

## Safety boundaries

- Public business pages only in the automatic search path.
- No guessed personal email addresses.
- No private profile bypass or authenticated scraping.
- No automatic `decision_maker` role assignment from title text.
- No overwrite of an existing verified contact.
- No research for do-not-contact accounts.
- No direct customer messaging from a person-search result.
- Existing send, conversation ownership, pricing and commercial takeover controls remain
  authoritative.

## Acceptance

- Generic titles without a named person do not create candidates.
- Company-domain email / personal LinkedIn raises confidence but is never guessed.
- Strong commercial evidence can auto-promote while keeping role unconfirmed.
- A technical/project candidate cannot become the first default contact automatically.
- Search results are restricted to the customer's own domain.
- Candidate scans respect bounded page/account limits and cooldowns.
- repeated scans do not duplicate candidates or review tasks.
- Customer 360 exposes staged candidates.
- full backend suite and frontend production build remain green.

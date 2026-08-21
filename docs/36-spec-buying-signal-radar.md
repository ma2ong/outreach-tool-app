# Spec 36 — Public Buying Signal Radar

**Status:** implementation wave
**Date:** 2026-08-21
**Depends on:** Specs 33–35

## Problem

Discovery already reads public company websites to find contact details, ICP fit and a
personalized hook. Recheck already revisits contacted accounts on a quality-based
schedule. The CRM already has a canonical, source-backed `buying_signals` table.

What is missing is the bridge between those systems: the website reader currently
throws away public evidence that an account may be entering a buying window.

Examples:

- a new studio, showroom, venue, store or facility is being opened/expanded;
- an RFP/RFQ/tender/procurement notice appears;
- the company is hiring AV/video/LED/event-production technical roles;
- the company announces an expo booth or upcoming exhibition presence;
- the company is actively seeking distributors/dealers/partners.

## Goal

Turn public evidence already fetched by discovery/recheck into reviewable,
source-backed buying signals without introducing a second crawler or letting keyword
matches directly trigger customer messages.

## Architecture

### 1. Deterministic detector

Add a pure `signal_detector` module that receives `(source_url, page_text)` pairs and
returns candidate signals. It must:

- support English, Korean and a small set of common Chinese terms already likely to
  appear in source material;
- require multiple pieces of evidence for noisy categories where possible;
- return the exact source URL and a short evidence excerpt;
- assign a conservative confidence rather than pretending every keyword is a purchase;
- dedupe repeated matches from the same page/type;
- never perform network access itself.

Initial categories:

- tender / RFQ / procurement — highest confidence;
- project expansion / new location / studio / venue;
- hiring for relevant technical/AV/event roles;
- exhibition / expo participation;
- distributor / dealer / partner recruitment.

### 2. Enrichment bridge

`enrich_domain()` already fetches the pages. Preserve the URL alongside each fetched
page and return `buying_signals` candidates in its result. Existing enrichment outputs
remain backward-compatible.

### 3. Discovery import bridge

A newly discovered candidate may carry buying-signal candidates. When that candidate is
actually imported as a lead, write those candidates through the existing
`sales_intelligence.create_signal()` path using the newly assigned `lead_no`.

Candidates rejected by ICP/contactability rules do not create orphan signal rows.

### 4. Recheck bridge

When an existing account is revisited, record newly detected signals even if the
contact fields themselves did not change. The existing buying-signal fingerprint keeps
repeated rechecks idempotent.

A detected signal should not overwrite lead fields and should not automatically send a
message. It becomes evidence available to Sales Intelligence, Customer 360 and
Opportunity Coach.

### 5. Agent behavior

Fresh, credible signals already influence account scoring and Opportunity Coach through
the canonical `buying_signals` table. This phase does not add another outbound executor.

The safe chain is:

`public evidence -> signal -> score/coach -> internal proposal/task -> existing outreach/reply safety path`

## False-positive controls

- Generic words such as “project”, “event” or “partner” alone are insufficient.
- Tender signals require procurement/bid/RFP/RFQ vocabulary.
- Hiring signals require both hiring/career vocabulary and a relevant technical/AV role.
- Exhibition signals require booth/exhibit/visit-us language plus expo/show context.
- Project signals require change/expansion/opening/launch language plus a facility/use
  context such as studio, venue, store, showroom, arena or control room.
- Source evidence is preserved so Allen can inspect why the Agent cared.

## Safety boundaries

- Public company pages only; no bypass of authentication or scraping controls.
- No guessed person identity, private email or private profile enrichment.
- A keyword match never sends customer-facing outreach by itself.
- Unknown dates remain unknown; `captured_at` is not falsely presented as event date.
- Existing DNC, bounce, sending caps and autonomy controls remain authoritative.

## Acceptance

- The detector recognizes representative tender, project, hiring, exhibition and
  distributor evidence and rejects generic noisy text.
- `enrich_domain()` returns source-backed signal candidates while preserving existing
  fields.
- imported discovery candidates create canonical buying-signal rows only after lead
  creation.
- recheck records a new signal even when no contact field changed, then remains
  idempotent on the next identical check.
- full backend tests and frontend production build remain green.

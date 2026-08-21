# Spec 35 — LED Sales Brain, Customer 360 and Opportunity Coach

**Status:** implementation wave
**Date:** 2026-08-21
**Depends on:** Specs 22, 33–34

## Problem

The Agent now owns account attention, but an experienced LED-display salesperson does
more than remember who is due. They know what makes an LED project sufficiently
qualified, which missing fact matters next, which buyer role is missing, and whether a
deal is genuinely progressing or merely has a stage label.

The repository already contains useful primitives: multiple contacts, opportunity
stages, buying signals, quotes, activities and explainable account scoring. The missing
layer is a deterministic sales operating model that joins those facts together.

## Goals

1. Encode an LED-specific qualification playbook by application without inventing facts.
2. Expand opportunity records with the technical/commercial discovery fields an LED
   salesperson actually needs before configuration and quotation.
3. Build Customer 360 as a single read model over the existing CRM truths.
4. Add an Opportunity Coach that identifies missing requirements, stale next steps and
   missing decision-maker coverage.
5. Feed the highest-risk open opportunities into the existing proposal/task system so
   the Agent actively protects live pipeline without sending customer-facing messages.
6. Reuse the existing `buying_signals` table rather than creating a competing signal
   subsystem.

## Opportunity qualification fields

Keep existing fields and add portable structured discovery fields:

- viewing distance (`viewing_distance_m`)
- brightness requirement (`brightness_nits`)
- refresh-rate requirement (`refresh_rate_hz`)
- maintenance access (`maintenance_access`)
- cabinet preference (`cabinet_size`)
- control-system constraint (`control_system`)
- installation/structure note (`installation_type`)
- project timing (`project_timing`)
- budget context (`budget_range`)
- decision process (`decision_process`)
- technical notes (`technical_notes`)

All are optional. Unknown stays unknown. Schema migration must work on an existing
SQLite database via additive columns only.

## LED application playbook

Support at least:

- Rental
- Fixed Installation
- DOOH
- Retail
- Sports
- Church
- Control Room
- Broadcast
- Virtual Production / XR
- generic LED project fallback

The playbook returns ordered qualification fields. Common project facts come first;
application-specific facts then adjust priority. Examples:

- Rental/XR: refresh rate, cabinet format, control workflow and serviceability matter
  earlier.
- Outdoor/DOOH/Sports: environment, brightness and maintenance access matter earlier.
- Control Room/Broadcast: viewing distance, pixel pitch, refresh/control constraints and
  long-term serviceability matter earlier.
- Retail/Church/Fixed: physical dimensions, viewing distance, installation access and
  project timing normally dominate early qualification.

The system asks for one highest-value missing fact at a time. It never recommends a
specific pitch, brightness, controller or commercial term unless that value exists in
product/customer context.

## Decision-maker coverage

A contact explicitly marked `decision_maker` is authoritative. Titles may provide
supporting evidence for coverage but must not silently mutate the contact role.

For a real LED opportunity, the coach should distinguish between:

- commercial authority: Owner/Founder/CEO/Purchasing/Procurement/Buyer;
- project authority: Project Manager/AV Manager/Technical Director/Engineer;
- finance is useful later but does not replace project/commercial ownership.

If the account lacks relevant authority, coach the next action as contact enrichment or
referral discovery instead of continuing generic follow-up to a weak contact.

## Customer 360

Customer 360 is a read model only. It aggregates, without duplicating CRM state:

- account record and explainable sales score;
- contacts and decision-maker coverage;
- open/closed opportunities and qualification progress;
- new/recent buying signals and their source evidence;
- open tasks;
- recent inbound messages and sends;
- quotes;
- one concise list of current risks and next-best actions.

No new editable customer truth is stored in Customer 360 itself.

## Opportunity Coach

For every open opportunity calculate:

- qualification completeness;
- next-step health (missing, overdue or dated);
- stage staleness;
- decision-maker coverage;
- recent buying-signal support;
- a health score and severity;
- the single best next action.

The deterministic safety net may create at most three internal `create_task` proposals
per Agent cycle. It never sends a message. Existing autonomy controls decide whether a
proposal waits for Allen or becomes an internal task automatically.

High-priority examples:

- quoted/negotiation deal with no next action date;
- overdue next action;
- live project missing both dimensions and application/environment context;
- quoted deal with no decision/project authority identified;
- stale live project where a fresh buying signal exists but nobody owns follow-up.

## Buying signals

`backend/app/sales_intelligence.py` already owns the canonical `buying_signals` table,
source URL, confidence, fingerprint and status. This phase consumes that model in
Customer 360 and Opportunity Coach. It does not add a duplicate signals table.

Future collectors may write into the same API/schema for tenders, hiring, exhibitions,
project news and social evidence.

## Safety boundaries

- Agent does not decide price, discount, payment terms or delivery promises.
- Qualification gaps produce questions/tasks, not fabricated technical values.
- Title heuristics never automatically promote a person to a CRM role.
- No autonomous cold social initiation is introduced here.
- Customer-facing replies remain behind the existing reply-draft and autonomy paths.

## Acceptance

- Existing databases receive additive opportunity columns without data loss.
- Playbook returns application-aware ordered gaps and one next question.
- Customer 360 combines contacts, opportunities, signals, tasks, replies/sends and
  quotes without creating a second source of truth.
- Opportunity Coach detects missing/overdue next steps and missing decision authority.
- Repeated Agent cycles do not duplicate the same coaching proposal.
- Full backend pytest and frontend production build remain green.

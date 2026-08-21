# Comprehensive Audit — LED Display Sales Agent

**Date:** 2026-08-21  
**Scope:** customer development, CRM truth, autonomous operation, sales judgment, safety, learning and runtime reliability

## Executive conclusion

The product is no longer a simple outreach tool. The repository already contains most
of the structural pieces of an autonomous salesperson: lead discovery, qualification,
contact/channel data, outreach history, sequences, inbox ingestion, intent
classification, reply drafting, opportunities, quotes/orders, buying signals, sales
priority, an Agent mission, daily planning, proposal/approval execution, conversation
handoff, learning, deliverability safeguards and reporting.

The main design problem is therefore **not missing AI chat**. It is closing the loop
between these pieces so the system continuously owns customer attention and improves
from outcomes. PR #1 fixes the first critical operational gap: an Account Brain for
contacted customers, independent background scheduling, missed-plan recovery, correct
idempotency, consistent in-flight state and CI regression gates.

The remaining work below is ordered by business impact rather than novelty.

---

## 1. What is already strong and should not be replaced

### CRM and action truth

The repository already separates durable business facts from model reasoning: leads,
contacts, outreach, inbox, activities, opportunities, quotes/orders, buying signals and
Agent proposals are stored as explicit records. This is the correct foundation for an
operator Agent. Do not replace it with an LLM memory database that becomes a second CRM.

### Safety architecture

The proposal/autonomy spine is a good design. Each action type has `off / propose /
auto`, and the executor reuses normal send/business paths rather than introducing a
second unsafe route. Quote/negotiation takeover, do-not-contact, bounce suppression,
mailbox quota and conversation ownership are valuable constraints, not friction to
remove.

### Evidence discipline

Sales Intelligence scores are explainable and buying signals require provenance.
Reply drafting also treats unsourced numbers as defects. This is much closer to a real
B2B salesperson than a generic autonomous-agent loop.

### Learning signal

Rejected proposals and Allen-edited drafts are already retained as learning data. This
is the right raw material for personalization because it measures actual corrections,
not synthetic self-critique.

---

## 2. P0 — operational gaps fixed in PR #1

### 2.1 Account attention gap — fixed

**Old behavior:** already-contacted customers could disappear if there was no new reply,
open task, active sequence or stalled opportunity event.

**Fix:** deterministic Account Brain scans contacted accounts with no owner for the next
step, calculates a conservative 5/7/14-day follow-up due date, reuses the existing
explainable score/next-best-action and produces at most three internal task proposals per
cycle.

### 2.2 Scheduler coupling — fixed

**Old behavior:** `OUTREACH_AUTO_POLL=0` stopped the entire background loop, not just
email polling.

**Fix:** email polling, social scan, website recheck, sequence hygiene and Agent execution
now share an independent operating cycle rather than one master email switch.

### 2.3 Missed morning plan — fixed

**Old behavior:** starting/waking the local PC after 12:00 meant no automatic plan that
day.

**Fix:** bounded afternoon catch-up until the report hour, reusing the existing attempt
limit and retry cooldown.

### 2.4 Plan idempotency collision — fixed

**Old behavior:** different same-day batch actions of the same kind could share the same
fingerprint because the validated payload was not represented in the dedupe key.

**Fix:** exact validated payload gets a stable digest; exact repeats still collapse but
different batches survive.

### 2.5 In-flight visibility — fixed

Approved/running proposals are now consistently treated as open work in the planner and
summary counts.

### 2.6 Regression gate — fixed

The repository previously had no GitHub Actions workflow. PR #1 adds backend pytest and
frontend production-build checks with all external test I/O explicitly disabled.

---

## 3. P1 — what is still required for “another Allen”

### 3.1 Sales Playbook / LED domain brain

**Current gap:** the reply drafter is excellent at not inventing facts, but its explicit
LED-domain knowledge is still thin. Safety is not the same as senior sales judgment.

Build one versioned `Sales Playbook` consumed by planning, replies and opportunity
coaching. It should encode decision logic rather than unverified product claims:

- distinguish Rental / Fixed Installation / DOOH / Retail / Sports / Church / Control
  Room / Broadcast / XR / corporate meeting-room buying motions;
- qualification order: application → indoor/outdoor → screen dimensions → viewing
  distance / pitch rationale → environment/brightness → quantity → destination →
  installation/maintenance → control/camera constraints → timing/decision process;
- ask one highest-information question at a time instead of sending a questionnaire;
- rental/XR: prioritize cabinet format, refresh/camera behavior, rigging, fast service,
  weight and mixed 500×500/500×1000 needs where facts support it;
- fixed installation: prioritize exact dimensions, front/rear maintenance, structure,
  environment and service access;
- outdoor: prioritize brightness/environment, waterproofing/structure constraints and
  service access without inventing ratings/specs;
- fine pitch/COB/GOB: establish viewing distance/use case and durability needs before
  recommending technology;
- never turn a sales heuristic into a promised specification.

The product catalog and proven project cases should be retrieved as evidence, not baked
into prompts as facts that can go stale.

**Acceptance:** senior-sales test scenarios evaluate the next question/action, not just
English quality.

### 3.2 Customer 360 / stage ownership

Today customer truth is distributed across outreach, inbox, notes, tasks, opportunities,
quotes, sequences and proposals. That is correct storage, but the Agent still needs a
single derived timeline/state view.

Add a deterministic `Account State` projection with:

- last inbound / last outbound / last meaningful interaction;
- current owner (Agent vs Allen) per channel;
- lifecycle: prospect → contacted → engaged → qualified → requirements → quoted →
  negotiation → won/lost/nurture;
- current project facts and explicitly unknown fields;
- next action, owner, due date and why;
- active sequence/task/proposal conflict detection;
- inactivity age by lifecycle stage.

Do not make stage an LLM-only label. The model may propose a transition; deterministic
business events should confirm it.

### 3.3 Source-specific buying-signal collectors

The data model supports project/hiring/exhibition/distributor/tender/social/site-change
signals, but a model is only as proactive as its sensors.

Implement collectors separately with provenance and confidence:

1. customer website changes and project/news pages;
2. exhibition exhibitor/visitor lists relevant to AV/LED/signage;
3. public tenders/RFP sources by target market;
4. hiring signals for AV/LED/project roles;
5. public social/company posts indicating installations, venue openings or inventory;
6. distributor/brand-page changes.

Each signal needs source URL, observed date, evidence snippet, confidence, expiry and
fingerprint. Never use a generic “AI web search” result as an untraceable intent fact.

### 3.4 Decision-maker/contact enrichment

Discovery can find companies, but the next bottleneck is often “right company, wrong
person.” Build an enrichment queue that prioritizes high-fit accounts missing Owner /
Purchasing / Project / AV decision roles.

Store every proposed email/phone/social handle with source, observed date, confidence and
verification status. Prefer public company evidence. Separate role mailbox from named
person. Never silently overwrite a verified contact with a model guess.

### 3.5 Opportunity coach after qualification

The Agent should continuously audit open opportunities for missing deal mechanics:

- project facts still unknown;
- customer decision date / installation deadline;
- decision maker and technical approver;
- quotation sent but no explicit follow-up date;
- technical issue blocking quote;
- accepted quote not converted to order;
- payment/production/shipment milestone overdue.

It may recommend the next action and draft non-commercial follow-up. Pricing, discount,
payment terms and delivery commitments remain Allen-only.

### 3.6 Nurture and reactivation

Not every silent prospect should receive endless follow-ups. Add an explicit nurture
state after the normal sequence ends. Reactivate only on one of:

- fresh buying signal;
- meaningful website/project change;
- new contact/decision maker;
- elapsed long-term nurture interval;
- Allen manual trigger.

This keeps Account Brain from turning into a perpetual reminder engine.

---

## 4. P1 — learning that actually improves sales

### 4.1 Structured learning from Allen edits

Current edit/reject data is valuable but should be converted into features:

- tone correction;
- wrong intent;
- wrong next question;
- factual omission;
- technical mistake;
- timing mistake;
- customer not worth pursuing;
- commercial boundary crossed.

Promote a lesson to the playbook only after repeated evidence. One correction should not
rewrite global behavior.

### 4.2 Outcome-aware template experimentation

The system already detects campaigns with enough sends and zero replies. Extend this to
controlled experiments:

- segment by country + ICP + use case + channel;
- minimum sample before judging;
- measure positive reply / qualified reply, not opens;
- one changed variable per experiment;
- champion/challenger promotion only after threshold;
- hard stop on bounce/complaint deterioration.

The Agent can propose experiments; it should not autonomously rewrite every campaign
from tiny samples.

### 4.3 Sales-quality evaluation suite

Add a fixture library of realistic LED conversations and expected behavior. Examples:

- “Need 18 sqm outdoor screen” with no dimensions;
- rental company asking P3.91 stock/pricing;
- XR studio asking refresh/camera requirements;
- buyer gives drawing whose calculated area conflicts with stated sqm;
- customer asks quote before destination/size is clear;
- Korean customer negotiates payment terms;
- customer has gone silent after quote;
- rejection / unsubscribe / referral.

Tests should assert required questions, forbidden promises, ownership transition and next
action — not exact prose.

---

## 5. P2 — true 24/7 autonomy

The current product is local-first. While the PC/process is off, the Agent is off. A
true always-on salesperson requires a durable runtime, not a bigger model.

### Recommended architecture

- hosted API/worker with durable queue;
- scheduler jobs stored in DB, not only process memory;
- leases/idempotency keys on executions;
- restart-safe retry policy by action risk;
- secrets in a managed secret store;
- channel connectors designed for server operation;
- audit log for every external action;
- health/heartbeat + stale-worker alert;
- local UI may remain the control cockpit.

Do not migrate everything to cloud at once. Start with read-only sensing + planning,
then email, then only channels whose platform/session model supports reliable server-side
operation.

---

## 6. P2 — deliverability and compliance operations

Existing bounce safety is a strong start. Add operational controls:

- timezone-aware business-hour sending by recipient market;
- cross-channel frequency cap per account;
- global suppression + reason + source + timestamp;
- mailbox/domain health dashboard;
- SPF/DKIM/DMARC configuration checks where technically available;
- complaint/unsubscribe trend alerts;
- campaign-level bounce and positive-reply quality;
- regional policy configuration rather than one universal outreach rule.

Legal/compliance rules differ by jurisdiction and should be configurable and reviewed,
not invented by the Agent.

---

## 7. P2 — observability and economics

Add an Agent operations dashboard with:

- runs succeeded/failed/paused;
- proposals by kind and acceptance/edit/rejection rate;
- customers recovered by Account Brain;
- time from inbound reply to first action;
- overdue opportunities/tasks;
- model calls, latency and estimated cost by task;
- discovery cost per qualified/contactable lead;
- qualified replies and opportunities created per campaign;
- Agent-caused incidents and safety stops.

This answers the business question: “Is the Agent creating qualified pipeline, or only
doing more activity?”

---

## 8. Recommended autonomy ladder

Do not switch every dial to `auto` on day one. A senior salesperson earns autonomy by
risk class.

### Level 1 — auto immediately after regression verification

- create internal tasks;
- stop sequence after explicit reply/rejection;
- deterministic Account Brain reminders;
- website rechecks and source-backed signal capture;
- qualified discovery/import under the existing quality gate.

### Level 2 — auto after mailbox/channel health is verified

- enroll qualified leads into proven language-matched sequences;
- first-touch email using Allen-approved templates and existing quota/bounce guards;
- routine inquiry/spec/sample replies that contain no flagged commercial/technical
  assertion.

### Level 3 — always human-owned

- price and quotation amount;
- discount;
- payment terms;
- committed production/delivery date;
- strategic negotiation;
- unusual technical claim without approved evidence;
- high-value account exception handling.

This is the practical meaning of “another Allen”: the Agent owns attention, preparation,
routine execution and memory; Allen owns irreversible commercial judgment.

---

## 9. Target end-state

A fully developed version should behave like this without Allen opening the CRM:

1. continuously senses inboxes, logged-in channels and approved public sources;
2. finds and qualifies new target companies;
3. enriches the right decision contact with evidence;
4. selects a proven message/sequence and sends within safety limits;
5. remembers every interaction and updates deterministic account state;
6. answers routine customer questions from evidence;
7. detects when a real LED project exists and gathers missing requirements one useful
   question at a time;
8. hands pricing/negotiation to Allen with a complete brief;
9. resumes ownership when Allen hands the conversation back;
10. watches silent accounts, quotes and orders for the next due action;
11. learns from Allen edits and actual qualified outcomes;
12. explains every action, source, risk and result after the fact.

That is materially different from a chatbot. It is a supervised autonomous sales
operating system.

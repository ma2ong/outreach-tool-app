# Product Requirements Document: Autonomous LED Sales Agent

**Version**: 1.0  
**Date**: 2026-08-20  
**Quality Score**: 93/100  
**Status**: Phase D1 implemented and verified

## Executive summary

Spec 22 gave the system perception, planning, memory, execution and learning, but the
real pipeline still breaks between discovering a candidate and turning it into a
contactable lead. A discovery run can finish successfully while leaving every candidate
behind a manual checkbox. A failed morning plan also marks the whole day as done.

Phase D turns the assistant into a duty-bound operator: it has a persistent sales
mission, wakes on a schedule, retries bounded failures, imports only evidence-backed
prospects, enrolls qualified contacts into the right follow-up sequence, and records
what happened. Allen should spend time on quote/negotiation decisions and exceptions,
not on moving rows between screens.

## Problem statement

**Current situation**

- Agent discovery ends at a candidate list and requires manual import.
- Imported leads require another manual step or another day's plan before nurture.
- The planner may say discovery is needed while returning zero executable actions.
- One model/network failure suppresses planning for the rest of the day.
- The Agent has no explicit persistent mission defining markets and acquisition quality.

**Proposed solution**

Add a mission-driven operator layer around the existing Agent. It must close the
discovery-to-sequence gap without creating a second send path or weakening any guard.

## Success metrics

- Manual operating touches: only quote/negotiation, high-risk exceptions and policy
  changes require Allen by default.
- Reply SLA: a supported inbound reply is classified and acted on within 15 minutes.
- Acquisition: meet the configured daily number of qualified, contactable new leads.
- Auto-import precision: at least 90% of audited imports are genuine target buyers.
- Safety: zero sends to do-not-contact, invalid/bounced or duplicate accounts.
- Reliability: a transient planning failure retries up to three times and is visible.
- Model resilience: draft/planning prefers the configured backend and automatically
  falls back to another configured backend during quota or availability windows.
- Auditability: every autonomous discovery/import/enrollment records counts and reasons.

## Personas

### Allen — owner and closer

- Wants a second self to operate prospecting every day.
- Handles pricing, negotiation, strategic accounts and exceptions.
- Needs concise outcomes and warnings, not another task list to administer.

### Sales Agent — operator

- Works from a persistent mission and real pipeline state.
- Uses only validated actions and existing templates/sequences.
- Stops when evidence or authority is missing.

## Core user stories and acceptance criteria

### D1. Persistent sales mission

As Allen, I want to define target markets, daily qualified-lead target, minimum fit and
automatic sequence enrollment so the Agent works toward my priorities without asking
for the same instructions each day.

- Mission is stored in SQLite and shown in the Agent settings.
- Invalid/empty mission values are normalized safely.
- The planner receives the mission in its world state.

### D2. No-empty-plan fallback

As Allen, I want the system to act when the model correctly identifies an empty lead
pool but returns no action.

- If today's qualified acquisition target is unmet and no discovery is pending, an
  evidence-backed `discover_run` proposal is created.
- It rotates configured markets rather than searching one country forever.
- It never fabricates lead IDs, templates or a customer message.

### D3. Qualified automatic import

As Allen, I want autonomous discovery to import only sendable target buyers.

- Candidate is not excluded, blocked or duplicate.
- Public email has valid syntax.
- ICP score meets the configured minimum (default 75).
- Candidate has a website-derived brief or hook for personalization.
- A candidate with a detected country outside the requested market is rejected rather
  than relabeled as the target country.
- Rejected candidates remain visible with a machine-readable reason.
- Manually approved discovery keeps the current review-and-checkbox flow.

### D4. Automatic nurture handoff

As Allen, I want newly imported prospects to enter the correct existing sequence.

- South Korea uses an active Korean email sequence; other markets use English.
- Invalid emails are not enrolled.
- Enrollment uses `sequences.enroll_leads`; sending remains in the existing autosend
  scheduler with all caps and suppression rules.
- Missing sequence is reported, not silently ignored.

### D5. Bounded recovery

As Allen, I want a transient model/network failure to retry without burning unlimited
quota or making the Agent silently dead for a day.

- If the model is unavailable while today's acquisition target is unmet, immediately
  run the deterministic discovery fallback; it still uses the normal quality gates.
- If no useful fallback exists, morning planning retries after a cooldown, at most
  three attempts per day.
- A successful or valid empty plan marks the day complete.
- Attempt count and last failure are visible in Agent status.

## Safety boundaries

- Quote and negotiation remain human-only hard rules.
- Cold social DMs remain manual.
- The Agent never writes cold copy; it uses existing templates and sequences.
- New action kinds default to `propose`; autonomy changes are explicit.
- Auto-import cannot lower the configured minimum below 75 in D1.
- Real-data verification uses a copied database and does not execute external sends.

## Phase plan

### Phase D1 — close the operating loop (this wave)

- Mission settings and API/UI.
- Deterministic discovery fallback.
- Shared import service with strict auto-qualification.
- Auto-enroll after autonomous discovery.
- Bounded planning retries and status visibility.

### Phase D2 — outcome-aware operator

- Durable run ledger and incident escalation.
- Daily goal completion score and “why target missed”.
- Campaign/market allocation based on statistically sufficient outcomes.
- Automatic pause when bounce/rejection thresholds degrade.

### Phase D3 — conversational salesperson

- Thread-level conversation state and promised-next-action tracking.
- Follow-up drafted from conversation commitments, not only fixed day offsets.
- Human takeover/resume protocol for negotiations and strategic accounts.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Garbage candidates pollute CRM | High | Strict evidence/email/fit gate, dedupe, screening, audit reasons |
| Sender reputation damage | High | Existing verification, bounce suppression, caps and autosend path only |
| Model plans nothing or malformed actions | Medium | Deterministic fallback and whitelist validation |
| Retry burns model quota | Medium | Cooldown plus three-attempt daily ceiling |
| Social account restriction | High | No autonomous cold social conversation |
| Agent oversteps commercial authority | High | Quote/negotiation code-level prohibition |

## Completion evidence for D1

- Focused unit/API tests for mission, fallback, quality gate, auto-import, language
  enrollment and retry behavior.
- Full backend suite passes.
- Frontend production build passes.
- Fresh DB migration and copied-real-DB schema/status checks pass.
- No real message or live social action is executed during verification.

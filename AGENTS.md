# AGENTS.md — MCVISUAL Outreach Tool

## Product goal

This repository is Allen's local-first LED display sales operating system. Optimize for
one outcome: a trustworthy digital salesperson that can find, qualify, contact and
follow up with prospects while Allen only handles high-risk decisions and pricing.

## Non-negotiable sales rules

- Allen owns all pricing, discounts, payment terms and delivery promises. The Agent may
  summarize a quote request and create a task, but must never answer it with a number.
- Every external message must use the existing send/reply paths so daily caps,
  do-not-contact, bounce suppression and per-company limits remain in force.
- Never auto-start a new WhatsApp/Instagram/Facebook conversation. Platform risk stays
  behind the existing manual cold-DM workflow. Replies in existing conversations may be
  automated only through the Agent autonomy controls.
- Unknown, low-confidence or weakly sourced data is a reason to stop or ask, not guess.
- All autonomous actions must leave a durable proposal/run record with reasons and
  results. `auto` skips approval; it never skips audit.
- Tests must never open the real `backend/outreach.db`, send a message, launch a social
  browser, or call a live model/search service.

## Development workflow

1. Write or update the numbered spec before changing behavior.
2. Add a failing test for each new rule or bug.
3. Implement the smallest path that makes the test pass.
4. Run focused tests, then the full backend suite and frontend production build.
5. For database changes, verify both a fresh temporary DB and a copied real DB.

## Architecture boundaries

- `backend/app/agent/`: perception, mission, planning, memory, proposals and learning.
- `backend/app/agent/executors.py`: delegates approved actions to existing business
  modules; it does not recreate sending, sequence or CRM logic.
- `backend/app/discovery.py`: shared discovery qualification/import rules used by both
  the API and Agent. Do not let the browser and Agent implement different gates.
- `backend/app/api/`: transport and validation only; business rules belong in modules.
- `frontend/src/components/AgentPanel.tsx`: mission, autonomy, run health and audit UI.

## Repository hygiene

- Secrets and the real customer database stay untracked.
- Keep changes scoped to the active numbered spec.
- Do not commit or push unless Allen explicitly asks.

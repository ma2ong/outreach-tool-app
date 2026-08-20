# Spec 26 — Conversation ownership and promise tracking

**Status:** implemented and verified  
**Date:** 2026-08-20  
**Depends on:** Specs 22, 24 and 25

## Problem

The Agent can classify and draft a reply, and it correctly refuses to quote. It does
not yet own the conversation as a durable state. After Allen takes over a negotiation,
a later simple-looking message could be drafted by the Agent again. A reply that says
“I will confirm and come back” can also be sent without creating the promised next step.

## Required behavior

### Per-channel ownership

- Persist one state per customer and channel: owner (`agent` or `allen`), state
  (`waiting_us`, `waiting_customer`, `human_takeover`, `closed`), reason, source message,
  next action and due date.
- Quote and negotiation intents immediately transfer that channel to Allen.
- A reply older than seven days, or without a trustworthy timestamp, is never treated
  as newly arrived: transfer it to Allen and create a review task instead of drafting.
- While Allen owns a channel, subsequent replies never receive an Agent draft; they
  become an internal reminder tied to the new message.
- Allen can explicitly take over or return a channel to the Agent from the Agent page.
- Returning ownership does not send anything or restart an old sequence automatically.

### Promise tracking

- When a draft leaves a question unanswered, the draft proposal carries that fact.
- After the reply is actually sent, create a next-day high-priority task to deliver the
  missing answer and store it as the conversation's next action.
- A sent reply with no open commitment moves to `waiting_customer` without inventing a
  task.
- Failed or merely proposed replies do not move to `waiting_customer`.
- Drafting records the backend that actually produced the reply. A Claude quota window
  may fall back to configured DeepSeek/API, while the same evidence and pricing guards
  remain mandatory.

### Visibility

- Agent status shows all channels currently owned by Allen, with company, reason and
  next action.
- Ownership transitions remain queryable in SQLite; no state exists only in browser
  memory.

## Hard boundaries

- Takeover never grants the Agent permission to quote or negotiate.
- Resume does not auto-send, auto-enroll or clear do-not-contact.
- Conversation state cannot override inbox message evidence or channel send guards.

## Acceptance evidence

- Tests cover quote takeover, draft suppression during takeover, explicit resume,
  post-send waiting state and promised-next-action creation.
- API and Agent UI expose takeover/resume.
- Full suite/build and copied-database UI verification pass.

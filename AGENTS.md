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
- Do not auto-start a new WhatsApp/Instagram/Facebook conversation unless Allen has
  explicitly switched that channel to `auto` (see `docs/53`), which costs a typed
  confirmation and is per channel. Default is `manual`: the Agent prepares the day's
  queue and a person presses send. Nothing may raise that setting on his behalf — not a
  migration, not a seed, not a default. The risk did not change when the switch was
  added: a banned Instagram account is gone, and the WhatsApp number carries WeChat and
  every customer contact. What changed is who decides to spend it.
- Unknown, low-confidence or weakly sourced data is a reason to stop or ask, not guess.
- All autonomous actions must leave a durable proposal/run record with reasons and
  results. `auto` skips approval; it never skips audit.
- Tests must never open the real `backend/outreach.db`, send a message, launch a social
  browser, or call a live model/search service.

## When a guard says no

A block is a stop, not a puzzle to route around. `message_guard`, the daily caps, the
do-not-contact list, the language check on enrollment and the pricing rule above all
refuse specific actions, and the only legitimate response is to reach the same goal a
genuinely safer way — a smaller batch, a message that actually says something about the
company, a task for Allen instead of a number.

What is never adapting is the same action wearing a lower signature:

- writing "very competitive, around 15% below market" because a figure with a currency
  symbol would be caught — the pricing rule is about committing Allen to a price, not
  about the characters used to write it;
- padding a template with the company name so the personalisation check passes while
  the message still says nothing about them;
- splitting a batch across runs to get under a daily cap, or sending from a second
  mailbox because the first is capped;
- reaching a customer through a channel that has no guard on it because the guarded one
  refused.

Only the first of those is caught mechanically today (`message_guard` reads currency
next to a number). The rest hold because they are written down here, which is the honest
state of it — a rule nobody enforces is worth stating only if everyone reading this
treats it as binding anyway. Each of those is a new and riskier action, not a retry. The honest path is to report the
block with its reason and what was being attempted, and — where the action genuinely
should proceed — put it in front of Allen unchanged.

The same rule binds whoever is changing this codebase: a guard that is in the way is
either wrong (change the rule in its spec, in the open) or right (do the work it is
asking for). Loosening a check so a test passes, or so today's batch goes out, is the
same move as the agent base64-ing a command.

## Development workflow

1. Write or update the numbered spec before changing behavior.
2. Add a failing test for each new rule or bug.
3. Implement the smallest path that makes the test pass.
4. Run focused tests, then the full backend suite and frontend production build.
5. For database changes, verify both a fresh temporary DB and a copied real DB.

## Two agents, two worktrees

Claude and Codex both work on this repository. On 2026-08-31 they were editing the same
working tree and swept each other's uncommitted files into their own commits — twice, in
opposite directions. Nothing was lost either time, but both commit messages described
less than the commit contained, which is the kind of quiet mismatch that makes history
untrustworthy. Git has one index per working tree; `git add -A` takes whatever is there.

So each agent gets its own working tree on its own branch:

| Directory | Branch | Who |
|---|---|---|
| `C:\Users\Administrator\outreach-tool` | `main` | **the live install** — runs the server Allen uses, owns `backend/outreach.db` |
| `C:\Users\Administrator\outreach-claude` | `claude/work` | Claude |
| `C:\Users\Administrator\outreach-codex` | `codex/work` | Codex |

Work, test and commit on your own branch. Merge to `main` when Allen asks; that is where
the app is built and served from.

**A second server cannot double-send, and it is worth knowing why.** The first instinct
is that two servers on one database would both see the same due queue and mail every
customer twice. They would not: `runtime_leases` is a row in that database, owned by
`mode:host:pid:uuid`, and `run_leased_cycle` returns `acquired: False` to anyone who
finds it held and unexpired — the second process stands by without running a cycle.
That is what the lease is for.

Run the preview anyway, because a second contender still muddies the picture: it
competes for the lease, so whichever process wins is decided by timing, and the loser's
idle standby writes noise into a log Allen reads when sending looks stuck.

```
.\scripts\dev_instance.ps1 -Port 8020
```

It reads the live database so the screens show real rows, and every scheduler —
autosend, the social queue, the Agent, reply polling, website rechecks — is off, so it
never enters the contest. Pick a free port; 8000 and 8010 are taken.

Two things a fresh worktree does not have, because they are correctly untracked:
`backend/auth_password.txt` (the smoke suite logs in with it) and `backend/outreach.db`
(point `OUTREACH_DB` at the live one instead of copying it). `npm install` once in
`frontend/`.

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

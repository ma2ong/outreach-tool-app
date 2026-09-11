# Spec 107: Continuous LED sales operator

Implement the full 2026-09-08 audit, not just its first package.

## Delivery and completion gates

- [x] A: integrate current main, truthful capability states and partial/skip outcomes,
  working navigation and isolated Playwright CI.
- [x] B: executable work contracts, atomic claims, durable send intent and unknown
  outcomes; uncertain sends must not be blindly retried.
- [x] C: continuous budgeted planning, fair customer selection, next-action coverage
  after replies, commitments and explicit human handoff.
- [x] D: evidence-backed discovery and configurable routing with migration parity.
- [x] E: structured LED requirements, approved facts, attachment evidence, professional
  next questions and promise tracking.
- [x] F: owner-aware home, customer next-action card, guided activation and navigation.
- [x] G: versioned copy, correction lessons, outcome attribution and rollback.
- [x] H: isolated sales scenarios, fault injection, fresh/copied DB validation, full
  backend tests, frontend build, browser smoke and final diff review.

## A1: skipped work is not successful work

Disabled, not-configured and idle outcomes retain prior errors and success/output
timestamps. Partial outcomes retain both processed counts and failure details. Only an
actual successful attempt clears consecutive failures. Subsequent jobs still run after
a failed job. Legacy unspecified return values remain compatible.

Telemetry including connection cleanup is best-effort and cannot fail the observed job.
The UI must distinguish skipped work from recovered success.

Reply ingestion is the source-of-truth operation and must survive optional enrichment,
but enrichment exceptions are not silent: email and social poll results identify the
lead/message and failed stage, and runtime health becomes partial when any enrichment
failed after replies were safely stored. A later clean poll is the only success that
clears that capability error.

## A2: one stuck capability cannot freeze the operator

Each scheduled capability has an explicit wall-clock deadline. Crossing it records a
stalled state and allows later capabilities in the cycle to run, but it does not kill a
thread that may already have entered an external transport. The live invocation remains
registered, so later cycles observe it instead of starting a duplicate. When it finally
returns, its real success or failure is collected before that capability may run again.
Send intents remain the final duplicate-delivery guard.

There is one scheduler implementation. The pre-runtime autosend thread entrypoint is
removed so a future startup change cannot accidentally run email scheduling beside the
leased Worker with different health and retry semantics.

## A3: portfolio reads scale by query, not by customer

Dashboard, Sales Intelligence and Agent-world reads must bulk-load customer contacts,
signals, opportunities, outreach state and next-action evidence. Adding customers may
increase rows processed but must not add a fixed bundle of SQL statements per customer.
The single-customer score remains available for detail views. A regression fixture with
at least eighty customers keeps the portfolio summary below eighty SELECT statements;
the production-copy benchmark records both elapsed time and statement counts.

## A4: the web bootstrap does not own sales orchestration

`app.main` assembles FastAPI, initializes schema and starts the configured Worker; it
does not define jobs, their order, retry timing or the standalone Worker's database.
Job adapters live in `background_jobs`, generic deadline orchestration in `scheduler`,
and both embedded and standalone entrypoints in `worker`. The dependency direction is
one way: Worker code must not import the web application to run a cycle. The job order
remains reply poll, social scan, website recheck, sequence maintenance, email send,
social queue, contact naming and Agent planning.

## A5: every production launcher is duplicate-safe

The scheduled-task, local double-click and online-tunnel launchers all enter through
the same identity-aware runner. If port 8000 already belongs to this application they
reuse it; if another process owns the port they stop with a clear error. No supported
launcher invokes Uvicorn directly. Local and online launchers verify the application
identity before opening the dashboard or exposing a tunnel.

## A6: merged discovery readers keep their own availability truth

A discovery channel with several readers evaluates the selected reader's prerequisites,
not an unrelated reader's. In particular Google Playwright does not require the model
key used by the browser-use reader. Pure parser tests explicitly stub machine
prerequisites; merely injecting a runner never bypasses production safety checks.

## Boundaries

## B1: sequence delivery intent

Before calling a sequence transport, durably claim (enrollment_id, current_step).
Only one caller can claim that key, including callers holding a stale due queue.
Record lead, channel, target, rendered subject/body and timestamps for reconciliation.
Once transport is entered, any exception is an uncertain outcome, not permission to
retry. A crash leaves a pending intent with the same no-retry protection. Successful
transport and CRM bookkeeping finishes the intent as sent. Failure to persist a claim
must prevent transport. Existing send and business guards still run first. This slice
does not yet solve replies or cross-path caps.
An unresolved previous step also blocks claiming any following step of its enrollment.

Acceptance: injected post-send bookkeeping failure and transport timeout both suppress
a second send; a reentrant competing caller cannot send; pre-send guard rejection does
not reserve an intent. Never auto-expire intents into retryable work.
Sequence due dates use the operator's local date consistently; UTC midnight must not
hide a newly enrolled step during the Asian working morning.
The same local-sales-day rule applies to caps, task ownership, cooldowns, social scans,
rechecks, morning/report counts and relationship events.
Optional daily-report delivery failures remain non-fatal but become Agent capability
errors instead of being silently discarded.

## B2: reply delivery intent

An approved Agent email or social reply must durably claim its proposal before entering
the transport. Transport errors and post-send bookkeeping errors become unknown delivery
outcomes and the same proposal cannot enter the transport again. Pre-send guard failures
create no claim. The existing runtime reconciliation UI covers both sequence and reply
intents; confirming a reply as sent repairs the handled/conversation/note state without
transport, while confirming not sent permits an explicit retry. This does not loosen
do-not-contact, mailbox choice, social targeting or any pricing boundary.

## B3: proposal execution claim

Approval changes `pending` to an approved state with a compare-and-set transaction.
Execution then atomically claims `approved` as `executing` before invoking any handler.
Only one concurrent request may own either transition; all others fail visibly before
business I/O. An interrupted executing action is marked failed on restart and external
delivery still uses its durable intent for sent/unknown reconciliation.

## B4: background work stays on the request database

An API request may be served from an overridden, preview or test database. Every
background task spawned by that request must capture that connection's actual SQLite
file and reopen the same file; it must never fall back to an import-time `DB_PATH`.
This applies to campaign send, channel send, sequence send, social queue send,
discovery, classification and email verification.

A regression points the application's default path at a different sentinel database
and proves that the requested database receives the result while the sentinel remains
untouched. The regression must stub all network and message transports.

## B5: every outbound path has a durable transport claim

Manual email campaigns, manual browser-channel campaigns and both manual and automatic
social queues claim each rendered message after its guards and before transport. The
claim key identifies the customer, destination and exact rendered content; queue rows
also use their durable row id. A transport exception is an unknown outcome even when
the provider may have accepted the message, and repeating the request cannot enter the
transport until Allen explicitly reconciles it as not sent.

For social queue rows, marking the row sent is part of the claimed operation rather
than a later API-only bookkeeping step. Confirming an unknown campaign or queue send as
sent repairs outreach, campaign log and queue state without touching the transport.
Claim/schema work is initialized once per batch, not once per customer.

When a rotating mailbox is selected, its id is stored on the intent before SMTP. A
confirmed-sent reconciliation also repairs that mailbox's daily counter exactly once.
The safer ambiguity rule is conservative: if the process died after SMTP acceptance
but before it could persist the counter marker, confirmation may reserve one extra slot,
but it may never under-count a possibly delivered message and continue beyond the cap.

## C1: bounded continuous planning and fair prospect selection

Planning operates throughout the working day, at most six attempts per day and no more
than once per hour. It pauses while earlier proposals still await Allen, preventing an
ever-growing approval queue. A successful empty or fully auto-executed plan does not
declare the entire day finished: later account/reply state can trigger another bounded
pass. The shortlist must consider every eligible untouched account, rather than the
oldest 400 IDs, while the prompt still receives only the best twelve.
Mission progress reuses the autonomous-import qualification gate and additionally
requires a configured target market; DNC, wrong-market and evidence-free rows never
close the daily acquisition target.

## C2: replied-account next action and promises

Sending a complete reply leaves an Agent-owned next action: if the customer stays
silent for seven days, prepare one short evidence-bound follow-up through the existing
reply proposal/send path. At most two such warm follow-ups may be sent for one customer
turn; after that the conversation closes until a new inbound message or signal resets
it. A draft that promises information it could not source creates a durable high-priority
human-owned commitment and transfers the conversation to Allen instead of pretending
the Agent still owns it. New customer messages reset the warm-follow-up counter.

## E1: durable inbound attachment evidence

Email ingestion records the RFC Message-ID and attachment metadata (decoded filename,
content type, byte size and SHA-256) without storing or executing attachment bytes.
The stable message identifier deduplicates a re-polled email even when the provider
changes its Date representation. Attachment names are visible beside the reply so a
salesperson and the Agent know that requirements may be in a drawing or specification.
Attachment content remains untrusted and is not parsed until a separate allow-listed,
size-bounded parser is specified and tested.

## E2: customer-stated LED project facts

After a real reply is classified, deterministic extractors capture only values visible
in that message: pixel pitch, indoor/outdoor, dimensions with units, area, quantity,
brightness, refresh rate, viewing distance and explicit quarter timing. Every value
keeps the inbound message id and exact source quote. Generic prose produces no fact.

When exactly one open opportunity exists, a captured value may fill an empty matching
field. It never overwrites an existing value. A different later value is surfaced as a
conflict for confirmation instead of being guessed as a correction or a second project.
Customer and drafting views receive the sourced facts and conflict list, so the Agent
does not ask for known facts and does not hide contradictory dimensions/specifications.
Capture failure is reported in the Agent run; it cannot undo the already classified
reply or block other customers.

## D1: routing rules are operable, not hidden rows

Sequence routing exposes enabled state, priority, country, language, customer type and
destination sequence through CRUD-safe API operations and the Sequence screen. A
preview for a hypothetical customer shows the winning rule plus every matching
candidate in actual evaluation order, making priority conflicts visible before new
leads are enrolled. Editing or disabling a rule never rewrites historical enrollments.

Decision-maker research distinguishes a legitimate empty result from a search or page
adapter failure. Query failures are stored with the scan, aggregated by the bounded
sweep and returned by the Agent job, so runtime health becomes partial instead of
silently teaching the operator that no public contact exists.

## F1: one operating home and one customer next action

The sidebar groups the existing screens under five sales goals: today's work,
customers and conversations, development plan, opportunities and orders, and data and
settings. Grouping must not remove a route. Navigation accepts only declared page ids;
an invalid dashboard action cannot silently render a blank page.

The dashboard separates work the Agent will perform from decisions Allen must make.
In particular, due email sequence work belongs to Allen only while email autosend is
off; when it is on, the page shows the amount and send window under Agent work and does
not offer a second manual send as a required decision.

The customer drawer shows the current conversation owner, state, next action, due date
and reason before profile fields. Allen can explicitly take over, return the thread to
the Agent, or adjust its next-action date. Scheduling preserves the current owner and
state and writes a conversation event; it cannot create a second execution path.

## F2: guided activation uses existing business truth

A first-time operator sees one ordered commissioning path on the home page: explicitly
confirm target markets, verify a real send/receive mailbox login, approve at least one
product or public case as Agent knowledge, inspect a dry-run operating plan, and review
the autonomy boundary. Progress is inferred from the mission, mailbox verification,
approved knowledge and two review acknowledgements; there is no second configuration
store that can drift from the real system.

Reviewing autonomy never raises a permission. The preview names what the Agent may do,
what remains Allen-owned and the current email/social modes. The completion state says
the operator is prepared; live Worker/capability health remains a separate runtime fact.
Changing a mailbox password invalidates its prior verification. Empty and failed states
link to the exact existing screen that can resolve them.

## G1: learning is evidence, approval and scope — not prompt drift

Edited drafts remain immutable evidence of what Allen changed, but raw recent examples
must never become global prompt instructions merely because five edits exist. A
correction becomes an active lesson only after Allen names the lesson and explicitly
activates it. Every lesson records its category (fact, sales action, tone or timing),
applicable channel, market and customer type, source proposal ids, version, status and
an append-only lifecycle event. Drafting receives only active lessons whose declared
scope matches the current customer and channel.

Retiring a lesson immediately removes it from future prompts without deleting its
evidence. Re-activating it creates another auditable lifecycle event. The Agent page
shows unlearned correction examples, active/candidate/retired lessons and their scope;
no model-generated lesson may silently enable itself. Small samples may be reviewed,
but are labelled as weak evidence and never treated as an automatic winner.

## G2: outbound copy has immutable versions and safe rollback

Every human edit to a Sequence step snapshots the prior and resulting copy, including
subject, body, delay, channel and segment. History is append-only. Rolling back selects
an immutable historical version, runs it through the same preview/message guard as a
normal edit and stores the rollback as a new version; it never rewrites history or
bypasses a current safety rule. Existing repository-copy revert remains separate.

Copy experiment reporting attributes outcomes beyond a raw reply: meaningful human
reply, captured project requirements and open opportunity progress, deduplicated per
lead. Results below the configured minimum sample are explicitly `insufficient`; the
system reports evidence and never auto-promotes a winner.

Preserve historical enrollments, live data, existing copy and approved facts. Reuse
existing send paths and authorization. Pricing, terms and delivery promises remain
Allen-owned. Tests isolate external I/O. Commit, push and deployment follow AGENTS.

## Baseline and progress

2026-09-08: main 77b4159, Codex HEAD 929cd56 with pending reliability changes. Later
main behavior must be integrated without discarding either side. Old tests do not
validate the integrated baseline. No package has passed final acceptance yet.

Implementation checkpoint: Codex fast-forwarded to main 7a796a0, preserving the
pending patch with Git autostash db4b186. Resolved main.py conflict by retaining the
contact-name job in its original position and observing its failures. Spec 88 from the
pending patch is now 113; main's command spec remains 88. Added and verified regressions
for skipped/partial capability outcomes and declared-vs-legacy Sequence routing.
Full integrated suite initially reported 1812 passes and one outdated skip assertion;
that assertion now checks the explicit disabled result and the retained contact job.
Next checkpoint: added running_since and read-time stalled observation after 20 minutes;
this is diagnostic only, never cancellation or an automatic resend. Regressions passed
after first reproducing both missing states. Current integrated backend suite: 1817
passed (109.96s); frontend production build passed; isolated Playwright: 22 passed,
including authenticated login. Temporary API on port 8020 stopped after validation.
Git diff --check passed; changed/untracked file inventory contains no customer DB,
backup, log or credential files. This is not final acceptance of the whole roadmap.
Remaining A work includes job deadlines, all adapter partial-result mappings and
copied-DB migration validation. B-H remain open. Inspection of sequence_send confirms
the send-success/DB-write-failure uncertain-outcome gap still needs a durable send intent.

## Final acceptance — 2026-09-11

The integrated implementation in `codex/work` now satisfies A-H. This is source and
test acceptance only; it has not been committed, pushed, merged into the live `main`
worktree or deployed.

- After merging current `origin/main` (`210db7a`), Python 3.14.2:
  `python -m pytest backend/tests -q` -> 2,040 passed in 135.06s.
  Focused decision-maker/runtime fault injection -> 84 passed.
- `python -m compileall -q backend/app` passed. Exact backend dependency versions and
  GitHub Actions both target Python 3.14.
- `npm run build` passed: 75 modules; JavaScript 489.89 kB / 143.07 kB gzip.
  Production and complete `npm audit` both reported zero vulnerabilities.
- The isolated database/server smoke run disabled every external Worker capability;
  all 23 Playwright scenarios passed, including authenticated login, Dashboard,
  discovery, customers, lead detail, Inbox, Sequences, Agent, opportunities and orders.
  The temporary server was stopped and port 8022 was confirmed free.
- Current schema was exercised on both a fresh temporary database and an online,
  read-only-derived copy of the live database. `PRAGMA quick_check` returned `ok` for
  both; the fresh database has 35 tables / 8 sequences and the migrated copy has
  47 tables / 8 sequences. The source live database was never opened for writing.
- Production-copy performance: Sales Intelligence summary used 10 SELECT statements
  in 64.0 ms; the complete Agent world used 63 SELECT statements and 27.2-34.1 ms warm.
  The 80-customer regression also enforces fewer than 80 portfolio SELECT statements.
- Final review includes startup identity checks across every supported production
  launcher, one-way Worker dependencies, all outbound transport call sites, new broad
  exception paths, hard-coded secret patterns and repository hygiene. `git diff
  --check` passed. No customer database, backup, log, password, session key or browser
  authentication artifact is changed or untracked for inclusion; those local artifacts
  remain ignored.

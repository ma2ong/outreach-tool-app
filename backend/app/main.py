import datetime
import glob
import datetime as _dt
import os
import sqlite3
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import auth

from app.main_deps import get_conn, DB_PATH  # re-exported for tests / dependency overrides
from app.db import connect, init_schema
from app.api import leads as leads_api
from app.api import stats as stats_api
from app.api import send as send_api
from app.api import discover as discover_api
from app.api import channels as channels_api
from app.api import templates as templates_api
from app.api import sequences as sequences_api
from app.api import replies as replies_api
from app.api import verify as verify_api
from app.api import mailboxes as mailboxes_api
from app.api import classify as classify_api
from app.api import products as products_api
from app.api import inbox as inbox_api
from app.api import blocklist as blocklist_api
from app.api import opportunities as opportunities_api
from app.api import autosend as autosend_api
from app.api import readiness as readiness_api
from app.api import activities as activities_api
from app.api import contacts as contacts_api
from app.api import sales_documents as sales_documents_api
from app.api import social_queue as social_queue_api
from app.api import sales_intelligence as sales_intelligence_api
from app.api import decision_makers as decision_makers_api
from app.api import runtime as runtime_api
from app.api import agent as agent_api

BACKUP_KEEP = 14
REPLY_POLL_SECONDS = 900   # steady-state operating cycle
REPLY_RETRY_SECONDS = 60   # transient mail/DB failure or standby behind another leader
RECHECK_PER_DAY = 20       # website re-reads per day; each one is a live page fetch


def backup_db(db_path: str = DB_PATH) -> str | None:
    """Copy the DB into backups/ once per day; prune to the newest BACKUP_KEEP files."""
    if not os.path.isfile(db_path):
        return None
    bdir = os.path.join(os.path.dirname(os.path.abspath(db_path)), "backups")
    os.makedirs(bdir, exist_ok=True)
    dest = os.path.join(bdir, f"outreach-{datetime.date.today().isoformat()}.db")
    if not os.path.exists(dest):
        # A file copy can omit committed rows that still live in SQLite's WAL file.
        # The backup API takes a transactionally consistent snapshot while the live
        # app keeps serving reads/writes.
        tmp = dest + ".tmp"
        if os.path.exists(tmp):
            os.remove(tmp)
        source = sqlite3.connect(db_path, timeout=30)
        target = sqlite3.connect(tmp)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        os.replace(tmp, dest)
    for old in sorted(glob.glob(os.path.join(bdir, "outreach-*.db")))[:-BACKUP_KEEP]:
        os.remove(old)
    return dest


def auto_poll_replies() -> bool:
    """Pull replies so the inbox is current without Allen remembering to click 拉取邮件.

    An intentionally disabled poll is healthy for scheduler timing: email polling is one
    capability, not the master switch for every other autonomous job.
    """
    if os.environ.get("OUTREACH_AUTO_POLL", "1") == "0":
        return True
    from app import replies
    conn = None
    try:
        conn = connect(DB_PATH)
        return not replies.poll_all_replies(conn)["errors"]
    except Exception:  # noqa: BLE001 — best-effort background refresh
        return False
    finally:
        if conn is not None:
            conn.close()


def auto_scan_social() -> None:
    """Once a day, read logged-in WhatsApp/Instagram thread lists."""
    if os.environ.get("OUTREACH_AUTO_SCAN", "1") == "0":
        return
    from app import inbound
    from app.api.channels import ENGINE
    conn = None
    try:
        conn = connect(DB_PATH)
        if not inbound.should_scan_today(conn):
            return
        live = [c for c in inbound.CHANNELS if ENGINE.status(c) == "connected"]
        if live:
            inbound.scan_all(conn, ENGINE.scan_threads, channels=live)
    except Exception:  # noqa: BLE001 — a browser hiccup must not kill the operating loop
        pass
    finally:
        if conn is not None:
            conn.close()


def auto_recheck() -> None:
    """Once a day, re-read due lead websites, capped because each is live I/O."""
    if os.environ.get("OUTREACH_AUTO_RECHECK", "1") == "0":
        return
    from app import recheck, settings
    conn = None
    try:
        conn = connect(DB_PATH)
        today = datetime.date.today().isoformat()
        if settings.get(conn, "recheck_last_run") == today:
            return
        settings.set_value(conn, "recheck_last_run", today)
        recheck.sweep(conn, limit=RECHECK_PER_DAY)
    except Exception:  # noqa: BLE001 — a dead site must not kill the operating loop
        pass
    finally:
        if conn is not None:
            conn.close()


def auto_prune_sequences() -> None:
    """Keep the follow-up queue matched to who can actually be reached, both ways."""
    from app import sequences
    conn = None
    try:
        conn = connect(DB_PATH)
        sequences.block_unsendable(conn)
        sequences.reopen_sendable(conn)
    except Exception:  # noqa: BLE001 — housekeeping must not kill the operating loop
        pass
    finally:
        if conn is not None:
            conn.close()


def auto_send_sequences() -> None:
    """Run the daily email-sequence sender inside the same leader lease as the Agent.

    Historically this had a second daemon scheduler. With multiple web processes that
    meant multiple schedulers. Centralising it here makes the lease authoritative for
    *all* unattended sales execution while retaining the old environment switch name.
    WhatsApp/Instagram/Facebook remain manual-only.
    """
    if os.environ.get("OUTREACH_AUTOSEND_SCHEDULER", "1") == "0":
        return
    from app import autosend
    conn = None
    try:
        conn = connect(DB_PATH)
        if autosend.should_run(conn):
            autosend.run_once(conn, send_api.pick_sender(conn), send_api.DEFAULT_ATTACHMENT)
    except Exception as exc:  # noqa: BLE001 — a bad tick must not kill the loop
        # But it must not vanish either. pick_sender() is evaluated out here, so a
        # "no usable mailbox" error used to disappear without touching any status the
        # dashboard reads: the panel kept showing a five-day-old result with no reason.
        if conn is not None:
            try:
                from app import settings
                settings.set_value(conn, "autosend_last_result",
                                   f"{_dt.datetime.now():%m-%d %H:%M} 自动发送启动失败：{str(exc)[:110]}")
            except Exception:  # noqa: BLE001
                pass
    finally:
        if conn is not None:
            conn.close()


def auto_social_queue() -> None:
    """Prepare the day's social DMs, and send them only for channels set to `auto`.

    Building the queue is always safe — it writes rows and reaches nobody. Sending is
    gated per channel by a setting Allen had to type a confirmation to raise
    (`docs/53`), so the default path here still ends with a queue waiting for a person.
    """
    if os.environ.get("OUTREACH_SOCIAL_QUEUE", "1") == "0":
        return
    from app import social_autonomy, social_queue
    conn = None
    try:
        conn = connect(DB_PATH)
        social_queue.build_today(conn)
        social_autonomy.run_due(conn)
        # Only after the queue is empty for the day: one account both messaging
        # strangers and browsing strangers in the same minute is the most machine-like
        # pattern there is (docs/71 R2). social_watch checks that itself.
        from app import social_watch
        from app.api import channels as channels_api
        social_watch.watch(conn, channels_api.ENGINE, limit=3)
    except Exception:  # noqa: BLE001 — never take the operating loop down with it
        pass
    finally:
        if conn is not None:
            conn.close()


def auto_agent_run() -> None:
    """Run the autonomous sales operator against the current business state."""
    if os.environ.get("OUTREACH_AGENT", "1") == "0":
        return
    from app import decision_maker_radar
    from app.agent import account_brain, catchup, opportunity_coach
    from app.agent import run as agent_run
    conn = None
    try:
        conn = connect(DB_PATH)
        agent_run.run_once(conn)
        catchup.run_if_due(conn)
        account_brain.safety_net(conn)
        opportunity_coach.safety_net(conn)
        if os.environ.get("OUTREACH_AUTO_RESEARCH", "1") != "0":
            decision_maker_radar.sweep(conn)
    except Exception:  # noqa: BLE001 — the agent must not kill the operating loop
        pass
    finally:
        if conn is not None:
            conn.close()


def background_cycle() -> bool:
    """One ordered sales-operator cycle. The runtime lease is outside this function.

    Fresh replies are read first so a customer response can stop a sequence before the
    daily sender is considered. The Agent plans last, after all new operational facts are
    visible. `OUTREACH_AUTO_POLL=0` skips only email polling, not the rest of the cycle.
    """
    ok = auto_poll_replies()
    auto_scan_social()
    auto_recheck()
    auto_prune_sequences()
    auto_send_sequences()
    auto_social_queue()
    auto_agent_run()
    return ok


def reply_poll_loop() -> None:
    """Backward-compatible embedded worker, protected by the durable leader lease."""
    from app import runtime

    owner = runtime.owner_id("embedded")
    while True:
        try:
            result = runtime.run_leased_cycle(
                DB_PATH, background_cycle, owner=owner, mode="embedded", release_after=False)
        except Exception:  # noqa: BLE001 — a transient DB failure should retry, not kill the thread
            delay = REPLY_RETRY_SECONDS
        else:
            if not result["acquired"]:
                delay = REPLY_RETRY_SECONDS
            elif result["cycle_ok"] and result["email_poll_ok"]:
                delay = REPLY_POLL_SECONDS
            else:
                delay = REPLY_RETRY_SECONDS
        time.sleep(delay)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Idempotent: CREATE TABLE IF NOT EXISTS + additive column migration, so an
    # existing outreach.db picks up new tables/columns on upgrade without re-running migrate.
    from app.dedupe import normalize_all_websites
    from app.opportunities import ensure_schema as ensure_opportunity_schema
    from app.activities import ensure_schema as ensure_activity_schema, migrate_existing
    from app.contacts import ensure_schema as ensure_contact_schema, migrate_existing as migrate_contacts
    from app.sales_documents import ensure_schema as ensure_sales_document_schema
    from app.sales_intelligence import ensure_schema as ensure_sales_intelligence_schema
    from app.decision_maker_radar import ensure_schema as ensure_decision_maker_schema
    from app.runtime import ensure_schema as ensure_runtime_schema
    backup_db()  # the lead base is the business asset — snapshot before touching it
    conn = connect(DB_PATH)
    try:
        init_schema(conn)
        ensure_contact_schema(conn)
        migrate_contacts(conn)
        ensure_opportunity_schema(conn)
        ensure_sales_document_schema(conn)
        ensure_activity_schema(conn)
        ensure_sales_intelligence_schema(conn)
        ensure_decision_maker_schema(conn)
        ensure_runtime_schema(conn)
        migrate_existing(conn)
        normalize_all_websites(conn)  # idempotent data fix: consistent website form
        from app.replies import backfill_bounced_at
        backfill_bounced_at(conn)  # idempotent: bounce dates the inbox still remembers
        from app.agent.proposals import ensure_schema as ensure_agent_schema
        from app.agent.proposals import fail_interrupted
        ensure_agent_schema(conn)
        # Background executions die with the process; their proposals would otherwise
        # read 执行中 forever, neither finished nor failed.
        fail_interrupted(conn)
        # docs/86 R3. The copy ships with the code, so a fresh install having zero
        # sequences and asking the user to press 「载入现成话术」 is the product making
        # its own setup someone else's job — and skipping it silently makes every later
        # step do nothing. Only on a book that has none: an install where the user has
        # deleted or edited them is left exactly as it is.
        if not conn.execute("SELECT 1 FROM sequences LIMIT 1").fetchone():
            from app import seeds
            seeds.seed_templates(conn)
            seeds.seed_sequences(conn)
    finally:
        conn.close()
    # Desktop/local remains zero-config. Hosted web services disable this and run
    # `python -m app.worker` in a separate supervised worker process.
    if os.environ.get("OUTREACH_EMBEDDED_WORKER", "1") != "0":
        threading.Thread(target=reply_poll_loop, daemon=True,
                         name="outreach-embedded-worker").start()
    yield


app = FastAPI(title="Outreach Tool", lifespan=lifespan)

# 公网保护：有密码文件才生效（本地免密用法不变）。SPA 页面本身可公开（无数据），
# 数据和操作全在 /api 下，未登录一律 401，登录/状态接口除外。
_AUTH_EXEMPT = ("/api/login", "/api/auth/status", "/api/logout")


@app.middleware("http")
async def require_auth(request, call_next):
    path = request.url.path
    if path.startswith("/api") and path not in _AUTH_EXEMPT and auth.enabled():
        if not auth.verify_token(request.cookies.get(auth.COOKIE_NAME)):
            return JSONResponse(status_code=401, content={"detail": "login required"})
    return await call_next(request)

app.include_router(leads_api.router)
app.include_router(stats_api.router)
app.include_router(send_api.router)
app.include_router(discover_api.router)
app.include_router(channels_api.router)
app.include_router(templates_api.router)
app.include_router(sequences_api.router)
app.include_router(replies_api.router)
app.include_router(verify_api.router)
app.include_router(mailboxes_api.router)
app.include_router(classify_api.router)
app.include_router(products_api.router)
app.include_router(inbox_api.router)
app.include_router(blocklist_api.router)
app.include_router(opportunities_api.router)
app.include_router(autosend_api.router)
app.include_router(readiness_api.router)
app.include_router(activities_api.router)
app.include_router(contacts_api.router)
app.include_router(sales_documents_api.router)
app.include_router(social_queue_api.router)
app.include_router(sales_intelligence_api.router)
app.include_router(decision_makers_api.router)
app.include_router(runtime_api.router)
app.include_router(agent_api.router)
from app.api import conversations as conversations_api  # noqa: E402
app.include_router(conversations_api.router)
from app.api import auth as auth_api  # noqa: E402
from app.api import health as health_api  # noqa: E402
app.include_router(auth_api.router)
app.include_router(health_api.router)

_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="static")

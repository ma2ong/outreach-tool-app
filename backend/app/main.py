import datetime
import glob
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

BACKUP_KEEP = 14
REPLY_POLL_SECONDS = 900   # steady-state inbox refresh
REPLY_RETRY_SECONDS = 60   # until the first clean sweep — covers "network not up yet at logon"
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
    """Pull replies so the inbox is current without Allen remembering to click 拉取邮件
    — a missed pull means the sequences keep chasing people who already answered.
    Fully fault-tolerant: no Gmail password or a network hiccup just skips this round;
    the manual button still exists. Returns True when every mailbox was read."""
    if os.environ.get("OUTREACH_AUTO_POLL", "1") == "0":
        return False
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
    """Once a day, read the WhatsApp/Instagram thread lists — but only for channels
    already logged in. Forcing a browser window open on a schedule would both surprise
    Allen and, on a session that needs a re-scan of the QR code, do nothing useful."""
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
    except Exception:  # noqa: BLE001 — a browser hiccup must not kill the poll loop
        pass
    finally:
        if conn is not None:
            conn.close()


def auto_recheck() -> None:
    """Once a day, re-read the websites of leads whose check has come round.

    Capped at RECHECK_PER_DAY because every one is a real page fetch, and silent by
    design: a check that found nothing writes nothing anywhere Allen has to look."""
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
    except Exception:  # noqa: BLE001 — a dead site must not kill the poll loop
        pass
    finally:
        if conn is not None:
            conn.close()


def reply_poll_loop() -> None:
    """Keep pulling for as long as the app runs.

    Polling used to happen exactly once, at startup. The app now auto-starts at logon,
    where the network is routinely not up yet — the pull timed out, the failure was
    swallowed, and nothing ever retried, so replies stayed invisible until someone
    clicked the button. Retry fast until the first clean sweep, then settle down."""
    if os.environ.get("OUTREACH_AUTO_POLL", "1") == "0":
        return
    while True:
        ok = auto_poll_replies()
        auto_scan_social()
        auto_recheck()
        time.sleep(REPLY_POLL_SECONDS if ok else REPLY_RETRY_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Idempotent: CREATE TABLE IF NOT EXISTS + additive column migration, so an
    # existing outreach.db picks up new tables/columns on upgrade without re-running migrate.
    from app.dedupe import normalize_all_websites
    from app.opportunities import ensure_schema as ensure_opportunity_schema
    from app.activities import ensure_schema as ensure_activity_schema, migrate_existing
    from app.contacts import ensure_schema as ensure_contact_schema, migrate_existing as migrate_contacts
    from app.sales_documents import ensure_schema as ensure_sales_document_schema
    backup_db()  # the lead base is the business asset — snapshot before touching it
    conn = connect(DB_PATH)
    try:
        init_schema(conn)
        ensure_contact_schema(conn)
        migrate_contacts(conn)
        ensure_opportunity_schema(conn)
        ensure_sales_document_schema(conn)
        ensure_activity_schema(conn)
        migrate_existing(conn)
        normalize_all_websites(conn)  # idempotent data fix: consistent website form
    finally:
        conn.close()
    # background so a slow IMAP never delays the app coming up
    threading.Thread(target=reply_poll_loop, daemon=True).start()
    if os.environ.get("OUTREACH_AUTOSEND_SCHEDULER", "1") != "0":
        from app import autosend
        autosend.start_scheduler(DB_PATH)
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
from app.api import auth as auth_api  # noqa: E402
from app.api import health as health_api  # noqa: E402
app.include_router(auth_api.router)
app.include_router(health_api.router)

_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="static")

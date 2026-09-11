import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import auth
from app.backup import BACKUP_KEEP, startup_backup as backup_db

from app.main_deps import get_conn, DB_PATH  # re-exported for tests / dependency overrides
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
from app.api import activation as activation_api

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Idempotent: CREATE TABLE IF NOT EXISTS + additive column migration, so an
    # existing outreach.db picks up new tables/columns on upgrade without re-running migrate.
    from app import bootstrap, worker
    bootstrap.initialize(DB_PATH, backup_db)
    # Desktop/local remains zero-config. Hosted web services disable this and run
    # `python -m app.worker` in a separate supervised worker process.
    if os.environ.get("OUTREACH_EMBEDDED_WORKER", "1") != "0":
        threading.Thread(target=worker.run_embedded, args=(DB_PATH,), daemon=True,
                         name="outreach-embedded-worker").start()
    yield


app = FastAPI(title="Outreach Tool", lifespan=lifespan)

# 公网保护：有密码文件才生效（本地免密用法不变）。SPA 页面本身可公开（无数据），
# 数据和操作全在 /api 下，未登录一律 401，登录/状态接口除外。
_AUTH_EXEMPT = ("/api/login", "/api/auth/status", "/api/logout", "/api/runtime/identity")


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
app.include_router(activation_api.router)
from app.api import conversations as conversations_api  # noqa: E402
app.include_router(conversations_api.router)
from app.api import auth as auth_api  # noqa: E402
from app.api import health as health_api  # noqa: E402
app.include_router(auth_api.router)
app.include_router(health_api.router)

_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="static")

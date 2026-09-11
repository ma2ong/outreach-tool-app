from fastapi import APIRouter, HTTPException, Response

from app.browser_engine import CHANNELS
from app.playwright_engine import PlaywrightEngine

router = APIRouter(prefix="/api/channels")

ENGINE = PlaywrightEngine()  # injectable in tests


def _check(channel: str):
    if channel not in CHANNELS:
        raise HTTPException(status_code=400, detail="unknown channel")


@router.get("")
def list_channels():
    return {c: ENGINE.status(c) for c in sorted(CHANNELS)}


def _connect_hint(exc: Exception) -> str:
    """Name the actual cause. The old message guessed "a leftover browser window is
    holding the profile" for every failure — so when Playwright's chromium was simply
    not installed, the screen sent Allen hunting for windows that did not exist."""
    text = str(exc)
    if "Executable doesn't exist" in text or "playwright install" in text:
        return ("Playwright 的 Chromium 没有安装（或版本升级后需要重新下载）。"
                "在 backend 目录运行：python -m playwright install chromium"
                "。登录数据存在 ~/.outreach-tool/browser，装好后多半不用重新扫码。")
    if "Timeout" in text or "timeout" in text:
        return f"浏览器启动超时：{text[:200]}。机器忙或网络慢，稍等再点一次。"
    if "ProcessSingleton" in text or "already in use" in text or "SingletonLock" in text:
        return ("上次的浏览器窗口还占着登录数据。系统已尝试自动清理并重试；"
                "若仍失败，关掉所有自动化浏览器窗口后再点一次连接。")
    return f"浏览器启动失败：{text[:300]}"


@router.post("/{channel}/connect")
def connect(channel: str):
    _check(channel)
    try:
        ENGINE.connect(channel)
    except Exception as exc:  # noqa: BLE001 — a raw 500 told Allen nothing
        raise HTTPException(status_code=502, detail=_connect_hint(exc))
    # Returns while the browser is still coming up; the panel polls /status, which is
    # also where a launch failure surfaces.
    return {"status": ENGINE.status(channel)}


# ---- collecting accounts (docs/128 R5) ----
# A different tree from the one above on purpose: these are the logins used to *read*
# the platform, and they must never be the account Allen sends from (docs/126 R4).

@router.get("/scrape")
def scrape_channels():
    from app import scrape_browser

    return {"channels": [
        {"name": name, "state": scrape_browser.login_state(name),
         "logged_in": scrape_browser.logged_in(name),
         "hint": scrape_browser.LOGIN_HINT.get(name, "")}
        for name in scrape_browser.NEEDS_LOGIN]}


@router.post("/scrape/{channel}/login")
def scrape_login(channel: str):
    """Open a browser window for Allen to log a spare account into.

    The password is typed into that window and nowhere else: this endpoint takes no
    credentials and the server never sees any.
    """
    from app import scrape_browser

    try:
        scrape_browser.start_login(channel)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=_connect_hint(exc)) from exc
    return {"status": "等待登录"}


@router.get("/scrape/chrome-profiles")
def chrome_profiles():
    """Allen's own Chrome profiles, so he can hand one over instead of logging in here."""
    from app import scrape_browser

    return {"profiles": scrape_browser.chrome_profiles(),
            "chrome_running": scrape_browser.chrome_is_running()}


@router.post("/scrape/{channel}/import")
def scrape_import(channel: str, body: dict):
    from app import scrape_browser

    try:
        ok = scrape_browser.import_login(channel, str(body.get("folder") or ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except scrape_browser.Unavailable as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"导入失败：{str(exc)[:200]}") from exc
    return {"logged_in": ok,
            "detail": "" if ok else "复制过来了，但这份资料里没有登录态 —— 选错个人资料了？"}


@router.get("/{channel}/status")
def status(channel: str):
    _check(channel)
    st = ENGINE.refresh(channel) if hasattr(ENGINE, "refresh") else ENGINE.status(channel)
    # The launch runs after the connect request has already returned, so this is where
    # its failure has to be told — otherwise the browser dies silently behind a grey dot.
    raw = ENGINE.last_error(channel) if hasattr(ENGINE, "last_error") else ""
    return {"status": st, "error": _connect_hint(Exception(raw)) if raw else ""}


@router.get("/{channel}/qr")
def qr(channel: str):
    _check(channel)
    png = ENGINE.qr_png(channel)
    if png is None:
        raise HTTPException(status_code=404, detail="no qr")
    return Response(content=png, media_type="image/png")

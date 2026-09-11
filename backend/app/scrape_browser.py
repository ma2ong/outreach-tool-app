"""The second way of reading a page: Playwright, with a collecting identity (docs/128).

docs/126 R1 lined the three readers up by cost — a plain fetch, Playwright, then
browser-use — and this is the middle one. It is free and it can run headless, and it
costs one thing the others do not: a selector per site, which is only worth writing
where the page holds still.

Measured 2026-09-11, which is what decides who is in `SEARCH_URL`: Naver's results page
is already readable by `jina`, so Playwright buys nothing there; Naver's blogs name
companies in prose with no link at all, which no selector can reach; Bing hides the real
host in the cite line and, worse, answers a question you did not ask when it has no
answer for yours. What is left is Google — where the wall turned out to be the IP, not
the reader — Instagram, where a selector is the right tool and a collecting login is the
missing part, and Facebook, whose public pages need no account at all.

The profile tree is `~/.outreach-tool/scrape/`, never `~/.outreach-tool/browser/`. The
sending logins live in the second one, and a platform's rate limiter watches a logged-in
account browsing far more closely than it watches one sending messages. A collecting
account can be replaced; the account Allen sends from cannot (docs/126 R4).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from app import scrape_runner

SCRAPE_DIR = Path(os.environ.get(
    "OUTREACH_SCRAPE_DIR", str(Path.home() / ".outreach-tool" / "scrape")))
RUNNER = Path(__file__).resolve().parent / "scrape_runner.py"
RUN_TIMEOUT = 180

# Instagram's search page is served to an account and nothing else, and being logged out
# there is a channel that was never switched on rather than one that broke today
# (docs/126 R6). Facebook is deliberately not on this list: measured 2026-09-11, only its
# search is shut to a logged-out browser — every public Page's About tab reads fine
# without an account, so that channel carries none (docs/128 R4).
NEEDS_LOGIN = ("instagram",)
# 首页，不是 /accounts/login/：未登录时是同一个登录表单，而后者 2026-09-11 回过一次
# ERR_HTTP_RESPONSE_CODE_FAILURE。
LOGIN_URL = {"instagram": "https://www.instagram.com/"}
LOGIN_HINT = {
    "instagram": "未启用：需要先登录采集专用账号（小号）。到「渠道」页点「登录采集账号」，"
                 "会打开一个普通 Chrome 窗口，在里面像平时一样登录，然后关掉窗口 —— "
                 "不要用发私信那个账号：平台封的是账号，发信账号封了，"
                 "在谈的对话和联系人一起没（docs/126 R4）",
}
# The cookie a platform sets only after a real login. A profile directory is not the
# test: Chromium writes `Default/` the moment it starts, so the first version of
# `logged_in` called every profile that had ever been opened a logged-in one.
SESSION_COOKIE = {"instagram": (".instagram.com", ("sessionid",))}


class Blocked(RuntimeError):
    """The site served a wall instead of results — an answer, and not an empty one."""


class Unavailable(RuntimeError):
    """This reader is not installed or not logged in — not a failure to retry."""


def profile_dir(channel: str) -> Path:
    return SCRAPE_DIR / channel


def logged_in(channel: str) -> bool:
    """Is a collecting account actually logged in here?

    The session cookie is the only honest answer. Chromium's cookie file is locked while
    the browser is running, so a login still in progress reads as not-logged-in — which
    is why the panel tracks the window separately (`login_state`).
    """
    import sqlite3

    host, names = SESSION_COOKIE.get(channel, ("", ()))
    path = profile_dir(channel) / "Default" / "Network" / "Cookies"
    if not host or not path.is_file():
        return False
    try:
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
        try:
            row = db.execute(
                "SELECT 1 FROM cookies WHERE host_key LIKE ? AND name IN (%s) LIMIT 1"
                % ",".join("?" * len(names)), (f"%{host.lstrip('.')}", *names)).fetchone()
        finally:
            db.close()
    except sqlite3.Error:
        # Locked, or a Chromium schema we do not know. Saying "not logged in" sends
        # Allen to a login window he may not need; saying "logged in" sends the channel
        # at a wall. The first is the recoverable mistake.
        return False
    return row is not None


def unavailable(channel: str = "") -> str:
    """Why this cannot run right now, or "" when it can (docs/70 R4)."""
    try:
        import playwright  # noqa: F401
    except ImportError:
        return "没有安装 playwright（pip install playwright && playwright install chromium）"
    if channel in NEEDS_LOGIN and not logged_in(channel):
        return LOGIN_HINT[channel]
    return ""


def available(channel: str = "") -> bool:
    return not unavailable(channel)


def _spawn(argv: list[str]):
    """Start a window and return, rather than waiting for Allen to finish typing."""
    return subprocess.Popen(argv)


# The login windows this process opened, so the panel can tell "still logged out" from
# "the window is open and he is typing" — those look identical on disk.
_LOGIN_WINDOWS: dict = {}


# Where Windows keeps Chrome. Not Playwright's bundled Chromium and not Playwright at
# all: see `start_login`.
_CHROME_PATHS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.join(os.environ.get("LOCALAPPDATA", ""),
                 r"Google\Chrome\Application\chrome.exe"),
)


def chrome_path() -> str:
    for candidate in _CHROME_PATHS:
        if candidate and os.path.isfile(candidate):
            return candidate
    return ""


def start_login(channel: str):
    """Open an ordinary Chrome on the collecting profile, with nothing driving it.

    Measured 2026-09-11: a Playwright-driven browser — real Chrome build, automation
    flag removed, `navigator.webdriver` false — is answered by Instagram with a captcha
    page that never draws its captcha, while Allen's own Chrome logs in from this same
    machine and this same IP. reCAPTCHA itself renders fine in the driven window, so
    what is left is CDP, and CDP is not a flag: it is how Playwright works at all.

    So this launches Chrome the way the Start menu does, pointed at our own profile
    directory. No credential reaches this process, the session lands in
    `~/.outreach-tool/scrape/<channel>`, and the collector opens that directory later —
    browsing with a session already in hand is a different proposition from making one.
    """
    if channel not in LOGIN_URL:
        raise ValueError(f"{channel} 不需要登录采集账号")
    chrome = chrome_path()
    if not chrome:
        raise Unavailable(
            "找不到 Chrome。采集账号必须在普通 Chrome 里登录 —— 被程序驱动的浏览器"
            "登不进 Instagram（Meta 的验证码不渲染）。请先安装 Google Chrome")
    profile = profile_dir(channel)
    profile.mkdir(parents=True, exist_ok=True)
    proc = _spawn([chrome, f"--user-data-dir={profile}", "--no-first-run",
                   "--no-default-browser-check", LOGIN_URL[channel]])
    _LOGIN_WINDOWS[channel] = proc
    return proc


def login_state(channel: str) -> str:
    """已登录 / 等待登录 / 未登录 — three states, because they need three answers."""
    if logged_in(channel):
        return "已登录"
    proc = _LOGIN_WINDOWS.get(channel)
    return "等待登录" if proc is not None and proc.poll() is None else "未登录"


def _subprocess_run(argv: list[str], timeout: int) -> str:
    done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise subprocess.CalledProcessError(done.returncode, argv, stderr=done.stderr)
    return done.stdout


def _run_runner(argv: list[str], channel: str, run=None) -> dict:
    try:
        raw = (run or _subprocess_run)(argv, RUN_TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"{channel} 读了 {RUN_TIMEOUT} 秒还没读完，已放弃") from exc
    except (subprocess.CalledProcessError, OSError) as exc:
        raise RuntimeError(f"{channel} 采集进程没能跑起来：{str(exc)[:120]}") from exc
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise RuntimeError(f"{channel} 返回的不是 JSON：{str(raw)[:120]}") from exc
    if payload.get("blocked"):
        raise Blocked(f"{channel} 把我们挡下来了：{payload['blocked'][:160]}")
    if payload.get("error"):
        raise RuntimeError(f"{channel} 读取失败：{payload['error'][:160]}")
    return payload


def _argv(channel: str, limit: int, headed: bool) -> list[str]:
    profile = profile_dir(channel)
    profile.mkdir(parents=True, exist_ok=True)
    argv = [sys.executable, str(RUNNER), "--channel", channel,
            "--limit", str(limit), "--profile-dir", str(profile)]
    return argv if headed else argv + ["--headless"]


def read_pages(channel: str, handles: list[str], limit: int = 20, *, run=None) -> list[dict]:
    """Read public pages someone else found, one row each (docs/128 R4).

    Facebook's own search is shut to a logged-out browser, but its pages are not: the
    About tab prints the company's site, and that is read without an account at all —
    so this channel carries no account that can be banned and opens no window.
    """
    reason = unavailable(channel)
    if reason:
        raise Unavailable(reason)
    wanted = [h for h in handles if h][:limit]
    if not wanted:
        return []
    argv = _argv(channel, limit, headed=False) + ["--pages", ",".join(wanted)]
    return _run_runner(argv, channel, run).get("pages") or []


def read_hosts(channel: str, query: str, limit: int = 20, *,
               headless: bool | None = None, run=None) -> list[str]:
    """Company domains this channel shows for this query. Raises rather than lying.

    An empty list here means the page had nothing on it. Everything else — a wall, a
    dead browser, a login that expired — comes back as an exception carrying what
    happened, because "0 家" is a claim about the market and none of those are
    (docs/128 R2).
    """
    if channel not in scrape_runner.SEARCH_URL:
        raise ValueError(f"no playwright reader for channel: {channel}")
    reason = unavailable(channel)
    if reason:
        raise Unavailable(reason)
    # Logged-in channels run headed: a social network's bot checks are far harder on a
    # headless session, and these channels are attended anyway (docs/126 R5).
    headed = channel in NEEDS_LOGIN if headless is None else not headless
    argv = _argv(channel, limit, headed) + ["--query", query]
    payload = _run_runner(argv, channel, run)
    return [h for h in payload.get("hosts") or [] if h][:limit]

"""Reads a results page with Playwright, in its own process (docs/128 R3).

Nothing in the server imports this at call time except as a subprocess argument, and it
imports nothing from `app`: the two sides share a command line and one line of JSON.
That separation is not tidiness. `playwright_engine.py` owns a worker thread holding a
persistent context on the sending profiles, and a second Chromium opening the same
profile directory is the `exitCode=21` that engine already carries a kill-the-orphan
routine for. Collecting runs in a different process on a different profile tree, so the
two can never reach for the same lock.

The pure functions below — what counts as a wall, what counts as a handle, which link on
a profile is the company's own — live here rather than in the caller so they can be
tested without a browser, which is the only way they get tested at all until Allen logs
a collection account in (docs/128 R4).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse

_STDOUT = sys.stdout
sys.stdout = sys.stderr

# What a search engine says when it has decided we are a robot. Measured 2026-09-11 on
# Google through three readers: jina answered "This page maybe requiring CAPTCHA", and
# headless Playwright and a real Chrome window both answered with the unusual-traffic
# page — in Chinese when the browser's locale was Chinese.
_WALL = re.compile(
    r"unusual traffic|not a robot|requiring CAPTCHA|detected unusual|"
    r"异常流量|自动程序|비정상적인 트래픽", re.I)
# A wall says so at the top. Far enough in, the same words are just a result's text.
_WALL_WINDOW = 1200


def blocked_reason(text: str) -> str:
    """The wall's own words, or "" — never a bare True, because the reason is the point."""
    head = str(text or "")[:_WALL_WINDOW]
    found = _WALL.search(head)
    return head[max(0, found.start() - 40):found.end() + 60].strip() if found else ""


_PLATFORM_HOSTS = {
    "instagram": ("instagram.com", "facebook.com", "meta.com", "threads.com", "meta.ai",
                  "fb.com", "whatsapp.com"),
    "facebook": ("facebook.com", "instagram.com", "meta.com", "messenger.com", "fb.com",
                 "threads.com", "meta.ai", "whatsapp.com"),
}
# A handle is a path of its own: /ledworld_mx/. A post (/p/...), a tag, a reel and the
# platform's own sections are not companies.
_NOT_A_HANDLE = {"p", "reel", "reels", "explore", "stories", "direct", "accounts",
                 "about", "help", "privacy", "terms", "legal", "policies", "pages",
                 "groups", "marketplace", "watch", "events", "search", "login"}
_HANDLE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,29}$")
# A link-in-bio page is a redirect, not an address: enriching it reads the shortener.
# A redirect or a chat shortcut is a way to reach someone, not an address to enrich.
_REDIRECTORS = ("linktr.ee", "bit.ly", "lnkd.in", "linkin.bio", "beacons.ai",
                "taplink.cc", "l.instagram.com", "l.facebook.com",
                "wa.link", "wa.me", "api.whatsapp.com", "t.me", "m.me")
# Meta's own footer, on every profile page: about.meta.com, muse.ai, threads.com and
# the developer docs are not companies anyone can sell an LED screen to.
_META_FOOTER = ("about.meta.com", "muse.ai", "threads.com", "developers.facebook.com",
                "meta.ai", "about.instagram.com", "help.instagram.com")


def _host(url: str) -> str:
    host = urllib.parse.urlparse(str(url or "")).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def handles_from_hrefs(hrefs, channel: str) -> list[str]:
    """The account names on a search results page, in the order they appeared."""
    out: list[str] = []
    platform = _PLATFORM_HOSTS.get(channel, ())
    for href in hrefs or []:
        if _host(href) not in platform:
            continue
        parts = [p for p in urllib.parse.urlparse(str(href)).path.split("/") if p]
        if len(parts) != 1:
            continue
        handle = parts[0]
        if handle.lower() in _NOT_A_HANDLE or not _HANDLE.match(handle):
            continue
        if handle not in out:
            out.append(handle)
    return out


# Facebook's About tab prints the fields it has under their own labels: a phone under
# Mobile, an address, an email under Email, and the site under Website. Measured
# 2026-09-11 logged out — the page name, the category and all four fields are there, and
# only FB's own search is behind the login wall.
_ABOUT_DOMAIN = re.compile(
    r"\b((?:[a-z0-9][a-z0-9-]{0,60}\.)+[a-z]{2,12}(?:\.[a-z]{2,6})?)\b", re.I)
# A page that is restricted, renamed or deleted says this instead of its fields.
_NO_PAGE = re.compile(r"isn't available right now|content not found|页面不可用", re.I)
# Mail hosts: an address at one of these says where the owner reads mail, not where the
# company lives, and importing gmail.com as a customer is worse than importing nothing.
_NOT_A_COMPANY_HOST = (
    "facebook.com", "fb.com", "messenger.com", "instagram.com", "meta.com", "meta.ai",
    "threads.com", "whatsapp.com", "gmail.com", "googlemail.com", "hotmail.com",
    "outlook.com", "yahoo.com", "qq.com", "163.com", "naver.com", "icloud.com",
    "linkedin.com", "youtube.com", "twitter.com", "x.com", "tiktok.com", "goo.gl")


def site_from_about(text: str) -> str:
    """The company's own site as printed on its public About tab, or "".

    Read off the text rather than the links because Facebook renders an outbound URL as
    a redirect through its own host; the visible string is the one thing on that page
    that is the company's actual address. `enrich_domain` still has to reach the site
    and read it, so a misread here dies one step later rather than becoming a customer.
    """
    body = str(text or "")
    if _NO_PAGE.search(body):
        return ""
    for match in _ABOUT_DOMAIN.findall(body):
        host = match.lower().removeprefix("www.").rstrip(".")
        if any(host == bad or host.endswith("." + bad) for bad in _NOT_A_COMPANY_HOST):
            continue
        if host in _REDIRECTORS or "." not in host:
            continue
        return host
    return ""


def decode_redirect(href: str) -> str:
    """Unwrap Instagram's `l.instagram.com/?u=<encoded>`, or return the link unchanged.

    The bio link — the one field on a profile that is a fact about the company — is
    always wrapped, so a reader that skips redirectors skips the only link worth having.
    """
    parsed = urllib.parse.urlparse(str(href or ""))
    if parsed.netloc.lower().lstrip("l.") and parsed.netloc.lower() in (
            "l.instagram.com", "l.facebook.com", "lm.facebook.com"):
        target = urllib.parse.parse_qs(parsed.query).get("u")
        return target[0] if target else ""
    return str(href or "")


def bio_host(hrefs) -> str:
    """The site a profile links to in its bio, as a bare host.

    Measured 2026-09-11: pantallasledlemon links pantallasledlemon.com and
    pantallasledperu links exctecled.com, both through the redirector, both above the
    Meta footer that every profile carries.
    """
    for href in hrefs or []:
        host = _host(decode_redirect(href))
        if not host or host in _REDIRECTORS:
            continue
        if any(host == bad or host.endswith("." + bad)
               for bad in _META_FOOTER + _PLATFORM_HOSTS["instagram"]):
            continue
        return host
    return ""


# Instagram's own web search, called from inside the logged-in page. The DOM route does
# not exist for this: `/explore/search/keyword/?q=` renders 607 bytes and no results.
SEARCH_JS = """async (q) => {
  const r = await fetch('/api/v1/web/search/topsearch/?context=blended&query='
                        + encodeURIComponent(q),
                        {headers: {'X-IG-App-ID': '936619743392459'}});
  return {status: r.status, text: (await r.text()).slice(0, 300000)};
}"""


def instagram_users(text: str, limit: int, status: int = 200) -> list[str]:
    """The account names Instagram returned, or an exception saying why there are none.

    Note what this search is: Instagram matches **account names**, not descriptions.
    `led display distributor` returns nothing at all, while `pantallas led` returns five
    real Latin American LED companies. Empty is a normal answer to a phrase, and
    429 is Instagram declining — which is not the same as the market being empty
    (docs/128 R2).
    """
    if status == 429:
        raise RuntimeError("Instagram 限流（429）—— 这个采集账号暂时被限速，过一会儿再试")
    if status != 200:
        raise RuntimeError(f"Instagram 搜索返回 {status}")
    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise RuntimeError("Instagram 没有返回 JSON —— 登录态可能失效了") from exc
    out: list[str] = []
    for row in payload.get("users") or []:
        user = row.get("user") if isinstance(row, dict) else None
        name = (user or {}).get("username") if isinstance(user, dict) else None
        if name and name not in out:
            out.append(name)
        if len(out) >= max(1, limit):
            break
    return out


# One entry per channel: where to ask. A channel whose results page is stable enough to
# be worth a selector is in here; the ones that are not stay with browser-use
# (docs/126 R1), and the ones whose answers are not worth having are in neither.
SEARCH_URL = {
    "google": "https://www.google.com/search?q={q}&num=30",
    # The second leg of the channel that produces Korean buyers. jina reads this page
    # today; this reader exists for the day jina does not (docs/128 R8).
    "naver-web": "https://search.naver.com/search.naver?where=web&query={q}",
    # The search happens through `SEARCH_JS` once this page is open; the keyword route
    # renders 607 bytes and no results.
    "instagram": "https://www.instagram.com/",
}
# Facebook is not in there: its own search answers a logged-out browser with `Not Found`
# (9 bytes, measured 2026-09-11). Its pages are public though, so that channel arrives
# here with a list of pages someone else found and reads each one's About tab.
ABOUT_URL = "https://www.facebook.com/{h}/about"
CHANNELS = tuple(sorted(set(SEARCH_URL) | {"facebook"}))
_LINKS_JS = "() => [...document.querySelectorAll('a[href]')].map(a => a.href)"
# Google keeps the real URL in the link. Bing does not — it wraps every result in a
# bing.com redirect and prints the real host only in the cite line, which is the smaller
# of the two reasons Bing is not here (docs/128).
_GOOGLE_JS = ("() => [...document.querySelectorAll('div#search a[href^=\"http\"]')]"
              ".map(a => a.href)")
# Channels whose results are plain links on the page, and the selector that finds them.
# Naver puts its results in ordinary anchors; Google keeps its own inside div#search.
LINK_CHANNELS = {"google": _GOOGLE_JS, "naver-web": _LINKS_JS}
# The first links on a results page belong to the search engine itself — Naver's answer
# to a keyword opens with eight of its own nav links. This process does not know what a
# company is (that lives in `discovery_sources.is_company_site`), so it hands back more
# than was asked for and lets the side that knows do the cutting.
_LINK_OVERFETCH = 6


def _profile_url(channel: str, handle: str) -> str:
    return (f"https://www.instagram.com/{handle}/" if channel == "instagram"
            else f"https://www.facebook.com/{handle}")


def _read_about(page, handles: list[str]) -> list[dict]:
    """One row per public Facebook page: the handle, and the site it says it has."""
    rows: list[dict] = []
    for handle in handles:
        try:
            page.goto(ABOUT_URL.format(h=handle), wait_until="domcontentloaded",
                      timeout=45000)
            page.wait_for_timeout(2500)
            rows.append({"handle": handle, "domain": site_from_about(page.inner_text("body"))})
        except Exception:  # noqa: BLE001 — one page, not the channel
            continue
    return rows


# A browser that announces it is automated gets treated as one. Measured 2026-09-11:
# Playwright's bundled Chromium reports `navigator.webdriver === true` and brands itself
# "Chromium", and Instagram answered Allen's login with its captcha page — which then
# never drew the captcha, leaving a blank screen with a Meta logo on it. Real Chrome
# with `--enable-automation` removed reports false and brands itself "Google Chrome".
_QUIET_ARGS = ["--window-position=80,80", "--window-size=1120,920",
               "--disable-blink-features=AutomationControlled"]


def kill_stale(profile_dir: str) -> int:
    """Kill a browser still holding this profile, so the next launch is not refused.

    The sending engine carries the same routine and the same scar: an orphaned Chromium
    keeps the profile locked and every later launch dies. Matching on the profile path
    alone is safe here in a way it is not there — this path is ours by construction and
    Allen's own Chrome never opens it.
    """
    if os.name != "nt":
        return 0
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
          "Where-Object { $_.CommandLine -like '*" + str(profile_dir) + "*' } | "
          "ForEach-Object { Stop-Process -Id $_.ProcessId -Force; $_.ProcessId }")
    try:
        done = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                              capture_output=True, text=True, timeout=25)
    except Exception:  # noqa: BLE001 — nothing to kill is not an error
        return 0
    return len([line for line in done.stdout.split() if line.strip()])


def launch_quiet(play, profile_dir: str, headless: bool):
    """A browser window that does not announce itself, on this profile.

    Headed means a person is going to look at it or type into it, and that is exactly
    when the automation flags cost something — so those runs get the real Chrome build.
    The headless readers keep Playwright's own Chromium, which is what Facebook's public
    pages were measured with and what works there today.
    """
    options = {"headless": headless, "args": list(_QUIET_ARGS),
               "ignore_default_args": ["--enable-automation"]}
    channels = ("chrome", None) if not headless else (None,)
    last: Exception | None = None
    for attempt, channel in enumerate(channels):
        kw = {**options, **({"channel": channel} if channel else {})}
        try:
            return play.chromium.launch_persistent_context(profile_dir, **kw)
        except Exception as exc:  # noqa: BLE001
            last = exc
            # Only a lock is worth clearing; a missing Chrome just means the next channel.
            if "already in use" in str(exc) or "ProcessSingleton" in str(exc):
                if kill_stale(profile_dir):
                    time.sleep(2)
                    return play.chromium.launch_persistent_context(profile_dir, **kw)
            if attempt == len(channels) - 1:
                raise last
    raise last  # type: ignore[misc]


def _read(args) -> dict:
    from playwright.sync_api import sync_playwright

    channel = args.channel
    out: dict = {"hosts": [], "handles": [], "pages": [], "blocked": ""}
    url = (ABOUT_URL.format(h=(args.pages or ["facebook"])[0]) if channel == "facebook"
           else SEARCH_URL[channel].format(q=urllib.parse.quote(args.query)))
    with sync_playwright() as play:
        browser = launch_quiet(play, args.profile_dir, headless=args.headless)
        try:
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)
            wall = blocked_reason(page.inner_text("body"))
            if wall:
                out["blocked"] = wall
                return out
            if channel == "facebook":
                out["pages"] = _read_about(page, args.pages or [])
                out["hosts"] = [r["domain"] for r in out["pages"] if r["domain"]]
                return out
            if channel in LINK_CHANNELS:
                for href in page.evaluate(LINK_CHANNELS[channel]):
                    host = _host(href)
                    if host and host not in out["hosts"]:
                        out["hosts"].append(host)
                out["hosts"] = out["hosts"][:args.limit * _LINK_OVERFETCH]
                return out
            # Instagram: its own search endpoint, called from inside the logged-in page.
            # A name is not a company, so each account is opened once and what crosses is
            # the site its bio links to (docs/124 R1).
            answer = page.evaluate(SEARCH_JS, args.query)
            out["handles"] = instagram_users(answer.get("text") or "", args.limit,
                                             answer.get("status") or 0)
            for handle in out["handles"]:
                try:
                    page.goto(_profile_url(channel, handle),
                              wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(3000)
                    host = bio_host(page.evaluate(_LINKS_JS))
                except Exception:  # noqa: BLE001 — one profile, not the channel
                    continue
                if host and host not in out["hosts"]:
                    out["hosts"].append(host)
                    out["pages"].append({"handle": handle, "domain": host})
            return out
        finally:
            try:
                browser.close()
            except Exception:  # noqa: BLE001 — closing a dead browser is not an error
                pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True, choices=CHANNELS)
    parser.add_argument("--query", default="")
    # Facebook pages someone else already found, comma separated: its own search is shut.
    parser.add_argument("--pages", default="")
    parser.add_argument("--profile-dir", required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    args.pages = [h for h in args.pages.split(",") if h.strip()]
    try:
        result = _read(args)
    except Exception as exc:  # noqa: BLE001 — the caller reads JSON, not a traceback
        print(f"scrape failed: {exc}", file=sys.stderr)
        result = {"hosts": [], "handles": [], "pages": [], "error": str(exc)[:200]}
    print(json.dumps(result, ensure_ascii=False), file=_STDOUT)


if __name__ == "__main__":
    main()

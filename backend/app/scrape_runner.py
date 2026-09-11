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
import re
import sys
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
_REDIRECTORS = ("linktr.ee", "bit.ly", "lnkd.in", "linkin.bio", "beacons.ai",
                "taplink.cc", "l.instagram.com", "l.facebook.com")


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


def external_host(hrefs, channel: str) -> str:
    """The company's own site, as linked from its profile — the only field that crosses.

    docs/124 R1 and docs/126 R2 both land here: a handle is not a company we can write
    to, and a company name read off a profile is a guess. The link in the bio is the one
    thing on that page that is a fact about the company, and `enrich_domain` checks even
    that by reading the site itself.
    """
    platform = _PLATFORM_HOSTS.get(channel, ())
    for href in hrefs or []:
        host = _host(href)
        if not host or any(host == p or host.endswith("." + p) for p in platform):
            continue
        if host in _REDIRECTORS:
            continue
        return host
    return ""


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


# One entry per channel: where to ask. A channel whose results page is stable enough to
# be worth a selector is in here; the ones that are not stay with browser-use
# (docs/126 R1), and the ones whose answers are not worth having are in neither.
SEARCH_URL = {
    "google": "https://www.google.com/search?q={q}&num=30",
    "instagram": "https://www.instagram.com/explore/search/keyword/?q={q}",
}
# Facebook is not in there: its own search answers a logged-out browser with `Not Found`
# (9 bytes, measured 2026-09-11). Its pages are public though, so that channel arrives
# here with a list of pages someone else found and reads each one's About tab.
ABOUT_URL = "https://www.facebook.com/{h}/about"
# Where Allen logs a collecting account in. He types into this window; nothing about the
# account passes through the server (docs/128 R5).
LOGIN_URL = {"instagram": "https://www.instagram.com/accounts/login/"}
LOGIN_WAIT = 1800          # half an hour, then the window is on its own
CHANNELS = tuple(sorted(set(SEARCH_URL) | {"facebook"}))
_LINKS_JS = "() => [...document.querySelectorAll('a[href]')].map(a => a.href)"
# Google keeps the real URL in the link. Bing does not — it wraps every result in a
# bing.com redirect and prints the real host only in the cite line, which is the smaller
# of the two reasons Bing is not here (docs/128).
_GOOGLE_JS = ("() => [...document.querySelectorAll('div#search a[href^=\"http\"]')]"
              ".map(a => a.href)")


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


def _login(args) -> dict:
    """Open the collecting profile and wait for the window to be closed.

    The wait is the whole point: closing the context before Allen finishes typing would
    throw the session away, and a persistent context only writes its cookies out when it
    shuts down cleanly.
    """
    import time

    from playwright.sync_api import sync_playwright

    with sync_playwright() as play:
        browser = play.chromium.launch_persistent_context(
            args.profile_dir, headless=False,
            args=["--window-position=80,80", "--window-size=1100,900"])
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto(LOGIN_URL[args.channel], wait_until="domcontentloaded", timeout=60000)
        deadline = time.monotonic() + LOGIN_WAIT
        while time.monotonic() < deadline:
            try:
                if not [p for p in browser.pages if not p.is_closed()]:
                    break
            except Exception:  # noqa: BLE001 — the window is gone, which is the signal
                break
            time.sleep(2)
        try:
            browser.close()
        except Exception:  # noqa: BLE001
            pass
    return {"hosts": [], "handles": [], "pages": [], "blocked": ""}


def _read(args) -> dict:
    from playwright.sync_api import sync_playwright

    channel = args.channel
    out: dict = {"hosts": [], "handles": [], "pages": [], "blocked": ""}
    url = (ABOUT_URL.format(h=(args.pages or ["facebook"])[0]) if channel == "facebook"
           else SEARCH_URL[channel].format(q=urllib.parse.quote(args.query)))
    with sync_playwright() as play:
        browser = play.chromium.launch_persistent_context(
            args.profile_dir, headless=args.headless,
            viewport={"width": 1360, "height": 900},
            args=["--window-position=80,80", "--window-size=1200,900"])
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
            if channel == "google":
                for href in page.evaluate(_GOOGLE_JS):
                    host = _host(href)
                    if host and host not in out["hosts"]:
                        out["hosts"].append(host)
                out["hosts"] = out["hosts"][:args.limit]
                return out
            # Social: a results page gives account names, and a name is not a company.
            # Each profile is opened once, to read the site it links to.
            out["handles"] = handles_from_hrefs(page.evaluate(_LINKS_JS), channel)[:args.limit]
            for handle in out["handles"]:
                try:
                    page.goto(_profile_url(channel, handle),
                              wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(2500)
                    host = external_host(page.evaluate(_LINKS_JS), channel)
                except Exception:  # noqa: BLE001 — one profile, not the channel
                    continue
                if host and host not in out["hosts"]:
                    out["hosts"].append(host)
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
    parser.add_argument("--login", action="store_true")
    args = parser.parse_args()
    args.pages = [h for h in args.pages.split(",") if h.strip()]
    try:
        result = _login(args) if args.login else _read(args)
    except Exception as exc:  # noqa: BLE001 — the caller reads JSON, not a traceback
        print(f"scrape failed: {exc}", file=sys.stderr)
        result = {"hosts": [], "handles": [], "pages": [], "error": str(exc)[:200]}
    print(json.dumps(result, ensure_ascii=False), file=_STDOUT)


if __name__ == "__main__":
    main()

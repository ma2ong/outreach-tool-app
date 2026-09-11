"""Where new customers come from — one declaration per channel (docs/70).

Prospecting had exactly one route: a DuckDuckGo query, written as a function. Adding a
second meant new code, new tests and a deploy, which is why three months later there was
still one. Google Maps, Naver, social and directory pages are not four more functions.

A channel declares three things — where to ask, how to read the answer, and whether it
is usable at all — and everything else is shared. In particular they all hand their
candidates to `discovery.import_candidates`, so the peer filter, the duplicate check and
the enrichment of known customers exist once rather than four slightly different times.

The shape is borrowed from AutoCLI, which maintains 55 sites as declarative adapters
rather than 55 pieces of code. The tools themselves are not: they drive the browser a
person is sitting in front of, and this runs at 3am with nobody there.
"""
from __future__ import annotations

import os
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Callable

# A result is only ever a company domain plus whatever the channel happened to know.
Candidate = dict


@dataclass
class Source:
    """One place to look for customers, and the ways it can be read."""

    name: str
    label: str
    kind: str                      # api | page | browser | social
    # How this channel is read (docs/126 R1, docs/128 R5): http is a plain fetch,
    # playwright drives a headless or logged-in Chromium, browser is browser-use driving
    # a real Chrome. Declared cheapest first — the first one is what an unqualified
    # request gets — so the API can refuse a reader a channel does not have.
    readers: dict[str, Callable[[str, int], list[Candidate]]] = field(default_factory=dict)
    # Why this channel cannot run right now, or "" when it can. Being unconfigured and
    # being broken are different states and the report must not merge them (docs/70 R4).
    unavailable: Callable[[], str] = field(default=lambda: "")
    # An alternative route that is fine to leave unconfigured. Reporting it as 未启用
    # every day would be a daily reminder of a door Allen cannot open — NAVER Cloud
    # Platform wants Korean real-name verification — while the page channel already
    # covers the same market.
    optional: bool = False
    # False when reading this channel opens a window on Allen's screen or needs a login
    # that only he can give. docs/126 R5: a scheduler must not be able to reach it, so
    # `gather` skips it unless named.
    unattended: bool = True

    @property
    def engines(self) -> tuple[str, ...]:
        return tuple(self.readers)

    def fetch(self, query: str, limit: int = 20, engine: str | None = None) -> list[Candidate]:
        """Read this channel. An undeclared reader is refused rather than substituted."""
        if engine and engine not in self.readers:
            raise ValueError(
                f"{self.name} 没有「{engine}」这种读法，它声明的是：{'/'.join(self.engines)}")
        return self.readers[engine or self.engines[0]](query, limit)

    def available(self) -> bool:
        return not self.unavailable()


# --------------------------------------------------------------- helpers

_HOST = re.compile(r"^https?://(?:www\.)?([^/]+)", re.I)
# Places that host other people's pages: a hit here is not a company we can sell to.
_NOT_A_COMPANY = (
    "facebook.com", "instagram.com", "linkedin.com", "youtube.com", "twitter.com",
    "x.com", "tiktok.com", "pinterest.com", "yelp.com", "alibaba.com", "made-in-china.com",
    "indiamart.com", "amazon.", "ebay.", "naver.com", "blog.naver.com", "cafe.naver.com",
    "tistory.com", "wordpress.com", "blogspot.com", "wikipedia.org", "google.",
    # Naver's own CDN and corporate pages come back on every Korean query.
    "pstatic.net", "navercorp.com", "daum.net", "kakao.com", "nate.com",
)


def host_of(url: str) -> str:
    match = _HOST.match(str(url or "").strip())
    return match.group(1).lower() if match else ""


def is_company_site(url: str) -> bool:
    host = host_of(url)
    return bool(host) and not any(bad in host for bad in _NOT_A_COMPANY)


# --------------------------------------------------------------- naver

_NAVER_TAGS = re.compile(r"<[^>]+>")
# The old Developers Center closed to new applications; search moved to NAVER API Hub
# on Naver Cloud Platform, with different header names and a different host. A legacy
# Client ID now authenticates to nothing — "Scopes are Empty" is what that looks like.
_HUB_HOST = "https://naverapihub.apigw.ntruss.com"


def _naver_keys() -> tuple[str, str]:
    return (os.environ.get("NAVER_API_KEY_ID", ""),
            os.environ.get("NAVER_API_KEY", ""))


def _naver_unavailable() -> str:
    key_id, key = _naver_keys()
    if not key_id or not key:
        return "没有配置 NAVER_API_KEY_ID / NAVER_API_KEY（Naver Cloud Platform → API Hub）"
    return ""


def _naver_call(path: str, params: dict) -> dict:
    import json
    import urllib.error
    import urllib.request

    key_id, key = _naver_keys()
    url = f"{_HUB_HOST}{path}?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={
        "X-NCP-APIGW-API-KEY-ID": key_id, "X-NCP-APIGW-API-KEY": key})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # The body carries the actual reason; the status alone sends you looking in the
        # wrong place — "Scopes are Empty" and a wrong key are both 401 and mean
        # opposite things.
        detail = exc.read().decode("utf-8", "replace")[:200]
        raise RuntimeError(f"Naver {exc.code}: {detail}") from exc


def naver_search(query: str, limit: int = 20) -> list[Candidate]:
    """Korean web search. Korea is the primary market and Google's coverage there is thin."""
    key_id, key = _naver_keys()
    if not key_id or not key:
        return []
    payload = _naver_call("/search/v1/webkr", {"display": min(limit, 100), "query": query})
    out: list[Candidate] = []
    for item in payload.get("items", []):
        link = item.get("link") or ""
        if not is_company_site(link):
            continue
        out.append({
            "domain": host_of(link), "website": host_of(link),
            "title": _NAVER_TAGS.sub("", item.get("title") or "").strip(),
            "country": "South Korea", "source": "naver",
        })
    return out


def naver_local(query: str, limit: int = 20) -> list[Candidate]:
    """Korean business listings — Naver's answer to a maps search.

    A local result carries the address and phone as published by the business, which is
    the part a web search does not give: "AV 렌탈 강남" returns companies with a city
    and a number already attached.
    """
    key_id, key = _naver_keys()
    if not key_id or not key:
        return []
    payload = _naver_call("/search/v1/local",
                          {"display": min(limit, 5), "query": query})
    out: list[Candidate] = []
    for item in payload.get("items", []):
        link = item.get("link") or ""
        name = _NAVER_TAGS.sub("", item.get("title") or "").strip()
        if not name:
            continue
        candidate: Candidate = {
            "company_en": name, "country": "South Korea", "source": "naver-local",
            "city": (item.get("address") or "").split(" ")[0] or None,
            "phone": item.get("telephone") or None,
        }
        # A listing without its own site is still a lead — the phone is the way in.
        if is_company_site(link):
            candidate["domain"] = host_of(link)
            candidate["website"] = host_of(link)
        else:
            candidate["domain"] = f"naver-local:{name}"
        out.append(candidate)
    return out


_MD_LINK = re.compile(r"\]\((https?://[^)\s]+)\)")


def naver_page_search(query: str, limit: int = 20) -> list[Candidate]:
    """Korean search by reading the results page, the way a person would.

    The API route needs a NAVER Cloud Platform account, and that needs Korean
    real-name verification — a door Allen cannot open from Shenzhen. Reading the public
    results page needs no account at all, and Korea is the primary market, so a channel
    that works today beats a better one that never opens.
    """
    from app.jina import fetch

    url = ("https://search.naver.com/search.naver?where=web&query="
           + urllib.parse.quote(query))
    text = fetch(url, timeout=45)
    out: list[Candidate] = []
    seen: set[str] = set()
    for link in _MD_LINK.findall(text):
        if not is_company_site(link):
            continue
        host = host_of(link)
        if host in seen:
            continue
        seen.add(host)
        out.append({"domain": host, "website": host,
                    "country": "South Korea", "source": "naver-web"})
        if len(out) >= limit:
            break
    return out


# --------------------------------------------------------------- duckduckgo

def duckduckgo_search(query: str, limit: int = 20) -> list[Candidate]:
    """The channel that already existed, wrapped in the same shape as the others."""
    from app.search import search_domains

    return [{**row, "website": row.get("domain"), "source": "duckduckgo"}
            for row in search_domains(query, limit)]


# --------------------------------------------------------------- browser channels

def _browser_unavailable() -> str:
    from app import browser_harvest

    return browser_harvest.unavailable()


def _browser_search(name: str, url: str, allow: tuple[str, ...],
                    country: str | None = None) -> Callable[[str, int], list[Candidate]]:
    """A search engine read by a real browser, for the ones a plain fetch cannot open.

    Measured 2026-09-10: Google answers `jina.fetch` with 704 bytes of
    "This page maybe requiring CAPTCHA", and Bing returns its shell twice running with
    the result links missing. Neither is a channel until a browser opens it.
    """
    def fetch(query: str, limit: int = 20) -> list[Candidate]:
        from app import browser_harvest

        target = url.format(q=urllib.parse.quote(query))
        hosts = browser_harvest.read_with_browser(
            target, task="search", query=query, limit=limit, allow=allow)
        return [{"domain": host, "website": host, "source": name,
                 **({"country": country} if country else {})}
                for host in hosts if is_company_site(f"http://{host}")]
    return fetch


# ------------------------------------------------------- playwright channels

def _scrape_unavailable(channel: str) -> str:
    from app import scrape_browser

    return scrape_browser.unavailable(channel)


# Which country a channel's results are known to be about. A search engine reached from
# Shenzhen returns whatever it returns; Naver is Korea by construction, and the social
# channels are not, so only the ones that know say so.
def _playwright_search(name: str, country: str | None = None
                       ) -> Callable[[str, int], list[Candidate]]:
    """A results page read by Playwright: free, headless where it can be, one selector.

    Whatever this raises — a wall, a login that expired, a browser that died — travels
    up to `gather`, which reports it as that channel's failure with its reason attached.
    Swallowing it here would turn being turned away into "this keyword has no customers"
    (docs/128 R2).
    """
    def fetch(query: str, limit: int = 20) -> list[Candidate]:
        from app import scrape_browser

        return [{"domain": host, "website": host, "source": name,
                 **({"country": country} if country else {})}
                for host in scrape_browser.read_hosts(name, query, limit)
                if is_company_site(f"http://{host}")]
    return fetch


# How many names one blog run may spend on lookups. Each is a fetch of its own, and a
# blog page that mentions forty companies is mentioning them, not listing them.
_MAX_PROSE_NAMES = 12


def _compact(text: str) -> str:
    return re.sub(r"[\s\-_.·,()（）주식회사㈜]+", "", str(text or "")).lower()


def _site_says_its_name(host: str, name: str, fetch=None) -> bool:
    """Does this site call itself that? The half of docs/126 R2 that search cannot do.

    Measured 2026-09-10, and the reason this function exists: searching Naver for
    진영LED전광판 returns bandyled.com — a real Korean LED company, but a different one —
    and searching for a name invented on the spot
    (이런회사는없습니다주식회사12345) returns etoland.co.kr. A search engine always
    answers something, so "the name found nothing" is not a filter that exists.

    A company's own site says its own name, in whatever script it uses. That is the
    second source, and it is the only one that actually separates these cases.
    """
    from app.jina import fetch as jina_fetch

    try:
        text = (fetch or jina_fetch)(f"https://{host}", timeout=30)
    except Exception:  # noqa: BLE001 — unreachable site is an unconfirmed name
        return False
    return _compact(name) in _compact(text)


def _domain_for_name(name: str, search=None, fetch=None) -> str:
    """Turn a company name the model read out of prose into a domain, or into nothing.

    docs/126 R2: the name is spent as a query and never stored. What comes back is
    only kept when the site it points at says that name itself — otherwise the model's
    reading of the blog goes in the bin, which is the outcome docs/124 R1 wants for
    anything a second source will not confirm.
    """
    try:
        rows = (search or naver_page_search)(name, 3)
    except Exception:  # noqa: BLE001 — one name, not the channel
        return ""
    for row in rows:
        host = row.get("domain") or ""
        if host and is_company_site(f"http://{host}") and _site_says_its_name(host, name, fetch):
            return host
    return ""


def naver_blog_browser(query: str, limit: int = 20) -> list[Candidate]:
    """Korean blogs, where the company is named in the prose and never linked.

    Measured 2026-09-10 on `LED 전광판 유통업체`: the blog results carry 73KB of text and
    exactly zero new company links — three domains already found by the web channel and
    one openstreetmap.org. Inside that text sits 진영LED전광판, a real company with no
    link anywhere on the page. Reading the links is not a thin version of this channel;
    it is a total miss.
    """
    from app import browser_harvest

    url = ("https://search.naver.com/search.naver?where=blog&query="
           + urllib.parse.quote(query))
    names = browser_harvest.read_with_browser(
        url, task="prose", query=query, limit=_MAX_PROSE_NAMES,
        allow=("*.naver.com",))
    out: list[Candidate] = []
    seen: set[str] = set()
    for name in names[:_MAX_PROSE_NAMES]:
        host = _domain_for_name(name)
        if not host or host in seen:
            continue
        seen.add(host)
        out.append({"domain": host, "website": host,
                    "country": "South Korea", "source": "naver-blog"})
        if len(out) >= limit:
            break
    return out


# --------------------------------------------------------------- registry

SOURCES: dict[str, Source] = {
    "duckduckgo": Source(
        name="duckduckgo", label="搜索引擎", kind="page",
        readers={"http": duckduckgo_search}),
    "naver-web": Source(
        name="naver-web", label="Naver 搜索（韩国）", kind="page",
        readers={"http": naver_page_search}),
    # Kept for the day the account exists: the API returns cleaner results and the local
    # endpoint carries addresses and phone numbers the page does not.
    "naver": Source(
        name="naver", label="Naver API 网页搜索", kind="api",
        readers={"http": naver_search},
        unavailable=_naver_unavailable, optional=True),
    "naver-local": Source(
        name="naver-local", label="Naver API 本地商户", kind="api",
        readers={"http": naver_local},
        unavailable=_naver_unavailable, optional=True),
    # Everything below opens a window or needs a login Allen has to give, so none of it
    # is unattended (docs/126 R5), and all of it is optional: an unconfigured browser
    # route must not be reported as a channel that broke today.
    #
    # Google declares both browsers, cheapest first. Measured 2026-09-11: all three
    # readers got the unusual-traffic page, the real Chrome window included, with the
    # machine's own IP printed on it — the wall is the address we come from, not the
    # reader. The channel stays registered because an IP changes; what it must not do is
    # answer "0 家" while being turned away (docs/128 R2).
    "google": Source(
        name="google", label="Google 搜索（浏览器）", kind="browser",
        readers={"playwright": _playwright_search("google"),
                 "browser": _browser_search("google", "https://www.google.com/search?q={q}",
                                            ("*.google.com",))},
        unavailable=_browser_unavailable, optional=True, unattended=False),
    "naver-blog": Source(
        name="naver-blog", label="Naver 博客（浏览器读正文）", kind="browser",
        readers={"browser": naver_blog_browser},
        unavailable=_browser_unavailable, optional=True, unattended=False),
    # docs/128 R4. Registered now so the channels page can say how to switch them on;
    # until a collection account is logged in they report 未启用 and read nothing.
    "instagram": Source(
        name="instagram", label="Instagram 搜索（采集账号）", kind="social",
        readers={"playwright": _playwright_search("instagram")},
        unavailable=lambda: _scrape_unavailable("instagram"),
        optional=True, unattended=False),
    "facebook": Source(
        name="facebook", label="Facebook 主页搜索（采集账号）", kind="social",
        readers={"playwright": _playwright_search("facebook")},
        unavailable=lambda: _scrape_unavailable("facebook"),
        optional=True, unattended=False),
}


def available(conn=None) -> list[Source]:
    return [s for s in SOURCES.values() if s.available()]


def status() -> list[dict]:
    """What each channel can do right now, for the report and the channels page."""
    return [{"name": s.name, "label": s.label, "kind": s.kind,
             "available": s.available(), "reason": s.unavailable(),
             "optional": s.optional, "engines": list(s.engines),
             "unattended": s.unattended}
            for s in SOURCES.values()]


def gather(queries: list[str], limit_per_query: int = 20,
           only: list[str] | None = None, engine: str | None = None) -> dict:
    """Ask every usable channel, and report each one's outcome separately.

    One channel failing must never take the day's prospecting with it (docs/70 R2):
    Naver redesigns, Google rate-limits and Instagram wants a fresh login, and those
    never happen on the same day.
    """
    results: dict[str, Candidate] = {}
    per_source: list[dict] = []
    for source in SOURCES.values():
        if only and source.name not in only:
            continue
        # docs/126 R5. `gather` is the unattended path — the Agent's nightly prospecting
        # ends up here — and a channel that opens a Chrome window must never be reached
        # by a timer. Naming it explicitly in `only` is Allen pressing the button.
        if not source.unattended and not only:
            continue
        if not source.available():
            per_source.append({"name": source.name, "status": "未启用",
                               "reason": source.unavailable(), "found": 0})
            continue
        found = 0
        errors: list[str] = []
        for query in queries:
            try:
                for candidate in source.fetch(query, limit_per_query, engine):
                    key = candidate.get("domain")
                    if key and key not in results:
                        results[key] = candidate
                        found += 1
            except Exception as exc:  # noqa: BLE001 — one channel, not the day
                errors.append(str(exc)[:120])
        per_source.append({
            "name": source.name, "found": found,
            "status": "失败" if errors and not found else "ok",
            "reason": errors[0] if errors else "",
        })
    return {"candidates": list(results.values()), "sources": per_source}

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
    """One place to look for customers."""

    name: str
    label: str
    kind: str                      # api | page | browser
    fetch: Callable[[str, int], list[Candidate]]
    # Why this channel cannot run right now, or "" when it can. Being unconfigured and
    # being broken are different states and the report must not merge them (docs/70 R4).
    unavailable: Callable[[], str] = field(default=lambda: "")
    # An alternative route that is fine to leave unconfigured. Reporting it as 未启用
    # every day would be a daily reminder of a door Allen cannot open — NAVER Cloud
    # Platform wants Korean real-name verification — while the page channel already
    # covers the same market.
    optional: bool = False

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


# --------------------------------------------------------------- registry

SOURCES: dict[str, Source] = {
    "duckduckgo": Source(
        name="duckduckgo", label="搜索引擎", kind="page", fetch=duckduckgo_search),
    "naver-web": Source(
        name="naver-web", label="Naver 搜索（韩国）", kind="page",
        fetch=naver_page_search),
    # Kept for the day the account exists: the API returns cleaner results and the local
    # endpoint carries addresses and phone numbers the page does not.
    "naver": Source(
        name="naver", label="Naver API 网页搜索", kind="api", fetch=naver_search,
        unavailable=_naver_unavailable, optional=True),
    "naver-local": Source(
        name="naver-local", label="Naver API 本地商户", kind="api",
        fetch=naver_local, unavailable=_naver_unavailable, optional=True),
}


def available(conn=None) -> list[Source]:
    return [s for s in SOURCES.values() if s.available()]


def status() -> list[dict]:
    """What each channel can do right now, for the report and the channels page."""
    return [{"name": s.name, "label": s.label, "kind": s.kind,
             "available": s.available(), "reason": s.unavailable(),
             "optional": s.optional}
            for s in SOURCES.values()]


def gather(queries: list[str], limit_per_query: int = 20,
           only: list[str] | None = None) -> dict:
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
        if not source.available():
            per_source.append({"name": source.name, "status": "未启用",
                               "reason": source.unavailable(), "found": 0})
            continue
        found = 0
        errors: list[str] = []
        for query in queries:
            try:
                for candidate in source.fetch(query, limit_per_query):
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

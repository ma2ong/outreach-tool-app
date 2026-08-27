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
)


def host_of(url: str) -> str:
    match = _HOST.match(str(url or "").strip())
    return match.group(1).lower() if match else ""


def is_company_site(url: str) -> bool:
    host = host_of(url)
    return bool(host) and not any(bad in host for bad in _NOT_A_COMPANY)


# --------------------------------------------------------------- naver

_NAVER_TAGS = re.compile(r"<[^>]+>")


def _naver_keys() -> tuple[str, str]:
    return (os.environ.get("NAVER_CLIENT_ID", ""),
            os.environ.get("NAVER_CLIENT_SECRET", ""))


def _naver_unavailable() -> str:
    cid, secret = _naver_keys()
    if not cid or not secret:
        return "没有配置 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET"
    return ""


def naver_search(query: str, limit: int = 20) -> list[Candidate]:
    """Korean web search through Naver's official open API.

    Korea is the primary market and Google's coverage there is thin. This is an official
    API with a free 25,000/day allowance, so it is the one channel that does not depend
    on scraping surviving a redesign.
    """
    import json
    import urllib.request

    cid, secret = _naver_keys()
    if not cid or not secret:
        return []
    url = ("https://openapi.naver.com/v1/search/webkr.json?display="
           f"{min(limit, 100)}&query={urllib.parse.quote(query)}")
    request = urllib.request.Request(url, headers={
        "X-Naver-Client-Id": cid, "X-Naver-Client-Secret": secret})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    out: list[Candidate] = []
    for item in payload.get("items", []):
        link = item.get("link") or ""
        if not is_company_site(link):
            continue
        out.append({
            "domain": host_of(link),
            "website": host_of(link),
            "title": _NAVER_TAGS.sub("", item.get("title") or "").strip(),
            "country": "South Korea",
            "source": "naver",
        })
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
    "naver": Source(
        name="naver", label="Naver（韩国）", kind="api", fetch=naver_search,
        unavailable=_naver_unavailable),
}


def available(conn=None) -> list[Source]:
    return [s for s in SOURCES.values() if s.available()]


def status() -> list[dict]:
    """What each channel can do right now, for the report and the channels page."""
    return [{"name": s.name, "label": s.label, "kind": s.kind,
             "available": s.available(), "reason": s.unavailable()}
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

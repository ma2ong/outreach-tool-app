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
    # A channel may expose readers with different prerequisites. Google Playwright
    # needs Playwright; browser-use needs its separate venv and model key.
    reader_unavailable: dict[str, Callable[[], str]] = field(default_factory=dict)
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

    def fetch(self, query: str, limit: int = 20, engine: str | None = None,
              *, unattended: bool = False) -> list[Candidate]:
        """Read this channel, cheapest reader first, falling through on nothing (R8).

        A reader stops being the answer in three ways — it throws, it gets walled, or it
        comes back empty because a selector moved under it — and none of those mean the
        market is empty. docs/124 R4 already handled this by hand: a page that harvested
        zero companies is exactly where the browser button appeared. The only thing that
        needed a person in it was the decision, and the decision is always the same.

        Naming a reader means that reader and no other: a request that asked for `http`
        and quietly got a Chrome window is not an answer to the question asked.

        `unattended` is what keeps docs/126 R5 intact. A fallback is precisely how a
        timer ends up opening Chrome at 3am, so on that path the window-opening readers
        are not in the list at all.
        """
        if engine and engine not in self.readers:
            raise ValueError(
                f"{self.name} 没有「{engine}」这种读法，它声明的是：{'/'.join(self.engines)}")
        if engine:
            return self.readers[engine](query, limit)
        chain = [e for e in self.engines if not (unattended and e == "browser")]
        failure: Exception | None = None
        for name in chain:
            try:
                rows = self.readers[name](query, limit)
            except Exception as exc:  # noqa: BLE001 — the next reader is the recovery
                failure = exc
                continue
            if rows:
                return rows
        if failure is not None:
            raise failure
        return []

    def reason(self, engine: str | None = None) -> str:
        selected = engine or next(iter(self.readers), "")
        check = self.reader_unavailable.get(selected, self.unavailable)
        return check()

    def available(self, engine: str | None = None) -> bool:
        return not self.reason(engine)


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


# --------------------------------------------------------------- google

# Google's own door, the one it leaves open. Measured 2026-09-11, eight attempts at the
# front door — jina, headless Chromium, a headed real Chrome, the same with every
# automation flag stripped and `navigator.webdriver` false, and a profile warmed by an
# undriven Chrome — produced one momentary pass and seven "unusual traffic" walls. The
# wall is this machine's address as far as the public search page is concerned, and the
# Programmable Search API does not have one: 100 queries a day, free, no browser.
_GOOGLE_CSE_FILE = "google_cse.txt"
_GOOGLE_URL = "https://www.googleapis.com/customsearch/v1"
# The order matters and the creation page does not tell you: it insists on at least one
# site before it will create anything, and the "search the entire web" switch only
# appears afterwards, in the engine's own settings.
_GOOGLE_HOWTO = (
    "没有配置 Google 搜索 API。两个值，都免费，五分钟拿到："
    "① 到 https://programmablesearchengine.google.com/ 新建搜索引擎：随便起个名，"
    "「要搜索的网站」先填一个占位的 www.example.com（这一步必填，否则创建不了），"
    "勾人机验证后创建；② 创建完进它的设置页，打开「搜索整个网络」，"
    "再把 www.example.com 那条删掉，然后复制「搜索引擎 ID」（cx）；"
    "③ 拿 API key：先到 https://console.cloud.google.com/apis/library/customsearch.googleapis.com "
    "选一个项目并点「启用」，再到 https://console.cloud.google.com/apis/credentials "
    "点「创建凭据 → API 密钥」，复制那串 AIzaSy…。"
    "把 key 和 cx 各写一行进 backend/google_cse.txt，顺序随意。"
    "（每天 100 次免费，超出才收费）")


def _google_cse_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        _GOOGLE_CSE_FILE)


def _google_cse() -> tuple[str, str]:
    """The API key and the search engine id, in whichever order they were written.

    Two opaque strings in a text file is a coin flip, and a wrong guess costs a whole
    round trip to discover. Their shapes differ — a Google API key starts with `AIza`
    and is about forty characters; a search engine id does not — so the file does not
    have to be written in a particular order to work.
    """
    key = os.environ.get("GOOGLE_CSE_KEY", "")
    cx = os.environ.get("GOOGLE_CSE_ID", "")
    if key and cx:
        return key, cx
    try:
        with open(_google_cse_path(), encoding="utf-8") as handle:
            lines = [line.strip() for line in handle if line.strip()]
    except OSError:
        return key, cx
    for line in lines:
        if line.startswith("AIza"):
            key = key or line
        elif not cx or line != key:
            cx = cx or line
    return key, cx


def _google_unavailable() -> str:
    key, cx = _google_cse()
    return "" if key and cx else _GOOGLE_HOWTO


def google_hint(status: int, body: str) -> str:
    """Turn Google's refusal into the step that fixes it (docs/70 R4, docs/128 R2).

    Both of these are ordinary and both look like a wall of JSON: the API not switched
    on for the project the key belongs to, and the free 100 calls spent for the day.
    """
    text = str(body or "")[:300]
    if status == 403 and "does not have the access" in text:
        # 两种原因，第二种是 2026-09-11 实测出来的：全新项目、API 确认已启用、
        # key 就在该项目里且限制只放行 Custom Search，依然被拒——账号那条
        # 「免费试用需要支付预付款」横幅是跨项目的，免费额度不发给这种状态的账号。
        return ("Google 拒绝了这把 key。两种可能：① Custom Search API 没有在**这把 key "
                "所在的项目**里启用（到 "
                "https://console.cloud.google.com/apis/library/customsearch.googleapis.com "
                "切到那个项目点「启用」）；② 这个 Google 账号的结算/试用状态拿不到免费额度"
                "——控制台顶部若挂着「免费试用需要支付预付款」，换项目也没用，要么处理结算，"
                "要么就别用这条渠道（其余渠道不受影响）")
    if status == 429 or "Quota exceeded" in text:
        return "今天的 100 次免费额度用完了，明天自动恢复（超额才收费，系统不会替你付钱）"
    return f"Google {status}: {text}"


def _google_call(key: str, cx: str, query: str, count: int) -> dict:
    import json as _json
    import urllib.error
    import urllib.request

    url = f"{_GOOGLE_URL}?" + urllib.parse.urlencode(
        {"key": key, "cx": cx, "q": query, "num": min(max(count, 1), 10)})
    try:
        with urllib.request.urlopen(url, timeout=25) as response:
            return _json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 429 is the daily quota, 403 is usually the API not enabled yet. Both are
        # sentences Allen can act on; a bare status code is not (docs/128 R2).
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(google_hint(exc.code, detail)) from exc


def google_api_search(query: str, limit: int = 20) -> list[Candidate]:
    """Google, asked the way Google is willing to answer (docs/128 R9)."""
    key, cx = _google_cse()
    if not (key and cx):
        raise RuntimeError(_GOOGLE_HOWTO)
    payload = _google_call(key, cx, query, limit)
    out: list[Candidate] = []
    seen: set[str] = set()
    for item in payload.get("items") or []:
        link = item.get("link") or ""
        if not is_company_site(link):
            continue
        host = host_of(link)
        if not host or host in seen:
            continue
        seen.add(host)
        out.append({"domain": host, "website": host, "source": "google",
                    "title": str(item.get("title") or "").strip()})
        if len(out) >= limit:
            break
    return out


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

        rows = [{"domain": host, "website": host, "source": name,
                 **({"country": country} if country else {})}
                for host in scrape_browser.read_hosts(name, query, limit)
                if is_company_site(f"http://{host}")]
        return rows[:limit]
    return fetch


def _facebook_page_urls(query: str, limit: int = 10) -> list[str]:
    """Where Facebook pages are found, given that Facebook's own search will not say.

    Logged out, `facebook.com/search/pages/` answers `Not Found` in nine bytes. A plain
    web search does answer, and the one already running here is free and unattended.
    """
    from app.search import search_urls

    return search_urls(f"site:facebook.com {query}", limit=max(limit * 3, limit))


def instagram_accounts(query: str, limit: int = 20) -> list[Candidate]:
    """Companies found through their Instagram account (docs/128 R5).

    Instagram's search matches **account names**, not descriptions: `pantallas led`
    returns five Latin American LED companies and `led display distributor` returns
    nothing at all. Short, name-like keywords are what this channel is for.

    Only the domain crosses (docs/124 R1) — the bio's phone and email stay on the page —
    and the handle rides along so the company arrives carrying the address its DMs would
    go to.
    """
    from app import scrape_browser

    payload = scrape_browser.read_search(
        "instagram", instagram_query(query), min(limit, MAX_INSTAGRAM_PROFILES))
    rows = payload.get("pages") or [{"domain": h} for h in payload.get("hosts") or []]
    out: list[Candidate] = []
    seen: set[str] = set()
    for row in rows:
        host = (row.get("domain") or "").lower()
        if not host or host in seen or not is_company_site(f"http://{host}"):
            continue
        seen.add(host)
        candidate: Candidate = {"domain": host, "website": host, "source": "instagram"}
        if row.get("handle"):
            candidate["instagram"] = row["handle"]
        out.append(candidate)
    return out


def instagram_browser(query: str, limit: int = 20) -> list[Candidate]:
    """The same channel read by a model instead of a selector (docs/128 R8).

    Instagram's search endpoint and its profile markup are Meta's to change, and the day
    they do, `instagram_accounts` returns nothing at all. browser-use is the reader that
    does not care what the DOM looks like — it costs a model call per step and a visible
    window, which is why it is second and why a timer never reaches it.

    It drives the collecting profile, not the sending one, and it never leaves
    instagram.com.
    """
    from app import browser_harvest, scrape_browser

    hosts = browser_harvest.read_with_browser(
        "https://www.instagram.com/", task="social",
        query=instagram_query(query), limit=min(limit, MAX_INSTAGRAM_PROFILES),
        allow=("*.instagram.com",), profile_dir=scrape_browser.profile_dir("instagram"))
    return [{"domain": host, "website": host, "source": "instagram"}
            for host in hosts if is_company_site(f"http://{host}")]


def facebook_public_pages(query: str, limit: int = 20) -> list[Candidate]:
    """Companies found through their public Facebook page (docs/128 R4).

    No account is involved on either end: the pages are public, the reader is a
    logged-out headless browser, and nothing here can be banned. Only the domain crosses
    (docs/124 R1) — the About tab's email and phone stay on the page, and `enrich_domain`
    reads the company's own site for those as it does for every other channel. What the
    page adds is its own handle, so a company arrives already carrying the address its
    Facebook DMs would go to.
    """
    from app import scrape_browser
    from app.scrape_runner import handles_from_hrefs

    handles = handles_from_hrefs(_facebook_page_urls(query, limit), "facebook")[:limit]
    out: list[Candidate] = []
    seen: set[str] = set()
    for row in scrape_browser.read_pages("facebook", handles, limit):
        host = (row.get("domain") or "").lower()
        # A page with no site on it is a page, not a company we can write to.
        if not host or host in seen or not is_company_site(f"http://{host}"):
            continue
        seen.add(host)
        out.append({"domain": host, "website": host, "source": "facebook",
                    "facebook": row.get("handle")})
    return out


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


# How many profiles one unattended Instagram run may walk. `gather` asks for 20 by
# default, and twenty profile visits per keyword on a spare account, every night, is how
# a spare account stops working.
MAX_INSTAGRAM_PROFILES = 8

# Instagram matches account names, not descriptions: measured 2026-09-11,
# `LED video wall installer contact` matches nothing at all while `led video wall`
# matches four accounts. The unattended path inherits Allen's keyword lines, which are
# written as descriptions, so the head of the phrase is what gets asked.
_INSTAGRAM_WORDS = 3


def instagram_query(query: str) -> str:
    return " ".join(str(query or "").split()[:_INSTAGRAM_WORDS])


_BLOG_SYSTEM = (
    "你在读韩国博客的搜索结果页。找出正文里被提到的公司（LED 显示屏的供应商、安装商、"
    "经销商、制造商）。只回公司名字本身，按页面上的写法原样输出，不要网址、不要邮箱、"
    "不要电话。返回 JSON：{\"companies\":[{\"name\":\"회사 이름\"}]}")
# The page is 85KB of markdown and the names sit in the posts' own text. Sending more
# than this buys nothing: the results below the fold are the same blogs paginated.
_BLOG_CHARS = 40000


def _blog_text(query: str) -> str:
    from app.jina import fetch

    return fetch("https://search.naver.com/search.naver?where=blog&query="
                 + urllib.parse.quote(query), timeout=60)


def _names_from_prose(text: str, limit: int) -> list[str]:
    """One cheap model call over text that was fetched for free (docs/128 R7)."""
    from app.agent import llm

    data = llm.deepseek_json(_BLOG_SYSTEM, text[:_BLOG_CHARS])
    out: list[str] = []
    for row in data.get("companies") or []:
        name = " ".join(str((row or {}).get("name") or "").split())[:80]
        if name and name not in out:
            out.append(name)
        if len(out) >= limit:
            break
    return out


def naver_blog_prose(query: str, limit: int = 20) -> list[Candidate]:
    """Korean blogs, read the cheap way: free text plus one model call.

    docs/126 gave this channel to browser-use because the companies are named in prose
    with no link. That was the right reader for the wrong reason — the prose was never
    behind the browser. `jina` already returned 85,749 characters of it, and pulling the
    names out is one DeepSeek call of 1.6 seconds against browser-use's 85-121 and a
    window on Allen's screen.

    docs/126 R2 is unchanged and is what keeps this honest: a name is spent as a query
    and only kept when the site it resolves to says that name itself.
    """
    names = _names_from_prose(_blog_text(query), _MAX_PROSE_NAMES)
    out: list[Candidate] = []
    seen: set[str] = set()
    for name in names:
        host = _domain_for_name(name)
        if not host or host in seen:
            continue
        seen.add(host)
        out.append({"domain": host, "website": host,
                    "country": "South Korea", "source": "naver-blog"})
        if len(out) >= limit:
            break
    return out


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
    # Two legs, and the second one is not a luxury: the first goes through jina, which
    # is a service someone else runs. Measured 2026-09-11, a headless browser reads the
    # same results page and finds the same kind of company (docs/128 R8).
    "naver-web": Source(
        name="naver-web", label="Naver 搜索（韩国）", kind="page",
        readers={"http": naver_page_search,
                 "playwright": _playwright_search("naver-web", country="South Korea")},
        reader_unavailable={"playwright": lambda: _scrape_unavailable("naver-web")}),
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
        readers={"http": google_api_search,
                 "playwright": _playwright_search("google"),
                 "browser": _browser_search("google", "https://www.google.com/search?q={q}",
                                            ("*.google.com",))},
        reader_unavailable={"http": _google_unavailable,
                            "playwright": lambda: _scrape_unavailable("google"),
                            "browser": _browser_unavailable},
        optional=True, unattended=True),
    # Cheapest first: the prose is free to fetch and one model call reads it. The
    # browser-use route stays declared for a page the fetch cannot open (docs/128 R7).
    "naver-blog": Source(
        name="naver-blog", label="Naver 博客（读正文）", kind="page",
        readers={"http": naver_blog_prose, "browser": naver_blog_browser},
        optional=True, unattended=True),
    # docs/128 R4. Registered now so the channels page can say how to switch them on;
    # until a collection account is logged in they report 未启用 and read nothing.
    # Headless, so nothing opens on Allen's screen; capped, because the account that
    # makes it possible is one he would rather not replace (docs/128 R7).
    "instagram": Source(
        name="instagram", label="Instagram 搜索（采集小号）", kind="social",
        readers={"playwright": instagram_accounts, "browser": instagram_browser},
        unavailable=lambda: _scrape_unavailable("instagram"),
        reader_unavailable={"playwright": lambda: _scrape_unavailable("instagram"),
                            "browser": _browser_unavailable},
        optional=True, unattended=True),
    # The one channel that needs a browser and still runs with nobody there: public
    # pages, a logged-out headless reader, no account to lose (docs/128 R4).
    "facebook": Source(
        name="facebook", label="Facebook 公共主页", kind="social",
        readers={"playwright": facebook_public_pages},
        unavailable=lambda: _scrape_unavailable("facebook"),
        optional=True, unattended=True),
}


def available(conn=None) -> list[Source]:
    return [s for s in SOURCES.values() if s.available()]


def status() -> list[dict]:
    """What each channel can do right now, for the report and the channels page."""
    return [{"name": s.name, "label": s.label, "kind": s.kind,
             "available": s.available(), "reason": s.reason(),
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
        if not source.available(engine):
            per_source.append({"name": source.name, "status": "未启用",
                               "reason": source.reason(engine), "found": 0})
            continue
        found = 0
        errors: list[str] = []
        for query in queries:
            try:
                for candidate in source.fetch(query, limit_per_query, engine,
                                              unattended=not only):
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

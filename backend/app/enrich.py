import re
from typing import Callable

from app.brief import build as build_brief
from app.icp import classify_text
from app.jina import fetch as jina_fetch

_EMAIL = re.compile(r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}', re.I)
_JUNK = ("sentry", "wixpress", "example.", "@2x", "@3x", ".png", ".jpg", ".jpeg", ".gif", ".webp",
         "noreply", "no-reply", "donotreply", "do-not-reply")
_PREFER = ("info@", "sales@", "contact@", "hello@", "enquiries@", "office@")

_TITLE = re.compile(r'^\s*(?:#\s+|Title:\s*)(.+)$', re.I | re.M)
_TITLE_SEP = re.compile(r'\s+[|\-–—]\s+')

_WA = re.compile(r'(?:wa\.me/|api\.whatsapp\.com/send\?phone=)(?:%2B|\+)?(\d{8,15})', re.I)
_TEL = re.compile(r'tel:\+?([\d\-().\s]{8,20})', re.I)
_INTL = re.compile(r'\+\d[\d\-().\s]{7,18}\d')

_IG = re.compile(r'instagram\.com/([A-Za-z0-9_.]{2,30})', re.I)
_IG_JUNK = {"p", "reel", "reels", "explore", "accounts", "stories", "share", "tv"}
_FB = re.compile(r'facebook\.com/([A-Za-z0-9_.\-]{2,50})', re.I)
_FB_JUNK = {"sharer", "sharer.php", "share.php", "share", "plugins", "tr", "dialog",
            "login", "groups", "events", "hashtag", "photo.php", "profile.php",
            "pages", "watch", "policy.php", "privacy"}
_LI = re.compile(r'linkedin\.com/(company|in)/([A-Za-z0-9_\-%.]+)', re.I)


def extract_emails(text: str) -> list[str]:
    out, seen = [], set()
    for m in _EMAIL.finditer(text):
        e = m.group(0)
        low = e.lower()
        if any(j in low for j in _JUNK):
            continue
        if low not in seen:
            seen.add(low)
            out.append(e)
    return out


def _digits(raw: str) -> str:
    return re.sub(r'\D', '', raw)


def extract_phones(text: str) -> list[str]:
    """Normalized +digits, WhatsApp (wa.me) numbers first."""
    out, seen = [], set()
    groups = (
        [m.group(1) for m in _WA.finditer(text)],
        [m.group(1) for m in _TEL.finditer(text)],
        [m.group(0) for m in _INTL.finditer(text)],
    )
    for grp in groups:
        for raw in grp:
            d = _digits(raw)
            if not 8 <= len(d) <= 15 or d in seen:
                continue
            seen.add(d)
            out.append("+" + d)
    return out


def extract_socials(text: str) -> dict:
    ig = fb = li = None
    for m in _IG.finditer(text):
        h = m.group(1)
        if h.lower() not in _IG_JUNK:
            ig = h
            break
    for m in _FB.finditer(text):
        h = m.group(1)
        if h.lower() not in _FB_JUNK:
            fb = h
            break
    m = _LI.search(text)
    if m:
        li = f"linkedin.com/{m.group(1).lower()}/{m.group(2)}"
    return {"instagram": ig, "facebook": fb, "linkedin": li}


_GENERIC_TITLES = {
    "contact", "contact us", "contacts", "contact-us", "contacto", "contáctanos",
    "contactanos", "contato", "contate-nos", "kontakt", "문의", "연락처",
    "home", "homepage", "inicio", "início", "início-2", "start",
    "404", "page not found", "not found", "error", "página não encontrada",
    "pagina nao encontrada", "página no encontrada", "error 404",
    "about", "about us", "sobre", "nosotros", "quienes somos", "회사소개",
}


def extract_company_name(text: str) -> str | None:
    """Best-effort company name from a page title / first markdown H1."""
    m = _TITLE.search(text)
    if not m:
        return None
    name = _TITLE_SEP.split(m.group(1).strip())[0].strip()
    if not name or name.lower().strip(" -–—|") in _GENERIC_TITLES:
        return None
    return name


_PATH_SOURCE = {"/contact": "site.contact-page", "/contact-us": "site.contact-page",
                "": "site.homepage"}
_CONTACT_PATHS = ("/contact", "/contact-us", "")

_LINK_RE = re.compile(r'\[([^\]]{0,80})\]\((https?://[^)\s]+)\)')
# Evergreen company/product pages are used to improve ICP and cold-message evidence.
_CONTENT_LINK_WORDS = {
    "product": 3, "products": 3, "productos": 3, "produtos": 3, "goods": 3,
    "catalog": 3, "catalogo": 3, "catálogo": 3, "제품": 3, "상품": 3,
    "about": 2, "aboutus": 2, "about-us": 2, "company": 2, "corp": 2, "profile": 2,
    "empresa": 2, "sobre": 2, "nosotros": 2, "quienes": 2, "shopinfo": 2,
    "회사": 2, "회사소개": 2, "소개": 2,
    "service": 1, "services": 1, "servicios": 1, "solution": 1, "solutions": 1,
    "business": 1, "portfolio": 1, "project": 1, "projects": 1, "사업": 1, "서비스": 1,
}
# Current-event pages are followed independently. A company already listing P2.5 on the
# homepage may still announce an RFQ tomorrow; product evidence must not suppress radar.
_SIGNAL_LINK_WORDS = {
    "news": 4, "press": 4, "updates": 3, "career": 4, "careers": 4, "jobs": 4,
    "tender": 5, "procurement": 5, "rfp": 5, "rfq": 5, "bid": 4,
    "event": 3, "events": 3, "expo": 3, "exhibition": 3,
    "뉴스": 4, "소식": 4, "공지": 4, "채용": 5, "입찰": 5, "조달": 5, "전시": 3,
    "新闻": 4, "资讯": 4, "招聘": 5, "招标": 5, "采购": 5, "展会": 3,
}
_LINK_SKIP = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".pdf", ".zip",
              "facebook.com", "instagram.com", "youtube.com", "linkedin.com",
              "twitter.com", "x.com", "kakao", "naver.me")
_MAX_FOLLOWED = 2
_MAX_SIGNAL_FOLLOWED = 2


def _rank_links(text: str, domain: str, seen: set[str], words: dict[str, int],
                limit: int) -> list[str]:
    host = domain.split("/")[0].lower().removeprefix("www.")
    scored: dict[str, int] = {}
    for label, url in _LINK_RE.findall(text or ""):
        clean = url.rstrip(").,")
        low = clean.lower()
        if clean in seen or any(s in low for s in _LINK_SKIP):
            continue
        if host not in low.split("?")[0]:
            continue
        haystack = f"{low} {label.lower()}"
        score = sum(weight for word, weight in words.items() if word in haystack)
        if score:
            scored[clean] = max(scored.get(clean, 0), score)
    return sorted(scored, key=lambda u: (-scored[u], u))[:limit]


def _content_links(text: str, domain: str, seen: set[str]) -> list[str]:
    """Same-host evergreen pages, best evidence candidates first."""
    return _rank_links(text, domain, seen, _CONTENT_LINK_WORDS, _MAX_FOLLOWED)


def _signal_links(text: str, domain: str, seen: set[str]) -> list[str]:
    """Same-host current-event pages, independently capped from product enrichment."""
    return _rank_links(text, domain, seen, _SIGNAL_LINK_WORDS, _MAX_SIGNAL_FOLLOWED)


def _fetch_extra(pages: list[dict], urls: list[str], fetch: Callable[[str], str]) -> None:
    for url in urls:
        try:
            text = fetch(url)
        except Exception:  # noqa: BLE001
            continue
        pages.append({"url": url, "text": text})


def enrich_domain(domain: str, fetch: Callable[[str], str] = jina_fetch) -> dict:
    from app.brief import _pitches
    from app.signal_detector import detect_pages

    emails: list[str] = []
    email_sources: dict[str, str] = {}
    phones: list[str] = []
    socials = {"instagram": None, "facebook": None, "linkedin": None}
    company = None
    home_company = None
    pages: list[dict] = []
    for path in _CONTACT_PATHS:
        url = f"https://{domain}{path}"
        try:
            text = fetch(url)
        except Exception:  # noqa: BLE001
            continue
        pages.append({"url": url, "text": text})
        name = extract_company_name(text)
        if path == "":
            home_company = name
        if company is None:
            company = name
        for e in extract_emails(text):
            email_sources.setdefault(e.lower(), _PATH_SOURCE[path])
            if e not in emails:
                emails.append(e)
        for p in extract_phones(text):
            if p not in phones:
                phones.append(p)
        for k, v in extract_socials(text).items():
            if socials[k] is None:
                socials[k] = v
        if emails and phones and all(socials.values()):
            break
    company = home_company or company

    joined = "\n".join(page["text"] for page in pages)
    seen = {page["url"] for page in pages}
    # Improve product/company evidence only when the contact pass did not already find a
    # specific pitch. This keeps the old bounded behavior.
    if not _pitches(joined):
        urls = _content_links(joined, domain, seen)
        _fetch_extra(pages, urls, fetch)
        seen.update(urls)

    # Buying-window pages are a separate bounded pass. This still reuses links from the
    # pages we already fetched and never becomes a site-wide crawler.
    radar_text = "\n".join(page["text"] for page in pages)
    signal_urls = _signal_links(radar_text, domain, seen)
    _fetch_extra(pages, signal_urls, fetch)

    text = "\n".join(page["text"] for page in pages)
    icp = classify_text(text)
    best = None
    for e in emails:
        if any(e.lower().startswith(p) for p in _PREFER):
            best = e
            break
    if best is None and emails:
        best = emails[0]
    written = build_brief(text, icp=icp)
    return {"domain": domain, "pages": len(pages),
            "emails": emails, "email": best, "company": company,
            "email_source": email_sources.get(best.lower()) if best else None,
            "phone": phones[0] if phones else None, "phones": phones,
            "icp_type": icp["icp_type"], "fit_score": icp["fit_score"],
            "brief": written["brief"], "hook": written["hook"],
            "buying_signals": detect_pages(pages), **socials}

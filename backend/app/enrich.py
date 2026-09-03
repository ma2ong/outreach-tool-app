import re
from typing import Callable

from app import screening
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
# The '+' is captured, not skipped: it is the only thing separating a dialable
# international number from a local one.
_TEL = re.compile(r'tel:(\+?[\d\-().\s]{8,20})', re.I)
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
    """WhatsApp (wa.me) numbers first, then whatever the page prints.

    Only a number that already carries a country code keeps the '+' form. A local
    number written as 'tel:877.773.4346' has no country in it, and prefixing one
    ('+8777734346') both invents a country code screening would then read back as
    China and leaves a number nobody can dial. wa.me numbers are exempt: WhatsApp
    links are international by definition. A conventional `00` international prefix
    is normalized to `+` rather than being preserved as the fake country code `+00`.
    """
    out, seen = [], set()
    groups = (
        [(m.group(1), True) for m in _WA.finditer(text)],
        [(m.group(1), False) for m in _TEL.finditer(text)],
        [(m.group(0), True) for m in _INTL.finditer(text)],
    )
    for grp in groups:
        for raw, international in grp:
            cleaned = raw.strip()
            d = _digits(raw)
            international = international or cleaned.startswith(("+", "00"))
            if cleaned.startswith("00"):
                d = d[2:]
            if not 8 <= len(d) <= 15 or d in seen:
                continue
            seen.add(d)
            out.append("+" + d if international else cleaned)
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


# "Contact PixelFLEX" is a page title, not a company — eight records in the book carry
# one. Stripping the word costs us any prospect genuinely named "Contact <something>",
# which in an LED/AV lead base is a trade worth making.
_CONTACT_PREFIX = re.compile(r'^contact(?:\s+us)?\s*[-–—:|]\s*|^contact\s+(?!us\b)', re.I)

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
    # "Contact Us | Impact LED" names the page first and the company second, so take
    # the first part that is not just a page label.
    for part in _TITLE_SEP.split(m.group(1).strip()):
        name = _CONTACT_PREFIX.sub("", part.strip()).strip()
        if name and name.lower().strip(" -–—|") not in _GENERIC_TITLES:
            return name
    return None


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
# docs/94 R1. 案例页也独立一档。它和产品页回答的是两个问题：产品页说他们卖什么，
# 案例页说他们做过什么 —— 后者是开场白唯一的材料来源。以前 project/portfolio 挂在
# _CONTENT_LINK_WORDS 里、权重 1，永远抢不到那 2 个名额。
#
# 词表覆盖西语、葡语、韩语、中文：书里 1311 家客户分布在这些市场，只写英文
# 等于只对英文站生效。
_CASE_LINK_WORDS = {
    "case": 5, "cases": 5, "case-study": 5, "case-studies": 5, "casestudy": 5,
    "reference": 4, "references": 4, "project": 4, "projects": 4,
    "portfolio": 4, "installation": 4, "installations": 4, "gallery": 3,
    "work": 2, "works": 2, "clients": 2, "customers": 2,
    "proyecto": 4, "proyectos": 4, "obras": 4, "casos": 5, "referencias": 4,
    "projeto": 4, "projetos": 4, "realizacoes": 4, "realizações": 4,
    "시공사례": 5, "사례": 5, "실적": 4, "포트폴리오": 4, "구축사례": 5,
    "案例": 5, "工程案例": 5, "成功案例": 5, "项目": 4, "业绩": 4,
}

# Current-event pages are followed independently. A company already listing P2.5 on the
# homepage may still announce an RFQ tomorrow; product evidence must not suppress radar.
_SIGNAL_LINK_WORDS = {
    "news": 4, "press": 4, "updates": 3, "career": 4, "careers": 4, "jobs": 4,
    # docs/94 R3 —— blog 和 news 常常是同一个栏目的两个叫法，不另开一档。
    "blog": 4, "insights": 3, "stories": 3, "articles": 3, "noticias": 4,
    "notícias": 4, "블로그": 4, "博客": 4, "动态": 4,
    "tender": 5, "procurement": 5, "rfp": 5, "rfq": 5, "bid": 4,
    "event": 3, "events": 3, "expo": 3, "exhibition": 3,
    "뉴스": 4, "소식": 4, "공지": 4, "채용": 5, "입찰": 5, "조달": 5, "전시": 3,
    "新闻": 4, "资讯": 4, "招聘": 5, "招标": 5, "采购": 5, "展会": 3,
}
_LINK_SKIP = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".pdf", ".zip",
              "facebook.com", "instagram.com", "youtube.com", "linkedin.com",
              "twitter.com", "x.com", "kakao", "naver.me")
# docs/94：官网放开 —— 抓官网不碰任何登录态，不触发平台风控，代价只是几次
# r.jina.ai 请求和几秒钟。社媒的 20 次/天一动不动，那条线管的是封号，不是速度。
_MAX_FOLLOWED = 3
_MAX_SIGNAL_FOLLOWED = 3
_MAX_CASE_FOLLOWED = 3


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


def _case_links(text: str, domain: str, seen: set[str]) -> list[str]:
    """Same-host pages saying what this company has actually built (docs/94 R1)."""
    return _rank_links(text, domain, seen, _CASE_LINK_WORDS, _MAX_CASE_FOLLOWED)


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

    # Country is an identity fact. Infer it only from the bounded contact/home pass,
    # before following product, project, news or signal pages. Those later pages often
    # mention customer markets and case-study countries that are not the company's own.
    identity_text = "\n".join(page["text"] for page in pages)
    country = screening.country_from_text(identity_text)

    joined = identity_text
    seen = {page["url"] for page in pages}
    # Improve product/company evidence only when the contact pass did not already find a
    # specific pitch. This keeps the old bounded behavior.
    if not _pitches(joined):
        urls = _content_links(joined, domain, seen)
        _fetch_extra(pages, urls, fetch)
        seen.update(urls)

    # docs/94 R2. 案例那一轮不看 `_pitches`：点距是规格，案例是「他们上个月做了什么」，
    # 后者才是开场白的材料。知道他们卖 P2.5 不等于拿到了一句可以引用的话。
    #
    # 位置在 `country` 推断之后，一行都不能往上挪（R5）：一家葡萄牙公司的案例页上
    # 全是迪拜、新加坡、伦敦 —— 那些是客户所在地，不是他们自己的国家。
    case_urls = _case_links("\n".join(p["text"] for p in pages), domain, seen)
    _fetch_extra(pages, case_urls, fetch)
    seen.update(case_urls)

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
    return {"domain": domain, "pages": len(pages), "country": country,
            "emails": emails, "email": best, "company": company,
            "email_source": email_sources.get(best.lower()) if best else None,
            "phone": phones[0] if phones else None, "phones": phones,
            "icp_type": icp["icp_type"], "fit_score": icp["fit_score"],
            "brief": written["brief"], "hook": written["hook"],
            "buying_signals": detect_pages(pages), **socials}
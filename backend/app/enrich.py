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


# Page titles that name the page rather than the company. The contact page is fetched
# first, so without this the company name came back as "Contact", "Inicio", "Contact Us"
# — and on a site whose /contact 404s, "Página não encontrada".
_GENERIC_TITLES = {
    "contact", "contact us", "contacts", "contact-us", "contacto", "contáctanos",
    "contactanos", "contato", "contate-nos", "kontakt", "문의", "연락처",
    "home", "homepage", "inicio", "início", "início-2", "start",
    "404", "page not found", "not found", "error", "página não encontrada",
    "pagina nao encontrada", "página no encontrada", "error 404",
    "about", "about us", "sobre", "nosotros", "quienes somos", "회사소개",
}


def extract_company_name(text: str) -> str | None:
    """Best-effort company name from a page title / first markdown H1.

    Returns None for titles that name the page instead of the company — a lead called
    "Contact" is worse than one called after its own domain, because it looks like a
    real answer."""
    m = _TITLE.search(text)
    if not m:
        return None
    name = _TITLE_SEP.split(m.group(1).strip())[0].strip()
    if not name or name.lower().strip(" -–—|") in _GENERIC_TITLES:
        return None
    return name


# Which page an address was read off. Kept per-email so the address we end up choosing
# can say where it came from: a contact page address and a footer address are both real,
# but only one of them was put there for buyers to use.
_PATH_SOURCE = {"/contact": "site.contact-page", "/contact-us": "site.contact-page",
                "": "site.homepage"}
_CONTACT_PATHS = ("/contact", "/contact-us", "")

# Where the description of the business actually lives, when the contact pass found none.
#
# Guessing paths does not work. rgbkorea.com answers its homepage with a navigation shell
# and keeps every word about itself at /shopinfo/company.html — a Cafe24 convention no
# list of English guesses would ever contain. But the shell links to it, in plain sight.
# So instead of guessing, read the page's own links and follow the one it says is about
# the company or the products.
#
# The vocabulary is multilingual for the same reason the gloss table is: the markets that
# most need this are the ones that do not write their nav in English. That is not a
# per-country branch — every site is scored by the same table, and a Korean site scores
# on 회사소개 exactly as an English one scores on "about".
_LINK_RE = re.compile(r'\[([^\]]{0,80})\]\((https?://[^)\s]+)\)')
_LINK_WORDS = {
    # products — the strongest signal, since specs live there
    "product": 3, "products": 3, "productos": 3, "produtos": 3, "goods": 3,
    "catalog": 3, "catalogo": 3, "catálogo": 3, "제품": 3, "상품": 3,
    # who they are
    "about": 2, "aboutus": 2, "about-us": 2, "company": 2, "corp": 2, "profile": 2,
    "empresa": 2, "sobre": 2, "nosotros": 2, "quienes": 2, "shopinfo": 2,
    "회사": 2, "회사소개": 2, "소개": 2,
    # what they do
    "service": 1, "services": 1, "servicios": 1, "solution": 1, "solutions": 1,
    "business": 1, "portfolio": 1, "project": 1, "projects": 1, "사업": 1, "서비스": 1,
}
_LINK_SKIP = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".pdf", ".zip",
              "facebook.com", "instagram.com", "youtube.com", "linkedin.com",
              "twitter.com", "x.com", "kakao", "naver.me")
_MAX_FOLLOWED = 2


def _content_links(text: str, domain: str, seen: set[str]) -> list[str]:
    """The page's own links, best candidates first. Same host only — a supplier's link to
    a partner's catalogue would describe the wrong company."""
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
        score = sum(w for word, w in _LINK_WORDS.items() if word in haystack)
        if score:
            scored[clean] = max(scored.get(clean, 0), score)
    return sorted(scored, key=lambda u: -scored[u])[:_MAX_FOLLOWED]


def enrich_domain(domain: str, fetch: Callable[[str], str] = jina_fetch) -> dict:
    from app.brief import _pitches

    emails: list[str] = []
    email_sources: dict[str, str] = {}
    phones: list[str] = []
    socials = {"instagram": None, "facebook": None, "linkedin": None}
    company = None
    home_company = None
    all_text: list[str] = []
    for path in _CONTACT_PATHS:
        try:
            text = fetch(f"https://{domain}{path}")
        except Exception:  # noqa: BLE001
            continue
        all_text.append(text)
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
    # The homepage titles itself after the company; a subpage titles itself after itself.
    company = home_company or company

    # Triggered by a missing spec, not by a missing category. "Saw P1–P10 panels listed
    # on your site" is worth far more in a cold message than "Saw the rental work on your
    # site", and the pitch is almost never on the contact page — so a site that has told
    # us what it does but not what it sells is exactly the one worth two more fetches.
    joined = "\n".join(all_text)
    if not _pitches(joined):
        seen = {f"https://{domain}{p}" for p in _CONTACT_PATHS}
        for url in _content_links(joined, domain, seen):
            try:
                followed = fetch(url)
            except Exception:  # noqa: BLE001
                continue
            all_text.append(followed)

    text = "\n".join(all_text)
    icp = classify_text(text)
    best = None
    for e in emails:
        if any(e.lower().startswith(p) for p in _PREFER):
            best = e
            break
    if best is None and emails:
        best = emails[0]
    written = build_brief(text, icp=icp)
    # How many pages actually came back. Every fetch failure above is swallowed per-path
    # so one dead URL cannot lose the others — which means an entirely unreachable site
    # returns the same empty result as a site with nothing on it. Callers that care about
    # the difference (the backfill writes one off permanently, the other it must retry)
    # have no way to tell them apart without this.
    return {"domain": domain, "pages": len(all_text),
            "emails": emails, "email": best, "company": company,
            "email_source": email_sources.get(best.lower()) if best else None,
            "phone": phones[0] if phones else None, "phones": phones,
            "icp_type": icp["icp_type"], "fit_score": icp["fit_score"],
            "brief": written["brief"], "hook": written["hook"], **socials}

"""Conservative extraction of named business contacts from public company pages.

This is deliberately not an email-guesser. A candidate needs a named person plus a
relevant job title visible in public text. Email/LinkedIn only increase confidence when
they are present in the same small evidence window. The caller decides whether a
candidate is strong enough to promote into CRM.
"""
from __future__ import annotations

import re
import urllib.parse


COMMERCIAL_RE = re.compile(
    r"\b(?:head of procurement|procurement manager|purchasing manager|purchase manager|"
    r"senior buyer|buyer|owner|founder|co-founder|chief executive officer|ceo|president|"
    r"general manager|commercial director|commercial manager|managing director)\b|"
    r"대표이사|대표|사장|구매담당|구매팀장|구매부장|采购经理|采购负责人|采购总监|总经理|老板",
    re.I,
)
PROJECT_RE = re.compile(
    r"\b(?:technical director|technical manager|project director|project manager|"
    r"av director|av manager|audio visual manager|audiovisual manager|systems engineer|"
    r"video engineer|led engineer|chief technology officer|cto|engineering manager|"
    r"production manager|operations manager)\b|"
    r"기술이사|기술팀장|프로젝트매니저|프로젝트 매니저|엔지니어|영상기술|"
    r"技术总监|技术经理|项目经理|工程经理|视频工程师",
    re.I,
)
_EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
_LINKEDIN_RE = re.compile(r"https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9_.%\-/]+", re.I)
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_SEP_RE = re.compile(r"\s*(?:\||•|·|—|–|\s+-\s+|:)\s*")
_ASCII_NAME_RE = re.compile(r"^[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ'.-]+(?:\s+[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ'.-]+){1,3}$")
_KO_NAME_RE = re.compile(r"^[가-힣]{2,5}$")
_ZH_NAME_RE = re.compile(r"^[\u4e00-\u9fff]{2,4}$")
_PEOPLE_PATH = re.compile(r"/(?:team|people|leadership|management|about|company|contact|staff|조직|임직원|团队|管理)(?:/|$)", re.I)
_GENERIC = {
    "our team", "team", "leadership", "management", "contact", "contact us", "about us",
    "company", "staff", "sales team", "technical team", "procurement", "purchasing",
}


def _clean_label(text: str) -> str:
    text = re.sub(r"^\s*#{1,6}\s*", "", text or "").strip()
    m = _MD_LINK_RE.fullmatch(text)
    if m:
        text = m.group(1).strip()
    text = re.sub(r"[*_`]", "", text).strip(" -–—|:•·\t")
    return re.sub(r"\s+", " ", text)


def _looks_name(value: str) -> bool:
    value = _clean_label(value)
    if not value or value.lower() in _GENERIC or len(value) > 70:
        return False
    if COMMERCIAL_RE.search(value) or PROJECT_RE.search(value) or "@" in value:
        return False
    return bool(_ASCII_NAME_RE.fullmatch(value) or _KO_NAME_RE.fullmatch(value)
                or _ZH_NAME_RE.fullmatch(value))


def _role(line: str) -> tuple[str, str] | None:
    commercial = COMMERCIAL_RE.search(line or "")
    project = PROJECT_RE.search(line or "")
    if commercial and (not project or commercial.start() <= project.start()):
        return "commercial", commercial.group(0)
    if project:
        return "project", project.group(0)
    return None


def _name_from_window(lines: list[str], idx: int) -> str | None:
    # Same-line layouts such as "Jane Smith | Purchasing Manager" are common.
    current = _clean_label(lines[idx])
    for part in _SEP_RE.split(current):
        if _looks_name(part):
            return _clean_label(part)
    # Markdown team pages more often put the person's H2 immediately above the title.
    for pos in range(idx - 1, max(-1, idx - 4), -1):
        candidate = _clean_label(lines[pos])
        if _looks_name(candidate):
            return candidate
    # Less common but still explicit: "Purchasing Manager — Jane Smith".
    for pos in range(idx + 1, min(len(lines), idx + 3)):
        candidate = _clean_label(lines[pos])
        if _looks_name(candidate):
            return candidate
    return None


def _same_company_email(email: str, company_domain: str | None) -> bool:
    if not email or not company_domain:
        return False
    host = email.rsplit("@", 1)[-1].lower().removeprefix("www.")
    domain = company_domain.lower().removeprefix("www.")
    return host == domain or host.endswith("." + domain)


def detect_page(source_url: str, text: str, company_domain: str | None = None) -> list[dict]:
    """Return source-backed named business contacts from one public page."""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for idx, line in enumerate(lines):
        role = _role(line)
        if not role:
            continue
        role_kind, title_hit = role
        name = _name_from_window(lines, idx)
        if not name:
            continue
        key = (name.lower(), role_kind)
        if key in seen:
            continue
        seen.add(key)
        lo, hi = max(0, idx - 2), min(len(lines), idx + 4)
        window = "\n".join(lines[lo:hi])
        emails = _EMAIL_RE.findall(window)
        company_email = next((e.lower() for e in emails if _same_company_email(e, company_domain)), None)
        linkedin = next(iter(_LINKEDIN_RE.findall(window)), None)
        # Sometimes the LinkedIn URL is a markdown target that the plain URL regex sees;
        # normalise a trailing markdown punctuation mark just in case.
        linkedin = linkedin.rstrip("/.,)") if linkedin else None
        confidence = 78
        if company_email:
            confidence += 12
        if linkedin:
            confidence += 7
        if _PEOPLE_PATH.search(urllib.parse.urlparse(source_url).path or ""):
            confidence += 3
        confidence = min(98, confidence)
        evidence = " | ".join(_clean_label(v) for v in lines[lo:hi] if _clean_label(v))[:700]
        out.append({
            "name": name,
            "title": _clean_label(title_hit),
            "email": company_email,
            "linkedin": linkedin,
            "role_kind": role_kind,
            "source_url": source_url,
            "evidence": evidence,
            "confidence": confidence,
        })
    return out


def detect_pages(pages: list[dict], company_domain: str | None = None) -> list[dict]:
    """Merge duplicate people while keeping the strongest public evidence."""
    best: dict[tuple[str, str], dict] = {}
    for page in pages or []:
        url, text = str(page.get("url") or ""), str(page.get("text") or "")
        if not url or not text:
            continue
        for candidate in detect_page(url, text, company_domain=company_domain):
            key = (candidate["name"].lower(), candidate["role_kind"])
            current = best.get(key)
            if current is None or candidate["confidence"] > current["confidence"]:
                best[key] = candidate
    return sorted(best.values(), key=lambda row: (-row["confidence"], row["name"]))

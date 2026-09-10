"""Safe template personalization for outbound messages.

Only known tokens are replaced. Customer-specific fit copy follows the same closed
Rental / Install / General vocabulary used by outbound routing; legacy tags are
canonicalised in app.customer_types before they reach this module.

Greeting policy is centralized here so email and social use exactly the same rule:
Korean customers are addressed by a verified business title only, never by name; other
markets use a verified first name when available. Hooks are also normalized at render
time so old stored "Saw ..." openers do not keep leaking template-like language.
"""
import re

_TOKEN_RE = re.compile(r"\{(name|company|contact|greeting|country|city|hook_ko|hook|fit_ko|fit)\}")
_GAP_RE = re.compile(r"[^\S\n]{2,}")
_BLANK_RUN_RE = re.compile(r"\n{3,}")
_ORPHAN_PUNCT_RE = re.compile(r"[^\S\n]+([,.!?;:])")
_DOUBLED_PUNCT_RE = re.compile(r"[,;:，、]+([.!?。！？])")
_ORPHAN_DASH_RE = re.compile(r"[^\S\n]*[—–-][^\S\n]*(?=[.,!?;:])")
_ORPHAN_HONORIFIC_RE = re.compile(r"[,，][^\S\n]*(?<![\w가-힣])님(?=[\s,.，。!?]|$)")
_TRAILING_SPACE_RE = re.compile(r"[^\S\n]+$", re.M)


# These lines describe what matters to the three commercial segments without creating
# hidden sub-types such as outdoor, reseller or end-user.
_FIT_LINES = {
    "Rental": "built for crews that reload every week, and sized to mix with stock you"
              " already own",
    "Install": "the kind that has to still be supportable and expandable three years"
               " after the install",
    "General": "with a broad LED range that can be narrowed once the application and"
               " screen size are clear",
}

_FIT_LINES_KO = {
    "Rental": "매주 설치·철수를 반복하는 현장을 견디고, 기존 보유 장비와 섞어 쓸 수 있는 캐비닛",
    "Install": "설치 후에도 증설과 A/S를 이어가기 쉬운 제품",
    "General": "용도와 화면 크기에 맞춰 필요한 제품군만 좁혀서 제안할 수 있는 구성",
}


_HOOK_GLOSS_KO = {
    "rental": "렌탈", "screen rental": "스크린 렌탈", "stage rental": "무대 렌탈",
    "AV rental": "AV 렌탈", "leasing": "임대", "staging": "무대 시공",
    "event production": "행사 제작", "events": "행사", "concert": "콘서트",
    "festival": "페스티벌", "touring": "투어",
    "installation": "설치", "panel installation": "패널 설치",
    "screen installation": "스크린 설치", "integration": "통합 시공",
    "AV integration": "AV 통합", "systems integration": "시스템 통합",
    "audiovisual integration": "음향영상 통합", "AV solutions": "AV 솔루션",
    "audio visual": "음향영상", "video systems": "영상 시스템",
    "integrated control": "통합 제어", "structured cabling": "통합 배선",
    "distribution": "유통", "wholesale": "도매", "resale": "판매",
    "dealership": "대리점", "supply": "납품", "LED supply": "LED 납품",
    "LED screen supply": "LED 스크린 납품", "screen sales": "스크린 판매",
    "panel sales": "패널 판매",
    "signage": "사이니지", "LED signage": "LED 전광판", "digital signage": "디지털 사이니지",
    "billboard": "옥외 광고판", "outdoor advertising": "옥외 광고",
    "custom signs": "맞춤 사인", "visual communication": "비주얼 커뮤니케이션",
    "media wall": "미디어월", "LED panels": "LED 패널",
}
_HOOK_PITCH_RE = re.compile(r"^Saw (.+?) panels listed on your site\.$")
_HOOK_WORK_RE = re.compile(
    r"^Saw the (.+?) work(?: you do(?: around (.+?))?)?( on your site)?\.$")
_LEGACY_GENERIC_HOOK = "Saw that your company works with LED displays."
_LEGACY_GENERIC_HOOK_KO = "귀사에서 LED 디스플레이 관련 업무를 하고 계신 것을 봤습니다."


_NOT_A_PERSON = re.compile(
    r"\b(delivery|sales|services?|group|inc|llc|ltd|corp|company|team|support|media|"
    r"productions?|systems?|solutions?|rental|events?|studio|technolog\w*|design|display|"
    r"screens?|led|av|audio|sound|video|lighting|marketing|management|projects?|staff|"
    r"department|office|centers?|centres?|quote|content|markdown|testimonials|"
    r"entertainment|stage|visual|digital|creative|works|world|live|park|nationwide|"
    r"outside|inside|customer|client|general|contact|about|home|welcome|innovation|activit\w*|areas?|history|profile|overview|awards?|mentorship|foundation)\b",
    re.I,
)
_PERSON_TOKEN = re.compile(r"[A-Za-z][A-Za-z'’\-\.]{0,19}")
_KO_ZH_NAME = re.compile(r"^[가-힣]{2,4}$|^[一-鿿]{2,4}$")


def looks_like_a_person(value: str) -> bool:
    name = re.sub(r"\s+", " ", str(value or "")).strip()
    if not name or len(name) > 40:
        return False
    if _KO_ZH_NAME.fullmatch(name):
        return True
    if _NOT_A_PERSON.search(name):
        return False
    tokens = name.split()
    if not 1 <= len(tokens) <= 3:
        return False
    for token in tokens:
        core = token.strip(".")
        if not core or not _PERSON_TOKEN.fullmatch(token) or not core[0].isupper():
            return False
    return True


_KO_TITLES = (
    "대표이사", "대표", "사장", "회장", "부사장", "전무", "상무", "이사",
    "본부장", "부장", "차장", "과장", "대리", "팀장", "실장", "소장", "원장",
)
_EN_TO_KO_TITLE = re.compile(
    r"\b(chief executive officer|ceo|president|owner|founder|co-founder)\b", re.I)


def korean_title(lead: dict) -> str:
    """Return a known Korean business title; never guess a title from a vague role."""
    haystack = " ".join(str(lead.get(field) or "")
                        for field in ("title", "contact_name", "role"))
    for word in _KO_TITLES:
        if word in haystack:
            return "대표" if word == "대표이사" else word
    if _EN_TO_KO_TITLE.search(haystack):
        return "대표"
    return ""


_KOREAN_COUNTRIES = {
    "south korea", "korea", "republic of korea", "korea, republic of", "korea south",
    "kr", "kor", "대한민국", "한국", "韩国", "韓國",
}


def is_korean_customer(lead: dict) -> bool:
    """Country is the authority for Korean address style; never infer it from a name."""
    country = re.sub(r"\s+", " ", str(lead.get("country") or "")).strip().casefold()
    return country in _KOREAN_COUNTRIES


def _safe_contact(lead: dict) -> str:
    contact = str(lead.get("contact_name") or "").strip()
    return contact if contact and looks_like_a_person(contact) else ""


def greeting(lead: dict) -> str:
    """Return the complete first-line greeting for every outbound channel.

    Korea: known title -> 안녕하세요, 부장님. / unknown title -> 안녕하세요.
    Other markets: known person -> Hi John, / unknown person -> Hi,
    """
    if is_korean_customer(lead):
        title = korean_title(lead)
        return f"안녕하세요, {title}님." if title else "안녕하세요."
    contact = _safe_contact(lead)
    return f"Hi {contact.split()[0]}," if contact else "Hi,"


def _generic_hook() -> str:
    from app.backfill_hooks import GENERIC_HOOK
    return GENERIC_HOOK


def _generic_hook_ko() -> str:
    from app.backfill_hooks import GENERIC_HOOK_KO
    return GENERIC_HOOK_KO


def natural_hook(lead: dict) -> str:
    """Make legacy generated hooks read like a human note without changing their facts."""
    hook = str(lead.get("hook") or "").strip() or _generic_hook()
    if hook in {_generic_hook(), _LEGACY_GENERIC_HOOK}:
        return _generic_hook()

    pitch = _HOOK_PITCH_RE.match(hook)
    if pitch:
        pitches = pitch.group(1)
        return f"I noticed {pitches} panels on your website."

    work = _HOOK_WORK_RE.match(hook)
    if work:
        what, where, on_site = work.group(1), work.group(2), work.group(3)
        if where:
            return f"I came across your {what} work around {where}."
        if on_site:
            return f"I was looking through your website and noticed your {what} work."
        return f"I came across your {what} work."

    # Source-specific hooks written by the verified hook writer used to start with the
    # same canned "Saw ..." shape. Keep every fact after that verb, only soften the lead.
    if hook.startswith("Saw "):
        return "I noticed " + hook[4:]
    return hook


def _naturalize_korean_hook(line: str) -> str:
    """Turn the old observational ending into a more natural reason-for-contact line."""
    text = str(line or "").strip()
    if text == _LEGACY_GENERIC_HOOK_KO:
        return _generic_hook_ko()
    if text.endswith("봤습니다."):
        return text[:-len("봤습니다.")] + "보고 연락드렸습니다."
    return text


def hook_ko(lead: dict) -> str:
    """Return a natural Korean version of a verified/generated hook, else empty."""
    stored = (lead.get("hook_ko") or "").strip()
    if stored:
        return _naturalize_korean_hook(stored)
    hook = (lead.get("hook") or "").strip()
    if not hook:
        return ""

    from app.backfill_hooks import GENERIC_HOOK, GENERIC_HOOK_KO

    if hook in {GENERIC_HOOK, _LEGACY_GENERIC_HOOK}:
        return GENERIC_HOOK_KO
    pitch = _HOOK_PITCH_RE.match(hook)
    if pitch:
        pitches = pitch.group(1).replace(" and ", ", ")
        return f"홈페이지에서 {pitches} 패널 라인업을 보고 연락드렸습니다."

    work = _HOOK_WORK_RE.match(hook)
    if not work:
        return ""
    terms = [t.strip() for t in re.split(r",| and ", work.group(1)) if t.strip()]
    korean = [_HOOK_GLOSS_KO.get(term) for term in terms]
    if not korean or any(k is None for k in korean):
        return ""
    where = work.group(2)
    joined = " · ".join(korean)
    if where:
        return f"{where} 지역에서 하시는 {joined} 작업을 보고 연락드렸습니다."
    if work.group(3):
        return f"홈페이지에서 {joined} 작업을 보고 연락드렸습니다."
    return f"{joined} 작업을 하시는 걸 보고 연락드렸습니다."


def _fit_line(lead: dict, table: dict | None = None) -> str:
    """Return one fit line from the canonical three-type customer routing."""
    from app.customer_types import customer_types

    table = table if table is not None else _FIT_LINES
    types = customer_types(lead.get("tags"))
    if not types:
        return ""
    return table.get(types[0], "")


def render(text: str | None, lead: dict) -> str:
    if not text:
        return ""
    company = lead.get("company_en") or ""
    contact = _safe_contact(lead)

    # Keep {contact} backwards compatible for older/manual templates. New outbound copy
    # uses {greeting}, which is the only token that applies the country-aware address rule.
    ko_address = "{contact}님" in text
    values = {
        "name": company,
        "company": company,
        "contact": (korean_title(lead) if ko_address
                    else (contact.split()[0] if contact else "")),
        "greeting": greeting(lead),
        "country": lead.get("country") or "",
        "city": lead.get("city") or "",
        "hook": natural_hook(lead),
        "fit": _fit_line(lead),
        "fit_ko": _fit_line(lead, _FIT_LINES_KO),
        "hook_ko": hook_ko(lead) or _generic_hook_ko(),
    }
    dropped = False

    def _sub(match: re.Match) -> str:
        nonlocal dropped
        value = values[match.group(1)]
        dropped = dropped or not value
        return value

    out = _TOKEN_RE.sub(_sub, text)
    if not dropped:
        return out
    out = _GAP_RE.sub(" ", out)
    out = _ORPHAN_HONORIFIC_RE.sub("", out)
    out = _ORPHAN_DASH_RE.sub("", out)
    out = _ORPHAN_PUNCT_RE.sub(r"\1", out)
    out = _DOUBLED_PUNCT_RE.sub(r"\1", out)
    out = _BLANK_RUN_RE.sub("\n\n", out)
    return _TRAILING_SPACE_RE.sub("", out)

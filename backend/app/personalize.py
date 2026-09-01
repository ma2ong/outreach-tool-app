"""Safe template personalization for outreach messages.

Replaces only the known tokens below; anything else in braces is left intact,
so a stray '{price}' in a template can never crash a send (str.format raised
KeyError). {contact} falls back to 'there' so 'Hi {contact}' always reads fine.

{hook} comes from app.brief and is often empty — plenty of sites publish nothing specific
enough to quote back. It is a whole sentence for exactly that reason: dropping it leaves
the message intact, where a half sentence would go out reading "Saw  on your site."

The brief itself is deliberately not a token. It is written in the third person for Allen
to read ("The site mentions ..."), and a template that sent it would be quoting the
customer's own website back at them.
"""
import re

_TOKEN_RE = re.compile(r"\{(name|company|contact|country|city|hook_ko|hook|fit_ko|fit)\}")
# Closes the gap an empty token leaves behind. Only applied when something did render
# empty, so a template that spaces itself deliberately is left alone.
_GAP_RE = re.compile(r"[^\S\n]{2,}")
# A token alone on its own line leaves an empty paragraph behind. Three blank lines in
# the middle of a letter reads as a template that failed to fill in.
_BLANK_RUN_RE = re.compile(r"\n{3,}")
# "Hi {contact}," with no contact name used to render "Hi there," — a greeting that
# announces a mass send on the majority of leads, which have no contact name. Dropping
# the token instead leaves "Hi ," so the punctuation is pulled back up to the word.
_ORPHAN_PUNCT_RE = re.compile(r"[^\S\n]+([,.!?;:])")
# "we build the panels ourselves, {fit}." with an unknown customer type collapses to
# "ourselves, ." and then, once the space above is eaten, to "ourselves,." — a comma
# holding the place of a clause that is not there. Keep the closing mark, drop the
# one that was only ever a joint.
_DOUBLED_PUNCT_RE = re.compile(r"[,;:，、]+([.!?。！？])")
# "We build LED panels in Shenzhen — {fit}." with no type renders "... Shenzhen —."
# A dash introduces something; with nothing after it, it goes too.
_ORPHAN_DASH_RE = re.compile(r"[^\S\n]*[—–-][^\S\n]*(?=[.,!?;:])")
# Korean attaches the honorific to the name, so "안녕하세요, {contact}님." with no name
# renders "안녕하세요, 님." — an honorific addressed to nobody, which is worse in Korean
# than the missing name it is trying to cover. The whole address drops instead.
# The lookbehind is what keeps "김종수님" intact: only an honorific with no name in
# front of it is an orphan.
_ORPHAN_HONORIFIC_RE = re.compile(r"[,，][^\S\n]*(?<![\w가-힣])님(?=[\s,.，。!?]|$)")
_TRAILING_SPACE_RE = re.compile(r"[^\S\n]+$", re.M)


# What each kind of buyer is actually weighing. A rental company repacks the same panels
# every week and needs them to survive it; an integrator is signing up to support the
# install for years. "We manufacture LED panels" says neither, and every factory in
# Shenzhen can send it (docs/67 R4).
_FIT_LINES = {
    "租赁商": "built for crews that reload every week, and sized to mix with stock you"
              " already own",
    "系统集成商": "the kind that has to still be supportable and expandable three years"
                 " after the install",
    "工程商": "the kind that has to still be supportable and expandable three years"
             " after the install",
    "广告商": "bright enough for daylight and built to run all day outdoors",
    "代理商": "with stock you can quote from and OEM if a client wants their own badge",
    "批发商": "with stock you can quote from and OEM if a client wants their own badge",
    "终端用户": "picked for the room rather than the catalogue",
}

_FIT_LINES_KO = {
    "租赁商": "매주 설치·철수를 반복하는 현장을 견디고, 기존 보유 장비와 섞어 쓸 수 있는 캐비닛",
    "系统集成商": "설치 3년 뒤에도 증설과 A/S가 되는 제품",
    "工程商": "설치 3년 뒤에도 증설과 A/S가 되는 제품",
    "广告商": "주간에도 충분히 밝고 옥외 상시 구동에 맞춘 제품",
    "代理商": "견적 낼 수 있는 재고와 OEM까지 가능한 제품",
    "批发商": "견적 낼 수 있는 재고와 OEM까지 가능한 제품",
    "终端用户": "카탈로그가 아니라 설치 공간에 맞춰 고른 제품",
}


# The stored hook is English because `brief.build` glosses every site term into English
# (see app/brief.py). Inside a Korean letter that reads half-finished, so the sentence is
# turned back into Korean here rather than re-fetching every Korean company's site — it
# is our own generated sentence, in two known shapes, not a translation of theirs.
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
    r"^Saw the (.+?) work(?: you do around (.+?))?(?: on your site)?\.$")


def hook_ko(lead: dict) -> str:
    """The stored English hook, said in Korean. Empty when the shape is unfamiliar.

    Empty is the right answer for anything unrecognised: a half-translated opener is
    worse than none, and the letter closes the gap on its own.
    """
    hook = (lead.get("hook") or "").strip()
    if not hook:
        return ""
    pitch = _HOOK_PITCH_RE.match(hook)
    if pitch:
        # "P1, P2 and P2.5" — the English conjunction has no place in a Korean sentence.
        pitches = pitch.group(1).replace(" and ", ", ")
        return f"홈페이지에서 {pitches} 패널 라인업을 봤습니다."
    work = _HOOK_WORK_RE.match(hook)
    if not work:
        return ""
    terms = [t.strip() for t in re.split(r",| and ", work.group(1)) if t.strip()]
    korean = [_HOOK_GLOSS_KO.get(term) for term in terms]
    if not korean or any(k is None for k in korean):
        return ""      # an unglossed term would leave English inside a Korean sentence
    where = work.group(2)
    joined = " · ".join(korean)
    if where:
        return f"{where} 지역에서 하시는 {joined} 작업을 봤습니다."
    return f"홈페이지에서 {joined} 작업을 봤습니다."


def _fit_line(lead: dict, table: dict | None = None) -> str:
    """One sentence aimed at this kind of buyer, or nothing when we do not know.

    Nothing is the right answer when the type is unknown: the letter reads fine without
    it, and a guessed line addressed to the wrong kind of company is worse than a
    shorter letter.
    """
    from app.customer_types import customer_types

    table = table if table is not None else _FIT_LINES
    for kind in customer_types(lead.get("tags")):
        line = table.get(kind)
        if line:
            return line
    return ""


def render(text: str | None, lead: dict) -> str:
    if not text:
        return ""
    company = lead.get("company_en") or ""
    contact = (lead.get("contact_name") or "").strip()
    values = {
        "name": company,
        "company": company,
        "contact": contact.split()[0] if contact else "",
        "country": lead.get("country") or "",
        "city": lead.get("city") or "",
        "hook": (lead.get("hook") or "").strip(),
        "fit": _fit_line(lead),
        "fit_ko": _fit_line(lead, _FIT_LINES_KO),
        "hook_ko": hook_ko(lead),
    }
    dropped = False

    def _sub(m: re.Match) -> str:
        nonlocal dropped
        value = values[m.group(1)]
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

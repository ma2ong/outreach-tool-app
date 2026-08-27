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

_TOKEN_RE = re.compile(r"\{(name|company|contact|country|city|hook|fit_ko|fit)\}")
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
    "租赁商": "Most of our rental customers care about two things: panels that survive"
              " weekly load-in and out, and boxes that match what they already own so"
              " stock can be mixed on one wall.",
    "系统集成商": "For integration work the questions are usually spec compliance, how"
                 " long the same product stays available for expansion, and who answers"
                 " when something needs support three years in.",
    "工程商": "For project work the questions are usually spec compliance, how long the"
             " same product stays available for expansion, and who answers when"
             " something needs support three years in.",
    "广告商": "For signage the deciding factors are usually daylight brightness, power"
             " draw over years of continuous run, and how the cabinet handles weather.",
    "代理商": "If you resell, what usually matters is stock you can quote from, margin"
             " that holds, and OEM options when a client wants their own badge.",
    "批发商": "If you resell, what usually matters is stock you can quote from, margin"
             " that holds, and OEM options when a client wants their own badge.",
    "终端用户": "For a screen you will own and run yourself, the questions worth asking"
               " early are brightness for the room, service access, and what spare"
               " parts cost later.",
}


# The same lines in Korean. A separate token rather than a language guess: the template
# author knows which language the letter is in, and render() has no way to find out.
_FIT_LINES_KO = {
    "租赁商": "렌탈 업체에서는 보통 두 가지를 보십니다. 매주 반복되는 설치·철수를 견디는"
              " 내구성, 그리고 기존 보유 장비와 한 화면에 섞어 쓸 수 있는 캐비닛인지입니다.",
    "系统集成商": "시공·통합 프로젝트에서는 사양 충족 여부, 증설 시 같은 제품을 계속 구할 수"
                 " 있는지, 그리고 3년 뒤 문제가 생겼을 때 누가 대응하는지가 관건입니다.",
    "工程商": "시공 프로젝트에서는 사양 충족 여부, 증설 시 같은 제품을 계속 구할 수 있는지,"
             " 그리고 3년 뒤 문제가 생겼을 때 누가 대응하는지가 관건입니다.",
    "广告商": "옥외 광고용으로는 주간 밝기, 장시간 연속 구동 시의 소비전력, 그리고 캐비닛의"
             " 방수·방진 성능이 결정적입니다.",
    "代理商": "유통을 하신다면 견적 낼 수 있는 재고, 유지되는 마진, 그리고 고객사 브랜드를"
             " 붙일 수 있는 OEM 가능 여부가 중요합니다.",
    "批发商": "유통을 하신다면 견적 낼 수 있는 재고, 유지되는 마진, 그리고 고객사 브랜드를"
             " 붙일 수 있는 OEM 가능 여부가 중요합니다.",
    "终端用户": "직접 운영하실 화면이라면 설치 공간의 밝기, 유지보수 접근성, 그리고 나중에"
               " 예비 부품 비용이 얼마인지를 먼저 확인하시는 편이 좋습니다.",
}


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
    out = _ORPHAN_PUNCT_RE.sub(r"\1", out)
    out = _BLANK_RUN_RE.sub("\n\n", out)
    return _TRAILING_SPACE_RE.sub("", out)

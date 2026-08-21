"""Conservative buying-signal detection over public company-page text.

This module does no network access and creates no CRM rows. It only turns evidence that
has already been fetched into source-backed candidates. Noisy words such as "project"
or "event" are deliberately insufficient on their own.
"""
from __future__ import annotations

import re


_WS = re.compile(r"\s+")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?。！？])\s+|\n+")

_TENDER = re.compile(
    r"\b(?:rfp|rfq|request for proposals?|request for quotations?|invitation to bid|"
    r"call for tenders?|tender notice|procurement notice)\b|"
    r"입찰(?:공고)?|조달(?:공고)?|견적\s*요청|제안\s*요청|"
    r"招标(?:公告)?|投标|采购公告|询价公告",
    re.I,
)

_PROJECT_ACTION = re.compile(
    r"\b(?:opening|opens?|opened|launch(?:ing|ed)?|expand(?:ing|ed)?|expansion|"
    r"renovat(?:e|ing|ed|ion)|relocat(?:e|ing|ed|ion)|new\s+(?:facility|location|studio|"
    r"venue|store|showroom|arena|campus|office|control room|broadcast studio)|"
    r"breaks? ground|under construction)\b|"
    r"신규\s*(?:오픈|개장|개소)|확장|증설|리뉴얼|이전\s*오픈|"
    r"新(?:开|建|增|扩)|开业|扩建|扩张|装修升级|搬迁",
    re.I,
)
_PROJECT_PLACE = re.compile(
    r"\b(?:studio|venue|event space|store|showroom|arena|stadium|campus|facility|"
    r"office|control room|broadcast studio|retail location|mall|shopping center|"
    r"shopping centre|church|worship center|worship centre|theatre|theater|cinema|"
    r"hotel|conference center|conference centre)\b|"
    r"스튜디오|공연장|행사장|매장|쇼룸|경기장|캠퍼스|시설|사무실|컨트롤룸|방송국|"
    r"演播室|摄影棚|场馆|门店|展厅|体育馆|商场|控制室|会议中心",
    re.I,
)

_HIRING = re.compile(
    r"\b(?:we(?:'re| are) hiring|now hiring|join our team|careers?|job openings?|"
    r"vacanc(?:y|ies)|recruit(?:ing|ment)?)\b|채용|구인|인재\s*모집|招聘|诚聘|招贤纳士",
    re.I,
)
_HIRING_ROLE = re.compile(
    r"\b(?:audio\s*visual|a/?v|video engineer|led technician|display technician|"
    r"event technician|production manager|technical director|broadcast engineer|"
    r"systems? engineer|integration engineer|project manager|video technician|"
    r"event production|av technician)\b|"
    r"영상|AV\s*엔지니어|기술\s*(?:담당|엔지니어)|프로덕션|프로젝트\s*매니저|"
    r"音视频|AV工程师|视频工程师|技术总监|项目经理|活动技术",
    re.I,
)

_EXPO = re.compile(
    r"\b(?:expo|exhibition|trade show|infocomm|integrated systems europe|\bise\b|"
    r"nab show|livedesign|live design international|ldiw?)\b|전시회|박람회|엑스포|展会|展览会|博览会",
    re.I,
)
_EXPO_PARTICIPATION = re.compile(
    r"\b(?:booth|stand\s*[a-z0-9-]*|exhibit(?:ing|or)?|visit us|meet us|see us|"
    r"find us|hall\s*\d)\b|부스|참가|출展|参展|展位|莅临",
    re.I,
)

_DISTRIBUTOR = re.compile(
    r"\b(?:become (?:a|our) (?:distributor|dealer|reseller)|looking for (?:new )?"
    r"(?:distributors|dealers|resellers)|seeking (?:distributors|dealers|partners)|"
    r"(?:distributor|dealer|reseller)s? wanted|join our (?:dealer|distributor|partner) network|"
    r"partner with us)\b|대리점\s*모집|총판\s*모집|파트너\s*모집|"
    r"招募(?:代理|经销商)|寻找(?:经销商|代理商)|诚招代理|经销商招募",
    re.I,
)


def _clean(text: str) -> str:
    return _WS.sub(" ", text or "").strip()


def _window(text: str, match: re.Match, radius: int = 240) -> str:
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    return _clean(text[start:end])[:650]


def _headline(label: str, excerpt: str) -> str:
    """Use the evidence sentence in the title so changed public evidence can be distinct."""
    pieces = [p.strip(" -–—|:;") for p in _SENTENCE_BREAK.split(excerpt) if p.strip()]
    detail = min(pieces, key=len) if pieces else excerpt
    detail = _clean(detail)[:120]
    return f"{label}：{detail}"[:240]


def _use_case(text: str) -> str | None:
    low = text.lower()
    if re.search(r"\b(?:xr|virtual production)\b|가상\s*제작|虚拟制作", low, re.I):
        return "Virtual Production"
    if re.search(r"\b(?:broadcast|tv studio|television studio)\b|방송|演播", low, re.I):
        return "Broadcast"
    if re.search(r"\b(?:rental|event production|live events?)\b|렌탈|행사|租赁|活动", low, re.I):
        return "Rental"
    if re.search(r"\b(?:stadium|arena|sports?)\b|경기장|体育馆|球场", low, re.I):
        return "Sports"
    if re.search(r"\b(?:control room|command center|command centre)\b|컨트롤룸|控制室", low, re.I):
        return "Control Room"
    if re.search(r"\b(?:church|worship)\b|교회|예배|教会", low, re.I):
        return "Church"
    if re.search(r"\b(?:store|retail|mall|showroom)\b|매장|쇼룸|门店|商场|展厅", low, re.I):
        return "Retail"
    if re.search(r"\b(?:dooh|billboard|outdoor advertising)\b|옥외광고|户外广告", low, re.I):
        return "DOOH"
    return None


def _candidate(signal_type: str, label: str, source_url: str, excerpt: str,
               confidence: int, suggested_angle: str) -> dict:
    return {
        "signal_type": signal_type,
        "headline": _headline(label, excerpt),
        "evidence": excerpt[:2000],
        "source_url": source_url,
        "occurred_at": None,
        "confidence": confidence,
        "use_case": _use_case(excerpt),
        "product_fit": "LED display / video wall / digital signage",
        "suggested_angle": suggested_angle,
    }


def _nearby_pair(text: str, first: re.Pattern, second: re.Pattern,
                 radius: int = 320) -> tuple[re.Match, str] | None:
    """Require both ideas in one local passage, not merely somewhere on a long page."""
    for match in first.finditer(text):
        excerpt = _window(text, match, radius)
        if second.search(excerpt):
            return match, excerpt
    return None


def detect_page(source_url: str, text: str) -> list[dict]:
    """Detect conservative signal candidates on one already-fetched public page."""
    if not source_url or not text:
        return []
    out: list[dict] = []

    tender = _TENDER.search(text)
    if tender:
        excerpt = _window(text, tender)
        out.append(_candidate(
            "tender", "公开采购 / RFQ", source_url, excerpt, 85,
            "核实公开采购/RFQ是否包含 LED 显示、视频墙或数字标牌需求，并确认参与窗口。"))

    project = _nearby_pair(text, _PROJECT_ACTION, _PROJECT_PLACE)
    if project:
        _, excerpt = project
        out.append(_candidate(
            "project", "新建 / 扩建项目", source_url, excerpt, 70,
            "围绕新建、扩建或翻新项目确认是否有 LED 显示、视频墙或数字标牌需求。"))

    hiring = _nearby_pair(text, _HIRING, _HIRING_ROLE)
    if hiring:
        _, excerpt = hiring
        out.append(_candidate(
            "hiring", "AV / 技术岗位招聘", source_url, excerpt, 65,
            "技术/AV 团队扩张可能对应项目量上升，可确认近期 LED 项目和供应商需求。"))

    expo = _nearby_pair(text, _EXPO, _EXPO_PARTICIPATION)
    if expo:
        _, excerpt = expo
        out.append(_candidate(
            "exhibition", "展会参展", source_url, excerpt, 65,
            "结合展会节点确认展台 LED、活动显示、租赁库存或现场视频需求。"))

    distributor = _DISTRIBUTOR.search(text)
    if distributor:
        excerpt = _window(text, distributor)
        out.append(_candidate(
            "distributor", "渠道 / 经销商拓展", source_url, excerpt, 70,
            "确认其渠道拓展计划，以及是否需要新的 LED 产品供应商、OEM/ODM 或项目支持。"))

    # One page can legitimately contain two different signals; only collapse exact
    # type/headline repeats caused by repeated navigation/footer text.
    seen = set()
    unique = []
    for item in out:
        key = (item["signal_type"], item["headline"].lower(), item["source_url"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def detect_pages(pages: list[dict]) -> list[dict]:
    out = []
    seen = set()
    for page in pages:
        for item in detect_page(str(page.get("url") or ""), str(page.get("text") or "")):
            key = (item["signal_type"], item["headline"].lower(), item["source_url"].lower())
            if key not in seen:
                seen.add(key)
                out.append(item)
    return out

"""The last check a cold email passes before it leaves.

The guard judges the rendered text, not the stored template. It never rewrites copy to
make it pass: a hold is visible and the caller decides what to change.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

GUARDED_CHANNELS = ("email",)

# Narrow on purpose. Technical outreach is full of legitimate numbers (P2.5, 200 sqm,
# years and phone numbers). Currency beside a number is an actual commercial number and
# belongs to Allen, not a cold-email automation.
_PRICE = re.compile(
    r"(?:[$€£¥₩]\s?\d[\d,.]*)"
    r"|(?:\b(?:usd|eur|gbp|rmb|cny|jpy|krw|brl|mxn|clp|cop|pen)\s?\d[\d,.]*)"
    r"|(?:\b\d[\d,.]*\s?(?:usd|eur|gbp|rmb|cny|jpy|krw|brl|mxn|clp|cop|pen)\b)"
    r"|(?:\d[\d,.]*\s?(?:元|美金|美元|块))",
    re.I,
)

# docs/82 R1. Sentences that hand the recipient the "don't reply" option, in our own
# words. Allen banned the whole shape after reading one go out:
#
#     If ours won't mix with your stock I'll say so and leave it there.
#
# His reasoning is the right one: a cold email from an unknown Shenzhen factory puts the
# reader under no pressure at all, so offering a way out of a pressure that does not
# exist only says the quiet part for them. Four years and 3,031 letters in his own hand
# contain none of this — docs/82 records what they contain instead.
#
# This sits beside the pricing rule rather than only in the seed copy, because copy is
# rows in a database and can be edited from the UI; the rule has to live on the send path.
_EXIT_LINE = re.compile(
    r"leave it there"
    r"|i'?ll (?:say so and )?(?:stop|leave)(?: here| it there| you (?:alone|be))?"
    # "following up on my last message" means the previous one, not the final one, and
    # the first version of this refused two perfectly good follow-up templates for it.
    # Only the farewell sense is banned, so the announcement has to be present: either
    # the sentence opens on it, or something says the sender is signing off.
    r"|(?:^|[.!?]\s+|\n)\s*(?:one\s+)?last (?:note|email|message)\b"
    r"|(?:this|here) is my (?:very )?last"
    r"|last (?:note|email|message) (?:from me|i'?ll send|you'?ll (?:get|hear))"
    r"|won'?t (?:contact|bother|email|write to) you again"
    r"|(?:that'?s|that is) a fine answer"
    r"|fill up your inbox"
    r"|worth your time"
    r"|sorry to (?:bother|disturb|trouble)"
    r"|feel free to ignore"
    r"|no (?:hard feelings|worries) if"
    # Reassuring them that not needing us is fine. Same family as the farewell: it
    # answers "should I reply?" on the reader's behalf, and the answer it gives is no.
    # Anchored on what is being negated — need, interest, fit, plan — rather than on the
    # polite phrase, so "Shipping to Brazil? No problem at all." and "if the pitch isn't
    # right we can change it" are both still sentences we may write.
    r"|\bif\b[^.!?\n]{0,60}\b(?:aren'?t|isn'?t|are not|is not|don'?t|do not|not|no"
    r"|none|nothing|neither|never)\b"
    r"[^.!?\n]{0,40}(?:on your (?:plan|radar)|a fit|of interest|interested|needed"
    r"|need (?:it|them|this|led|displays|panels)|for you|useful|relevant|the right time)"
    r"[^.!?\n]{0,40}\b(?:no problem|no worries|not a problem|perfectly fine|fine by me"
    r"|(?:that'?s|that is|it'?s|it is) (?:totally |perfectly |completely |quite )?"
    r"(?:fine|ok|okay|alright))"
    r"|no need to (?:reply|respond|answer|get back)"
    r"|(?:필요|관심)[^.!?\n]{0,24}않(?:으셔도|아도|더라도|으시면)[^.!?\n]{0,12}"
    r"(?:괜찮|무방|상관없|부담)"
    r"|답장[^.!?\n]{0,10}안 ?(?:하셔도|주셔도)[^.!?\n]{0,10}(?:괜찮|무방|됩니다)"
    r"|不(?:需要|感兴趣)[^。！？\n]{0,10}也?没关系"
    r"|더 연락(?:드리지|하지) ?않겠"
    r"|마지막 (?:메일|메시지)"
    r"|그것으로 충분한 답변"
    r"|귀찮게"
    r"|불편하시면"
    r"|시간을 뺏"
    r"|不再(?:打扰|联系)"
    r"|最后一封",
    re.I)


_WORD = re.compile(r"[a-z0-9]+")
_GENERIC_NAME_WORDS = {
    "led", "display", "displays", "screen", "screens", "visual", "video", "wall",
    "walls", "av", "audio", "media", "systems", "system", "group", "inc", "llc",
    "ltd", "co", "company", "solutions", "productions", "rentals", "rental", "the",
    "and",
}


@dataclass(frozen=True)
class Verdict:
    blocked: bool
    reason: str = ""
    detail: str = ""


def _distinctive_terms(lead: dict) -> list[str]:
    """Words that plausibly tie the rendered opening to this particular lead."""
    terms: list[str] = []
    terms.extend(
        word
        for word in _WORD.findall(str(lead.get("company_en") or "").lower())
        if word not in _GENERIC_NAME_WORDS
    )
    host = str(lead.get("website") or "").lower()
    host = re.sub(r"^https?://|^www\.", "", host).split("/")[0].split(".")[0]
    if len(host) > 2 and host not in _GENERIC_NAME_WORDS:
        terms.append(host)
    for field in ("city", "hook"):
        value = str(lead.get(field) or "").strip()
        if not value:
            continue
        terms.extend(
            word for word in _WORD.findall(value.lower())
            if len(word) > 3 and word not in _GENERIC_NAME_WORDS
        )
    # Preserve order for useful error messages while deduping.
    return list(dict.fromkeys(terms))


def can_be_addressed(lead: dict) -> bool:
    """Whether a first cold letter to this lead could pass `check` at all.

    Callers that build a queue use this to leave out records the guard would refuse
    anyway. Enrolling them regardless does not send more mail — it parks them in
    `quality_hold` and quietly shortens the day, which is the failure docs/67 found
    110 follow-ups sitting in.
    """
    name = str(lead.get("company_en") or "").strip()
    # A row whose company name is somebody's mailbox cannot be written to by name.
    if not name or "@" in name:
        return False
    return bool(_distinctive_terms(lead))


def check(body: str, lead: dict, *, subject: str = "", channel: str = "email",
          step_order: int = 0) -> Verdict:
    """Judge exactly the subject/body that would be handed to the sender."""
    text = f"{subject}\n{body}"
    price = _PRICE.search(text)
    if price:
        return Verdict(
            True,
            "pricing",
            f"最终文本里出现价格「{price.group(0).strip()}」——冷邮件自动化不能代替 Allen 定价",
        )
    # Every channel, every language, no override (docs/82 R1).
    exit_line = _EXIT_LINE.search(text)
    if exit_line:
        return Verdict(
            True,
            "exit_line",
            f"最终文本里出现退出语「{exit_line.group(0).strip()}」——"
            "不许主动提出不再联系、声明这是最后一封、或替对方把「没需求」说成好答案（docs/82）",
        )
    if channel not in GUARDED_CHANNELS or step_order > 0:
        return Verdict(False)

    written = set(_WORD.findall(text.lower()))
    terms = _distinctive_terms(lead)
    if written.intersection(terms):
        return Verdict(False)

    # A Korean letter says the hook in Korean, so none of the English terms above can
    # appear in it and this check could never pass — it only ever did because the
    # company name was in the subject line, which Allen has now taken out of both the
    # subject and the body. The translated hook is the same evidence in the other
    # language: it is written from this lead's own hook and from nothing else.
    from app.personalize import hook_ko

    ko = hook_ko(lead).strip()
    if ko and ko in text:
        return Verdict(False)

    # docs/85 R4. A lead whose stored hook is the generic one is a lead we looked at and
    # found nothing quotable about, and Allen has decided those still get written to —
    # 没有开场白不是不写的理由 (docs/80 R2). The test is the stored hook, not the text: a
    # letter cannot pass by containing the sentence, only by belonging to a company we
    # deliberately marked. A lead with no hook at all is still refused.
    from app.backfill_hooks import GENERIC_HOOK

    if str(lead.get("hook") or "").strip() == GENERIC_HOOK:
        return Verdict(False)

    company = lead.get("company_en") or f"#{lead.get('no')}"
    if terms:
        return Verdict(
            True,
            "impersonal",
            f"首封最终文本没有可识别的 {company} 个性化信息（可用线索：{terms[0]}）",
        )
    return Verdict(
        True,
        "impersonal",
        f"{company} 没有可验证的个性化线索；先补公司/官网 hook/城市信息再发",
    )

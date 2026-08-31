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

# docs/82 R6. Accommodating phrases, banned outright rather than only in the "you don't
# have to reply" sense. An earlier version let "Shipping to Brazil? No problem at all"
# through on the grounds that it was about capability; Allen's judgement — 这两句也很垃圾
# 不能放 — is the better one. "No problem" answers a complaint nobody made and puts us in
# the position of accommodating rather than being able. The sentence that says the same
# thing from strength is shorter: "We ship to Brazil weekly."
_HEDGING = re.compile(
    r"\bno problem\b"
    r"|\bnot a problem\b"
    r"|\bno worries\b"
    r"|(?:that'?s|that is|it'?s|it is) (?:totally |perfectly |completely |quite )?"
    r"(?:fine|ok|okay|alright)\b"
    r"|\bfine by me\b"
    r"|\bhappy to accommodate\b"
    r"|괜찮습니다"
    r"|문제 ?없습니다"
    r"|상관없습니다"
    r"|没关系"
    r"|没问题",
    re.I)

# docs/82 R4. Insisting we make it ourselves defends against a doubt the reader has not
# raised. His own letters state the identity and move on: 심천 LED 전광판 업체
# 맥스컬러입니다 / This is Allen from Shenzhen Maxcolor.
_SELF_MADE = re.compile(
    r"\bourselves\b"
    r"|\bour own factory\b"
    r"|\bin-?house factory\b"
    r"|\bwe (?:build|make|manufacture|produce) (?:the |them |it |these )?"
    r"(?:panels |displays |screens )?(?:ourselves|in our own)"
    r"|rather than from a trader"
    r"|not a trader"
    r"|자체 ?공장"
    r"|직접 (?:만듭|만들|생산|제조)"
    r"|무역상[^.!?\n]{0,12}(?:거치지|아닌)"
    r"|自己(?:生产|制造|工厂)",
    re.I)

# docs/82 R5. An imperative that asks the stranger to produce information, paired with
# what we will do in return, is a trade proposed before they agreed to trade. His close
# reports availability and leaves the move to them: 관심하신 제품 있으시면 연락주세요~
_INSTRUCTION = re.compile(
    r"(?:^|[.!?]\s+|\n)\s*"
    r"(?:just )?(?:tell|send|give|reply to|get back to|forward|share with) me\b"
    r"|(?:^|[.!?]\s+|\n)\s*(?:just )?(?:let me know|reply with|send over|send through)\b"
    r"[^.!?\n]{0,60}\band (?:i'?ll|i will|you'?ll|you will)\b"
    r"|(?:^|[.!?]\s+|\n)\s*(?:please )?(?:confirm|provide|specify) ",
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


# docs/82 R7. Allen: 邮件主题永远不要出现公司名…不然别人一看你的名字就不会看了。直接从
# 名字就能够判断出这个邮件值不值得看。
#
# Both names are out, for opposite reasons. Ours is unknown to the reader and reads as a
# supplier pitch before the subject has said anything. Theirs, sitting at the front of a
# subject line, is the signature of mail merge — nobody types a customer's own name into
# a subject except a machine. What is left has to earn the open on content alone, which
# is what his own subjects do: 전후면 유지보수 OK! R3 렌탈형 제품 만나보세요.
_OUR_BRAND = re.compile(r"maxcolor|맥스컬러|迈彩", re.I)


def _company_in_subject(subject: str, lead: dict) -> str:
    """The company name found in a subject line, or "" — ours or theirs."""
    line = str(subject or "").strip()
    if not line:
        return ""
    ours = _OUR_BRAND.search(line)
    if ours:
        return ours.group(0)
    written = set(_WORD.findall(line.lower()))
    for word in _WORD.findall(str(lead.get("company_en") or "").lower()):
        if len(word) > 3 and word not in _GENERIC_NAME_WORDS and word in written:
            return word
    return ""


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
    hedge = _HEDGING.search(text)
    if hedge:
        return Verdict(
            True,
            "hedging",
            f"最终文本里出现迎合语「{hedge.group(0).strip()}」——"
            "「没问题/没关系」是在回答一个没人提出的抱怨，把我们放在让步的位置。"
            "直接说能力：把「Shipping to Brazil? No problem at all」写成"
            "「We ship to Brazil weekly」（docs/82 R6）",
        )
    self_made = _SELF_MADE.search(text)
    if self_made:
        return Verdict(
            True,
            "self_made",
            f"最终文本里强调了自己制造「{self_made.group(0).strip()}」——"
            "报身份就够了（an LED display manufacturer in Shenzhen / "
            "심천 LED 디스플레이 제조업체），强调是在替一个没人提出的质疑辩护（docs/82 R4）",
        )
    named = _company_in_subject(subject, lead)
    if named:
        return Verdict(
            True,
            "subject_names_a_company",
            f"主题里出现了公司名「{named}」——主题要靠自己的内容换来打开，"
            "对方看到一个不认识的供应商名字就删了，看到自己的公司名则像群发。"
            "写成一个产品加它最硬的那个参数（docs/82 R7）",
        )
    instruction = _INSTRUCTION.search(text)
    if instruction:
        return Verdict(
            True,
            "instruction",
            f"最终文本里在给对方派活「{instruction.group(0).strip()}」——"
            "收尾要说我们这边能提供什么，动作留给对方自己决定，"
            "不要在对方还没同意做生意之前先要求他给信息（docs/82 R5）",
        )
    if channel not in GUARDED_CHANNELS or step_order > 0:
        return Verdict(False)

    written = set(_WORD.findall(text.lower()))
    terms = _distinctive_terms(lead)
    if written.intersection(terms):
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

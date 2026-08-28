"""Read a few social profiles a day, for two answers at once (docs/71).

Allen corrected an earlier assumption of mine, and that correction is the whole reason
this exists:

    大家的官网说实话都不怎么维护的……当然也可以去观察对方的 ins、fb 等社媒的发布，
    某个负责人的电话、邮箱、职位的变化，最近的案例等应该会有很多变化

He is right. An LED rental company's website can go three years without an edit while its
Instagram still has last week's show on it. What changes, changes there.

Reading a public profile is far lighter than sending a DM — it is content anyone can see.
But reading a lot of them quickly is the classic shape of a bot, and docs/53 already
established what an Instagram ban costs: it does not come back, and the WhatsApp number
carries WeChat and every customer contact. So every limit below is about keeping the
account, not about manners.

One visit answers two questions, because visits are the scarce resource here: is this
company worth developing, and what has this customer been doing lately.
"""
from __future__ import annotations

import datetime as dt
import random
import re
import time

from app import relationship_events, settings

# docs/71 R1. Twenty a day is 600 a month — already more than Allen could read by hand
# in a year. More would not find customers faster, only lose the account faster.
DAILY_LIMIT = 20
GAP_SECONDS = (40, 90)

_K_DATE = "social_watch_date"
_K_COUNT = "social_watch_count"
_K_FAILED = "social_watch_failed"

# Following is a write action, and platforms tolerate those far less than reads: a burst
# of follows is one of the oldest ban signatures there is. Ten a day is 300 a month,
# already more than Allen follows by hand (docs/72 R2).
FOLLOW_LIMIT = 10
_K_FOLLOWS = "social_follow_count"
_K_FOLLOW_BLOCKED = "social_follow_blocked_date"

# What a bio has to say before this account is worth a follow and a message. Half of it
# is not enough: following an unrelated account also makes this account's following list
# look less like a person in the LED trade, which is one of the things platforms read.
_ICP_WORDS = (
    "led wall", "led walls", "led screen", "led display", "video wall", "videowall",
    "led panel", "digital signage", "av production", "event production",
    "event technology", "stage", "rental", "전광판", "led 디스플레이", "렌탈",
    "pantalla led", "painel de led", "locação",
)

# What a post is worth stopping on. These are the words that mean "there is work
# happening", in the languages his market writes in.
_SIGNALS: dict[str, tuple[str, ...]] = {
    "项目": ("install", "installed", "installation", "project", "delivered",
             "완료", "시공", "설치", "납품", "instalación", "instalação", "projeto"),
    "活动": ("event", "concert", "festival", "stage", "tour", "show",
             "행사", "공연", "무대", "evento", "espetáculo"),
    "展会": ("booth", "expo", "exhibition", "trade show", "infocomm", "ise",
             "부스", "전시회", "박람회", "feria"),
    "招聘": ("hiring", "we're hiring", "join our team", "채용", "구인", "vaga"),
    "新设备": ("new screen", "new panels", "new led", "upgraded", "신규 도입",
               "novo painel"),
}

# Contact details published on a profile: the reason to read one even when nothing else
# is new (docs/71 R4).
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\+?\d[\d\s().-]{7,17}\d")
# A bio writes its website bare — "electriceventsdc.com", no scheme — so the scheme has
# to be optional. But a loose pattern then reads "20+ Years of D.C." as a domain, so the
# ending is checked against real TLDs rather than "two or more letters".
_TLD = (r"com|net|org|io|co|biz|info|tv|us|ca|au|nz|uk|de|fr|it|es|cz|pl|se|nl|br|mx|"
        r"ar|cl|pe|co|kr|jp|cn|in|ph|vn|th|my|sg|ae|za|ru|tr|gr|pt|ie|fi|no|dk")
_SITE = re.compile(
    r"(?<![@\w.])(?!(?:www\.)?(?:instagram|facebook|fb|linkedin|youtube|tiktok)\.)"
    rf"((?:[a-z0-9][a-z0-9-]*\.)+(?:{_TLD})(?:\.(?:{_TLD}))?)(?![a-z0-9])",
    re.I)


def _today() -> str:
    return dt.date.today().isoformat()


def _used_today(conn) -> int:
    if settings.get(conn, _K_DATE) != _today():
        return 0
    try:
        return int(settings.get(conn, _K_COUNT) or 0)
    except ValueError:
        return 0


def remaining(conn) -> int:
    return max(0, DAILY_LIMIT - _used_today(conn))


def _spend(conn, n: int = 1) -> None:
    settings.set_value(conn, _K_DATE, _today())
    settings.set_value(conn, _K_COUNT, str(_used_today(conn) + n))


def failed_today(conn) -> set[str]:
    """Handles that already refused us today; docs/71 R6 says do not ask again."""
    if settings.get(conn, _K_DATE) != _today():
        return set()
    return {h for h in (settings.get(conn, _K_FAILED) or "").split(",") if h}


def _note_failure(conn, handle: str) -> None:
    failed = failed_today(conn) | {handle}
    settings.set_value(conn, _K_DATE, _today())
    settings.set_value(conn, _K_FAILED, ",".join(sorted(failed)))


def sending_pending(conn) -> int:
    """Messages still queued for today.

    The engine is single-threaded, so watching would queue behind sending anyway — but
    the real reason is that one account both messaging strangers and browsing strangers
    in the same minute is the most machine-like pattern there is (docs/71 R2).
    """
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM social_dm_queue WHERE queue_date=? AND status='ready'",
            (_today(),)).fetchone()[0]
    except Exception:  # noqa: BLE001 — schema may not exist yet
        return 0


def read_signals(text: str) -> list[dict]:
    """What this profile says it has been doing."""
    low = (text or "").lower()
    found = []
    for label, words in _SIGNALS.items():
        for word in words:
            if word in low:
                # Quote the surrounding sentence: a claim with no quotable source is
                # one Allen cannot safely repeat in an email (docs/71 R5).
                at = low.index(word)
                excerpt = " ".join(text[max(0, at - 90):at + 120].split())
                found.append({"kind": label, "word": word, "excerpt": excerpt})
                break
    return found


def read_contacts(text: str) -> dict:
    """Contact details a profile publishes about itself."""
    out: dict[str, str] = {}
    email = _EMAIL.search(text or "")
    if email:
        out["email"] = email.group(0)
    site = _SITE.search(text or "")
    if site:
        out["website"] = site.group(1).lower()
    phone = _PHONE.search(text or "")
    if phone:
        digits = re.sub(r"\D", "", phone.group(0))
        if 9 <= len(digits) <= 15:
            out["phone"] = phone.group(0).strip()
    return out


def follows_left(conn) -> int:
    if settings.get(conn, _K_FOLLOW_BLOCKED) == _today():
        return 0        # the platform refused once today; docs/72 R2 says stop
    if settings.get(conn, _K_DATE) != _today():
        return FOLLOW_LIMIT
    try:
        return max(0, FOLLOW_LIMIT - int(settings.get(conn, _K_FOLLOWS) or 0))
    except ValueError:
        return FOLLOW_LIMIT


def looks_like_a_customer(text: str) -> tuple[bool, str]:
    """(worth following, why not).

    Two things must be true: the bio says what they do, and something in it can be
    checked — a site, an address, a number. A bio that only says "LED" could be anyone,
    including a competitor's marketing account, and following it costs more than the
    wasted slot (docs/72 R3).
    """
    low = (text or "").lower()
    word = next((w for w in _ICP_WORDS if w in low), None)
    if not word:
        return False, "简介里看不出是做 LED 这一行的"
    contacts = read_contacts(text)
    if not contacts:
        return False, "简介里没有官网/邮箱/电话，无从验证"
    return True, ""


def due_profiles(conn, limit: int = DAILY_LIMIT) -> list[dict]:
    """Customers with a handle we have not looked at recently.

    Oldest first, and never one we already failed on today.
    """
    rows = conn.execute(
        "SELECT no, company_en, instagram, facebook, tags FROM leads"
        " WHERE COALESCE(do_not_contact, 0) = 0"
        "   AND (COALESCE(instagram,'') <> '' OR COALESCE(facebook,'') <> '')"
        " ORDER BY COALESCE(updated_at, created_at) ASC LIMIT ?", (limit * 4,)).fetchall()
    skip = failed_today(conn)
    out = []
    for row in rows:
        handle = (row["instagram"] or "").strip().lstrip("@")
        channel = "instagram"
        if not handle:
            handle, channel = (row["facebook"] or "").strip(), "facebook"
        if not handle or handle in skip:
            continue
        out.append({"lead_no": row["no"], "company": row["company_en"],
                    "channel": channel, "handle": handle})
        if len(out) >= limit:
            break
    return out


def watch(conn, engine, limit: int | None = None,
          sleeper=time.sleep) -> dict:
    """Read today's allowance of profiles and record what they said."""
    pending = sending_pending(conn)
    if pending:
        return {"looked": 0, "skipped": f"今天还有 {pending} 条私信没发，先不浏览",
                "facts": 0, "failures": 0}

    budget = min(limit or DAILY_LIMIT, remaining(conn))
    if budget <= 0:
        return {"looked": 0, "skipped": "今天的浏览额度用完了", "facts": 0,
                "failures": 0}

    targets = due_profiles(conn, budget)
    looked = facts = failures = followed = 0
    for i, target in enumerate(targets):
        try:
            profile = engine.read_profile(target["channel"], target["handle"])
        except Exception as exc:  # noqa: BLE001 — one profile, not the run
            _note_failure(conn, target["handle"])
            _spend(conn)
            failures += 1
            relationship_events.record(
                conn, target["lead_no"], "fact",
                f"{target['channel']} 主页看不了：{str(exc)[:60]}",
                source="agent", channel=target["channel"])
            continue

        _spend(conn)
        looked += 1
        facts += _record(conn, target, profile)
        outcome = follow_if_worth_it(conn, engine, target, profile)
        if outcome == "已关注":
            followed += 1
        if i + 1 < len(targets):
            sleeper(random.randint(*GAP_SECONDS))
    return {"looked": looked, "facts": facts, "failures": failures,
            "followed": followed, "skipped": ""}


def _spend_follow(conn) -> None:
    settings.set_value(conn, _K_DATE, _today())
    try:
        used = int(settings.get(conn, _K_FOLLOWS) or 0)
    except ValueError:
        used = 0
    settings.set_value(conn, _K_FOLLOWS, str(used + 1))


def follow_if_worth_it(conn, engine, target: dict, profile: dict) -> str:
    """Follow this account when the bio shows a real LED buyer (docs/72 R3).

    Returns a short outcome for the report. Following an unrelated account costs more
    than the wasted slot: it makes this account's following list look less like someone
    in the LED trade, which is one of the things a platform reads.
    """
    worth, why = looks_like_a_customer(profile.get("text", ""))
    if not worth:
        return f"不关注：{why}"
    if follows_left(conn) <= 0:
        return "今天的关注额度用完了"
    try:
        result = engine.follow(target["channel"], target["handle"])
    except Exception as exc:  # noqa: BLE001
        # The platform refusing a write action is its last warning before a block.
        settings.set_value(conn, _K_FOLLOW_BLOCKED, _today())
        relationship_events.record(
            conn, target["lead_no"], "fact", f"关注失败，今天不再关注任何人：{str(exc)[:60]}",
            source="agent", channel=target["channel"])
        return f"关注失败，当天停止关注：{str(exc)[:50]}"
    _spend_follow(conn)
    if result.get("already"):
        return "本来就已关注"
    relationship_events.record(
        conn, target["lead_no"], "fact", f"已关注 {target['channel']} @{target['handle']}",
        source="agent", channel=target["channel"],
        detail={"url": profile.get("url")})
    return "已关注"


def _record(conn, target: dict, profile: dict) -> int:
    """Write down what this visit learned, and fill blanks on the record."""
    from app import repository as repo

    written = 0
    signals = read_signals(profile.get("text", ""))
    if signals:
        relationship_events.record(
            conn, target["lead_no"], "fact",
            "社媒动态：" + "、".join(sorted({s["kind"] for s in signals})),
            source="discovery", channel=target["channel"],
            detail={"url": profile.get("url"), "signals": signals[:5]})
        written += 1

    contacts = read_contacts(profile.get("text", ""))
    if contacts:
        current = conn.execute(
            "SELECT email, phone, website FROM leads WHERE no=?",
            (target["lead_no"],)).fetchone()
        patch = {k: v for k, v in contacts.items()
                 if not str((current[k] if k in current.keys() else "") or "").strip()}
        if patch:
            repo.update_lead(conn, target["lead_no"], patch)
            relationship_events.record(
                conn, target["lead_no"], "fact",
                "社媒主页上补到：" + "、".join(patch),
                source="discovery", channel=target["channel"],
                detail={"url": profile.get("url"), "fields": patch})
            written += 1
    return written

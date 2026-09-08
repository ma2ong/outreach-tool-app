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

# docs/91 R1. 看过是看过，改过是改过。`leads.updated_at` 的含义是「这条记录被改过」，
# 而一次什么都没学到的访问不该改记录 —— 把「看过」塞进那一列，`recheck`、`dedupe`
# 和导入路径都会以为这家公司刚被更新过。所以访问单独记一张表。
VISIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS social_visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_no INTEGER NOT NULL,
    channel TEXT NOT NULL,
    handle TEXT NOT NULL,
    at TEXT NOT NULL,
    outcome TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_social_visits_lead ON social_visits(lead_no, at);
"""

# 一个社媒主页两周回看一次。官网的回看归 docs/47 的 recheck 管，不是这里。
REVISIT_DAYS = 14

# docs/91 R2. 帖子写着哪一天。读不到日期的不算「最近动态」—— `_SIGNALS` 的关键词
# 在一个六年没更新的主页上一样能命中，而那恰好是最没价值的一类线索。
_POST_DATE = re.compile(
    r"(20\d{2})\s*[年./-]\s*(\d{1,2})\s*[月./-]\s*(\d{1,2})|"
    r"(20\d{2})-(\d{1,2})-(\d{1,2})")
# Allen 09-03：「只看近两年的帖子即可，太久远的不用看了」。两年是他给的线 ——
# 一条 2023 年的帖子仍然说明这家公司活着、在做这门生意；2019 年的不说明任何还成立的事。
STALE_AFTER_DAYS = 730

# docs/91 R4. 平台自己的框架不是这家公司说的话。一句 excerpt 里混着 Cookie 政策，
# 它就永远不能被放进给客户的信里 —— 这条决定了 R3 的成败。
_CHROME = (
    "服务条款", "广告", "Ad Choices", "Cookie", "更多", "帖子", "筛选条件",
    "查看翻译", "展开", "查看更多评论", "以 Allen Ma 的身份评论", "没有照片描述",
    "分享了帖子", "隐私政策", "Privacy Policy", "Terms of Service", "Log In",
    "Sign Up", "See more", "View translation", "登录", "注册",
)

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


def ensure_schema(conn) -> None:
    conn.executescript(VISIT_SCHEMA)
    conn.commit()


def record_visit(conn, lead_no: int, channel: str, handle: str, outcome: str) -> None:
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO social_visits(lead_no, channel, handle, at, outcome)"
        " VALUES (?,?,?,?,?)",
        (lead_no, channel, handle, dt.datetime.now(dt.UTC).isoformat(), outcome))
    conn.commit()


def strip_chrome(text: str) -> str:
    """去掉平台导航，剩下的才是这家公司说的话（docs/91 R4）。"""
    out = text or ""
    for word in _CHROME:
        out = out.replace(word, " ")
    return " ".join(out.split())


def latest_post_date(text: str) -> dt.date | None:
    """主页上最近的一条帖子是哪天（docs/91 R2）。读不到就是 None。"""
    best: dt.date | None = None
    for m in _POST_DATE.finditer(text or ""):
        parts = [p for p in m.groups() if p]
        if len(parts) != 3:
            continue
        try:
            found = dt.date(int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            continue
        if best is None or found > best:
            best = found
    return best


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
    """Messages still queued for today — how many are waiting on Allen, nothing more.

    This used to gate browsing, until docs/77 established that the count is never zero
    and so browsing never ran. It stays because the morning readout has a real use for
    it: how much of today's queue is still unsent.
    """
    try:
        # The queue's day starts at 09:00, not midnight (docs/94 R2), so asking for the
        # calendar date would report an empty queue every night between the two.
        from app import social_queue

        return conn.execute(
            "SELECT COUNT(*) FROM social_dm_queue WHERE queue_date=? AND status='ready'",
            (social_queue.sales_day(),)).fetchone()[0]
    except Exception:  # noqa: BLE001 — schema may not exist yet
        return 0


# docs/77 R1. The rule this replaces asked whether any DM was still queued today, and
# that is never false: the queue is rebuilt every morning and its `manual` rows exist
# precisely to sit there until Allen presses send. Browsing therefore never ran once.
# What docs/71 R2 was actually protecting against is the same account messaging and
# browsing strangers in the same minute, so the gate now asks about a real send. Twenty
# minutes against a fifteen-minute operating cycle means any cycle that sent skips
# browsing, and the next one resumes.
QUIET_AFTER_SEND = dt.timedelta(minutes=20)


def sent_within_quiet_window(conn, now: dt.datetime | None = None) -> int | None:
    """Minutes since the last real social DM, or None if it was long enough ago."""
    from app import social_autonomy, social_queue

    now = now or dt.datetime.now(dt.UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.UTC)
    newest = None
    for channel in social_queue.CHANNELS:
        raw = social_autonomy.last_send_at(conn, channel)
        if not raw:
            continue
        try:
            stamp = dt.datetime.fromisoformat(raw)
        except ValueError:  # a malformed stamp must not block browsing forever
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=dt.UTC)
        if newest is None or stamp > newest:
            newest = stamp
    if newest is None or now - newest >= QUIET_AFTER_SEND:
        return None
    return max(0, int((now - newest).total_seconds() // 60))


def read_signals(text: str) -> list[dict]:
    """What this profile says it has been doing.

    docs/91 R3/R4：引的是一句可以直接放进信里的话，不是一个类别名，
    而且引之前先把平台导航剔掉 —— 一句 excerpt 里混着 Cookie 政策，
    它就永远不能被引用。
    """
    clean = strip_chrome(text)
    low = clean.lower()
    found = []
    for label, words in _SIGNALS.items():
        for word in words:
            if word in low:
                at = low.index(word)
                excerpt = " ".join(clean[max(0, at - 90):at + 120].split())
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
    ensure_schema(conn)
    # docs/91 R1. 之前这里排的是 `leads.updated_at` —— 而访问不更新那一列，
    # 于是看过的公司原地不动，下一轮还排最前面：628 家排着队，每天重读第 1、2 家。
    # 现在按「上次看这家是什么时候」排，冷却期内的直接排除。
    rows = conn.execute(
        "SELECT l.no, l.company_en, l.instagram, l.facebook, l.tags,"
        "       (SELECT MAX(v.at) FROM social_visits v WHERE v.lead_no = l.no) seen_at"
        " FROM leads l"
        " WHERE COALESCE(l.do_not_contact, 0) = 0"
        "   AND (COALESCE(l.instagram,'') <> '' OR COALESCE(l.facebook,'') <> '')"
        "   AND (seen_at IS NULL OR seen_at < ?)"
        " ORDER BY seen_at IS NOT NULL, seen_at ASC,"
        "          COALESCE(l.updated_at, l.created_at) ASC LIMIT ?",
        ((dt.datetime.now(dt.UTC) - dt.timedelta(days=REVISIT_DAYS)).isoformat(),
         limit * 4)).fetchall()
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
          sleeper=time.sleep, now: dt.datetime | None = None) -> dict:
    """Read today's allowance of profiles and record what they said."""
    since = sent_within_quiet_window(conn, now)
    if since is not None:
        return {"looked": 0, "skipped": f"{since} 分钟前刚发过私信，这一轮不浏览",
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
            record_visit(conn, target["lead_no"], target["channel"], target["handle"],
                         f"读不了：{str(exc)[:40]}")
            failures += 1
            relationship_events.record(
                conn, target["lead_no"], "fact",
                f"{target['channel']} 主页看不了：{str(exc)[:60]}",
                source="agent", channel=target["channel"])
            continue

        _spend(conn)
        looked += 1
        gained = _record(conn, target, profile)
        # docs/91 R1 —— 看过就记下看过了，哪怕什么都没学到。不记，628 家就永远轮不到。
        record_visit(conn, target["lead_no"], target["channel"], target["handle"],
                     f"{gained} 条" if gained else "无新内容")
        facts += gained
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

    That test is about a stranger met while browsing. A company Allen has decided to
    write to has already passed a stronger one, which is why the send path calls
    `follow_now` instead (docs/110 R2).
    """
    worth, why = looks_like_a_customer(profile.get("text", ""))
    if not worth:
        return f"不关注：{why}"
    return follow_now(conn, engine, target, profile.get("url"))


def follow_now(conn, engine, target: dict, url: str | None = None) -> str:
    """点关注。额度、当天停手、留痕都在这里，判断值不值得关注的在调用方。"""
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
    # docs/110 R2：额度限的是写动作。已经关注着的时候一次点击都没发生，不该扣。
    if result.get("already"):
        return "本来就已关注"
    _spend_follow(conn)
    relationship_events.record(
        conn, target["lead_no"], "fact", f"已关注 {target['channel']} @{target['handle']}",
        source="agent", channel=target["channel"], detail={"url": url})
    return "已关注"


def strip_sent(text: str, sent_body: str) -> str:
    """把我们刚发出去的那段话从页面文字里删掉（docs/110 R4）。

    FB / IG 的聊天浮层在导航之后仍然挂在页面上，而我们的信里有 "LED display"、
    有我们自己的邮箱和电话 —— 不删，它会被记成「客户的近况」和「主页上补到的联系方式」。
    """
    out = text or ""
    body = (sent_body or "").strip()
    if not body:
        return out
    out = out.replace(body, " ")
    for line in body.splitlines():
        line = line.strip()
        if len(line) >= 12:
            out = out.replace(line, " ")
    return out


def after_send(conn, engine, lead_no: int, channel: str, handle: str,
               sent_body: str = "") -> dict:
    """私信刚发完，浏览器就停在对方主页上 —— 别空手离开（docs/110 R1）。

    关注、重读主页、把读到的记下来。任何一步失败都只是一行记录：这些是顺手做的事，
    不许反噬那条已经发出去的私信（docs/110 R7）。
    """
    if channel not in ("instagram", "facebook") or not handle:
        return {}
    target = {"lead_no": lead_no, "channel": channel,
              "handle": str(handle).strip().lstrip("@")}
    out = {"read": False, "facts": 0, "followed": ""}
    try:
        profile = engine.read_profile(channel, target["handle"])
    except Exception as exc:  # noqa: BLE001 — 读不了就是读不了，信已经发出去了
        record_visit(conn, lead_no, channel, target["handle"],
                     f"发完私信读不了主页：{str(exc)[:40]}")
        out["error"] = str(exc)[:80]
        return out
    # docs/110 R4，在任何解析之前。
    profile = {**profile, "text": strip_sent(profile.get("text", ""), sent_body)}
    out["read"] = True
    try:
        out["facts"] = _record(conn, target, profile)
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:80]
    # docs/110 R3：不花 20 家/天的浏览额度（这次访问已经发生了），但要记进访问表，
    # 否则明天浏览线还会把这家排到最前面，去读一遍昨天刚读过的主页。
    record_visit(conn, lead_no, channel, target["handle"],
                 f"发私信时顺带读：{out['facts']} 条" if out["facts"] else "发私信时顺带读：无新内容")
    try:
        out["followed"] = follow_now(conn, engine, target, profile.get("url"))
    except Exception as exc:  # noqa: BLE001
        out["followed"] = f"关注出错：{str(exc)[:50]}"
    return out


# docs/91 R3。社媒信号类别 → docs/85 认识的词汇。表里没有的类别不进 hook：
# `personalize._HOOK_GLOSS_KO` 缺一个词，整句韩语开场白会消失，
# 而「招聘」「新设备」本来也不是买家线索。
_HOOK_TERM = {"活动": "events", "项目": "installation", "展会": "events"}


def hook_from_signals(lead: dict, signals: list[dict]) -> str:
    """从社媒信号造一句开场白 —— 造不出来就返回空（docs/91 R3）。

    只替换那句对谁都一样的通用开场白。用官网材料建出来的 hook 已经比一个类别词具体，
    拿「events」换掉「digital signage and LED panels ... around Kitchener」是降级。
    """
    from app.backfill_hooks import GENERIC_HOOK

    current = str(lead.get("hook") or "").strip()
    if current and current != GENERIC_HOOK:
        return ""
    terms = [t for t in (_HOOK_TERM.get(s["kind"]) for s in signals) if t]
    if not terms:
        return ""
    term = terms[0]
    city = str(lead.get("city") or "").strip()
    # 两种句式都必须落在 `personalize._HOOK_WORK_RE` 上，否则韩语那一半会空掉。
    return (f"Saw the {term} work you do around {city}."
            if city else f"Saw the {term} work you do.")


def _already_written(conn, lead_no: int, summary: str) -> bool:
    """同一句话不写第二遍（docs/91 R6）—— 15 条一模一样的记录是噪音，不是十五次观察。"""
    relationship_events.ensure_schema(conn)
    return conn.execute(
        "SELECT 1 FROM relationship_events WHERE lead_no=? AND summary=? LIMIT 1",
        (lead_no, summary)).fetchone() is not None


def _radar_signal(conn, target: dict, profile: dict, best: dict, posted: dt.date) -> None:
    """一条带日期的近期动态，也要出现在销售雷达上（docs/110 R5）。

    在这之前，社媒读到的东西只写进 `relationship_events` —— Agent 读得到，人看不到。
    库里 17 条社媒动态，雷达上 0 条 social 信号，就是这条线断在这里。
    """
    from app import sales_intelligence

    url = (profile.get("url") or "").strip()
    if not re.match(r"^https?://", url, re.I):
        return  # 雷达要求来源可以点开验证；点不开的证据不算证据
    try:
        sales_intelligence.create_signal(conn, target["lead_no"], {
            "signal_type": "social",
            "headline": f"社媒{best['kind']}：{target['channel']} @{target['handle']}",
            "evidence": best["excerpt"][:2000],
            "source_url": url,
            "occurred_at": posted.isoformat(),
            # 60：主页上的一句原话，日期是帖子自己写的。比官网改版（70）弱一点，
            # 因为关键词命中的那一句未必就是这家公司最近在做的事。
            "confidence": 60,
        })
    except Exception:  # noqa: BLE001 — 雷达写不进，动态照样进时间线
        pass


def _named_people(conn, target: dict, profile: dict) -> int:
    """主页上写着「名字 + 职位」的人，进决策人雷达的候选名单（docs/110 R6）。

    不自动写进客户资料：一个猜出来的负责人姓名比没有姓名更贵 —— 下一封信会直呼其名。
    """
    from app import decision_maker_radar, people_detector

    try:
        found = people_detector.detect_page(profile.get("url") or "",
                                            strip_chrome_lines(profile.get("text", "")))
        if not found:
            return 0
        result = decision_maker_radar.persist_candidates(
            conn, target["lead_no"], found, auto_promote=False)
        if result["created"]:
            names = "、".join(f"{c['name']}（{c['title']}）" for c in found[:3])
            relationship_events.record(
                conn, target["lead_no"], "fact", f"社媒主页上看到负责人：{names}",
                source="discovery", channel=target["channel"],
                detail={"url": profile.get("url")})
        return result["created"]
    except Exception:  # noqa: BLE001 — 认不出人不影响这次访问的其余部分
        return 0


def strip_chrome_lines(text: str) -> str:
    """按行剔平台导航 —— `detect_page` 按行读，`strip_chrome` 会把换行也压掉。"""
    keep = []
    for line in (text or "").splitlines():
        clean = line.strip()
        if clean and not any(word in clean for word in _CHROME):
            keep.append(clean)
    return "\n".join(keep)


def _record(conn, target: dict, profile: dict) -> int:
    """Write down what this visit learned, and fill blanks on the record."""
    from app import repository as repo

    written = 0
    text = profile.get("text", "")
    posted = latest_post_date(text)
    age = (dt.date.today() - posted).days if posted else None

    signals = read_signals(text)
    # docs/91 R2. 判据是「近期」而不是「存在」。一家 2019 年之后再没发过帖的公司，
    # 它的社媒告诉你的是「这条线索凉了」，不是「他们在做活动」—— 两个结论都值得记，
    # 但不能记反。读不到日期时同样不敢当成动态。
    if signals and age is not None and age <= STALE_AFTER_DAYS:
        best = max(signals, key=lambda x: len(x["excerpt"]))
        summary = f"社媒动态（{posted.isoformat()}）：{best['excerpt'][:160]}"
        if not _already_written(conn, target["lead_no"], summary):
            relationship_events.record(
                conn, target["lead_no"], "fact", summary,
                source="discovery", channel=target["channel"],
                detail={"url": profile.get("url"), "posted_at": posted.isoformat(),
                        "signals": signals[:5]})
            written += 1
        _radar_signal(conn, target, profile, best, posted)
        lead = conn.execute(
            "SELECT no, company_en, country, hook, city FROM leads WHERE no=?",
            (target["lead_no"],)).fetchone()
        # docs/97，Allen 09-03：「开场白引用官网原文**或者看到社媒最近做的一些项目**，
        # 引不出退回通用句。」一条带日期的社媒原句，讲的是他们上个月做的项目，比官网上
        # 挂了三年的那段介绍更具体 —— 先让 docs/93 的模型读这段清理过的主页文字，它
        # 一样要交回逐字对得上的出处。引不出才退回下面那句类目级的。
        better = None
        if lead:
            from app import hook_writer

            hook_writer.ensure_schema(conn)
            sourced = conn.execute(
                "SELECT COALESCE(hook_quote,'') q FROM leads WHERE no=?",
                (target["lead_no"],)).fetchone()["q"].strip()
            # docs/91 R3 的那条不降级规矩仍然成立，只是判据换了：已经有出处的开场白
            # （官网原话）不被社媒盖掉。没有出处的（正则句、通用句）才让模型来写。
            if not sourced:
                better = hook_writer.improve(conn, dict(lead), strip_chrome(text),
                                             profile.get("url") or "")
        if better:
            relationship_events.record(
                conn, target["lead_no"], "fact",
                f"开场白改用社媒原话：{better['hook']}",
                source="discovery", channel=target["channel"],
                detail={"url": profile.get("url"), "quote": better["quote"][:200]})
            written += 1
        fresh_hook = "" if better else (hook_from_signals(dict(lead), signals) if lead else "")
        if fresh_hook:
            conn.execute("UPDATE leads SET hook=? WHERE no=?",
                         (fresh_hook, target["lead_no"]))
            conn.commit()
            relationship_events.record(
                conn, target["lead_no"], "fact", f"开场白改用社媒线索：{fresh_hook}",
                source="discovery", channel=target["channel"],
                detail={"url": profile.get("url")})
            written += 1
    elif signals or posted:
        # 三种结果，不是两种。读不到日期 ≠ 久未更新 —— 后者是一个我们没有观察到的
        # 结论，而这份规格反对的正是这个。所以话照引，只是不声称它是「最近」的。
        if posted:
            summary = f"社媒主页久未更新：最近一条是 {posted.isoformat()}"
        else:
            best = max(signals, key=lambda x: len(x["excerpt"]))
            summary = f"社媒主页写着（日期不详）：{best['excerpt'][:160]}"
        if not _already_written(conn, target["lead_no"], summary):
            relationship_events.record(
                conn, target["lead_no"], "fact", summary,
                source="discovery", channel=target["channel"],
                detail={"url": profile.get("url"),
                        "posted_at": posted.isoformat() if posted else None,
                        "signals": signals[:5]})
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
    written += _named_people(conn, target, profile)
    return written

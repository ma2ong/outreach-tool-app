"""Today's social DM queue: prepare first, send only through the existing channel flow.

The queue deliberately keeps first-touch social copy shorter than email. Customer routing
has only three variants: Rental / Install / General. A mixed or uncertain company gets
General; outdoor remains a product/application, never a customer segment.
"""
from __future__ import annotations

import datetime as dt
import random
import re

from app import local_time, message_guard
from app.personalize import is_korean_customer, render

CHANNELS = ("whatsapp", "instagram", "facebook")

# Keep preparation comfortably below platform caps and vary it by day.
DAILY_RANGE = {"whatsapp": (8, 15), "instagram": (8, 15), "facebook": (5, 9)}
WEEKEND_FACTOR = 0.5

_CONTACT_COL = {"whatsapp": "phone", "instagram": "instagram", "facebook": "facebook"}
_CHANNEL_PREFERENCE = ("instagram", "whatsapp", "facebook")

SCHEMA = """
CREATE TABLE IF NOT EXISTS social_dm_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    queue_date TEXT NOT NULL,
    lead_no INTEGER NOT NULL,
    channel TEXT NOT NULL,
    target TEXT NOT NULL,
    body TEXT NOT NULL,
    rank_order INTEGER NOT NULL DEFAULT 0,
    reason TEXT,
    edited INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ready',
    variant TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(lead_no) REFERENCES leads(no) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_social_queue_day_lead
    ON social_dm_queue(queue_date, lead_no);
CREATE INDEX IF NOT EXISTS idx_social_queue_day ON social_dm_queue(queue_date, rank_order);
"""

# Four shapes per segment reduce repetitive platform patterns while keeping the commercial
# logic stable. Each message says what we can help with and asks for one easy input; it
# avoids price-first language, distributor comparisons and vague "worth a conversation" CTAs.
_FAMILIES: dict[str, tuple[str, ...]] = {
    "rental": (
        "We supply rental LED for indoor and outdoor use in P2.604, P2.976, P3.91 and P4.8. "
        "If you have a project coming up, send me the pitch or specs you need and I can "
        "recommend a suitable configuration and prepare a detailed quotation.",
        "For rental LED, we offer P2.604 / P2.976 / P3.91 / P4.8 for both indoor and outdoor "
        "use. Send me the pitch or specs you need and I can suggest the right configuration "
        "and prepare a detailed quotation.",
        "We work with rental and staging companies on die-cast LED cabinets in P2.604, P2.976, "
        "P3.91 and P4.8. If you're reviewing a project or new stock, send me the specs and I "
        "can recommend a suitable setup and prepare a quotation.",
        "Rental LED is one of our main lines, with P2.604 / P2.976 / P3.91 / P4.8 for indoor "
        "and outdoor use. Send me the pitch, size or requirements and I can recommend a "
        "suitable configuration and prepare a quotation.",
    ),
    "install": (
        "We supply fixed-install LED for indoor and outdoor projects. If you're specifying a "
        "job, send me the pitch, screen size or requirements and I can recommend a suitable "
        "configuration and prepare a detailed quotation.",
        "For fixed installs, we cover fine-pitch indoor through outdoor LED. Send me the "
        "application, pitch or screen size and I can suggest the right configuration and "
        "prepare a quotation.",
        "We work with integrators on fixed-install LED projects. If you have a project in "
        "design, send me the pitch, screen size or specs and I can recommend a suitable "
        "configuration and prepare a detailed quotation.",
        "Fixed-install LED is one of our main lines, with front/rear service options. Send me "
        "the project requirements and I can recommend the suitable product configuration and "
        "prepare a quotation.",
    ),
    "general": (
        "We supply LED displays across fine-pitch, indoor, rental and outdoor fixed. If LED is "
        "in your pipeline, send me the application, pitch, size or specs you need and I can "
        "recommend the suitable option and prepare a detailed quotation.",
        "We work with LED display buyers across rental and installation projects. Send me the "
        "application, pitch or screen size and I can suggest a suitable configuration and "
        "prepare a quotation.",
        "We supply LED display panels for commercial, rental and outdoor projects. Tell me the "
        "pitch, application or requirements you usually work with and I can recommend the "
        "closest option and prepare a detailed quotation.",
        "We cover a broad LED display range from fine-pitch to outdoor. If a project comes up, "
        "send me the use case, size or specs you need and I can recommend the suitable product "
        "and prepare a quotation.",
    ),
}

_FAMILIES_KO: dict[str, tuple[str, ...]] = {
    "rental": (
        "렌탈용은 실내·실외 모두 P2.604 / P2.976 / P3.91 / P4.8 라인업으로 대응하고 있습니다. "
        "필요하신 피치나 제품 사양을 알려주시면 용도에 맞는 구성과 상세 견적을 보내드리겠습니다.",
        "렌탈 LED는 P2.604 / P2.976 / P3.91 / P4.8까지 실내·실외 모두 가능합니다. "
        "검토 중인 사양을 알려주시면 맞는 구성으로 안내드리고 견적도 함께 보내드리겠습니다.",
        "렌탈·행사용 다이캐스팅 LED 캐비닛을 공급하고 있습니다. 필요한 피치와 사양을 "
        "보내주시면 용도에 맞는 제품 구성과 상세 견적을 정리해 드리겠습니다.",
        "렌탈 LED가 주요 제품군 중 하나입니다. 피치, 화면 크기 또는 필요한 사양을 알려주시면 "
        "적합한 구성으로 추천드리고 견적도 보내드리겠습니다.",
    ),
    "install": (
        "고정 설치용은 실내부터 실외까지 다양한 사양으로 대응하고 있습니다. 피치, 화면 크기 또는 "
        "필요한 조건을 알려주시면 용도에 맞는 제품 구성과 상세 견적을 보내드리겠습니다.",
        "고정 설치 프로젝트 검토 중이시면 사용 용도와 화면 크기를 알려주세요. 맞는 피치와 제품 "
        "구성을 추천드리고 견적도 함께 보내드리겠습니다.",
        "AV·시스템 통합 프로젝트용 고정 설치 LED를 공급하고 있습니다. 필요한 피치와 화면 크기, "
        "사양을 보내주시면 적합한 구성과 상세 견적을 정리해 드리겠습니다.",
        "고정 설치 LED는 전·후면 유지보수 옵션으로 대응 가능합니다. 프로젝트 조건을 알려주시면 "
        "맞는 제품을 추천드리고 견적도 보내드리겠습니다.",
    ),
    "general": (
        "파인피치부터 실내, 렌탈, 실외 고정형까지 LED 제품군을 공급하고 있습니다. 사용 용도, "
        "피치, 화면 크기 또는 필요한 사양을 알려주시면 맞는 제품과 상세 견적을 보내드리겠습니다.",
        "렌탈과 고정 설치 프로젝트 모두 대응하고 있습니다. 검토 중인 용도와 화면 크기를 알려주시면 "
        "적합한 제품 구성을 추천드리고 견적도 함께 보내드리겠습니다.",
        "상업용, 렌탈용, 실외용 LED 디스플레이를 공급하고 있습니다. 주로 보시는 피치나 필요한 "
        "사양을 알려주시면 가장 적합한 제품과 상세 견적을 안내드리겠습니다.",
        "파인피치부터 실외까지 다양한 LED 제품군을 대응하고 있습니다. 프로젝트 용도, 크기 또는 "
        "필요한 사양을 보내주시면 맞는 제품을 추천드리고 견적도 보내드리겠습니다.",
    ),
}


def sentence_for(segment: str, nth: int, *, korean: bool = False) -> str:
    """The short social message family for this customer segment and market."""
    families = _FAMILIES_KO if korean else _FAMILIES
    family = families[segment]
    return family[nth % len(family)]


def variant_of(lead: dict) -> str:
    """Stable variant identity for measurement and send-log attribution."""
    from app import copy_segments

    segment = copy_segments.segment_of(lead)
    nth = int(lead.get("no") or 0) % len(_FAMILIES[segment])
    return f"social:{segment}#{nth}"


def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA)
    have = {r["name"] for r in conn.execute("PRAGMA table_info(social_dm_queue)")}
    if "variant" not in have:
        conn.execute("ALTER TABLE social_dm_queue ADD COLUMN variant TEXT")
    conn.commit()


def sales_day(now: dt.datetime | None = None) -> str:
    """Sales day follows the shared Shenzhen 09:00 boundary."""
    return local_time.sales_day(now).isoformat()


def _allowance(channel: str, now: dt.datetime) -> int:
    """How many messages to prepare today — stable within a day, varied across days."""
    low, high = DAILY_RANGE[channel]
    day = local_time.sales_day(now)
    rng = random.Random(f"{day.isoformat()}:{channel}")
    count = rng.randint(low, high)
    if day.weekday() >= 5:
        count = max(2, int(count * WEEKEND_FACTOR))
    return count


def _day_started(now: dt.datetime | None = None) -> str:
    return dt.datetime.combine(
        local_time.sales_day(now), local_time.DAY_STARTS).strftime("%Y-%m-%d %H:%M:%S")


_FIT_RE = re.compile(r"\((\d+)\)")


def _fit_score(target_fit: str | None) -> int:
    match = _FIT_RE.search(str(target_fit or ""))
    return int(match.group(1)) if match else 0


def _candidates(conn, now: dt.datetime) -> list[dict]:
    """Leads worth a DM today, best first."""
    from app import sales_intelligence

    sales_intelligence.ensure_schema(conn)
    rows = conn.execute(
        """
        SELECT l.no, l.company_en, l.contact_name, l.title, l.country, l.city, l.website,
               l.hook, l.brief, l.phone, l.instagram, l.facebook, l.target_fit,
               l.whatsapp_status, l.tags, l.business,
               COALESCE(MAX(CASE WHEN b.status != 'dismissed' THEN b.confidence END), 0) signal,
               EXISTS(SELECT 1 FROM outreach o WHERE o.lead_no=l.no
                      AND o.status IN ('messaged','replied')) touched
        FROM leads l
        LEFT JOIN buying_signals b ON b.lead_no = l.no
        WHERE COALESCE(l.do_not_contact, 0) = 0
          AND l.no NOT IN (SELECT lead_no FROM send_log
                           WHERE datetime(sent_at, 'localtime') >= ?)
          AND l.no NOT IN (SELECT e.lead_no FROM sequence_enrollments e
                           JOIN sequences s ON s.id = e.sequence_id
                           WHERE e.status='active' AND s.channel='email'
                             AND e.next_due_date <= date(?))
        GROUP BY l.no
        """,
        (_day_started(now), sales_day(now)),
    ).fetchall()

    from app import icp

    leads = [dict(r) for r in rows if not icp.is_off_trade(r)]
    leads.sort(key=lambda r: (-int(r["signal"] or 0), -_fit_score(r["target_fit"]),
                              0 if str(r["hook"] or "").strip() else 1,
                              int(r["touched"] or 0), r["no"]))
    return leads


def _channel_for(conn, lead: dict, taken: set[str]) -> tuple[str, str] | None:
    """Pick the one usable social channel for this company today."""
    from app import channel_outreach as co

    for channel in _CHANNEL_PREFERENCE:
        if channel in taken:
            continue
        if not str(lead.get(_CONTACT_COL[channel]) or "").strip():
            continue
        if channel == "whatsapp" and (lead.get("whatsapp_status") or "") == "none":
            continue
        from app import recontact
        blocked = conn.execute(
            f"SELECT 1 FROM ({recontact.BLOCKED_SQL}) WHERE lead_no=?",
            [*recontact.blocked_params(channel), lead["no"]]).fetchone()
        if blocked:
            continue
        try:
            target = co._target(channel, lead)
        except Exception:  # an unusable handle is simply not a candidate
            continue
        if target:
            return channel, target
    return None


def _compose(lead: dict) -> str:
    from app import copy_segments

    hook = str(lead.get("hook") or lead.get("hook_ko") or "").strip()
    no = int(lead.get("no") or 0)
    korean = is_korean_customer(lead)
    sentence = sentence_for(copy_segments.segment_of(lead), no, korean=korean)
    parts = ["{greeting}"]
    if hook:
        parts.append("{hook_ko}" if korean else "{hook}")
    parts.append(sentence)
    return render(" ".join(parts), lead).strip()


def build_today(conn, now: dt.datetime | None = None) -> dict:
    """Prepare today's queue. This function writes queue rows; it does not send."""
    ensure_schema(conn)
    now = now or dt.datetime.now()
    today = sales_day(now)
    conn.execute("DELETE FROM social_dm_queue WHERE queue_date != ? AND edited = 0", (today,))
    conn.execute("DELETE FROM social_dm_queue WHERE queue_date != ?", (today,))

    kept = {row["lead_no"]: dict(row) for row in conn.execute(
        "SELECT * FROM social_dm_queue WHERE queue_date=? AND edited=1", (today,))}
    conn.execute("DELETE FROM social_dm_queue WHERE queue_date=? AND edited=0", (today,))

    from app import social_autonomy
    allowance = {c: (0 if social_autonomy.get(conn, c) == "off" else _allowance(c, now))
                 for c in CHANNELS}
    for row in kept.values():
        allowance[row["channel"]] = max(0, allowance[row["channel"]] - 1)

    holds: list[dict] = []
    rank = 0
    per_channel = {c: 0 for c in CHANNELS}
    seen_bodies: set[str] = {row["body"].strip().lower() for row in kept.values()}
    for lead in _candidates(conn, now):
        if lead["no"] in kept:
            per_channel[kept[lead["no"]]["channel"]] += 1
            continue
        if all(allowance[c] <= 0 for c in CHANNELS):
            break
        full = {c for c in CHANNELS if allowance[c] <= 0}
        picked = _channel_for(conn, lead, full)
        if picked is None:
            continue
        channel, target = picked
        body = _compose(lead)
        guarded_as = "email" if str(lead.get("hook") or "").strip() else channel
        verdict = message_guard.check(body, lead, channel=guarded_as)
        if verdict.blocked:
            holds.append({"lead_no": lead["no"], "company": lead["company_en"],
                          "reason": verdict.reason, "detail": verdict.detail})
            continue
        if body.strip().lower() in seen_bodies:
            holds.append({"lead_no": lead["no"], "company": lead["company_en"],
                          "reason": "duplicate",
                          "detail": f"这条私信和今天另一条一字不差（{lead['company_en']} 的 hook 太通用），"
                                    "补一条更具体的开场白再发"})
            continue
        seen_bodies.add(body.strip().lower())
        rank += 1
        conn.execute(
            "INSERT INTO social_dm_queue(queue_date, lead_no, channel, target, body,"
            " rank_order, created_at, variant) VALUES (?,?,?,?,?,?,?,?)",
            (today, lead["no"], channel, target, body, rank, now.isoformat(),
             variant_of(lead)))
        allowance[channel] -= 1
        per_channel[channel] += 1
    conn.commit()
    return {"date": today, "queued": sum(per_channel.values()), "per_channel": per_channel,
            "held": len(holds), "holds": holds[:20]}


def today(conn, now: dt.datetime | None = None) -> list[dict]:
    ensure_schema(conn)
    return [dict(r) for r in conn.execute(
        "SELECT q.*, l.company_en, l.country, l.website FROM social_dm_queue q"
        " JOIN leads l ON l.no = q.lead_no"
        " WHERE q.queue_date=? ORDER BY q.rank_order", (sales_day(now),))]


def awaiting_you(conn, now: dt.datetime | None = None) -> int:
    """How many of today's rows actually wait for manual send."""
    from app import social_autonomy

    return sum(1 for row in today(conn, now)
               if row["status"] == "ready"
               and social_autonomy.effective_mode(
                   social_autonomy.get(conn, row["channel"]), row["country"]) != "auto")


def edit(conn, queue_id: int, body: str) -> bool:
    """A human edit survives queue rebuilds."""
    text = str(body or "").strip()
    if not text:
        return False
    cur = conn.execute(
        "UPDATE social_dm_queue SET body=?, edited=1 WHERE id=? AND status='ready'",
        (text, queue_id))
    conn.commit()
    return cur.rowcount > 0


def drop(conn, queue_id: int) -> bool:
    cur = conn.execute("DELETE FROM social_dm_queue WHERE id=? AND status='ready'", (queue_id,))
    conn.commit()
    return cur.rowcount > 0


def mark_no_whatsapp(conn, queue_id: int) -> bool:
    """Persist a manual observation that this phone number has no WhatsApp account."""
    row = conn.execute(
        "SELECT lead_no FROM social_dm_queue"
        " WHERE id=? AND status='ready' AND channel='whatsapp'", (queue_id,)).fetchone()
    if row is None:
        return False
    conn.execute("UPDATE leads SET whatsapp_status='none' WHERE no=?", (row["lead_no"],))
    conn.execute("DELETE FROM social_dm_queue WHERE id=?", (queue_id,))
    conn.commit()
    return True

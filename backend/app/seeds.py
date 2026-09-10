"""Ready-made templates and the system cold-email sequences."""

from app.outreach_defaults import EN_BODY, EN_SUBJECT, KO_BODY, KO_SIGNOFF, KO_SUBJECT, SIGNOFF


def _cold_email_templates():
    """Manual cold-email picker mirrors the General system sequence (docs/84, 127)."""
    from app import seed_sequences as seq

    for korean in (False, True):
        lang, label = ("ko", "韩语") if korean else ("en", "英语")
        for order, _offset, subject, body in seq.steps_for("general", korean):
            yield f"冷邮件 · 中性版 · 第{order + 1}封（{label}）", lang, subject, body


EMAIL_TEMPLATES = list(_cold_email_templates())


def _dm_templates():
    """One reachable starter DM per docs/127 customer segment."""
    from app import copy_segments, social_queue

    for segment in copy_segments.SEGMENTS:
        yield (f"私信 · {copy_segments.LABEL[segment]}（英语）", "en",
               "Hi {contact}, " + social_queue.sentence_for(segment, 0))


DM_TEMPLATES = list(_dm_templates())


# Optional material-request templates remain separate from first-touch segmentation.
# Outdoor here is a product/application fact inside a comparison sheet, not a customer
# family or routing decision.
ALLEN_STYLE_TEMPLATES = [
    ("资料 · 产品线对比（英语）", "en",
     "LED range comparison",
     """Hi {contact},

{hook}

I'm Allen, handling export sales for an LED display manufacturer in Shenzhen.

Our range covers:

  · Fine pitch P0.6-P1.8, 600-800 nits — control rooms, studios, boardrooms
  · Indoor commercial P2-P4, 600-800 nits — retail, conference, stage backdrop
  · Rental P2.6-P3.9 indoor and P3.9-P4.8 outdoor, die-cast cabinets
  · Outdoor fixed P2.5-P10, 5,500-8,000 nits — billboards and building facades

Would a one-page comparison with cabinet weight, power and service access be useful to
{company}?

Allen Ma · Shenzhen Maxcolor Visual
WhatsApp/WeChat +86 135-7087-1001
"""),
    ("资料 · 产品线对比（韩语）", "ko",
     "LED 제품군 비교표",
     """안녕하세요, {contact}님.

{hook_ko}

저는 심천의 LED 디스플레이 제조업체에서 해외영업을 담당하는 Allen입니다.

{company}에서 검토하실 만한 범위를 간단히 정리해 드립니다.

  · 미세 피치 P0.6-P1.8 (600-800 nits) — 관제실, 스튜디오, 회의실
  · 실내 상업용 P2-P4 (600-800 nits) — 리테일, 컨퍼런스, 무대 배경
  · 렌탈용 실내 P2.6-P3.9 / 실외 P3.9-P4.8, 다이캐스팅 캐비닛
  · 실외 고정 P2.5-P10 (5,500-8,000 nits) — 옥외광고, 건물 외벽

캐비닛 무게, 소비전력, 유지보수 방식을 한눈에 볼 수 있는 비교표가 {company} 검토에
도움이 될까요?

Allen Ma · Shenzhen Maxcolor Visual
Kakaotalk / WeChat +86 13570871001
"""),
    ("资料 · 规格书（英语）", "en",
     "Cabinet data sheet",
     """Hi {contact},

I'm Allen, handling export sales for an LED display manufacturer in Shenzhen.

For drawings and tender checks, our data sheet can include:

  · cabinet dimensions and weight
  · maximum and average power
  · brightness and front/rear service access

Would that drawing-ready sheet be useful to {company}?

Allen Ma · Shenzhen Maxcolor Visual
WhatsApp/WeChat +86 135-7087-1001
"""),
    ("资料 · 规格书（韩语）", "ko",
     "캐비닛 도면 자료",
     """안녕하세요, {contact}님.

저는 심천의 LED 디스플레이 제조업체에서 해외영업을 담당하는 Allen입니다.

도면과 입찰 검토용 자료에는 아래 내용을 함께 정리할 수 있습니다.

  · 캐비닛 크기와 무게
  · 최대·평균 소비전력
  · 밝기와 전후면 유지보수 방식

이 도면용 자료가 {company} 검토에 도움이 될까요?

Allen Ma · Shenzhen Maxcolor Visual
Kakaotalk / WeChat +86 13570871001
"""),
]

ALLEN_STYLE_DM = [
    ("私信 · 产品线对比（韩语）", "ko",
     "안녕하세요, {contact}님. 심천의 LED 디스플레이 제조업체에서 해외영업을 담당하는 "
     "Allen입니다. 실내 P0.6~P4, 렌탈 P2.6-P4.8, 실외 P2.5-P10 비교표가 도움이 될까요?"),
]


def _bundled_templates():
    for name, lang, subject, body in EMAIL_TEMPLATES + ALLEN_STYLE_TEMPLATES:
        yield name, "email", subject, body, lang
    for name, lang, body in DM_TEMPLATES + ALLEN_STYLE_DM:
        for channel, suffix in (("whatsapp", "WA"), ("instagram", "IG"),
                                ("facebook", "FB")):
            yield f"{name} · {suffix}", channel, None, body, lang


def seed_templates(conn) -> int:
    """Add missing starter templates, keyed by system name and channel."""
    from app import repository
    existing = {(t.name, t.channel) for t in repository.list_templates(conn)}
    added = 0
    for name, channel, subject, body, lang in _bundled_templates():
        if (name, channel) in existing:
            continue
        repository.add_template(conn, name, channel, subject, body, lang)
        added += 1
    return added


# Exact names of system-owned rows retired by earlier copy migrations plus the Outdoor
# DM family retired by docs/127. User-created templates are never matched by this list.
RETIRED_TEMPLATES = tuple(
    [f"{n}（{lang}）" for lang in ("英语", "韩语")
     for n in ("首次触达", "跟进2：案例+提问", "跟进3：最后一封",
               "工厂直供介绍", "规格书索取")]
    + [f"DM {n}（{lang}） · {suffix}" for lang in ("英语", "韩语")
       for n in ("首次触达", "跟进", "工厂直供") for suffix in ("WA", "IG")]
    + [f"私信 · 户外为主（英语） · {suffix}" for suffix in ("WA", "IG", "FB")]
)


def drop_retired_templates(conn) -> int:
    """Remove only named system rows that the repo no longer ships."""
    cur = conn.execute(
        "DELETE FROM templates WHERE name IN (%s)"
        % ",".join("?" * len(RETIRED_TEMPLATES)), RETIRED_TEMPLATES)
    return cur.rowcount


def refresh_bundled_templates(conn) -> int:
    """Refresh named system templates while preserving every unknown/custom row."""
    from app import repository

    drop_retired_templates(conn)
    refreshed = 0
    for name, channel, subject, body, lang in _bundled_templates():
        cur = conn.execute(
            "UPDATE templates SET subject=?, body=?, lang=? WHERE name=? AND channel=?",
            (subject, body, lang, name, channel),
        )
        if not cur.rowcount:
            repository.add_template(conn, name, channel, subject, body, lang)
        refreshed += 1
    conn.commit()
    return refreshed


def seed_sequences(conn) -> list[int]:
    """Load/refresh the three-segment cold-email sequences in both languages."""
    from app import seed_sequences as seq

    before = {r[0] for r in conn.execute("SELECT id FROM sequences")}
    ids = seq.seed_all(conn).values()
    return sorted(i for i in ids if i not in before)

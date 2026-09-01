"""Ready-made templates and a follow-up sequence, loaded in one click."""

from app.outreach_defaults import EN_BODY, EN_SUBJECT, KO_BODY, KO_SIGNOFF, KO_SUBJECT, SIGNOFF

# docs/84 R1: the manual panel offers the letters the sequence actually sends, generated
# rather than copied. The openers that used to be written out here never sent a single
# email and had drifted several revisions behind the sequence — a second string saying
# the same thing is a second string that goes stale.
#
# The neutral segment, because a hand-picked batch spans customer types and 中性版 is the
# letter written for not knowing which. English has one letter and Korean three: Allen
# deleted the English neutral follow-ups outright (docs/82 R7), so they are not on offer
# here either.
def _cold_email_templates():
    from app import seed_sequences as seq

    for korean in (False, True):
        lang, label = ("ko", "韩语") if korean else ("en", "英语")
        for order, _offset, subject, body in seq.steps_for("general", korean):
            yield f"冷邮件 · 中性版 · 第{order + 1}封（{label}）", lang, subject, body


EMAIL_TEMPLATES = list(_cold_email_templates())


# docs/84 R1 again, for the other channel: one template per customer type, taken from the
# family the DM queue actually sends. What used to be here was three shapes no send path
# could reach, each stored twice because IG and WA needed a row apiece and the bodies were
# byte-identical.
def _dm_templates():
    from app import copy_segments, social_queue

    for segment in copy_segments.SEGMENTS:
        yield (f"私信 · {copy_segments.LABEL[segment]}（英语）", "en",
               "Hi {contact}, " + social_queue.sentence_for(segment, 0))


DM_TEMPLATES = list(_dm_templates())


# docs/82. Written in Allen's own shape, learned from 2,956 letters he sent himself
# between 2022 and 2025 — not copied from them. His order every time: greet warmly, say
# which factory is writing and who you are, put the range and its real numbers in front
# of the reader, then invite. 안녕하세요~ 심천 LED 전광판 업체 맥스컬러입니다 … 관심하신
# 제품 있으시면 연락주세요~
#
# What is deliberately absent: a series name or a cabinet dimension. An earlier pass
# lifted "R3 시리즈, 500×500 / 500×1000mm" straight out of his June 2025 emails and he
# stopped it — 你毕竟不熟悉我的产品线，所以不用具体到哪个产品之类的. A series can be
# renamed or dropped and this file would not know. Every number below is a row in
# `products` with agent_approved=1.
#
# docs/83 keeps company names out of subjects and puts the useful context in the body.
ALLEN_STYLE_TEMPLATES = [
    ("资料 · 产品线对比（英语）", "en",
     "LED range comparison",
     """Hi {contact},

{hook}

I'm Allen, handling export sales for an LED display manufacturer in Shenzhen.

Our range covers:

  · Fine pitch P0.7-P1.8, 600-800 nits — control rooms, studios, boardrooms
  · Indoor commercial P2-P3, 600-800 nits — retail, conference, stage backdrop
  · Rental P2.6-P3.9 indoor and P3.9-P4.8 outdoor, die-cast cabinets
  · Outdoor fixed P4-P10, 5,500-8,000 nits — billboards and building facades

Would a one-page comparison with cabinet weight, power and service access be useful to
{company}?

Allen Ma · Shenzhen Maxcolor Visual
WhatsApp/WeChat +86 135-7087-1001
"""),
    ("资料 · 产品线对比（韩语）", "ko",
     "LED 제품군 비교표",
     """안녕하세요, {contact}님.

{hook_ko}

저는 선전의 LED 디스플레이 제조업체에서 해외영업을 담당하는 Allen입니다.

{company}에서 검토하실 만한 범위를 간단히 정리해 드립니다.

  · 미세 피치 P0.7-P1.8 (600-800 nits) — 관제실, 스튜디오, 회의실
  · 실내 상업용 P2-P3 (600-800 nits) — 리테일, 컨퍼런스, 무대 배경
  · 렌탈용 실내 P2.6-P3.9 / 실외 P3.9-P4.8, 다이캐스팅 캐비닛
  · 실외 고정 P4-P10 (5,500-8,000 nits) — 옥외광고, 건물 외벽

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

저는 선전의 LED 디스플레이 제조업체에서 해외영업을 담당하는 Allen입니다.

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
     "안녕하세요, {contact}님. 선전의 LED 디스플레이 제조업체에서 해외영업을 담당하는 "
     "Allen입니다. 실내 P2-P3, 렌탈 P2.6-P4.8, 실외 P4-P10 비교표가 도움이 될까요?"),
]


def _bundled_templates():
    for name, lang, subject, body in EMAIL_TEMPLATES + ALLEN_STYLE_TEMPLATES:
        yield name, "email", subject, body, lang
    # Facebook was offered in the panel with nothing behind it — picking it showed
    # 「暂无模板」. One body per row per channel because the panel filters by channel;
    # the text is written once above.
    for name, lang, body in DM_TEMPLATES + ALLEN_STYLE_DM:
        for channel, suffix in (("whatsapp", "WA"), ("instagram", "IG"),
                                ("facebook", "FB")):
            yield f"{name} · {suffix}", channel, None, body, lang


def seed_templates(conn) -> int:
    """Add missing starter templates, keyed by their system name and channel."""
    from app import repository
    existing = {(t.name, t.channel) for t in repository.list_templates(conn)}
    added = 0
    for name, channel, subject, body, lang in _bundled_templates():
        if (name, channel) in existing:
            continue
        repository.add_template(conn, name, channel, subject, body, lang)
        added += 1
    return added


# Names this file used to ship under. They are deleted rather than renamed: the copy
# behind them is generated now, so there is nothing in the old row worth carrying over,
# and a rename would have to guess which of two old rows becomes which new one. Anything
# Allen saved himself is not in this set and is never touched (docs/84 R3).
RETIRED_TEMPLATES = tuple(
    [f"{n}（{lang}）" for lang in ("英语", "韩语")
     for n in ("首次触达", "跟进2：案例+提问", "跟进3：最后一封",
               "工厂直供介绍", "规格书索取")]
    + [f"DM {n}（{lang}） · {suffix}" for lang in ("英语", "韩语")
       for n in ("首次触达", "跟进", "工厂直供") for suffix in ("WA", "IG")]
)


def drop_retired_templates(conn) -> int:
    """Remove the rows this file no longer ships. Allen's own templates are safe."""
    cur = conn.execute(
        "DELETE FROM templates WHERE name IN (%s)"
        % ",".join("?" * len(RETIRED_TEMPLATES)), RETIRED_TEMPLATES)
    return cur.rowcount


def refresh_bundled_templates(conn) -> int:
    """Refresh only the named system templates; preserve every unknown row."""
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
    """Load the cold-email sequences — every customer type, both languages.

    There used to be two built here as well, from a copy of the templates above, and they
    were a fourth place holding the same letters (docs/84 R1). `seed_all` owns them now;
    this stays because "一键载入" calls it by name.
    """
    from app import seed_sequences as seq

    before = {r[0] for r in conn.execute("SELECT id FROM sequences")}
    ids = seq.seed_all(conn).values()
    # Only what this call created: "一键载入" reports what it added, and seed_all
    # rewrites the steps of the ones already there every time by design.
    return sorted(i for i in ids if i not in before)

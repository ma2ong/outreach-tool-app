"""Ready-made templates and a follow-up sequence, loaded in one click."""

from app.outreach_defaults import EN_BODY, EN_SUBJECT, KO_BODY, KO_SIGNOFF, KO_SUBJECT, SIGNOFF

# 两种语言都照 Allen 实际在发的销售逻辑来写：首封必须落到这家公司本身，后续再用
# 项目状态二选一把对话推进。首封里的 {hook} 没抓到会自动省掉，但 {company} 仍保留。
EMAIL_TEMPLATES = [
    ("首次触达（英语）", "en", EN_SUBJECT, EN_BODY),
    ("跟进2：案例+提问（英语）", "en", "Re: LED panel specs",
     f"""Hi {{contact}},

For project drawings, our comparison can include cabinet dimensions and weight, maximum
and average power, brightness, and front/rear service in one table.

Would that format be useful to {{company}}?

{SIGNOFF}"""),
    ("跟进3：最后一封（英语）", "en", "Re: LED panel specs",
     f"""Hi {{contact}},

A compact reference for {{company}}: fine pitch from P0.7, P2-P3 indoor commercial,
P2.6-P4.8 die-cast rental, and P4-P10 outdoor fixed.

Would the one-page range comparison be useful to keep with your supplier files?

{SIGNOFF}"""),
    ("首次触达（韩语）", "ko", KO_SUBJECT, KO_BODY),
    ("跟进2：案例+提问（韩语）", "ko", "Re: LED 패널 사양",
     f"""안녕하세요, {{contact}}님.

프로젝트 도면에 필요한 캐비닛 크기와 무게, 최대·평균 소비전력, 밝기, 전후면
유지보수 방식을 한 표에 정리할 수 있습니다.

이 형식의 비교표가 {{company}}에 도움이 될까요?

{KO_SIGNOFF}"""),
    ("跟进3：最后一封（韩语）", "ko", "Re: LED 패널 사양",
     f"""안녕하세요, {{contact}}님.

{{company}}에서 참고하실 수 있도록 제품 범위를 간단히 정리드립니다. P0.7부터의
미세 피치, 실내 상업용 P2-P3, 렌탈용 P2.6-P4.8, 실외 고정형 P4-P10까지입니다.

한 페이지 제품군 비교표를 공급업체 자료로 보관하시면 도움이 될까요?

{KO_SIGNOFF}"""),
]

# DM 规矩保持不变：不提公司名、只说 from Shenzhen China、冷启动仍由手工确认。
DM_TEMPLATES = [
    ("DM 首次触达（英语）", "en",
     "Hi {contact}, I'm Allen, handling export sales for an LED display manufacturer in Shenzhen. "
     "We cover P0.7-P10 across fine-pitch, rental and outdoor LED; would a one-page range sheet be useful?"),
    ("DM 首次触达（韩语）", "ko",
     "안녕하세요, {contact}님. 선전의 LED 디스플레이 제조업체에서 해외영업을 담당하는 "
     "Allen입니다. P0.7-P10 제품군을 한눈에 볼 수 있는 비교표가 도움이 될까요?"),
    ("DM 跟进（英语）", "en",
     "Hi {contact}, our comparison sheet includes pitch, brightness, cabinet weight, power and "
     "service access. Would that be useful for a current product review?"),
    ("DM 跟进（韩语）", "ko",
     "안녕하세요, {contact}님. 제품 비교표에는 피치, 밝기, 캐비닛 무게, 소비전력, "
     "유지보수 방식이 포함됩니다. 현재 제품 검토에 도움이 될까요?"),
]


def _by_lang(lang: str) -> dict[str, tuple[str, str]]:
    out = {}
    for name, tpl_lang, subject, body in EMAIL_TEMPLATES:
        if tpl_lang != lang:
            continue
        key = "first" if name.startswith("首次") else "f2" if name.startswith("跟进2") else "f3"
        out[key] = (subject, body)
    return out


SEQUENCE_LANGS = [("en", "英语"), ("ko", "韩语")]

EMAIL_SEQUENCES = [
    {
        "name": f"冷邮件 3 步跟进（{label}）",
        "channel": "email",
        "steps": [
            {"day_offset": 0, "subject": _by_lang(lang)["first"][0], "body": _by_lang(lang)["first"][1]},
            {"day_offset": 3, "subject": _by_lang(lang)["f2"][0], "body": _by_lang(lang)["f2"][1]},
            {"day_offset": 8, "subject": _by_lang(lang)["f3"][0], "body": _by_lang(lang)["f3"][1]},
        ],
    }
    for lang, label in SEQUENCE_LANGS
]


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
    ("工厂直供介绍（英语）", "en",
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
    ("工厂直供介绍（韩语）", "ko",
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
    ("规格书索取（英语）", "en",
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
    ("规格书索取（韩语）", "ko",
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
    ("DM 工厂直供（英语）", "en",
     "Hi {contact}, I'm Allen, handling export sales for an LED display manufacturer in Shenzhen. "
     "Indoor P2-P3 at 600-800 nits, rental P2.6-P4.8 die-cast, outdoor P4-P10 at "
     "5,500-8,000 nits; would a one-page range sheet be useful?"),
    ("DM 工厂直供（韩语）", "ko",
     "안녕하세요, {contact}님. 선전의 LED 디스플레이 제조업체에서 해외영업을 담당하는 "
     "Allen입니다. 실내 P2-P3, 렌탈 P2.6-P4.8, 실외 P4-P10 비교표가 도움이 될까요?"),
]


def _bundled_templates():
    for name, lang, subject, body in EMAIL_TEMPLATES + ALLEN_STYLE_TEMPLATES:
        yield name, "email", subject, body, lang
    for name, lang, body in DM_TEMPLATES + ALLEN_STYLE_DM:
        for channel in ("whatsapp", "instagram"):
            suffix = "WA" if channel == "whatsapp" else "IG"
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


def refresh_bundled_templates(conn) -> int:
    """Refresh only the 22 named system templates; preserve every unknown row."""
    from app import repository

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
    """Add the 3-step cold-email sequences (EN/KO); skips ones already there."""
    from app import sequences
    added = []
    for seq in EMAIL_SEQUENCES:
        if conn.execute("SELECT 1 FROM sequences WHERE name=?", (seq["name"],)).fetchone():
            continue
        added.append(sequences.create_sequence(conn, seq["name"], seq["channel"], seq["steps"]))
    return added

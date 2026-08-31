"""Ready-made templates and a follow-up sequence, loaded in one click."""

from app.outreach_defaults import EN_BODY, EN_SUBJECT, KO_BODY, KO_SIGNOFF, KO_SUBJECT, SIGNOFF

# 两种语言都照 Allen 实际在发的销售逻辑来写：首封必须落到这家公司本身，后续再用
# 项目状态二选一把对话推进。首封里的 {hook} 没抓到会自动省掉，但 {company} 仍保留。
EMAIL_TEMPLATES = [
    ("首次触达（英语）", "en", EN_SUBJECT, EN_BODY),
    ("跟进2：案例+提问（英语）", "en", "Re: Recent LED Display Projects",
     f"""Hi {{contact}},

Just following up on the LED display projects I shared earlier.

Are you working on a specific project at the moment, or keeping a supplier on file for when one comes up? Either way, let me know and I'll send only what is actually useful to you.

Looking forward to hearing from you.

{SIGNOFF}"""),
    ("跟进3：最后一封（英语）", "en", "Re: LED Displays — whenever you need them",
     f"""Hi {{contact}},

This is my last note — I don't want to fill up your inbox.

If LED displays aren't on your plan right now, no problem at all. Whenever a project comes up, just contact me anytime and I'll send specs and pricing the same day.

Hope we can have a good opportunity to work together in the future!

{SIGNOFF}"""),
    ("首次触达（韩语）", "ko", KO_SUBJECT, KO_BODY),
    ("跟进2：案例+提问（韩语）", "ko", "Re: 한국 LED 디스플레이 납품 사례",
     f"""안녕하세요~

지난번 보내드린 LED 디스플레이 설치사례 잘 보셨는지요.

혹시 지금 검토 중이신 현장이 있으실까요? 아니면 나중을 위해 공급처를 미리 알아두시는 단계이신지요.
어느 쪽이든 알려주시면 거기에 맞는 자료만 정리해서 보내드리겠습니다.

회신 기다리겠습니다.

{KO_SIGNOFF}"""),
    ("跟进3：最后一封（韩语）", "ko", "Re: 한국 LED 디스플레이 — 필요하실 때 언제든지",
     f"""안녕하세요~

계속 메일 드리기 조심스러워 이번까지만 연락드립니다.

지금 당장 필요하지 않으셔도 괜찮습니다. 나중에 LED 디스플레이 건이 생기면 언제든 편하게 연락 주세요.
문의 주시면 당일에 현장 조건에 맞는 사양과 견적 정리해서 보내드리겠습니다.

좋은 하루 보내세요!

{KO_SIGNOFF}"""),
]

# DM 规矩保持不变：不提公司名、只说 from Shenzhen China、冷启动仍由手工确认。
DM_TEMPLATES = [
    ("DM 首次触达（英语）", "en",
     "Hi {name}, this is Allen from an LED display factory in Shenzhen, China. We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing. Happy to share recent project references if you have upcoming LED display needs."),
    ("DM 首次触达（韩语）", "ko",
     "안녕하세요~ 중국 선전에서 LED 디스플레이 만드는 Allen이라고 합니다. 최근 한국에 납품한 설치사례 보내드릴게요. P0.7~P10 실내/실외 패널을 제조사 직접 가격으로 공급하고 있습니다. 검토 중이신 현장 있으시면 편하게 연락 주세요~"),
    ("DM 跟进（英语）", "en",
     "Hi {name}, following up on my last message. Are you working on an LED display project right now, or should I check back later? Either way, happy to send specs and pricing whenever it's useful."),
    ("DM 跟进（韩语）", "ko",
     "안녕하세요~ 지난번 보내드린 LED 설치사례 보셨을까요? 지금 진행 중이신 현장 있으시면 조건에 맞춰 사양이랑 견적 정리해서 보내드리겠습니다. 없으시면 나중에 필요하실 때 편하게 연락 주세요~"),
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
# {company} is in every subject because the manual panel is judged by `message_guard`
# like every other path, and the company name is what makes an automated letter read as
# addressed to someone. Twelve of the fourteen older templates fail that check today.
ALLEN_STYLE_TEMPLATES = [
    ("工厂直供介绍（英语）", "en",
     "{company} — LED panels direct from our factory in Shenzhen",
     """Hi {contact},

I hope this email finds you well. This is Allen Ma from Shenzhen Maxcolor
Visual, an LED display manufacturer here in Shenzhen.

A quick note on what we cover, in case it is useful to {company}:

  · Fine pitch P0.7-P1.8, 600-1,000 nits — control rooms, studios, boardrooms
  · Indoor commercial P2-P3, 800-1,200 nits — retail, conference, stage backdrop
  · Rental P2.6-P3.9 indoor and P3.9-P4.8 outdoor, die-cast cabinets
  · Outdoor fixed P4-P10, 5,500-8,000 nits — billboards and building facades

If any of these is close to what {company} works with, I'd be glad to send the full spec
sheet — weight and power per cabinet included. Just let me know which one, whenever it's
convenient.

Allen Ma · Shenzhen Maxcolor Visual
WhatsApp/WeChat +86 135-7087-1001
"""),
    ("工厂直供介绍（韩语）", "ko",
     "{company} — 심천 자체 공장에서 만드는 LED 디스플레이",
     """안녕하세요~ {contact}님.

심천 LED 디스플레이 제조업체 맥스컬러의 Allen 마이용입니다.

{company}에서 검토하실 만한 범위를 간단히 정리해 드립니다.

  · 미세 피치 P0.7-P1.8 (600-1,000 nits) — 관제실, 스튜디오, 회의실
  · 실내 상업용 P2-P3 (800-1,200 nits) — 리테일, 컨퍼런스, 무대 배경
  · 렌탈용 실내 P2.6-P3.9 / 실외 P3.9-P4.8, 다이캐스팅 캐비닛
  · 실외 고정 P4-P10 (5,500-8,000 nits) — 옥외광고, 건물 외벽

관심 있으신 사양이 있으시면 사양서 기꺼이 보내드리겠습니다. 캐비닛별 무게와 소비전력까지
함께 정리해 드립니다. 편하실 때 말씀만 주세요.

Allen Ma · Shenzhen Maxcolor Visual
Kakaotalk / WeChat +86 13570871001
"""),
    ("规格书索取（英语）", "en",
     "{company} — spec sheet and drawing, same day",
     """Hi {contact},

This is Allen from Shenzhen Maxcolor Visual, an LED display manufacturer in Shenzhen.
The specs come from us directly rather than from a trader passing on a datasheet.

Whenever {company} has a job coming up, I'd be glad to put together, usually the same
day:

  · the full spec sheet for that pitch
  · weight and power draw per cabinet, so it drops straight into your drawing
  · indoor or outdoor brightness options for that viewing distance

Allen Ma · Shenzhen Maxcolor Visual
WhatsApp/WeChat +86 135-7087-1001
"""),
    ("规格书索取（韩语）", "ko",
     "{company} — 사양서와 도면, 당일 발송",
     """안녕하세요~ {contact}님.

심천 LED 디스플레이 제조업체 맥스컬러의 Allen입니다. 사양은 중간 무역상을 거치지 않고
저희가 바로 드립니다.

{company}에서 건이 생기시면 아래를 함께 정리해 기꺼이 보내드리겠습니다. 보통 당일에
드릴 수 있습니다.

  · 해당 피치 전체 사양서
  · 캐비닛별 무게와 소비전력 — 도면에 그대로 넣으실 수 있습니다
  · 시청 거리에 맞는 실내외 밝기 옵션

Allen Ma · Shenzhen Maxcolor Visual
Kakaotalk / WeChat +86 13570871001
"""),
]

ALLEN_STYLE_DM = [
    ("DM 工厂直供（英语）", "en",
     "Hi{contact_comma} this is Allen from Shenzhen Maxcolor Visual, an LED display "
     "manufacturer in Shenzhen. Indoor P2-P3, rental P2.6-P4.8 die-cast, outdoor P4-P10 "
     "at 5,500-8,000 nits. Happy to send the spec sheet for whichever pitch you use, "
     "whenever it is useful."),
    ("DM 工厂直供（韩语）", "ko",
     "안녕하세요~ 심천 LED 디스플레이 제조업체 맥스컬러의 Allen입니다. 실내 P2-P3, 렌탈 "
     "P2.6-P4.8 다이캐스팅, 실외 P4-P10(5,500-8,000 nits)까지 가능합니다. 쓰시는 사양에 "
     "맞는 사양서 기꺼이 보내드리겠습니다. 편하실 때 편하게 말씀 주세요~"),
]


def seed_templates(conn) -> int:
    """Add starter templates; skips any whose name already exists."""
    from app import repository
    existing = {t.name for t in repository.list_templates(conn)}
    added = 0
    for name, lang, subject, body in EMAIL_TEMPLATES:
        if name not in existing:
            repository.add_template(conn, name, "email", subject, body, lang)
            added += 1
    for name, lang, subject, body in ALLEN_STYLE_TEMPLATES:
        if name not in existing:
            repository.add_template(conn, name, "email", subject, body, lang)
            added += 1
    for name, lang, body in DM_TEMPLATES + ALLEN_STYLE_DM:
        for channel in ("whatsapp", "instagram"):
            full = f"{name} · {'WA' if channel == 'whatsapp' else 'IG'}"
            if full not in existing:
                repository.add_template(conn, full, channel, None, body, lang)
                added += 1
    return added


def seed_sequences(conn) -> list[int]:
    """Add the 3-step cold-email sequences (EN/KO); skips ones already there."""
    from app import sequences
    added = []
    for seq in EMAIL_SEQUENCES:
        if conn.execute("SELECT 1 FROM sequences WHERE name=?", (seq["name"],)).fetchone():
            continue
        added.append(sequences.create_sequence(conn, seq["name"], seq["channel"], seq["steps"]))
    return added

"""Ready-made templates and a follow-up sequence, loaded in one click.

The lead base has 800+ touches but zero saved templates and zero sequences: the
features exist, they just start from a blank page, so they never get used. These
seeds are Allen's actual outreach voice (factory-direct, no company name in DMs,
case photo attached) so the first send is one click, not one hour of typing.
"""

SIGNOFF = """Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com"""

OPT_OUT = 'If you\'d prefer not to receive these emails, just reply "unsubscribe" and I won\'t contact you again.'

# Korean business mail is its own register, not the English one translated. Three things
# it needs that a translation does not give you:
#   - the greeting addresses the company's 담당자 (the person in charge), not a first name.
#     Cold B2B mail in Korea rarely uses one, and {contact} falls back to "there", which
#     would render "안녕하세요, there님" — {name} is always present and reads correctly.
#   - 격식체 (-습니다/-십시오) throughout. Anything softer reads as a consumer ad.
#   - a Korean sign-off. A bare English block under Korean body text reads as a mass mail.
KO_SIGNOFF = """감사합니다.

Allen Ma | 해외영업
Shenzhen Maxcolor Visual Co., Ltd. (중국 선전)
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com"""

KO_OPT_OUT = ('메일 수신을 원하지 않으시면 "수신거부"라고 회신해 주십시오. '
              '이후로는 연락드리지 않겠습니다.')

EMAIL_TEMPLATES = [
    ("首次触达（英语）", "en", "LED Display Panels — Factory Direct from Shenzhen",
     f"""Hi {{contact}},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I came across {{name}} and your LED display work. We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing, and I've attached a sheet of recent projects.

If you have an upcoming LED display need, I can recommend options based on size, viewing distance, pixel pitch, and indoor/outdoor use.

{OPT_OUT}

{SIGNOFF}"""),
    ("跟进2：案例+提问（英语）", "en", "Re: LED Display Panels — quick question",
     f"""Hi {{contact}},

Following up on my note about LED panels for {{name}}.

Quick question so I don't waste your time: are you sourcing for a specific project right now, or keeping a supplier on file for when one comes up? Either answer is useful — I'll send what actually fits.

{OPT_OUT}

{SIGNOFF}"""),
    ("跟进3：最后一封（英语）", "en", "Re: LED Display Panels — closing the loop",
     f"""Hi {{contact}},

Last note from me — I don't want to clutter your inbox.

If LED displays aren't on your radar, no problem at all. If they come up later, my details are below and I'll send pricing the same day you ask.

{SIGNOFF}"""),
    ("首次触达（韩语）", "ko", "[LED 디스플레이] 중국 선전 제조사 직접 공급 안내",
     f"""안녕하세요, {{name}} 담당자님.

중국 선전에서 LED 디스플레이를 제조하는 Allen이라고 합니다.

{{name}}에서 LED 디스플레이를 취급하시는 것을 보고 연락드렸습니다. 저희는 실내외용 P0.7~P10 LED 패널을 제조사에서 직접 공급하고 있으며, 최근 납품 사례를 정리한 자료를 첨부해 드립니다.

검토 중이신 건이 있으시면 설치 환경과 화면 크기, 시야 거리에 맞춰 사양과 단가를 정리해 보내드리겠습니다.

당장 필요하지 않으시더라도 첨부 자료만 참고용으로 보관해 주시면 감사하겠습니다.

{KO_OPT_OUT}

{KO_SIGNOFF}"""),
    ("跟进2：案例+提问（韩语）", "ko", "Re: [LED 디스플레이] 진행 중인 건이 있으신지요",
     f"""안녕하세요, {{name}} 담당자님.

지난번 보내드린 LED 패널 건으로 다시 연락드립니다.

바쁘실 테니 한 가지만 여쭙겠습니다. 지금 구체적으로 진행 중인 프로젝트가 있으신가요, 아니면 필요하실 때를 대비해 거래처를 미리 알아보시는 단계이신가요?

어느 쪽인지만 알려주시면 그에 맞는 자료만 간단히 보내드리겠습니다. 답변이 어려우시면 이 메일은 넘기셔도 괜찮습니다.

{KO_OPT_OUT}

{KO_SIGNOFF}"""),
    ("跟进3：最后一封（韩语）", "ko", "Re: [LED 디스플레이] 마지막으로 인사드립니다",
     f"""안녕하세요, {{name}} 담당자님.

계속 메일을 드리는 것이 부담이 되실 것 같아 이번을 마지막으로 하겠습니다.

지금은 LED 디스플레이 도입 계획이 없으시더라도 전혀 괜찮습니다. 다만 나중에 필요하신 일이 생기면 아래 연락처로 편하게 문의해 주십시오. 요청 주신 날 안에 사양과 견적을 정리해 보내드리겠습니다.

그동안 시간 내주셔서 감사합니다.

{KO_SIGNOFF}"""),
]

# DM 规矩：不提公司名、只说 from Shenzhen China、必带案例图（发送端自动附图）
DM_TEMPLATES = [
    ("DM 首次触达（英语）", "en",
     "Hi {name}, this is Allen from an LED display factory in Shenzhen, China. We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing. Happy to share recent project references if you have upcoming LED display needs."),
    ("DM 首次触达（韩语）", "ko",
     "안녕하세요, {name} 담당자님. 중국 선전에서 LED 디스플레이를 만드는 Allen이라고 합니다. 실내외용 P0.7~P10 LED 패널을 제조사 직접 가격으로 공급하고 있습니다. 진행 중이거나 예정된 LED 건이 있으시면 최근 납품 사례 보내드리겠습니다."),
    ("DM 跟进（英语）", "en",
     "Hi {name}, following up on my last message. Are you working on an LED display project right now, or should I check back later? Either way, happy to send specs and pricing whenever it's useful."),
    ("DM 跟进（韩语）", "ko",
     "안녕하세요, {name} 담당자님. 지난번 보내드린 메시지 관련해 한 번만 더 여쭙습니다. 현재 진행 중인 LED 건이 있으신가요? 없으시면 나중에 필요하실 때 연락 주셔도 괜찮습니다. 사양과 단가는 언제든 정리해 드리겠습니다."),
]

def _by_lang(lang: str) -> dict[str, tuple[str, str]]:
    """{step_key: (subject, body)} for one language, keyed off the template names."""
    out = {}
    for name, tpl_lang, subject, body in EMAIL_TEMPLATES:
        if tpl_lang != lang:
            continue
        key = "first" if name.startswith("首次") else "f2" if name.startswith("跟进2") else "f3"
        out[key] = (subject, body)
    return out


# 冷邮件的回复几乎都在第 2–4 触，所以每个序列都是 3 步：第 0 / 3 / 8 天。
# 只留英语和韩语：韩国客户用韩语，其余市场一律英语。西语/葡语话术已下线——维护四套
# 文案的成本没有换来回复，而半吊子的本地化比一封干净的英文信更伤信任。
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


def seed_templates(conn) -> int:
    """Add the starter templates; skips any whose name already exists."""
    from app import repository
    existing = {t.name for t in repository.list_templates(conn)}
    added = 0
    for name, lang, subject, body in EMAIL_TEMPLATES:
        if name not in existing:
            repository.add_template(conn, name, "email", subject, body, lang)
            added += 1
    for name, lang, body in DM_TEMPLATES:
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

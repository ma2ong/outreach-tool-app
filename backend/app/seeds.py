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


def seed_templates(conn) -> int:
    """Add starter templates; skips any whose name already exists."""
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

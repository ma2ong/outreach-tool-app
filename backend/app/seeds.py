"""Ready-made templates and a follow-up sequence, loaded in one click.

The lead base has 800+ touches but zero saved templates and zero sequences: the
features exist, they just start from a blank page, so they never get used. These
seeds are Allen's actual outreach voice (factory-direct, no company name in DMs,
case photo attached) so the first send is one click, not one hour of typing.
"""

# 两种语言都照 Allen 实际在发、并且真有人读的那两封信来写，不套冷邮件公式。共同点：
#   - 有联系人名就叫名字（Hi Dave,），没有就只留 "Hi,"。原来 {contact} 缺失会兜底成
#     "there"，在大多数没有联系人名的客户上渲染成 "Hi there," —— 一眼就是群发。
#     兜底已改成留空，标点由 personalize 收拢。
#   - 第一句先给东西（交付案例），再谈需求。
#   - 写真实点距。P1.86 / P2.5 / P3.91 让对方看出我们真做过他要的东西，
#     笼统的 "P0.7–P10" 读起来像产品目录。
#   - 不写退订段落。Allen 的既有做法；回复里说要停的，由 replies._UNSUB_RE
#     识别（中英韩都覆盖）自动加入不再联系，不靠信里那一行。
SIGNOFF = """Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001"""

# 韩语不是把英文翻过去，是 Allen 实际发韩国客户那封信的写法：
#   - 先给价值再说自己是谁。开头就是「韩国交付案例分享」，不是公司自我介绍。
#   - 不称呼收件人。韩国冷邮件本来就少直呼名字，而且 {contact} 缺失时会兜底成英文
#     "there"，渲染出「안녕하세요, there님」——不写称呼直接绕开了这个坑。
#   - 列真实交付过的点距，不写笼统范围：韩国同行看 P1.53 / P1.86 认得出是行内人。
#   - 联系方式给 KakaoTalk。韩国客户不用 WhatsApp。
#   - 语气松弛（~ 和 !），不用격식체。过度郑重反而像模板群发。
KO_SIGNOFF = """Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
Kakaotalk / WeChat: +86 13570871001
Email: allenma2ong@gmail.com"""

EMAIL_TEMPLATES = [
    ("首次触达（英语）", "en", "Recent LED Display Projects — Shenzhen Maxcolor Visual",
     f"""Hi {{contact}},

I'd like to share some recent LED display projects we delivered in Korea.

We have completed various indoor and outdoor projects including P1.86, P2.5, P3.91, and P10 LED displays.

If you have any upcoming projects, please feel free to contact me anytime. We would be happy to recommend suitable products and provide you with competitive pricing based on your project needs.

Hope we can have a good opportunity to work together!

{SIGNOFF}"""),
    ("跟进2：案例+提问（英语）", "en", "Re: Recent LED Display Projects",
     f"""Hi {{contact}},

Just following up on the LED display projects I shared earlier.

Are you working on a specific project at the moment, or keeping a supplier on file for when one comes up? Either way, let me know and I'll send only what is actually useful to you.

Feel free to reply anytime.

{SIGNOFF}"""),
    ("跟进3：最后一封（英语）", "en", "Re: LED Displays — whenever you need them",
     f"""Hi {{contact}},

This is my last note — I don't want to fill up your inbox.

If LED displays aren't on your plan right now, no problem at all. Whenever a project comes up, just contact me anytime and I'll send specs and pricing the same day.

Hope we can work together some day!

{SIGNOFF}"""),
    ("首次触达（韩语）", "ko", "한국 LED 디스플레이 납품 사례 공유드립니다",
     f"""안녕하세요~

최근 저희가 한국에 납품한 LED 디스플레이 설치사례를 공유드립니다.
P1.53, P1.86, P2.5, P3.91, P10 등 실내/실외 다양한 프로젝트를 진행했습니다.

혹시 최근 검토 중이거나 진행 예정인 프로젝트가 있으면 편하게 연락 주세요.
현장 조건에 맞는 제품 추천과 좋은 조건으로 견적 드리겠습니다.

좋은 기회로 함께 협력할 수 있기를 바랍니다!

{KO_SIGNOFF}"""),
    ("跟进2：案例+提问（韩语）", "ko", "Re: 한국 LED 디스플레이 납품 사례",
     f"""안녕하세요~

지난번 보내드린 LED 디스플레이 설치사례 잘 보셨는지요.

혹시 지금 검토 중이신 현장이 있으실까요? 아니면 나중을 위해 공급처를 미리 알아두시는 단계이신지요.
어느 쪽이든 알려주시면 거기에 맞는 자료만 정리해서 보내드리겠습니다.

편하게 답 주세요~

{KO_SIGNOFF}"""),
    ("跟进3：最后一封（韩语）", "ko", "Re: 한국 LED 디스플레이 — 필요하실 때 언제든지",
     f"""안녕하세요~

계속 메일 드리기 조심스러워 이번까지만 연락드립니다.

지금 당장 필요하지 않으셔도 괜찮습니다. 나중에 LED 디스플레이 건이 생기면 언제든 편하게 연락 주세요.
문의 주시면 당일에 현장 조건에 맞는 사양과 견적 정리해서 보내드리겠습니다.

좋은 하루 보내세요!

{KO_SIGNOFF}"""),
]

# DM 规矩：不提公司名、只说 from Shenzhen China、必带案例图（发送端自动附图）
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

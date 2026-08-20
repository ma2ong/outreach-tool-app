"""
Message Crafter: 为单条 prospect 生成平台专属个性化消息
通过 `claude -p` 调用，使用用户的 Anthropic 订阅账号，无需 API Key
用法: python message_crafter.py  (直接运行则跑测试样本)
"""
import sys, os, json, subprocess, shlex
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

WORD_LIMITS = {
    "instagram": (40, 60),
    "facebook":  (50, 80),
    "whatsapp":  (30, 50),
}

SYSTEM_CONTEXT = """You are Allen Ma, an LED display industry professional at Maicai Visual in Shenzhen.
You're reaching out to fellow LED industry players — not as a factory salesman, but as a peer.

Background knowledge:
- Fine pitch indoor panels (P1.5–P3): high refresh rate, viewing distance, cabinet weight
- Outdoor fixed: IP rating, brightness (nits), wind load, power consumption
- Rental panels: quick-lock mechanism, carbon fiber vs aluminum cabinet, P2.6/P3.91/P4.81
- Korea wedding hall project: P2.5, 7680Hz refresh rate, excellent color uniformity
- Pixel pitch, refresh rate, brightness, contrast, scan mode, viewing angle

Tone: Peer-to-peer conversation, not a pitch. Curiosity-driven.

Hard rules:
- NEVER use: "I hope this message finds you well", "leading manufacturer", "best price", "factory direct", "wholesale", "competitive price", "dear sir", "dear friend"
- NEVER mention the recipient's company name — use "you", "your team", "your operation", "your setup" instead
- NO Chinese-style English
- NO mass-message patterns
- Max 1 emoji total
- End with a genuine question (not a CTA)
- Include at least 1 piece of specific information from the prospect's profile
- Sound like a human who actually looked at their account"""


def _call_claude(prompt: str) -> str:
    """通过 claude -p 调用，返回纯文本输出"""
    full_prompt = SYSTEM_CONTEXT + "\n\n---\n\n" + prompt

    result = subprocess.run(
        ["claude", "-p", full_prompt],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude 调用失败: {result.stderr.strip()}")
    return result.stdout.strip()


def craft_message(prospect: dict, platform: str) -> str:
    min_w, max_w = WORD_LIMITS.get(platform, (40, 60))

    source_hint = ""
    if platform == "whatsapp":
        if prospect.get("instagram"):
            source_hint = f"Mention you found them via Instagram (@{prospect['instagram']})."
        elif prospect.get("facebook"):
            source_hint = f"Mention you found them on Facebook."
        else:
            source_hint = "Mention you found their contact from their website or Google Maps."

    prompt = f"""Write a {platform.capitalize()} cold outreach message to this LED industry prospect.

Prospect profile:
- Company: {prospect.get('company_en', '')}
- City/Country: {prospect.get('city', '')}, {prospect.get('country', '')}
- Business: {prospect.get('business', '')}
- Platform handle: {prospect.get('username', '')}
- Phone: {prospect.get('phone_whatsapp', '') if platform == 'whatsapp' else '(not shown)'}

{source_hint}

Requirements:
- Length: {min_w}–{max_w} words
- Platform: {platform}
- Reference at least 1 specific detail from their business description
- End with a genuine industry question (not "contact us" or "check our catalog")
- No pleasantries opener
- NEVER name the recipient's company — use "you", "your team", "your setup", "your operation" instead
- If their business mentions rental, ask about panel size or cabinet type they use
- If fixed install, ask about pixel pitch or viewing distance
- If general LED sales, ask about their main market or product focus

Write ONLY the message text. No subject line, no label, no explanation."""

    return _call_claude(prompt)


def craft_followup(prospect: dict, platform: str, original_message: str) -> str:
    """生成跟进消息（72小时无回复后）"""
    min_w, max_w = WORD_LIMITS.get(platform, (40, 60))

    prompt = f"""Write a short follow-up message for this LED prospect who hasn't replied.

Original message sent:
{original_message}

Prospect: {prospect.get('company_en', '')} in {prospect.get('country', '')}
Business: {prospect.get('business', '')}

Requirements:
- Length: {min_w - 10}–{min_w + 5} words (shorter than original)
- Don't repeat the same question
- New angle: mention a specific LED application relevant to their market, or ask about a pain point
- Completely different opening from the original
- End with a yes/no question to lower friction

Write ONLY the message text."""

    return _call_claude(prompt)


def craft_reply_response(prospect: dict, platform: str, their_reply: str, intent: str) -> str:
    """
    生成对回复的响应
    intent: 'hot' (询价/规格) | 'warm' (要资料) | 'cold' (拒绝)
    """
    if intent == "cold":
        return ""

    if intent == "hot":
        intent_instruction = "HOT lead — they want pricing or specs. Acknowledge their need, suggest a specific product angle matching their business, mention the Korea P2.5 wedding hall project as a reference (7680Hz refresh), propose to move to WhatsApp or Zoom for detailed discussion."
    else:
        intent_instruction = "WARM lead — they want more info. Keep it brief, tell them you'll send a catalog or spec sheet, ask one clarifying question about their typical project size or market."

    prompt = f"""The prospect replied to my LED outreach message. Write my response.

Prospect: {prospect.get('company_en', '')} in {prospect.get('country', '')}
Business: {prospect.get('business', '')}
Their reply: "{their_reply}"

{intent_instruction}

Requirements:
- Conversational, not templated
- Under 80 words
- End with a clear next step

Write ONLY the message text."""

    return _call_claude(prompt)


if __name__ == "__main__":
    test_prospects = [
        {
            "company_en": "LedWave",
            "city": "São Paulo",
            "country": "Brazil",
            "business": "LED panel sales, rental, OOH media; B Corp certified",
            "username": "ledwave",
            "instagram": "ledwave",
            "facebook": "ledwavesaopaulo",
            "phone_whatsapp": "+55 11 3044-4609",
        },
        {
            "company_en": "PubliMaster Colombia",
            "city": "Medellín",
            "country": "Colombia",
            "business": "LED screen importer & commercializer; events/indoor/outdoor advertising",
            "username": "publimastersj",
            "instagram": "publimastersj",
            "facebook": "publimasterSJ",
            "phone_whatsapp": "+57 311 2419363",
        },
    ]

    for p in test_prospects:
        print(f"\n{'='*60}")
        print(f"Company: {p['company_en']} ({p['country']})")
        for platform in ("instagram", "facebook", "whatsapp"):
            print(f"\n--- {platform.upper()} ---")
            print("生成中...", end=" ", flush=True)
            try:
                msg = craft_message(p, platform)
                print(f"✓ ({len(msg.split())} 词)")
                print(msg)
            except Exception as e:
                print(f"✗ {e}")

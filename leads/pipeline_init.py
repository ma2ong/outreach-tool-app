"""
初始化 pipeline：从所有版本脚本提取 leads，按平台分类写入 prospects.json
运行一次即可；后续状态由 daily_runner.py 维护。
"""
import ast, re, os, json
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
PIPELINE = os.path.join(BASE, "pipeline")


def load_all_leads():
    v4_src = open(os.path.join(BASE, "generate_led_leads_v4.py"), encoding="utf-8").read()
    leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", v4_src, re.M | re.S).group(1))
    for v in ("v5","v6","v7","v8","v9","v10","v11","v12","v13","v14","v15","v16","v17"):
        path = os.path.join(BASE, f"generate_led_leads_{v}.py")
        if not os.path.exists(path):
            continue
        src = open(path, encoding="utf-8").read()
        m = re.search(r"^new_entries = (\[.+?^\])", src, re.M | re.S)
        if m:
            leads.extend(ast.literal_eval(m.group(1)))
    return leads


def extract_username(url_or_username):
    """从 'instagram.com/username' 或 'username' 提取纯用户名"""
    if not url_or_username:
        return ""
    s = url_or_username.strip().rstrip("/")
    # 移除协议和域名部分
    for prefix in ("https://", "http://", "www.", "instagram.com/", "facebook.com/", "linkedin.com/company/", "linkedin.com/in/"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s.strip("/")


def extract_phone(phone_str):
    """提取第一个电话号码（可能有多个用 / 分隔）"""
    if not phone_str:
        return ""
    return phone_str.split("/")[0].strip()


def build_prospect(lead, platform):
    """构建 prospect 记录，添加 pipeline 状态字段"""
    username = extract_username(lead.get(platform, ""))
    if not username:
        return None

    return {
        # 原始 lead 数据
        "no": lead.get("no"),
        "country": lead.get("country"),
        "region": lead.get("region"),
        "company_en": lead.get("company_en"),
        "company_local": lead.get("company_local", ""),
        "city": lead.get("city", ""),
        "email": lead.get("email", ""),
        "phone_whatsapp": extract_phone(lead.get("phone_whatsapp", "")),
        "website": lead.get("website", ""),
        "business": lead.get("business", ""),
        "instagram": extract_username(lead.get("instagram", "")),
        "facebook": extract_username(lead.get("facebook", "")),
        # 该平台字段
        "platform": platform,
        "username": username,
        # pipeline 状态
        "status": "prospect",          # prospect → warmed → messaged → replied
        "warmup_done": False,
        "warmup_date": None,
        "message_sent_date": None,
        "message_text": None,
        "reply_received": False,
        "reply_date": None,
        "reply_text": None,
        "lead_score": None,            # hot / warm / cold
        "touch_count": 0,              # 触达次数，最多2次
        "added_date": datetime.now().strftime("%Y-%m-%d"),
        "notes": "",
    }


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    leads = load_all_leads()
    print(f"Total leads loaded: {len(leads)}")

    ig_prospects = []
    fb_prospects = []
    wa_prospects = []
    seen_ig = set()
    seen_fb = set()

    for lead in leads:
        ig_user = extract_username(lead.get("instagram", ""))
        fb_user = extract_username(lead.get("facebook", ""))
        phone = extract_phone(lead.get("phone_whatsapp", ""))

        if ig_user and ig_user not in seen_ig:
            p = build_prospect(lead, "instagram")
            if p:
                ig_prospects.append(p)
                seen_ig.add(ig_user)

        if fb_user and fb_user not in seen_fb:
            p = build_prospect(lead, "facebook")
            if p:
                fb_prospects.append(p)
                seen_fb.add(fb_user)

        # WhatsApp: 只收录有明确 +非86 号码的
        if phone and not phone.startswith("+86") and not phone.startswith("86"):
            wa_prospects.append({
                "no": lead.get("no"),
                "country": lead.get("country"),
                "company_en": lead.get("company_en"),
                "city": lead.get("city", ""),
                "business": lead.get("business", ""),
                "phone": phone,
                "website": lead.get("website", ""),
                "instagram": ig_user,
                "facebook": fb_user,
                "platform": "whatsapp",
                "username": phone,
                "status": "prospect",
                "touch_count": 0,
                "message_sent_date": None,
                "added_date": datetime.now().strftime("%Y-%m-%d"),
            })

    # 写入各平台 prospects.json
    write_json(os.path.join(PIPELINE, "instagram", "prospects.json"), ig_prospects)
    write_json(os.path.join(PIPELINE, "facebook", "prospects.json"), fb_prospects)
    write_json(os.path.join(PIPELINE, "whatsapp", "prospects.json"), wa_prospects)

    # 初始化空文件
    for platform in ("instagram", "facebook", "whatsapp"):
        for fname in ("warmed.json", "messaged.json", "replies.json"):
            path = os.path.join(PIPELINE, platform, fname)
            if not os.path.exists(path):
                write_json(path, [])

    write_json(os.path.join(PIPELINE, "blacklist.json"), [])
    write_json(os.path.join(PIPELINE, "hot_leads.json"), [])

    print(f"Instagram prospects: {len(ig_prospects)}")
    print(f"Facebook prospects:  {len(fb_prospects)}")
    print(f"WhatsApp prospects:  {len(wa_prospects)}")
    print(f"\nPipeline initialized at: {PIPELINE}")


if __name__ == "__main__":
    main()

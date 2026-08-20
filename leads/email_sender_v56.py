"""
Email sender v56 - verified USA LED display batch.
Sends Korea project case image and records results in pipeline/email/prospects.json.
"""
import datetime
import json
import os
import random
import smtplib
import sys
import time
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent
EMAIL_PIPELINE = BASE / "pipeline/email/prospects.json"
TODAY = datetime.date.today().isoformat()

GMAIL_USER = "allenma2ong@gmail.com"
_pw_file = Path.home() / ".gmail_app_password"
GMAIL_APP_PASSWORD = (
    os.environ.get("GMAIL_APP_PASSWORD")
    or (_pw_file.read_text(encoding="utf-8").strip() if _pw_file.exists() else "")
)
ATTACHMENT = Path(r"C:\Users\Administrator\Desktop\korea-led-projects-poster-4k.jpg")

SUBJECT = "Recent LED Display Projects - Shenzhen Maxcolor Visual"
BODY_TEMPLATE = """\
Hi {name},

I'd like to share some recent LED display projects we delivered in Korea.

We have completed various indoor and outdoor projects including P1.86, P2.5, P3.91, and P10 LED displays.

If you have any upcoming projects, please feel free to contact me anytime.

We would be happy to recommend suitable products and provide you with competitive pricing based on your project needs.

Hope we can have a good opportunity to work together!

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

TARGETS = [
    {"no": 759, "company_en": "Eden USA", "email": "sales@edenusa.com", "name": "Eden USA Team", "city": "Corona / Los Angeles, CA"},
    {"no": 760, "company_en": "EuroLedwall USA", "email": "info@euroledwallusa.com", "name": "EuroLedwall Team", "city": "Los Angeles, CA"},
    {"no": 761, "company_en": "Fidelis Sound & Lighting", "email": "info@fidelisatx.com", "name": "Fidelis Team", "city": "Austin, TX"},
    {"no": 762, "company_en": "AV America Florida", "email": "info@av-america.com", "name": "AV America Team", "city": "Orlando / Miami, FL"},
    {"no": 763, "company_en": "Digital Art Video", "email": "production@digitalartvideo.com", "name": "Digital Art Video Team", "city": "New York, NY"},
    {"no": 764, "company_en": "One World Rental USA", "email": "sales@oneworldrental.com", "name": "One World Rental Team", "city": "Phoenix / USA nationwide"},
    {"no": 765, "company_en": "Los Angeles LED Video Walls", "email": "info@losangelesledvideowalls.com", "name": "Los Angeles LED Video Walls Team", "city": "Los Angeles, CA"},
    {"no": 766, "company_en": "Pixals LED Screen Rental Los Angeles", "email": "hello@pixals.net", "name": "Pixals Team", "city": "Los Angeles, CA"},
    {"no": 767, "company_en": "Los Angeles Video Walls", "email": "info@ledwallrentallosangeles.com", "name": "Los Angeles Video Walls Team", "city": "Los Angeles, CA"},
    {"no": 768, "company_en": "SergeiSolutions", "email": "info@sergeisolutions.com", "name": "SergeiSolutions Team", "city": "Los Angeles, CA"},
]


def load_pipeline():
    with open(EMAIL_PIPELINE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_pipeline(data):
    with open(EMAIL_PIPELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def already_sent(no):
    return any(row.get("no") == no and row.get("status") == "messaged" for row in load_pipeline())


def mark_sent(target):
    data = load_pipeline()
    for row in data:
        if row.get("no") == target["no"]:
            row.update({
                "status": "messaged",
                "touch_count": max(int(row.get("touch_count") or 0), 1),
                "message_sent_date": TODAY,
                "message_channel": "email",
                "target_fit": "verified_led_display",
                "do_not_contact": False,
                "email": target["email"],
                "company_en": target["company_en"],
                "country": "USA",
            })
            break
    else:
        data.append({
            "no": target["no"],
            "company_en": target["company_en"],
            "country": "USA",
            "email": target["email"],
            "status": "messaged",
            "touch_count": 1,
            "message_sent_date": TODAY,
            "message_channel": "email",
            "target_fit": "verified_led_display",
            "do_not_contact": False,
        })
    save_pipeline(data)


def send_email(target):
    msg = MIMEMultipart("mixed")
    msg["Subject"] = SUBJECT
    msg["From"] = GMAIL_USER
    msg["To"] = target["email"]
    msg.attach(MIMEText(BODY_TEMPLATE.format(name=target["name"]), "plain", "utf-8"))
    if ATTACHMENT.exists():
        with open(ATTACHMENT, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{ATTACHMENT.name}"')
        msg.attach(part)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, target["email"], msg.as_bytes())


def main():
    if not GMAIL_APP_PASSWORD:
        print("ERROR: Gmail app password missing.", flush=True)
        return
    print(f"=== Email Sender v56 | {len(TARGETS)} USA verified LED targets | {TODAY} ===", flush=True)
    sent = 0
    for idx, target in enumerate(TARGETS, 1):
        print(f"\n[{idx}/{len(TARGETS)}] no:{target['no']} {target['company_en']} -> {target['email']}", flush=True)
        if already_sent(target["no"]):
            print("  SKIP: already sent", flush=True)
            continue
        try:
            send_email(target)
        except Exception as exc:
            print(f"  FAILED: {exc}", flush=True)
        else:
            mark_sent(target)
            sent += 1
            print("  SENT", flush=True)
        if idx < len(TARGETS):
            wait = random.randint(18, 35)
            print(f"  waiting {wait}s...", flush=True)
            time.sleep(wait)
    print(f"\n=== Done: {sent}/{len(TARGETS)} sent ===", flush=True)


if __name__ == "__main__":
    main()

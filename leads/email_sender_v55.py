"""
Email sender v55 - USA batch (8 companies)
Attaches Korea project case image and records sends in pipeline/email/prospects.json.
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
    {"no": 751, "company_en": "Live Light Inc.", "email": "info@livelightent.com", "name": "Live Light Team", "city": "Fresno, CA"},
    {"no": 752, "company_en": "Freedom Fun USA Oklahoma City", "email": "okc@freedomfunusa.com", "name": "Freedom Fun OKC Team", "city": "Oklahoma City, OK"},
    {"no": 753, "company_en": "KEAR Media", "email": "mykearmedia@gmail.com", "name": "KEAR Media Team", "city": "Boise, ID"},
    {"no": 754, "company_en": "All Things Audio Visual", "email": "info@allthingsaudiovisual.com", "name": "All Things Audio Visual Team", "city": "Boise, ID"},
    {"no": 755, "company_en": "Colossal Productions", "email": "Colossalproductionsllc@gmail.com", "name": "Colossal Productions Team", "city": "Knoxville, TN"},
    {"no": 756, "company_en": "Strategic Integrated Systems", "email": "info@strategic.is", "name": "Strategic Integrated Systems Team", "city": "Knoxville, TN"},
    {"no": 757, "company_en": "Anytime Party Machines USA", "email": "info@anytimepartymachinesusa.com", "name": "Anytime Party Machines Team", "city": "Atlanta / Knoxville / Nashville"},
    {"no": 758, "company_en": "SkySlate Signs", "email": "sales@skyslate.com", "name": "SkySlate Team", "city": "Oklahoma City, OK"},
]


def load_pipeline():
    with open(EMAIL_PIPELINE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_pipeline(data):
    with open(EMAIL_PIPELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_already_sent(no):
    return any(p.get("no") == no and p.get("status") == "messaged" for p in load_pipeline())


def mark_sent(target):
    data = load_pipeline()
    for row in data:
        if row.get("no") == target["no"]:
            row.update({
                "status": "messaged",
                "touch_count": max(int(row.get("touch_count") or 0), 1),
                "message_sent_date": TODAY,
                "message_channel": "email",
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
    else:
        print(f"  WARNING: attachment missing: {ATTACHMENT}", flush=True)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, target["email"], msg.as_bytes())


def main():
    if not GMAIL_APP_PASSWORD:
        print("ERROR: Gmail app password missing.", flush=True)
        return

    print(f"=== Email Sender v55 | {len(TARGETS)} USA targets | {TODAY} ===", flush=True)
    sent = 0
    for idx, target in enumerate(TARGETS, 1):
        print(f"\n[{idx}/{len(TARGETS)}] no:{target['no']} {target['company_en']} -> {target['email']}", flush=True)
        if is_already_sent(target["no"]):
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
            wait = random.randint(20, 45)
            print(f"  waiting {wait}s...", flush=True)
            time.sleep(wait)
    print(f"\n=== Done: {sent}/{len(TARGETS)} sent ===", flush=True)


if __name__ == "__main__":
    main()

"""
Email sender v58 - verified USA LED display batch.
Attaches the latest recent Korea projects poster.
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
PIPELINE = BASE / "pipeline/email/prospects.json"
TODAY = datetime.date.today().isoformat()
GMAIL_USER = "allenma2ong@gmail.com"
PW_FILE = Path.home() / ".gmail_app_password"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD") or (
    PW_FILE.read_text(encoding="utf-8").strip() if PW_FILE.exists() else ""
)
ATTACHMENT = Path(r"C:\Users\Administrator\Desktop\Recent-led-projects-poster-4k.jpg")

SUBJECT = "Recent LED Display Installations in Korea"
BODY_TEMPLATE = """\
Hi {name},

I found your LED display / LED video wall work and wanted to share a recent reference from Korea.

The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you have upcoming LED display projects, I can help recommend panel options based on screen size, viewing distance, installation method, and indoor/outdoor use.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

TARGETS = [
    {"no": 775, "company_en": "HV ALL IN SOLUTIONS", "email": "Info@hvledusa.com", "name": "HV ALL IN SOLUTIONS Team"},
    {"no": 776, "company_en": "EAV Pro", "email": "info@eavpro.com", "name": "EAV Pro Team"},
    {"no": 777, "company_en": "LED Media Group", "email": "info@ledmediagroup.com", "name": "LED Media Group Team"},
    {"no": 779, "company_en": "Intela USA", "email": "contact@intelaus.com", "name": "Intela USA Team"},
]


def load_pipeline():
    return json.load(open(PIPELINE, encoding="utf-8"))


def save_pipeline(data):
    json.dump(data, open(PIPELINE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def already_sent(no):
    return any(row.get("no") == no and row.get("status") == "messaged" for row in load_pipeline())


def mark_sent(target):
    data = load_pipeline()
    payload = {
        "no": target["no"],
        "company_en": target["company_en"],
        "country": "USA",
        "email": target["email"],
        "status": "messaged",
        "touch_count": 1,
        "message_sent_date": TODAY,
        "message_channel": "email",
        "target_fit": "verified_led_display",
        "attachment": str(ATTACHMENT),
    }
    for row in data:
        if row.get("no") == target["no"]:
            row.update(payload)
            break
    else:
        data.append(payload)
    save_pipeline(data)


def send_email(target):
    msg = MIMEMultipart("mixed")
    msg["Subject"] = SUBJECT
    msg["From"] = GMAIL_USER
    msg["To"] = target["email"]
    msg.attach(MIMEText(BODY_TEMPLATE.format(name=target["name"]), "plain", "utf-8"))
    if not ATTACHMENT.exists():
        raise FileNotFoundError(f"Missing attachment: {ATTACHMENT}")
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
    print(f"=== Email Sender v58 | {len(TARGETS)} targets | {TODAY} ===", flush=True)
    sent = 0
    for idx, target in enumerate(TARGETS, 1):
        print(f"\n[{idx}/{len(TARGETS)}] no:{target['no']} {target['company_en']} -> {target['email']}", flush=True)
        if already_sent(target["no"]):
            print("  SKIP: already sent", flush=True)
            continue
        try:
            send_email(target)
            mark_sent(target)
            sent += 1
            print("  SENT", flush=True)
        except Exception as exc:
            print(f"  FAILED: {exc}", flush=True)
        if idx < len(TARGETS):
            wait = random.randint(16, 28)
            print(f"  waiting {wait}s...", flush=True)
            time.sleep(wait)
    print(f"\n=== Done: {sent}/{len(TARGETS)} sent ===", flush=True)


if __name__ == "__main__":
    main()

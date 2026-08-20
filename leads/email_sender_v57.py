"""
Email sender v57 - verified USA LED display batch.
Uses the latest recent Korea projects poster as attachment.
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
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD") or (
    _pw_file.read_text(encoding="utf-8").strip() if _pw_file.exists() else ""
)
ATTACHMENT = Path(r"C:\Users\Administrator\Desktop\Recent-led-projects-poster-4k.jpg")

SUBJECT = "Recent LED Display Installations in Korea"
BODY_TEMPLATE = """\
Hi {name},

I'm reaching out because your work is closely related to LED video walls and LED screen projects.

I attached a recent Korea project reference with indoor fine-pitch LED walls, outdoor LED screens, creative columns, and commercial LED installations.

If you have upcoming LED display projects, I would be glad to recommend suitable panel options based on the size, viewing distance, indoor/outdoor environment, and installation method.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

TARGETS = [
    {"no": 771, "company_en": "Smart LED Inc.", "email": "sergio@smartledinc.com", "name": "Sergio"},
    {"no": 773, "company_en": "Unity Logics", "email": "info@unitylogics.com", "name": "Unity Logics Team"},
    {"no": 774, "company_en": "Show Production Miami", "email": "info@showproductionmiami.com", "name": "Show Production Miami Team"},
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
                "email": target["email"],
                "company_en": target["company_en"],
                "country": "USA",
                "attachment": str(ATTACHMENT),
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
            "attachment": str(ATTACHMENT),
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
        print(f"  WARNING: missing attachment: {ATTACHMENT}", flush=True)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, target["email"], msg.as_bytes())


def main():
    if not GMAIL_APP_PASSWORD:
        print("ERROR: Gmail app password missing.", flush=True)
        return
    print(f"=== Email Sender v57 | {len(TARGETS)} targets | {TODAY} ===", flush=True)
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

"""
Email sender v37 - USA new cities batch (7 companies)
Chicago x3, Dallas, Denver, Seattle, Boston
"""
import json, sys, time, random, datetime, smtplib, os
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent
EMAIL_PIPELINE = BASE / "pipeline/email/prospects.json"
TODAY = datetime.date.today().isoformat()

GMAIL_USER = "allenma2ong@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
ATTACHMENT = Path(r"C:\Users\Administrator\Desktop\korea-led-projects-poster-4k.jpg")

SUBJECT = "Recent LED Display Projects — Shenzhen Maxcolor Visual"

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
    {"no": 626, "company_en": "Vantage Production Group", "email": "info@vantagepg.com",     "name": "Vantage Team",    "city": "Chicago, IL"},
    {"no": 627, "company_en": "Chicago Audio & Lighting",  "email": "chicagoavrentals@gmail.com", "name": "Chicago AV Team", "city": "Schaumburg, IL"},
    {"no": 628, "company_en": "Insane Impact",             "email": "Dsteffen@insaneimpact.com",  "name": "D. Steffen",      "city": "Chicago, IL"},
    {"no": 629, "company_en": "CMG Visuals",               "email": "sales@cmgvisuals.com",       "name": "CMG Visuals Team","city": "Dallas, TX"},
    {"no": 630, "company_en": "Denver Display",            "email": "support@denverdisplay.com",  "name": "Denver Display Team", "city": "Denver, CO"},
    {"no": 631, "company_en": "Seattle Video Wall",        "email": "hello@seattlevideowall.com", "name": "Seattle Video Wall Team", "city": "Seattle, WA"},
    {"no": 632, "company_en": "Boston Audio Rentals",      "email": "info@BostonAudioRentals.com","name": "Boston AV Team",  "city": "Norwood, MA"},
]


def send_email(to_email: str, name: str) -> bool:
    body = BODY_TEMPLATE.format(name=name)

    msg = MIMEMultipart("mixed")
    msg["Subject"] = SUBJECT
    msg["From"] = GMAIL_USER
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain", "utf-8"))

    if ATTACHMENT.exists():
        with open(ATTACHMENT, "rb") as f:
            part = MIMEBase("image", "jpeg")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename="LED-Display-Projects-Maxcolor-Visual.jpg")
        msg.attach(part)
    else:
        print(f"  ⚠ Attachment not found: {ATTACHMENT}", flush=True)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"  ✗ SMTP error: {e}", flush=True)
        return False


def mark_sent(no: int, email: str, company: str):
    data = json.load(open(EMAIL_PIPELINE, encoding="utf-8"))
    for p in data:
        if p.get("no") == no or p.get("email") == email:
            p["status"] = "messaged"
            p["touch_count"] = p.get("touch_count", 0) + 1
            p["email_sent_date"] = TODAY
            p["message_sent_date"] = TODAY
            p["message_channel"] = "email"
            print(f"  → pipeline updated: {company}", flush=True)
            with open(EMAIL_PIPELINE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return
    # New entry
    new_entry = {
        "no": no,
        "company_en": company,
        "email": email,
        "country": "USA",
        "status": "messaged",
        "touch_count": 1,
        "email_sent_date": TODAY,
        "added_date": TODAY,
        "message_sent_date": TODAY,
        "message_channel": "email",
    }
    data.append(new_entry)
    with open(EMAIL_PIPELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  → pipeline new entry: {company}", flush=True)


def main():
    if not GMAIL_APP_PASSWORD:
        print("✗ GMAIL_APP_PASSWORD not set. Run:")
        print('  $env:GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"; python email_sender_v37.py')
        return

    print(f"=== Email Sender v37 | {len(TARGETS)} USA companies | {TODAY} ===\n", flush=True)

    sent = 0
    for i, t in enumerate(TARGETS, 1):
        print(f"[{i}/{len(TARGETS)}] {t['company_en']} ({t['city']})", flush=True)
        print(f"  To: {t['email']}", flush=True)
        ok = send_email(t["email"], t["name"])
        if ok:
            mark_sent(t["no"], t["email"], t["company_en"])
            sent += 1
            print(f"  ✓ SENT\n", flush=True)
        else:
            print(f"  ✗ FAILED\n", flush=True)
        if i < len(TARGETS):
            wait = random.randint(45, 90)
            print(f"  waiting {wait}s...\n", flush=True)
            time.sleep(wait)

    print(f"=== Done: {sent}/{len(TARGETS)} emails sent ===")


if __name__ == "__main__":
    main()

"""
Email sender v43 — USA v43 batch (6 companies)
Raleigh NC: Triangle Media Solutions
Knoxville TN: The Production Source
Charlottesville VA: The AV Company
New Orleans LA: Power On Productions
Madison WI: Hinckley Productions
DeForest WI: STAR Studios LLC
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
    {"no": 657, "company_en": "Triangle Media Solutions", "email": "admin@trianglemediasolutions.com", "name": "Triangle Media Team",    "city": "Raleigh, NC"},
    {"no": 658, "company_en": "The Production Source",    "email": "info@theproductionsource.net",    "name": "Production Source Team", "city": "Knoxville, TN"},
    {"no": 659, "company_en": "The AV Company",           "email": "info@theavcompany.net",           "name": "AV Company Team",        "city": "Charlottesville, VA"},
    {"no": 660, "company_en": "Power On Productions",     "email": "info@poweronav.com",              "name": "Power On Team",          "city": "New Orleans, LA"},
    {"no": 661, "company_en": "Hinckley Productions",     "email": "info@hinckleyproductions.com",    "name": "Hinckley Team",          "city": "Madison, WI"},
    {"no": 662, "company_en": "STAR Studios LLC",          "email": "sales@starstudioswi.com",        "name": "STAR Studios Team",      "city": "DeForest, WI"},
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
        if p.get("no") == no:
            p["status"] = "messaged"
            p["touch_count"] = p.get("touch_count", 0) + 1
            p["email_sent_date"] = TODAY
            p["message_sent_date"] = TODAY
            p["message_channel"] = "email"
            print(f"  → pipeline updated: {company}", flush=True)
            with open(EMAIL_PIPELINE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return
    print(f"  ⚠ not found in pipeline: no={no}", flush=True)


def main():
    if not GMAIL_APP_PASSWORD:
        print("✗ GMAIL_APP_PASSWORD not set. Run:")
        print('  $env:GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"; python email_sender_v43.py')
        return
    print(f"=== Email Sender v43 | {len(TARGETS)} USA companies | {TODAY} ===\n", flush=True)
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

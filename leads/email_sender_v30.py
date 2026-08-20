"""
Email sender - USA batch v30
Sends English intro email to US LED companies (nos 568-573 with emails)
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

PERSONALIZATION = {
    "info@airbornevisuals.com": {
        "name": "Airborne Visuals Team",
        "note": "Your pre-configured LED booth kits for Las Vegas, Orlando, Chicago, and NYC trade shows are impressive. We manufacture modular P2.5–P4 LED tiles designed for exactly these fast-setup trade show booth configurations.",
    },
    "info@geoevent.net": {
        "name": "GeoEvent Team",
        "note": "We saw your inventory of 1000s of LED tiles for West Coast production — tours, corporate shows, and esports events. We supply P1.9–P3.9 LED panels in large quantities to rental companies at your scale.",
    },
    "sales@bouncemultimedia.com": {
        "name": "Bounce Multimedia Team",
        "note": "We noticed your NovaStar-based LED wall systems and 1500 sq ft studio facility in Houston. We supply Novastar-compatible LED tiles and have been working with Houston-area production companies for event rental.",
    },
    "info@trueblue-exhibits.com": {
        "name": "TrueBlue Exhibits Team",
        "note": "Your factory-direct LED wall program for trade shows across Las Vegas, NYC, Orlando, and Chicago caught our attention. We manufacture the LED panels behind similar trade show packages and can offer direct pricing.",
    },
}

TARGET_EMAILS = [
    "info@airbornevisuals.com",
    "info@geoevent.net",
    "sales@bouncemultimedia.com",
    "info@trueblue-exhibits.com",
]


def send_email(to_email: str) -> bool:
    pers = PERSONALIZATION.get(to_email, {})
    name = pers.get("name", "Team")
    note = pers.get("note", "We supply LED panels to AV rental and event production companies in the US.")
    body = BODY_TEMPLATE.format(name=name, personalized_note=note)

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

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.sendmail(GMAIL_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"  ✗ SMTP error: {e}", flush=True)
        return False


def mark_sent(email: str):
    data = json.load(open(EMAIL_PIPELINE, encoding="utf-8"))
    for p in data:
        if p.get("email") == email:
            p["status"] = "messaged"
            p["email_sent_date"] = TODAY
            p["touch_count"] = p.get("touch_count", 0) + 1
            break
    with open(EMAIL_PIPELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  → pipeline 已更新: {email} status=messaged", flush=True)


def main():
    if not GMAIL_APP_PASSWORD:
        print("ERROR: GMAIL_APP_PASSWORD environment variable not set")
        print("Usage: GMAIL_APP_PASSWORD='xxxx xxxx xxxx xxxx' python email_sender_v30.py")
        return

    data = json.load(open(EMAIL_PIPELINE, encoding="utf-8"))
    sent_emails = {p["email"] for p in data if p.get("status") == "messaged"}

    queue = [e for e in TARGET_EMAILS if e not in sent_emails]

    print(f"=== Email Sender USA v30 | {len(queue)} emails | {TODAY} ===\n", flush=True)

    if not queue:
        print("全部已发送")
        return

    sent = 0
    for i, email in enumerate(queue, 1):
        p_data = next((p for p in data if p.get("email") == email), {})
        pers = PERSONALIZATION.get(email, {})
        name = pers.get("name", "Team")

        print(f"[{i}/{len(queue)}] {email} | {p_data.get('company_en', '')}", flush=True)
        print(f"  To: {name}", flush=True)

        ok = send_email(email)
        if ok:
            mark_sent(email)
            sent += 1
            print(f"  ✓ SENT\n", flush=True)
        else:
            print(f"  ✗ FAILED\n", flush=True)

        if i < len(queue):
            wait = random.randint(45, 90)
            print(f"  waiting {wait}s...", flush=True)
            time.sleep(wait)

    print(f"\n=== Done: {sent}/{len(queue)} emails sent ===")


if __name__ == "__main__":
    main()

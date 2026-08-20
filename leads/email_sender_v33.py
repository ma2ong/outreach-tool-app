"""
Email Sender v33 — USA v33 batch (nos 588-593, 6 companies with email)
Special FX Rentals, AB AV Rentals, Atlanta Pro AV, Technical Elements,
Rayne Events, Promosa
Attachment: korea-led-projects-poster-4k.jpg
"""
import smtplib, json, time, datetime, sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

GMAIL_USER = "allenma2ong@gmail.com"
GMAIL_APP_PW = "oghn yyxr vtgw niwh"
ATTACHMENT = Path(r"C:\Users\Administrator\Desktop\korea-led-projects-poster-4k.jpg")

EMAIL_PIPELINE = Path(__file__).parent / "pipeline/email/prospects.json"
TODAY = datetime.date.today().isoformat()

SUBJECT = "Recent LED Display Projects — Shenzhen Maxcolor Visual"

TARGETS = [
    {"no": 588, "to": "Info@SpecialFXRentals.com", "name": ""},
    {"no": 589, "to": "Allen@abavrentals.com", "name": "Allen"},
    {"no": 590, "to": "info@atlantaproav.com", "name": ""},
    {"no": 591, "to": "info@teatlanta.com", "name": ""},
    {"no": 592, "to": "info@rayneevents.com", "name": ""},
    {"no": 593, "to": "info@promosa.com", "name": ""},
]

BODY_TEMPLATE = """\
Hi{name_part},

I'd like to share some recent LED display projects we delivered in Korea.

We have completed various indoor and outdoor projects including P1.86, P2.5, P3.91, and P10 LED displays.

If you have any upcoming projects, please feel free to contact me anytime. We would be happy to recommend suitable products and provide you with competitive pricing based on your project needs.

Hope we can have a good opportunity to work together!

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
"""


def send_email(to_addr: str, name: str, no: int) -> bool:
    name_part = f" {name}" if name else ""
    body = BODY_TEMPLATE.replace("{name_part}", name_part)

    msg = MIMEMultipart("mixed")
    msg["From"] = GMAIL_USER
    msg["To"] = to_addr
    msg["Subject"] = SUBJECT
    msg.attach(MIMEText(body, "plain", "utf-8"))

    if ATTACHMENT.exists():
        with open(ATTACHMENT, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{ATTACHMENT.name}"')
        msg.attach(part)
    else:
        print(f"  ⚠ attachment not found: {ATTACHMENT}", flush=True)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PW)
            server.sendmail(GMAIL_USER, to_addr, msg.as_bytes())
        return True
    except Exception as e:
        print(f"  ✗ SMTP error: {e}", flush=True)
        return False


def mark_sent(no: int, to_addr: str):
    data = json.load(open(EMAIL_PIPELINE, encoding="utf-8"))
    for p in data:
        if p.get("no") == no:
            p["status"] = "messaged"
            p["touch_count"] = p.get("touch_count", 0) + 1
            p["message_sent_date"] = TODAY
            p["message_channel"] = "email"
            break
    with open(EMAIL_PIPELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  → pipeline updated: no:{no} status=messaged", flush=True)


def main():
    print(f"=== Email Sender v33 | {len(TARGETS)} USA v33 | {TODAY} ===\n", flush=True)
    sent = 0
    for i, t in enumerate(TARGETS, 1):
        print(f"[{i}/{len(TARGETS)}] no:{t['no']} → {t['to']}", flush=True)
        ok = send_email(t["to"], t["name"], t["no"])
        if ok:
            mark_sent(t["no"], t["to"])
            sent += 1
            print(f"  ✓ SENT\n", flush=True)
        else:
            print(f"  ✗ FAILED\n", flush=True)
        if i < len(TARGETS):
            time.sleep(8)
    print(f"=== Done: {sent}/{len(TARGETS)} emails sent ===")


if __name__ == "__main__":
    main()

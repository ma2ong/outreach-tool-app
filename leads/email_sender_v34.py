"""
Email Sender v34 — USA v34 batch (nos 597-610, 13 with email)
AV For You, Fire Up Creative, Showtime LED, KC Event Company, TSV Sound & Vision,
JAWS AVL, Outdoor LED Rentals, Elite Multimedia, Fairfield Pro AV,
FireFly AV Design, Mathes Event Productions, Picture This, North State AV
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
    {"no": 597, "to": "rentals@avforyou.com",        "name": ""},
    {"no": 598, "to": "dave@fireupvideo.com",          "name": "Dave"},
    {"no": 599, "to": "info@showtimeled.com",          "name": ""},
    {"no": 600, "to": "info@kceventcompany.com",       "name": ""},
    {"no": 601, "to": "info@tsvstl.com",               "name": ""},
    {"no": 602, "to": "info@jawsaudio.com",            "name": ""},
    {"no": 604, "to": "info@outdoorledrentals.com",    "name": ""},
    {"no": 605, "to": "rentals@elitemultimedia.com",   "name": ""},
    {"no": 606, "to": "samjr@fairfieldpro.com",        "name": "Sam"},
    {"no": 607, "to": "noah@fireflyavdesign.com",      "name": "Noah"},
    {"no": 608, "to": "info@mathesevents.com",         "name": ""},
    {"no": 609, "to": "info@pixthis.com",              "name": ""},
    {"no": 610, "to": "info@northstateav.com",         "name": ""},
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
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PW)
            server.sendmail(GMAIL_USER, to_addr, msg.as_bytes())
        return True
    except Exception as e:
        print(f"  ✗ SMTP error: {e}", flush=True)
        return False


def mark_sent(no: int):
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
    print(f"  → pipeline updated: no:{no}", flush=True)


def main():
    print(f"=== Email Sender v34 | {len(TARGETS)} USA v34 | {TODAY} ===\n", flush=True)
    sent = 0
    for i, t in enumerate(TARGETS, 1):
        print(f"[{i}/{len(TARGETS)}] no:{t['no']} → {t['to']}", flush=True)
        ok = send_email(t["to"], t["name"], t["no"])
        if ok:
            mark_sent(t["no"])
            sent += 1
            print(f"  ✓ SENT\n", flush=True)
        else:
            print(f"  ✗ FAILED\n", flush=True)
        if i < len(TARGETS):
            time.sleep(8)
    print(f"=== Done: {sent}/{len(TARGETS)} emails sent ===")


if __name__ == "__main__":
    main()

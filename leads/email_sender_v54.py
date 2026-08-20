"""
Email sender v54 — v54 batch (3 companies with email)
Brazil: Stage Audiovisual (Curitiba)
Argentina: AudioLuz (Rosario), 7Sentidos (Cordoba)
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
_pw_file = Path.home() / ".gmail_app_password"
GMAIL_APP_PASSWORD = (
    os.environ.get("GMAIL_APP_PASSWORD")
    or (_pw_file.read_text(encoding="utf-8").strip() if _pw_file.exists() else "")
)
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
    {"no": 746, "company_en": "Stage Audiovisual Curitiba", "email": "comercial@stageaudiovisual.com.br", "name": "Stage Audiovisual Team", "city": "Curitiba, BR"},
    {"no": 747, "company_en": "AudioLuz Rosario",           "email": "contacto@audioluz.com.ar",          "name": "AudioLuz Team",          "city": "Rosario, AR"},
    {"no": 748, "company_en": "7Sentidos Cordoba",           "email": "info@sietesentidos.com.ar",         "name": "7Sentidos Team",         "city": "Cordoba, AR"},
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
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{ATTACHMENT.name}"')
        msg.attach(part)
    else:
        print(f"  WARNING: Attachment not found: {ATTACHMENT}", flush=True)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, to_email, msg.as_bytes())
        return True
    except Exception as e:
        print(f"  ERROR: {e}", flush=True)
        return False


def load_pipeline():
    with open(EMAIL_PIPELINE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_pipeline(data):
    with open(EMAIL_PIPELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_already_sent(no):
    for p in load_pipeline():
        if p.get("no") == no and p.get("status") == "messaged":
            return True
    return False


def mark_sent(no, email):
    data = load_pipeline()
    for p in data:
        if p.get("no") == no:
            p["status"] = "messaged"
            p["message_sent_date"] = TODAY
            p["message_channel"] = "email"
            p["email"] = email
            break
    else:
        data.append({
            "no": no, "email": email, "status": "messaged",
            "message_sent_date": TODAY, "message_channel": "email"
        })
    save_pipeline(data)


def main():
    if not GMAIL_APP_PASSWORD:
        print("ERROR: Set GMAIL_APP_PASSWORD env var first.", flush=True)
        return

    print(f"=== Email Sender v54 | {len(TARGETS)} targets | {TODAY} ===", flush=True)

    for i, t in enumerate(TARGETS, 1):
        print(f"\n[{i}/{len(TARGETS)}] {t['company_en']} ({t['city']}) -> {t['email']}", flush=True)

        if is_already_sent(t["no"]):
            print(f"  SKIP: already sent", flush=True)
            continue

        ok = send_email(t["email"], t["name"])
        if ok:
            print(f"  Sent", flush=True)
            mark_sent(t["no"], t["email"])
        else:
            print(f"  Failed", flush=True)

        if i < len(TARGETS):
            wait = random.randint(45, 90)
            print(f"  waiting {wait}s...", flush=True)
            time.sleep(wait)

    print(f"\n=== Done ===", flush=True)


if __name__ == "__main__":
    main()

"""
Email sender v47 — 6 targets (nos 692-697, VOX has no email)
Raleigh NC / Memphis TN / El Paso TX / Orlando FL x3
"""
import smtplib, json, datetime, os, sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
SENDER = "allenma2ong@gmail.com"
GMAIL_APP_PW = os.environ.get("GMAIL_APP_PASSWORD", "")

BASE = Path(__file__).parent
EMAIL_PIPELINE = BASE / "pipeline/email/prospects.json"
TODAY = datetime.date.today().isoformat()

TARGETS = [
    {
        "no": 692, "to": "info@gsfaudio.com",
        "company": "GSF Productions", "city": "Raleigh, NC",
        "subject": "LED Display Panels for GSF Productions — Factory-Direct from Shenzhen",
        "body": """Hi GSF Productions team,

I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV rental companies and production houses in the US.

Your LED video wall rental and production services for corporate events and live shows in the Raleigh area caught our attention. We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing, with quick shipping to NC.

If you're sourcing LED panels or looking to expand your video wall inventory, I'd love to share our specs and pricing.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp: +86 138-2345-6789
""",
    },
    {
        "no": 693, "to": "info@productionone.com",
        "company": "ProductionOne", "city": "Memphis, TN",
        "subject": "LED Display Panels for ProductionOne — Factory-Direct from Shenzhen",
        "body": """Hi ProductionOne team,

I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV production companies across the US.

Your LED video wall rental and installation services for corporate events, concerts, and trade shows in the Memphis area look impressive. We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing, with fast delivery to TN.

If you're sourcing LED panels or expanding your video wall inventory, happy to share specs and pricing.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp: +86 138-2345-6789
""",
    },
    {
        "no": 694, "to": "service@techpro-av.com",
        "company": "TechPro Audio & Video", "city": "El Paso, TX",
        "subject": "LED Video Wall Panels for TechPro AV — Factory-Direct from Shenzhen",
        "body": """Hi TechPro team,

I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV integrators and video wall installers in the US.

Your video wall installation and digital signage work in El Paso looks great. We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing, suitable for commercial installations and rental fleets.

If you're sourcing LED panels for upcoming projects, I'd love to share our product specs and pricing.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp: +86 138-2345-6789
""",
    },
    {
        "no": 695, "to": "info@excelpresentations.com",
        "company": "Excel Presentation Services", "city": "Orlando, FL",
        "subject": "LED Display Panels for Your Orlando Video Wall Rental Fleet",
        "body": """Hi Excel Presentations team,

I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for video wall rental specialists in the US.

Your LED video wall rental services for trade shows, corporate events, and outdoor venues in Orlando look excellent. We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing, with reliable stock availability for the US market.

If you're sourcing LED panels or looking to refresh your rental inventory, happy to share specs and pricing.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp: +86 138-2345-6789
""",
    },
    {
        "no": 696, "to": "info@avrentalorlando.com",
        "company": "AV Rental Orlando", "city": "Orlando, FL",
        "subject": "LED Display Panels for AV Rental Orlando — Factory-Direct Pricing",
        "body": """Hi AV Rental Orlando team,

I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV rental companies serving the convention and events market.

Your seamless LED video wall services for OCCC, hotels, and outdoor stages in Orlando are impressive. We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing, and work with rental fleets across the US.

If you're sourcing LED panels, I'd be happy to share specs and pricing.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp: +86 138-2345-6789
""",
    },
    {
        "no": 697, "to": "hello@orlandovideowallrental.com",
        "company": "Orlando Video Walls", "city": "Orlando, FL",
        "subject": "LED Display Panels for Orlando Video Wall Rental — Factory-Direct",
        "body": """Hi Orlando Video Walls team,

I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for video wall rental companies in the US.

Your LED video wall, giant LED, and mobile LED trailer rental services for events in Orlando look great. We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing, with strong stock for the US rental market.

If you're looking to source LED panels or expand your fleet, happy to connect and share specs.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp: +86 138-2345-6789
""",
    },
]


def send_email(target: dict) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = target["subject"]
    msg["From"] = SENDER
    msg["To"] = target["to"]
    msg.attach(MIMEText(target["body"], "plain", "utf-8"))
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as s:
            s.login(SENDER, GMAIL_APP_PW)
            s.sendmail(SENDER, [target["to"]], msg.as_string())
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
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


def main():
    if not GMAIL_APP_PW:
        print("ERROR: GMAIL_APP_PASSWORD not set")
        return

    print(f"=== Email Sender v47 | {len(TARGETS)} targets | {TODAY} ===\n")
    sent = 0
    for t in TARGETS:
        print(f"[{t['no']}] {t['company']} ({t['city']}) → {t['to']}")
        ok = send_email(t)
        if ok:
            mark_sent(t["no"])
            sent += 1
            print(f"  ✓ SENT\n")
        else:
            print(f"  ✗ FAILED\n")

    print(f"=== Done: {sent}/{len(TARGETS)} emails sent ===")


if __name__ == "__main__":
    main()

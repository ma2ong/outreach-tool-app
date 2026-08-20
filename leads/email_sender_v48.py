"""Email sender v48 — 6 targets (nos 699-704)"""
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
        "no": 699, "to": "Sales@rockymountainroll.com",
        "company": "Rocky Mountain Roll", "city": "Meridian, ID",
        "subject": "LED Display Panels for Rocky Mountain Roll — Factory-Direct from Shenzhen",
        "body": """Hi Rocky Mountain Roll team,

I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV rental companies in the Pacific Northwest.

Your LED video wall rental and event production services across the Boise area and Idaho look impressive — 40+ years in the business is a great track record. We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing, with reliable delivery to ID.

If you're sourcing LED panels or looking to expand your video wall inventory, happy to share specs and pricing.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp: +86 138-2345-6789
""",
    },
    {
        "no": 700, "to": "rentals@rmav.com",
        "company": "Rocky Mountain Audio Visual", "city": "Boise, ID",
        "subject": "LED Display Panels for RMAV — Factory-Direct from Shenzhen",
        "body": """Hi RMAV team,

I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV service providers across the US.

Your LED large-screen display solutions for conferences, trade shows, and concerts across Idaho and the Pacific Northwest are impressive. We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing.

If you're sourcing LED panels, I'd be happy to share our product specs and pricing.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp: +86 138-2345-6789
""",
    },
    {
        "no": 701, "to": "info@azmobilemedia.net",
        "company": "Arizona Mobile Media", "city": "Tucson, AZ",
        "subject": "Outdoor LED Screen Panels for Arizona Mobile Media — Factory-Direct",
        "body": """Hi Arizona Mobile Media team,

I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for mobile LED screen rental companies in the US.

Your trailer-mounted outdoor LED screens and live production services for music festivals and corporate events across Arizona look great. We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing, including high-brightness outdoor panels suited for mobile trailer applications.

If you're sourcing LED panels for your fleet, happy to share specs and pricing.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp: +86 138-2345-6789
""",
    },
    {
        "no": 702, "to": "sealsproductions7@gmail.com",
        "company": "Seals Productions", "city": "Chattanooga, TN",
        "subject": "LED Display Panels for Seals Productions — Factory-Direct from Shenzhen",
        "body": """Hi Kendall,

I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for event production companies in the Southeast US.

Your LED display, lighting, and audio services for events in the Chattanooga area look great. We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing, with fast shipping to TN.

If you're sourcing LED panels or expanding your display inventory, happy to connect and share specs.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp: +86 138-2345-6789
""",
    },
    {
        "no": 703, "to": "Sales@ampdspokane.com",
        "company": "AMPD Lighting and Audio Visual", "city": "Spokane, WA",
        "subject": "LED Video Wall Panels for AMPD — Factory-Direct from Shenzhen",
        "body": """Hi AMPD team,

I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for premium AV rental companies in the Pacific Northwest.

Your 30×10ft LED video wall setup for concerts, corporate events, and church productions across Washington and Idaho is impressive. We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing — well-suited for large-format rental applications.

If you're sourcing LED panels or looking to expand your video wall capacity, happy to share specs and pricing.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp: +86 138-2345-6789
""",
    },
    {
        "no": 704, "to": "info@avlsusa.com",
        "company": "AVL Solutions", "city": "Greenville, SC",
        "subject": "Outdoor LED Screen Panels for AVL Solutions — Factory-Direct Pricing",
        "body": """Hi AVL Solutions team,

I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV rental companies in the Southeast US.

Your 20+ years of outdoor mobile LED screen rental services for music festivals, graduations, and drive-in events in the Greenville area are impressive. We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing, including weatherproof outdoor panels ideal for your mobile rental fleet.

If you're sourcing LED panels, happy to share specs and pricing.

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
        print('Run: $env:GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"; python email_sender_v48.py')
        return

    print(f"=== Email Sender v48 | {len(TARGETS)} targets | {TODAY} ===\n")
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

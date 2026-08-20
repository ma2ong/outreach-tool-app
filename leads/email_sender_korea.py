"""
Korea email sender via Gmail SMTP.
Fixed Korean body + Korea project poster image as attachment.
Run: set GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx && python email_sender_korea.py
"""
import json, sys, os, time, random, smtplib, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

TODAY = datetime.date.today().isoformat()
BASE = Path(__file__).parent
PROSPECTS_FILE = BASE / "pipeline/whatsapp/prospects.json"

GMAIL_USER = "allenma2ong@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

ATTACHMENT = Path(r"C:\Users\Administrator\Desktop\korea-led-projects-poster-4k.jpg")

SUBJECT = "한국 LED 디스플레이 납품 사례 공유드립니다"

BODY = """\
안녕하세요~

최근 저희가 한국에 납품한 LED 디스플레이 설치사례를 공유드립니다.
P1.53, P1.86, P2.5, P3.91, P10 등 실내/실외 다양한 프로젝트를 진행했습니다.

혹시 최근 검토 중이거나 진행 예정인 프로젝트가 있으면 편하게 연락 주세요.
현장 조건에 맞는 제품 추천과 좋은 조건으로 견적 드리겠습니다.

좋은 기회로 함께 협력할 수 있기를 바랍니다!

Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
▎ Kakaotalk / WeChat: +86 13570871001
Email: allenma2ong@gmail.com\
"""


def send_email(to_addr: str) -> bool:
    try:
        msg = MIMEMultipart()
        msg["Subject"] = SUBJECT
        msg["From"] = f"Allen Ma <{GMAIL_USER}>"
        msg["To"] = to_addr
        msg.attach(MIMEText(BODY, "plain", "utf-8"))

        if ATTACHMENT.exists():
            with open(ATTACHMENT, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{ATTACHMENT.name}"',
            )
            msg.attach(part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, to_addr, msg.as_string())
        return True
    except Exception as e:
        print(f"  SMTP error: {e}", flush=True)
        return False


def mark_sent(data, no: int, email: str):
    for p in data:
        if p.get("no") == no:
            p["status"] = "messaged"
            p["touch_count"] = 1
            p["message_sent_date"] = TODAY
            p["message_channel"] = "email"
            p["email_to"] = email
            p["message_text"] = BODY[:200]
            break
    with open(PROSPECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def wait_until_8am():
    """Sleep until tomorrow 08:00 Asia/Shanghai (= UTC+8)."""
    import datetime as dt
    now = dt.datetime.now()
    target = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now >= target:
        target += dt.timedelta(days=1)
    secs = (target - now).total_seconds()
    print(f"Waiting until {target.strftime('%Y-%m-%d 08:00')} Asia/Shanghai "
          f"({secs/3600:.1f}h)...", flush=True)
    time.sleep(secs)


def main():
    if not GMAIL_APP_PASSWORD:
        print("ERROR: Set GMAIL_APP_PASSWORD first.")
        print("  set GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx")
        sys.exit(1)

    if not ATTACHMENT.exists():
        print(f"WARNING: Attachment not found: {ATTACHMENT}")

    with open(PROSPECTS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # Collect all already-sent email addresses (from previous batches)
    already_sent = {p["email_to"].lower() for p in data if p.get("email_to")}

    JUNK = {"wixpress", "sentry"}
    seen_emails = set()
    targets = []
    for p in data:
        if (p.get("country") == "Korea"
                and p.get("status") == "prospect"
                and p.get("email")
                and "@" in p["email"]
                and not any(j in p["email"] for j in JUNK)):
            em = p["email"].lower()
            if em in already_sent:
                print(f"  skip no:{p['no']} {p['company_en']} — {p['email']} already sent")
                continue
            if em in seen_emails:
                continue
            seen_emails.add(em)
            targets.append(p)

    print(f"=== Korea Email Sender | {len(targets)} targets | {TODAY} ===\n", flush=True)
    print(f"Subject: {SUBJECT}", flush=True)
    print(f"Attachment: {ATTACHMENT.name if ATTACHMENT.exists() else 'NOT FOUND'}\n", flush=True)

    sent, failed = 0, 0
    for i, p in enumerate(targets, 1):
        email = p["email"]
        print(f"[{i}/{len(targets)}] no:{p['no']} {p['company_en']}  →  {email}", flush=True)

        ok = send_email(email)
        if ok:
            mark_sent(data, p["no"], email)
            print(f"  SENT", flush=True)
            sent += 1
        else:
            failed += 1

        if i < len(targets):
            wait = random.randint(30, 60)
            print(f"  waiting {wait}s...\n", flush=True)
            time.sleep(wait)

    st = Counter(p.get("status") for p in data)
    print(f"\n=== Done: {sent} sent, {failed} failed ===", flush=True)
    print(f"Pipeline: {dict(st)}", flush=True)


if __name__ == "__main__":
    main()

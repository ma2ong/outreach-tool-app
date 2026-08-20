"""
International LED leads email sender.
Reads all leads (v4-v18) with emails, skips already-sent addresses, sends per-country templates.
Run: GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx" python email_sender_intl.py
"""
import json, ast, re, sys, os, time, random, smtplib, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

TODAY = datetime.date.today().isoformat()
BASE = Path(__file__).parent
PROSPECTS_FILE = BASE / "pipeline/whatsapp/prospects.json"

GMAIL_USER = "allenma2ong@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

JUNK = {"wixpress", "sentry", "example.com", "google.com", "facebook.com",
        "instagram.com", "naver.com", "kakao.com", "w3.org", "schema.org"}

# ── Per-country templates ────────────────────────────────────────────────────

TEMPLATES = {
    "Brazil": {
        "subject": "Fornecedor de Painéis LED – Projetos Recentes | Shenzhen Maxcolor Visual",
        "body": """\
Olá,

Somos a Shenzhen Maxcolor Visual, fabricante de displays LED na China com projetos no Brasil e na América Latina.

Trabalhamos com P1.53, P1.86, P2.5, P3.91, P4, P10 – instalações internas e externas, videowall e painéis de grande formato.

Se tiver projetos em andamento ou previstos, entre em contato. Podemos oferecer recomendações técnicas e cotações competitivas.

Aguardamos uma oportunidade de colaboração!

Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
▎ WhatsApp/WeChat: +86 13570871001
Email: allenma2ong@gmail.com"""
    },
    "Colombia": {
        "subject": "Proveedor de Pantallas LED – Proyectos Recientes | Shenzhen Maxcolor Visual",
        "body": """\
Hola,

Somos Shenzhen Maxcolor Visual, fabricante de pantallas LED en China con proyectos en Latinoamérica.

Manejamos P1.53, P1.86, P2.5, P3.91, P4, P10 – instalaciones interiores y exteriores, videowalls y pantallas de gran formato.

Si tiene proyectos en curso o planificados, con gusto le brindamos recomendaciones técnicas y cotizaciones competitivas.

¡Esperamos poder colaborar juntos!

Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
▎ WhatsApp/WeChat: +86 13570871001
Email: allenma2ong@gmail.com"""
    },
    "Chile": {
        "subject": "Proveedor de Pantallas LED – Proyectos Recientes | Shenzhen Maxcolor Visual",
        "body": """\
Hola,

Somos Shenzhen Maxcolor Visual, fabricante de pantallas LED en China con proyectos en Latinoamérica.

Manejamos P1.53, P1.86, P2.5, P3.91, P4, P10 – instalaciones interiores y exteriores, videowalls y pantallas de gran formato.

Si tiene proyectos en curso o planificados, con gusto le brindamos recomendaciones técnicas y cotizaciones competitivas.

¡Esperamos poder colaborar juntos!

Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
▎ WhatsApp/WeChat: +86 13570871001
Email: allenma2ong@gmail.com"""
    },
    "Peru": {
        "subject": "Proveedor de Pantallas LED – Proyectos Recientes | Shenzhen Maxcolor Visual",
        "body": """\
Hola,

Somos Shenzhen Maxcolor Visual, fabricante de pantallas LED en China con proyectos en Latinoamérica.

Manejamos P1.53, P1.86, P2.5, P3.91, P4, P10 – instalaciones interiores y exteriores, videowalls y pantallas de gran formato.

Si tiene proyectos en curso o planificados, con gusto le brindamos recomendaciones técnicas y cotizaciones competitivas.

¡Esperamos poder colaborar juntos!

Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
▎ WhatsApp/WeChat: +86 13570871001
Email: allenma2ong@gmail.com"""
    },
    "Argentina": {
        "subject": "Proveedor de Pantallas LED – Proyectos Recientes | Shenzhen Maxcolor Visual",
        "body": """\
Hola,

Somos Shenzhen Maxcolor Visual, fabricante de pantallas LED en China con proyectos en Latinoamérica.

Manejamos P1.53, P1.86, P2.5, P3.91, P4, P10 – instalaciones interiores y exteriores, videowalls y pantallas de gran formato.

Si tiene proyectos en curso o planificados, con gusto le brindamos recomendaciones técnicas y cotizaciones competitivas.

¡Esperamos poder colaborar juntos!

Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
▎ WhatsApp/WeChat: +86 13570871001
Email: allenma2ong@gmail.com"""
    },
    "Mexico": {
        "subject": "Proveedor de Pantallas LED – Proyectos Recientes | Shenzhen Maxcolor Visual",
        "body": """\
Hola,

Somos Shenzhen Maxcolor Visual, fabricante de pantallas LED en China con proyectos en México y Latinoamérica.

Manejamos P1.53, P1.86, P2.5, P3.91, P4, P10 – instalaciones interiores y exteriores, videowalls y pantallas de gran formato.

Si tiene proyectos en curso o planificados, con gusto le brindamos recomendaciones técnicas y cotizaciones competitivas.

¡Esperamos poder colaborar juntos!

Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
▎ WhatsApp/WeChat: +86 13570871001
Email: allenma2ong@gmail.com"""
    },
    "USA": {
        "subject": "LED Display Supplier – Installation Projects & Pricing | Shenzhen Maxcolor Visual",
        "body": """\
Hi,

We're Shenzhen Maxcolor Visual, a Chinese LED display manufacturer with global installation projects.

We supply P1.53, P1.86, P2.5, P3.91, P4, P10 – indoor/outdoor LED walls, fine-pitch displays, and large-format screens.

If you have upcoming or active projects, feel free to reach out. We can provide technical support and competitive pricing.

Looking forward to working together!

Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
▎ WhatsApp/WeChat: +86 13570871001
Email: allenma2ong@gmail.com"""
    },
    "Canada": {
        "subject": "LED Display Supplier – Installation Projects & Pricing | Shenzhen Maxcolor Visual",
        "body": """\
Hi,

We're Shenzhen Maxcolor Visual, a Chinese LED display manufacturer with global installation projects.

We supply P1.53, P1.86, P2.5, P3.91, P4, P10 – indoor/outdoor LED walls, fine-pitch displays, and large-format screens.

If you have upcoming or active projects, feel free to reach out. We can provide technical support and competitive pricing.

Looking forward to working together!

Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
▎ WhatsApp/WeChat: +86 13570871001
Email: allenma2ong@gmail.com"""
    },
    "Korea": {
        "subject": "한국 LED 디스플레이 납품 사례 공유드립니다",
        "body": """\
안녕하세요~

최근 저희가 한국에 납품한 LED 디스플레이 설치사례를 공유드립니다.
P1.53, P1.86, P2.5, P3.91, P10 등 실내/실외 다양한 프로젝트를 진행했습니다.

혹시 최근 검토 중이거나 진행 예정인 프로젝트가 있으면 편하게 연락 주세요.
현장 조건에 맞는 제품 추천과 좋은 조건으로 견적 드리겠습니다.

좋은 기회로 함께 협력할 수 있기를 바랍니다!

Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
▎ Kakaotalk / WeChat: +86 13570871001
Email: allenma2ong@gmail.com"""
    },
}


def load_all_leads():
    v4_src = open(BASE / "generate_led_leads_v4.py", encoding="utf-8").read()
    leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", v4_src, re.M | re.S).group(1))
    for vname in [f"v{i}" for i in range(5, 20)]:
        path = BASE / f"generate_led_leads_{vname}.py"
        if not path.exists():
            continue
        src = open(path, encoding="utf-8").read()
        m = re.search(r"^new_entries = (\[.+?^\])", src, re.M | re.S)
        if m:
            leads.extend(ast.literal_eval(m.group(1)))
    return leads


def send_email(to_addr: str, subject: str, body: str) -> bool:
    for attempt in range(3):
        try:
            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = f"Allen Ma <{GMAIL_USER}>"
            msg["To"] = to_addr
            msg.attach(MIMEText(body, "plain", "utf-8"))
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                server.sendmail(GMAIL_USER, to_addr, msg.as_string())
            return True
        except Exception as e:
            print(f"  attempt {attempt+1} error: {e}", flush=True)
            if attempt < 2:
                time.sleep(10)
    return False


def mark_sent_pipeline(pipeline_data, no: int, email: str, country: str):
    """Mark as messaged in pipeline if the no exists there; otherwise just track."""
    for p in pipeline_data:
        if p.get("no") == no:
            p["status"] = "messaged"
            p["touch_count"] = 1
            p["message_sent_date"] = TODAY
            p["message_channel"] = "email"
            p["email_to"] = email
            return True
    # Not in WA pipeline — add a record
    pipeline_data.append({
        "no": no,
        "country": country,
        "status": "messaged",
        "touch_count": 1,
        "message_sent_date": TODAY,
        "message_channel": "email",
        "email_to": email,
    })
    return True


def main():
    if not GMAIL_APP_PASSWORD:
        print("ERROR: Set GMAIL_APP_PASSWORD env var first.")
        sys.exit(1)

    leads = load_all_leads()

    with open(PROSPECTS_FILE, encoding="utf-8") as f:
        pipeline = json.load(f)

    sent_emails = {p["email_to"].lower() for p in pipeline if p.get("email_to")}
    messaged_nos = {p["no"] for p in pipeline if p.get("status") == "messaged"}

    # Build target list — deduplicate by email address
    seen = set()
    targets = []
    for l in leads:
        em = l.get("email", "").strip().lower()
        if not em or "@" not in em:
            continue
        if any(j in em for j in JUNK):
            continue
        if em in sent_emails or l.get("no") in messaged_nos:
            continue
        if em in seen:
            continue
        seen.add(em)
        targets.append(l)

    print(f"=== Intl Email Sender | {len(targets)} targets | {TODAY} ===\n", flush=True)
    by_country = Counter(l.get("country") for l in targets)
    print("By country:", dict(by_country))
    print()

    sent, failed = 0, 0
    for i, l in enumerate(targets, 1):
        country = l.get("country", "USA")
        tmpl = TEMPLATES.get(country, TEMPLATES["USA"])
        email = l["email"].strip()

        print(f"[{i}/{len(targets)}] no:{l['no']} {country} {l['company_en']}  →  {email}", flush=True)
        ok = send_email(email, tmpl["subject"], tmpl["body"])

        if ok:
            mark_sent_pipeline(pipeline, l["no"], email, country)
            with open(PROSPECTS_FILE, "w", encoding="utf-8") as f:
                json.dump(pipeline, f, ensure_ascii=False, indent=2)
            print(f"  SENT", flush=True)
            sent += 1
        else:
            print(f"  FAILED", flush=True)
            failed += 1

        if i < len(targets):
            wait = random.randint(35, 65)
            print(f"  waiting {wait}s...\n", flush=True)
            time.sleep(wait)

    st = Counter(p.get("status") for p in pipeline)
    print(f"\n=== Done: {sent} sent, {failed} failed ===", flush=True)
    print(f"Pipeline: {dict(st)}", flush=True)


if __name__ == "__main__":
    main()

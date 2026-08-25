import os
import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from app import identity

# The legacy single-mailbox fallback, used only when no mailbox is configured in the
# Mailboxes panel. It is the company address now, not a personal Gmail, so the name no
# longer claims otherwise — GMAIL_USER stays as an alias because callers import it.
FALLBACK_SENDER = identity.SENDER_EMAIL
GMAIL_USER = FALLBACK_SENDER
# maxcolorvisual.com is hosted on NetEase enterprise mail (MX hzmx01.mxmail.netease.com).
FALLBACK_SMTP_HOST = "smtp.qiye.163.com"
PW_FILE = Path.home() / ".mailbox_app_password"
LEGACY_PW_FILE = Path.home() / ".gmail_app_password"


def get_password() -> str:
    for env in ("MAILBOX_APP_PASSWORD", "GMAIL_APP_PASSWORD"):
        value = os.environ.get(env)
        if value:
            return value
    for path in (PW_FILE, LEGACY_PW_FILE):
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    return ""


def build_message(sender: str, to: str, subject: str, body: str, attachment: str | None) -> MIMEMultipart:
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.attach(MIMEText(body, "plain", "utf-8"))
    if attachment:
        # Silently dropping a missing attachment is worse than failing: the copy says
        # "I've attached a sheet of recent projects" and the customer sees nothing.
        if not os.path.exists(attachment):
            raise FileNotFoundError(f"附件不存在：{attachment}")
        with open(attachment, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(attachment)}"')
        msg.attach(part)
    return msg


def default_mailbox() -> dict:
    pw = get_password()
    if not pw:
        raise RuntimeError("Gmail app password missing (~/.gmail_app_password or GMAIL_APP_PASSWORD)")
    return {"email": FALLBACK_SENDER, "smtp_host": FALLBACK_SMTP_HOST, "port": 465,
            "username": FALLBACK_SENDER, "password": pw}


def send_email(to: str, subject: str, body: str, attachment: str | None = None) -> None:
    """Send from the fallback Gmail (used when no sender mailboxes are configured)."""
    send_via(default_mailbox(), to, subject, body, attachment)


STARTTLS_FALLBACK_PORT = 587


def _open(host: str, port: int, user: str, password: str):
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        server = smtplib.SMTP(host, port, timeout=20)
        server.starttls()
    server.login(user, password)
    return server


def _connect(mailbox: dict):
    """SMTP connection, logged in.

    Some networks (security software, corporate filters) break the TLS handshake on
    465/SMTPS while STARTTLS on 587 goes through — measured on this machine, where 465
    dies with SSLEOFError. Falling back keeps a whole campaign from failing silently.
    """
    host = mailbox["smtp_host"]
    port = int(mailbox.get("port") or 465)
    user = mailbox["username"]
    password = mailbox["password"]
    try:
        return _open(host, port, user, password)
    except (ssl.SSLError, OSError) as exc:
        if port != 465 or isinstance(exc, smtplib.SMTPAuthenticationError):
            raise
        return _open(host, STARTTLS_FALLBACK_PORT, user, password)


def send_via(mailbox: dict, to: str, subject: str, body: str, attachment: str | None = None) -> None:
    """Send from a configured mailbox (rotation)."""
    sender = mailbox["email"]
    msg = build_message(sender, to, subject, body, attachment)
    with _connect(mailbox) as server:
        server.sendmail(sender, to, msg.as_bytes())


def test_mailbox(mailbox: dict) -> None:
    """Log in without sending. Raises with the SMTP reason if host/port/password are wrong,
    so a bad mailbox is caught at setup instead of halfway through a campaign."""
    with _connect(mailbox):
        pass

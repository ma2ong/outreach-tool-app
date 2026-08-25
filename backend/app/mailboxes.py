"""Sender-mailbox rotation to protect deliverability.

Sending hundreds of cold emails from one address gets it flagged. Configure a few
sender mailboxes; the email send path picks the least-used active mailbox that still
has daily capacity, spreading volume so no single domain looks spammy (the Smartlead
approach). With zero mailboxes configured the send path falls back to the single
legacy Gmail, so this is opt-in.

Passwords live in the local single-user DB and are never returned by the API.
"""
import datetime as _dt


def infer_imap_host(smtp_host: str) -> str | None:
    host = (smtp_host or "").strip().lower()
    known = {
        "smtp.gmail.com": "imap.gmail.com",
        "smtp.office365.com": "outlook.office365.com",
        "smtp-mail.outlook.com": "outlook.office365.com",
        "smtp.zoho.com": "imap.zoho.com",
        # NetEase enterprise mail. The generic smtp->imap swap below would land on the
        # same host, but the paid (qiye) and free (ym) tiers are different services and
        # naming both here keeps that visible.
        "smtp.qiye.163.com": "imap.qiye.163.com",
        "smtp.ym.163.com": "imap.ym.163.com",
    }
    if host in known:
        return known[host]
    return host.replace("smtp.", "imap.", 1) if host.startswith("smtp.") else None


def _today() -> str:
    return _dt.date.today().isoformat()


def add_mailbox(conn, email: str, smtp_host: str, port: int, username: str,
                password: str, daily_cap: int = 40, imap_host: str | None = None,
                imap_port: int = 993, imap_enabled: bool = True) -> int:
    cur = conn.execute(
        "INSERT INTO mailboxes(email, smtp_host, port, imap_host, imap_port,"
        " username, password, daily_cap, active, created_at, imap_enabled)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
        (email, smtp_host, port, imap_host, imap_port, username, password,
         daily_cap, _dt.datetime.now(_dt.UTC).isoformat(), 1 if imap_enabled else 0))
    conn.commit()
    return cur.lastrowid


def list_mailboxes(conn, include_secrets: bool = False) -> list[dict]:
    rows = conn.execute(
        "SELECT id, email, smtp_host, port, imap_host, imap_port, username,"
        " password, daily_cap, active, imap_enabled FROM mailboxes ORDER BY id")
    out = []
    for r in rows:
        d = dict(r)
        d["active"] = bool(d["active"])
        d["imap_enabled"] = bool(d["imap_enabled"])
        d["sent_today"] = sent_today(conn, d["id"])
        if not include_secrets:
            d.pop("password", None)
        out.append(d)
    return out


def set_password(conn, mailbox_id: int, password: str) -> bool:
    """Replace the stored credential.

    Without this the only way to fix a password was to delete the mailbox and add it
    again, so the natural move — typing into the password box on screen and pressing
    Test — was filling in the *new mailbox* form while testing the old row. The test then
    logged in with an empty string, and NetEase answers that by closing the connection:
    "Connection unexpectedly closed", which reads like a network fault rather than a
    missing password.
    """
    if not password:
        return False
    cur = conn.execute("UPDATE mailboxes SET password=? WHERE id=?", (password, mailbox_id))
    conn.commit()
    return cur.rowcount > 0


def has_password(conn, mailbox_id: int) -> bool:
    row = conn.execute("SELECT COALESCE(password,'') p FROM mailboxes WHERE id=?",
                       (mailbox_id,)).fetchone()
    return bool(row and row["p"])


def set_active(conn, mailbox_id: int, active: bool) -> bool:
    cur = conn.execute("UPDATE mailboxes SET active=? WHERE id=?", (1 if active else 0, mailbox_id))
    conn.commit()
    return cur.rowcount > 0


def delete_mailbox(conn, mailbox_id: int) -> bool:
    cur = conn.execute("DELETE FROM mailboxes WHERE id=?", (mailbox_id,))
    conn.commit()
    return cur.rowcount > 0


def sent_today(conn, mailbox_id: int) -> int:
    row = conn.execute("SELECT count FROM mailbox_sends WHERE mailbox_id=? AND date=?",
                       (mailbox_id, _today())).fetchone()
    return row["count"] if row else 0


def record_send(conn, mailbox_id: int) -> None:
    conn.execute(
        "INSERT INTO mailbox_sends(mailbox_id, date, count) VALUES (?, ?, 1)"
        " ON CONFLICT(mailbox_id, date) DO UPDATE SET count=count+1",
        (mailbox_id, _today()))
    conn.commit()


def pick_mailbox(conn) -> dict | None:
    """Least-used active mailbox that still has daily capacity, or None if all capped."""
    today = _today()
    row = conn.execute(
        "SELECT m.id, m.email, m.smtp_host, m.port, m.username, m.password, m.daily_cap,"
        "       COALESCE(s.count, 0) AS used"
        " FROM mailboxes m"
        " LEFT JOIN mailbox_sends s ON s.mailbox_id = m.id AND s.date = ?"
        " WHERE m.active = 1 AND COALESCE(s.count, 0) < m.daily_cap"
        " ORDER BY used ASC, m.id ASC LIMIT 1", (today,)).fetchone()
    return dict(row) if row else None


def total_remaining(conn) -> int:
    """Sum of remaining daily capacity across active mailboxes."""
    today = _today()
    row = conn.execute(
        "SELECT COALESCE(SUM(MAX(m.daily_cap - COALESCE(s.count, 0), 0)), 0) AS rem"
        " FROM mailboxes m"
        " LEFT JOIN mailbox_sends s ON s.mailbox_id = m.id AND s.date = ?"
        " WHERE m.active = 1", (today,)).fetchone()
    return row["rem"] or 0


def has_active(conn) -> bool:
    return conn.execute("SELECT 1 FROM mailboxes WHERE active=1 LIMIT 1").fetchone() is not None

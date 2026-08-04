"""Inbox intelligence: poll IMAP, store reply content, handle bounces & unsubscribes.

Each fetched message is classified:
- bounce   (mailer-daemon / delivery-failure with a permanent reason): extract the failed
  recipient, mark that lead's email_status='invalid' so every send path skips it. The
  notice itself is NOT filed in the inbox — the inbox is for messages worth reading, and
  the only useful part of a bounce (never mail this address again) is already applied.
- delayed  (same sender, temporary reason): counted in the poll summary and dropped —
  the address is still good, the server was just slow, so there is nothing to read or do.
- unsubscribe (remove me / stop ...): set lead.do_not_contact=1 (suppressed everywhere)
  and also mark replied (it IS a human answer, and must stop sequences).
- reply    : store content, mark replied via repository.mark_replied, which stops any
  active sequence enrollment so the follow-up queue never chases someone who answered.

Matched messages land in inbox_messages so the salesperson reads replies inside the
tool instead of digging through Gmail. A UNIQUE index dedupes re-polls.

The IMAP fetch is isolated behind a `fetch_messages` callable so tests inject fake
messages and never touch the network.
"""
import datetime as _dt
import email
import imaplib
import re
import json
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime

from app import contacts, mailboxes, repository, settings
from app.channels.email_adapter import GMAIL_USER, get_password

# Allow-list what an address may contain rather than blacklisting delimiters: Gmail's
# bounce notice is localised, so the failed address is followed immediately by a
# full-width comma ("...contato@ledwave.com.br，或该地址无法接收邮件") which a
# blacklist regex swallows into the match, and the lead lookup then never hits.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
_BOUNCE_FROM_RE = re.compile(r"mailer-daemon|postmaster|mail delivery", re.I)
_BOUNCE_SUBJ_RE = re.compile(
    r"undeliver|delivery status|delivery has failed|returned to sender|failure notice|"
    r"delivery incomplete|address not found", re.I)
# Only a permanent failure justifies burning the address. A delay notice ("we'll keep
# trying for 44 hours") arrives from the same mailer-daemon and looks identical, so
# without this an ordinary greylist wobble would mark a live lead unmailable forever.
_PERMANENT_RE = re.compile(
    r"\b5\.\d\.\d\b|\b55[0-3]\b|no such user|does not exist|user unknown|"
    r"address not found|mailbox (is )?unavailable|recipient (address )?rejected|"
    r"找不到地址|地址不存在|无法接收邮件", re.I)
_UNSUB_RE = re.compile(
    r"unsubscribe|remove me|take me off|stop (contacting|emailing|sending|messaging)|"
    r"do( not|n'?t) (contact|email)", re.I)

_BODY_LIMIT = 4000

_K_LAST_AT = "reply_sync_last_at"
_K_LAST_SUCCESS = "reply_sync_last_success_at"
_K_LAST_STATUS = "reply_sync_last_status"
_K_LAST_RESULT = "reply_sync_last_result"

SINCE_DAYS_MIN = 7
SINCE_DAYS_MAX = 30


def adaptive_since_days(conn) -> int:
    """Look back far enough to cover the gap since the last successful poll.
    A fixed 7-day window silently drops every reply that arrived while polling was
    broken for longer than a week — and polling can be broken for weeks unnoticed."""
    last = settings.get(conn, _K_LAST_SUCCESS)
    if not last:
        return SINCE_DAYS_MAX
    try:
        when = _dt.datetime.fromisoformat(last)
    except ValueError:
        return SINCE_DAYS_MAX
    if when.tzinfo is None:
        when = when.replace(tzinfo=_dt.UTC)
    gap = (_dt.datetime.now(_dt.UTC) - when).days
    return max(SINCE_DAYS_MIN, min(SINCE_DAYS_MAX, gap + 2))


def _norm(addr: str) -> str:
    return (addr or "").strip().lower()


def _decode(value) -> str:
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:  # noqa: BLE001
        return value or ""


def _plain_body(msg) -> str:
    parts = msg.walk() if msg.is_multipart() else [msg]
    fallback = ""
    for part in parts:
        if part.get_content_maintype() != "text":
            continue
        try:
            text = part.get_payload(decode=True).decode(
                part.get_content_charset() or "utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            continue
        if part.get_content_subtype() == "plain":
            return text[:_BODY_LIMIT]
        fallback = fallback or re.sub(r"<[^>]+>", " ", text)
    return fallback[:_BODY_LIMIT]


def fetch_mailbox_messages(mailbox: dict, since_days: int = 7) -> list[dict]:
    """Fetch full messages from one configured mailbox without changing read state."""
    host = mailbox.get("imap_host") or mailboxes.infer_imap_host(mailbox.get("smtp_host", ""))
    if not host:
        raise RuntimeError("IMAP server missing")
    pw = mailbox.get("password")
    if not pw:
        raise RuntimeError("mailbox password missing")
    since = (_dt.date.today() - _dt.timedelta(days=since_days)).strftime("%d-%b-%Y")
    messages: list[dict] = []
    with imaplib.IMAP4_SSL(host, int(mailbox.get("imap_port") or 993)) as im:
        im.login(mailbox.get("username") or mailbox.get("email"), pw)
        im.select("INBOX")
        typ, data = im.search(None, f'(SINCE "{since}")')
        if typ != "OK":
            return []
        for num in data[0].split():
            typ, msg_data = im.fetch(num, "(BODY.PEEK[])")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            display_name, addr = parseaddr(msg.get("From", ""))
            try:
                received = parsedate_to_datetime(msg.get("Date")).isoformat()
            except Exception:  # noqa: BLE001
                received = ""
            messages.append({
                "from_addr": _norm(addr),
                "from_name": _decode(display_name),
                "subject": _decode(msg.get("Subject", "")),
                "body": _plain_body(msg),
                "received_at": received,
            })
    return messages


def fetch_recent_messages(since_days: int = 7) -> list[dict]:
    """Backward-compatible fetch for the legacy fallback Gmail."""
    pw = get_password()
    if not pw:
        raise RuntimeError("Gmail app password missing (~/.gmail_app_password or GMAIL_APP_PASSWORD)")
    return fetch_mailbox_messages({
        "email": GMAIL_USER,
        "username": GMAIL_USER,
        "password": pw,
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
    }, since_days)


def test_mailbox(mailbox: dict) -> None:
    """Verify IMAP credentials without fetching or changing any message."""
    host = mailbox.get("imap_host") or mailboxes.infer_imap_host(mailbox.get("smtp_host", ""))
    if not host:
        raise RuntimeError("IMAP server missing")
    with imaplib.IMAP4_SSL(host, int(mailbox.get("imap_port") or 993)) as im:
        im.login(mailbox.get("username") or mailbox.get("email"), mailbox.get("password"))


def _store(conn, lead_no: int, kind: str, m: dict,
           contact_id: int | None = None) -> int | None:
    cur = conn.execute(
        "INSERT OR IGNORE INTO inbox_messages(lead_no, contact_id, channel, kind, from_addr, subject, body, received_at)"
        " VALUES (?, ?, 'email', ?, ?, ?, ?, ?)",
        (lead_no, contact_id, kind, _norm(m.get("from_addr")), m.get("subject") or "",
         m.get("body") or "", m.get("received_at") or ""))
    return cur.lastrowid if cur.rowcount > 0 else None


# Domains where the local-part identifies a person, not a company — a reply from
# john@gmail.com tells us nothing about our lead info@gmail.com, so never match by domain.
_FREE_MAIL = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "msn.com",
    "yahoo.com", "yahoo.co.uk", "yahoo.com.br", "ymail.com", "icloud.com", "me.com",
    "aol.com", "protonmail.com", "proton.me", "gmx.com", "zoho.com", "mail.com",
    "qq.com", "163.com", "126.com", "sina.com", "foxmail.com", "naver.com", "hanmail.net",
}


def _domain(addr: str) -> str:
    return addr.split("@", 1)[1] if "@" in addr else ""


def _lead_emails(conn) -> dict[str, int]:
    return contacts.email_leads(conn)


def _by_domain(by_email: dict[str, int]) -> dict[str, list[int]]:
    """Company domain -> its lead numbers (free-mail domains excluded)."""
    out: dict[str, list[int]] = {}
    for addr, no in by_email.items():
        dom = _domain(addr)
        if dom and dom not in _FREE_MAIL:
            if no not in out.setdefault(dom, []):
                out[dom].append(no)
    return out


def _resolve_sender(sender: str, by_email: dict[str, int], by_domain: dict[str, list[int]]) -> list[int]:
    """Lead numbers a reply belongs to: exact email first, then same company domain.
    Domain fallback catches the very common case of a person replying from their own
    address to mail we sent to info@/sales@ at the same company."""
    if sender in by_email:
        return [by_email[sender]]
    return by_domain.get(_domain(sender), [])


def process_messages(conn, messages: list[dict]) -> dict:
    """Classify and store fetched messages against the lead base."""
    by_email = _lead_emails(conn)
    by_domain = _by_domain(by_email)
    replies_n = bounces = delayed = unsubs = stored = 0
    lead_nos: list[int] = []
    for m in messages:
        sender = _norm(m.get("from_addr"))
        subject, body = m.get("subject") or "", m.get("body") or ""
        if _BOUNCE_FROM_RE.search(sender) or _BOUNCE_SUBJ_RE.search(subject):
            permanent = bool(_PERMANENT_RE.search(f"{subject}\n{body}"))
            failed = [a for a in _EMAIL_RE.findall(body) if _norm(a) in by_email]
            for addr in {_norm(a) for a in failed}:
                no = by_email[addr]
                # Unproven failures are shown, never acted on — a wrongly burned address
                # costs a real lead, a retained dead one only costs one more send.
                if permanent:
                    conn.execute("UPDATE leads SET email_status='invalid' WHERE no=?", (no,))
                    contacts.sync_primary_email_status(conn, no, "invalid")
                    bounces += 1
                else:
                    delayed += 1
                lead_nos.append(no)
            continue
        matched = _resolve_sender(sender, by_email, by_domain)
        if not matched:
            continue
        kind = "unsubscribe" if _UNSUB_RE.search(subject) or _UNSUB_RE.search(body) else "reply"
        # A reply/unsub from someone at the company applies to every lead we hold there:
        # store the message once (on the first), stop chasing all of them.
        exact_contact = contacts.find_email(conn, sender, lead_no=matched[0])
        if exact_contact is None and kind == "reply" and len(matched) == 1:
            # A person often replies from john@company.com after outreach went to
            # info@company.com. The unique company-domain match is strong enough to
            # adopt that person as a secondary contact, but never make them the send
            # target when a primary contact already exists.
            try:
                exact_contact = contacts.create(
                    conn, matched[0], {
                        "name": m.get("from_name") or None,
                        "email": sender,
                        "role": "other",
                    }, source="reply")
            except contacts.ContactValidation:
                exact_contact = None
        inbox_id = _store(
            conn, matched[0], kind, m,
            contact_id=exact_contact["id"] if exact_contact else None)
        if inbox_id:
            stored += 1
            if kind == "reply":
                from app import activities
                activities.create_reply_task(conn, inbox_id)
        for no in matched:
            if kind == "unsubscribe":
                conn.execute("UPDATE leads SET do_not_contact=1 WHERE no=?", (no,))
            repository.mark_replied(conn, no, "email")
            lead_nos.append(no)
        if kind == "unsubscribe":
            unsubs += 1
        else:
            replies_n += 1
    conn.commit()
    return {"replies": replies_n, "bounces": bounces, "delayed": delayed,
            "unsubscribes": unsubs, "stored": stored, "lead_nos": lead_nos}


def match_and_mark(conn, sender_emails: list[str]) -> dict:
    """Mark leads whose email matches a sender as replied on the email channel.
    Returns {matched, newly_replied, lead_nos}."""
    wanted = {_norm(a) for a in sender_emails if a}
    if not wanted:
        return {"matched": 0, "newly_replied": 0, "lead_nos": []}
    by_email = _lead_emails(conn)
    newly, lead_nos = 0, []
    for addr, no in by_email.items():
        if addr not in wanted:
            continue
        lead_nos.append(no)
        already = conn.execute(
            "SELECT 1 FROM outreach WHERE lead_no=? AND channel='email' AND status='replied'",
            (no,)).fetchone()
        repository.mark_replied(conn, no, "email")
        if not already:
            newly += 1
    return {"matched": len(lead_nos), "newly_replied": newly, "lead_nos": lead_nos}


def poll_replies(conn, fetch_messages=fetch_recent_messages, since_days: int = 7) -> dict:
    return process_messages(conn, fetch_messages(since_days))


def poll_all_replies(conn, fetcher=fetch_mailbox_messages, since_days: int | None = None) -> dict:
    """Poll every active mailbox. One bad account must not hide replies in the others.
    since_days=None widens the window to cover however long polling has been down."""
    if since_days is None:
        since_days = adaptive_since_days(conn)
    configured = [m for m in mailboxes.list_mailboxes(conn, include_secrets=True) if m["active"]]
    targets = configured
    if not targets:
        pw = get_password()
        if pw:
            targets = [{
                "email": GMAIL_USER, "username": GMAIL_USER, "password": pw,
                "imap_host": "imap.gmail.com", "imap_port": 993,
            }]
    if not targets:
        settings.set_value(conn, _K_LAST_STATUS, "error")
        settings.set_value(conn, _K_LAST_RESULT, "未配置可用的收件邮箱")
        raise RuntimeError("no active mailbox and fallback Gmail password missing")

    totals = {"replies": 0, "bounces": 0, "delayed": 0, "unsubscribes": 0, "stored": 0}
    lead_nos: list[int] = []
    errors: list[dict] = []
    checked = 0
    for mailbox in targets:
        try:
            result = process_messages(conn, fetcher(mailbox, since_days))
        except Exception as exc:  # noqa: BLE001 — continue with the remaining accounts
            errors.append({"email": mailbox.get("email", ""), "error": str(exc)[:200]})
            continue
        checked += 1
        for key in totals:
            totals[key] += result[key]
        lead_nos.extend(result["lead_nos"])

    status = "success" if not errors else ("partial" if checked else "error")
    now = _dt.datetime.now(_dt.UTC).isoformat()
    summary = {
        **totals,
        "lead_nos": lead_nos,
        "mailboxes_checked": checked,
        "mailboxes_total": len(targets),
        "errors": errors,
        "since_days": since_days,
    }
    settings.set_value(conn, _K_LAST_AT, now)
    settings.set_value(conn, _K_LAST_STATUS, status)
    settings.set_value(conn, _K_LAST_RESULT, json.dumps(summary, ensure_ascii=False))
    # Only a clean sweep may narrow the next look-back window; a partial run leaves the
    # failed mailbox's gap uncovered.
    if status == "success":
        settings.set_value(conn, _K_LAST_SUCCESS, now)
    return summary

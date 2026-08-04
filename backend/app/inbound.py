"""Inbound detection for the browser channels (WhatsApp / Instagram).

Email replies arrive over IMAP. WhatsApp and Instagram have no such feed, so 527 of
the 616 touched leads had no inbound path at all — a customer answering on WhatsApp
was invisible to the funnel, which is the real reason 已回复 sat at 0.

What this deliberately does NOT do: open the conversation. Clicking into a thread marks
it read on Allen's phone too, so the scan reads only what the thread list already
shows — who it is, and the last-message preview. That is enough to know someone
answered and roughly about what; the full thread is one click away in the app itself.

The browser half lives in playwright_engine; everything here is pure data so the
matching rules are testable without a browser.
"""
import datetime as _dt
import json
import re

from app import contacts, repository, settings

CHANNELS = ("whatsapp", "instagram")

_K_LAST_AT = "social_scan_last_at"
_K_LAST_DATE = "social_scan_last_date"
_K_LAST_RESULT = "social_scan_last_result"

# A thread title has to carry this many digits before it can be a phone number;
# below that it is a display name that happens to contain a digit.
_MIN_PHONE_DIGITS = 8
_PREVIEW_LIMIT = 500


def normalize_phone(raw: str) -> str:
    return re.sub(r"\D", "", raw or "")


def normalize_handle(raw: str) -> str:
    return (raw or "").strip().lstrip("@").lower()


def _lead_phones(conn) -> dict[str, int]:
    return contacts.phone_leads(conn, _MIN_PHONE_DIGITS)


def _lead_handles(conn) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in conn.execute(
            "SELECT no, instagram FROM leads WHERE instagram IS NOT NULL AND instagram != ''"):
        handle = normalize_handle(r["instagram"])
        if handle:
            out[handle] = r["no"]
    return out


def match_phone(sender: str, by_phone: dict[str, int]) -> int | None:
    """WhatsApp shows a saved contact's name but an unsaved number as '+55 11 9999-9999',
    and the stored lead phone may or may not carry the country code. Try the whole
    number, then the tail — but only when exactly one lead owns that tail, because a
    wrong match would mark the wrong customer as having replied."""
    digits = normalize_phone(sender)
    if len(digits) < _MIN_PHONE_DIGITS:
        return None
    if digits in by_phone:
        return by_phone[digits]
    tail = digits[-_MIN_PHONE_DIGITS:]
    hits = {no for num, no in by_phone.items() if num.endswith(tail)}
    return hits.pop() if len(hits) == 1 else None


def match_handle(sender: str, by_handle: dict[str, int]) -> int | None:
    return by_handle.get(normalize_handle(sender))


# Instagram's thread list shows the profile's display name, never the @handle, and that
# name usually trails a tagline: "LED ABC - Painéis de LED" for the lead stored as
# "LED ABC". Cut at the first separator, then compare on letters and digits only.
_NAME_TAIL = re.compile(r"\s+[|｜·•/–—]\s*|\s+-\s+")
_MIN_NAME_CHARS = 6


def normalize_name(raw: str) -> str:
    head = _NAME_TAIL.split((raw or "").lower(), 1)[0]
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", head, flags=re.UNICODE)).strip()


def _lead_names(conn) -> list[tuple[str, int]]:
    return [(normalize_name(r["company_en"]), r["no"]) for r in conn.execute(
        "SELECT no, company_en FROM leads WHERE company_en IS NOT NULL AND company_en != ''")
        if normalize_name(r["company_en"])]


def match_name(sender: str, by_name: list[tuple[str, int]]) -> int | None:
    """Exact first, then a prefix relation in either direction — the display name may be
    shorter than the stored company ("Light It Up AV" vs "Light It Up AV & Turf") or
    longer. Anything ambiguous is dropped: a wrong match marks the wrong customer as
    having replied and silently ends their follow-up."""
    name = normalize_name(sender)
    if len(name) < _MIN_NAME_CHARS:
        return None
    exact = {no for n, no in by_name if n == name}
    if len(exact) == 1:
        return exact.pop()
    if exact:
        return None
    near = {no for n, no in by_name
            if len(n) >= _MIN_NAME_CHARS and (n.startswith(name) or name.startswith(n))}
    return near.pop() if len(near) == 1 else None


# --- turning a scraped row into a thread -------------------------------------------
# innerText is layout-dependent: once a row scrolls out of the viewport it collapses to
# one unbroken string, merging the name into the preview ("Adam Ortiz你: Hi! I'm Allen…").
# That left the preview empty, so every off-screen thread read as an inbound reply —
# 112 of 193 threads were false positives. Leaf textContent is layout-independent, so
# rows are rebuilt from that instead, and the parsing lives here where it can be tested.
_NOISE = re.compile(
    r"^[·•|]$|^\d+\s*(周|天|小时|分钟|秒|w|d|h|m|s|min)$|"
    r"^(已验证|verified|在线|active now|刚刚|now|yesterday|昨天)$", re.I)
_OUTGOING = re.compile(r"^\s*(you|你|您)\s*[:：]|^\s*(you sent|你发送了|您发送了)", re.I)
# Instagram writes its own notices into the preview slot; they are messages from nobody.
_NOTICE = re.compile(
    r"无法接收消息|无法发送|不接收任何人|并非所有人都可以发消息|撤回了一条消息|"
    r"can'?t receive|not everyone can message|unsent a message", re.I)

# An autoresponder is not a human answering. Recording one as a reply would stop the
# follow-up sequence for a lead nobody has actually read yet — worse than the blind spot
# this replaces. So these are shown in the inbox and deliberately not acted on.
# Biased towards catching too many: a real reply misread as auto still shows up and the
# lead just keeps its follow-ups, while the reverse silently ends a live conversation.
_AUTO_REPLY = re.compile(
    r"thank(s| you) for (contacting|reaching out|connecting|messaging|your (message|inquiry))|"
    r"we('| ha)ve received your|we ?('|wi)?ll (get back|be back|reply)|be back (in|soon|shortly)|"
    r"for any inquir|please send us your|automatic(ally)? repl|auto-?repl|away from|"
    r"感谢您的(留言|来信)|会在短时间内为您解答|我们已收到|自动回复|"
    r"메시지가 접수되었습니다|문의해주셔서 감사합니다|감사합니다\.?$", re.I)


# "AVL 发送了附件。" is Instagram's placeholder for a message with no text at all — an
# image or a GIF card, which is what a business account's automation usually sends. It
# proves something arrived, not that a human wrote it, so it is filed to be looked at
# but never marks the lead replied: that would silently end the follow-up.
_NO_TEXT = re.compile(
    r"发送了附件|发送了一(张|条|个)|sent an attachment|sent (a|an) (photo|video|image|reel|post|gif|attachment)",
    re.I)


def is_auto_reply(text: str) -> bool:
    return bool(_AUTO_REPLY.search(text or ""))


def is_no_text(text: str) -> bool:
    return bool(_NO_TEXT.search(text or ""))


def _clean(leaves) -> list[str]:
    return [p.strip() for p in (leaves or []) if p and p.strip()]


def instagram_thread(leaves) -> dict | None:
    """Instagram row -> thread dict. Direction is only knowable from the preview prefix,
    so a row without a readable preview is dropped rather than guessed inbound."""
    parts = _clean(leaves)
    if not parts:
        return None
    name = parts[0]
    preview = next((p for p in parts[1:] if not _NOISE.match(p)), "")
    if not preview or _NOTICE.search(preview):
        return None
    return {"sender": name, "name": name, "preview": preview,
            "outgoing": bool(_OUTGOING.search(preview)), "unread": False}


def whatsapp_thread(leaves, title=None, outgoing=False, unread=False) -> dict | None:
    """WhatsApp row -> thread dict. Direction comes from the delivery-status icon, a DOM
    query rather than text, so it stays correct even when the preview text is garbled."""
    parts = _clean(leaves)
    name = (title or (parts[0] if parts else "")).strip()
    if not name:
        return None
    body = [p for p in parts if p != name and not _NOISE.match(p)]
    preview = max(body, key=len) if body else ""
    return {"sender": name, "name": name, "preview": preview,
            "outgoing": bool(outgoing), "unread": bool(unread)}


def _already_recorded(conn, lead_no: int, channel: str, body: str) -> bool:
    """The thread list has no stable message id and its timestamps are relative
    ('昨天'), so identical preview text from the same lead is treated as the same
    message. A genuinely new message changes the preview and lands as a new row."""
    return conn.execute(
        "SELECT 1 FROM inbox_messages WHERE lead_no=? AND channel=? AND body=?",
        (lead_no, channel, body)).fetchone() is not None


def process_threads(conn, channel: str, threads: list[dict]) -> dict:
    """Turn scraped thread rows into inbox messages and replied flags.

    Each row: {sender, name, preview, outgoing, unread}. `outgoing` means the last
    message in that thread is ours — the overwhelming majority of threads, and not
    a reply."""
    if channel not in CHANNELS:
        raise ValueError(f"unsupported channel {channel}")
    by_name = _lead_names(conn)
    if channel == "whatsapp":
        primary, lookup = match_phone, _lead_phones(conn)
    else:
        primary, lookup = match_handle, _lead_handles(conn)

    def resolve(sender: str) -> int | None:
        # WhatsApp shows a saved contact's name and Instagram only ever shows the
        # display name, so the company-name fallback is what makes those threads
        # attributable at all.
        return primary(sender, lookup) or match_name(sender, by_name)

    replies = stored = outgoing = auto = 0
    unmatched: list[str] = []
    lead_nos: list[int] = []
    now = _dt.datetime.now(_dt.UTC).isoformat()
    for t in threads:
        if t.get("outgoing"):
            outgoing += 1
            continue
        sender = (t.get("sender") or "").strip()
        no = resolve(sender) if sender else None
        if no is None:
            if sender:
                unmatched.append(sender[:60])
            continue
        body = (t.get("preview") or "")[:_PREVIEW_LIMIT]
        kind = "auto" if is_auto_reply(body) else ("attachment" if is_no_text(body) else "reply")
        robot = kind != "reply"
        if robot:
            auto += 1
        else:
            replies += 1
            lead_nos.append(no)
        if not _already_recorded(conn, no, channel, body):
            contact = contacts.find_phone(conn, sender, no) if channel == "whatsapp" else None
            cur = conn.execute(
                "INSERT INTO inbox_messages(lead_no, contact_id, channel, kind, from_addr, subject, body, received_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (no, contact["id"] if contact else None, channel, kind, sender,
                 (t.get("name") or sender)[:120], body, now))
            stored += 1
            if kind == "reply":
                from app import activities
                activities.create_reply_task(conn, cur.lastrowid)
        if not robot:
            repository.mark_replied(conn, no, channel)
    conn.commit()
    return {"channel": channel, "threads": len(threads), "replies": replies,
            "auto": auto, "stored": stored, "outgoing": outgoing,
            "unmatched": unmatched[:20], "lead_nos": lead_nos}


def scan(conn, channel: str, scanner) -> dict:
    """Scrape one channel and record what came back. `scanner(channel) -> rows` is the
    browser seam so tests never need Playwright."""
    result = process_threads(conn, channel, scanner(channel))
    _record(conn, [result])
    return result


def scan_all(conn, scanner, channels=CHANNELS) -> dict:
    """Scan every browser channel. One broken channel must not hide the other's replies
    — Instagram's markup shifts far more often than WhatsApp's."""
    results, errors = [], []
    for channel in channels:
        try:
            results.append(process_threads(conn, channel, scanner(channel)))
        except Exception as exc:  # noqa: BLE001 — continue with the remaining channels
            errors.append({"channel": channel, "error": str(exc)[:200]})
    return _record(conn, results, errors)


def _record(conn, results: list[dict], errors: list[dict] | None = None) -> dict:
    errors = errors or []
    summary = {
        "replies": sum(r["replies"] for r in results),
        "auto": sum(r["auto"] for r in results),
        "stored": sum(r["stored"] for r in results),
        "threads": sum(r["threads"] for r in results),
        # An inbound message we cannot pin to a lead is still someone talking to Allen.
        # Dropping it silently would rebuild the blind spot this whole thing exists to close.
        "unmatched": [u for r in results for u in r["unmatched"]],
        "channels": results,
        "errors": errors,
    }
    now = _dt.datetime.now(_dt.UTC)
    settings.set_value(conn, _K_LAST_AT, now.isoformat())
    settings.set_value(conn, _K_LAST_RESULT, json.dumps(summary, ensure_ascii=False))
    if results and not errors:
        settings.set_value(conn, _K_LAST_DATE, now.date().isoformat())
    return summary


def status(conn) -> dict:
    raw = settings.get(conn, _K_LAST_RESULT)
    try:
        last = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        last = None
    return {"last_at": settings.get(conn, _K_LAST_AT) or None,
            "last_date": settings.get(conn, _K_LAST_DATE) or None,
            "last_result": last}


def should_scan_today(conn, now: _dt.datetime | None = None, window=(9, 20)) -> bool:
    now = now or _dt.datetime.now()
    if not (window[0] <= now.hour < window[1]):
        return False
    return settings.get(conn, _K_LAST_DATE) != now.date().isoformat()

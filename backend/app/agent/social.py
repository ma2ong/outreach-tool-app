"""Reading and answering WhatsApp / Instagram / Facebook conversations.

The daily scan reads the chat list and never opens a thread, so it leaves the phone's
unread badges alone — but a one-line preview is not something you can write a reply
from. Allen's call (2026-08-19): his WA and IG are not used for anything else, so
losing the unread marks is an acceptable price for real drafts.

So this module opens the thread on demand, and only for a message that is already
classified as worth answering. Reading every conversation on a schedule would burn the
unread state of the whole inbox for no gain.
"""
from __future__ import annotations

import datetime as dt
import json

CHANNELS = ("whatsapp", "instagram", "facebook")
_CONTACT_COL = {"whatsapp": "phone", "instagram": "instagram", "facebook": "facebook"}
THREAD_LIMIT = 20


class NoTarget(RuntimeError):
    """We know they replied but not where to write back."""


def target_for(conn, lead_no: int, channel: str) -> str:
    col = _CONTACT_COL.get(channel)
    if not col:
        raise NoTarget(f"不支持的渠道 {channel}")
    row = conn.execute(f"SELECT {col} AS handle FROM leads WHERE no=?", (lead_no,)).fetchone()
    raw = (row["handle"] if row else "") or ""
    if channel == "whatsapp":
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            raise NoTarget("客户没有可用的 WhatsApp 号码")
        return digits
    handle = raw.strip().lstrip("@")
    if not handle:
        raise NoTarget(f"客户没有可用的 {channel} 账号")
    return handle.rstrip("/").rsplit("/", 1)[-1]


def stored_thread(message: dict) -> list[dict]:
    try:
        return json.loads(message.get("thread_json") or "[]")
    except (TypeError, json.JSONDecodeError):
        return []


def fetch_thread(conn, message: dict, engine=None) -> list[dict]:
    """Open the conversation, store what it says, return the messages.

    Returns [] when the thread could not be read; the caller falls back to a nudge
    rather than drafting from the preview.
    """
    existing = stored_thread(message)
    if existing:
        return existing
    if engine is None:
        # The one live browser session, shared with the channels API — a second engine
        # would mean a second browser profile and a second login.
        from app.api.channels import ENGINE
        engine = ENGINE
    target = target_for(conn, message["lead_no"], message["channel"])
    thread = engine.read_thread(message["channel"], target, THREAD_LIMIT) or []
    conn.execute("UPDATE inbox_messages SET thread_json=?, thread_read_at=? WHERE id=?",
                 (json.dumps(thread, ensure_ascii=False),
                  dt.datetime.now(dt.UTC).isoformat(), message["id"]))
    conn.commit()
    return thread


def last_inbound(thread: list[dict]) -> str:
    """The customer's most recent turn — several consecutive messages read as one."""
    block: list[str] = []
    for item in reversed(thread):
        if item.get("outgoing"):
            break
        text = (item.get("text") or "").strip()
        if text:
            block.append(text)
    return "\n".join(reversed(block)).strip()


def transcript(thread: list[dict]) -> str:
    return "\n".join(
        f"{'US' if m.get('outgoing') else 'THEM'}: {(m.get('text') or '').strip()}"
        for m in thread if (m.get("text") or "").strip())

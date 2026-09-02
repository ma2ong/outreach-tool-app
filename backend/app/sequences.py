"""Follow-up sequences: multi-step outreach that generates a manual-send due queue.

Design boundary: a sequence never sends by itself. `due_queue` surfaces which
enrolled leads are due for their next touch today; the business rep reviews and
sends through the normal rate-limited /api/send path. This keeps the anti-ban
limits and platform-ToS boundary intact while adding follow-up structure.

Enrollment drives eligibility (not the outreach 'messaged' exclusion), so step 2+
can reach a lead that step 1 already messaged. Replies stop the enrollment.
"""
import datetime as _dt
import re

# A sequence written in Korean can only go to Korean companies. The reverse is not
# restricted: English is the working language of the trade, and a Korean buyer reading
# an English cold email is ordinary.
#
# The guard is enforced both when enrolling and again when building the due/send queue.
# That second boundary matters for historical bad enrollments created before this rule.
_KOREAN_TEXT = re.compile(r"[가-힣]")
_KOREAN_COUNTRIES = {"south korea", "korea", "republic of korea", "대한민국", "한국"}


def _today() -> str:
    return _dt.date.today().isoformat()


def _plus_days(date_iso: str, days: int) -> str:
    return (_dt.date.fromisoformat(date_iso) + _dt.timedelta(days=days)).isoformat()


def create_sequence(conn, name: str, channel: str, steps: list[dict]) -> int:
    """steps: [{day_offset, subject?, body, image?}] in send order."""
    cur = conn.execute(
        "INSERT INTO sequences(name, channel, active, created_at) VALUES (?, ?, 1, ?)",
        (name, channel, _dt.datetime.now(_dt.UTC).isoformat()))
    sid = cur.lastrowid
    for i, s in enumerate(steps):
        conn.execute(
            "INSERT INTO sequence_steps(sequence_id, step_order, day_offset, subject, body, image)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (sid, i, int(s.get("day_offset", 0)), s.get("subject"), s["body"], s.get("image")))
    conn.commit()
    return sid


def _steps(conn, sid: int) -> list[dict]:
    from app.sequence_edit import ensure_schema

    ensure_schema(conn)
    return [dict(r) | {"edited": bool(r["edited"])} for r in conn.execute(
        "SELECT step_order, day_offset, subject, body, image, edited FROM sequence_steps"
        " WHERE sequence_id=? ORDER BY step_order", (sid,))]


def list_sequences(conn) -> list[dict]:
    seqs = []
    for r in conn.execute("SELECT id, name, channel, active FROM sequences ORDER BY id"):
        d = dict(r)
        d["active"] = bool(d["active"])
        d["steps"] = _steps(conn, r["id"])
        d["enrolled"] = conn.execute(
            "SELECT COUNT(*) c FROM sequence_enrollments WHERE sequence_id=? AND status='active'",
            (r["id"],)).fetchone()["c"]
        seqs.append(d)
    return seqs


def get_sequence(conn, sid: int) -> dict | None:
    r = conn.execute("SELECT id, name, channel, active FROM sequences WHERE id=?", (sid,)).fetchone()
    if r is None:
        return None
    d = dict(r)
    d["active"] = bool(d["active"])
    d["steps"] = _steps(conn, sid)
    d["enrolled"] = conn.execute(
        "SELECT COUNT(*) c FROM sequence_enrollments WHERE sequence_id=? AND status='active'",
        (sid,)).fetchone()["c"]
    return d


def is_korean_sequence(conn, sid: int) -> bool:
    """Whether the actual customer-facing copy is Korean.

    The sequence name is deliberately ignored. Operators may label an English sequence
    in Korean for their own convenience; only subject/body text is a sending condition.
    """
    text = " ".join(
        f"{s.get('subject') or ''} {s.get('body') or ''}" for s in _steps(conn, sid))
    return bool(_KOREAN_TEXT.search(text))


def _is_korean_country(value: str | None) -> bool:
    return str(value or "").strip().lower() in _KOREAN_COUNTRIES


def language_blocked(conn, sid: int, lead_nos: list[int]) -> list[int]:
    """Leads this sequence must not be sent to because of its language."""
    if not lead_nos or not is_korean_sequence(conn, sid):
        return []
    placeholders = ",".join("?" * len(lead_nos))
    rows = conn.execute(
        f"SELECT no, country FROM leads WHERE no IN ({placeholders})", lead_nos).fetchall()
    return [r["no"] for r in rows if not _is_korean_country(r["country"])]


def enroll_leads(conn, sid: int, lead_nos: list[int]) -> int:
    """Enrol leads at step 0; due today (day_offset of step 0, usually 0).
    Skips leads that already replied on this sequence's channel, leads the sequence's
    language rules out, and dup enrollments."""
    steps = _steps(conn, sid)
    if not steps:
        return 0
    seq = conn.execute("SELECT channel FROM sequences WHERE id=?", (sid,)).fetchone()
    if seq is None:
        return 0
    channel = seq["channel"]
    today = _today()
    first_due = _plus_days(today, steps[0]["day_offset"])
    wrong_language = set(language_blocked(conn, sid, lead_nos))
    enrolled = 0
    for no in lead_nos:
        if no in wrong_language:
            continue
        replied = conn.execute(
            "SELECT 1 FROM outreach WHERE lead_no=? AND channel=? AND status='replied'",
            (no, channel)).fetchone()
        if replied:
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO sequence_enrollments"
            "(lead_no, sequence_id, current_step, status, enrolled_at, next_due_date)"
            " VALUES (?, ?, 0, 'active', ?, ?)",
            (no, sid, today, first_due))
        enrolled += cur.rowcount
    conn.commit()
    return enrolled


def due_queue(conn, channel: str | None = None) -> list[dict]:
    """Active enrollments safe and due for their next touch today.

    Language is checked again here, not only at enrollment. `sequence_send.send_due`
    derives its sendable IDs from this queue, so a historical wrong-language enrollment
    cannot bypass the rule merely because it predates the enrollment guard.
    """
    sql = (
        "SELECT e.id enrollment_id, e.lead_no, e.sequence_id, e.current_step,"
        "       l.company_en, l.country AS _lead_country, s.name sequence_name, s.channel,"
        "       st.subject, st.body, st.image, st.step_order"
        " FROM sequence_enrollments e"
        " JOIN sequences s ON s.id = e.sequence_id"
        " JOIN leads l ON l.no = e.lead_no"
        " JOIN sequence_steps st ON st.sequence_id = e.sequence_id AND st.step_order = e.current_step"
        " WHERE e.status='active' AND e.next_due_date <= date('now')"
        "   AND COALESCE(l.do_not_contact, 0) = 0"
        "   AND l.no NOT IN (SELECT lead_no FROM send_log"
        "       WHERE date(sent_at, 'localtime')=date('now', 'localtime'))"
        "   AND l.no NOT IN (SELECT lead_no FROM outreach WHERE channel=s.channel AND status='replied')")
    params: list = []
    if channel:
        sql += " AND s.channel = ?"
        params.append(channel)
    sql += " ORDER BY e.next_due_date, e.lead_no"
    rows = [dict(r) for r in conn.execute(sql, params)]
    korean_by_sequence: dict[int, bool] = {}
    safe: list[dict] = []
    for row in rows:
        sid = row["sequence_id"]
        korean = korean_by_sequence.setdefault(sid, is_korean_sequence(conn, sid))
        country = row.pop("_lead_country", None)
        if korean and not _is_korean_country(country):
            continue
        safe.append(row)
    return safe


# The lead column a sequence needs an address in, per channel.
_CHANNEL_ADDRESS = {"email": "email", "whatsapp": "phone",
                    "instagram": "instagram", "facebook": "facebook"}


def block_unsendable(conn) -> int:
    """Park active enrollments that can never send, so the due queue tells the truth.

    An enrollment whose lead holds no address on the sequence's channel — or an email
    that has already hard-bounced — is skipped by the send path every single day and
    never advances: it stays 'active' forever and pads today's queue with work nobody
    can do. 'blocked' keeps the row for the record while dropping it out of due_queue.
    """
    blocked = 0
    for channel, col in _CHANNEL_ADDRESS.items():
        bounced = " OR email_status='invalid'" if channel == "email" else ""
        cur = conn.execute(
            f"""UPDATE sequence_enrollments SET status='blocked'
                WHERE status='active'
                  AND sequence_id IN (SELECT id FROM sequences WHERE channel=?)
                  AND lead_no IN (SELECT no FROM leads
                                  WHERE {col} IS NULL OR {col}='' {bounced})""",
            (channel,))
        blocked += cur.rowcount
    conn.commit()
    return blocked


def reopen_sendable(conn) -> int:
    """Un-park enrollments whose address came back, so a repaired lead rejoins follow-up.

    block_unsendable on its own is a one-way door. A re-verification routinely recovers
    addresses a transient DNS failure had marked invalid — 35 of them on the first real
    run — and without this their enrollments would stay parked for good, quietly costing
    more leads than the parking ever saved. 'blocked' is only ever written by
    block_unsendable, so reversing it on the same condition cannot disturb a lead that
    replied or completed. The past next_due_date puts them straight back in today's queue,
    which is right: they are overdue.
    """
    reopened = 0
    for channel, col in _CHANNEL_ADDRESS.items():
        live = " AND COALESCE(email_status,'') != 'invalid'" if channel == "email" else ""
        cur = conn.execute(
            f"""UPDATE sequence_enrollments SET status='active'
                WHERE status='blocked'
                  AND sequence_id IN (SELECT id FROM sequences WHERE channel=?)
                  AND lead_no IN (SELECT no FROM leads
                                  WHERE {col} IS NOT NULL AND {col} != '' {live})""",
            (channel,))
        reopened += cur.rowcount
    conn.commit()
    return reopened


def advance_enrollment(conn, enrollment_id: int) -> None:
    """Call after a step is sent: move to next step or complete the enrollment."""
    e = conn.execute(
        "SELECT sequence_id, current_step, enrolled_at FROM sequence_enrollments WHERE id=?",
        (enrollment_id,)).fetchone()
    if e is None:
        return
    nxt = conn.execute(
        "SELECT day_offset FROM sequence_steps WHERE sequence_id=? AND step_order=?",
        (e["sequence_id"], e["current_step"] + 1)).fetchone()
    if nxt is None:
        conn.execute("UPDATE sequence_enrollments SET status='completed' WHERE id=?", (enrollment_id,))
    else:
        due = _plus_days(e["enrolled_at"], nxt["day_offset"])
        conn.execute(
            "UPDATE sequence_enrollments SET current_step=current_step+1, next_due_date=? WHERE id=?",
            (due, enrollment_id))
    conn.commit()


def stop_for_lead(conn, lead_no: int, channel: str | None = None) -> int:
    """Stop active enrollments for a lead (e.g. they replied). Channel-scoped if given."""
    sql = "UPDATE sequence_enrollments SET status='replied' WHERE lead_no=? AND status='active'"
    params: list = [lead_no]
    if channel:
        sql += " AND sequence_id IN (SELECT id FROM sequences WHERE channel=?)"
        params.append(channel)
    cur = conn.execute(sql, params)
    conn.commit()
    return cur.rowcount
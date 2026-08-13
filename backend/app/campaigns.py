"""Campaign analytics: which pitch/country/channel actually gets replies.

Every outgoing message is logged with a campaign label (user-supplied, or an
auto label like 'email 2026-07-10' / '序列:Cold 3-touch'). Reply attribution is
lead-level: a campaign's reply count = its distinct leads that have replied on
that channel. Country stats come straight from outreach x leads.
"""
import datetime as _dt


def log_send(conn, lead_no: int, channel: str, campaign: str) -> None:
    conn.execute(
        "INSERT INTO send_log(lead_no, channel, campaign, sent_at) VALUES (?, ?, ?, ?)",
        (lead_no, channel, campaign, _dt.datetime.now(_dt.UTC).isoformat()))
    conn.commit()


def default_label(channel: str) -> str:
    return f"{channel} {_dt.date.today().isoformat()}"


def contacted_today(conn, lead_no: int) -> bool:
    """Global cadence guard: one bulk/automated touch per lead per local day.

    Per-channel caps protect accounts; this protects the customer experience. A lead
    emailed this morning must not receive the same cold pitch on three social channels
    later that day.
    """
    return conn.execute(
        "SELECT 1 FROM send_log WHERE lead_no=?"
        " AND date(sent_at, 'localtime')=date('now', 'localtime') LIMIT 1",
        (lead_no,),
    ).fetchone() is not None


def campaign_stats(conn) -> list[dict]:
    rows = conn.execute(
        """SELECT s.campaign, s.channel,
                  COUNT(*) AS sent,
                  COUNT(DISTINCT s.lead_no) AS leads,
                  COUNT(DISTINCT CASE WHEN o.status = 'replied' THEN s.lead_no END) AS replied,
                  MIN(s.sent_at) AS first_sent, MAX(s.sent_at) AS last_sent
           FROM send_log s
           LEFT JOIN outreach o ON o.lead_no = s.lead_no AND o.channel = s.channel
           GROUP BY s.campaign, s.channel
           ORDER BY MAX(s.sent_at) DESC""").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["reply_rate"] = round(d["replied"] / d["leads"] * 100, 1) if d["leads"] else 0.0
        out.append(d)
    return out


def quality_stats(conn) -> list[dict]:
    """Reply rate split by email quality — the one cut campaign labels cannot make.

    Role mailboxes (info@, sales@) took 55% of every email ever sent from here, and
    whether they are worth the send is the biggest single lever on the reply rate.
    Date/sequence labels group straight across that split, so the question stays
    unanswerable until it is grouped this way. Email only: email_status means nothing
    on the browser channels.
    """
    rows = conn.execute(
        """SELECT COALESCE(l.email_status, 'unverified') AS quality,
                  COUNT(DISTINCT o.lead_no) AS touched,
                  COUNT(DISTINCT CASE WHEN o.status = 'replied' THEN o.lead_no END) AS replied
           FROM outreach o JOIN leads l ON l.no = o.lead_no
           WHERE o.channel = 'email' AND o.status IN ('messaged', 'replied')
           GROUP BY 1 ORDER BY touched DESC""").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["reply_rate"] = round(d["replied"] / d["touched"] * 100, 1) if d["touched"] else 0.0
        out.append(d)
    return out


# Above this, mailbox providers throttle the sender and start filing the rest as spam.
BOUNCE_DANGER_PCT = 2.0


def deliverability(conn, days: int = 30) -> dict:
    """Hard-bounce rate over a recent window, with the reputation alarm attached.

    Counted per lead on both sides (leads mailed vs leads that bounced) so one dead
    address that bounces on every step does not read as several dead addresses.

    The bounce side reads leads.bounced_at, not the inbox: bounce notices are
    deliberately not filed there (nothing in one is worth reading), so counting inbox
    rows would freeze this metric at whatever history happened to predate that rule.

    This matters because a bounce rate past BOUNCE_DANGER_PCT gets the sending mailbox
    throttled and quietly files the rest of the campaign in spam — on the dashboard
    that is indistinguishable from bad copy, and rewriting the copy will not fix it.
    """
    since = (_dt.date.today() - _dt.timedelta(days=days)).isoformat()
    sends = conn.execute(
        "SELECT COUNT(DISTINCT lead_no) c FROM send_log"
        " WHERE channel = 'email' AND sent_at >= ?", (since,)).fetchone()["c"]
    bounced = conn.execute(
        "SELECT COUNT(*) c FROM leads WHERE bounced_at >= ?", (since,)).fetchone()["c"]
    rate = round(bounced / sends * 100, 1) if sends else 0.0
    # Bounces only arrive over IMAP, and this rate decays towards a healthy-looking 0
    # whenever they stop arriving — on a list that is getting worse, not better. Two
    # separate ways to go blind, and the second one leaves the reply sync reporting
    # perfect health:
    #   1. the sync itself is failing
    #   2. mail goes out from a send-only mailbox. Bounces follow the envelope sender,
    #      never the Reply-To, so they land in a mailbox nothing can read — replies
    #      still arrive through the forward or reply-to and the sweep stays 'success'.
    from app import mailboxes, settings
    sync_broken = settings.get(conn, "reply_sync_last_status") not in (None, "success")
    unseen_sender = any(m["active"] and not m["imap_enabled"]
                        for m in mailboxes.list_mailboxes(conn))
    blind = sync_broken or unseen_sender
    return {"days": days, "sends": sends, "bounced": bounced,
            "bounce_rate": rate, "danger": rate > BOUNCE_DANGER_PCT, "blind": blind}


def country_stats(conn, min_touched: int = 3) -> list[dict]:
    rows = conn.execute(
        """SELECT l.country,
                  COUNT(DISTINCT o.lead_no) AS touched,
                  COUNT(DISTINCT CASE WHEN o.status = 'replied' THEN o.lead_no END) AS replied
           FROM outreach o JOIN leads l ON l.no = o.lead_no
           WHERE l.country IS NOT NULL AND o.status IN ('messaged', 'replied')
           GROUP BY l.country HAVING touched >= ?
           ORDER BY replied * 1.0 / touched DESC, touched DESC""", (min_touched,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["reply_rate"] = round(d["replied"] / d["touched"] * 100, 1) if d["touched"] else 0.0
        out.append(d)
    return out

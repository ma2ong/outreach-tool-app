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

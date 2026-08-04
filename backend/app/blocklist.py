"""Never-collect-again list, matched on domain.

Deleting a lead only clears today's database. The collector keeps its finds in
output/leads/generate_led_leads_v*.py and `python -m app.migrate` replays every one of
those files, so a competitor deleted by hand walks right back in on the next import —
which is what makes a delete button feel broken.

Domain, not company name: names get rewritten ("XcolorLED USA" / "Xcolor LED USA") and
would need fuzzy matching to catch, while a domain is exact and cheap. Email addresses
are matched by their domain too, so a record that carries only info@theirdomain.com is
still caught.
"""
import datetime as _dt

from app.dedupe import normalize_website


class BlockedLead(Exception):
    """Raised by insert_lead when the record belongs to a blocked domain."""

    def __init__(self, domain: str):
        super().__init__(f"{domain} 在「永不再收录」名单中")
        self.domain = domain


def domain_of(value: str | None) -> str | None:
    """Domain of a website or an email address; None when there is nothing to match on."""
    if not value:
        return None
    raw = value.strip()
    if "@" in raw:
        raw = raw.rsplit("@", 1)[1]
    norm = normalize_website(raw)
    return norm.split("/")[0] if norm else None


def list_all(conn) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT id, domain, reason, created_at FROM lead_blocklist ORDER BY id DESC")]


def add(conn, value: str, reason: str | None = None) -> dict | None:
    """Block a domain. Returns the stored row, or None when `value` has no domain in it."""
    domain = domain_of(value)
    if not domain:
        return None
    conn.execute(
        "INSERT OR IGNORE INTO lead_blocklist(domain, reason, created_at) VALUES (?, ?, ?)",
        (domain, reason, _dt.datetime.now(_dt.UTC).isoformat()))
    conn.commit()
    row = conn.execute(
        "SELECT id, domain, reason, created_at FROM lead_blocklist WHERE domain=?",
        (domain,)).fetchone()
    return dict(row) if row else None


def remove(conn, block_id: int) -> bool:
    cur = conn.execute("DELETE FROM lead_blocklist WHERE id=?", (block_id,))
    conn.commit()
    return cur.rowcount > 0


def blocked_domains(conn) -> set[str]:
    return {r["domain"] for r in conn.execute("SELECT domain FROM lead_blocklist")}


def match(domains: set[str], *values: str | None) -> str | None:
    """The blocked domain one of these website/email values belongs to, if any.
    A blocked domain also covers its subdomains — shop.theirs.com is still theirs."""
    if not domains:
        return None
    for value in values:
        d = domain_of(value)
        if not d:
            continue
        for blocked in domains:
            if d == blocked or d.endswith("." + blocked):
                return blocked
    return None


def is_blocked(conn, website: str | None = None, email: str | None = None) -> str | None:
    return match(blocked_domains(conn), website, email)

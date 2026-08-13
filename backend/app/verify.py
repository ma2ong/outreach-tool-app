"""Email verification to protect deliverability.

Classifies each lead email so the send path can skip dead addresses (which cause
hard bounces and wreck sender reputation):

- invalid : bad syntax, or the domain has no MX/A record (won't accept mail) -> skip
- role    : valid domain but a role mailbox (info@, sales@ ...) -> keep, just flagged
- valid   : valid domain, personal-looking local part
- unknown : DNS lookup failed transiently -> keep (never penalize a lead on a hiccup)

An address that has already hard-bounced is never re-classified: DNS would clear it
(the domain resolves and has MX, which is how the bounce reached us) and the send
path would burn sender reputation on it a second time. leads.bounced_at holds that.

MX resolution is injected so tests stay offline; the default uses dnspython.
"""
import re

_SYNTAX = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_ROLE = {"info", "sales", "contact", "admin", "support", "office", "hello",
         "enquiries", "enquiry", "marketing", "webmaster", "noreply", "no-reply",
         "service", "services", "mail", "team", "help", "hi"}

# status values, best (keep) to worst (skip)
SKIP_STATUS = "invalid"


def default_resolver(domain: str) -> bool | None:
    """True: domain accepts mail; False: no MX/A; None: transient DNS failure."""
    try:
        import dns.resolver
    except Exception:  # noqa: BLE001 - dnspython missing -> can't judge
        return None
    try:
        return len(dns.resolver.resolve(domain, "MX")) > 0
    except dns.resolver.NXDOMAIN:
        # Domain does not exist -> invalid. Do NOT fall back to A: some resolvers
        # hijack NXDOMAIN A-lookups and would make any typo look deliverable.
        return False
    except dns.resolver.NoAnswer:
        # Domain exists but has no MX -> RFC 5321 implicit MX = its A record.
        try:
            dns.resolver.resolve(domain, "A")
            return True
        except dns.resolver.NoAnswer:
            return False
        except dns.resolver.NXDOMAIN:
            return False
        except Exception:  # noqa: BLE001
            return None
    except Exception:  # noqa: BLE001 - timeout / no nameserver
        return None


def classify_email(addr: str, resolve_domain=default_resolver) -> tuple[str, str]:
    a = (addr or "").strip()
    if not _SYNTAX.match(a):
        return ("invalid", "syntax")
    local, domain = a.rsplit("@", 1)
    accepts = resolve_domain(domain.lower())
    if accepts is False:
        return ("invalid", "no-mx")
    if accepts is None:
        return ("unknown", "dns-error")
    if local.lower() in _ROLE:
        return ("role", "role-address")
    return ("valid", "ok")


def verify_leads(conn, lead_nos: list[int] | None = None, resolve_domain=default_resolver) -> dict:
    from app import contacts
    contacts.ensure_schema(conn)
    if lead_nos:
        ph = ",".join("?" * len(lead_nos))
        rows = conn.execute(
            f"SELECT no, email, bounced_at FROM leads"
            f" WHERE email IS NOT NULL AND email != '' AND no IN ({ph})",
            lead_nos).fetchall()
    else:
        rows = conn.execute(
            "SELECT no, email, bounced_at FROM leads"
            " WHERE email IS NOT NULL AND email != ''").fetchall()
    counts = {"valid": 0, "role": 0, "invalid": 0, "unknown": 0}
    cache: dict[str, bool | None] = {}

    def _resolve(domain: str):
        if domain not in cache:
            cache[domain] = resolve_domain(domain)
        return cache[domain]

    for r in rows:
        # A hard bounce outranks DNS. The domain of a bounced address resolves fine and
        # has MX — that is how the bounce got back to us — so re-classifying it would
        # read 'valid' and hand a known-dead address back to the send path, where it
        # bounces again and costs sender reputation a second time.
        if r["bounced_at"]:
            counts["invalid"] = counts.get("invalid", 0) + 1
            continue
        status, _ = classify_email(r["email"], _resolve)
        conn.execute("UPDATE leads SET email_status=? WHERE no=?", (status, r["no"]))
        conn.execute(
            "UPDATE contacts SET email_status=?, updated_at=datetime('now')"
            " WHERE lead_no=? AND is_primary=1",
            (status, r["no"]),
        )
        counts[status] = counts.get(status, 0) + 1
    conn.commit()
    return {"checked": len(rows), **counts}

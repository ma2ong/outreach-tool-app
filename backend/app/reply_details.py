"""Read the contact details a customer put in their own reply (docs/86 R5).

A reply signature is the best data we ever get about a company — it is the customer
telling us their own number, their own site, their own name and title, without being
asked. Until now it sat in `inbox_messages.body` and Allen retyped it by hand:

    AB Medina | Producer/Owner
    Full Life Productions
    C: 678-232-4066
    W: fulllifeproductions.com
    E: info@fulllifeproductions.com

Three rules keep this from making the book worse.

Only the reply itself is read, never the quoted thread below it. Our own signature is in
every quote, and a book that learned Allen's phone number for six hundred customers would
be worse than one that learned nothing.

Nothing already known is overwritten. A field we have came from somewhere — a site read,
an import, Allen's own typing — and a signature is not evidence that the old value was
wrong, only that another one exists. Empty fields are filled; filled fields are left.

And every write is attributable: docs/45 asks for a source, and 「客户自己在回信里写的」
is the strongest one in this system.
"""
from __future__ import annotations

import re

from app.phone_format import book_form

# Where the reply stops and the thread we sent begins. Everything below the first of
# these is our own words coming back at us.
_QUOTE_START = re.compile(
    r"^\s*(?:>|On .{0,80}\bwrote:|-{2,}\s*Original Message|From:\s|發件人|发件人[:：]"
    r"|보낸\s*사람)", re.M)

# "C: 678-232-4066" / "M +55 11 99999-0000" / "Tel: ..." — a labelled number in a
# signature. The label matters: a bare number in prose is as likely to be a quantity.
_PHONE = re.compile(
    r"(?:^|\n)\s*(?:C|M|T|P|Tel|Phone|Mobile|Cell|WhatsApp|WA|휴대폰|전화)\s*[:.]?\s*"
    r"(\+?[\d][\d\s().\-]{6,20}\d)", re.I)
_SITE = re.compile(
    r"(?:^|\n)\s*(?:W|Web|Website|Site|URL)\s*[:.]?\s*"
    r"((?:https?://)?(?:www\.)?[a-z0-9][a-z0-9.\-]*\.[a-z]{2,}(?:/\S*)?)", re.I)
# "AB Medina | Producer/Owner" or "AB Medina - Producer" — a name and a title on one line.
_NAME_TITLE = re.compile(
    r"(?:^|\n)\s*([A-Z][A-Za-z.\-']+(?:\s+[A-Z][A-Za-z.\-']+){0,3})\s*[|｜/–—-]\s*"
    r"((?:[A-Za-z][A-Za-z/&.\- ]{2,40})?"
    r"(?:Owner|Producer|Manager|Director|CEO|President|Founder|Partner|Head|Sales|Buyer)"
    r"[A-Za-z/&.\- ]{0,20})")

_ROLE_ADDR = re.compile(
    r"^(info|sales|contact|hello|admin|office|support|enquiry|enquiries|team)@", re.I)


def own_words(body: str | None) -> str:
    """The part of the message the customer wrote, without the thread underneath."""
    text = str(body or "")
    m = _QUOTE_START.search(text)
    return text[:m.start()] if m else text


def read(body: str | None, country: str | None = None) -> dict:
    """Contact details the customer stated about themselves. Keys are lead columns."""
    text = own_words(body)
    out: dict[str, str] = {}

    phone = _PHONE.search(text)
    if phone:
        formatted = book_form(phone.group(1).strip(), country)
        out["phone"] = formatted or phone.group(1).strip()

    site = _SITE.search(text)
    if site:
        host = re.sub(r"^https?://", "", site.group(1).strip(), flags=re.I).rstrip("/")
        # A signature's W: line is the company site; an email host is not a claim.
        if "." in host and not host.lower().startswith("mailto"):
            out["website"] = host

    who = _NAME_TITLE.search(text)
    if who:
        out["contact_name"] = who.group(1).strip()
        out["contact_title"] = who.group(2).strip(" |/-–—")
    return out


def apply(conn, lead_no: int, body: str | None) -> dict:
    """Fill in what the book is missing, and report exactly what was written.

    Returns {} when the reply said nothing new — which is most replies, and is why this
    reports rather than logs: a silent enricher is the failure mode this book keeps
    producing (docs/86 R2).
    """
    row = conn.execute(
        "SELECT no, country, phone, website, contact_name FROM leads WHERE no=?",
        (lead_no,)).fetchone()
    if row is None:
        return {}
    found = read(body, row["country"])
    written: dict[str, str] = {}
    for field in ("phone", "website", "contact_name"):
        value = found.get(field)
        if not value:
            continue
        held = str(row[field] or "").strip()
        # Never overwrite: a value we hold came from somewhere, and a signature is not
        # evidence that it was wrong — only that another one exists.
        #
        # One exception, and it is not really one: a phone column holding something that
        # is not a phone number. FULL LIFE PRODUCTIONS held "234234423423" while their
        # own reply gave +1 678-232-4066, and the rule as written kept the junk. This
        # does not prefer the signature over a real number — it replaces a non-number.
        junk = (field == "phone" and held
                and book_form(held, row["country"]) is None
                and not held.startswith("+"))
        if held and not junk:
            continue
        conn.execute(f"UPDATE leads SET {field}=? WHERE no=?", (value, lead_no))
        written[field] = value
    if written:
        conn.commit()
    return written

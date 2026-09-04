"""Read the contact details a customer put in their own reply (docs/86 R5, docs/106).

A reply signature is the best data we ever get about a company — it is the customer
telling us their own number, their own site, their own name and title, without being
asked. Until now it sat in `inbox_messages.body` and Allen retyped it by hand:

    Sincerely,

    Roman Gerashenko
    CEO
    Alternis LLC + Brands

    m: 917-495-9116
    e: roman@alternis.com
    w: www.alternis.com

docs/106 is why this reads a block and not a line: the original rule wanted the name and
the title on one line with a separator between them, and across ten real replies it
produced zero names and zero titles. Signatures put them on separate lines.

Four rules keep this from making the book worse.

Only the reply itself is read, never the quoted thread below it. Our own signature is in
every quote, and a book that learned Allen's phone number for six hundred customers would
be worse than one that learned nothing.

An address has to be theirs before it is written: labelled in the signature, or at the
sender's own domain, or at the company's own website domain. "We already buy from
tony@absen.com" is a sentence about somebody else.

Nothing already known is overwritten. A field we have came from somewhere — a site read,
an import, Allen's own typing — and a signature is not evidence that the old value was
wrong, only that another one exists. Empty fields are filled; filled fields are left.

And every write is attributable: docs/45 asks for a source, and 「客户自己在回信里写的」
is the strongest one in this system.
"""
from __future__ import annotations

import re
import sys

from app import contact_names, contact_roles, contacts
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
_ADDR = r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}"
_EMAIL_ANY = re.compile(_ADDR)
# "E: info@..." / "e-mail: ..." — the label is the customer saying this one is his.
_EMAIL_LABELLED = re.compile(
    r"(?:^|\n)\s*(?:E|e-?mail|mail|이메일|邮箱|郵箱)\s*[:.]\s*(" + _ADDR + r")", re.I)

# "AB Medina | Producer/Owner" — a name and a title on one line. ` I ` is in the
# separator class because the one message docs/86 R5 was written for spells it with a
# capital I, not a pipe (docs/106). Safe: the right side still has to be a job.
_NAME_TITLE = re.compile(
    r"(?:^|\n)\s*([A-Z][A-Za-z.\-']+(?:\s+[A-Z][A-Za-z.\-']+){0,3})\s*(?:[|｜/–—-]|\sI\s)\s*"
    r"((?:[A-Za-z][A-Za-z/&.\- ]{2,40})?"
    r"(?:Owner|Producer|Manager|Director|CEO|President|Founder|Partner|Head|Sales|Buyer)"
    r"[A-Za-z/&.\- ]{0,20})")

# "Sincerely," / "감사합니다" — the line that says the letter is over and the signature
# starts. Only an anchor: the name still has to pass `contact_names.is_sayable`.
_SIGNOFF = re.compile(
    r"^(sincerely|regards|best regards|kind regards|warm regards|best wishes|best|"
    r"thanks|thank you|many thanks|cheers|respectfully|"
    r"감사합니다|고맙습니다|谢谢|此致|敬礼)[,，.!。]*$", re.I)

# Words that make a line a job title rather than a name or a company. Both lists are
# already in this codebase and are reused rather than restated: `TITLE_WORDS` is what
# docs/98 uses to reject a title that arrived where a name belonged, and `ROLE_WORDS`
# is the multilingual half — 대표 / gerente / diretor come from there.
_TITLE_TOKENS = set(contact_names.TITLE_WORDS) | {
    token
    for _role, words in contact_roles.ROLE_WORDS
    for phrase in words
    for token in phrase.split()
}
_TITLE_GLUE = {"of", "and", "the", "a", "at", "for", "de", "da", "do", "y", "e"}
_WORDS = re.compile(r"[^0-9A-Za-z가-힯一-鿿]+")

_ROLE_ADDR = re.compile(
    r"^(info|sales|contact|hello|admin|office|support|enquiry|enquiries|team)@", re.I)


def own_words(body: str | None) -> str:
    """The part of the message the customer wrote, without the thread underneath."""
    text = str(body or "")
    m = _QUOTE_START.search(text)
    return text[:m.start()] if m else text


def _bare_host(value: str | None) -> str:
    host = re.sub(r"^https?://", "", str(value or "").strip(), flags=re.I)
    host = host.split("/", 1)[0].strip().lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def _domain(addr: str) -> str:
    return addr.split("@", 1)[1].lower() if "@" in addr else ""


def is_title_line(line: str) -> bool:
    """A line that is a job, not a person and not a company.

    Every word has to be a title word, so "CEO" and "Head of Sales" are titles while
    "Alternis LLC + Brands" and "Full Life Productions" are not.
    """
    text = line.strip(" \t·•|-–—")
    if not text or len(text) > 60:
        return False
    tokens = [t.lower() for t in _WORDS.split(text) if t]
    if not tokens:
        return False
    return all(t in _TITLE_TOKENS or t in _TITLE_GLUE for t in tokens)


def _has_signature_detail(lines: list[str]) -> bool:
    """Does this block carry a labelled phone / site / address? A name on its own is a
    guess; a name above a `m:` line is a signature."""
    block = "\n" + "\n".join(lines)
    return bool(_PHONE.search(block) or _SITE.search(block)
                or _EMAIL_LABELLED.search(block) or _EMAIL_ANY.search(block))


def _read_person(text: str, company: str | None) -> dict:
    """Name and title as the customer signed them."""
    same_line = _NAME_TITLE.search(text)
    if same_line:
        name = same_line.group(1).strip()
        if contact_names.is_sayable(name, company or ""):
            return {"contact_name": name,
                    "title": same_line.group(2).strip(" |/-–—")}

    lines = text.splitlines()
    filled = [i for i, line in enumerate(lines) if line.strip()]

    # A title line names itself; the line above it is the person who holds it.
    for pos, i in enumerate(filled):
        if pos == 0 or not is_title_line(lines[i]):
            continue
        above = lines[filled[pos - 1]].strip()
        if contact_names.is_sayable(above, company or ""):
            return {"contact_name": above,
                    "title": lines[i].strip(" \t·•|-–—")}

    # No title line: take the name under the sign-off, but only when the block also
    # carries a real contact detail — otherwise "Thanks," / "Michael" in the middle of
    # a message would be read as a signature.
    for pos, i in enumerate(filled):
        if not _SIGNOFF.match(lines[i].strip()):
            continue
        rest = filled[pos + 1:pos + 4]
        if not rest or not _has_signature_detail(lines[rest[0]:]):
            continue
        for j in rest:
            candidate = lines[j].strip()
            if contact_names.is_sayable(candidate, company or ""):
                return {"contact_name": candidate}
    return {}


def _read_email(text: str, *, website: str | None, sender: str | None,
                ours: set[str] | None = None) -> str | None:
    """The address the customer gave for himself — never one he merely mentioned.

    Trusted three ways: it carries an `E:` label, it is at the domain the reply came
    from, or it is at the company's own website domain. Our own domains are excluded
    outright: a customer writing `allen@maxcolorvisual.com` in his own words is quoting
    us, not reporting an address.
    """
    ours = {d for d in (ours or set()) if d}
    trusted = set()
    if sender and "@" in sender:
        trusted.add(_domain(sender))
    site = _bare_host(website)
    if site:
        trusted.add(site)
    labelled = {m.group(1).lower() for m in _EMAIL_LABELLED.finditer(text)}
    for raw in _EMAIL_ANY.findall(text):
        addr = raw.lower()
        domain = _domain(addr)
        if not domain or domain in ours:
            continue
        if addr in labelled or domain in trusted or _bare_host(domain) in trusted:
            return addr
    return None


def read(body: str | None, country: str | None = None, *, company: str | None = None,
         website: str | None = None, sender: str | None = None,
         ours: set[str] | None = None) -> dict:
    """Contact details the customer stated about themselves. Keys are lead columns."""
    text = own_words(body)
    out: dict[str, str] = {}

    phone = _PHONE.search(text)
    if phone:
        formatted = book_form(phone.group(1).strip(), country)
        out["phone"] = formatted or phone.group(1).strip()

    site = _SITE.search(text)
    if site:
        # The book holds bare hosts — 977 websites, not one with a scheme and not one
        # with a `www.` (docs/106). A signature's W: line arrives in that shape.
        host = _bare_host(site.group(1))
        if "." in host and not host.startswith("mailto"):
            out["website"] = host

    out.update(_read_person(text, company))

    email = _read_email(text, website=website, sender=sender, ours=ours)
    if email:
        out["email"] = email
    return out


def our_domains(conn) -> set[str]:
    """Domains that are ours, whatever a reply says. Never adopted as a customer's."""
    from app import mailboxes
    from app.channels.email_adapter import FALLBACK_SENDER

    domains = {_domain(FALLBACK_SENDER)}
    try:
        for mailbox in mailboxes.list_mailboxes(conn):
            domains.add(_domain(str(mailbox.get("email") or "")))
    except Exception:  # noqa: BLE001 — a missing mailbox table must not lose a reply
        pass
    return {d for d in domains if d}


# Columns this fills, and where each one lives. `website` is only on the company.
_PERSON_FIELDS = {"contact_name": "name", "title": "title", "email": "email",
                  "phone": "phone"}
_LEAD_FIELDS = ("phone", "website", "contact_name", "title", "email")


def _is_junk_phone(held: str, country: str | None) -> bool:
    """A phone column holding something that is not a phone number.

    FULL LIFE PRODUCTIONS held "234234423423" while their own reply gave
    +1 678-232-4066, and never-overwrite kept the junk. This does not prefer the
    signature over a real number — it replaces a thing that is not a number.
    """
    return bool(held) and book_form(held, country) is None and not held.startswith("+")


def _keep(held: str, field: str, country: str | None) -> bool:
    """Is the value already in this column a reason to leave it alone?"""
    return bool(held) and not (field == "phone" and _is_junk_phone(held, country))


def _target_contact(conn, lead_no: int, contact_id: int | None):
    """Whose row this signature belongs to: the person who wrote it, else the primary.

    It matters which. A signature is one person's, and writing Roman's title onto the
    row for `info@` would relabel a shared mailbox as the CEO.
    """
    contacts.ensure_schema(conn)
    if contact_id:
        row = conn.execute(
            "SELECT id, name, title, email, phone, is_primary FROM contacts"
            " WHERE id=? AND lead_no=?", (contact_id, lead_no)).fetchone()
        if row:
            return row
    return conn.execute(
        "SELECT id, name, title, email, phone, is_primary FROM contacts"
        " WHERE lead_no=? AND is_primary=1", (lead_no,)).fetchone()


def apply(conn, lead_no: int, body: str | None, *, contact_id: int | None = None,
          sender: str | None = None) -> dict:
    """Fill in what the book is missing, and report exactly what was written.

    Returns {} when the reply said nothing new — which is most replies, and is why this
    reports rather than logs: a silent enricher is the failure mode this book keeps
    producing (docs/86 R2).
    """
    row = conn.execute(
        "SELECT no, country, company_en, phone, website, contact_name, title, email"
        " FROM leads WHERE no=?", (lead_no,)).fetchone()
    if row is None:
        return {}
    found = read(body, row["country"], company=row["company_en"],
                 website=row["website"], sender=sender, ours=our_domains(conn))
    if not found:
        return {}
    written: dict[str, str] = {}

    # The person's own fields belong on the contact row. Writing them straight to
    # `leads` looks like it works and does not last: `contacts._sync_lead` copies the
    # primary contact over those five columns — nulls included — the next time anyone
    # edits this company's contacts (docs/106 R4).
    target = _target_contact(conn, lead_no, contact_id)
    if target:
        patch = {}
        for field, column in _PERSON_FIELDS.items():
            value = found.get(field)
            if value and not _keep(str(target[column] or "").strip(), field,
                                   row["country"]):
                patch[column] = value
        if patch:
            try:
                contacts.update(conn, target["id"], patch)
                written.update({f: found[f] for f, c in _PERSON_FIELDS.items()
                                if c in patch})
            except contacts.ContactValidation:
                # An address another contact at this company already holds, or a value
                # the contact rules refuse. Never a reason to lose the reply.
                pass

    # The company's own columns. When the target above was the primary contact its sync
    # has already filled these, and this loop finds nothing left to do — so it is read
    # back from the row rather than from `row`, which is now stale.
    for field in _LEAD_FIELDS:
        value = found.get(field)
        if not value:
            continue
        held = str(conn.execute(
            f"SELECT COALESCE({field}, '') v FROM leads WHERE no=?",
            (lead_no,)).fetchone()["v"]).strip()
        if _keep(held, field, row["country"]):
            continue
        conn.execute(f"UPDATE leads SET {field}=? WHERE no=?", (value, lead_no))
        written[field] = value
    if written:
        conn.commit()
    return written


def backfill(conn, apply_writes: bool = False) -> list[dict]:
    """Re-read every reply already filed.

    docs/106: the rule meant to do this has produced zero names and zero titles since it
    shipped, so the replies already in the book have never once been read properly.

    Without `apply_writes` this reports what each reply *says*, not what would be
    written — most of it is already in the book, and which of it is new depends on
    whose contact row the signature lands on. The `--apply` run reports the writes.
    """
    rows = conn.execute(
        "SELECT id, lead_no, contact_id, from_addr, body FROM inbox_messages"
        " WHERE kind='reply' ORDER BY id").fetchall()
    out = []
    for row in rows:
        if apply_writes:
            found = apply(conn, row["lead_no"], row["body"],
                          contact_id=row["contact_id"], sender=row["from_addr"])
        else:
            lead = conn.execute(
                "SELECT country, company_en, website FROM leads WHERE no=?",
                (row["lead_no"],)).fetchone()
            if lead is None:
                continue
            found = read(row["body"], lead["country"], company=lead["company_en"],
                         website=lead["website"], sender=row["from_addr"],
                         ours=our_domains(conn))
        if found:
            out.append({"inbox_id": row["id"], "lead_no": row["lead_no"], **found})
    return out


def main(argv: list[str]) -> None:
    from app.db import connect
    from app.main_deps import DB_PATH

    write = "--apply" in argv
    conn = connect(DB_PATH)
    found = backfill(conn, apply_writes=write)
    for item in found:
        detail = ", ".join(f"{k}={v}" for k, v in item.items()
                           if k not in ("inbox_id", "lead_no"))
        print(f"  #{item['lead_no']:>5}  {detail}")
    if write:
        print(f"已写入 {len(found)} 封回信里的信息")
    else:
        print(f"读到 {len(found)} 封回信里的落款（加 --apply 把其中书上空着的写进去）")


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])

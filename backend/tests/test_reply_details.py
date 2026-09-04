"""What a customer tells us about themselves in their own reply (docs/86 R5, docs/106)."""
import pytest

from app import contacts, reply_details

# The real message, character for character: the separator between the name and the
# title is a capital I, not a pipe. docs/106 — the test used to spell it with a pipe,
# which is why the rule looked green and had never matched this signature.
SIG = """I already buy from Maxcolor.
My guy is Tony.

AB Medina I Producer/Owner
Full Life Productions
C: 678-232-4066
W: fulllifeproductions.com
E: info@fulllifeproductions.com

> On Sep 1, 2026, at 10:07 PM, allen@maxcolorvisual.com wrote:
>
> Hi,
> Allen Ma · Shenzhen Maxcolor Visual
> WhatsApp/WeChat +86 135-7087-1001
"""

# inbox_messages id=4805, lead 1180 — three lines, no separator anywhere.
BLOCK = """Hi Allen,

We are about to start a new project..  So we will need more LED walls


Sincerely,

Roman Gerashenko
CEO
Alternis LLC + Brands

m: 917-495-9116
e: roman@alternis.com
w: www.alternis.com

-----Original Message-----
From: allen@maxcolorvisual.com <allen@maxcolorvisual.com>
Sent: Wednesday, September 2, 2026 9:54 PM
"""


def test_the_quoted_thread_is_not_read():
    """Our own signature is in every quote. A book that learned Allen's own number for
    six hundred customers would be worse than one that learned nothing."""
    kept = reply_details.own_words(SIG)
    assert "678-232-4066" in kept
    assert "135-7087-1001" not in kept and "allen@maxcolorvisual.com" not in kept


def test_a_signature_is_read_as_the_customer_wrote_it():
    got = reply_details.read(SIG, "USA")
    assert got["phone"] == "+16782324066"
    assert got["website"] == "fulllifeproductions.com"
    assert got["contact_name"] == "AB Medina"
    assert "Producer" in got["title"]
    assert got["email"] == "info@fulllifeproductions.com"


def test_a_name_a_title_and_a_company_on_three_lines():
    """docs/106: the shape that produced nothing at all — no separator to match on."""
    got = reply_details.read(BLOCK, "USA", company="Alternis LLC",
                             sender="roman@alternis.com")
    assert got["contact_name"] == "Roman Gerashenko"
    assert got["title"] == "CEO"
    assert got["email"] == "roman@alternis.com"
    assert got["phone"] == "+19174959116"
    # 977 websites in the book, not one of them carries a `www.`
    assert got["website"] == "alternis.com"


def test_the_company_line_is_not_a_name_and_not_a_title():
    assert not reply_details.is_title_line("Alternis LLC + Brands")
    assert not reply_details.is_title_line("Full Life Productions")
    assert reply_details.is_title_line("CEO")
    assert reply_details.is_title_line("Head of Sales")
    assert reply_details.is_title_line("대표")


def test_a_name_under_a_sign_off_needs_a_contact_detail_under_it():
    """"Thanks, / Michael" inside a sentence is not a signature."""
    prose = "Thanks,\n\nMichael said he would send the drawings next week.\n"
    assert "contact_name" not in reply_details.read(prose)
    signed = "Thanks,\n\nMichael Reyes\nm: 917-495-9116\n"
    assert reply_details.read(signed, "USA")["contact_name"] == "Michael Reyes"


@pytest.mark.parametrize("line,expected", [
    ("\nM: +55 11 99137-8503\n", "+5511991378503"),
    ("\nTel: 02-847-2123\n", "+8228472123"),
    ("\nWhatsApp: 410 659 507\n", "+61410659507"),
])
def test_labelled_numbers_are_stored_the_way_we_would_dial_them(line, expected):
    country = {"+5": "Brazil", "+8": "South Korea", "+6": "Australia"}[expected[:2]]
    assert reply_details.read(line, country)["phone"] == expected


def test_a_number_in_prose_is_not_a_phone_number():
    """A label is what separates a signature from a sentence."""
    assert "phone" not in reply_details.read("We ran 40 000 panels last year.", "USA")


def test_an_address_he_only_mentioned_is_not_his(conn):
    """docs/106 R3. Reading this one would put a competitor into the send queue."""
    body = "We already buy these from tony@absen.com, so no thanks."
    assert "email" not in reply_details.read(
        body, "USA", website="alpha.com", sender="buyer@alpha.com")


def test_our_own_address_is_never_read_as_theirs():
    body = "Please keep writing to allen@maxcolorvisual.com, I read that one.\n"
    assert "email" not in reply_details.read(
        body, "USA", sender="buyer@alpha.com", ours={"maxcolorvisual.com"})


def test_an_address_at_the_senders_own_domain_is_his():
    body = "Copy my colleague too: procurement@alpha.com\n"
    got = reply_details.read(body, "USA", sender="buyer@alpha.com")
    assert got["email"] == "procurement@alpha.com"


def test_nothing_known_is_overwritten(conn):
    conn.execute("UPDATE leads SET phone='+15551234567', website='old.com',"
                 " contact_name='Existing', title='Buyer', email='old@alpha.com'"
                 " WHERE no=1")
    conn.commit()
    assert reply_details.apply(conn, 1, SIG) == {}
    row = conn.execute("SELECT phone, website, contact_name, title, email FROM leads"
                       " WHERE no=1").fetchone()
    assert row["phone"] == "+15551234567" and row["website"] == "old.com"
    assert row["title"] == "Buyer" and row["email"] == "old@alpha.com"


def test_empty_fields_are_filled_and_reported(conn):
    conn.execute("UPDATE leads SET phone=NULL, website=NULL, contact_name=NULL,"
                 " title=NULL, email=NULL, country='USA' WHERE no=1")
    conn.commit()
    written = reply_details.apply(conn, 1, SIG)
    assert written == {"phone": "+16782324066", "website": "fulllifeproductions.com",
                       "contact_name": "AB Medina", "title": "Producer/Owner",
                       "email": "info@fulllifeproductions.com"}
    row = conn.execute("SELECT phone, title, email FROM leads WHERE no=1").fetchone()
    assert row["phone"] == "+16782324066" and row["title"] == "Producer/Owner"
    assert row["email"] == "info@fulllifeproductions.com"


def test_a_reply_that_says_nothing_new_writes_nothing(conn):
    assert reply_details.apply(conn, 1, "Thanks, not interested.") == {}


def test_junk_in_the_phone_column_is_not_a_value_worth_keeping(conn):
    """FULL LIFE PRODUCTIONS held "234234423423" while their own reply gave
    +1 678-232-4066. Not preferring the signature over a real number — replacing a
    thing that is not a number."""
    conn.execute("UPDATE leads SET phone='234234423423', country='USA',"
                 " website=NULL, contact_name=NULL WHERE no=1")
    conn.commit()
    assert reply_details.apply(conn, 1, SIG)["phone"] == "+16782324066"


def test_a_real_number_is_still_never_replaced(conn):
    conn.execute("UPDATE leads SET phone='+15551234567', country='USA' WHERE no=1")
    conn.commit()
    assert "phone" not in reply_details.apply(conn, 1, SIG)


def test_what_is_filled_survives_the_next_contact_edit(conn):
    """docs/106 R4. Written straight to `leads` it looked filled and was gone the next
    time anyone touched this company's contacts: `_sync_lead` copies the primary
    contact over those columns, nulls included."""
    conn.execute("UPDATE leads SET phone=NULL, contact_name=NULL, title=NULL,"
                 " email=NULL, website=NULL, country='USA' WHERE no=1")
    conn.commit()
    primary = contacts.create(conn, 1, {"name": "Front Desk"}, is_primary=True)

    assert reply_details.apply(conn, 1, SIG)["phone"] == "+16782324066"
    contacts.update(conn, primary["id"], {"note": "spoke on Tuesday"})

    row = conn.execute("SELECT phone, title FROM leads WHERE no=1").fetchone()
    assert row["phone"] == "+16782324066" and row["title"] == "Producer/Owner"
    # The name it already had is not one of the empty fields, so it stays.
    assert contacts.get(conn, primary["id"])["name"] == "Front Desk"


def test_the_signature_lands_on_whoever_wrote_it(conn):
    """A secondary contact's title is his, not the shared mailbox's."""
    conn.execute("UPDATE leads SET country='USA' WHERE no=1")
    conn.commit()
    front = contacts.create(conn, 1, {"name": "Front Desk", "email": "info@alpha.com"},
                            is_primary=True)
    person = contacts.create(conn, 1, {"name": "AB Medina", "email": "ab@alpha.com"})

    reply_details.apply(conn, 1, SIG, contact_id=person["id"])

    assert contacts.get(conn, person["id"])["title"] == "Producer/Owner"
    assert contacts.get(conn, front["id"])["title"] is None


def test_the_backfill_reads_replies_already_filed(conn):
    """And lands each signature on whoever wrote it: the inbox row has said which
    contact sent it all along."""
    conn.execute("UPDATE leads SET phone=NULL, contact_name=NULL, title=NULL,"
                 " website=NULL, email=NULL, country='USA' WHERE no=1")
    conn.commit()
    front = contacts.create(conn, 1, {"name": "Front Desk", "email": "info@alpha.com"},
                            is_primary=True)
    person = contacts.create(conn, 1, {"name": "AB Medina", "email": "ab@alpha.com"})
    conn.execute(
        "INSERT INTO inbox_messages(lead_no, contact_id, channel, kind, from_addr,"
        " subject, body, received_at) VALUES (1, ?, 'email', 'reply', 'ab@alpha.com',"
        " 's', ?, '2026-09-04')", (person["id"], SIG))
    conn.commit()

    preview = reply_details.backfill(conn)
    assert preview and preview[0]["title"] == "Producer/Owner"
    assert conn.execute("SELECT title FROM leads WHERE no=1").fetchone()[0] is None

    reply_details.backfill(conn, apply_writes=True)
    assert conn.execute("SELECT title FROM leads WHERE no=1").fetchone()[0] == "Producer/Owner"
    assert contacts.get(conn, person["id"])["title"] == "Producer/Owner"
    assert contacts.get(conn, front["id"])["title"] is None

"""What a customer tells us about themselves in their own reply (docs/86 R5)."""
import pytest

from app import reply_details

SIG = """I already buy from Maxcolor.
My guy is Tony.

AB Medina | Producer/Owner
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
    assert "Producer" in got["contact_title"]


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


def test_nothing_known_is_overwritten(conn):
    conn.execute("UPDATE leads SET phone='+15551234567', website='old.com',"
                 " contact_name='Existing' WHERE no=1")
    conn.commit()
    assert reply_details.apply(conn, 1, SIG) == {}
    row = conn.execute("SELECT phone, website, contact_name FROM leads WHERE no=1").fetchone()
    assert row["phone"] == "+15551234567" and row["website"] == "old.com"


def test_empty_fields_are_filled_and_reported(conn):
    conn.execute("UPDATE leads SET phone=NULL, website=NULL, contact_name=NULL,"
                 " country='USA' WHERE no=1")
    conn.commit()
    written = reply_details.apply(conn, 1, SIG)
    assert written == {"phone": "+16782324066", "website": "fulllifeproductions.com",
                       "contact_name": "AB Medina"}
    row = conn.execute("SELECT phone, website FROM leads WHERE no=1").fetchone()
    assert row["phone"] == "+16782324066"


def test_a_reply_that_says_nothing_new_writes_nothing(conn):
    assert reply_details.apply(conn, 1, "Thanks, not interested.") == {}

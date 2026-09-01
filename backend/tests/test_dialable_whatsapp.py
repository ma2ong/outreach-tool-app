"""WhatsApp needs a full international number (docs/62).

Allen sent his WhatsApp batch by hand and got "该电话号码没有注册 WhatsApp" on nearly
every one. They were registered. `_target` stripped `404-835-2230` down to
`4048352230` — ten digits, no country code — and wa.me answered about that string, not
about the company.

280 of 855 stored numbers have no `+`, so every WhatsApp attempt on them had been wasted.
Worse, docs/59 now writes "this number has no WhatsApp" on failure, which would have
burned all 280 permanently. These tests are what keeps the two specs compatible.
"""
import pytest

from app.channel_outreach import dialable_whatsapp as dial


@pytest.mark.parametrize("phone,country,expected", [
    ("404-835-2230", "USA", "14048352230"),
    ("(202) 695-3325", "USA", "12026953325"),
    ("281-630-6900", "United States", "12816306900"),
    ("+82 31 504-3773", "South Korea", "82315043773"),
    ("11 3044-4609", "Brazil", "551130444609"),
])
def test_a_national_number_gets_its_country_code(phone, country, expected):
    assert dial(phone, country) == expected


def test_a_number_already_international_is_left_alone():
    # Adding 82 again would produce 8282…, a number belonging to nobody.
    assert dial("+82 31 504-3773", "South Korea") == "82315043773"


def test_a_us_number_written_with_its_1_is_not_doubled():
    assert dial("1-615-457-3540", "USA") == "16154573540"


@pytest.mark.parametrize("phone", [
    "800-574-1702", "866-335-4723", "1-833-879-6728", "+1 833-934-1724",
    "888-555-1212", "877-555-1212",
])
def test_a_switchboard_number_is_never_dialled(phone):
    # These ranges cannot hold a WhatsApp account, so trying is a browser trip spent
    # confirming something already known.
    assert dial(phone, "USA") == ""


def test_a_country_we_cannot_place_means_no_whatsapp_channel():
    # Dialling the national number anyway is not a lesser attempt: it fails for certain,
    # and docs/59 would record that failure as a fact about the number.
    assert dial("031 504-3773", "") == ""
    assert dial("555-1234", "Freedonia") == ""


@pytest.mark.parametrize("phone", ["", None, "n/a", "123", "1"])
def test_nothing_usable_yields_nothing(phone):
    assert dial(phone, "USA") == ""


def test_the_number_labelled_wa_is_the_one_dialled():
    """The field says which one WhatsApp is on; taking the first half dialled the
    landline of six real companies, and docs/59 would have recorded each as having no
    WhatsApp and dropped them from the queue for good (docs/83 R1)."""
    assert dial("+55 11 2291-0031 / WA: +55 11 95663-5316", "Brazil") == "5511956635316"
    assert dial("(19) 3365-1636 / WA: (19) 99901-2883", "Brazil") == "5519999012883"
    assert dial("601 4321929 / WA: +57 317 521 1104", "Colombia") == "573175211104"


def test_an_unlabelled_second_number_is_still_ignored():
    assert dial("+55 11 2291-0031 / 11 95663-5316", "Brazil") == "551122910031"


def test_a_wa_label_pointing_at_a_link_falls_back_to_the_number():
    """`WA: wa.link/7jz8hw` names no number, so the voice line is all we have."""
    assert dial("(54) 3025-2921 / WA: wa.link/7jz8hw", "Brazil") == "555430252921"


def test_the_stored_number_is_never_rewritten():
    # The country code is added when dialling, not saved back: 404-835-2230 is what the
    # website said, and that record stays intact.
    import inspect

    from app import channel_outreach

    assert "UPDATE leads SET phone" not in inspect.getsource(channel_outreach)

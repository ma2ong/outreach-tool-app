"""What a stored phone number means, and when we refuse to touch it (docs/83)."""
import pytest

from app.phone_format import book_form, international, split_numbers


@pytest.mark.parametrize("field,voice,whatsapp", [
    ("(19) 3365-1636 / WA: (19) 99901-2883", "(19) 3365-1636", "(19) 99901-2883"),
    ("601 4321929 / WA: +57 317 521 1104", "601 4321929", "+57 317 521 1104"),
    ("713-887-2805", "713-887-2805", "713-887-2805"),
    # The label names no number, so there is no WhatsApp half to prefer.
    ("(54) 3025-2921 / WA: wa.link/7jz8hw", "(54) 3025-2921", "(54) 3025-2921"),
    ("WA: (19) 99762-6990", "(19) 99762-6990", "(19) 99762-6990"),
    ("", "", ""),
])
def test_the_wa_label_decides_which_number_is_which(field, voice, whatsapp):
    assert split_numbers(field) == (voice, whatsapp)


@pytest.mark.parametrize("number,country,expected", [
    ("713-887-2805", "USA", "17138872805"),
    ("(19) 99901-2883", "Brazil", "5519999012883"),
    ("945 241 745", "Spain", "34945241745"),
    # The trunk zero is for dialling long distance at home; it goes when the code arrives.
    ("02-847-2123", "South Korea", "8228472123"),
    ("042-627-8400", "South Korea", "82426278400"),
    ("0161 713 3396", "UK", "441617133396"),
    ("293166771", "Australia", "61293166771"),
    # '00' is the international prefix — what follows is already international.
    ("0056 512 406339", "Chile", "56512406339"),
    ("+55 11 2291-0031", "Brazil", "551122910031"),
])
def test_a_number_we_can_show_is_shown(number, country, expected):
    assert international(number, country) == expected


@pytest.mark.parametrize("number,country", [
    ("214-674-8695", None),          # no country is no evidence
    ("7751412485", ""),
    ("20230831", "USA"),             # a date somebody typed into the phone column
    ("34523352345322", "South Korea"),
    ("1833-7989", "South Korea"),    # 15xx/18xx does not route from abroad
    ("0800 947 336", "New Zealand"),
    ("1300 600 222", "Australia"),
    ("4373-9500", "Argentina"),      # no area code: nothing to build a real number from
])
def test_what_cannot_be_shown_is_left_alone(number, country):
    assert international(number, country) is None


def test_the_book_keeps_the_wa_label_it_was_given():
    assert book_form("(19) 3365-1636 / WA: (19) 99901-2883", "Brazil") == (
        "+551933651636 / WA: +5519999012883")


def test_one_number_stays_one_number():
    assert book_form("713-887-2805", "USA") == "+17138872805"
    # Same number written twice is not two numbers.
    assert book_form("+55 11 2291-0031 / WA: 11 2291-0031", "Brazil") == "+551122910031"


def test_a_part_we_cannot_show_is_kept_exactly_as_written():
    """4373-9500 has no area code, so there is no international form to write. It is
    still a number Allen has, and tidying it away would lose it."""
    assert book_form("4373-9500 / WA: +54 9 11 3848-0840", "Argentina") == (
        "4373-9500 / WA: +5491138480840")


def test_a_second_number_is_never_dropped():
    """Two mobiles on one row is two numbers, not one number and some noise."""
    assert book_form("+55 11 98940-4332 / +55 11 96334-5500", "Brazil") == (
        "+5511989404332 / +5511963345500")
    assert book_form("+55 11 3044-4609 / 0800 943-7800", "Brazil") == (
        "+551130444609 / 0800 943-7800")


def test_nothing_to_change_reports_nothing_to_change():
    assert book_form("+17138872805", "USA") is None
    assert book_form("", "USA") is None

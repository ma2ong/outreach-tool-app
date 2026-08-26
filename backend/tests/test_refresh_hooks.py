"""Rewriting the hooks that several companies shared, from data already on the record."""
from app.refresh_hooks import rewrite


def test_the_city_is_what_separates_two_rental_houses():
    assert rewrite("Saw the rental work on your site.", "Houston, TX", None) == \
        "Saw the rental work you do around Houston."


def test_the_second_thing_the_brief_quoted_comes_back_in():
    """The brief had two categories and the hook kept one — that is how 336 leads ended
    up sharing a sentence."""
    brief = 'The site mentions "locação" (rental) and "eventos" (events).'
    assert rewrite("Saw the rental work on your site.", None, brief) == \
        "Saw the rental and events work on your site."


def test_city_and_second_term_together():
    brief = 'The site mentions "locação" (rental) and "eventos" (events).'
    assert rewrite("Saw the rental work on your site.", "São Paulo, SP", brief) == \
        "Saw the rental and events work you do around São Paulo."


def test_an_overlapping_pair_says_one_thing_twice():
    brief = 'The site mentions "signage" and "digital sign" (digital signage).'
    assert "digital signage" not in rewrite("Saw the signage work on your site.", None, brief)


def test_a_city_field_holding_a_list_is_not_pasted_in():
    """`city` really does hold "São Paulo / Goiânia / Rio / Brasília" on some records."""
    out = rewrite("Saw the rental work on your site.", "São Paulo / Goiânia / Rio", None)
    assert "/" not in out


def test_a_pitch_hook_is_already_the_best_kind_and_is_left_alone():
    hook = "Saw P1.9 and P8.9 panels listed on your site."
    assert rewrite(hook, "Houston, TX", 'The site mentions "rental".') == hook


def test_nothing_to_add_means_no_change():
    hook = "Saw the rental work on your site."
    assert rewrite(hook, None, None) == hook


def test_it_never_invents_a_category_the_site_did_not_name():
    """Only what the brief already quoted; this fetches nothing and must not guess."""
    out = rewrite("Saw the rental work on your site.", None,
                  'The site mentions "locação" (rental).')
    assert out == "Saw the rental work on your site."

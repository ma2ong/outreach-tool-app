"""Copy is an experiment, not one total (docs/69).

The only figure available before this was "361 sent, 1 reply" — four markets, five
customer types, three steps and two languages compressed into one number that cannot say
whether the opener is weak, the list is wrong, or the third letter is what burns people.
Every adjustment made without the breakdown is a guess.
"""
import pytest

from app import campaigns
from app import copy_experiments as ce
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country) VALUES
            (1,'A','USA'), (2,'B','USA'), (3,'C','South Korea'), (4,'D','USA');
        INSERT INTO outreach(lead_no, channel, status) VALUES
            (1,'email','replied'), (2,'email','messaged'),
            (3,'email','messaged'), (4,'email','replied');
    """)
    c.commit()
    return c


def _send(conn, no, **kw):
    campaigns.log_send(conn, no, kw.pop("channel", "email"), "序列:x", **kw)


def test_the_table_answers_a_question_the_single_number_could_not(conn):
    _send(conn, 1, variant="英语·角度二", step=0, audience="租赁商", market="USA")
    _send(conn, 2, variant="英语·角度二", step=0, audience="租赁商", market="USA")
    _send(conn, 3, variant="英语·角度二", step=0, audience="工程商", market="South Korea")

    by_market = {r["market"]: r for r in ce.breakdown(conn, ("variant", "market"))}
    assert by_market["USA"]["reply_rate"] == 50.0
    assert by_market["South Korea"]["reply_rate"] == 0.0


def test_it_can_be_cut_by_who_read_it(conn):
    _send(conn, 1, variant="v", step=0, audience="租赁商", market="USA")
    _send(conn, 3, variant="v", step=0, audience="工程商", market="South Korea")
    rows = {r["audience"]: r["reply_rate"] for r in ce.breakdown(conn, ("audience",))}
    assert rows["租赁商"] == 100.0 and rows["工程商"] == 0.0


def test_three_letters_to_one_customer_are_one_lead_not_three(conn):
    # Otherwise a three-step sequence looks like a third of the reply rate it earned.
    for step in (0, 1, 2):
        _send(conn, 1, variant="v", step=step, audience="租赁商", market="USA")
    row = ce.breakdown(conn, ("variant",))[0]
    assert row["sent"] == 3 and row["leads"] == 1 and row["replied"] == 1
    assert row["reply_rate"] == 100.0


def test_history_without_the_fields_is_unmeasured_not_zero(conn):
    campaigns.log_send(conn, 1, "email", "序列:旧的")    # no variant
    assert ce.breakdown(conn, ("variant",)) == []
    assert ce.unmeasured(conn) == 1


def test_an_unknown_dimension_is_refused_rather_than_guessed(conn):
    with pytest.raises(ValueError):
        ce.breakdown(conn, ("colour",))


def test_a_reply_on_another_channel_is_not_credited_to_this_one(conn):
    conn.execute("INSERT INTO outreach(lead_no, channel, status)"
                 " VALUES (3,'whatsapp','replied')")
    conn.commit()
    _send(conn, 3, variant="v", step=0, audience="工程商", market="South Korea")
    assert ce.breakdown(conn, ("variant",))[0]["replied"] == 0


# --- R3: split, do not switch everything at once ---------------------------------

def test_a_customer_stays_in_the_same_arm():
    # An experiment where the same person sees both versions measures nothing.
    arms = ["角度一", "角度二"]
    assert ce.variant_for(7, arms) == ce.variant_for(7, arms)


def test_the_split_is_even_enough_to_compare():
    arms = ["角度一", "角度二"]
    picked = [ce.variant_for(n, arms) for n in range(100)]
    assert picked.count("角度一") == picked.count("角度二") == 50


def test_one_arm_means_everyone_gets_it():
    assert ce.variant_for(3, ["只有一个"]) == "只有一个"


def test_no_arms_means_no_choice():
    assert ce.variant_for(3, []) is None

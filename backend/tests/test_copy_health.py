"""Copy that can never be sent should say so before Allen picks it (docs/82).

Twelve templates sat in the table refusing to send and nothing reported it: three carried
the exit lines docs/82 bans, the rest had no {company} anywhere. The refusal only showed
up as a block at send time, with a reason that reads like a problem with the customer.
"""
import pytest

from app import copy_health
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    return c


def _template(conn, name, subject, body, channel="email"):
    conn.execute("INSERT INTO templates(name, channel, subject, body, lang)"
                 " VALUES (?,?,?,?,'en')", (name, channel, subject, body))
    conn.commit()


def test_copy_that_can_never_send_is_reported(conn):
    _template(conn, "no company anywhere", "Recent LED projects",
              "Hi, we build LED panels in Shenzhen. Worth a conversation?")
    out = copy_health.scan(conn)
    assert len(out["refused"]) == 1
    assert out["refused"][0]["reason"] == "impersonal"
    assert out["refused"][0]["name"] == "no company anywhere"


def test_an_exit_line_is_reported_on_a_dm_template_too(conn):
    _template(conn, "goodbye DM", None,
              "Hi {company}, this is my last message — I'll stop here.",
              channel="whatsapp")
    out = copy_health.scan(conn)
    assert out["by_reason"] == {"exit_line": 1}


def test_copy_that_sends_is_not_reported(conn):
    _template(conn, "good one", "indoor LED specs",
              "Hi {contact},\n\nThis is Allen with an LED display manufacturer in Shenzhen.\n"
              "We cover P2-P3 indoor at 600-800 nits. Would a spec sheet help {company}?")
    out = copy_health.scan(conn)
    assert out["refused"] == [] and out["checked"] == 1


def test_the_verdict_uses_a_lead_with_everything_filled_in(conn):
    """A refusal must mean 'never sendable', not 'this lead was thin' — otherwise the
    check cries wolf on every company with no city."""
    _template(conn, "leans on the city", "LED panel specs",
              "Hi {contact}, we supply {city} companies like {company} direct.")
    assert copy_health.scan(conn)["refused"] == []

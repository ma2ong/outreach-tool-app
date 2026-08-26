"""The end-of-day note, written the way a sales assistant reports to the person in charge.

The old one was six numbers with no nouns in them: "发出 40 条" told Allen nothing about
which channel, which customers, or what he is supposed to do next. A report he cannot act
on is a report he stops reading.
"""
import datetime as dt

import pytest

from app.agent import report
from app.db import connect, init_schema

TODAY = dt.date(2026, 8, 26)


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, email, phone, instagram, hook) VALUES
            (1,'Verum AV','USA','a@verumav.com','+13468378628','verumav','Saw the rental work.'),
            (2,'Orlando Video Walls','USA','b@ovw.com','+13477964269','ovw','Saw P1 panels.'),
            (3,'CCS Projects','USA','c@ccs.com','+19493506983','ccsav','Saw the AV work.'),
            (4,'LedWave','Brazil','d@ledwave.com','+5511956635316','ledwave','Saw P1-P10.'),
            (5,'Samik','South Korea','e@samik.kr','+8225102000','samik','Saw the signage work.');
    """)
    c.commit()
    return c


def _sent(conn, lead_no, channel, campaign, when=TODAY):
    conn.execute("INSERT INTO send_log(lead_no, channel, campaign, sent_at) VALUES (?,?,?,?)",
                 (lead_no, channel, campaign, f"{when.isoformat()}T10:00:00"))
    conn.commit()


def _inbox(conn, lead_no, kind, body="hi", when=TODAY):
    conn.execute(
        "INSERT INTO inbox_messages(lead_no, channel, kind, from_addr, subject, body, received_at)"
        " VALUES (?, 'email', ?, 'x@y.com', 'Re:', ?, ?)",
        (lead_no, kind, body, f"{when.isoformat()}T11:00:00"))
    conn.commit()


# ---------------------------------------------------------------- what went out

def test_it_says_which_channel_and_names_the_companies(conn):
    """"发出 40 条" is not something anyone can act on."""
    _sent(conn, 1, "email", "序列:冷邮件 3 步跟进（英语）")
    _sent(conn, 2, "email", "序列:冷邮件 3 步跟进（英语）")
    _sent(conn, 3, "instagram", "每日社媒队列")
    text = report.compose(conn, TODAY)
    assert "邮件" in text and "Instagram" in text
    assert "Verum AV" in text and "CCS Projects" in text


def test_a_long_list_is_summarised_not_dumped(conn):
    """Forty company names is a wall, not a report."""
    for no in range(1, 6):
        _sent(conn, no, "email", "序列:冷邮件 3 步跟进（英语）")
    text = report.compose(conn, TODAY)
    assert "等 5 家" in text or "共 5 家" in text
    assert text.count("Verum AV") <= 1


def test_which_sequence_step_went_out(conn):
    """"First touch" and "third follow-up" are different days of work."""
    _sent(conn, 1, "email", "序列:冷邮件 3 步跟进（英语）")
    assert "英语" in report.compose(conn, TODAY)


# ---------------------------------------------------------------- what came back

def test_a_reply_is_named_because_it_is_the_only_thing_that_matters(conn):
    _inbox(conn, 4, "reply", "Please send pricing for P2.5")
    text = report.compose(conn, TODAY)
    assert "LedWave" in text and "回复" in text


def test_bounces_and_autoreplies_are_counted_apart_from_real_replies(conn):
    """Reading an autoresponder as a reply is what stopped a live sequence in August."""
    _inbox(conn, 1, "reply")
    _inbox(conn, 2, "auto")
    _inbox(conn, 3, "bounce")
    text = report.compose(conn, TODAY)
    assert "自动回复 1" in text and "退信 1" in text


# ---------------------------------------------------------------- what is waiting

def test_it_ends_with_what_is_queued_for_tomorrow(conn):
    """A report about a finished day still has to say what happens next."""
    conn.executescript("""
        INSERT INTO sequences(id, name, channel, active, created_at)
            VALUES (1, '冷邮件 3 步跟进（英语）', 'email', 1, '2026-08-01');
        INSERT INTO sequence_steps(sequence_id, step_order, day_offset, subject, body)
            VALUES (1, 0, 0, 'S', 'B');
        INSERT INTO sequence_enrollments(lead_no, sequence_id, current_step, status,
                                         enrolled_at, next_due_date)
            VALUES (1, 1, 0, 'active', '2026-08-01', '2026-08-26'),
                   (2, 1, 0, 'active', '2026-08-01', '2026-08-26');
    """)
    conn.commit()
    assert "2 条" in report.compose(conn, TODAY)


def test_pricing_requests_are_called_out_because_they_are_allens_alone(conn):
    from app.agent import proposals

    proposals.ensure_schema(conn)
    proposals.set_autonomy(conn, "create_task", "propose")
    proposals.create(conn, "create_task", lead_no=1, title="要你来定价：Verum AV 200sqm",
                     payload={})
    assert "报价" in report.compose(conn, TODAY)


# ---------------------------------------------------------------- shape

def test_a_quiet_day_says_so_plainly_instead_of_printing_empty_sections(conn):
    text = report.compose(conn, TODAY)
    assert "没有" in text
    assert "邮件 0" not in text  # 不为了对齐格式而列一堆零


def test_yesterdays_work_is_not_in_todays_report(conn):
    _sent(conn, 1, "email", "序列", when=TODAY - dt.timedelta(days=1))
    assert "Verum AV" not in report.compose(conn, TODAY)

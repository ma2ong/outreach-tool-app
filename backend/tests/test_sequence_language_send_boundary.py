from app import sequence_send, sequences
from app.db import connect, init_schema


def _db(tmp_path):
    conn = connect(str(tmp_path / "sequence-language.db"))
    init_schema(conn)
    conn.executescript("""
        INSERT INTO leads(no, company_en, country, email) VALUES
          (1, 'US Integrator', 'USA', 'sales@us.example'),
          (2, 'Korea AV', 'South Korea', 'sales@kr.example');
    """)
    conn.commit()
    return conn


def test_sequence_name_does_not_define_customer_language(tmp_path):
    conn = _db(tmp_path)
    sid = sequences.create_sequence(
        conn, "韩国客户英文跟进", "email",
        [{"day_offset": 0, "subject": "LED display follow-up", "body": "Hi, following up."}],
    )
    assert sequences.is_korean_sequence(conn, sid) is False
    assert sequences.language_blocked(conn, sid, [1, 2]) == []
    assert sequences.enroll_leads(conn, sid, [1, 2]) == 2


def test_historical_wrong_language_enrollment_never_enters_send_queue(tmp_path):
    conn = _db(tmp_path)
    sid = sequences.create_sequence(
        conn, "Korean follow-up", "email",
        [{"day_offset": 0, "subject": "한국 LED 디스플레이", "body": "안녕하세요. 후속 연락드립니다."}],
    )
    today = sequences._today()
    # Simulate a row created before the language guard existed. Do not use enroll_leads:
    # the point is to prove the send boundary protects historical bad data too.
    cur = conn.execute(
        "INSERT INTO sequence_enrollments"
        "(lead_no, sequence_id, current_step, status, enrolled_at, next_due_date)"
        " VALUES (1, ?, 0, 'active', ?, ?)",
        (sid, today, today),
    )
    bad_enrollment = cur.lastrowid
    conn.commit()

    assert bad_enrollment not in {row["enrollment_id"] for row in sequences.due_queue(conn)}

    def must_not_send(*_args, **_kwargs):
        raise AssertionError("wrong-language historical enrollment reached sender")

    result = sequence_send.send_due(conn, [bad_enrollment], sender=must_not_send)
    assert result["sent"] == 0
    assert result["failed"] == 0


def test_korean_copy_still_reaches_korean_lead(tmp_path):
    conn = _db(tmp_path)
    sid = sequences.create_sequence(
        conn, "Korean follow-up", "email",
        [{"day_offset": 0, "subject": "한국 LED 디스플레이", "body": "안녕하세요. 후속 연락드립니다."}],
    )
    assert sequences.language_blocked(conn, sid, [1, 2]) == [1]
    assert sequences.enroll_leads(conn, sid, [1, 2]) == 1
    due = sequences.due_queue(conn)
    assert [row["lead_no"] for row in due] == [2]

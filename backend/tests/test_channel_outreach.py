from app import channel_outreach as co
from app.browser_engine import FakeEngine


def _seed(conn):
    conn.executescript("""
        DELETE FROM outreach;
        DELETE FROM leads;
        INSERT INTO leads(no, company_en, phone, instagram) VALUES
            (1,'Alpha','+1 (555) 123-4567','alpha_ig'),
            (2,'Beta',NULL,'beta_ig'),
            (3,'Gamma','+55 11 99999-8888',NULL),
            (4,'Delta','+1 555 000 1111','delta_ig');
        INSERT INTO outreach(lead_no, channel, status) VALUES (4,'whatsapp','messaged');
    """)
    conn.commit()


def test_eligible_whatsapp_needs_phone_and_not_sent(conn):
    _seed(conn)
    elig = co.eligible(conn, [1, 2, 3, 4], "whatsapp")
    assert [l["no"] for l in elig] == [1, 3]  # 2 no phone, 4 already messaged


def test_eligible_instagram_needs_handle(conn):
    _seed(conn)
    elig = co.eligible(conn, [1, 2, 3, 4], "instagram")
    assert [l["no"] for l in elig] == [1, 2, 4]  # 3 has no instagram


def test_send_whatsapp_normalizes_number_and_marks(conn):
    _seed(conn)
    eng = FakeEngine()
    res = co.send_channel_campaign(conn, [1, 3], "whatsapp", "Hi {name}", eng, delay_range=(0, 0))
    assert res["sent"] == 2
    # phone normalized to digits only
    assert ("whatsapp", "15551234567", "Hi Alpha", None) in eng.sent
    assert ("whatsapp", "5511999998888", "Hi Gamma", None) in eng.sent
    rows = conn.execute("SELECT lead_no FROM outreach WHERE channel='whatsapp' AND status='messaged' ORDER BY lead_no").fetchall()
    assert [r["lead_no"] for r in rows] == [1, 3, 4]


def test_send_instagram_uses_handle(conn):
    _seed(conn)
    eng = FakeEngine()
    res = co.send_channel_campaign(conn, [1], "instagram", "yo {name}", eng, delay_range=(0, 0))
    assert res["sent"] == 1
    assert eng.sent == [("instagram", "alpha_ig", "yo Alpha", None)]


def test_send_passes_image_through(conn):
    _seed(conn)
    eng = FakeEngine()
    res = co.send_channel_campaign(conn, [1], "whatsapp", "Hi {name}", eng,
                                   delay_range=(0, 0), image="C:/poster.jpg")
    assert res["sent"] == 1
    assert eng.sent == [("whatsapp", "15551234567", "Hi Alpha", "C:/poster.jpg")]


def test_send_records_failure(conn):
    _seed(conn)
    eng = FakeEngine()
    eng.fail_targets.add("15551234567")
    res = co.send_channel_campaign(conn, [1], "whatsapp", "Hi", eng, delay_range=(0, 0))
    assert res["failed"] == 1 and res["sent"] == 0


def test_uncertain_social_transport_is_not_reentered(conn):
    _seed(conn)

    class AcceptedThenTimeout:
        def __init__(self):
            self.calls = []

        def send_message(self, channel, target, body, image):
            self.calls.append((channel, target, body))
            raise TimeoutError("browser result unknown")

    engine = AcceptedThenTimeout()
    first = co.send_channel_campaign(
        conn, [1], "instagram", "Hi {name}", engine, delay_range=(0, 0),
        campaign="Manual social")
    second = co.send_channel_campaign(
        conn, [1], "instagram", "Hi {name}", engine, delay_range=(0, 0),
        campaign="Manual social")

    assert first["failed"] == 1
    assert second["sent"] == 0
    assert len(engine.calls) == 1
    assert conn.execute("SELECT status FROM delivery_intents").fetchone()["status"] == "unknown"


def test_batch_capped_at_20(conn):
    conn.execute("DELETE FROM outreach")
    conn.execute("DELETE FROM leads")
    conn.executemany(
        "INSERT INTO leads(no, company_en, phone) VALUES (?, ?, ?)",
        [(i, f"Co{i}", f"+1555000{i:04d}") for i in range(1, 26)])
    conn.commit()
    eng = FakeEngine()
    res = co.send_channel_campaign(conn, list(range(1, 26)), "whatsapp", "Hi", eng, delay_range=(0, 0))
    assert res["sent"] == 20
    assert res["deferred"] == 5
    assert res["skipped"] == 0
    assert len(eng.sent) == 20


def test_eligible_excludes_replied(conn):
    _seed(conn)
    conn.execute("INSERT INTO outreach(lead_no, channel, status) VALUES (1,'whatsapp','replied')")
    conn.commit()
    assert [l["no"] for l in co.eligible(conn, [1, 3], "whatsapp")] == [3]


def test_daily_cap_limits_batch(conn):
    import datetime
    today = datetime.date.today().isoformat()
    conn.execute("DELETE FROM outreach")
    conn.execute("DELETE FROM leads")
    conn.executemany(
        "INSERT INTO leads(no, company_en, phone) VALUES (?, ?, ?)",
        [(i, f"Co{i}", f"+1555000{i:04d}") for i in range(1, 16)])
    # 35 already sent today on other leads -> only 5 left of the 40/day cap
    conn.executemany(
        "INSERT INTO leads(no, company_en, phone) VALUES (?, ?, ?)",
        [(i, f"Old{i}", f"+1666000{i:04d}") for i in range(100, 135)])
    conn.executemany(
        "INSERT INTO outreach(lead_no, channel, status, message_sent_date) VALUES (?, 'whatsapp', 'messaged', ?)",
        [(i, today) for i in range(100, 135)])
    conn.commit()
    eng = FakeEngine()
    res = co.send_channel_campaign(conn, list(range(1, 16)), "whatsapp", "Hi", eng, delay_range=(0, 0))
    assert res["sent"] == 5
    assert res["deferred"] == 10


def test_sent_today_counts_channel(conn):
    import datetime
    today = datetime.date.today().isoformat()
    _seed(conn)
    conn.execute("UPDATE outreach SET message_sent_date=? WHERE lead_no=4", (today,))
    conn.commit()
    assert co.sent_today(conn, "whatsapp") == 1
    assert co.sent_today(conn, "instagram") == 0


def test_facebook_eligible_and_send(conn):
    from app import channel_outreach as co
    from app.browser_engine import FakeEngine
    conn.execute("UPDATE leads SET facebook='alphafb' WHERE no=1")
    conn.execute("UPDATE leads SET facebook='gammafb' WHERE no=3")
    conn.commit()
    assert [l["no"] for l in co.eligible(conn, [1, 2, 3], "facebook")] == [1, 3]
    engine = FakeEngine()
    res = co.send_channel_campaign(conn, [1, 3], "facebook", "Hi {name}", engine,
                                   delay_range=(0, 0), image="poster.jpg")
    assert res["sent"] == 2
    assert engine.sent[0] == ("facebook", "alphafb", "Hi Alpha AV", "poster.jpg")
    # 阶段自动跟随
    assert conn.execute("SELECT stage FROM leads WHERE no=1").fetchone()["stage"] == "contacted"


def test_facebook_daily_cap_is_lower(conn):
    from app import channel_outreach as co
    assert co.DAILY_CAP["facebook"] == 20 < co.DAILY_CAP["whatsapp"]
    assert co.DEFAULT_DELAY["facebook"][0] >= co.DEFAULT_DELAY["instagram"][0]

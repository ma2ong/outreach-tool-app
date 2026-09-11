"""WhatsApp/Instagram inbound detection. 527 of 616 touched leads sat on these two
channels with no inbound path at all, so every rule here is about not turning that
blind spot into a *wrong* spot."""
import pytest

from app import inbound
from app.browser_engine import FakeEngine
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, phone, instagram) VALUES
            (1, 'LedWave', 'Brazil', '5511988887777', 'ledwave.br'),
            (2, 'Mundo de LED', 'Brazil', '+55 21 97777-6666', '@mundoled'),
            (3, 'Demco', 'Chile', '56912345678', NULL);
        INSERT INTO outreach(lead_no, channel, status, touch_count) VALUES
            (1, 'whatsapp', 'messaged', 1),
            (2, 'whatsapp', 'messaged', 1),
            (1, 'instagram', 'messaged', 1);
    """)
    c.commit()
    return c


def _thread(sender, preview="Hi, please send price list", outgoing=False):
    return {"sender": sender, "name": sender, "preview": preview,
            "outgoing": outgoing, "unread": True}


# ---- matching ----

def test_matches_number_however_whatsapp_formats_it(conn):
    res = inbound.process_threads(conn, "whatsapp", [_thread("+55 11 98888-7777")])
    assert res["replies"] == 1 and res["lead_nos"] == [1]
    assert conn.execute(
        "SELECT status FROM outreach WHERE lead_no=1 AND channel='whatsapp'"
    ).fetchone()[0] == "replied"


def test_stored_lead_phone_with_punctuation_still_matches(conn):
    res = inbound.process_threads(conn, "whatsapp", [_thread("+55 21 9 7777-6666")])
    assert res["lead_nos"] == [2]


def test_instagram_handle_matches_ignoring_at_and_case(conn):
    res = inbound.process_threads(conn, "instagram", [_thread("@LedWave.BR")])
    assert res["lead_nos"] == [1]
    assert conn.execute(
        "SELECT status FROM outreach WHERE lead_no=1 AND channel='instagram'"
    ).fetchone()[0] == "replied"


def test_ambiguous_tail_is_never_guessed(conn):
    """Two leads ending in the same 8 digits: marking the wrong customer as replied
    would stop the follow-up sequence for someone who never answered."""
    conn.execute("UPDATE leads SET phone='5521988887777' WHERE no=3")
    conn.commit()
    res = inbound.process_threads(conn, "whatsapp", [_thread("988887777")])
    assert res["replies"] == 0 and res["unmatched"] == ["988887777"]


def test_saved_contact_name_is_not_forced_into_a_match(conn):
    res = inbound.process_threads(conn, "whatsapp", [_thread("Carlos Silva")])
    assert res["replies"] == 0 and res["unmatched"] == ["Carlos Silva"]


# ---- direction ----

def test_our_own_last_message_is_not_a_reply(conn):
    """Nearly every thread's last message is ours; counting those as replies would
    report 616 replies and be exactly as useless as reporting 0."""
    res = inbound.process_threads(
        conn, "whatsapp", [_thread("+55 11 98888-7777", outgoing=True)])
    assert res["replies"] == 0 and res["outgoing"] == 1
    assert conn.execute(
        "SELECT status FROM outreach WHERE lead_no=1 AND channel='whatsapp'"
    ).fetchone()[0] == "messaged"


# ---- storage ----

def test_same_preview_is_not_recorded_twice(conn):
    inbound.process_threads(conn, "whatsapp", [_thread("+55 11 98888-7777")])
    res = inbound.process_threads(conn, "whatsapp", [_thread("+55 11 98888-7777")])
    assert res["replies"] == 1 and res["stored"] == 0
    assert conn.execute("SELECT COUNT(*) FROM inbox_messages").fetchone()[0] == 1


def test_new_message_from_same_lead_lands_as_a_new_row(conn):
    inbound.process_threads(conn, "whatsapp", [_thread("+55 11 98888-7777", "price?")])
    inbound.process_threads(conn, "whatsapp", [_thread("+55 11 98888-7777", "and P2.5?")])
    bodies = [r[0] for r in conn.execute(
        "SELECT body FROM inbox_messages WHERE lead_no=1 ORDER BY id")]
    assert bodies == ["price?", "and P2.5?"]


def test_reply_stops_the_whatsapp_sequence(conn):
    from app import sequences
    sid = sequences.create_sequence(conn, "WA", "whatsapp", [{"day_offset": 0, "body": "hi"}])
    sequences.enroll_leads(conn, sid, [1, 2])
    inbound.process_threads(conn, "whatsapp", [_thread("+55 11 98888-7777")])
    assert {d["lead_no"] for d in sequences.due_queue(conn, "whatsapp")} == {2}


# ---- orchestration ----

def test_one_broken_channel_does_not_hide_the_other(conn):
    def scanner(channel):
        if channel == "instagram":
            raise RuntimeError("Instagram markup changed")
        return [_thread("+55 11 98888-7777")]

    res = inbound.scan_all(conn, scanner)
    assert res["replies"] == 1
    assert res["errors"] == [{"channel": "instagram", "error": "Instagram markup changed"}]
    # a partially failed sweep must not tick the day off, or Instagram would stay
    # unscanned until tomorrow on the strength of WhatsApp having worked
    assert inbound.should_scan_today(conn, _dt())


def test_social_reply_enrichment_failure_is_reported_as_partial_not_swallowed(conn, monkeypatch):
    monkeypatch.setattr(
        "app.reply_details.apply",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("parser broke")),
    )
    result = inbound.scan_all(
        conn, lambda channel: [_thread("+55 11 98888-7777")] if channel == "whatsapp" else [],
    )

    assert result["replies"] == 1
    assert result["errors"] == [{
        "lead_no": 1, "message_id": 1, "stage": "reply_details", "error": "parser broke",
    }]
    assert inbound.should_scan_today(conn, _dt())


def test_clean_sweep_marks_the_day_done(conn):
    engine = FakeEngine()
    engine.threads = {"whatsapp": [_thread("+55 11 98888-7777")], "instagram": []}
    assert inbound.should_scan_today(conn, _dt())
    inbound.scan_all(conn, engine.scan_threads)
    assert not inbound.should_scan_today(conn, _dt())


def test_outside_the_window_no_scan_is_owed(conn):
    import datetime
    assert not inbound.should_scan_today(conn, datetime.datetime(2026, 8, 3, 3, 0))


def test_status_survives_a_corrupt_result_blob(conn):
    from app import settings
    settings.set_value(conn, "social_scan_last_result", "{not json")
    assert inbound.status(conn)["last_result"] is None


def _dt():
    # inside the scan window, today — a hard-coded date made "the day is done" pass only
    # on the day the test was written, since the scan records the real current date
    import datetime
    return datetime.datetime.combine(datetime.date.today(), datetime.time(10, 0))


# ---- Instagram display-name matching ----
# Verbatim thread titles from Allen's Instagram inbox: IG never shows the @handle, so
# without the company-name fallback every Instagram thread is unattributable.

def test_display_name_with_a_tagline_matches_the_company(conn):
    conn.execute("UPDATE leads SET company_en='LED ABC', instagram='ledabcpaineldeled' WHERE no=1")
    conn.commit()
    res = inbound.process_threads(
        conn, "instagram", [_thread("LED ABC - Painéis de LED", "quanto custa?")])
    assert res["lead_nos"] == [1]


def test_display_name_shorter_than_the_company_still_matches(conn):
    conn.execute("UPDATE leads SET company_en='Light It Up AV & Turf' WHERE no=3")
    conn.commit()
    res = inbound.process_threads(conn, "instagram", [_thread("Light It Up AV", "interested")])
    assert res["lead_nos"] == [3]


def test_pipe_tagline_is_cut(conn):
    conn.execute("UPDATE leads SET company_en='ProCore Productions' WHERE no=3")
    conn.commit()
    res = inbound.process_threads(
        conn, "instagram", [_thread("ProCore Productions | LA AV Rentals", "send specs")])
    assert res["lead_nos"] == [3]


def test_two_companies_sharing_a_prefix_are_left_alone(conn):
    conn.execute("UPDATE leads SET company_en='LED Solutions Brazil' WHERE no=1")
    conn.execute("UPDATE leads SET company_en='LED Solutions Chile' WHERE no=3")
    conn.commit()
    res = inbound.process_threads(conn, "instagram", [_thread("LED Solutions", "hi")])
    assert res["replies"] == 0


def test_short_generic_name_never_matches(conn):
    conn.execute("UPDATE leads SET company_en='LED' WHERE no=1")
    conn.commit()
    assert inbound.process_threads(conn, "instagram", [_thread("LED", "hi")])["replies"] == 0


def test_whatsapp_saved_contact_falls_back_to_company_name(conn):
    conn.execute("UPDATE leads SET company_en='Demco Ltda' WHERE no=3")
    conn.commit()
    res = inbound.process_threads(conn, "whatsapp", [_thread("Demco Ltda", "precio?")])
    assert res["lead_nos"] == [3]


def test_unattributable_inbound_is_reported_not_dropped(conn):
    """A reply we cannot pin to a lead is still someone talking to Allen; swallowing it
    would rebuild the very blind spot this closes."""
    res = inbound.scan_all(conn, lambda ch: [_thread("齋藤留美", "hey random msg")]
                           if ch == "instagram" else [])
    assert res["unmatched"] == ["齋藤留美"]


# ---- row parsing ----
# Leaf sets copied verbatim from Allen's Instagram inbox.

def test_instagram_row_is_read_from_leaves():
    t = inbound.instagram_thread(
        ["Mobile Billboard Trucks", "你: Hi! I'm Allen, from an LED display factory", "·", "8周"])
    assert t["sender"] == "Mobile Billboard Trucks" and t["outgoing"]


def test_verified_badge_does_not_become_the_preview():
    t = inbound.instagram_thread(
        ["Mobile Billboard Miami", "已验证", "你: Hi! I'm Allen", "·", "8周"])
    assert t["outgoing"] and t["preview"].startswith("你:")


def test_media_sent_by_us_is_outgoing():
    """'你发送了照片。' has no colon; missing it counted our own photo as their reply."""
    assert inbound.instagram_thread(["Crunchy Tech", "你发送了照片。", "·", "4周"])["outgoing"]


def test_their_message_is_inbound():
    t = inbound.instagram_thread(["여동진 플레져 PLZR", "넵", "·", "2周"])
    assert t and not t["outgoing"]


def test_platform_notice_is_not_a_message():
    assert inbound.instagram_thread(
        ["Light It Up AV", "这个账户无法接收消息，因为对方不接收任何人发来的新陌生消息。", "·"]) is None


def test_row_without_a_readable_preview_is_dropped():
    """The regression that produced 112 false replies out of 193 threads: a row with no
    usable preview must not default to 'they answered'."""
    assert inbound.instagram_thread(["Adam Ortiz", "·", "8周"]) is None
    assert inbound.instagram_thread([]) is None


def test_whatsapp_direction_comes_from_the_icon_not_the_text():
    """WhatsApp's status icon is a DOM query, so direction stays right even when the
    preview text is garbled by a mid-scroll re-render."""
    out = inbound.whatsapp_thread(["+55 11 98888-7777", "10:32", "Ok, send the quote"],
                                  title="+55 11 98888-7777", outgoing=True)
    assert out["outgoing"] and out["preview"] == "Ok, send the quote"
    inb = inbound.whatsapp_thread(["+55 11 98888-7777", "10:32", "Ok, send the quote"],
                                  title="+55 11 98888-7777", outgoing=False)
    assert not inb["outgoing"]


def test_whatsapp_prefers_the_title_attribute_for_the_name():
    t = inbound.whatsapp_thread(["truncated nam…", "09:14", "hi"], title="Demco Ltda")
    assert t["sender"] == "Demco Ltda"


# ---- autoresponders ----
# Verbatim previews from Allen's Instagram inbox. Marking these replied would end the
# follow-up sequence for a lead no human has actually read.

@pytest.mark.parametrize("preview", [
    "Hi, thanks for contacting us. We've received your message",
    "Thank you for your message! For any inquiries please email",
    "Hello leddisplay_allen, please send us your requirements",
    "您好！我们会在短时间内为您解答。",
    "안녕하세요. 메시지가 접수되었습니다. 문의해주셔서 감사합니다.",
])
def test_autoresponder_is_recorded_but_not_treated_as_a_reply(conn, preview):
    res = inbound.process_threads(conn, "whatsapp", [_thread("+55 11 98888-7777", preview)])
    assert res["auto"] == 1 and res["replies"] == 0 and res["stored"] == 1
    assert conn.execute(
        "SELECT status FROM outreach WHERE lead_no=1 AND channel='whatsapp'"
    ).fetchone()[0] == "messaged"
    assert conn.execute("SELECT kind FROM inbox_messages WHERE lead_no=1").fetchone()[0] == "auto"


def test_autoresponder_does_not_stop_the_sequence(conn):
    from app import sequences
    sid = sequences.create_sequence(conn, "WA", "whatsapp", [{"day_offset": 0, "body": "hi"}])
    sequences.enroll_leads(conn, sid, [1])
    inbound.process_threads(
        conn, "whatsapp", [_thread("+55 11 98888-7777", "Thanks for contacting us!")])
    assert {d["lead_no"] for d in sequences.due_queue(conn, "whatsapp")} == {1}


def test_a_real_human_answer_still_counts(conn):
    res = inbound.process_threads(conn, "whatsapp", [_thread("+55 11 98888-7777", "넵")])
    assert res["replies"] == 1 and res["auto"] == 0


def test_page_messaging_notice_is_not_a_message():
    assert inbound.instagram_thread(
        ["Power Factory Productions", "并非所有人都可以发消息给这个主页。", "·"]) is None


@pytest.mark.parametrize("preview", [
    "Hi leddisplay_allen! Thanks for connecting with us. We usually reply within",
    "Hi 👋 leddisplay_allen, we'll be back in the morning to answer you",
    "Thanks for messaging us! Someone will reply shortly",
])
def test_away_messages_are_also_autoresponders(conn, preview):
    """Caught in a live scan: these were being marked as human replies and would have
    ended the follow-up for leads nobody had read."""
    res = inbound.process_threads(conn, "instagram", [_thread("LedWave", preview)])
    assert res["auto"] == 1 and res["replies"] == 0


def test_a_human_reply_that_merely_says_thanks_is_not_swallowed(conn):
    res = inbound.process_threads(
        conn, "instagram", [_thread("LedWave", "Thanks! Please send the P2.5 price")])
    assert res["replies"] == 1 and res["auto"] == 0


@pytest.mark.parametrize("preview", [
    "LedWave 发送了附件。",
    "LedWave sent an attachment",
    "LedWave sent a photo",
])
def test_an_attachment_without_text_is_not_a_human_reply(conn, preview):
    """Verbatim from a live scan: an image-only message is what business automation
    sends, and its preview carries no words to judge. Filed to be looked at, but the
    follow-up keeps running."""
    res = inbound.process_threads(conn, "instagram", [_thread("LedWave", preview)])
    assert res["replies"] == 0 and res["auto"] == 1
    assert conn.execute("SELECT kind FROM inbox_messages WHERE lead_no=1").fetchone()[0] == "attachment"
    assert conn.execute(
        "SELECT status FROM outreach WHERE lead_no=1 AND channel='instagram'"
    ).fetchone()[0] == "messaged"


# ---- what they say about themselves (docs/106 R5) ----

def test_contact_details_in_a_social_reply_reach_the_book(conn):
    """A customer who answers on Instagram states his address the same way he would in
    an email. Until docs/106 this path read none of it."""
    preview = "Sure, send it over.\nE: compras@ledwave.com.br\nW: ledwave.com.br"
    inbound.process_threads(conn, "instagram", [_thread("LedWave", preview)])
    row = conn.execute("SELECT email, website FROM leads WHERE no=1").fetchone()
    assert row["email"] == "compras@ledwave.com.br"
    assert row["website"] == "ledwave.com.br"


def test_an_unlabelled_address_in_a_dm_is_not_adopted(conn):
    """docs/106 R3. A DM has no sender domain to vouch for an address, and this lead
    has no website either — so a bare address in the preview stays out of the book."""
    inbound.process_threads(
        conn, "instagram", [_thread("LedWave", "we buy from tony@absen.com")])
    assert conn.execute("SELECT email FROM leads WHERE no=1").fetchone()[0] is None


def test_a_social_reply_never_overwrites_what_the_book_holds(conn):
    conn.execute("UPDATE leads SET email='old@ledwave.com.br' WHERE no=1")
    conn.commit()
    inbound.process_threads(
        conn, "instagram", [_thread("LedWave", "E: novo@ledwave.com.br")])
    assert conn.execute(
        "SELECT email FROM leads WHERE no=1").fetchone()[0] == "old@ledwave.com.br"

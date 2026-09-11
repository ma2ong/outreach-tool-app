import datetime as dt

from app import opportunities
from app.agent import draft, project_facts


def _message(conn, body: str) -> dict:
    cur = conn.execute(
        "INSERT INTO inbox_messages(lead_no,channel,kind,from_addr,subject,body,received_at)"
        " VALUES (1,'email','reply','buyer@example.com','Re: project',?,?)",
        (body, dt.datetime.now(dt.UTC).isoformat()),
    )
    conn.commit()
    return dict(conn.execute("SELECT * FROM inbox_messages WHERE id=?", (cur.lastrowid,)).fetchone())


def test_customer_stated_led_facts_are_sourced_and_fill_only_empty_opportunity_fields(conn):
    opportunity = opportunities.create(conn, 1, {"title": "Arena screen"})
    message = _message(
        conn,
        "We need 3 outdoor screens, P2.5, each 6m x 3m, 5000 nits and 3840Hz for Q4.",
    )
    captured = project_facts.capture(conn, message)
    assert {item["field"] for item in captured["facts"]} >= {
        "quantity", "indoor_outdoor", "pixel_pitch", "width_m", "height_m",
        "brightness_nits", "refresh_rate_hz", "project_timing",
    }
    pitch = next(item for item in captured["facts"] if item["field"] == "pixel_pitch")
    assert pitch["source_message_id"] == message["id"]
    assert pitch["source_quote"] == "P2.5"

    updated = opportunities.get(conn, opportunity["id"])
    assert updated["pixel_pitch"] == "P2.5"
    assert updated["indoor_outdoor"] == "outdoor"
    assert updated["width_m"] == 6 and updated["height_m"] == 3
    assert updated["brightness_nits"] == 5000
    assert updated["refresh_rate_hz"] == 3840
    assert updated["quantity"] == 1


def test_a_later_conflicting_fact_is_visible_and_does_not_overwrite(conn):
    opportunity = opportunities.create(conn, 1, {
        "title": "Arena screen", "pixel_pitch": "P2.5", "width_m": 6,
    })
    project_facts.capture(conn, _message(conn, "The screen is P2.5 and 6m x 3m."))
    project_facts.capture(conn, _message(conn, "Correction: use P3.0 and 5m x 3m."))

    summary = project_facts.for_lead(conn, 1)
    assert {item["field"] for item in summary["conflicts"]} >= {"pixel_pitch", "width_m"}
    unchanged = opportunities.get(conn, opportunity["id"])
    assert unchanged["pixel_pitch"] == "P2.5" and unchanged["width_m"] == 6


def test_generic_interest_does_not_become_an_invented_project_fact(conn):
    result = project_facts.capture(conn, _message(conn, "Looks interesting. Please tell me more."))
    assert result["facts"] == []


def test_reply_drafting_receives_sourced_facts_and_conflicts(conn):
    first = _message(conn, "Use P2.5 for the outdoor wall.")
    project_facts.capture(conn, first)
    latest = _message(conn, "Correction: the drawing says P3.0.")
    project_facts.capture(conn, latest)
    rendered = draft._render(draft.build_context(conn, latest))
    assert "CUSTOMER-STATED PROJECT FACTS" in rendered
    assert "P2.5" in rendered and "P3" in rendered
    assert "CONFLICT" in rendered

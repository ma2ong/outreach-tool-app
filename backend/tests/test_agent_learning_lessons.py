import datetime as dt
import json

from app.agent import learn, proposals


def _edited_reply(conn, *, lead_no=1, channel="email", before="Long draft", after="Short reply"):
    proposal = proposals.create(
        conn, "reply_draft", lead_no=lead_no, title=f"reply-{channel}-{before}",
        payload={"channel": channel, "body": after}, dedupe_key=f"{channel}-{before}-{after}",
    )
    now = dt.datetime.now(dt.UTC).isoformat()
    conn.execute(
        "UPDATE agent_proposals SET status='executed', original_payload=?, decided_at=? WHERE id=?",
        (json.dumps({"channel": channel, "body": before}), now, proposal["id"]),
    )
    conn.commit()
    return proposal["id"]


def test_raw_edits_are_evidence_not_automatic_global_prompt_rules(conn):
    for i in range(6):
        _edited_reply(conn, before=f"draft {i}", after=f"sent {i}")

    summary = learn.summary(conn)
    assert len(summary["edited_examples"]) == 6
    assert summary["guidance_active"] is False
    assert learn.draft_guidance(conn, channel="email", country="USA",
                                customer_type="install") == ""


def test_only_active_lessons_matching_channel_market_and_customer_type_are_used(conn):
    ids = [_edited_reply(conn, before=f"draft {i}", after=f"sent {i}") for i in range(2)]
    lesson = learn.create_lesson(
        conn, "Ask one concrete next question and remove generic praise.",
        category="sales_action", channel="email", market="USA",
        customer_type="install", source_proposal_ids=ids,
    )
    assert lesson["status"] == "candidate"
    assert lesson["evidence_strength"] == "insufficient"
    assert learn.draft_guidance(conn, channel="email", country="USA",
                                customer_type="install") == ""

    active = learn.set_lesson_status(conn, lesson["id"], "active")
    assert active["status"] == "active"
    assert "Ask one concrete next question" in learn.draft_guidance(
        conn, channel="email", country="United States", customer_type="install")
    assert learn.draft_guidance(conn, channel="instagram", country="USA",
                                customer_type="install") == ""
    assert learn.draft_guidance(conn, channel="email", country="Korea",
                                customer_type="install") == ""

    learn.set_lesson_status(conn, lesson["id"], "retired")
    assert learn.draft_guidance(conn, channel="email", country="USA",
                                customer_type="install") == ""
    events = learn.lesson_events(conn, lesson["id"])
    assert [event["action"] for event in events] == ["created", "activated", "retired"]


def test_learning_lesson_edits_create_a_new_version_without_rewriting_history(conn):
    lesson = learn.create_lesson(conn, "Use one question.", category="tone")
    revised = learn.revise_lesson(conn, lesson["id"], "Use one short question.")

    assert revised["version"] == 2
    assert revised["supersedes_id"] == lesson["id"]
    assert learn.get_lesson(conn, lesson["id"])["rule_text"] == "Use one question."
    assert learn.get_lesson(conn, lesson["id"])["status"] == "retired"
    assert revised["status"] == "candidate"

"""What the customer memory must never do: forget silently, or state what it cannot source."""
import datetime as dt

import pytest

from app.agent import memory, proposals


def _message(conn, lead_no=1, body="Budget only opens in Q3.") -> int:
    cur = conn.execute(
        "INSERT INTO inbox_messages(lead_no, channel, kind, from_addr, subject, body,"
        " received_at) VALUES (?, 'email', 'reply', 'buyer@alpha.com', 'Re: LED', ?, ?)",
        (lead_no, body, dt.datetime.now(dt.UTC).isoformat()))
    conn.commit()
    return cur.lastrowid


def _note(conn, lead_no=1, text="Called, prefers WhatsApp.") -> int:
    cur = conn.execute(
        "INSERT INTO notes(lead_no, created_at, text) VALUES (?, ?, ?)",
        (lead_no, dt.datetime.now(dt.UTC).isoformat(), text))
    conn.commit()
    return cur.lastrowid


def test_unmentioned_items_survive_a_synthesis(conn):
    """The whole point. The old memory rewrote 200 characters of prose every time, so a
    fact stayed only if the model happened to restate it; here it stays unless something
    explicitly removes it."""
    evidence = f"inbox:{_message(conn)}"
    memory.apply_changes(conn, 1, [
        {"action": "create", "kind": "profile", "content": "Buys through a distributor.",
         "evidence": [evidence]},
        {"action": "create", "kind": "log", "content": "Budget opens Q3.",
         "evidence": [evidence]},
    ])
    later = f"inbox:{_message(conn, body='Sending the drawings tomorrow.')}"
    memory.apply_changes(conn, 1, [
        {"action": "create", "kind": "log", "content": "Drawings due tomorrow.",
         "evidence": [later]},
    ])
    contents = {item["content"] for item in memory.items(conn, 1)}
    assert contents == {"Buys through a distributor.", "Budget opens Q3.",
                        "Drawings due tomorrow."}


def test_a_fact_without_a_real_source_is_dropped(conn):
    """A memory nobody can trace back is how an invented fact reaches a customer."""
    applied = memory.apply_changes(conn, 1, [
        {"action": "create", "kind": "profile", "content": "Their CEO is Korean.",
         "evidence": ["inbox:99999"]},
        {"action": "create", "kind": "profile", "content": "No evidence at all.",
         "evidence": []},
    ])
    assert applied["applied"] == 0
    assert applied["rejected"] == 2
    assert memory.items(conn, 1) == []


def test_note_evidence_counts_too(conn):
    memory.apply_changes(conn, 1, [
        {"action": "create", "kind": "profile", "content": "Prefers WhatsApp.",
         "evidence": [f"note:{_note(conn)}"]},
    ])
    assert [item["content"] for item in memory.items(conn, 1)] == ["Prefers WhatsApp."]


def test_allens_own_memory_is_not_the_agents_to_edit(conn):
    """What a person wrote down by hand is usually the part the model cannot see."""
    written = memory.write_explicit(conn, 1, "Owner dislikes being chased. Wait for him.")
    evidence = f"inbox:{_message(conn)}"
    result = memory.apply_changes(conn, 1, [
        {"action": "update", "id": written["id"], "content": "Owner is fine with chasing.",
         "evidence": [evidence]},
        {"action": "remove", "id": written["id"], "evidence": [evidence]},
    ])
    assert result["applied"] == 0 and result["rejected"] == 2
    kept = memory.items(conn, 1)[0]
    assert kept["content"] == "Owner dislikes being chased. Wait for him."
    assert kept["origin"] == "explicit"


def test_a_superseded_fact_leaves_the_summary_but_stays_on_the_record(conn):
    """That a customer changed their mind says more than what they now think."""
    evidence = f"inbox:{_message(conn)}"
    memory.apply_changes(conn, 1, [
        {"action": "create", "kind": "log", "content": "Wants P2.5.", "evidence": [evidence]}])
    item_id = memory.items(conn, 1)[0]["id"]
    later = f"inbox:{_message(conn, body='Actually P3.9 outdoor.')}"
    memory.apply_changes(conn, 1, [
        {"action": "remove", "id": item_id, "evidence": [later]}])
    assert memory.items(conn, 1) == []
    history = memory.items(conn, 1, include_superseded=True)
    assert len(history) == 1 and history[0]["superseded_at"]


def test_summary_stays_the_field_draft_reads(conn):
    """draft.py and /api/agent/leads/{no}/memory read get_memory()['summary']; the
    change of storage underneath must not reach them."""
    evidence = f"inbox:{_message(conn)}"
    memory.apply_changes(conn, 1, [
        {"action": "create", "kind": "profile", "content": "Buys through a distributor.",
         "evidence": [evidence]},
        {"action": "create", "kind": "log", "content": "Budget opens Q3.",
         "evidence": [evidence]},
    ])
    summary = proposals.get_memory(conn, 1)["summary"]
    assert "distributor" in summary and "Q3" in summary


def test_oversized_and_overlong_batches_are_bounded(conn):
    evidence = [f"inbox:{_message(conn)}"]
    changes = [{"action": "create", "kind": "log", "content": f"Fact {i}.",
                "evidence": evidence} for i in range(memory.MAX_CHANGES_PER_SYNTHESIS + 5)]
    result = memory.apply_changes(conn, 1, changes)
    assert result["applied"] == memory.MAX_CHANGES_PER_SYNTHESIS
    long_content = "x" * (memory.MAX_CONTENT_CHARS + 200)
    memory.apply_changes(conn, 2, [
        {"action": "create", "kind": "profile", "content": long_content,
         "evidence": [f"inbox:{_message(conn, lead_no=2)}"]}])
    assert len(memory.items(conn, 2)[0]["content"]) == memory.MAX_CONTENT_CHARS


def test_synthesis_falls_back_to_the_existing_memory_when_the_model_is_down(conn):
    """Memory is a nice-to-have; its absence must never block a reply going out."""
    evidence = f"inbox:{_message(conn)}"
    memory.apply_changes(conn, 1, [
        {"action": "create", "kind": "profile", "content": "Buys through a distributor.",
         "evidence": [evidence]}])

    def explode(*args, **kwargs):
        raise memory.llm.LLMUnavailable("no backend")

    ctx = {"lead": {"no": 1, "company_en": "Alpha AV"}, "opportunities": [], "history": [],
           "message": {"id": 1, "body": "hi", "intent": None}}
    import app.agent.llm as llm_module
    original = llm_module.complete_json
    llm_module.complete_json = explode
    try:
        assert "distributor" in memory.update(conn, ctx)
    finally:
        llm_module.complete_json = original


def test_a_fully_rejected_synthesis_does_not_wipe_what_was_there(conn):
    """Every change failing is exactly when the old memory matters most; rendering an
    empty item set over it would turn a rejected batch into data loss."""
    proposals.set_memory(conn, 1, "Legacy paragraph from before the item store.", 3)
    result = memory.apply_changes(conn, 1, [
        {"action": "create", "kind": "log", "content": "Invented.", "evidence": ["inbox:99999"]}])
    assert result["applied"] == 0
    assert proposals.get_memory(conn, 1)["summary"] == "Legacy paragraph from before the item store."

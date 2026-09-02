"""Changing the copy from the product, and the two things that make it safe (docs/86)."""
import pytest

from app import seed_sequences, sequence_edit


@pytest.fixture
def seq_id(conn):
    conn.execute("UPDATE leads SET hook='Saw the rental work you do around Austin.',"
                 " city='Austin', company_en='Verum AV' WHERE no=1")
    conn.commit()
    return seed_sequences.seed(conn, "测试序列", [
        (0, 0, "rental LED panels", "Hi {contact},\n\n{hook}\n\nP2.6-P4.8 die-cast.\n"),
        (1, 14, "Re: rental LED panels", "Hi {contact},\n\nA cabinet sheet?\n"),
    ])


def test_a_preview_is_a_real_letter_to_a_real_company(conn, seq_id):
    out = sequence_edit.preview(conn, seq_id, 0, "rental LED panels",
                                "Hi {contact},\n\n{hook}\n\nP2.6-P4.8 die-cast.\n")
    assert "{hook}" not in out["body"] and "Austin" in out["body"]
    assert out["blocked"] is False


def test_the_guard_answers_while_the_editor_is_open(conn, seq_id):
    """A step the guard would refuse is refused now, not on the morning it silently
    holds a batch."""
    with pytest.raises(ValueError, match="价格|pricing|退出语|个性化"):
        sequence_edit.update_step(conn, seq_id, 0, subject="quote",
                                  body="Rental P2.6 at USD 1200/sqm.")
    kept = conn.execute("SELECT body FROM sequence_steps WHERE sequence_id=? AND step_order=0",
                        (seq_id,)).fetchone()["body"]
    assert "1200" not in kept, "被拒绝的文案不能落库"


def test_an_edit_is_stored_and_marked(conn, seq_id):
    sequence_edit.update_step(conn, seq_id, 0, subject="rental LED panels",
                              body="Hi {contact},\n\n{hook}\n\nP2.6-P3.9 die-cast.\n")
    row = conn.execute("SELECT body, edited FROM sequence_steps"
                       " WHERE sequence_id=? AND step_order=0", (seq_id,)).fetchone()
    assert "P2.6-P3.9" in row["body"] and row["edited"] == 1
    assert sequence_edit.edited_sequences(conn) == {seq_id}


def test_the_seeder_does_not_overwrite_an_edit(conn, seq_id):
    """The whole reason editing was unsafe before: seed() rewrites every step."""
    sequence_edit.update_step(conn, seq_id, 0, subject="my own subject",
                              body="Hi {contact},\n\n{hook}\n\nMy own words. P2.6.\n")
    seed_sequences.seed(conn, "测试序列", [
        (0, 0, "repo subject", "Hi {contact},\n\n{hook}\n\nrepo words.\n")])
    row = conn.execute("SELECT subject, body FROM sequence_steps"
                       " WHERE sequence_id=? AND step_order=0", (seq_id,)).fetchone()
    assert row["subject"] == "my own subject"
    assert "My own words" in row["body"]


def test_reverting_hands_the_sequence_back(conn, seq_id):
    sequence_edit.update_step(conn, seq_id, 0, subject="mine",
                              body="Hi {contact},\n\n{hook}\n\nMine. P2.6.\n")
    assert sequence_edit.revert(conn, seq_id) >= 1
    seed_sequences.seed(conn, "测试序列", [
        (0, 0, "repo subject", "Hi {contact},\n\n{hook}\n\nrepo words.\n")])
    row = conn.execute("SELECT subject FROM sequence_steps"
                       " WHERE sequence_id=? AND step_order=0", (seq_id,)).fetchone()
    assert row["subject"] == "repo subject"


def test_an_untouched_sequence_is_still_kept_current(conn, seq_id):
    seed_sequences.seed(conn, "测试序列", [
        (0, 0, "new repo subject", "Hi {contact},\n\n{hook}\n\nnew repo words.\n")])
    row = conn.execute("SELECT subject FROM sequence_steps"
                       " WHERE sequence_id=? AND step_order=0", (seq_id,)).fetchone()
    assert row["subject"] == "new repo subject"

"""Legacy Outdoor routing after docs/127.

Historical send records remain untouched. Existing sequence enrollments, however, must
have a path into the surviving Rental / Install / General book when the migration tool
is applied.
"""
from app import merge_sequences, seed_sequences


def _legacy_outdoor_sequence(conn, korean=False):
    seed_sequences.ensure_routing_columns(conn)
    return conn.execute(
        "INSERT INTO sequences(name,channel,active,segment,korean) VALUES (?,?,1,'outdoor',?)",
        (f"legacy outdoor {'ko' if korean else 'en'}", "email", int(korean)),
    ).lastrowid


def test_outdoor_only_customer_moves_to_general(conn):
    targets = seed_sequences.seed_all(conn)
    old = _legacy_outdoor_sequence(conn)
    conn.execute(
        "INSERT INTO leads(no,company_en,country,business) VALUES (7001,'BillboardCo','USA',?)",
        ("digital billboard and facade advertising",),
    )
    conn.execute(
        "INSERT INTO sequence_enrollments(lead_no,sequence_id,current_step,status,enrolled_at)"
        " VALUES (7001,?,0,'active','2026-09-01')", (old,),
    )
    conn.commit()

    moves = [m for m in merge_sequences.plan(conn) if m["lead_no"] == 7001]
    assert len(moves) == 1
    assert moves[0]["segment"] == "general"
    assert moves[0]["to"] == targets[("general", False)]


def test_mixed_rental_and_install_customer_moves_to_general(conn):
    targets = seed_sequences.seed_all(conn)
    old = _legacy_outdoor_sequence(conn)
    conn.execute(
        "INSERT INTO leads(no,company_en,country,business) VALUES (7002,'MixedAV','USA',?)",
        ("event LED rental, staging and permanent AV installation",),
    )
    conn.execute(
        "INSERT INTO sequence_enrollments(lead_no,sequence_id,current_step,status,enrolled_at)"
        " VALUES (7002,?,0,'active','2026-09-01')", (old,),
    )
    conn.commit()

    moves = [m for m in merge_sequences.plan(conn) if m["lead_no"] == 7002]
    assert len(moves) == 1
    assert moves[0]["segment"] == "general"
    assert moves[0]["to"] == targets[("general", False)]

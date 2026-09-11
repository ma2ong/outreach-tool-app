from app import sequence_routing, sequences
from app.agent.executors import _sequence_for


def _sequence(conn, name):
    return sequences.create_sequence(conn, name, "email", [{"day_offset": 0, "body": "hi"}])


def test_database_rule_priority_and_country_choose_sequence(conn):
    default = _sequence(conn, "English rental")
    usa = _sequence(conn, "USA rental")
    sequence_routing.add_rule(conn, default, priority=10, language="en",
                              customer_type="rental")
    sequence_routing.add_rule(conn, usa, priority=20, country="USA", language="en",
                              customer_type="rental")
    lead = {"country": "USA", "tags": "租赁商"}
    assert _sequence_for(conn, lead) == usa


def test_no_segment_match_falls_back_to_language_general(conn):
    general = _sequence(conn, "Korean general")
    sequence_routing.add_rule(conn, general, priority=1, language="ko",
                              customer_type="general")
    assert _sequence_for(conn, {"country": "South Korea", "tags": "租赁商"}) == general


def test_new_declared_route_replaces_same_destination_without_touching_enrollments(conn):
    old = _sequence(conn, "Old")
    new = _sequence(conn, "New")
    sequence_routing.add_rule(conn, old, priority=1, language="en",
                              customer_type="install")
    sequences.enroll_leads(conn, old, [1])
    sequence_routing.replace_declared_route(
        conn, new, customer_type="install", language="en")
    assert _sequence_for(conn, {"country": "USA", "tags": "工程商"}) == new
    row = conn.execute("SELECT sequence_id,status FROM sequence_enrollments WHERE lead_no=1").fetchone()
    assert dict(row) == {"sequence_id": old, "status": "active"}


def test_country_specific_replacement_does_not_disable_global_rule(conn):
    global_sequence = _sequence(conn, "Global")
    usa_sequence = _sequence(conn, "USA")
    sequence_routing.add_rule(conn, global_sequence, priority=10, language="en",
                              customer_type="install")
    sequence_routing.replace_declared_route(
        conn, usa_sequence, customer_type="install", language="en",
        country="USA", priority=20)
    assert _sequence_for(conn, {"country": "USA", "tags": "工程商"}) == usa_sequence
    assert _sequence_for(conn, {"country": "Canada", "tags": "工程商"}) == global_sequence


def test_declared_segment_beats_older_legacy_named_sequence(conn):
    from app.seed_sequences import ensure_routing_columns, name_for
    _sequence(conn, name_for("rental", False))
    declared = _sequence(conn, "Explicit rental assignment")
    ensure_routing_columns(conn)
    conn.execute("UPDATE sequences SET segment='rental',korean=0 WHERE id=?", (declared,))
    conn.commit()
    assert _sequence_for(conn, {"country": "USA", "tags": "租赁商"}) == declared


def test_replacement_seeds_old_declarations_before_disabling_them(conn):
    from app.seed_sequences import ensure_routing_columns
    old = _sequence(conn, "Old rental")
    new = _sequence(conn, "New rental")
    ensure_routing_columns(conn)
    conn.execute("UPDATE sequences SET segment='rental',korean=0 WHERE id=?", (old,))
    conn.commit()
    sequence_routing.replace_declared_route(conn, new, customer_type="rental",
                                           language="en", priority=0)
    assert _sequence_for(conn, {"country": "USA", "tags": "租赁商"}) == new


def test_rule_update_and_explanation_use_real_evaluation_order(conn):
    general = _sequence(conn, "General")
    rental = _sequence(conn, "Rental")
    general_rule = sequence_routing.add_rule(
        conn, general, priority=999, language="en", customer_type="general")
    rental_rule = sequence_routing.add_rule(
        conn, rental, priority=10, country="USA", language="en", customer_type="rental")

    explanation = sequence_routing.explain(
        conn, {"country": "United States", "tags": "租赁商"})
    assert explanation["sequence_id"] == rental
    assert [item["id"] for item in explanation["matches"]] == [rental_rule, general_rule]
    assert explanation["matches"][0]["match_level"] == "customer_type"

    sequence_routing.update_rule(conn, rental_rule, enabled=False, priority=20,
                                 country="USA", language="en", customer_type="rental",
                                 sequence_id=rental)
    assert sequence_routing.route(conn, {"country": "US", "tags": "租赁商"}) == general
    listed = {item["id"]: item for item in sequence_routing.list_rules(conn)}
    assert listed[rental_rule]["enabled"] == 0
    assert listed[rental_rule]["sequence_name"] == "Rental"

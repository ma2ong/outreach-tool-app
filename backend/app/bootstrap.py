"""Database/schema startup work for the web process."""
from __future__ import annotations

from collections.abc import Callable

from app.db import connect, init_schema


def initialize(db_path: str, backup_fn: Callable[[str], object]) -> None:
    from app.dedupe import normalize_all_websites
    from app.opportunities import ensure_schema as ensure_opportunity_schema
    from app.activities import ensure_schema as ensure_activity_schema, migrate_existing
    from app.contacts import ensure_schema as ensure_contact_schema, migrate_existing as migrate_contacts
    from app.sales_documents import ensure_schema as ensure_sales_document_schema
    from app.sales_intelligence import ensure_schema as ensure_sales_intelligence_schema
    from app.decision_maker_radar import ensure_schema as ensure_decision_maker_schema
    from app.runtime import ensure_schema as ensure_runtime_schema
    from app.sequence_routing import ensure_schema as ensure_sequence_routing_schema
    from app.delivery_intents import ensure_schema as ensure_delivery_intent_schema
    from app.copy_versions import ensure_schema as ensure_copy_version_schema
    from app.agent.learn import ensure_lesson_schema
    from app.agent.project_facts import ensure_schema as ensure_project_fact_schema

    backup_fn(db_path)
    conn = connect(db_path)
    try:
        init_schema(conn)
        ensure_contact_schema(conn)
        migrate_contacts(conn)
        ensure_opportunity_schema(conn)
        ensure_sales_document_schema(conn)
        ensure_activity_schema(conn)
        ensure_sales_intelligence_schema(conn)
        ensure_decision_maker_schema(conn)
        ensure_runtime_schema(conn)
        ensure_sequence_routing_schema(conn)
        ensure_delivery_intent_schema(conn)
        ensure_copy_version_schema(conn)
        ensure_lesson_schema(conn)
        ensure_project_fact_schema(conn)
        migrate_existing(conn)
        normalize_all_websites(conn)
        from app.replies import backfill_bounced_at
        backfill_bounced_at(conn)
        from app.agent.proposals import ensure_schema as ensure_agent_schema
        from app.agent.proposals import fail_interrupted
        ensure_agent_schema(conn)
        fail_interrupted(conn)
        if not conn.execute("SELECT 1 FROM sequences LIMIT 1").fetchone():
            from app import seeds
            seeds.seed_templates(conn)
            seeds.seed_sequences(conn)
    finally:
        conn.close()

"""Create the harmless, local-only record needed by browser smoke checks."""
from __future__ import annotations

import os
import json

from app.db import connect, init_schema


def main() -> None:
    path = os.environ["OUTREACH_DB"]
    conn = connect(path)
    try:
        init_schema(conn)
        conn.execute(
            "INSERT OR IGNORE INTO leads(no,company_en,country,email,website) VALUES (1,?,?,?,?)",
            ("CI LED Demo", "USA", "ci@example.invalid", "https://example.invalid"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO inbox_messages(id,lead_no,channel,kind,from_addr,subject,"
            " body,received_at,attachments_json) VALUES (1,1,'email','reply',"
            " 'buyer@example.invalid','Re: demo','Please review the drawing.',"
            " '2026-09-09T08:00:00+08:00',?)",
            (json.dumps([{
                "filename": "CI cabinet drawing.pdf", "content_type": "application/pdf",
                "size": 2048, "sha256": "ci-only-evidence",
            }]),),
        )
        from app import sequence_routing, sequences
        sid = sequences.create_sequence(
            conn, "CI Rental Follow-up", "email",
            [{"day_offset": 0, "subject": "Hello {company}", "body": "Demo only"}],
        )
        sequence_routing.add_rule(
            conn, sid, priority=50, country="USA", language="en", customer_type="rental")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()

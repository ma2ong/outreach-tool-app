import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    no INTEGER PRIMARY KEY,
    company_en TEXT NOT NULL,
    company_local TEXT,
    country TEXT,
    region TEXT,
    city TEXT,
    contact_name TEXT,
    title TEXT,
    email TEXT,
    phone TEXT,
    website TEXT,
    instagram TEXT,
    facebook TEXT,
    linkedin TEXT,
    business TEXT,
    target_fit TEXT,
    brief TEXT,
    hook TEXT,
    email_source TEXT,
    recheck_due TEXT,
    recheck_count INTEGER DEFAULT 0,
    whatsapp_verified INTEGER DEFAULT 0,
    source_urls TEXT,
    stage TEXT DEFAULT 'new',
    tags TEXT,
    follow_up_date TEXT,
    next_action TEXT,
    email_status TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS outreach (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_no INTEGER NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL,
    touch_count INTEGER DEFAULT 0,
    message_sent_date TEXT,
    reply_received INTEGER DEFAULT 0,
    exclude_reason TEXT,
    UNIQUE(lead_no, channel)
);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_no INTEGER NOT NULL,
    created_at TEXT,
    text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    channel TEXT NOT NULL,
    subject TEXT,
    body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sequences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    channel TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS sequence_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence_id INTEGER NOT NULL,
    step_order INTEGER NOT NULL,
    day_offset INTEGER NOT NULL DEFAULT 0,
    subject TEXT,
    body TEXT NOT NULL,
    image TEXT
);
CREATE TABLE IF NOT EXISTS sequence_enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_no INTEGER NOT NULL,
    sequence_id INTEGER NOT NULL,
    current_step INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    enrolled_at TEXT,
    next_due_date TEXT,
    UNIQUE(lead_no, sequence_id)
);
CREATE TABLE IF NOT EXISTS mailboxes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    smtp_host TEXT NOT NULL,
    port INTEGER NOT NULL DEFAULT 465,
    imap_host TEXT,
    imap_port INTEGER NOT NULL DEFAULT 993,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    daily_cap INTEGER NOT NULL DEFAULT 40,
    active INTEGER DEFAULT 1,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS mailbox_sends (
    mailbox_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (mailbox_id, date)
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model TEXT NOT NULL,
    pixel_pitch TEXT,
    brightness TEXT,
    use_case TEXT,
    ref_price_sqm TEXT
);
CREATE TABLE IF NOT EXISTS send_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_no INTEGER NOT NULL,
    channel TEXT NOT NULL,
    campaign TEXT NOT NULL,
    sent_at TEXT
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS lead_blocklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL UNIQUE,
    reason TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS inbox_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_no INTEGER NOT NULL,
    channel TEXT NOT NULL DEFAULT 'email',
    kind TEXT NOT NULL DEFAULT 'reply',
    from_addr TEXT,
    subject TEXT,
    body TEXT,
    received_at TEXT,
    is_read INTEGER DEFAULT 0,
    handled_at TEXT
);
"""

# Created after column migration so indexes on new columns (stage) don't fail on old DBs.
INDEXES = """
CREATE INDEX IF NOT EXISTS idx_leads_country ON leads(country);
CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(stage);
CREATE INDEX IF NOT EXISTS idx_outreach_channel ON outreach(channel, status);
CREATE INDEX IF NOT EXISTS idx_notes_lead ON notes(lead_no);
CREATE INDEX IF NOT EXISTS idx_seq_steps ON sequence_steps(sequence_id, step_order);
CREATE INDEX IF NOT EXISTS idx_enroll_due ON sequence_enrollments(status, next_due_date);
CREATE INDEX IF NOT EXISTS idx_enroll_lead ON sequence_enrollments(lead_no);
CREATE INDEX IF NOT EXISTS idx_send_log_campaign ON send_log(campaign, channel);
CREATE UNIQUE INDEX IF NOT EXISTS idx_inbox_dedup
    ON inbox_messages(lead_no, kind, from_addr, subject, received_at);
CREATE INDEX IF NOT EXISTS idx_inbox_read ON inbox_messages(is_read);
"""

# Additive columns for pre-existing tables (DB created before later upgrades).
_TABLE_COLUMNS = {
    "leads": {
        "stage": "TEXT DEFAULT 'new'",
        "tags": "TEXT",
        "follow_up_date": "TEXT",
        "next_action": "TEXT",
        "email_status": "TEXT",
        "do_not_contact": "INTEGER DEFAULT 0",
        "brief": "TEXT",
        "hook": "TEXT",
        "email_source": "TEXT",
        "recheck_due": "TEXT",
        "recheck_count": "INTEGER DEFAULT 0",
        # When this address hard-bounced. A durable fact, unlike email_status, which
        # a DNS re-verification overwrites — the domain of a bounced address still
        # resolves and still has MX (that is how the bounce reached us), so without
        # this the address is handed straight back to the send path.
        "bounced_at": "TEXT",
    },
    "templates": {
        "lang": "TEXT",
    },
    "mailboxes": {
        "imap_host": "TEXT",
        "imap_port": "INTEGER NOT NULL DEFAULT 993",
        # Send-only mailboxes exist: a domain can be authenticated for sending while
        # its plan withholds IMAP. Polling one is a guaranteed error that would mask
        # the healthy mailboxes' status and keep the whole sync reading 'partial'.
        "imap_enabled": "INTEGER NOT NULL DEFAULT 1",
    },
    "products": {
        # The old product table was built for a quick reference-price card. These extra
        # fields turn user-approved rows into a safe Agent knowledge source without
        # creating a second catalog table. Existing/default rows start unapproved.
        "indoor_outdoor": "TEXT",
        "refresh_rate_hz": "INTEGER",
        "maintenance_access": "TEXT",
        "cabinet_size": "TEXT",
        "control_system": "TEXT",
        "notes": "TEXT",
        "agent_approved": "INTEGER NOT NULL DEFAULT 0",
        # Exact engineering facts used by Solution Engineer. They deliberately stay
        # separate from cabinet_size/pitch text: deterministic layout/resolution/power
        # math must never reverse-engineer an exact value from a marketing label.
        "cabinet_width_mm": "REAL",
        "cabinet_height_mm": "REAL",
        "cabinet_resolution_w": "INTEGER",
        "cabinet_resolution_h": "INTEGER",
        "module_width_mm": "REAL",
        "module_height_mm": "REAL",
        "max_power_w_cabinet": "REAL",
        "avg_power_w_cabinet": "REAL",
    },
    # agent_proposals is created by app.agent.proposals.ensure_schema, but a DB that
    # already has the table predates this column.
    "agent_proposals": {
        "original_payload": "TEXT",
    },
    "inbox_messages": {
        "handled_at": "TEXT",
        "contact_id": "INTEGER",
        # Which of our addresses the customer wrote to. Needed to answer from that same
        # address: replying to a thread from a different mailbox breaks threading and
        # reads as a different company.
        "mailbox_email": "TEXT",
        # Agent intent classification. Kept on the message, not the lead: one customer
        # can ask for a quote today and reject next month, and both stay true of the
        # message that carried them.
        "intent": "TEXT",
        "intent_confidence": "INTEGER",
        # What the customer actually asked for, in their own numbers. Extracted in the
        # same classify call, so Allen sees the requirement without re-reading the mail.
        "intent_needs": "TEXT",
        "intent_at": "TEXT",
        # The real conversation, read by opening the thread (social only). `body` stays
        # the one-line preview because the scan dedupes on it — overwriting it would make
        # every later scan re-insert the same message as new.
        "thread_json": "TEXT",
        "thread_read_at": "TEXT",
    },
}


def connect(path: str) -> sqlite3.Connection:
    # Reply polling, automatic follow-ups and API requests can write concurrently.
    # Waiting is safer than immediately failing a real sales action with
    # "database is locked" while a background task holds the short write lock.
    conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def _migrate_columns(conn: sqlite3.Connection) -> None:
    for table, cols in _TABLE_COLUMNS.items():
        existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        # A table owned by a module's own ensure_schema (agent_proposals) does not exist
        # yet on a fresh DB; ALTER would fail before that module ever runs. Its CREATE
        # already carries the column, so skipping here is correct, not a deferral.
        if not existing:
            continue
        for col, decl in cols.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def init_schema(conn: sqlite3.Connection) -> None:
    # WAL lets readers continue while a background sender/sync commits. The mode is
    # persistent for the DB file; NORMAL keeps the local single-user durability/speed
    # trade-off sensible and daily backups remain the recovery boundary.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.executescript(SCHEMA)
    _migrate_columns(conn)
    conn.executescript(INDEXES)
    conn.commit()
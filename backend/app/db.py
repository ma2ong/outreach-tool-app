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
    is_read INTEGER DEFAULT 0
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
    },
    "templates": {
        "lang": "TEXT",
    },
    "mailboxes": {
        "imap_host": "TEXT",
        "imap_port": "INTEGER NOT NULL DEFAULT 993",
    },
}


def connect(path: str) -> sqlite3.Connection:
    # check_same_thread=False: FastAPI runs a request's dependency and endpoint in
    # different threadpool threads; each request opens/closes its own connection and
    # they never run concurrently, so disabling the per-thread check is safe here.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate_columns(conn: sqlite3.Connection) -> None:
    for table, cols in _TABLE_COLUMNS.items():
        existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        for col, decl in cols.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    _migrate_columns(conn)
    conn.executescript(INDEXES)
    conn.commit()

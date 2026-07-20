"""Shared SQLite data layer for the channel platform.

One partner schema, one database. Replaces the 15 divergent
JSON stores from the sandbox prototypes.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.environ.get("CHANNEL_DB", os.path.join(os.path.dirname(__file__), "..", "data", "channel.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS partners (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'authorized' CHECK(tier IN ('authorized','gold','platinum')),
    region TEXT,
    email TEXT,
    expertise TEXT DEFAULT '[]',          -- JSON array
    annual_revenue REAL DEFAULT 0,
    deals_registered INTEGER DEFAULT 0,
    deals_won INTEGER DEFAULT 0,
    certifications INTEGER DEFAULT 0,
    training_hours REAL DEFAULT 0,
    mdf_allocated REAL DEFAULT 0,
    mdf_used REAL DEFAULT 0,
    portal_logins_30d INTEGER DEFAULT 0,
    days_since_last_deal INTEGER DEFAULT 0,
    joined_at TEXT,
    metadata TEXT DEFAULT '{}',           -- JSON blob for module-specific fields
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS deals (
    id TEXT PRIMARY KEY,
    partner_id TEXT REFERENCES partners(id),
    customer TEXT,
    value REAL DEFAULT 0,
    status TEXT DEFAULT 'registered',     -- registered|won|lost|expired
    deal_type TEXT DEFAULT 'standard',
    registered_at TEXT,
    closed_at TEXT,
    metadata TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS referrals (
    id TEXT PRIMARY KEY,
    sender_partner_id TEXT REFERENCES partners(id),
    receiver_partner_id TEXT REFERENCES partners(id),
    customer TEXT,
    deal_value REAL DEFAULT 0,
    status TEXT DEFAULT 'submitted',      -- submitted|matched|won|lost
    fee_gross REAL,
    fee_net REAL,
    submitted_at TEXT,
    converted_at TEXT,
    metadata TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS incentive_claims (
    id TEXT PRIMARY KEY,
    partner_id TEXT REFERENCES partners(id),
    kind TEXT NOT NULL,                   -- rebate|mdf|spif
    amount REAL NOT NULL,
    status TEXT DEFAULT 'pending',        -- pending|approved|rejected|paid
    program TEXT,
    submitted_at TEXT,
    resolved_at TEXT,
    metadata TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partner_id TEXT REFERENCES partners(id),
    milestone TEXT NOT NULL,
    achieved_days INTEGER NOT NULL,       -- days from partner join to achievement
    recorded_at TEXT,
    UNIQUE(partner_id, milestone)
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partner_id TEXT REFERENCES partners(id),
    kind TEXT NOT NULL,                   -- health|churn_risk|growth|velocity|compliance
    score REAL NOT NULL,
    level TEXT,
    detail TEXT DEFAULT '{}',             -- JSON breakdown
    scored_at TEXT
);
"""


def _now():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@contextmanager
def connect():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_partner(p: dict):
    p = dict(p)
    p.setdefault("joined_at", _now())
    p["updated_at"] = _now()
    if isinstance(p.get("expertise"), list):
        p["expertise"] = json.dumps(p["expertise"])
    cols = ["id", "name", "tier", "region", "email", "expertise", "annual_revenue",
            "deals_registered", "deals_won", "certifications", "training_hours",
            "mdf_allocated", "mdf_used", "portal_logins_30d", "days_since_last_deal",
            "joined_at", "metadata", "updated_at"]
    vals = [p.get(c) for c in cols]
    with connect() as c:
        c.execute(
            f"INSERT INTO partners ({','.join(cols)}) VALUES ({','.join('?' * len(cols))}) "
            f"ON CONFLICT(id) DO UPDATE SET " + ",".join(f"{col}=excluded.{col}" for col in cols[1:]),
            vals,
        )


def get_partner(pid: str) -> dict | None:
    with connect() as c:
        row = c.execute("SELECT * FROM partners WHERE id=?", (pid,)).fetchone()
        return dict(row) if row else None


def list_partners(tier: str | None = None) -> list[dict]:
    with connect() as c:
        if tier:
            rows = c.execute("SELECT * FROM partners WHERE tier=? ORDER BY name", (tier,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM partners ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def record_score(partner_id: str, kind: str, score: float, level: str, detail: dict):
    with connect() as c:
        c.execute(
            "INSERT INTO scores (partner_id, kind, score, level, detail, scored_at) VALUES (?,?,?,?,?,?)",
            (partner_id, kind, score, level, json.dumps(detail), _now()),
        )


def insert(table: str, row: dict):
    row = dict(row)
    for k, v in row.items():
        if isinstance(v, (dict, list)):
            row[k] = json.dumps(v)
    cols = list(row.keys())
    with connect() as c:
        c.execute(
            f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
            [row[k] for k in cols],
        )


def query(sql: str, params=()) -> list[dict]:
    with connect() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]

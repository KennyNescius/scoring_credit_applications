"""
db.py — Persistence layer: immutable decision log + SCD Type 2 scorecard
versioning (ToR "Base requirement": "Application → decision → history chain;
immutable decision log" + "Scorecard versioned (SCD Type 2 or
valid_from/valid_to)").

SQLite, stdlib only. Two tables:
  scorecard_versions — SCD Type 2: a new row per training run, the previous
                        row's valid_to is closed instead of updating in place.
  decisions           — append-only. No UPDATE/DELETE path exists anywhere in
                        this module. Each row freezes the score/PD/decision
                        and the *language-agnostic* factor data (feature key,
                        raw value, baseline, points) at the moment the
                        decision was made -- human-readable text is generated
                        from this frozen data at display time in the current
                        session language, so viewing an old decision in a
                        different UI language doesn't change what was decided.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credit_scoring.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS scorecard_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    model_path TEXT NOT NULL,
    train_auc REAL,
    test_auc REAL,
    test_gini REAL,
    n_train INTEGER,
    description TEXT
);

CREATE TABLE IF NOT EXISTS decisions (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    application_id TEXT NOT NULL,
    applicant_id TEXT,
    scorecard_version_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    pd REAL NOT NULL,
    decision TEXT NOT NULL,
    threshold INTEGER NOT NULL,
    source TEXT NOT NULL,
    factors_json TEXT NOT NULL,
    input_snapshot_json TEXT NOT NULL,
    FOREIGN KEY (scorecard_version_id) REFERENCES scorecard_versions(version_id)
);

CREATE INDEX IF NOT EXISTS idx_decisions_application_id ON decisions(application_id);
CREATE INDEX IF NOT EXISTS idx_decisions_scorecard_version ON decisions(scorecard_version_id);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _now():
    return datetime.now(timezone.utc).isoformat()


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def get_active_scorecard_version(conn=None):
    own = conn is None
    conn = conn or get_conn()
    row = conn.execute(
        "SELECT * FROM scorecard_versions WHERE valid_to IS NULL ORDER BY version_id DESC LIMIT 1"
    ).fetchone()
    if own:
        conn.close()
    return row


def publish_scorecard_version(model_path, train_auc=None, test_auc=None, test_gini=None,
                               n_train=None, description=""):
    """SCD Type 2 write: close the currently-active version (if any) and
    insert a new one. Never UPDATEs an existing version's metrics in place --
    a decision's scorecard_version_id always points at a row whose contents
    never change after being closed, so old decisions stay reproducible."""
    conn = get_conn()
    now = _now()
    current = get_active_scorecard_version(conn)
    if current is not None:
        conn.execute(
            "UPDATE scorecard_versions SET valid_to = ? WHERE version_id = ?",
            (now, current["version_id"]),
        )
    cur = conn.execute(
        """INSERT INTO scorecard_versions
           (created_at, valid_from, valid_to, model_path, train_auc, test_auc, test_gini, n_train, description)
           VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?)""",
        (now, now, model_path, train_auc, test_auc, test_gini, n_train, description),
    )
    conn.commit()
    version_id = cur.lastrowid
    conn.close()
    return version_id


def get_scorecard_version(version_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM scorecard_versions WHERE version_id = ?", (version_id,)
    ).fetchone()
    conn.close()
    return row


def insert_decision(application_id, applicant_id, scorecard_version_id, score, pd_value,
                     decision, threshold, factors, input_snapshot, source):
    """Append-only. `factors` is the language-agnostic list from
    explain_decision() (feature key, raw value, baseline, points, direction)
    -- NOT pre-rendered text, so the log can be displayed in either UI
    language without the stored decision itself ever changing."""
    conn = get_conn()
    conn.execute(
        """INSERT INTO decisions
           (created_at, application_id, applicant_id, scorecard_version_id, score, pd,
            decision, threshold, source, factors_json, input_snapshot_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (_now(), application_id, applicant_id, scorecard_version_id, score, pd_value,
         decision, threshold, source,
         json.dumps(factors, ensure_ascii=False),
         json.dumps(input_snapshot, ensure_ascii=False, default=str)),
    )
    conn.commit()
    conn.close()


def insert_decisions_bulk(rows):
    """Same as insert_decision but batched (used to seed the log for the
    whole dataset once per scorecard version)."""
    conn = get_conn()
    now = _now()
    conn.executemany(
        """INSERT INTO decisions
           (created_at, application_id, applicant_id, scorecard_version_id, score, pd,
            decision, threshold, source, factors_json, input_snapshot_json)
           VALUES (:created_at, :application_id, :applicant_id, :scorecard_version_id, :score, :pd,
                   :decision, :threshold, :source, :factors_json, :input_snapshot_json)""",
        [{**r, "created_at": now} for r in rows],
    )
    conn.commit()
    conn.close()


def get_latest_decision_for_application(application_id):
    """An application_id can have more than one decision (e.g. re-scored
    after a retrain); the log keeps every one, this returns the newest."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM decisions WHERE application_id = ? ORDER BY decision_id DESC LIMIT 1",
        (application_id,),
    ).fetchone()
    conn.close()
    return row


def has_decisions_for_version(scorecard_version_id):
    conn = get_conn()
    n = conn.execute(
        "SELECT COUNT(*) FROM decisions WHERE scorecard_version_id = ?",
        (scorecard_version_id,),
    ).fetchone()[0]
    conn.close()
    return n > 0


def list_latest_decisions(limit=10000):
    """One row per application_id -- its most recent decision. Used for the
    underwriter queue, which shows current status per application rather
    than every historical re-score."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT d.* FROM decisions d
           INNER JOIN (
               SELECT application_id, MAX(decision_id) AS max_id
               FROM decisions GROUP BY application_id
           ) latest ON d.decision_id = latest.max_id
           ORDER BY d.decision_id DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def get_setting(key, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row is not None else default


def set_setting(key, value):
    conn = get_conn()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    conn.commit()
    conn.close()


def list_decisions(scorecard_version_id=None, limit=5000):
    conn = get_conn()
    if scorecard_version_id is not None:
        rows = conn.execute(
            "SELECT * FROM decisions WHERE scorecard_version_id = ? ORDER BY decision_id DESC LIMIT ?",
            (scorecard_version_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM decisions ORDER BY decision_id DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return rows

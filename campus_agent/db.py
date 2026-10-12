from __future__ import annotations
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT, university TEXT NOT NULL, iteration INTEGER NOT NULL, strategy_id INTEGER, data_mode TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'running', started_at TEXT NOT NULL, finished_at TEXT, stats_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS strategies (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, query_template TEXT NOT NULL, source_hint TEXT NOT NULL, version INTEGER NOT NULL, parent_id INTEGER, exploration INTEGER NOT NULL DEFAULT 0, score REAL NOT NULL DEFAULT 0, uses INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, FOREIGN KEY(parent_id) REFERENCES strategies(id));
CREATE TABLE IF NOT EXISTS candidates (id INTEGER PRIMARY KEY AUTOINCREMENT, fingerprint TEXT NOT NULL UNIQUE, full_name TEXT NOT NULL, university TEXT NOT NULL, organization TEXT, role TEXT, email TEXT, data_mode TEXT NOT NULL, first_seen_run_id INTEGER, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(first_seen_run_id) REFERENCES runs(id));
CREATE TABLE IF NOT EXISTS evidence (id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id INTEGER NOT NULL, kind TEXT NOT NULL, source_url TEXT NOT NULL, excerpt TEXT NOT NULL, publication_date TEXT, query_used TEXT, source_type TEXT NOT NULL DEFAULT 'public_web', FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS decisions (id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id INTEGER NOT NULL, run_id INTEGER NOT NULL, status TEXT NOT NULL CHECK(status IN ('APPROVED','NEEDS_REVIEW','REJECTED')), email_score REAL NOT NULL, student_score REAL NOT NULL, role_score REAL NOT NULL, fit_score REAL NOT NULL, duplicate_score REAL NOT NULL, overall_score REAL NOT NULL, reasons_json TEXT NOT NULL, policy_version TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE, FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id INTEGER NOT NULL, decision_id INTEGER NOT NULL, label TEXT NOT NULL, comment TEXT, reviewer TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE, FOREIGN KEY(decision_id) REFERENCES decisions(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS reflections (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL, summary TEXT NOT NULL, lessons_json TEXT NOT NULL, next_actions_json TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER, event_type TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE SET NULL);
CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status);
CREATE INDEX IF NOT EXISTS idx_evidence_candidate ON evidence(candidate_id);
CREATE INDEX IF NOT EXISTS idx_reviews_candidate ON reviews(candidate_id);
"""
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
class Database:
    def __init__(self, path: str | Path = "data/campus_agent.sqlite3") -> None:
        self.path = Path(path)
        self._memory_conn: sqlite3.Connection | None = None
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self._memory_conn = sqlite3.connect(":memory:")
            self._memory_conn.row_factory = sqlite3.Row
            self._memory_conn.execute("PRAGMA foreign_keys = ON")
    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = self._memory_conn
        owns_connection = conn is None
        if conn is None:
            conn = sqlite3.connect(str(self.path)); conn.row_factory = sqlite3.Row; conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn; conn.commit()
        finally:
            if owns_connection:
                conn.close()
    def init(self) -> None:
        with self.connect() as conn: conn.executescript(SCHEMA)
    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        with self.connect() as conn:
            cur = conn.execute(sql, params); return int(cur.lastrowid or 0)
    def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        with self.connect() as conn: return conn.execute(sql, params).fetchone()
    def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self.connect() as conn: return list(conn.execute(sql, params).fetchall())
    def log_event(self, run_id: int | None, event_type: str, payload: dict[str, Any]) -> None:
        self.execute("INSERT INTO events(run_id,event_type,payload_json,created_at) VALUES(?,?,?,?)", (run_id, event_type, json.dumps(payload), utc_now()))

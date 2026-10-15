from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS research_runs (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    finalized_at TEXT,
    stop_reason TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    publisher TEXT,
    published_at TEXT,
    accessed_at TEXT NOT NULL,
    source_type TEXT NOT NULL,
    parent_source_id TEXT REFERENCES sources(id) ON DELETE SET NULL,
    root_source_id TEXT REFERENCES sources(id) ON DELETE SET NULL,
    provenance_status TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_sources_run ON sources(run_id);
CREATE INDEX IF NOT EXISTS idx_sources_root ON sources(root_source_id);

CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    root_source_id TEXT REFERENCES sources(id) ON DELETE SET NULL,
    quote TEXT NOT NULL,
    locator TEXT NOT NULL,
    observed_at TEXT,
    metric TEXT,
    value TEXT,
    unit TEXT,
    market TEXT,
    period_start TEXT,
    period_end TEXT,
    scope TEXT,
    method TEXT,
    source_mode TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_evidence_run ON evidence(run_id);
CREATE INDEX IF NOT EXISTS idx_evidence_source ON evidence(source_id);

CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    target_metric TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    confidence_level TEXT NOT NULL,
    confidence_rationale TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_claims_run ON claims(run_id);

CREATE TABLE IF NOT EXISTS claim_evidence (
    claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    relation TEXT NOT NULL,
    PRIMARY KEY (claim_id, evidence_id, relation)
);

CREATE TABLE IF NOT EXISTS research_issues (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    message TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    related_claim_id TEXT REFERENCES claims(id) ON DELETE SET NULL,
    source_id TEXT REFERENCES sources(id) ON DELETE SET NULL,
    evidence_id TEXT REFERENCES evidence(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_issues_run ON research_issues(run_id);

CREATE TABLE IF NOT EXISTS store_snapshots (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    store TEXT NOT NULL,
    country TEXT NOT NULL,
    chart_type TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    source_mode TEXT NOT NULL,
    source_url TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_store_snapshots_history
    ON store_snapshots(run_id, store, country, chart_type, observed_at);

CREATE TABLE IF NOT EXISTS store_snapshot_items (
    snapshot_id TEXT NOT NULL REFERENCES store_snapshots(id) ON DELETE CASCADE,
    game_id TEXT NOT NULL,
    store_app_id TEXT NOT NULL,
    title TEXT NOT NULL,
    rank INTEGER NOT NULL CHECK (rank > 0),
    genre TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (snapshot_id, game_id)
);

CREATE INDEX IF NOT EXISTS idx_store_snapshot_items_game
    ON store_snapshot_items(game_id, snapshot_id);
"""


class Database:
    """Small SQLite wrapper with foreign keys and explicit transactions."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection: sqlite3.Connection | None = sqlite3.connect(
            self.path, check_same_thread=False
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.executescript(SCHEMA)
        claim_columns = {
            row["name"]
            for row in self._connection.execute("PRAGMA table_info(claims)")
        }
        if "target_metric" not in claim_columns:
            self._connection.execute("ALTER TABLE claims ADD COLUMN target_metric TEXT")
        self._connection.commit()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            if self._connection is None:
                raise RuntimeError("Database is closed")
            yield self._connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connection() as connection:
            try:
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def close(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

"""SQLite stores operational counters and expiry markers, never contract content."""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from threading import RLock
from uuid import UUID


def iso(now: datetime) -> str:
    return now.isoformat()


class MetadataDB:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.lock = RLock()
        with self.connection:
            self.connection.executescript("""
                CREATE TABLE IF NOT EXISTS run_log(
                    id INTEGER PRIMARY KEY, session_id TEXT, stage TEXT, started_at TEXT,
                    duration_ms INTEGER, calls INTEGER, input_tokens INTEGER,
                    output_tokens INTEGER, estimated_cost REAL, error_code TEXT,
                    graph_enabled INTEGER, graph_added_candidates INTEGER, created_at TEXT);
                CREATE TABLE IF NOT EXISTS daily_usage(day TEXT PRIMARY KEY, calls INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS rate_event(ip_hash TEXT NOT NULL, occurred_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS rate_event_window ON rate_event(ip_hash, occurred_at);
                CREATE TABLE IF NOT EXISTS expired_tombstone(
                    session_id TEXT PRIMARY KEY, status TEXT NOT NULL, expired_at TEXT NOT NULL);
            """)

    def close(self) -> None:
        self.connection.close()

    def remaining(self, day: str, quota: int) -> int:
        with self.lock:
            row = self.connection.execute("SELECT calls FROM daily_usage WHERE day=?", (day,)).fetchone()
            return quota - (row[0] if row else 0)

    def increment(self, day: str) -> None:
        with self.lock, self.connection:
            self.connection.execute("INSERT INTO daily_usage(day,calls) VALUES (?,1) "
                                    "ON CONFLICT(day) DO UPDATE SET calls=calls+1", (day,))

    def rate_check(self, key: str, now: datetime, limit: int, window_seconds: int) -> bool:
        cutoff = iso(now - timedelta(seconds=window_seconds))
        with self.lock, self.connection:
            self.connection.execute("DELETE FROM rate_event WHERE occurred_at<=?", (cutoff,))
            count = self.connection.execute(
                "SELECT COUNT(*) FROM rate_event WHERE ip_hash=? AND occurred_at>?",
                (key, cutoff)).fetchone()[0]
            if count >= limit:
                return False
            self.connection.execute("INSERT INTO rate_event VALUES (?,?)", (key, iso(now)))
            return True

    def add_tombstone(self, sid: UUID, now: datetime) -> None:
        with self.lock, self.connection:
            self.connection.execute("INSERT OR REPLACE INTO expired_tombstone VALUES (?,?,?)",
                                    (str(sid), "EXPIRED", iso(now)))

    def tombstone(self, sid: UUID) -> datetime | None:
        with self.lock:
            row = self.connection.execute("SELECT expired_at FROM expired_tombstone WHERE session_id=?",
                                          (str(sid),)).fetchone()
            return datetime.fromisoformat(row[0]) if row else None

    def prune_tombstones(self, cutoff: datetime) -> None:
        with self.lock, self.connection:
            self.connection.execute("DELETE FROM expired_tombstone WHERE expired_at<=?", (iso(cutoff),))


def init_db(path: str) -> MetadataDB:
    return MetadataDB(path)

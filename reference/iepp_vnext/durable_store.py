"""SQLite canonical-head compare-and-swap component for crash/concurrency tests."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from pathlib import Path


@dataclass(frozen=True)
class StoredHead:
    sid: str
    counter: int
    head: bytes
    last_evidence_id: bytes


class SQLiteCanonicalStore:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self.connection = sqlite3.connect(self.path, timeout=10, isolation_level=None, check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS canonical_head (
                sid TEXT PRIMARY KEY, counter INTEGER NOT NULL, head BLOB NOT NULL,
                last_evidence_id BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS accepted_evidence (
                evidence_id BLOB PRIMARY KEY, sid TEXT NOT NULL, counter INTEGER NOT NULL,
                head BLOB NOT NULL
            );
        """)

    def close(self) -> None:
        self.connection.close()

    def enroll(self, sid: str, head: bytes) -> None:
        self.connection.execute("INSERT INTO canonical_head VALUES (?, 0, ?, ?)", (sid, head, bytes(32)))

    def read(self, sid: str) -> StoredHead:
        row = self.connection.execute(
            "SELECT sid, counter, head, last_evidence_id FROM canonical_head WHERE sid = ?", (sid,)).fetchone()
        if row is None:
            raise KeyError(sid)
        return StoredHead(row[0], row[1], row[2], row[3])

    def compare_and_swap(self, sid: str, expected_counter: int, expected_head: bytes,
                         new_counter: int, new_head: bytes, evidence_id: bytes,
                         inject_failure: bool = False) -> tuple[bool, str]:
        connection = self.connection
        try:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT counter, head FROM canonical_head WHERE sid = ?", (sid,)).fetchone()
            if current is None:
                connection.execute("ROLLBACK")
                return False, "UNKNOWN_ENTITY"
            if connection.execute("SELECT 1 FROM accepted_evidence WHERE evidence_id = ?", (evidence_id,)).fetchone():
                connection.execute("ROLLBACK")
                return False, "REPLAY_DETECTED"
            if current[0] != expected_counter or current[1] != expected_head:
                connection.execute("ROLLBACK")
                return False, "CAS_CONFLICT"
            if new_counter != expected_counter + 1:
                connection.execute("ROLLBACK")
                return False, "COUNTER_INVALID"
            connection.execute("INSERT INTO accepted_evidence VALUES (?, ?, ?, ?)",
                               (evidence_id, sid, new_counter, new_head))
            if inject_failure:
                raise RuntimeError("injected-before-head-update")
            changed = connection.execute(
                "UPDATE canonical_head SET counter = ?, head = ?, last_evidence_id = ? "
                "WHERE sid = ? AND counter = ? AND head = ?",
                (new_counter, new_head, evidence_id, sid, expected_counter, expected_head)).rowcount
            if changed != 1:
                connection.execute("ROLLBACK")
                return False, "CAS_CONFLICT"
            connection.execute("COMMIT")
            return True, "COMMITTED"
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            if inject_failure:
                return False, "INJECTED_ROLLBACK"
            raise


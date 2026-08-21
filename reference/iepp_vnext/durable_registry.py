"""Crash-consistent SQLite registry for the IEPP v0.2.1 research profile.

This integrates challenge consumption, evidence uniqueness, canonical-head
advancement, entropy-health recording, and the global audit root in one
SQLite transaction.  It is a single-host research implementation, not a
distributed or production registry.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import sqlite3
import time
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from core import (Checkpoint, PROTOCOL, Challenge, MigrationEvidence, TransitionEvidence,
                  _u64, hash_parts, public_bytes)


SCHEMA_VERSION = 1
GENESIS_ROOT = bytes(32)


class RegistryIntegrityError(RuntimeError):
    """Raised when startup validation cannot establish a safe writable state."""


class InjectedCrash(RuntimeError):
    """Test-only crash at a named transaction boundary."""


class CommitResponseLost(RuntimeError):
    """The commit succeeded but the caller did not receive its normal response."""


@dataclass(frozen=True)
class DurableDecision:
    accepted: bool
    code: str
    entropy_health: str
    granted_evidence_level: str
    accepted_counter: int | None = None
    current_counter: int | None = None


class DurableRegistry:
    """Single-writer SQLite realization of the IEPP v0.2.1 registry state."""

    FAILURE_POINTS = frozenset({
        "after_begin", "after_challenge", "after_evidence", "after_audit",
        "after_head", "after_root", "after_commit",
    })

    def __init__(self, path: str | Path, registry_id: str,
                 checkpoint_key: Ed25519PrivateKey | None = None):
        self.path = str(path)
        self.registry_id = registry_id
        self.checkpoint_key = checkpoint_key or Ed25519PrivateKey.generate()
        try:
            self.connection = sqlite3.connect(
                self.path, timeout=10, isolation_level=None, check_same_thread=False)
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA synchronous=FULL")
            self.connection.execute("PRAGMA foreign_keys=ON")
            self._create_schema()
            self._initialize_or_validate()
        except (sqlite3.DatabaseError, RegistryIntegrityError):
            connection = getattr(self, "connection", None)
            if connection is not None:
                connection.close()
            raise RegistryIntegrityError("registry startup validation failed") from None

    def _create_schema(self) -> None:
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS registry_meta (
                registry_id TEXT PRIMARY KEY,
                sequence INTEGER NOT NULL,
                log_root BLOB NOT NULL,
                schema_version INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS enrollments (
                sid TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                counter INTEGER NOT NULL,
                canonical_head BLOB NOT NULL,
                key_id TEXT NOT NULL,
                public_key BLOB NOT NULL,
                entropy_profile_id TEXT NOT NULL,
                last_entropy_commitment BLOB,
                granted_evidence_level TEXT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS challenges (
                challenge_id BLOB PRIMARY KEY,
                sid TEXT NOT NULL,
                domain TEXT NOT NULL,
                nonce BLOB NOT NULL,
                issued_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                consumed_at INTEGER,
                consumed_by BLOB UNIQUE
            );
            CREATE TABLE IF NOT EXISTS accepted_evidence (
                evidence_id BLOB PRIMARY KEY,
                sid TEXT NOT NULL,
                counter INTEGER NOT NULL,
                previous_head BLOB NOT NULL,
                new_head BLOB NOT NULL,
                challenge_id BLOB NOT NULL UNIQUE,
                entropy_commitment BLOB NOT NULL,
                entropy_health TEXT NOT NULL,
                granted_evidence_level TEXT NOT NULL,
                accepted_at INTEGER NOT NULL,
                UNIQUE (sid, counter),
                FOREIGN KEY (sid) REFERENCES enrollments(sid),
                FOREIGN KEY (challenge_id) REFERENCES challenges(challenge_id)
            );
            CREATE TABLE IF NOT EXISTS audit_events (
                sequence INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,
                sid TEXT NOT NULL,
                counter INTEGER NOT NULL,
                object_id BLOB NOT NULL,
                previous_log_root BLOB NOT NULL,
                log_root BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS accepted_migrations (
                migration_id BLOB PRIMARY KEY,
                sid TEXT NOT NULL,
                counter INTEGER NOT NULL,
                challenge_id BLOB NOT NULL UNIQUE,
                old_key_id TEXT NOT NULL,
                new_key_id TEXT NOT NULL,
                new_public_key BLOB NOT NULL,
                accepted_at INTEGER NOT NULL,
                FOREIGN KEY (sid) REFERENCES enrollments(sid),
                FOREIGN KEY (challenge_id) REFERENCES challenges(challenge_id)
            );
        """)

    def _initialize_or_validate(self) -> None:
        integrity = self.connection.execute("PRAGMA integrity_check").fetchone()
        if integrity != ("ok",):
            raise RegistryIntegrityError("sqlite integrity check failed")
        rows = self.connection.execute(
            "SELECT registry_id, sequence, log_root, schema_version FROM registry_meta").fetchall()
        if not rows:
            # Initialization is allowed only for a truly empty database.  A damaged
            # or partially deleted registry must never silently become genesis.
            occupied = sum(self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                           for table in ("enrollments", "challenges", "accepted_evidence",
                                         "accepted_migrations", "audit_events"))
            if occupied:
                raise RegistryIntegrityError("missing metadata on non-empty registry")
            self.connection.execute("INSERT INTO registry_meta VALUES (?, 0, ?, ?)",
                                    (self.registry_id, GENESIS_ROOT, SCHEMA_VERSION))
            return
        if len(rows) != 1 or rows[0][0] != self.registry_id or rows[0][3] != SCHEMA_VERSION:
            raise RegistryIntegrityError("registry identity or schema mismatch")
        self._verify_links(rows[0][1], rows[0][2])

    def _verify_links(self, sequence: int, stored_root: bytes) -> None:
        previous = GENESIS_ROOT
        events = self.connection.execute(
            "SELECT sequence, kind, sid, counter, object_id, previous_log_root, log_root "
            "FROM audit_events ORDER BY sequence").fetchall()
        for expected_sequence, event in enumerate(events, 1):
            seq, kind, sid, counter, object_id, old_root, root = event
            expected_root = hash_parts(b"IEPP-Audit-v1", previous, _u64(seq), kind.encode(),
                                       sid.encode(), _u64(counter), object_id)
            if seq != expected_sequence or old_root != previous or root != expected_root:
                raise RegistryIntegrityError("audit chain mismatch")
            previous = root
        if sequence != len(events) or stored_root != previous:
            raise RegistryIntegrityError("registry metadata does not match audit tail")
        broken = self.connection.execute("""
            SELECT COUNT(*) FROM accepted_evidence ae
            LEFT JOIN challenges c ON c.challenge_id = ae.challenge_id
            LEFT JOIN audit_events a ON a.object_id = ae.evidence_id
            WHERE c.consumed_by != ae.evidence_id OR c.consumed_at IS NULL OR a.object_id IS NULL
        """).fetchone()[0]
        if broken:
            raise RegistryIntegrityError("accepted evidence has broken challenge/audit links")
        broken_migrations = self.connection.execute("""
            SELECT COUNT(*) FROM accepted_migrations am
            LEFT JOIN challenges c ON c.challenge_id = am.challenge_id
            LEFT JOIN audit_events a ON a.object_id = am.migration_id
            WHERE c.consumed_by != am.migration_id OR c.consumed_at IS NULL OR a.object_id IS NULL
        """).fetchone()[0]
        orphan_consumption = self.connection.execute("""
            SELECT COUNT(*) FROM challenges c
            LEFT JOIN accepted_evidence ae ON ae.evidence_id = c.consumed_by
            LEFT JOIN accepted_migrations am ON am.migration_id = c.consumed_by
            WHERE c.consumed_at IS NOT NULL AND ae.evidence_id IS NULL AND am.migration_id IS NULL
        """).fetchone()[0]
        if broken_migrations or orphan_consumption:
            raise RegistryIntegrityError("challenge/migration links are inconsistent")
        for sid, counter, head in self.connection.execute(
                "SELECT sid, counter, canonical_head FROM enrollments WHERE counter > 0"):
            row = self.connection.execute(
                "SELECT new_head FROM accepted_evidence WHERE sid = ? AND counter = ?", (sid, counter)).fetchone()
            if row is None or row[0] != head:
                raise RegistryIntegrityError("canonical head lacks matching evidence")

    def close(self) -> None:
        self.connection.close()

    def enroll(self, sid: str, domain: str, initial_state: bytes, key_id: str,
               key: Ed25519PublicKey, entropy_profile_id: str,
               granted_evidence_level: str = "L1") -> None:
        self.connection.execute(
            "INSERT INTO enrollments VALUES (?, ?, 0, ?, ?, ?, ?, NULL, ?, 'ACTIVE')",
            (sid, domain, initial_state, key_id, public_bytes(key), entropy_profile_id,
             granted_evidence_level))

    def issue_challenge(self, sid: str, domain: str, now: int | None = None, ttl: int = 30,
                        nonce: bytes | None = None) -> Challenge:
        import os
        now = int(time.time()) if now is None else now
        nonce = os.urandom(32) if nonce is None else nonce
        challenge_id = hash_parts(b"IEPP-Challenge-ID-v1", nonce, sid.encode(), domain.encode(), _u64(now))
        challenge = Challenge(challenge_id, nonce, sid, domain, now, now + ttl)
        self.connection.execute("INSERT INTO challenges VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)",
                                (challenge_id, sid, domain, nonce, now, now + ttl))
        return challenge

    @staticmethod
    def _inject(point: str, requested: str | None) -> None:
        if requested == point:
            raise InjectedCrash(point)

    def verify_and_advance(self, evidence: TransitionEvidence, now: int | None = None,
                           inject_failure: str | None = None) -> DurableDecision:
        if inject_failure is not None and inject_failure not in self.FAILURE_POINTS:
            raise ValueError("unknown failure point")
        now = int(time.time()) if now is None else now
        evidence_id = evidence.evidence_id()
        connection = self.connection
        committed = False
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._inject("after_begin", inject_failure)
            prior = connection.execute(
                "SELECT counter, entropy_health, granted_evidence_level FROM accepted_evidence "
                "WHERE evidence_id = ?", (evidence_id,)).fetchone()
            if prior is not None:
                current = connection.execute(
                    "SELECT counter FROM enrollments WHERE sid = ?", (evidence.sid,)).fetchone()
                connection.execute("ROLLBACK")
                return DurableDecision(False, "ALREADY_COMMITTED", prior[1], prior[2],
                                       prior[0], None if current is None else current[0])
            enrollment = connection.execute(
                "SELECT domain, counter, canonical_head, key_id, public_key, entropy_profile_id, "
                "last_entropy_commitment, granted_evidence_level, status FROM enrollments WHERE sid = ?",
                (evidence.sid,)).fetchone()
            if enrollment is None:
                return self._reject("UNKNOWN_ENTITY")
            domain, counter, head, key_id, key_bytes, entropy_profile, last_entropy, level, status = enrollment
            if status != "ACTIVE":
                return self._reject("ENTITY_NOT_ACTIVE")
            if evidence.protocol != PROTOCOL or evidence.domain != domain:
                return self._reject("DOMAIN_OR_PROTOCOL_MISMATCH")
            if evidence.key_id != key_id:
                return self._reject("KEY_ID_MISMATCH")
            try:
                Ed25519PublicKey.from_public_bytes(key_bytes).verify(
                    evidence.signature, evidence.unsigned_body())
            except (InvalidSignature, ValueError):
                return self._reject("SIGNATURE_INVALID")
            challenge = connection.execute(
                "SELECT sid, domain, nonce, expires_at, consumed_at FROM challenges WHERE challenge_id = ?",
                (evidence.challenge_id,)).fetchone()
            if challenge is None:
                return self._reject("CHALLENGE_UNKNOWN")
            if challenge[4] is not None:
                return self._reject("REPLAY_DETECTED")
            if (challenge[0], challenge[1], challenge[2], challenge[3]) != (
                    evidence.sid, evidence.domain, evidence.challenge_nonce, evidence.challenge_expires_at):
                return self._reject("CHALLENGE_BINDING_INVALID")
            if now > challenge[3]:
                return self._reject("CHALLENGE_EXPIRED")
            if evidence.counter <= counter:
                return self._reject("ROLLBACK_OR_LOSING_FORK")
            if evidence.counter != counter + 1:
                return self._reject("COUNTER_GAP")
            if evidence.previous != head:
                return self._reject("STALE_CANONICAL_STATE")
            if evidence.entropy_source != entropy_profile:
                return self._reject("ENTROPY_SOURCE_NOT_ALLOWED", "SUBSTITUTED")
            if evidence.entropy_commitment == last_entropy:
                return self._reject("ENTROPY_REPEATED", "REPEATED")
            expected_state = hash_parts(
                b"IEPP-State-vNext-1", evidence.sid.encode(), evidence.domain.encode(),
                _u64(evidence.counter), evidence.previous, evidence.challenge_id,
                evidence.challenge_nonce, evidence.entropy_commitment, evidence.entropy_source.encode(),
                evidence.runtime_commitment, evidence.attestation_commitment)
            if expected_state != evidence.state:
                return self._reject("STATE_TRANSITION_INVALID")

            changed = connection.execute(
                "UPDATE challenges SET consumed_at = ?, consumed_by = ? "
                "WHERE challenge_id = ? AND consumed_at IS NULL",
                (now, evidence_id, evidence.challenge_id)).rowcount
            if changed != 1:
                return self._reject("CHALLENGE_RACE_LOST")
            self._inject("after_challenge", inject_failure)
            connection.execute(
                "INSERT INTO accepted_evidence VALUES (?, ?, ?, ?, ?, ?, ?, 'OK', ?, ?)",
                (evidence_id, evidence.sid, evidence.counter, evidence.previous, evidence.state,
                 evidence.challenge_id, evidence.entropy_commitment, level, now))
            self._inject("after_evidence", inject_failure)
            sequence, old_root = connection.execute(
                "SELECT sequence, log_root FROM registry_meta WHERE registry_id = ?",
                (self.registry_id,)).fetchone()
            sequence += 1
            root = hash_parts(b"IEPP-Audit-v1", old_root, _u64(sequence), b"TRANSITION_ACCEPTED",
                              evidence.sid.encode(), _u64(evidence.counter), evidence_id)
            connection.execute("INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (sequence, "TRANSITION_ACCEPTED", evidence.sid, evidence.counter,
                                evidence_id, old_root, root))
            self._inject("after_audit", inject_failure)
            changed = connection.execute(
                "UPDATE enrollments SET counter = ?, canonical_head = ?, last_entropy_commitment = ?, "
                "granted_evidence_level = ? WHERE sid = ? AND counter = ? AND canonical_head = ?",
                (evidence.counter, evidence.state, evidence.entropy_commitment, level,
                 evidence.sid, counter, head)).rowcount
            if changed != 1:
                return self._reject("CAS_CONFLICT")
            self._inject("after_head", inject_failure)
            connection.execute(
                "UPDATE registry_meta SET sequence = ?, log_root = ? WHERE registry_id = ?",
                (sequence, root, self.registry_id))
            self._inject("after_root", inject_failure)
            connection.execute("COMMIT")
            committed = True
            self._inject("after_commit", inject_failure)
            return DurableDecision(True, "CONTINUITY_VALID", "OK", level,
                                   evidence.counter, evidence.counter)
        except InjectedCrash as error:
            if not committed and connection.in_transaction:
                connection.execute("ROLLBACK")
            if committed:
                raise CommitResponseLost(str(error)) from error
            raise
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise

    def _reject(self, code: str, entropy_health: str = "UNKNOWN") -> DurableDecision:
        if self.connection.in_transaction:
            self.connection.execute("ROLLBACK")
        return DurableDecision(False, code, entropy_health, "NONE")

    def state(self, sid: str) -> tuple[int, bytes, bytes | None, str]:
        row = self.connection.execute(
            "SELECT counter, canonical_head, last_entropy_commitment, granted_evidence_level "
            "FROM enrollments WHERE sid = ?", (sid,)).fetchone()
        if row is None:
            raise KeyError(sid)
        return row

    def migrate_key(self, migration: MigrationEvidence, now: int | None = None) -> DurableDecision:
        """Atomically consume a migration challenge, change the key, and append audit state."""
        now = int(time.time()) if now is None else now
        migration_id = hash_parts(b"IEPP-Migration-ID-v1", migration.unsigned_body(),
                                  migration.old_signature, migration.new_signature)
        connection = self.connection
        try:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute(
                "SELECT counter FROM accepted_migrations WHERE migration_id = ?", (migration_id,)).fetchone()
            if prior is not None:
                current = connection.execute(
                    "SELECT counter FROM enrollments WHERE sid = ?", (migration.sid,)).fetchone()
                connection.execute("ROLLBACK")
                return DurableDecision(False, "ALREADY_COMMITTED", "NOT_APPLICABLE", "L1",
                                       prior[0], None if current is None else current[0])
            enrollment = connection.execute(
                "SELECT domain, counter, canonical_head, key_id, public_key, granted_evidence_level, status "
                "FROM enrollments WHERE sid = ?", (migration.sid,)).fetchone()
            if enrollment is None:
                return self._reject("UNKNOWN_ENTITY")
            domain, counter, head, old_key_id, old_key, level, status = enrollment
            if status != "ACTIVE":
                return self._reject("ENTITY_NOT_ACTIVE")
            if migration.domain != domain or migration.counter != counter:
                return self._reject("MIGRATION_CONTEXT_INVALID")
            if migration.canonical_head != head or migration.old_key_id != old_key_id:
                return self._reject("MIGRATION_NOT_FROM_CANONICAL_HEAD")
            if migration.new_key_id == old_key_id:
                return self._reject("MIGRATION_KEY_ID_REUSED")
            challenge = connection.execute(
                "SELECT sid, domain, nonce, expires_at, consumed_at FROM challenges WHERE challenge_id = ?",
                (migration.challenge_id,)).fetchone()
            if challenge is None:
                return self._reject("CHALLENGE_UNKNOWN")
            if challenge[4] is not None:
                return self._reject("REPLAY_DETECTED")
            if (challenge[0], challenge[1], challenge[2], challenge[3]) != (
                    migration.sid, migration.domain, migration.challenge_nonce,
                    migration.challenge_expires_at):
                return self._reject("CHALLENGE_BINDING_INVALID")
            if now > challenge[3]:
                return self._reject("CHALLENGE_EXPIRED")
            try:
                Ed25519PublicKey.from_public_bytes(old_key).verify(
                    migration.old_signature, migration.unsigned_body())
                new_public = Ed25519PublicKey.from_public_bytes(migration.new_public_key)
                new_public.verify(migration.new_signature, migration.unsigned_body())
            except (InvalidSignature, ValueError):
                return self._reject("MIGRATION_SIGNATURE_INVALID")
            changed = connection.execute(
                "UPDATE challenges SET consumed_at = ?, consumed_by = ? "
                "WHERE challenge_id = ? AND consumed_at IS NULL",
                (now, migration_id, migration.challenge_id)).rowcount
            if changed != 1:
                return self._reject("CHALLENGE_RACE_LOST")
            connection.execute(
                "INSERT INTO accepted_migrations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (migration_id, migration.sid, counter, migration.challenge_id, old_key_id,
                 migration.new_key_id, migration.new_public_key, now))
            sequence, old_root = connection.execute(
                "SELECT sequence, log_root FROM registry_meta WHERE registry_id = ?",
                (self.registry_id,)).fetchone()
            sequence += 1
            root = hash_parts(b"IEPP-Audit-v1", old_root, _u64(sequence), b"KEY_MIGRATED",
                              migration.sid.encode(), _u64(counter), migration_id)
            connection.execute("INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (sequence, "KEY_MIGRATED", migration.sid, counter,
                                migration_id, old_root, root))
            changed = connection.execute(
                "UPDATE enrollments SET key_id = ?, public_key = ? WHERE sid = ? AND key_id = ?",
                (migration.new_key_id, public_bytes(new_public), migration.sid, old_key_id)).rowcount
            if changed != 1:
                return self._reject("CAS_CONFLICT")
            connection.execute(
                "UPDATE registry_meta SET sequence = ?, log_root = ? WHERE registry_id = ?",
                (sequence, root, self.registry_id))
            connection.execute("COMMIT")
            return DurableDecision(True, "KEY_MIGRATION_VALID", "NOT_APPLICABLE", level,
                                   counter, counter)
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise

    def checkpoint(self, sid: str) -> Checkpoint:
        sequence, root = self.connection.execute(
            "SELECT sequence, log_root FROM registry_meta WHERE registry_id = ?", (self.registry_id,)).fetchone()
        counter, head = self.connection.execute(
            "SELECT counter, canonical_head FROM enrollments WHERE sid = ?", (sid,)).fetchone()
        checkpoint = Checkpoint(self.registry_id, sequence, sid, counter, head, root, b"")
        return replace(checkpoint, signature=self.checkpoint_key.sign(checkpoint.body()))

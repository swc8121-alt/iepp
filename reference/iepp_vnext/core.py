"""IEPP vNext private reference core."""

from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import os
import threading
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


PROTOCOL = "IEPP-vNext-Research-1"


def hash_parts(tag: bytes, *parts: bytes) -> bytes:
    digest = sha256()
    digest.update(len(tag).to_bytes(4, "big"))
    digest.update(tag)
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.digest()


def public_bytes(key: Ed25519PublicKey) -> bytes:
    return key.public_bytes(Encoding.Raw, PublicFormat.Raw)


def _u64(value: int) -> bytes:
    return value.to_bytes(8, "big", signed=False)


@dataclass(frozen=True)
class Challenge:
    challenge_id: bytes
    nonce: bytes
    sid: str
    domain: str
    issued_at: int
    expires_at: int

    def body(self) -> bytes:
        return hash_parts(b"IEPP-Challenge-v1", self.nonce, self.sid.encode(), self.domain.encode(),
                          _u64(self.issued_at), _u64(self.expires_at))


@dataclass(frozen=True)
class TransitionEvidence:
    protocol: str
    sid: str
    domain: str
    counter: int
    previous: bytes
    state: bytes
    challenge_id: bytes
    challenge_nonce: bytes
    challenge_expires_at: int
    entropy_commitment: bytes
    entropy_source: str
    runtime_commitment: bytes
    attestation_commitment: bytes
    key_id: str
    signature: bytes

    def unsigned_body(self) -> bytes:
        return hash_parts(
            b"IEPP-Evidence-vNext-1", self.protocol.encode(), self.sid.encode(), self.domain.encode(),
            _u64(self.counter), self.previous, self.state, self.challenge_id, self.challenge_nonce,
            _u64(self.challenge_expires_at), self.entropy_commitment, self.entropy_source.encode(),
            self.runtime_commitment, self.attestation_commitment, self.key_id.encode())

    def evidence_id(self) -> bytes:
        return hash_parts(b"IEPP-Evidence-ID-v1", self.unsigned_body(), self.signature)


@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    kind: str
    sid: str
    counter: int
    evidence_id: bytes
    previous_log_root: bytes
    log_root: bytes


@dataclass(frozen=True)
class Checkpoint:
    registry_id: str
    sequence: int
    sid: str
    counter: int
    canonical_head: bytes
    log_root: bytes
    signature: bytes

    def body(self) -> bytes:
        return hash_parts(b"IEPP-Checkpoint-v1", self.registry_id.encode(), _u64(self.sequence),
                          self.sid.encode(), _u64(self.counter), self.canonical_head, self.log_root)


@dataclass(frozen=True)
class MigrationEvidence:
    sid: str
    domain: str
    counter: int
    canonical_head: bytes
    old_key_id: str
    new_key_id: str
    new_public_key: bytes
    challenge_id: bytes
    challenge_nonce: bytes
    challenge_expires_at: int
    old_signature: bytes
    new_signature: bytes

    def unsigned_body(self) -> bytes:
        return hash_parts(b"IEPP-Key-Migration-v1", self.sid.encode(), self.domain.encode(),
                          _u64(self.counter), self.canonical_head, self.old_key_id.encode(),
                          self.new_key_id.encode(), self.new_public_key, self.challenge_id,
                          self.challenge_nonce, _u64(self.challenge_expires_at))


@dataclass
class Enrollment:
    sid: str
    domain: str
    counter: int
    canonical_head: bytes
    key_id: str
    public_key: Ed25519PublicKey
    allowed_entropy_sources: frozenset[str]
    last_entropy_commitment: bytes | None = None


class ChallengeAuthority:
    def __init__(self):
        self._records: dict[bytes, tuple[Challenge, bool]] = {}
        self._lock = threading.Lock()

    def issue(self, sid: str, domain: str, now: int | None = None, ttl: int = 30,
              nonce: bytes | None = None) -> Challenge:
        now = int(time.time()) if now is None else now
        nonce = os.urandom(32) if nonce is None else nonce
        challenge_id = hash_parts(b"IEPP-Challenge-ID-v1", nonce, sid.encode(), domain.encode(), _u64(now))
        challenge = Challenge(challenge_id, nonce, sid, domain, now, now + ttl)
        with self._lock:
            if challenge_id in self._records:
                raise ValueError("challenge-id-collision")
            self._records[challenge_id] = (challenge, False)
        return challenge

    def inspect(self, challenge_id: bytes) -> tuple[Challenge, bool] | None:
        with self._lock:
            return self._records.get(challenge_id)

    def consume(self, challenge_id: bytes) -> bool:
        with self._lock:
            record = self._records.get(challenge_id)
            if record is None or record[1]:
                return False
            self._records[challenge_id] = (record[0], True)
            return True


class Prover:
    def __init__(self, sid: str, domain: str, key_id: str, private_key: Ed25519PrivateKey,
                 initial_state: bytes, counter: int = 0):
        self.sid, self.domain, self.key_id = sid, domain, key_id
        self.private_key, self.state, self.counter = private_key, initial_state, counter

    def clone(self) -> "Prover":
        return Prover(self.sid, self.domain, self.key_id, self.private_key, self.state, self.counter)

    def transition(self, challenge: Challenge, entropy: bytes, entropy_source: str,
                   runtime_commitment: bytes, attestation: bytes = b"") -> TransitionEvidence:
        counter = self.counter + 1
        entropy_commitment = hash_parts(b"IEPP-Entropy-v1", entropy)
        attestation_commitment = hash_parts(b"IEPP-Attestation-v1", attestation)
        state = hash_parts(
            b"IEPP-State-vNext-1", self.sid.encode(), self.domain.encode(), _u64(counter), self.state,
            challenge.challenge_id, challenge.nonce, entropy_commitment, entropy_source.encode(),
            runtime_commitment, attestation_commitment)
        evidence = TransitionEvidence(
            PROTOCOL, self.sid, self.domain, counter, self.state, state, challenge.challenge_id,
            challenge.nonce, challenge.expires_at, entropy_commitment, entropy_source,
            runtime_commitment, attestation_commitment, self.key_id, b"")
        evidence = replace(evidence, signature=self.private_key.sign(evidence.unsigned_body()))
        self.state, self.counter = state, counter
        return evidence


class AtomicRegistry:
    def __init__(self, registry_id: str, challenge_authority: ChallengeAuthority,
                 checkpoint_key: Ed25519PrivateKey | None = None):
        self.registry_id = registry_id
        self.challenges = challenge_authority
        self.checkpoint_key = checkpoint_key or Ed25519PrivateKey.generate()
        self.enrollments: dict[str, Enrollment] = {}
        self.seen_evidence: set[bytes] = set()
        self.audit: list[AuditEvent] = []
        self.log_root = bytes(32)
        self._lock = threading.Lock()

    def enroll(self, sid: str, domain: str, initial_state: bytes, key_id: str,
               key: Ed25519PublicKey, allowed_entropy_sources: set[str]) -> None:
        with self._lock:
            if sid in self.enrollments:
                raise ValueError("already-enrolled")
            self.enrollments[sid] = Enrollment(sid, domain, 0, initial_state, key_id, key,
                                               frozenset(allowed_entropy_sources))

    def _append(self, kind: str, enrollment: Enrollment, evidence_id: bytes) -> None:
        sequence = len(self.audit) + 1
        root = hash_parts(b"IEPP-Audit-v1", self.log_root, _u64(sequence), kind.encode(),
                          enrollment.sid.encode(), _u64(enrollment.counter), evidence_id)
        self.audit.append(AuditEvent(sequence, kind, enrollment.sid, enrollment.counter,
                                     evidence_id, self.log_root, root))
        self.log_root = root

    def verify_and_advance(self, evidence: TransitionEvidence, now: int | None = None) -> tuple[bool, str]:
        now = int(time.time()) if now is None else now
        with self._lock:
            enrollment = self.enrollments.get(evidence.sid)
            if enrollment is None:
                return False, "UNKNOWN_ENTITY"
            if evidence.protocol != PROTOCOL or evidence.domain != enrollment.domain:
                return False, "DOMAIN_OR_PROTOCOL_MISMATCH"
            if evidence.key_id != enrollment.key_id:
                return False, "KEY_ID_MISMATCH"
            try:
                enrollment.public_key.verify(evidence.signature, evidence.unsigned_body())
            except InvalidSignature:
                return False, "SIGNATURE_INVALID"
            evidence_id = evidence.evidence_id()
            if evidence_id in self.seen_evidence:
                return False, "REPLAY_DETECTED"
            challenge_record = self.challenges.inspect(evidence.challenge_id)
            if challenge_record is None:
                return False, "CHALLENGE_UNKNOWN"
            challenge, used = challenge_record
            if used:
                return False, "CHALLENGE_USED"
            if challenge.sid != evidence.sid or challenge.domain != evidence.domain:
                return False, "CHALLENGE_BINDING_INVALID"
            if challenge.nonce != evidence.challenge_nonce or challenge.expires_at != evidence.challenge_expires_at:
                return False, "CHALLENGE_SUBSTITUTED"
            if now > challenge.expires_at:
                return False, "CHALLENGE_EXPIRED"
            if evidence.counter <= enrollment.counter:
                return False, "ROLLBACK_OR_LOSING_FORK"
            if evidence.counter != enrollment.counter + 1:
                return False, "COUNTER_GAP"
            if evidence.previous != enrollment.canonical_head:
                return False, "STALE_CANONICAL_STATE"
            if evidence.entropy_source not in enrollment.allowed_entropy_sources:
                return False, "ENTROPY_SOURCE_NOT_ALLOWED"
            if evidence.entropy_commitment == enrollment.last_entropy_commitment:
                return False, "ENTROPY_REPEATED"
            expected_state = hash_parts(
                b"IEPP-State-vNext-1", evidence.sid.encode(), evidence.domain.encode(), _u64(evidence.counter),
                evidence.previous, evidence.challenge_id, evidence.challenge_nonce, evidence.entropy_commitment,
                evidence.entropy_source.encode(), evidence.runtime_commitment, evidence.attestation_commitment)
            if expected_state != evidence.state:
                return False, "STATE_TRANSITION_INVALID"
            if not self.challenges.consume(evidence.challenge_id):
                return False, "CHALLENGE_RACE_LOST"
            enrollment.counter = evidence.counter
            enrollment.canonical_head = evidence.state
            enrollment.last_entropy_commitment = evidence.entropy_commitment
            self.seen_evidence.add(evidence_id)
            self._append("TRANSITION_ACCEPTED", enrollment, evidence_id)
            return True, "CONTINUITY_VALID"

    def checkpoint(self, sid: str) -> Checkpoint:
        with self._lock:
            enrollment = self.enrollments[sid]
            checkpoint = Checkpoint(self.registry_id, len(self.audit), sid, enrollment.counter,
                                    enrollment.canonical_head, self.log_root, b"")
            return replace(checkpoint, signature=self.checkpoint_key.sign(checkpoint.body()))

    def migrate_key(self, migration: MigrationEvidence, now: int | None = None) -> tuple[bool, str]:
        now = int(time.time()) if now is None else now
        with self._lock:
            enrollment = self.enrollments.get(migration.sid)
            if enrollment is None:
                return False, "UNKNOWN_ENTITY"
            if migration.domain != enrollment.domain or migration.counter != enrollment.counter:
                return False, "MIGRATION_CONTEXT_INVALID"
            if migration.canonical_head != enrollment.canonical_head or migration.old_key_id != enrollment.key_id:
                return False, "MIGRATION_NOT_FROM_CANONICAL_HEAD"
            if migration.new_key_id == migration.old_key_id:
                return False, "MIGRATION_KEY_ID_REUSED"
            challenge_record = self.challenges.inspect(migration.challenge_id)
            if challenge_record is None:
                return False, "CHALLENGE_UNKNOWN"
            challenge, used = challenge_record
            if used:
                return False, "CHALLENGE_USED"
            if (challenge.sid, challenge.domain, challenge.nonce, challenge.expires_at) != (
                    migration.sid, migration.domain, migration.challenge_nonce, migration.challenge_expires_at):
                return False, "CHALLENGE_BINDING_INVALID"
            if now > challenge.expires_at:
                return False, "CHALLENGE_EXPIRED"
            try:
                enrollment.public_key.verify(migration.old_signature, migration.unsigned_body())
                new_public = Ed25519PublicKey.from_public_bytes(migration.new_public_key)
                new_public.verify(migration.new_signature, migration.unsigned_body())
            except (InvalidSignature, ValueError):
                return False, "MIGRATION_SIGNATURE_INVALID"
            if not self.challenges.consume(migration.challenge_id):
                return False, "CHALLENGE_RACE_LOST"
            migration_id = hash_parts(b"IEPP-Migration-ID-v1", migration.unsigned_body(),
                                      migration.old_signature, migration.new_signature)
            enrollment.key_id = migration.new_key_id
            enrollment.public_key = new_public
            self._append("KEY_MIGRATED", enrollment, migration_id)
            return True, "KEY_MIGRATION_VALID"

    def verify_audit_chain(self) -> bool:
        previous = bytes(32)
        for event in self.audit:
            expected = hash_parts(b"IEPP-Audit-v1", previous, _u64(event.sequence), event.kind.encode(),
                                  event.sid.encode(), _u64(event.counter), event.evidence_id)
            if event.previous_log_root != previous or event.log_root != expected:
                return False
            previous = expected
        return previous == self.log_root


def checkpoints_conflict(left: Checkpoint, right: Checkpoint) -> bool:
    """Detect a split view when two checkpoints claim the same registry/sequence/entity."""
    comparable = (left.registry_id, left.sequence, left.sid, left.counter) == (
        right.registry_id, right.sequence, right.sid, right.counter)
    return comparable and (left.canonical_head != right.canonical_head or left.log_root != right.log_root)


def verify_checkpoint(checkpoint: Checkpoint, public_key: Ed25519PublicKey) -> bool:
    try:
        public_key.verify(checkpoint.signature, checkpoint.body())
        return True
    except InvalidSignature:
        return False


def create_migration(prover: Prover, challenge: Challenge, new_key_id: str,
                     new_private_key: Ed25519PrivateKey) -> MigrationEvidence:
    migration = MigrationEvidence(prover.sid, prover.domain, prover.counter, prover.state, prover.key_id,
                                  new_key_id, public_bytes(new_private_key.public_key()), challenge.challenge_id,
                                  challenge.nonce, challenge.expires_at, b"", b"")
    body = migration.unsigned_body()
    return replace(migration, old_signature=prover.private_key.sign(body),
                   new_signature=new_private_key.sign(body))

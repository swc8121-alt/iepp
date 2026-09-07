"""Network-facing A3 registry logic for signed same-credential fork trials.

The engine intentionally implements a narrow L1 boundary: one configured entity,
one online registry, authenticated transitions, fresh in-memory challenges, and a
durable SQLite compare-and-swap canonical head. It is not a production service.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import threading
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from core import Challenge, ChallengeAuthority, PROTOCOL, TransitionEvidence, hash_parts
from durable_store import SQLiteCanonicalStore


HASH_BYTES = 32
SIGNATURE_BYTES = 64


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def challenge_to_dict(challenge: Challenge) -> dict:
    return {
        "challenge_id": challenge.challenge_id.hex(),
        "nonce": challenge.nonce.hex(),
        "sid": challenge.sid,
        "domain": challenge.domain,
        "issued_at": challenge.issued_at,
        "expires_at": challenge.expires_at,
    }


def challenge_from_dict(value: dict) -> Challenge:
    return Challenge(
        bytes.fromhex(value["challenge_id"]),
        bytes.fromhex(value["nonce"]),
        str(value["sid"]),
        str(value["domain"]),
        int(value["issued_at"]),
        int(value["expires_at"]),
    )


def evidence_to_dict(evidence: TransitionEvidence) -> dict:
    return {
        "protocol": evidence.protocol,
        "sid": evidence.sid,
        "domain": evidence.domain,
        "counter": evidence.counter,
        "previous": evidence.previous.hex(),
        "state": evidence.state.hex(),
        "challenge_id": evidence.challenge_id.hex(),
        "challenge_nonce": evidence.challenge_nonce.hex(),
        "challenge_expires_at": evidence.challenge_expires_at,
        "entropy_commitment": evidence.entropy_commitment.hex(),
        "entropy_source": evidence.entropy_source,
        "runtime_commitment": evidence.runtime_commitment.hex(),
        "attestation_commitment": evidence.attestation_commitment.hex(),
        "key_id": evidence.key_id,
        "signature": evidence.signature.hex(),
        "evidence_id": evidence.evidence_id().hex(),
    }


def evidence_from_dict(value: dict) -> TransitionEvidence:
    evidence = TransitionEvidence(
        str(value["protocol"]),
        str(value["sid"]),
        str(value["domain"]),
        int(value["counter"]),
        bytes.fromhex(value["previous"]),
        bytes.fromhex(value["state"]),
        bytes.fromhex(value["challenge_id"]),
        bytes.fromhex(value["challenge_nonce"]),
        int(value["challenge_expires_at"]),
        bytes.fromhex(value["entropy_commitment"]),
        str(value["entropy_source"]),
        bytes.fromhex(value["runtime_commitment"]),
        bytes.fromhex(value["attestation_commitment"]),
        str(value["key_id"]),
        bytes.fromhex(value["signature"]),
    )
    fixed_hash_fields = (
        evidence.previous,
        evidence.state,
        evidence.challenge_id,
        evidence.challenge_nonce,
        evidence.entropy_commitment,
        evidence.runtime_commitment,
        evidence.attestation_commitment,
    )
    if any(len(field) != HASH_BYTES for field in fixed_hash_fields):
        raise ValueError("invalid-hash-field-length")
    if len(evidence.signature) != SIGNATURE_BYTES:
        raise ValueError("invalid-signature-length")
    if not 0 <= evidence.counter < 2 ** 64:
        raise ValueError("counter-out-of-range")
    if not 0 <= evidence.challenge_expires_at < 2 ** 64:
        raise ValueError("challenge-expiry-out-of-range")
    claimed_id = value.get("evidence_id")
    if claimed_id is not None and claimed_id != evidence.evidence_id().hex():
        raise ValueError("evidence-id-mismatch")
    return evidence


@dataclass(frozen=True)
class A3Enrollment:
    sid: str
    domain: str
    key_id: str
    public_key: Ed25519PublicKey
    initial_state: bytes
    allowed_entropy_sources: frozenset[str]

    @classmethod
    def load(cls, path: str | Path) -> "A3Enrollment":
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if value.get("schema") != "iepp-a3-enrollment-v2":
            raise ValueError("unsupported-enrollment-schema")
        initial_state = bytes.fromhex(value["initial_state"])
        public_key_bytes = bytes.fromhex(value["public_key"])
        if len(initial_state) != HASH_BYTES or len(public_key_bytes) != HASH_BYTES:
            raise ValueError("invalid-enrollment-field-length")
        return cls(
            str(value["sid"]),
            str(value["domain"]),
            str(value["key_id"]),
            Ed25519PublicKey.from_public_bytes(public_key_bytes),
            initial_state,
            frozenset(str(item) for item in value["allowed_entropy_sources"]),
        )


class A3RegistryEngine:
    """Verify signed transitions and atomically select one canonical successor."""

    def __init__(self, database: str | Path, enrollment_path: str | Path,
                 event_log: str | Path | None = None):
        self.enrollment = A3Enrollment.load(enrollment_path)
        self.store = SQLiteCanonicalStore(database)
        self.challenges = ChallengeAuthority()
        self.event_log = Path(event_log) if event_log else None
        self._lock = threading.Lock()
        self._event_lock = threading.Lock()
        try:
            stored = self.store.read(self.enrollment.sid)
        except KeyError:
            self.store.enroll(self.enrollment.sid, self.enrollment.initial_state)
        else:
            if stored.counter == 0 and stored.head != self.enrollment.initial_state:
                raise ValueError("database-enrollment-mismatch")

    def close(self) -> None:
        self.store.close()

    def health(self) -> dict:
        with self._lock:
            head = self.store.read(self.enrollment.sid)
        return {
            "ok": True,
            "schema": "iepp-a3-registry-health-v2",
            "sid": head.sid,
            "counter": head.counter,
            "canonical_head": head.head.hex(),
            "claim_scope": "L1 single online registry",
        }

    def issue_challenge(self, sid: str, domain: str, ttl: int = 30) -> tuple[int, dict]:
        if sid != self.enrollment.sid or domain != self.enrollment.domain:
            return 404, {"ok": False, "reason": "UNKNOWN_ENTITY_OR_DOMAIN"}
        if ttl < 1 or ttl > 3600:
            return 400, {"ok": False, "reason": "TTL_OUT_OF_RANGE"}
        challenge = self.challenges.issue(sid, domain, ttl=ttl)
        response = {"ok": True, "challenge": challenge_to_dict(challenge)}
        self._append_event("CHALLENGE_ISSUED", response)
        return 200, response

    def head(self, sid: str) -> tuple[int, dict]:
        if sid != self.enrollment.sid:
            return 404, {"ok": False, "reason": "UNKNOWN_ENTITY"}
        with self._lock:
            stored = self.store.read(sid)
        return 200, {
            "ok": True,
            "sid": stored.sid,
            "counter": stored.counter,
            "canonical_head": stored.head.hex(),
            "last_evidence_id": stored.last_evidence_id.hex(),
        }

    def verify_and_advance(self, value: dict, now: int | None = None) -> tuple[int, dict]:
        now = int(time.time()) if now is None else now
        try:
            evidence = evidence_from_dict(value)
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            return 400, {"ok": False, "accepted": False, "reason": "MALFORMED_EVIDENCE",
                         "detail": str(error)}

        with self._lock:
            before = self.store.read(self.enrollment.sid)
            reason = self._validate(evidence, before.counter, before.head, now)
            if reason is not None:
                response = self._decision(False, reason, evidence, before.head, before.head)
                self._append_event("TRANSITION_REJECTED", response)
                return 200, response

            ok, cas_reason = self.store.compare_and_swap(
                evidence.sid,
                before.counter,
                before.head,
                evidence.counter,
                evidence.state,
                evidence.evidence_id(),
            )
            if not ok:
                after = self.store.read(self.enrollment.sid)
                response = self._decision(False, cas_reason, evidence, before.head, after.head)
                self._append_event("TRANSITION_REJECTED", response)
                return 200, response
            if not self.challenges.consume(evidence.challenge_id):
                raise RuntimeError("challenge-consume-failed-after-commit")
            after = self.store.read(self.enrollment.sid)
            response = self._decision(True, "CONTINUITY_VALID", evidence, before.head, after.head)
            self._append_event("TRANSITION_ACCEPTED", response)
            return 200, response

    def _validate(self, evidence: TransitionEvidence, current_counter: int,
                  current_head: bytes, now: int) -> str | None:
        enrollment = self.enrollment
        if evidence.sid != enrollment.sid:
            return "UNKNOWN_ENTITY"
        if evidence.protocol != PROTOCOL or evidence.domain != enrollment.domain:
            return "DOMAIN_OR_PROTOCOL_MISMATCH"
        if evidence.key_id != enrollment.key_id:
            return "KEY_ID_MISMATCH"
        try:
            enrollment.public_key.verify(evidence.signature, evidence.unsigned_body())
        except InvalidSignature:
            return "SIGNATURE_INVALID"
        evidence_id = evidence.evidence_id()
        if self.store.contains_evidence(evidence_id):
            return "REPLAY_DETECTED"
        challenge_record = self.challenges.inspect(evidence.challenge_id)
        if challenge_record is None:
            return "CHALLENGE_UNKNOWN"
        challenge, used = challenge_record
        if used:
            return "CHALLENGE_USED"
        if challenge.sid != evidence.sid or challenge.domain != evidence.domain:
            return "CHALLENGE_BINDING_INVALID"
        if (challenge.nonce != evidence.challenge_nonce or
                challenge.expires_at != evidence.challenge_expires_at):
            return "CHALLENGE_SUBSTITUTED"
        if now > challenge.expires_at:
            return "CHALLENGE_EXPIRED"
        if evidence.counter <= current_counter:
            return "ROLLBACK_OR_LOSING_FORK"
        if evidence.counter != current_counter + 1:
            return "COUNTER_GAP"
        if evidence.previous != current_head:
            return "STALE_CANONICAL_STATE"
        if evidence.entropy_source not in enrollment.allowed_entropy_sources:
            return "ENTROPY_SOURCE_NOT_ALLOWED"
        expected_state = hash_parts(
            b"IEPP-State-vNext-1",
            evidence.sid.encode(),
            evidence.domain.encode(),
            evidence.counter.to_bytes(8, "big", signed=False),
            evidence.previous,
            evidence.challenge_id,
            evidence.challenge_nonce,
            evidence.entropy_commitment,
            evidence.entropy_source.encode(),
            evidence.runtime_commitment,
            evidence.attestation_commitment,
        )
        if expected_state != evidence.state:
            return "STATE_TRANSITION_INVALID"
        return None

    @staticmethod
    def _decision(accepted: bool, reason: str, evidence: TransitionEvidence,
                  before: bytes, after: bytes) -> dict:
        return {
            "ok": True,
            "schema": "iepp-a3-registry-decision-v2",
            "accepted": accepted,
            "reason": reason,
            "sid": evidence.sid,
            "counter": evidence.counter,
            "evidence_id": evidence.evidence_id().hex(),
            "presented_predecessor": evidence.previous.hex(),
            "candidate_successor": evidence.state.hex(),
            "canonical_head_before": before.hex(),
            "canonical_head_after": after.hex(),
            "decided_at_utc": utc_now(),
        }

    def _append_event(self, event: str, payload: dict) -> None:
        if self.event_log is None:
            return
        record = {"event": event, "recorded_at_utc": utc_now(), **payload}
        with self._event_lock:
            self.event_log.parent.mkdir(parents=True, exist_ok=True)
            with self.event_log.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")

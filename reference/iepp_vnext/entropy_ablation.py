"""Ablation: canonical continuation with the entropy fields removed.

This is an experimental comparison variant, not an IEPP wire profile.  It keeps
the registered key, one-time challenge, predecessor, counter, signature, and
atomic registry update while omitting entropy_commitment and entropy_source.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from hashlib import sha256
import json
from pathlib import Path
import threading

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core import ChallengeAuthority, hash_parts


def _u64(value: int) -> bytes:
    return value.to_bytes(8, "big", signed=False)


@dataclass(frozen=True)
class Evidence:
    sid: str
    domain: str
    counter: int
    previous: bytes
    state: bytes
    challenge_id: bytes
    challenge_nonce: bytes
    challenge_expires_at: int
    key_id: str
    signature: bytes

    def unsigned_body(self) -> bytes:
        return hash_parts(
            b"IEPP-Ablation-NoEntropy-Evidence-v1",
            self.sid.encode(), self.domain.encode(), _u64(self.counter),
            self.previous, self.state, self.challenge_id, self.challenge_nonce,
            _u64(self.challenge_expires_at), self.key_id.encode(),
        )


class Prover:
    def __init__(self, key: Ed25519PrivateKey, state: bytes, counter: int = 0):
        self.key, self.state, self.counter = key, state, counter

    def clone(self) -> "Prover":
        return Prover(self.key, self.state, self.counter)

    def transition(self, challenge) -> Evidence:
        counter = self.counter + 1
        state = hash_parts(
            b"IEPP-Ablation-NoEntropy-State-v1", b"entity", b"domain",
            _u64(counter), self.state, challenge.challenge_id, challenge.nonce,
        )
        evidence = Evidence(
            "entity", "domain", counter, self.state, state,
            challenge.challenge_id, challenge.nonce, challenge.expires_at,
            "key", b"",
        )
        evidence = replace(evidence, signature=self.key.sign(evidence.unsigned_body()))
        self.state, self.counter = state, counter
        return evidence


class Registry:
    def __init__(self, authority: ChallengeAuthority, key: Ed25519PrivateKey, initial: bytes):
        self.authority, self.public_key = authority, key.public_key()
        self.counter, self.head = 0, initial
        self.seen: set[bytes] = set()
        self.lock = threading.Lock()

    def verify_and_advance(self, evidence: Evidence, now: int) -> bool:
        with self.lock:
            try:
                self.public_key.verify(evidence.signature, evidence.unsigned_body())
            except InvalidSignature:
                return False
            evidence_id = sha256(evidence.unsigned_body() + evidence.signature).digest()
            record = self.authority.inspect(evidence.challenge_id)
            if evidence_id in self.seen or record is None:
                return False
            challenge, used = record
            if used or now > challenge.expires_at:
                return False
            if (challenge.sid, challenge.domain, challenge.nonce, challenge.expires_at) != (
                evidence.sid, evidence.domain, evidence.challenge_nonce, evidence.challenge_expires_at
            ):
                return False
            if evidence.counter != self.counter + 1 or evidence.previous != self.head:
                return False
            expected = hash_parts(
                b"IEPP-Ablation-NoEntropy-State-v1", evidence.sid.encode(),
                evidence.domain.encode(), _u64(evidence.counter), evidence.previous,
                evidence.challenge_id, evidence.challenge_nonce,
            )
            if evidence.state != expected or not self.authority.consume(evidence.challenge_id):
                return False
            self.counter, self.head = evidence.counter, evidence.state
            self.seen.add(evidence_id)
            return True


def run(replay_trials: int = 10_000, fork_races: int = 1_000) -> dict:
    replay_false_accepts = 0
    for trial in range(replay_trials):
        key, initial, authority = Ed25519PrivateKey.generate(), sha256(b"initial").digest(), ChallengeAuthority()
        prover = Prover(key, initial)
        registry = Registry(authority, key, initial)
        challenge = authority.issue("entity", "domain", now=trial, ttl=5,
                                    nonce=sha256(f"r-{trial}".encode()).digest())
        evidence = prover.transition(challenge)
        assert registry.verify_and_advance(evidence, trial)
        replay_false_accepts += int(registry.verify_and_advance(evidence, trial))

    double_accepts = 0
    for trial in range(fork_races):
        key, initial, authority = Ed25519PrivateKey.generate(), sha256(b"initial").digest(), ChallengeAuthority()
        first, second = Prover(key, initial), Prover(key, initial)
        registry = Registry(authority, key, initial)
        c1 = authority.issue("entity", "domain", now=trial, ttl=5,
                             nonce=sha256(f"f1-{trial}".encode()).digest())
        c2 = authority.issue("entity", "domain", now=trial, ttl=5,
                             nonce=sha256(f"f2-{trial}".encode()).digest())
        accepted = sum((registry.verify_and_advance(first.transition(c1), trial),
                        registry.verify_and_advance(second.transition(c2), trial)))
        double_accepts += int(accepted > 1)

    return {
        "schema": "iepp-entropy-ablation-v1",
        "variant": "no-entropy-fields",
        "retained_controls": ["registered-key", "one-time-challenge", "predecessor",
                              "monotonic-counter", "signature", "atomic-head-update"],
        "replay_trials": replay_trials,
        "replay_false_accepts": replay_false_accepts,
        "fork_races": fork_races,
        "double_accepts": double_accepts,
        "claim": "Entropy fields are not the mechanism that serializes canonical successors.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-trials", type=int, default=10_000)
    parser.add_argument("--fork-races", type=int, default=1_000)
    parser.add_argument("--output", type=Path, default=Path("results/entropy_ablation_v1.json"))
    args = parser.parse_args()
    result = run(args.replay_trials, args.fork_races)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))

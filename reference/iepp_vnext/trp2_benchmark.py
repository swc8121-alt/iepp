"""TRP 2.0 executable security-game benchmark.

This is a dependency-free model test for the security properties in
``docs/TRP_2_Security_Model_v0.1.md``.  It intentionally models canonical
registry acceptance rather than claiming that random-looking output proves
identity.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import secrets
from typing import Dict, Tuple


def H(*parts: bytes) -> bytes:
    h = hashlib.sha256()
    for part in parts:
        h.update(len(part).to_bytes(4, "big"))
        h.update(part)
    return h.digest()


@dataclass(frozen=True)
class Challenge:
    cid: bytes
    nonce: bytes


@dataclass(frozen=True)
class Evidence:
    counter: int
    predecessor: bytes
    successor: bytes
    challenge_id: bytes
    challenge_nonce: bytes
    entropy_commitment: bytes
    tag: bytes


class Registry:
    def __init__(self, key: bytes):
        self.key = key
        self.counter = 0
        self.head = H(b"genesis")
        self.challenges: Dict[bytes, Tuple[bytes, bool]] = {}

    def challenge(self) -> Challenge:
        cid, nonce = secrets.token_bytes(16), secrets.token_bytes(32)
        self.challenges[cid] = (nonce, False)
        return Challenge(cid, nonce)

    def accept(self, ev: Evidence) -> bool:
        entry = self.challenges.get(ev.challenge_id)
        if entry is None or entry[1] or entry[0] != ev.challenge_nonce:
            return False
        if ev.counter != self.counter + 1 or ev.predecessor != self.head:
            return False
        body = encode_body(ev)
        if not hmac.compare_digest(hmac.new(self.key, body, hashlib.sha256).digest(), ev.tag):
            return False
        expected = transition(ev.predecessor, ev.counter, ev.challenge_id,
                              ev.challenge_nonce, ev.entropy_commitment)
        if not hmac.compare_digest(expected, ev.successor):
            return False
        self.challenges[ev.challenge_id] = (entry[0], True)
        self.counter, self.head = ev.counter, ev.successor
        return True


def transition(pred: bytes, counter: int, cid: bytes, nonce: bytes, ec: bytes) -> bytes:
    return H(b"IEPP-TRP2", pred, counter.to_bytes(8, "big"), cid, nonce, ec)


def encode_body(ev: Evidence) -> bytes:
    return H(b"evidence", ev.counter.to_bytes(8, "big"), ev.predecessor,
             ev.successor, ev.challenge_id, ev.challenge_nonce,
             ev.entropy_commitment)


def prove(key: bytes, counter: int, pred: bytes, challenge: Challenge,
          entropy: bytes | None = None) -> Evidence:
    entropy = entropy if entropy is not None else secrets.token_bytes(32)
    ec = H(b"entropy", entropy)
    succ = transition(pred, counter, challenge.cid, challenge.nonce, ec)
    unsigned = Evidence(counter, pred, succ, challenge.cid, challenge.nonce, ec, b"")
    tag = hmac.new(key, encode_body(unsigned), hashlib.sha256).digest()
    return Evidence(counter, pred, succ, challenge.cid, challenge.nonce, ec, tag)


def run(trials: int = 1000) -> dict:
    replay_accept = rollback_accept = forged_accept = dual_accept = 0
    key_state_race_accept = 0

    for _ in range(trials):
        key = secrets.token_bytes(32)
        reg = Registry(key)

        # Establish one legitimate canonical transition.
        c1 = reg.challenge()
        first = prove(key, 1, reg.head, c1)
        assert reg.accept(first)

        # A0 replay: consumed challenge/evidence must fail.
        replay_accept += int(reg.accept(first))

        # A1/A2 stale predecessor rollback with otherwise authentic evidence.
        c2 = reg.challenge()
        stale = prove(key, 2, H(b"genesis"), c2)
        rollback_accept += int(reg.accept(stale))

        # Observer/software clone without signing authority cannot forge.
        c3 = reg.challenge()
        fake_key = secrets.token_bytes(32)
        forged = prove(fake_key, 2, reg.head, c3)
        forged_accept += int(reg.accept(forged))

        # Snapshot-style fork: two authentic successors race from one head.
        pred, ctr = reg.head, reg.counter + 1
        ca, cb = reg.challenge(), reg.challenge()
        a = prove(key, ctr, pred, ca)
        b = prove(key, ctr, pred, cb)
        accepted_a = reg.accept(a)
        accepted_b = reg.accept(b)
        dual_accept += int(accepted_a and accepted_b)

        # A5 boundary control: key+current-state compromise can win a race.
        # Use a fresh registry so the attacker races from the actual current head.
        boundary = Registry(key)
        seed_c = boundary.challenge()
        assert boundary.accept(prove(key, 1, boundary.head, seed_c))
        attack_c = boundary.challenge()
        attacker = prove(key, 2, boundary.head, attack_c)
        key_state_race_accept += int(boundary.accept(attacker))

    return {
        "trials": trials,
        "replay_accept_rate": replay_accept / trials,
        "rollback_accept_rate": rollback_accept / trials,
        "unsigned_or_wrong_key_forgery_accept_rate": forged_accept / trials,
        "dual_canonical_accept_rate": dual_accept / trials,
        "key_plus_state_boundary_accept_rate": key_state_race_accept / trials,
        "expected": {
            "replay_accept_rate": 0.0,
            "rollback_accept_rate": 0.0,
            "unsigned_or_wrong_key_forgery_accept_rate": 0.0,
            "dual_canonical_accept_rate": 0.0,
            "key_plus_state_boundary_accept_rate": 1.0,
        },
    }


def assert_expected(result: dict) -> None:
    for metric, expected in result["expected"].items():
        actual = result[metric]
        if actual != expected:
            raise AssertionError(f"{metric}: expected {expected}, got {actual}")


if __name__ == "__main__":
    result = run()
    assert_expected(result)
    for key, value in result.items():
        if key != "expected":
            print(f"{key}: {value}")

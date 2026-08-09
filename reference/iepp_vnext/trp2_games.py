"""Deterministic TRP 2.0 security-game harness for the IEPP reference model.

This module tests protocol invariants; it does not claim a proof of TRP hardness.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import os
from typing import Dict, Tuple


def _h(*parts: bytes) -> bytes:
    h = hashlib.sha256()
    for p in parts:
        h.update(len(p).to_bytes(4, "big"))
        h.update(p)
    return h.digest()


@dataclass(frozen=True)
class Evidence:
    entity: str
    counter: int
    predecessor: bytes
    challenge: bytes
    entropy_commitment: bytes
    state: bytes
    tag: bytes


class MiniCLR:
    """Minimal atomic single-successor model used only for TRP game tests."""

    def __init__(self, entity: str = "agent-1", key: bytes | None = None):
        self.entity = entity
        self.key = key or os.urandom(32)
        self.head = _h(b"genesis", entity.encode())
        self.counter = 0
        self.used_challenges: set[bytes] = set()
        self.used_evidence: set[bytes] = set()

    def issue_challenge(self, nonce: bytes | None = None) -> bytes:
        return _h(b"challenge", self.entity.encode(), nonce or os.urandom(32))

    def make_evidence(self, challenge: bytes, entropy: bytes | None = None,
                      predecessor: bytes | None = None, counter: int | None = None) -> Evidence:
        pred = self.head if predecessor is None else predecessor
        ctr = self.counter + 1 if counter is None else counter
        ec = _h(b"entropy", entropy or os.urandom(32))
        state = _h(b"TRP2", self.entity.encode(), ctr.to_bytes(8, "big"), pred, challenge, ec)
        body = _h(self.entity.encode(), ctr.to_bytes(8, "big"), pred, challenge, ec, state)
        tag = hmac.new(self.key, body, hashlib.sha256).digest()
        return Evidence(self.entity, ctr, pred, challenge, ec, state, tag)

    def accept(self, ev: Evidence) -> Tuple[bool, str]:
        body = _h(ev.entity.encode(), ev.counter.to_bytes(8, "big"), ev.predecessor,
                  ev.challenge, ev.entropy_commitment, ev.state)
        expected_tag = hmac.new(self.key, body, hashlib.sha256).digest()
        evidence_id = _h(body, ev.tag)
        if ev.entity != self.entity or not hmac.compare_digest(expected_tag, ev.tag):
            return False, "AUTH_INVALID"
        if ev.challenge in self.used_challenges or evidence_id in self.used_evidence:
            return False, "REPLAY_DETECTED"
        if ev.counter != self.counter + 1 or ev.predecessor != self.head:
            return False, "STALE_CANONICAL_STATE"
        expected_state = _h(b"TRP2", ev.entity.encode(), ev.counter.to_bytes(8, "big"),
                            ev.predecessor, ev.challenge, ev.entropy_commitment)
        if not hmac.compare_digest(expected_state, ev.state):
            return False, "STATE_INVALID"
        self.head, self.counter = ev.state, ev.counter
        self.used_challenges.add(ev.challenge)
        self.used_evidence.add(evidence_id)
        return True, "CONTINUITY_VALID"


def run_games() -> Dict[str, bool]:
    results: Dict[str, bool] = {}

    # Positive continuation.
    r = MiniCLR(key=b"k" * 32)
    c1 = r.issue_challenge(b"c1")
    e1 = r.make_evidence(c1, b"e1")
    results["continuation"] = r.accept(e1)[0]

    # Replay must fail.
    results["replay_rejected"] = not r.accept(e1)[0]

    # Rollback/stale predecessor must fail after advancement.
    old_head, old_counter = e1.predecessor, 0
    c2 = r.issue_challenge(b"c2")
    stale = r.make_evidence(c2, b"e2", predecessor=old_head, counter=old_counter + 1)
    results["rollback_rejected"] = not r.accept(stale)[0]

    # Same-head fork race: exactly one winner.
    f = MiniCLR(key=b"f" * 32)
    base = f.head
    ca, cb = f.issue_challenge(b"a"), f.issue_challenge(b"b")
    a = f.make_evidence(ca, b"ea", predecessor=base, counter=1)
    b = f.make_evidence(cb, b"eb", predecessor=base, counter=1)
    wa, wb = f.accept(a)[0], f.accept(b)[0]
    results["fork_exactly_one_winner"] = (int(wa) + int(wb) == 1)

    # Challenge substitution without re-authentication must fail.
    s = MiniCLR(key=b"s" * 32)
    cs = s.issue_challenge(b"orig")
    es = s.make_evidence(cs, b"entropy")
    substituted = Evidence(es.entity, es.counter, es.predecessor, s.issue_challenge(b"evil"),
                           es.entropy_commitment, es.state, es.tag)
    results["challenge_substitution_rejected"] = not s.accept(substituted)[0]

    # Unauthorized migration analogue: evidence signed with another key fails.
    victim = MiniCLR(key=b"v" * 32)
    attacker = MiniCLR(entity=victim.entity, key=b"a" * 32)
    attacker.head, attacker.counter = victim.head, victim.counter
    cm = victim.issue_challenge(b"migration")
    forged = attacker.make_evidence(cm, b"m")
    results["unauthorized_key_rejected"] = not victim.accept(forged)[0]

    return results


def main() -> int:
    results = run_games()
    for name, passed in results.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())

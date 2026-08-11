import json
from hashlib import sha256
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core import AtomicRegistry, ChallengeAuthority, Prover


def make_system():
    sid, domain = "vector-entity", "trp2.vectors"
    key = Ed25519PrivateKey.generate()
    initial = sha256(b"vector-initial").digest()
    authority = ChallengeAuthority()
    registry = AtomicRegistry("vector-registry", authority)
    registry.enroll(sid, domain, initial, "key-1", key.public_key(), {"test.entropy"})
    return Prover(sid, domain, "key-1", key, initial), registry, authority


def execute(attack):
    prover, registry, authority = make_system()

    if attack == "exact_replay":
        challenge = authority.issue(prover.sid, prover.domain, now=1, ttl=10)
        evidence = prover.transition(challenge, b"e1", "test.entropy", b"runtime")
        assert registry.verify_and_advance(evidence, 2)[0]
        return "reject" if not registry.verify_and_advance(evidence, 2)[0] else "accept"

    if attack == "wrong_key_forgery":
        wrong = Prover(
            prover.sid,
            prover.domain,
            prover.key_id,
            Ed25519PrivateKey.generate(),
            prover.state,
        )
        challenge = authority.issue(prover.sid, prover.domain, now=1, ttl=10)
        evidence = wrong.transition(challenge, b"e1", "test.entropy", b"runtime")
        return "reject" if not registry.verify_and_advance(evidence, 2)[0] else "accept"

    if attack == "stale_predecessor":
        stale = prover.clone()
        first = authority.issue(prover.sid, prover.domain, now=1, ttl=10)
        assert registry.verify_and_advance(
            prover.transition(first, b"e1", "test.entropy", b"runtime"), 2
        )[0]
        challenge = authority.issue(prover.sid, prover.domain, now=2, ttl=10)
        evidence = stale.transition(challenge, b"e2", "test.entropy", b"runtime")
        return "reject" if not registry.verify_and_advance(evidence, 3)[0] else "accept"

    if attack == "fork_race":
        left, right = prover.clone(), prover.clone()
        left_challenge = authority.issue(prover.sid, prover.domain, now=1, ttl=10)
        right_challenge = authority.issue(prover.sid, prover.domain, now=1, ttl=10)
        results = [
            registry.verify_and_advance(
                left.transition(left_challenge, b"left", "test.entropy", b"runtime"), 2
            )[0],
            registry.verify_and_advance(
                right.transition(right_challenge, b"right", "test.entropy", b"runtime"), 2
            )[0],
        ]
        return "at_most_one_canonical" if sum(map(int, results)) <= 1 else "dual_accept"

    if attack == "key_plus_state_race":
        attacker = prover.clone()
        challenge = authority.issue(prover.sid, prover.domain, now=1, ttl=10)
        accepted = registry.verify_and_advance(
            attacker.transition(challenge, b"attacker", "test.entropy", b"runtime"), 2
        )[0]
        return "boundary_success_possible_at_L1" if accepted else "reject"

    raise AssertionError(f"unimplemented vector attack: {attack}")


class TRP2VectorTests(unittest.TestCase):
    def test_baseline_vectors_execute_against_real_core(self):
        data = json.loads(Path("trp2_vectors.json").read_text(encoding="utf-8"))
        self.assertEqual(data["trp_version"], "2.0-v0.1")
        ids = {vector["id"] for vector in data["vectors"]}
        self.assertTrue({"T01", "T03", "T04", "T05", "T10"}.issubset(ids))
        for vector in data["vectors"]:
            with self.subTest(vector=vector["id"]):
                self.assertIn(vector["profile"], {f"A{i}" for i in range(7)})
                self.assertEqual(execute(vector["attack"]), vector["expected"])


if __name__ == "__main__":
    unittest.main()

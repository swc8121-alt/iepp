from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import sys
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import (AtomicRegistry, ChallengeAuthority, PROTOCOL, Prover, create_migration,
                  checkpoints_conflict, hash_parts, verify_checkpoint)


def setup_system():
    sid, domain = "entity-8121", "iepp.test"
    key = Ed25519PrivateKey.generate()
    initial = sha256(b"initial").digest()
    challenges = ChallengeAuthority()
    registry = AtomicRegistry("registry-1", challenges)
    registry.enroll(sid, domain, initial, "key-1", key.public_key(), {"os.urandom", "test.entropy"})
    return Prover(sid, domain, "key-1", key, initial), registry, challenges


class CoreTests(unittest.TestCase):
    def test_valid_transition(self):
        prover, registry, ca = setup_system()
        challenge = ca.issue(prover.sid, prover.domain, now=10, ttl=10, nonce=b"a" * 32)
        evidence = prover.transition(challenge, b"entropy-a", "test.entropy", b"runtime")
        self.assertEqual(registry.verify_and_advance(evidence, now=11), (True, "CONTINUITY_VALID"))
        self.assertEqual(registry.enrollments[prover.sid].counter, 1)

    def test_exact_replay(self):
        prover, registry, ca = setup_system()
        challenge = ca.issue(prover.sid, prover.domain, now=10, ttl=10)
        evidence = prover.transition(challenge, b"e1", "test.entropy", b"r")
        self.assertTrue(registry.verify_and_advance(evidence, 11)[0])
        self.assertEqual(registry.verify_and_advance(evidence, 11), (False, "REPLAY_DETECTED"))

    def test_rollback(self):
        prover, registry, ca = setup_system()
        old = prover.clone()
        c1 = ca.issue(prover.sid, prover.domain, now=10, ttl=10)
        self.assertTrue(registry.verify_and_advance(prover.transition(c1, b"e1", "test.entropy", b"r1"), 11)[0])
        c2 = ca.issue(prover.sid, prover.domain, now=12, ttl=10)
        rolled = old.transition(c2, b"e2", "test.entropy", b"r2")
        self.assertEqual(registry.verify_and_advance(rolled, 13), (False, "ROLLBACK_OR_LOSING_FORK"))

    def test_atomic_fork_race_exactly_one_wins(self):
        prover, registry, ca = setup_system()
        left, right = prover.clone(), prover.clone()
        cl = ca.issue(prover.sid, prover.domain, now=10, ttl=10)
        cr = ca.issue(prover.sid, prover.domain, now=10, ttl=10)
        el = left.transition(cl, b"left", "test.entropy", b"r")
        er = right.transition(cr, b"right", "test.entropy", b"r")
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda e: registry.verify_and_advance(e, 11), (el, er)))
        self.assertEqual(sum(int(ok) for ok, _ in results), 1)
        self.assertIn("ROLLBACK_OR_LOSING_FORK", {reason for _, reason in results})

    def test_expired_unknown_and_used_challenges(self):
        prover, registry, ca = setup_system()
        expired = ca.issue(prover.sid, prover.domain, now=1, ttl=1)
        self.assertEqual(registry.verify_and_advance(
            prover.clone().transition(expired, b"e", "test.entropy", b"r"), 3),
            (False, "CHALLENGE_EXPIRED"))
        unknown = replace(expired, challenge_id=b"x" * 32)
        evidence = prover.clone().transition(unknown, b"e2", "test.entropy", b"r")
        self.assertEqual(registry.verify_and_advance(evidence, 1), (False, "CHALLENGE_UNKNOWN"))

    def test_domain_counter_state_and_signature_substitution(self):
        prover, registry, ca = setup_system()
        c = ca.issue(prover.sid, prover.domain, now=1, ttl=10)
        evidence = prover.transition(c, b"e", "test.entropy", b"r")
        mutations = [replace(evidence, domain="other"), replace(evidence, counter=9),
                     replace(evidence, runtime_commitment=b"tampered"),
                     replace(evidence, signature=bytes(64))]
        reasons = [registry.verify_and_advance(item, 2)[1] for item in mutations]
        self.assertEqual(reasons[0], "DOMAIN_OR_PROTOCOL_MISMATCH")
        self.assertTrue(all(reason != "CONTINUITY_VALID" for reason in reasons))

    def test_entropy_source_and_repetition(self):
        prover, registry, ca = setup_system()
        c1 = ca.issue(prover.sid, prover.domain, now=1, ttl=10)
        self.assertTrue(registry.verify_and_advance(
            prover.transition(c1, b"same", "test.entropy", b"r1"), 2)[0])
        before_second = prover.clone()
        c2 = ca.issue(prover.sid, prover.domain, now=2, ttl=10)
        repeated = before_second.transition(c2, b"same", "test.entropy", b"r2")
        self.assertEqual(registry.verify_and_advance(repeated, 3), (False, "ENTROPY_REPEATED"))
        c3 = ca.issue(prover.sid, prover.domain, now=2, ttl=10)
        bad_source = prover.clone().transition(c3, b"new", "untrusted", b"r3")
        self.assertEqual(registry.verify_and_advance(bad_source, 3), (False, "ENTROPY_SOURCE_NOT_ALLOWED"))

    def test_audit_chain_advances(self):
        prover, registry, ca = setup_system()
        roots = []
        for counter in range(1, 4):
            c = ca.issue(prover.sid, prover.domain, now=counter, ttl=10)
            evidence = prover.transition(c, f"e{counter}".encode(), "test.entropy", b"r")
            self.assertTrue(registry.verify_and_advance(evidence, counter)[0])
            roots.append(registry.log_root)
        self.assertEqual(len(set(roots)), 3)
        self.assertEqual(registry.audit[-1].previous_log_root, roots[-2])
        self.assertTrue(registry.verify_audit_chain())
        original = registry.audit[1]
        registry.audit[1] = replace(original, kind="TAMPERED")
        self.assertFalse(registry.verify_audit_chain())

    def test_authorized_key_migration_and_old_key_rejection(self):
        prover, registry, ca = setup_system()
        challenge = ca.issue(prover.sid, prover.domain, now=1, ttl=10)
        new_key = Ed25519PrivateKey.generate()
        migration = create_migration(prover, challenge, "key-2", new_key)
        self.assertEqual(registry.migrate_key(migration, 2), (True, "KEY_MIGRATION_VALID"))
        old_challenge = ca.issue(prover.sid, prover.domain, now=2, ttl=10)
        old_evidence = prover.transition(old_challenge, b"e", "test.entropy", b"r")
        self.assertEqual(registry.verify_and_advance(old_evidence, 3), (False, "KEY_ID_MISMATCH"))
        migrated = Prover(prover.sid, prover.domain, "key-2", new_key, registry.enrollments[prover.sid].canonical_head,
                          registry.enrollments[prover.sid].counter)
        new_challenge = ca.issue(prover.sid, prover.domain, now=3, ttl=10)
        self.assertTrue(registry.verify_and_advance(
            migrated.transition(new_challenge, b"e2", "test.entropy", b"r2"), 4)[0])

    def test_migration_requires_both_keys(self):
        prover, registry, ca = setup_system()
        challenge = ca.issue(prover.sid, prover.domain, now=1, ttl=10)
        new_key = Ed25519PrivateKey.generate()
        migration = create_migration(prover, challenge, "key-2", new_key)
        tampered = replace(migration, new_signature=bytes(64))
        self.assertEqual(registry.migrate_key(tampered, 2), (False, "MIGRATION_SIGNATURE_INVALID"))

    def test_split_view_checkpoint_detection(self):
        sid, domain = "entity", "domain"
        key, checkpoint_key = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
        initial = sha256(b"initial").digest()
        registries, provers = [], []
        for branch in range(2):
            ca = ChallengeAuthority()
            registry = AtomicRegistry("same-registry", ca, checkpoint_key)
            registry.enroll(sid, domain, initial, "k", key.public_key(), {"test.entropy"})
            prover = Prover(sid, domain, "k", key, initial)
            challenge = ca.issue(sid, domain, now=1, ttl=10, nonce=bytes([branch + 1]) * 32)
            evidence = prover.transition(challenge, f"entropy-{branch}".encode(), "test.entropy", b"r")
            self.assertTrue(registry.verify_and_advance(evidence, 2)[0])
            registries.append(registry)
            provers.append(prover)
        self.assertTrue(checkpoints_conflict(registries[0].checkpoint(sid), registries[1].checkpoint(sid)))
        checkpoint = registries[0].checkpoint(sid)
        self.assertTrue(verify_checkpoint(checkpoint, checkpoint_key.public_key()))
        self.assertFalse(verify_checkpoint(replace(checkpoint, canonical_head=b"x" * 32), checkpoint_key.public_key()))


if __name__ == "__main__":
    unittest.main()

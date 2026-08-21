from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import Prover, create_migration, verify_checkpoint
from durable_registry import (CommitResponseLost, DurableRegistry, InjectedCrash,
                              RegistryIntegrityError)


SID, DOMAIN, PROFILE = "entity-8121", "iepp.test", "test.entropy"


def make_system(path: Path, checkpoint_key=None):
    key = Ed25519PrivateKey.generate()
    initial = sha256(b"initial").digest()
    registry = DurableRegistry(path, "registry-1", checkpoint_key)
    registry.enroll(SID, DOMAIN, initial, "key-1", key.public_key(), PROFILE)
    return Prover(SID, DOMAIN, "key-1", key, initial), registry, key, initial


def evidence_for(registry, prover, marker=b"1", now=10):
    challenge = registry.issue_challenge(SID, DOMAIN, now=now, ttl=20, nonce=marker * 32)
    return prover.transition(challenge, b"entropy-" + marker, PROFILE, b"runtime")


class DurableRegistryFaultMatrixTests(unittest.TestCase):
    def test_f00_before_transaction_changes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            prover, registry, _, initial = make_system(Path(directory) / "registry.db")
            evidence_for(registry, prover)
            self.assertEqual(registry.state(SID)[:2], (0, initial))
            registry.close()

    def test_f01_through_f06_precommit_failures_roll_back_every_related_write(self):
        points = ("after_begin", "after_challenge", "after_evidence", "after_audit",
                  "after_head", "after_root")
        for point in points:
            with self.subTest(point=point), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "registry.db"
                prover, registry, _, initial = make_system(path)
                evidence = evidence_for(registry, prover)
                with self.assertRaises(InjectedCrash):
                    registry.verify_and_advance(evidence, now=11, inject_failure=point)
                registry.close()
                reopened = DurableRegistry(path, "registry-1")
                self.assertEqual(reopened.state(SID)[:2], (0, initial))
                self.assertEqual(reopened.connection.execute(
                    "SELECT COUNT(*) FROM accepted_evidence").fetchone()[0], 0)
                self.assertEqual(reopened.connection.execute(
                    "SELECT consumed_at FROM challenges").fetchone()[0], None)
                self.assertEqual(reopened.connection.execute(
                    "SELECT sequence FROM registry_meta").fetchone()[0], 0)
                reopened.close()

    def test_f07_f08_commit_response_loss_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.db"
            prover, registry, _, _ = make_system(path)
            evidence = evidence_for(registry, prover)
            with self.assertRaises(CommitResponseLost):
                registry.verify_and_advance(evidence, now=11, inject_failure="after_commit")
            self.assertEqual(registry.state(SID)[0], 1)
            retry = registry.verify_and_advance(evidence, now=11)
            self.assertEqual(retry.code, "ALREADY_COMMITTED")
            self.assertEqual((retry.accepted_counter, retry.current_counter), (1, 1))
            self.assertEqual(registry.connection.execute(
                "SELECT COUNT(*) FROM accepted_evidence").fetchone()[0], 1)
            self.assertEqual(registry.connection.execute(
                "SELECT COUNT(*) FROM audit_events").fetchone()[0], 1)
            registry.close()

    def test_f09_concurrent_successors_exactly_one_commits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.db"
            prover, first, _, _ = make_system(path)
            left, right = prover.clone(), prover.clone()
            left_evidence = evidence_for(first, left, b"a")
            right_evidence = evidence_for(first, right, b"b")
            second = DurableRegistry(path, "registry-1")
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda pair: pair[0].verify_and_advance(pair[1], now=11),
                                        ((first, left_evidence), (second, right_evidence))))
            self.assertEqual(sum(result.accepted for result in results), 1)
            self.assertIn("ROLLBACK_OR_LOSING_FORK", {result.code for result in results})
            first.close(); second.close()

    def test_f10_checkpoint_can_be_regenerated_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.db"
            checkpoint_key = Ed25519PrivateKey.generate()
            prover, registry, _, _ = make_system(path, checkpoint_key)
            self.assertTrue(registry.verify_and_advance(evidence_for(registry, prover), 11).accepted)
            expected = registry.checkpoint(SID)
            registry.close()
            reopened = DurableRegistry(path, "registry-1", checkpoint_key)
            regenerated = reopened.checkpoint(SID)
            self.assertEqual(regenerated, expected)
            self.assertTrue(verify_checkpoint(regenerated, checkpoint_key.public_key()))
            reopened.close()

    def test_f11_consistent_old_snapshot_is_not_locally_detectable(self):
        with tempfile.TemporaryDirectory() as directory:
            path, snapshot = Path(directory) / "registry.db", Path(directory) / "snapshot.db"
            prover, registry, key, initial = make_system(path)
            registry.close()
            shutil.copy2(path, snapshot)
            registry = DurableRegistry(path, "registry-1")
            self.assertTrue(registry.verify_and_advance(evidence_for(registry, prover), 11).accepted)
            registry.close()
            shutil.copy2(snapshot, path)
            restored = DurableRegistry(path, "registry-1")
            self.assertEqual(restored.state(SID)[:2], (0, initial))
            stale = Prover(SID, DOMAIN, "key-1", key, initial)
            self.assertTrue(restored.verify_and_advance(evidence_for(restored, stale, b"z"), 11).accepted)
            restored.close()

    def test_f12_corruption_fails_closed_without_genesis_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.db"
            _, registry, _, _ = make_system(path)
            registry.close()
            with path.open("r+b") as stream:
                stream.seek(0)
                stream.write(b"not-a-sqlite-registry")
            with self.assertRaises(RegistryIntegrityError):
                DurableRegistry(path, "registry-1")

    def test_entropy_health_and_canonical_decision_are_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            prover, registry, _, _ = make_system(Path(directory) / "registry.db")
            first = evidence_for(registry, prover, b"a")
            self.assertEqual(registry.verify_and_advance(first, 11).entropy_health, "OK")
            before = prover.clone()
            challenge = registry.issue_challenge(SID, DOMAIN, now=12, ttl=20, nonce=b"b" * 32)
            repeated = before.transition(challenge, b"entropy-a", PROFILE, b"runtime")
            decision = registry.verify_and_advance(repeated, 13)
            self.assertEqual((decision.accepted, decision.code, decision.entropy_health),
                             (False, "ENTROPY_REPEATED", "REPEATED"))
            registry.close()

    def test_key_migration_is_durable_atomic_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.db"
            prover, registry, _, _ = make_system(path)
            challenge = registry.issue_challenge(SID, DOMAIN, now=10, ttl=20, nonce=b"m" * 32)
            new_key = Ed25519PrivateKey.generate()
            migration = create_migration(prover, challenge, "key-2", new_key)
            self.assertEqual(registry.migrate_key(migration, 11).code, "KEY_MIGRATION_VALID")
            self.assertEqual(registry.migrate_key(migration, 11).code, "ALREADY_COMMITTED")
            registry.close()
            reopened = DurableRegistry(path, "registry-1")
            migrated = Prover(SID, DOMAIN, "key-2", new_key, prover.state, prover.counter)
            evidence = evidence_for(reopened, migrated, b"n", now=12)
            self.assertTrue(reopened.verify_and_advance(evidence, 13).accepted)
            self.assertEqual(reopened.connection.execute(
                "SELECT COUNT(*) FROM accepted_migrations").fetchone()[0], 1)
            reopened.close()


if __name__ == "__main__":
    unittest.main()

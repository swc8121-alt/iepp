"""TRP 2.0 merge-gate tests against the real IEPP vNext components.

These tests intentionally separate execution-copy diagnostics from canonical
acceptance.  They exercise the Ed25519 core and the durable SQLite CAS store,
not the reduced HMAC security-game model.
"""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import multiprocessing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core import AtomicRegistry, ChallengeAuthority, Prover
from durable_store import SQLiteCanonicalStore


def make_system():
    sid, domain = "trp2-entity", "trp2.integration"
    key = Ed25519PrivateKey.generate()
    initial = sha256(b"trp2-initial").digest()
    authority = ChallengeAuthority()
    registry = AtomicRegistry("trp2-registry", authority)
    registry.enroll(sid, domain, initial, "key-1", key.public_key(), {"test.entropy"})
    return Prover(sid, domain, "key-1", key, initial), registry, authority


def cas_worker(path, start, new_head, evidence_id, gate, output):
    store = SQLiteCanonicalStore(path)
    gate.wait()
    output.put(store.compare_and_swap("entity", 0, start, 1, new_head, evidence_id))
    store.close()


def crash_before_commit(path, evidence_id):
    connection = sqlite3.connect(path, timeout=10, isolation_level=None)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("BEGIN IMMEDIATE")
    connection.execute(
        "INSERT INTO accepted_evidence VALUES (?, ?, ?, ?)",
        (evidence_id, "entity", 1, sha256(b"uncommitted").digest()),
    )
    os._exit(73)


class TRP2RealCoreTests(unittest.TestCase):
    def test_replay_and_rollback_are_rejected_by_real_core(self):
        prover, registry, authority = make_system()
        stale = prover.clone()
        challenge = authority.issue(prover.sid, prover.domain, now=10, ttl=10)
        evidence = prover.transition(challenge, b"entropy-1", "test.entropy", b"runtime-1")
        self.assertEqual(registry.verify_and_advance(evidence, 11), (True, "CONTINUITY_VALID"))
        self.assertEqual(registry.verify_and_advance(evidence, 11), (False, "REPLAY_DETECTED"))

        rollback_challenge = authority.issue(prover.sid, prover.domain, now=12, ttl=10)
        rollback = stale.transition(
            rollback_challenge, b"entropy-2", "test.entropy", b"runtime-2"
        )
        self.assertEqual(
            registry.verify_and_advance(rollback, 13),
            (False, "ROLLBACK_OR_LOSING_FORK"),
        )

    def test_real_core_thread_race_has_one_canonical_winner(self):
        prover, registry, authority = make_system()
        left, right = prover.clone(), prover.clone()
        left_challenge = authority.issue(prover.sid, prover.domain, now=10, ttl=10)
        right_challenge = authority.issue(prover.sid, prover.domain, now=10, ttl=10)
        candidates = (
            left.transition(left_challenge, b"left", "test.entropy", b"runtime"),
            right.transition(right_challenge, b"right", "test.entropy", b"runtime"),
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda item: registry.verify_and_advance(item, 11), candidates))
        self.assertEqual(sum(int(ok) for ok, _ in results), 1)
        self.assertEqual(registry.enrollments[prover.sid].counter, 1)

    def test_snapshot_with_key_and_state_is_an_explicit_l1_boundary(self):
        legitimate, registry, authority = make_system()
        snapshot = legitimate.clone()
        attacker_challenge = authority.issue(legitimate.sid, legitimate.domain, now=10, ttl=10)
        legitimate_challenge = authority.issue(legitimate.sid, legitimate.domain, now=10, ttl=10)
        attacker = snapshot.transition(
            attacker_challenge, b"attacker", "test.entropy", b"snapshot-runtime"
        )
        honest = legitimate.transition(
            legitimate_challenge, b"honest", "test.entropy", b"honest-runtime"
        )
        self.assertEqual(registry.verify_and_advance(attacker, 11), (True, "CONTINUITY_VALID"))
        self.assertEqual(
            registry.verify_and_advance(honest, 11),
            (False, "ROLLBACK_OR_LOSING_FORK"),
        )


class TRP2DurableStoreTests(unittest.TestCase):
    def test_process_race_has_one_durable_canonical_winner(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "registry.db")
            initial = sha256(b"durable-initial").digest()
            store = SQLiteCanonicalStore(path)
            store.enroll("entity", initial)
            store.close()

            context = multiprocessing.get_context("spawn")
            gate, output = context.Event(), context.Queue()
            processes = [
                context.Process(
                    target=cas_worker,
                    args=(path, initial, sha256(label).digest(), label * 32, gate, output),
                )
                for label in (b"a", b"b")
            ]
            for process in processes:
                process.start()
            gate.set()
            results = [output.get(timeout=15) for _ in processes]
            for process in processes:
                process.join(timeout=15)
                self.assertEqual(process.exitcode, 0)

            reopened = SQLiteCanonicalStore(path)
            self.assertEqual(sum(int(ok) for ok, _ in results), 1)
            self.assertEqual(reopened.read("entity").counter, 1)
            reopened.close()

    def test_abrupt_exit_rolls_back_uncommitted_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "registry.db")
            initial, evidence_id = sha256(b"crash-initial").digest(), b"z" * 32
            store = SQLiteCanonicalStore(path)
            store.enroll("entity", initial)
            store.close()

            context = multiprocessing.get_context("spawn")
            process = context.Process(target=crash_before_commit, args=(path, evidence_id))
            process.start()
            process.join(timeout=15)
            self.assertEqual(process.exitcode, 73)

            reopened = SQLiteCanonicalStore(path)
            self.assertEqual((reopened.read("entity").counter, reopened.read("entity").head), (0, initial))
            self.assertIsNone(
                reopened.connection.execute(
                    "SELECT 1 FROM accepted_evidence WHERE evidence_id = ?", (evidence_id,)
                ).fetchone()
            )
            reopened.close()


if __name__ == "__main__":
    unittest.main()

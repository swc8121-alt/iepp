import copy
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from a3_registry import A3RegistryEngine
from a3_safe_resume_demo import run
from a3_vm_runner import build_candidate, prepare_workspace


class A3SignedForkTests(unittest.TestCase):
    def prepare(self, directory: str):
        workspace = Path(directory)
        prepared = prepare_workspace(
            workspace, "agent-1", "iepp.a3.test", "shared-test-key", "initial", False
        )
        snapshot = json.loads(Path(prepared["snapshot"]).read_text(encoding="utf-8"))
        engine = A3RegistryEngine(prepared["database"], prepared["enrollment"])
        return prepared, snapshot, engine

    @staticmethod
    def challenge(engine: A3RegistryEngine) -> dict:
        status, response = engine.issue_challenge("agent-1", "iepp.a3.test")
        if status != 200:
            raise AssertionError(response)
        return response["challenge"]

    def test_prepare_uses_real_ed25519_credential(self):
        with tempfile.TemporaryDirectory() as directory:
            prepared, snapshot, engine = self.prepare(directory)
            try:
                enrollment = json.loads(Path(prepared["enrollment"]).read_text(encoding="utf-8"))
                self.assertEqual(len(bytes.fromhex(snapshot["private_key"])), 32)
                self.assertEqual(len(bytes.fromhex(enrollment["public_key"])), 32)
                self.assertEqual(
                    sha256(bytes.fromhex(enrollment["public_key"])).hexdigest(),
                    snapshot["public_key_fingerprint_sha256"],
                )
                self.assertTrue(snapshot["test_only_cloned_private_key"])
            finally:
                engine.close()

    def test_valid_signed_transition_then_exact_replay_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            _, snapshot, engine = self.prepare(directory)
            try:
                candidate = build_candidate(
                    snapshot, "A", "trial-replay", "A3-REPLAY", self.challenge(engine), b"a" * 32
                )
                status, first = engine.verify_and_advance(candidate["evidence"])
                replay_status, replay = engine.verify_and_advance(candidate["evidence"])
                self.assertEqual(status, 200)
                self.assertTrue(first["accepted"])
                self.assertEqual(replay_status, 200)
                self.assertFalse(replay["accepted"])
                self.assertEqual(replay["reason"], "REPLAY_DETECTED")
            finally:
                engine.close()

    def test_tampered_signature_is_rejected_before_cas(self):
        with tempfile.TemporaryDirectory() as directory:
            _, snapshot, engine = self.prepare(directory)
            try:
                candidate = build_candidate(
                    snapshot, "A", "trial-signature", "A3-SIGNATURE",
                    self.challenge(engine), b"b" * 32,
                )
                tampered = copy.deepcopy(candidate["evidence"])
                signature = bytearray.fromhex(tampered["signature"])
                signature[0] ^= 1
                tampered["signature"] = bytes(signature).hex()
                tampered.pop("evidence_id")
                status, decision = engine.verify_and_advance(tampered)
                self.assertEqual(status, 200)
                self.assertFalse(decision["accepted"])
                self.assertEqual(decision["reason"], "SIGNATURE_INVALID")
                self.assertEqual(engine.store.read("agent-1").counter, 0)
            finally:
                engine.close()

    def test_shared_pre_restore_challenge_has_one_winner(self):
        with tempfile.TemporaryDirectory() as directory:
            _, snapshot, engine = self.prepare(directory)
            try:
                challenge = self.challenge(engine)
                left = build_candidate(snapshot, "A", "trial-shared", "A3-SHARED", challenge, b"c" * 32)
                right = build_candidate(snapshot, "B", "trial-shared", "A3-SHARED", challenge, b"d" * 32)
                decisions = [
                    engine.verify_and_advance(left["evidence"])[1],
                    engine.verify_and_advance(right["evidence"])[1],
                ]
                self.assertEqual(sum(item["accepted"] for item in decisions), 1)
                self.assertEqual({item["reason"] for item in decisions},
                                 {"CONTINUITY_VALID", "CHALLENGE_USED"})
            finally:
                engine.close()

    def test_loopback_safe_resume_demo_covers_both_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            summary, rows = run(Path(directory), trials=6)
            self.assertTrue(summary["passed"], summary["failures"])
            self.assertEqual(summary["canonical_accepts"], 6)
            self.assertEqual(summary["simulated_protected_actions"], 6)
            self.assertEqual(summary["double_accepts"], 0)
            self.assertEqual(len(rows), 12)
            self.assertEqual({row["snapshot_point"] for row in rows},
                             {"BEFORE_CHALLENGE", "AFTER_CHALLENGE"})


if __name__ == "__main__":
    unittest.main()

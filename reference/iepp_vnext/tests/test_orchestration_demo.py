import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orchestration_demo import CLAIM_BOUNDARY, Demo


class OrchestrationDemoTests(unittest.TestCase):
    def test_all_required_cases_and_log_contract(self):
        counter = 0

        def deterministic_entropy(length: int) -> bytes:
            nonlocal counter
            counter += 1
            return counter.to_bytes(length, "big")

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "evidence.jsonl"
            records = Demo(output, run_id="test-run", entropy=deterministic_entropy).run()
            persisted = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(records, persisted)
        cases = {item["case"] for item in records}
        self.assertTrue({"normal_continuation", "persisted_process_restart", "old_proof_replay",
                         "copied_credential_divergent_state", "same_state_fork",
                         "snapshot_restore_rollback", "entropy_source_fault_fallback"} <= cases)

        required = {"run_id", "timestamp", "monotonic_counter", "orchestrator_task_id", "agent_id",
                    "credential_key_id", "predecessor_hash", "current_hash",
                    "challenge_nonce_digest", "entropy_metadata", "branch_fork_id",
                    "verifier_decision", "reason_code", "evidence_level"}
        for item in records:
            self.assertFalse(required - item.keys())
            self.assertEqual(item["run_id"], "test-run")
            self.assertEqual(item["evidence_level"], "L1")
            self.assertEqual(item["claim_boundary"], CLAIM_BOUNDARY)
            self.assertIn(item["verifier_decision"], {"ACCEPT", "REJECT", "INDETERMINATE"})

        outcomes = {(item["case"], item["branch_fork_id"]):
                    (item["verifier_decision"], item["reason_code"]) for item in records}
        self.assertEqual(outcomes[("old_proof_replay", "replay")], ("REJECT", "REPLAY_DETECTED"))
        self.assertEqual(outcomes[("copied_credential_divergent_state", "credential-copy")],
                         ("REJECT", "STALE_CANONICAL_STATE"))
        self.assertEqual(outcomes[("same_state_fork", "B")], ("ACCEPT", "CONTINUITY_VALID"))
        self.assertEqual(outcomes[("same_state_fork", "B-prime")],
                         ("REJECT", "ROLLBACK_OR_LOSING_FORK"))
        self.assertTrue(next(item for item in records
                             if item["case"] == "entropy_source_fault_fallback")
                        ["entropy_metadata"]["fallback_used"])


if __name__ == "__main__":
    unittest.main()

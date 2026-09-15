import copy
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import a3_registry
from a3_registry_server import create_server
from a3_safe_resume_demo import result_row
from a3_vm_runner import (accepted_snapshot, build_candidate, cmd_export_snapshot,
                          http_json, issue_challenge, parser, prepare_workspace,
                          submit_candidate, write_private_snapshot)


class AcceptedSnapshotTests(unittest.TestCase):
    @contextmanager
    def lab(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            prepared = prepare_workspace(path, "agent-1", "iepp.a3.test", "lab-key", "p0")
            snapshot = json.loads(Path(prepared["snapshot"]).read_text())
            server = create_server(prepared["database"], prepared["enrollment"],
                                   event_log=str(path / "server.jsonl"))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                yield path, snapshot, server, url
            finally:
                server.shutdown()
                server.server_close()
                server.engine.close()
                thread.join(timeout=5)

    def candidate(self, snapshot, url, branch="A", trial="baseline", shared=None):
        challenge = shared or issue_challenge(url, snapshot["sid"], snapshot["domain"], 60)
        return build_candidate(snapshot, branch, trial, "A3-NEXT-TEST", challenge)

    def accepted(self, snapshot, url):
        candidate = self.candidate(snapshot, url)
        decision = submit_candidate(url, candidate)
        result = result_row(candidate, decision, 0)
        head = http_json(url + "/v1/head?sid=agent-1")
        return candidate, result, head

    def test_export_p1_continue_to_p2_and_reject_restored_p1(self):
        with self.lab() as (path, p0, server, url):
            candidate, result, head = self.accepted(p0, url)
            p1 = accepted_snapshot(p0, candidate, result, head)
            write_private_snapshot(path / "p1.json", p1)
            self.assertEqual(p1["counter"], 1)
            self.assertEqual(p1["private_key"], p0["private_key"])
            self.assertIsNone(p1["challenge"])
            self.assertEqual(p1["snapshot_point"], "BEFORE_CHALLENGE")
            continued = self.candidate(p1, url, trial="p2")
            self.assertTrue(submit_candidate(url, continued)["accepted"])
            restored_p1 = json.loads((path / "p1.json").read_text())
            old = self.candidate(restored_p1, url, trial="rollback")
            rejected = submit_candidate(url, old)
            self.assertFalse(rejected["accepted"])
            self.assertEqual(rejected["reason"], "ROLLBACK_OR_LOSING_FORK")
            self.assertEqual(rejected["canonical_head_after"], continued["evidence"]["state"])
            with self.assertRaisesRegex(ValueError, "registry-head"):
                accepted_snapshot(p0, candidate, result, http_json(url + "/v1/head?sid=agent-1"))

    def test_export_rejects_tampered_or_mismatched_inputs(self):
        with self.lab() as (_, p0, server, url):
            candidate, result, head = self.accepted(p0, url)
            for field, value in [("canonical_accept", False), ("transport_ok", False),
                                 ("transport_error", "timeout"), ("registry_reason", "CHALLENGE_USED"),
                                 ("protected_action", "BLOCKED"), ("branch_id", "B"),
                                 ("evidence_id", "00" * 32), ("candidate_successor", "00" * 32)]:
                with self.subTest(field=field), self.assertRaises(ValueError):
                    accepted_snapshot(p0, candidate, {**result, field: value}, head)
            for field, value in [("sid", "other"), ("counter", 2),
                                 ("last_evidence_id", "00" * 32), ("ok", False)]:
                with self.subTest(head=field), self.assertRaises(ValueError):
                    accepted_snapshot(p0, candidate, result, {**head, field: value})
            tampered = copy.deepcopy(candidate)
            tampered["evidence"]["signature"] = "00" * 64
            tampered["evidence"].pop("evidence_id")
            with self.assertRaisesRegex(ValueError, "signature"):
                accepted_snapshot(p0, tampered, result, head)
            with self.assertRaisesRegex(ValueError, "key-mismatch"):
                accepted_snapshot({**p0, "private_key": "01" * 32}, candidate, result, head)
            with self.assertRaisesRegex(ValueError, "continue-snapshot"):
                accepted_snapshot({**p0, "counter": 1}, candidate, result, head)

    def test_cli_new_private_file_only_and_no_secret_stdout(self):
        with self.lab() as (path, p0, server, url):
            candidate, result, head = self.accepted(p0, url)
            (path / "candidate.json").write_text(json.dumps(candidate))
            log = path / "result.jsonl"
            log.write_text(json.dumps(result) + "\n")
            args = parser().parse_args([
                "export-snapshot", "--snapshot", str(path / "snapshot.json"),
                "--candidate", str(path / "candidate.json"), "--log", str(log),
                "--registry-url", url, "--output", str(path / "p1.json")])
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(cmd_export_snapshot(args), 0)
            self.assertNotIn(p0["private_key"], output.getvalue())
            saved = (path / "p1.json").read_bytes()
            if os.name == "posix":
                self.assertEqual((path / "p1.json").stat().st_mode & 0o777, 0o600)
            with self.assertRaises(SystemExit):
                cmd_export_snapshot(args)
            self.assertEqual((path / "p1.json").read_bytes(), saved)
            args.output = str(path / "duplicate.json")
            log.write_text((json.dumps(result) + "\n") * 2)
            with self.assertRaisesRegex(SystemExit, "exactly-one"):
                cmd_export_snapshot(args)
            self.assertFalse((path / "duplicate.json").exists())

    def test_used_shared_challenge_after_p1_state_copy(self):
        with self.lab() as (_, p0, server, url):
            candidate, result, head = self.accepted(p0, url)
            p1 = accepted_snapshot(p0, candidate, result, head)
            shared = issue_challenge(url, p1["sid"], p1["domain"], 60)
            restored = copy.deepcopy(p1)
            b = self.candidate(p1, url, "B", "shared-ba", shared)
            a = self.candidate(restored, url, "A", "shared-ba", shared)
            self.assertTrue(submit_candidate(url, b)["accepted"])
            self.assertEqual(submit_candidate(url, a)["reason"], "CHALLENGE_USED")
            self.assertEqual(submit_candidate(url, b)["reason"], "REPLAY_DETECTED")

    def test_server_timing_observes_waiting_requests_without_double_accept(self):
        with self.lab() as (path, p0, server, url):
            candidates = [self.candidate(p0, url, branch) for branch in ("A", "B")]
            parsed = threading.Barrier(3, timeout=5)
            original = a3_registry.evidence_from_dict

            def rendezvous(value):
                evidence = original(value)
                parsed.wait()
                return evidence

            with patch.object(a3_registry, "evidence_from_dict", side_effect=rendezvous):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    # Hold the decision lock until both HTTP requests entered verification.
                    server.engine._lock.acquire()
                    try:
                        futures = [pool.submit(submit_candidate, url, c) for c in candidates]
                        parsed.wait()
                    finally:
                        server.engine._lock.release()
                    decisions = [future.result(timeout=5) for future in futures]
            self.assertEqual(sum(d["accepted"] for d in decisions), 1)
            timings = [d["registry_timing"] for d in decisions]
            self.assertEqual(len({t["server_instance_id"] for t in timings}), 1)
            self.assertEqual(len({t["request_id"] for t in timings}), 2)
            for t in timings:
                keys = ["request_received_monotonic_ns", "body_complete_monotonic_ns",
                        "verification_requested_monotonic_ns", "lock_acquired_monotonic_ns",
                        "decision_monotonic_ns"]
                times = [t[k] for k in keys]
                self.assertEqual(times, sorted(times))
            self.assertLess(max(t["verification_requested_monotonic_ns"] for t in timings),
                            min(t["decision_monotonic_ns"] for t in timings))
            events = [json.loads(line) for line in (path / "server.jsonl").read_text().splitlines()]
            events = [e for e in events if e["event"].startswith("TRANSITION_")]
            for decision in decisions:
                event = next(e for e in events if e["evidence_id"] == decision["evidence_id"])
                self.assertEqual(event["registry_timing"], decision["registry_timing"])


if __name__ == "__main__":
    unittest.main()

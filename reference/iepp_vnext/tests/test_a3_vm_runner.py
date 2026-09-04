import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "a3_vm_runner.py"


class A3VMRunnerTests(unittest.TestCase):
    def run_cmd(self, *args, expected=(0,)):
        result = subprocess.run([sys.executable, str(RUNNER), *args], cwd=ROOT,
                                text=True, capture_output=True)
        self.assertIn(result.returncode, expected, result.stderr + result.stdout)
        return result

    def test_ab_and_ba_each_have_one_winner(self):
        for order in (("A", "B"), ("B", "A")):
            with self.subTest(order=order), tempfile.TemporaryDirectory() as directory:
                work = Path(directory); log = work / "results.jsonl"
                self.run_cmd("prepare", "--workspace", str(work), "--snapshot-point", "BEFORE_CHALLENGE")
                for branch in ("A", "B"):
                    self.run_cmd("candidate", "--snapshot", str(work / "snapshot.json"),
                                 "--branch-id", branch, "--trial-id", "serial", "--case-id", "S1-serial",
                                 "--challenge-id", f"challenge-{branch}", "--output", str(work / f"{branch}.json"))
                self.run_cmd("submit", "--database", str(work / "registry.db"), "--candidate",
                             str(work / f"{order[0]}.json"), "--log", str(log))
                self.run_cmd("submit", "--database", str(work / "registry.db"), "--candidate",
                             str(work / f"{order[1]}.json"), "--log", str(log), expected=(2,))
                rows = [json.loads(line) for line in log.read_text().splitlines()]
                self.assertEqual(sum(row["canonical_accept"] for row in rows), 1)
                self.run_cmd("check", "--log", str(log))


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from pathlib import Path


class TRP2VectorTests(unittest.TestCase):
    def test_baseline_vectors(self):
        data = json.loads(Path("trp2_vectors.json").read_text(encoding="utf-8"))
        self.assertEqual(data["trp_version"], "2.0-v0.1")
        ids = {v["id"] for v in data["vectors"]}
        self.assertTrue({"T01", "T03", "T04", "T05", "T10"}.issubset(ids))
        for vector in data["vectors"]:
            self.assertIn(vector["profile"], {f"A{i}" for i in range(7)})
            self.assertTrue(vector["attack"])
            self.assertTrue(vector["expected"])


if __name__ == "__main__":
    unittest.main()

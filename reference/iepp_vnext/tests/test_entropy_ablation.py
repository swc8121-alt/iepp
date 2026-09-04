import unittest

from entropy_ablation import run


class EntropyAblationTests(unittest.TestCase):
    def test_no_entropy_fields_preserve_serialization_controls(self):
        result = run(replay_trials=10, fork_races=10)
        self.assertEqual(result["replay_false_accepts"], 0)
        self.assertEqual(result["double_accepts"], 0)


if __name__ == "__main__":
    unittest.main()

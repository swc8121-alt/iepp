import unittest

from trp2_benchmark import assert_expected, run


class TRP2SecurityGameTests(unittest.TestCase):
    def test_security_invariants(self):
        result = run(trials=100)
        assert_expected(result)

    def test_l1_key_state_boundary(self):
        result = run(trials=25)
        self.assertEqual(result["key_plus_state_boundary_accept_rate"], 1.0)
        self.assertEqual(result["dual_canonical_accept_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()

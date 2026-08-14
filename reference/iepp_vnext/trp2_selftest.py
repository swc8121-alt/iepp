"""Run all dependency-free TRP 2.0 checks without pytest."""

import unittest

from trp2_benchmark import assert_expected, run


if __name__ == "__main__":
    result = run(trials=1000)
    assert_expected(result)
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        "test_trp2_unittest",
        "test_trp2_profiles",
        "test_trp2_metrics",
    ])
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    if not outcome.wasSuccessful():
        raise SystemExit(1)
    print("TRP 2.0 aggregate self-test: PASS")

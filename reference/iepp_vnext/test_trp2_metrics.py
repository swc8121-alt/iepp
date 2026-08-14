import unittest

from trp2_metrics import BinaryMetric, security_report


class TRP2MetricTests(unittest.TestCase):
    def test_binary_metric(self):
        metric = BinaryMetric()
        metric.record(False)
        metric.record(True)
        self.assertEqual(metric.attempts, 2)
        self.assertEqual(metric.successes, 1)
        self.assertEqual(metric.rate, 0.5)
        self.assertEqual(security_report(example=metric)["example"]["rate"], 0.5)


if __name__ == "__main__":
    unittest.main()

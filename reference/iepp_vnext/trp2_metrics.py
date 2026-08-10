"""Metric helpers for TRP 2.0 reports."""

from dataclasses import dataclass


@dataclass
class BinaryMetric:
    attempts: int = 0
    successes: int = 0

    def record(self, success: bool) -> None:
        self.attempts += 1
        self.successes += int(success)

    @property
    def rate(self) -> float:
        return self.successes / self.attempts if self.attempts else 0.0

    def as_dict(self) -> dict:
        return {
            "attempts": self.attempts,
            "successes": self.successes,
            "rate": self.rate,
        }


def security_report(**metrics: BinaryMetric) -> dict:
    return {name: metric.as_dict() for name, metric in metrics.items()}

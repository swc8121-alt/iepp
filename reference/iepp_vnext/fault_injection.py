"""Network delivery fault experiments for ordered IEPP evidence."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import random
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import AtomicRegistry, ChallengeAuthority, Prover


def setup():
    key, initial = Ed25519PrivateKey.generate(), sha256(b"fault-initial").digest()
    ca = ChallengeAuthority()
    registry = AtomicRegistry("fault-registry", ca)
    registry.enroll("entity", "domain", initial, "key", key.public_key(), {"fault.entropy"})
    return Prover("entity", "domain", "key", key, initial), registry, ca


def run(steps: int = 2_000) -> dict:
    prover, registry, ca = setup()
    evidence = []
    for tick in range(1, steps + 1):
        challenge = ca.issue("entity", "domain", now=tick, ttl=steps * 3,
                             nonce=sha256(f"c-{tick}".encode()).digest())
        evidence.append(prover.transition(challenge, sha256(f"e-{tick}".encode()).digest(),
                                          "fault.entropy", b"runtime"))

    order = list(range(steps))
    random.Random(8121).shuffle(order)
    shuffled = [evidence[index] for index in order]
    outcomes = Counter()
    pending = {}
    # First arrival is arbitrarily reordered. Future-counter items are buffered
    # by the application after the protocol rejects them as gaps.
    for item in shuffled:
        ok, reason = registry.verify_and_advance(item, now=steps + 1)
        outcomes[reason] += 1
        if not ok and reason == "COUNTER_GAP":
            pending[item.counter] = item
    retry_count = 0
    # The application retries buffered evidence only when its predecessor has
    # become canonical, avoiding an O(n^2) blind retry storm.
    while registry.enrollments["entity"].counter < steps:
        next_counter = registry.enrollments["entity"].counter + 1
        item = pending.pop(next_counter)
        ok, reason = registry.verify_and_advance(item, now=steps + 1)
        outcomes[reason] += 1
        retry_count += 1
        if not ok:
            raise RuntimeError((next_counter, reason))

    duplicate_outcomes = Counter()
    for item in evidence:
        duplicate_outcomes[registry.verify_and_advance(item, now=steps + 1)[1]] += 1

    # Delayed evidence with a short TTL is rejected even when otherwise next.
    delayed_prover, delayed_registry, delayed_ca = setup()
    challenge = delayed_ca.issue("entity", "domain", now=1, ttl=1)
    delayed = delayed_prover.transition(challenge, b"entropy", "fault.entropy", b"runtime")
    delayed_result = delayed_registry.verify_and_advance(delayed, now=3)

    return {"schema": "iepp-network-fault-injection-v1", "steps": steps,
            "shuffled_delivery": {"eventual_counter": registry.enrollments["entity"].counter,
                                  "buffered_retries": retry_count,
                                  "outcomes": dict(sorted(outcomes.items()))},
            "duplicate_redelivery": dict(sorted(duplicate_outcomes.items())),
            "expired_delay": list(delayed_result),
            "note": "Application retry policy is distinct from protocol acceptance."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=2_000)
    parser.add_argument("--output", type=Path, default=Path("results/fault_injection_v1.json"))
    args = parser.parse_args()
    result = run(args.steps)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))

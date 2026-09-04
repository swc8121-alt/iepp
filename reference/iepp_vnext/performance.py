from __future__ import annotations

import argparse
from hashlib import sha256
import json
import platform
from pathlib import Path
import sys
from time import perf_counter_ns

import cryptography
import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import AtomicRegistry, ChallengeAuthority, Prover


def stats(samples_ns: list[int]) -> dict:
    values = np.asarray(samples_ns, dtype=np.float64) / 1_000_000
    return {"mean_ms": round(float(values.mean()), 6), "p50_ms": round(float(np.percentile(values, 50)), 6),
            "p95_ms": round(float(np.percentile(values, 95)), 6), "p99_ms": round(float(np.percentile(values, 99)), 6)}


def run(iterations: int = 10_000) -> dict:
    key = Ed25519PrivateKey.generate()
    initial = sha256(b"perf-initial").digest()
    ca = ChallengeAuthority()
    registry = AtomicRegistry("perf-registry", ca)
    registry.enroll("entity", "domain", initial, "key", key.public_key(), {"perf.entropy"})
    prover = Prover("entity", "domain", "key", key, initial)
    issue_times, prove_times, verify_times = [], [], []
    for tick in range(1, iterations + 1):
        start = perf_counter_ns()
        challenge = ca.issue("entity", "domain", now=tick, ttl=5,
                             nonce=sha256(f"challenge-{tick}".encode()).digest())
        issue_times.append(perf_counter_ns() - start)
        start = perf_counter_ns()
        evidence = prover.transition(challenge, sha256(f"entropy-{tick}".encode()).digest(),
                                     "perf.entropy", b"runtime")
        prove_times.append(perf_counter_ns() - start)
        start = perf_counter_ns()
        accepted = registry.verify_and_advance(evidence, tick)
        verify_times.append(perf_counter_ns() - start)
        if not accepted[0]:
            raise RuntimeError(accepted)
    start = perf_counter_ns()
    audit_valid = registry.verify_audit_chain()
    audit_ms = (perf_counter_ns() - start) / 1_000_000
    checkpoint_samples = []
    for _ in range(1_000):
        start = perf_counter_ns()
        registry.checkpoint("entity")
        checkpoint_samples.append(perf_counter_ns() - start)
    return {"schema": "iepp-vnext-performance-v1", "iterations": iterations,
            "challenge_issue": stats(issue_times), "prover_sign_transition": stats(prove_times),
            "registry_verify_advance": stats(verify_times), "checkpoint_sign": stats(checkpoint_samples),
            "audit_verify": {"events": len(registry.audit), "valid": audit_valid, "total_ms": round(audit_ms, 6)},
            "environment": {"python": platform.python_version(), "platform": platform.platform(),
                            "cryptography": cryptography.__version__},
            "warning": "In-memory single-process host measurement; excludes network and durable storage."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument("--output", type=Path, default=Path("results/performance_v1.json"))
    args = parser.parse_args()
    result = run(args.iterations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))

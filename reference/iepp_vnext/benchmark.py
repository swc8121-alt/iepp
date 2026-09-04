from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import AtomicRegistry, ChallengeAuthority, Prover


def zero_success_upper_95(trials: int) -> float:
    return round(1 - 0.05 ** (1 / trials), 10) if trials else 1.0


def system(label: str = "main"):
    sid, domain = f"entity-{label}", "iepp.benchmark"
    key = Ed25519PrivateKey.generate()
    initial = sha256(f"initial-{label}".encode()).digest()
    ca = ChallengeAuthority()
    registry = AtomicRegistry(f"registry-{label}", ca)
    registry.enroll(sid, domain, initial, "key-1", key.public_key(), {"benchmark.entropy"})
    return Prover(sid, domain, "key-1", key, initial), registry, ca


def run(valid_steps: int = 50_000, attack_trials: int = 10_000, fork_races: int = 1_000) -> dict:
    prover, registry, ca = system()
    initial_clone = prover.clone()
    last_evidence = None
    start = perf_counter()
    for tick in range(1, valid_steps + 1):
        challenge = ca.issue(prover.sid, prover.domain, now=tick, ttl=5,
                             nonce=sha256(f"challenge-{tick}".encode()).digest())
        last_evidence = prover.transition(challenge, sha256(f"entropy-{tick}".encode()).digest(),
                                          "benchmark.entropy", sha256(f"runtime-{tick}".encode()).digest())
        ok, reason = registry.verify_and_advance(last_evidence, tick)
        if not ok:
            raise RuntimeError((tick, reason))
    valid_seconds = perf_counter() - start

    attacks = Counter()
    for _ in range(attack_trials):
        attacks[registry.verify_and_advance(last_evidence, valid_steps)[1]] += 1

    for trial in range(attack_trials):
        challenge = ca.issue(prover.sid, prover.domain, now=valid_steps + 1, ttl=10,
                             nonce=sha256(f"rollback-{trial}".encode()).digest())
        evidence = initial_clone.clone().transition(challenge, f"rbe-{trial}".encode(),
                                                    "benchmark.entropy", b"runtime")
        attacks[registry.verify_and_advance(evidence, valid_steps + 2)[1]] += 1

    current = prover.clone()
    for trial in range(attack_trials):
        challenge = ca.issue(prover.sid, prover.domain, now=valid_steps + 1, ttl=10,
                             nonce=sha256(f"mutation-{trial}".encode()).digest())
        evidence = current.clone().transition(challenge, f"me-{trial}".encode(),
                                              "benchmark.entropy", b"runtime")
        mutated = replace(evidence, runtime_commitment=sha256(f"tampered-{trial}".encode()).digest())
        attacks[registry.verify_and_advance(mutated, valid_steps + 2)[1]] += 1

    # A persistent executor creates real concurrent compare-and-swap pressure.
    fork_prover, fork_registry, fork_ca = system("fork")
    fork_outcomes = Counter()
    with ThreadPoolExecutor(max_workers=2) as pool:
        for tick in range(1, fork_races + 1):
            left, right = fork_prover.clone(), fork_prover.clone()
            cl = fork_ca.issue(left.sid, left.domain, now=tick, ttl=5,
                               nonce=sha256(f"left-{tick}".encode()).digest())
            cr = fork_ca.issue(right.sid, right.domain, now=tick, ttl=5,
                               nonce=sha256(f"right-{tick}".encode()).digest())
            el = left.transition(cl, f"left-e-{tick}".encode(), "benchmark.entropy", b"r")
            er = right.transition(cr, f"right-e-{tick}".encode(), "benchmark.entropy", b"r")
            futures = [pool.submit(fork_registry.verify_and_advance, el, tick),
                       pool.submit(fork_registry.verify_and_advance, er, tick)]
            results = [future.result() for future in futures]
            fork_outcomes["accepted"] += sum(int(ok) for ok, _ in results)
            fork_outcomes["rejected"] += sum(int(not ok) for ok, _ in results)
            fork_outcomes["double_accept"] += int(sum(int(ok) for ok, _ in results) == 2)
            fork_prover = left if results[0][0] else right

    attack_successes = sum(count for reason, count in attacks.items() if reason == "CONTINUITY_VALID")
    return {
        "schema": "iepp-vnext-core-benchmark-v1",
        "valid_chain": {"steps": valid_steps, "accepted": valid_steps,
                        "seconds": round(valid_seconds, 6),
                        "transitions_per_second": round(valid_steps / valid_seconds, 3),
                        "final_counter": registry.enrollments[prover.sid].counter,
                        "audit_chain_valid": registry.verify_audit_chain()},
        "attacks": {"trials_each": attack_trials, "outcomes": dict(sorted(attacks.items())),
                    "continuity_false_accepts": attack_successes,
                    "zero_false_accept_upper_95_per_attack": zero_success_upper_95(attack_trials)},
        "fork_races": {"races": fork_races, **dict(fork_outcomes),
                       "double_accept_upper_95": zero_success_upper_95(fork_races)},
        "interpretation": "Finite empirical results are not a cryptographic proof; assumptions are defined in the core model.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--valid-steps", type=int, default=50_000)
    parser.add_argument("--attack-trials", type=int, default=10_000)
    parser.add_argument("--fork-races", type=int, default=1_000)
    parser.add_argument("--output", type=Path, default=Path("results/core_benchmark_v1.json"))
    args = parser.parse_args()
    result = run(args.valid_steps, args.attack_trials, args.fork_races)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))

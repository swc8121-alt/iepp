# TRP 2.0 benchmark results

The executable model is `trp2_benchmark.py`. Run:

```bash
cd reference/iepp_vnext
python trp2_benchmark.py
```

The regression suite can be run with the repository's Python test runner.

## Required baseline

For the bounded model, the expected baseline is:

| Metric | Expected |
|---|---:|
| replay accept rate | 0.0 |
| rollback/stale predecessor accept rate | 0.0 |
| wrong-key forgery accept rate | 0.0 |
| dual canonical accept rate in a fork race | 0.0 |
| key + current-state boundary accept rate | 1.0 |

The final row is intentionally a **negative/boundary control**. It prevents the benchmark from turning an L1 limitation into an unsupported claim. If the attacker possesses current signing authority and current state, the bounded software model permits the attacker to win a canonical race. Stronger claims require stronger evidence levels and assumptions.

These numbers are invariant checks in a bounded executable model, not empirical proof that every implementation or
deployment is secure. Separate actual-core tests cover in-memory concurrency. SQLite component tests cover durable
CAS behavior, and the v0.2.1 integrated registry has deterministic F00–F12 transaction tests. High-repetition
multiprocess termination, real VM snapshots, storage-device faults, entropy degradation, attestation, split-view
registries, and physical evidence still require separate evaluation.

# IEPP Core Validation v0.2.1

Status: reproducible L1 software experiment; not a production security claim  
Date: 2026-08-09

## Controlling result

The reference implementation supports a narrow, registry-relative claim:

> Given an enrolled authentication key, the current canonical head, a fresh single-use challenge, an allowed
> entropy-source profile, and an atomic registry update, the verifier rejects replay, rollback, field substitution,
> and losing non-canonical forks as the next canonical continuation.

The implementation uses Ed25519-signed transition evidence, length-prefixed domain-separated hashing, entity and
domain-bound challenges, monotonic counters, an atomic single-successor rule, hash-chained audit events, signed
checkpoints, and dual-signature key migration.

## Reproduction

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s reference/iepp_vnext/tests -v
python reference/iepp_vnext/benchmark.py
python reference/iepp_vnext/negative_boundaries.py
python reference/iepp_vnext/fault_injection.py
python reference/iepp_vnext/bounded_model.py
python reference/iepp_vnext/performance.py
```

## Results

| Test | Result |
|---|---:|
| Core and durable-store unit tests | 14 passed |
| Valid sequential transitions | 50,000 / 50,000 accepted |
| Exact replay false accepts | 0 / 10,000 |
| Rollback or losing-fork false accepts | 0 / 10,000 |
| Signed-field substitution false accepts | 0 / 10,000 |
| Concurrent fork races | 1,000 |
| Double acceptance in fork races | 0 / 1,000 |
| Shuffled network delivery | 2,000 eventually accepted with ordered buffering/retry |
| Duplicate redelivery | 2,000 / 2,000 rejected as replay |
| Bounded abstract states explored | 1,063,623 |
| Bounded abstract transitions explored | 2,319,131 |
| Bounded invariant violations | 0 |
| Integrated durable-registry fault cases | F00–F12 deterministic coverage passed |

With zero observed false accepts in 10,000 trials, the finite-sample 95% upper bound is approximately 0.02995% per
tested attack class. With zero double accepts in 1,000 races, the corresponding upper bound is approximately 0.2991%.
These are statistical observations, not cryptographic proofs.

## Performance

Measured on the recorded single-process Linux host with an in-memory registry:

| Operation | Mean | p95 |
|---|---:|---:|
| Challenge issue | 0.0030 ms | 0.0038 ms |
| Prover transition and Ed25519 signature | 0.0430 ms | 0.0568 ms |
| Registry verify and advance | 0.1189 ms | 0.1547 ms |
| Signed checkpoint | 0.0344 ms | 0.0349 ms |

The 50,000-step end-to-end loop processed about 6,050 transitions per second. Network, consensus, durable database,
and hardware-attestation latency are excluded.

## Durable registry evidence

The SQLite WAL/FULL-synchronous compare-and-swap component passed:

- canonical-head persistence across close and reopen;
- exactly one commit from two concurrent successor attempts;
- rollback of both evidence and head changes after an injected pre-update failure.

It is a tested storage component, not yet a complete production registry integration.

The v0.2.1 `DurableRegistry` additionally places challenge consumption, evidence insertion, canonical-head and
entropy-health updates, the audit event, and the global audit root inside one `BEGIN IMMEDIATE` transaction. Its
deterministic F00–F12 suite covers every pre-commit boundary, commit-response loss with `ALREADY_COMMITTED`, a
two-connection race, checkpoint regeneration, the required negative result for an internally consistent old
snapshot, and fail-closed handling of database corruption. High-repetition multiprocess kill and physical storage
fault campaigns remain open and must not be inferred from these deterministic tests.

## Required negative results

### Predictable entropy is accepted

One thousand unique but fully predictable counter-derived entropy values were accepted when labeled as an allowed
source. A commitment can detect immediate repetition; it cannot prove unpredictability or source integrity.

### Full key and state compromise wins by race

A clone holding the current state and valid signing key was accepted when submitted first. The later legitimate
branch was rejected as a losing fork. IEPP does not infer a metaphysical original from two equally authorized copies.

### Isolated registries can split

Two isolated registry views each accepted a different successor. Comparing signed checkpoints detected the conflict.
Gossip, quorum, transparency logging, or external anchoring is required to expose equivocation.

### Lost registry state reauthorizes stale lineage

A registry reinitialized from genesis accepted a stale branch. Durable transactional state and anchored recovery
checkpoints are mandatory.

## Interpretation

Runtime entropy contributes fork divergence but does not choose the canonical branch. Canonicality comes from the
registry and policy. Claims must identify their evidence level:

- L1: software key/state, declared software entropy, single registry;
- L2: protected runtime and platform attestation;
- L3: witnessed or quorum registry;
- L4: evaluated physical binding.

This v0.2 implementation and its results are L1 unless a test explicitly states otherwise.

## Remaining work

- run high-repetition multiprocess termination and storage-fault campaigns against the integrated transaction;
- implement and test multi-registry checkpoint gossip/quorum;
- inject process crashes, disk faults, packet loss, partitions, and recovery events;
- define TPM/TEE/PUF evidence profiles;
- perform unbounded formal analysis with an appropriate specification tool;
- obtain independent cryptographic and distributed-systems review.

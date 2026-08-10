# TRP 2.0 Adversarial Validation Plan v0.1

Status: working test plan

This plan converts the TRP 2.0 security model into falsifiable tests. A failure is evidence against the evaluated implementation/profile; a pass is not a universal proof.

## Test matrix

| ID | Attack | Attacker class | Success condition | Expected |
|---|---|---|---|---|
| T01 | exact replay | A0 | consumed evidence advances head | reject |
| T02 | challenge substitution | A0/A1 | evidence for C1 accepted for C2 | reject |
| T03 | wrong-key forgery | A1 | unauthenticated clone advances head | reject |
| T04 | stale predecessor | A1/A2 | old head replaces current head | reject |
| T05 | simultaneous fork | A3 | two successors canonical in one view | at most one |
| T06 | VM/process snapshot | A3 | snapshot silently replaces live branch after competing advance | reject/conflict |
| T07 | partial-state leakage | A2 | leakage enables unauthorized canonical continuation | measure/bound |
| T08 | entropy freeze/repeat | A4 | deployment retains unsupported strong evidence claim | detect/downgrade |
| T09 | entropy prediction | A4 | prediction alone bypasses auth/predecessor policy | reject |
| T10 | key+state compromise | A5 | attacker wins race from current head | expected boundary at L1 |
| T11 | registry split view | A6 | conflicting heads remain undetectable under claimed L3 | detect |
| T12 | registry rollback/restart | A6 | durable store reauthorizes stale branch | reject |

## Phases

### Phase A — bounded executable model
Run deterministic protocol-invariant tests at high trial counts. This phase validates replay, predecessor, authentication and single-successor invariants and includes the A5 boundary control.

### Phase B — reference implementation integration
Drive the actual `iepp_vnext` registry/prover APIs rather than a reduced model. Inject malformed evidence, challenge reuse, concurrent successors and durable-store faults.

### Phase C — concurrency and crash consistency
Use parallel workers and forced termination around challenge consumption and canonical-head updates. Measure any dual acceptance, lost update, stale reauthorization or inconsistent audit root.

### Phase D — real snapshot environment
Clone a running VM/container/process state at a declared boundary. Resume both copies, issue controlled challenges and measure divergence, race behavior and canonical acceptance. Report divergence separately from canonical security.

### Phase E — evidence-level tests
For L2+, test protected-key/state behavior and attestation failure. For L3, test split-view detection latency and checkpoint comparison. L4 claims require evaluated hardware/physical experiments and are not inferred from software results.

## Reporting

For every test record: commit SHA, platform, Python/runtime versions, evidence level, entropy source/profile, attacker view, trial count, attack budget, acceptance counts, confidence interval where statistical, timing, failure traces and negative controls.

No report may convert `0 successes in N trials` into a proof of zero attack probability. Protocol invariants and cryptographic/platform assumptions must be reported separately from empirical attack results.

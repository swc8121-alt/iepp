# IEPP entropy comparison — 2026-09-11

Evidence level: L1, single-process software. Base: `fe9b86e0f34ec34155a70c36a99714440bb09947`.
This is a finite local experiment, not a security proof or independent reproduction.

## Question and setup

Which observed outcomes depend on prover entropy, and which persist in the existing signed-state no-entropy baseline?

The harness compares OS random bytes, one fixed value, two alternating values, publicly predictable per-step values, and omitted entropy fields. All share the same initial-state convention, challenge authority, registered signing credential, and fresh challenge schedule. Two cloned provers have the same current key and state. A single in-memory registry selects a successor. Each ordering case uses 1,000 fresh fixtures per mode: original first, clone first, and two barrier-synchronized worker threads. Thread submission order alternates to expose scheduling bias; winner proportions are not attacker-success probabilities.

The baseline is the existing `entropy_ablation.py`, not a feature-identical implementation: it has narrower validation and no matching audit/checkpoint functionality. This comparison supports conclusions about the tested replay and successor-acceptance paths only. Fresh verifier challenges remain present even in the no-entropy mode.

## Results

| Observation | Result | Interpretation |
|---|---|---|
| Concurrent callers, each mode | 0 double accepts / 1,000, 0 zero accepts | Single-registry successor serialization held |
| Original submitted and verified first, each mode | Original accepted 1,000/1,000 | Ordered control |
| Full key/state clone verified first, each mode | Clone accepted 1,000/1,000 | No original-only protection under full current credential/state compromise |
| Replay, each mode | 0 false accepts / 1,000 | Tested replay control held |
| Unsigned state tampering, each mode | 0 false accepts / 1,000 | Signature control held for this mutation |
| Same challenge and parent, independent OS bytes | Different successor states 1,000/1,000 | Prover entropy adds divergence with otherwise identical inputs |
| Same challenge and parent, other modes | Different successor states 0/1,000 | Deterministic identical inputs did not separate the clones |
| Fixed entropy over successive accepted states | First accepted, second rejected: ENTROPY_REPEATED | Immediate repetition policy works |
| Alternating two values | Four consecutive transitions accepted | Immediate repetition policy is not a history-wide reuse detector |
| Publicly predictable changing values | Four consecutive transitions accepted | Commitment change is not evidence of unpredictability |
| Disallowed source label, four entropy modes | Rejected | Source allowlist check works; allowed labels do not attest a real source |

The existing ablation runner was also corrected from sequential calls to two barrier-synchronized threads. The new v2 run reports 0 replay false accepts / 10,000 and 0 double accepts / 1,000. Historical v1 results are preserved; its `fork_races` label described competing candidates checked sequentially, not actual concurrent callers.

## What this changes

The observed added role of independently sampled prover entropy is same-input branch divergence and policy/audit information. The tested canonical serialization does not depend on those fields. Divergence does not identify an original, and low-quality changing entropy can satisfy the current L1 checks. These are explicit boundaries, not newly demonstrated production guarantees.

The experiment does not measure VM snapshot/restore, multiple processes, network partitions, registry rollback, crash durability, protected key storage, physical entropy, entropy health-test certification, or L2 attestation. VM deployment alone would still not meet the specification's L2 requirements. No inference about practical attack success rates follows from the artificial ordered controls or local scheduler.

## Reproduce

From repository root, with repository dependencies installed:

```bash
python reference/iepp_vnext/entropy_comparison.py --trials 1000 --output reference/iepp_vnext/results/entropy_comparison_v1.json
python reference/iepp_vnext/entropy_ablation.py --replay-trials 10000 --fork-races 1000 --output reference/iepp_vnext/results/entropy_ablation_concurrent_v2.json
python -m unittest discover -s reference/iepp_vnext/tests -v
```

The comparison JSON records source hashes, Python/platform, base commit and counts. Keys and raw runtime entropy are not logged. Existing unit suite: 15 tests passed. OS bytes and scheduling vary between executions.

## Next boundary to test

Run the same ordered clone controls through separate VM processes with captured restore points and registry logs. Keep this labeled L1 unless protected key/state and platform attestation are actually verified. A later controlled comparison can evaluate which additional protection prevents the full-state clone from exercising the signing credential.

## 한국어 해석

- 엔트로피가 달라지면 같은 출발점의 분기가 달라질 수 있지만, 그것만으로 원본을 식별하지는 못했습니다.
- 이중 승인 방지는 이번 조건에서 엔트로피 필드를 제거해도 유지됐습니다.
- 현재 키와 상태를 복사한 복제본이 먼저 검증되면 승인됐습니다.
- 고정값의 즉시 반복은 거부했지만, 두 값의 교대 반복과 예측 가능한 변화는 통과했습니다. 엔트로피 품질 보장으로 해석할 수 없습니다.
- 실제 VM 복원·하드웨어 보호 실험은 이번에 수행하지 않았습니다.

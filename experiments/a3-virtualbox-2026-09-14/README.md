# A3 VirtualBox observations — 14 September 2026

**Evidence level: L1, one online registry and a cooperative policy gate. Partial A3 matrix.**

Four two-branch trials each recorded exactly one accepted successor and one simulated protected action. A separate submission after an actual VM rollback was rejected. These are five cases / nine client records, not five fork races. The shared-challenge serial trial is also corroborated by the uploaded server log.

[한국어 상세 보고서](REPORT_KO.md) · [Next-stage plan / 다음 단계](NEXT_STAGE_KO.md) · [File manifest](manifest.json)

## Observed cases

| Trial | Setup | Winner | Rejection |
|---|---|---|---|
| S1-0001 | Distinct fresh challenges; A then B | A | B: ROLLBACK_OR_LOSING_FORK |
| S1-0002 | Distinct fresh challenges; B then A | B | A: ROLLBACK_OR_LOSING_FORK |
| S1-0003 | Distinct fresh challenges; common scheduled submission time | A | B: ROLLBACK_OR_LOSING_FORK |
| RESTORE-0001 | Actual rollback of Node1; new challenge; registry retained prior head | None | ROLLBACK_OR_LOSING_FORK |
| S2-0001 | Same challenge included in a cold snapshot and clone; A then B | A | B: CHALLENGE_USED |

All nine client records report successful transport and no transport error. Accepted records say `EXECUTED_SIMULATED`; rejected records say `BLOCKED`. No real external protected action was measured.

## Evidence and provenance

- [First three trials: six client records](logs/a3-first-three-results.jsonl).
- [Actual rollback: one client record](logs/result-restore-0001.jsonl).
- [Shared challenge: two client records](logs/combined-S2-0001.jsonl).
- [Shared-challenge server log: two challenge issuances and two decisions](logs/registry-events.jsonl).
- Runner source pinned to [a8a5ef374afb18f2c8a7014641fa9fad33fdb26d](https://github.com/swc8121-alt/iepp/tree/a8a5ef374afb18f2c8a7014641fa9fad33fdb26d/reference/iepp_vnext), the head of PR #9 at publication. This results-only addition does not merge that implementation.
- Operator screenshots showed the same Git commit and clean working trees on the VM clients. Logs retain `iepp_source_revision: UNKNOWN`; screenshots supplement rather than replace it. The screenshots are not included in this public package.
- Reported platform: VirtualBox 7.2.16 on Windows 10; Ubuntu 24.04.5 guests; Python 3.12.3 clients. Windows registry runtime was reported as Python 3.13.15. These are operator records, not independently attested inventories.
- Exact Windows server source hashes and server logs for the earlier trials have not been supplied in this package.

The initial VM snapshot was named `S1_AFTER_P0_BEFORE_CHALLENGE`. Later S1 trials used new state files in existing VMs, not a fresh hypervisor restore for every trial. The shared stage used Node3's cold `S2_AFTER_CHALLENGE_04B` snapshot to clone Node4. It did not explicitly restore a VM after consumption of that shared challenge. The boolean `challenge_issued_before_restore` is derived from snapshot metadata and does not independently prove a hypervisor restore.

## Shared-challenge cross-check

Both client records have the same public-key fingerprint, predecessor and challenge ID, with different candidate successors. Matching server decisions agree on evidence ID, candidate successor, predecessor, before/after head, acceptance and reason. A was accepted at 01:44:53.189818 UTC; B was rejected at 01:45:01.235281 UTC, both before the 02:24:41 UTC expiration. The decision gap is 8.045463 seconds. B was rejected for a used challenge, not expiration. Final head is A's successor and counter remains 1.

The server log also preserves an earlier challenge issuance that was not used in these submitted results. A failed 14,400-second TTL request was corrected to 3,600 seconds during preparation; it is not counted as a protocol transition trial.

## Interpretation limits

- This is registry-relative continuation, not intrinsic or physical original identification. B won when submitted first.
- S1-0003's cross-VM send-time difference of 43,134 ns does not establish server-side overlap. S2-0001 was serial. No controlled-race completion claim is made.
- `entropy_health_status: NOT_EVALUATED` provides no entropy quality or unpredictability claim.
- `signature_present: true` is not independent cryptographic re-verification of the signed candidate.
- This does not validate hardware-backed L2–L4, malicious hypervisors, partitioned or rolled-back registries, durable challenge reuse protection across server restart, or bypass of the cooperative gate.
- Nine client records are not a statistical reliability or production-security guarantee. No A3 completion percentage is assigned.
- Issue [#6](https://github.com/swc8121-alt/iepp/issues/6) additionally asks for a baseline and snapshots after an accepted transition. Those conditions are not established by this package's enrolled-P0 snapshot cases.

Checks performed: two distinct branches and one acceptance per paired trial; common key/predecessor; correct distinct/shared challenge relation; winning final head; consistent simulated-action labels; no transport errors; rollback head unchanged; shared server/client field agreement. Hashes identify the uploaded bytes; they are not third-party timestamps or attestations. The files contain result metadata and commitments, not the cloneable private-key snapshot, raw entropy, database or private backup.

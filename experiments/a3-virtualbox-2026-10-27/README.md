# A3 two-VM VirtualBox evidence — 27 October 2026

**Observation level: `TWO_VM_OBSERVED`. Claim level: `L1_REGISTRY_RELATIVE_CONTINUATION`.**

This package records a fixed 22-trial snapshot/restore matrix run against two distinct Ubuntu virtual machines and a separate HTTP registry process. Every trial satisfied its scenario predicate. The result strengthens the September partial A3 observations with repeatable VM restores, both serial orderings, server-observed request overlap, shared-challenge races, and a post-consumption restore case.

It does not establish physical or historical runtime originality, clone resistance, hardware identity, guest attestation, distributed consensus, or an independent security benefit from entropy.

[한국어 증거 검토](EVIDENCE_REVIEW_KO.md) · [Runner instructions](runner/README_KO.md) · [SHA-256 manifest](SHA256SUMS.txt)

## Result summary

| Metric | Observed result |
|---|---:|
| Trials | 22 / 22 passed |
| Registry decision events | 42 |
| Controlled races | 8 |
| Server-processing overlap | 8 / 8 races |
| Exactly one accepted successor | 8 / 8 races |
| Overlapping CAS critical intervals | 0 / 8 races |
| Successful snapshot restores | 46 |
| Successful VM starts / shutdowns | 48 / 48 |

The eight controlled races used a two-participant server barrier. Their server-processing intervals overlapped, while the compare-and-swap intervals did not. This is the expected distinction: competing requests were present concurrently at the registry, and the atomic decision interval remained serialized.

## Scenario matrix

| Scenario | Purpose | Result |
|---|---|---:|
| `r1_baseline_continue` | Single valid continuation | 2 / 2 |
| `r2_fresh_order_ab` | Distinct challenges, A then B | 3 / 3 |
| `r3_fresh_order_ba` | Distinct challenges, B then A | 3 / 3 |
| `r4_controlled_race_fresh` | Controlled race with distinct challenges | 4 / 4 |
| `r5_shared_challenge_ab` | Shared challenge, A then B | 2 / 2 |
| `r6_shared_challenge_ba` | Shared challenge, B then A | 2 / 2 |
| `r7_controlled_race_shared_challenge` | Controlled race with one shared challenge | 4 / 4 |
| `r8_consumed_before_restore` | Restore after registry consumption | 2 / 2 |

For distinct fresh challenges, the first accepted candidate advanced the head and the competing candidate was rejected as `FORK_CONFLICT`. For a shared challenge, the first use was accepted and the second was rejected as `CHALLENGE_REPLAY`. The result is registry-relative: the winner follows arrival and policy order, not a claim of metaphysical or physical originality.

## Environment recorded by the runner

- Windows 10.0.19045 x64 host
- Oracle VM VirtualBox 7.2.16r174877
- two distinct Ubuntu 24.04 LTS VMs with different snapshot UUIDs
- Node.js v22.23.4 in both guests
- separate Node.js registry process over HTTP/1.1 on a localhost ephemeral port
- runner version 0.2.4.2

The VM display names are stored only as SHA-256 hashes. Password-file arguments are recorded as `<redacted>`. The evidence does retain low-sensitivity operational metadata such as snapshot UUIDs, software versions, the guest account name, and a generic Windows user path.

## Protocol boundary

The harness is intentionally narrower than the authenticated Python reference profile. Guest candidates contain an unkeyed `transition_digest`; the registry checks lineage, challenge use, digest consistency, policy revision, credential label, predecessor, and counter before an atomic head update. It does **not** verify an Ed25519 guest signature or attest a protected VM identity.

Accordingly, this package supports the following statement:

> Two distinct snapshot-restored VM producers submitted competing continuation candidates to one HTTP registry, which accepted at most one successor per predecessor and enforced single use of a challenge in the tested 22-trial matrix.

It does not support claims that the accepted producer was the original runtime, that a clone was prevented, that the guest channel was cryptographically authenticated, or that the result survives a malicious or partitioned registry.

## Evidence files

- `evidence-vm-20261027-140157.zip` — immutable original evidence archive
- `SHA256SUMS.txt` — whole-archive digest
- `EVIDENCE_REVIEW_KO.md` — separate recomputation record and claim limits
- `runner/` — exact v0.2.4.2 source whose five source hashes match `summary.json`

The archive SHA-256 is:

```text
1918b5e44f66de5a0e31db67eb0a5bd35911cea0ec7fd5a2ccc720bd26779f54
```

The trial evidence-chain head is:

```text
947895864ebc515e2a769029683919430fee33a3ff6c86f2f198a7c04f51fe29
```

## Offline verification

Extract the evidence archive, then run:

```bash
node runner/verify-bundle.mjs path/to/extracted-evidence-directory
```

Expected high-level output:

```json
{
  "ok": true,
  "verified_files": 4,
  "verified_trials": 22,
  "verified_registry_events": 42,
  "verified_races": 8,
  "observation_level": "TWO_VM_OBSERVED"
}
```

The verifier checks the four internally manifested files, the 22-entry evidence chain, registry candidate digests, unique request IDs, single accepted successor per predecessor, single first-use event per challenge, trial-to-event membership, race overlap and serialization conditions, summary counts, and the explicit claim boundary.

The internal hashes are not a digital signature or third-party timestamp. The repository commit and the published whole-archive digest bind the reviewed bytes, but independent reproduction remains necessary.

## Relationship to the September package

The [14 September package](../a3-virtualbox-2026-09-14/README.md) remains unchanged as historical evidence. It contained five cases and nine client records, with incomplete provenance and no server-observed controlled overlap. This package closes those specific matrix and provenance gaps for the new harness; it does not retroactively alter the earlier records or promote the evidence above L1.

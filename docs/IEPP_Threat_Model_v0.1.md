# IEPP Threat Model v0.1

Status: Working Draft

## 1. Security question

Can an adversary cause a verifier to accept a replayed, rolled-back, or non-canonical fork as the next valid continuation of an enrolled entity's canonical execution lineage?

This threat model separates empirical divergence, authenticated evidence, canonical selection, and host/platform trust. Immediate fork divergence is useful evidence, but it is not by itself proof that one branch is the original.

## 2. Protected assets

- integrity of the canonical commitment;
- freshness and single use of verifier challenges;
- authenticity and domain binding of transition evidence;
- confidentiality of protected state and raw entropy;
- auditability of forks, migration, recovery, and policy overrides;
- availability of verification and registry services.

## 3. Trust assumptions

Every evaluation must declare which assumptions hold:

1. The hash and authentication algorithms meet their stated security properties.
2. The verifier can generate fresh challenges.
3. The CLR can perform an atomic single-successor update or expose equivocation.
4. The prover's protected state cannot be modified without detection at the claimed evidence level.
5. Entropy meets the declared profile; no stronger physical claim is inferred from software entropy.
6. Enrollment, migration, and recovery policy are external governance inputs.

## 4. Adversaries

| Adversary | Capability | Required result | Current status |
|---|---|---|---|
| Network | Observe, delay, reorder, replay, substitute | Reject replay and substitution | Partially tested |
| Software clone | Copy application and visible configuration | Cannot silently advance canonical lineage | Partially tested |
| Snapshot | Copy VM memory and disk at step `t` | At most one successor accepted; conflict recorded | Real VM test required |
| Rollback | Restore an older prover state | Reject stale predecessor | Formal test required |
| Entropy | Bias, repeat, suppress, or predict entropy | Detect degradation or bound the claim | Minimum profile undefined |
| Host administrator | Inspect or modify process, RNG, clock, storage | Security limited by declared level | Not defended at L1 |
| Registry | Rewrite, race, or equivocate canonical state | Detect via append-only log, quorum, or anchor | Design required |
| Verifier | Reuse or maliciously choose challenges | Domain, freshness, and audit controls | Design required |
| Physical | Control device and physical entropy path | Hardware-dependent boundary | Future work |

## 5. Attack games

### 5.1 Replay

The adversary observes valid evidence for challenge `C1`, then presents it for a fresh challenge `C2` or after the original transition was accepted. Success means the verifier returns `CONTINUITY_VALID`.

Expected result: `CHALLENGE_INVALID` or `REPLAY_DETECTED`.

### 5.2 Rollback

After the registry accepts commitment `S[t]`, the adversary restores a prover to `S[t-k]` and attempts a new transition.

Success means the CLR replaces `S[t]` using evidence whose predecessor is not the current canonical commitment.

Expected result: `STALE_CANONICAL_STATE` or `ROLLBACK_DETECTED`.

### 5.3 Fork race

Two provers begin from the same accepted commitment and produce different successors. Success means both successors are accepted as canonical under the same single-successor policy and registry view.

Expected result: exactly one accepted successor; the other is `LINEAGE_FORKED`.

### 5.4 Challenge substitution

The adversary changes the challenge, verifier domain, entity identifier, counter, or time context in observed evidence.

Expected result: authentication or domain-binding failure.

### 5.5 Entropy degradation

The adversary freezes, repeats, biases, or replaces an entropy source. The objective is not to infer identity directly from randomness; it is to determine whether the implementation continues to claim an evidence level it no longer satisfies.

Expected result: `ENTROPY_TRUST_DEGRADED` or downgrade to an explicitly weaker profile.

### 5.6 Registry equivocation

A malicious or partitioned CLR presents different canonical heads to different verifiers.

Expected result: detectable split view through signed checkpoints, append-only transparency, quorum, or external anchoring. The mechanism is open design work in v0.1.

### 5.7 Authorized migration

The entity moves to a new runtime or hardware root. Success for an attacker means an unauthorized clone is accepted as a migration without satisfying policy.

Expected result: explicit migration evidence, old-root revocation or handoff, and an auditable boundary event.

## 6. Out of scope for L1

- fully malicious hypervisor with complete process and entropy control;
- physical extraction or replacement of all secrets and state;
- compromise of prover, verifier, registry, and policy authority at once;
- semantic identity, consciousness, personhood, or legal ownership;
- canonical selection without an external policy.

## 7. Reporting rules

Experimental reports must include:

- attacker knowledge and capabilities;
- exact success condition;
- evidence level and entropy source;
- number of trials and confidence bounds where appropriate;
- time to detection and performance cost;
- negative controls and failed hypotheses;
- distinction between empirical attack failure and a security proof.

The existing statistical clone-separation failure is a required negative result: output-distribution similarity did not identify the canonical clone. Canonical lineage verification, not statistical resemblance, is the governing mechanism for fork acceptance.

# Trajectory Reconstruction Problem (TRP) 2.0 — Security Model

Status: research working draft  
Scope: adversarial reconstruction of canonical IEPP execution-lineage continuity

## 1. Motivation

TRP 2.0 separates three claims that must not be conflated:

1. **Empirical divergence:** independently continued executions usually diverge.
2. **Protocol acceptance:** a verifier and canonical lineage registry (CLR) accept one authenticated, fresh successor under an explicit policy.
3. **Computational hardness:** an adversary cannot reconstruct or forge an accepted canonical continuation except with bounded advantage under declared assumptions.

Observed fork divergence or zero successes in finite experiments is evidence, not a proof of computational hardness.

## 2. State-transition model

For entity/session identifier `sid`, domain `domain`, counter `t`, previous state `S[t-1]`, fresh verifier challenge `C[t]`, runtime entropy `E[t]`, runtime measurement commitment `M[t]`, action/output commitment `A[t]`, and context `ctx[t]`:

```text
EC[t] = H("IEPP-Entropy-v1" || E[t])

S[t] = H(
  "IEPP-TRP2-State-v1" || sid || domain || t || S[t-1] ||
  C[t] || EC[t] || M[t] || A[t] || ctx[t]
)
```

The deployed core specification may encode these fields differently. TRP 2.0 requires unambiguous, length-prefixed, domain-separated encoding and authenticated binding of every verifier-relevant field.

## 3. TRP definition

**Trajectory Reconstruction Problem (TRP).** Given a canonical trajectory prefix and the information available under a declared leakage model, construct a future evidence sequence that is accepted as a canonical continuation even though the adversary is not executing the authorized canonical continuation required by the claimed evidence level and policy.

Let `View_A(k)` contain the public transcript through step `k`, public parameters, allowed side information, and any explicitly granted leakage. The adversary outputs candidate evidence `pi*` for one or more future transitions.

A TRP success occurs when:

```text
VerifyAndAdvance(CLR, pi*) = CONTINUITY_VALID
```

while the evidence violates the canonical-continuation condition defined by the active policy/evidence level.

This definition is deliberately policy-relative: cryptography alone does not determine metaphysical originality, consciousness, personhood, or canonicality without a selection policy.

## 4. Adversary advantage

For security parameter `lambda`, game `G`, evidence level `L`, and adversary `A`:

```text
Adv_TRP[A,G,L](lambda) = Pr[G(A, 1^lambda, L) = 1]
```

A future security theorem may claim negligible advantage only after the assumptions, leakage model, primitive reductions, registry semantics, and evidence-level guarantees are formalized. Until then, IEPP uses the term **TRP Hardness Conjecture**, not proven TRP hardness.

## 5. TRP security-game family

### TRP-CONT — continuation forgery

The adversary observes a valid prefix and attempts to create the next accepted canonical transition without satisfying the authorized continuation conditions.

Success: forged evidence becomes the new CLR head.

### TRP-FORK — fork impersonation

Two or more branches continue from the same accepted predecessor.

Success: more than one conflicting successor is accepted as canonical for the same predecessor under one single-successor registry view, or a losing branch is later accepted without an explicit audited policy transition.

### TRP-ROLLBACK — stale-state reconstruction

The adversary restores prover state from counter `t-k` after the CLR has advanced.

Success: stale-predecessor evidence advances the current canonical head.

### TRP-REPLAY — transcript reuse

The adversary reuses previously accepted evidence or binds it to a different challenge/session/domain.

Success: replayed or substituted evidence is accepted as a fresh continuation.

### TRP-SNAPSHOT — cloned-runtime race

The adversary copies all state available at the declared evidence level at step `t` and runs multiple descendants.

Success criterion depends on level. At L1, full theft of state and signing key is not claimed to be prevented; the protocol objective is at-most-one canonical successor per atomic CLR view plus conflict/audit evidence. Stronger clone-resistance requires protected runtime assumptions.

### TRP-RNG — entropy degradation/substitution

The adversary freezes, repeats, biases, predicts, or substitutes the declared entropy source.

Success: the implementation continues to assert an evidence level whose entropy requirements are no longer met, or entropy manipulation enables another TRP game beyond its stated bound.

Entropy uniqueness alone is not an identity proof.

### TRP-RACE — canonical registry race

The adversary schedules concurrent valid successors, delays messages, or exploits non-atomic updates.

Success: conflicting successors are simultaneously canonical under the same registry sequence/view.

### TRP-MIGRATE — unauthorized continuity transfer

The adversary attempts to move continuity to a new key/runtime/device without satisfying migration policy.

Success: the CLR accepts the new root as an authorized continuation without the required migration evidence.

### TRP-EQUIVOCATION — split-view registry

A malicious or partitioned registry exposes different canonical heads to isolated verifiers.

Success/detection must be stated separately. A single isolated verifier cannot generally detect a consistent split view. Detection requires signed checkpoints plus gossip, quorum, transparency logging, or an external anchor.

## 6. Leakage profiles

Every TRP result MUST state an explicit leakage profile. Suggested profiles:

- **P0 Public:** public transcript, challenges, identifiers, timing visible to a network observer.
- **P1 Application clone:** P0 plus application code/configuration and non-secret persistent data.
- **P2 Snapshot:** P1 plus a point-in-time copy of software-visible process/storage state.
- **P3 Key/state compromise:** current signing key and current software state compromised. L1 cannot promise clone prevention here; race containment, revocation, recovery, and audit become the relevant goals.
- **P4 Host control:** adversary controls OS/hypervisor, clocks, RNG plumbing, and storage. Claims require L2+ protected hardware/runtime assumptions.

Results from one profile MUST NOT be generalized to a stronger attacker.

## 7. Evidence-level interpretation

TRP claims inherit IEPP evidence levels:

- **L1 software:** continuity is registry-anchored and authenticated, but a fully compromised host/current key can impersonate the software entity.
- **L2 protected runtime:** key/state and selected measurements/entropy are hardware protected and attested.
- **L3 witnessed registry:** checkpoint gossip/quorum/transparency constrains registry equivocation.
- **L4 physical binding:** evaluated PUF/sensor/physical entropy and lifecycle controls may support stronger device-binding claims.

A TRP experiment MUST identify both leakage profile and evidence level.

## 8. TRP Hardness Conjecture

Informally, under a declared evidence level and leakage profile, if authentication remains unforgeable, hash commitments remain binding/preimage resistant as required, challenges are fresh, protected state/entropy assumptions hold, and the CLR enforces atomic single-successor semantics (or exposes equivocation), then an efficient adversary should not obtain non-negligible advantage in the applicable TRP games except for capabilities explicitly granted by that profile.

This is a research conjecture and decomposition target, not a completed reduction or theorem.

## 9. What TRP does not establish

TRP does not by itself prove:

- consciousness or persistent subjective identity;
- metaphysical originality;
- entropy source integrity from uniqueness alone;
- resistance to a fully compromised L1 host and signing key;
- global canonicality without a registry/selection policy;
- split-view detection without witness/gossip/anchor assumptions;
- computational hardness merely because finite attack trials recorded zero successes.

## 10. Required experimental matrix

A reproducible TRP 2.0 evaluation SHOULD include:

| Game | Positive path | Attack/negative control | Primary metric |
|---|---|---|---|
| CONT | valid sequential continuation | forged/tampered successor | false accept rate |
| FORK | one canonical successor | competing same-head successors | canonical winners per head |
| ROLLBACK | current predecessor | stale snapshot/predecessor | stale accept rate |
| REPLAY | fresh challenge/evidence | reused evidence/challenge substitution | replay accept rate |
| SNAPSHOT | controlled clone race | duplicated runtime state | double-canonical rate |
| RNG | healthy declared entropy | freeze/repeat/substitute | detection/downgrade rate |
| RACE | atomic concurrent updates | adversarial scheduling | double-commit rate |
| MIGRATE | authorized dual-bound migration | unauthorized key/runtime transfer | unauthorized migration rate |
| EQUIVOCATION | consistent checkpoints | conflicting signed checkpoints | detection rate/time |

Report trial count, attacker knowledge, success condition, confidence interval where meaningful, detection latency, performance cost, evidence level, leakage profile, and all negative results.

## 11. Interpretation of earlier IEPP experiments

Earlier immediate fork-divergence and attack-failure experiments remain useful empirical observations. They MUST NOT be described as proof that TRP is computationally hard. Statistical clone similarity/separation is likewise not the canonical-selection mechanism. The governing security mechanism is authenticated state evolution plus freshness and canonical registry semantics, with stronger claims conditional on higher evidence levels.

## 12. Research roadmap

1. Implement deterministic security-game harnesses for replay, rollback, fork, race, migration, entropy degradation, and snapshot models.
2. Add real VM/container snapshot and rollback experiments rather than only in-process simulation.
3. Define measurable entropy profiles and downgrade behavior.
4. Implement and test witnessed checkpoint equivocation detection for L3.
5. Separate empirical claims from reduction-based claims in papers, whitepapers, and website copy.
6. Attempt formal reductions for individual games rather than asserting a monolithic TRP proof.

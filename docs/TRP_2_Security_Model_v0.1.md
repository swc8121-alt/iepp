# TRP 2.0 — Canonical Continuation Security Model v0.1

Status: research working draft  
Applies to: IEPP Core Specification v0.2 and later

## 1. Purpose

The Trajectory Reconstruction Problem (TRP) is the security problem underlying IEPP continuity claims. TRP 2.0 narrows the claim from an informal assertion that a clone cannot reproduce an execution trajectory to a testable question:

> After observing or compromising an execution lineage up to a declared boundary, can an adversary cause the canonical registry to accept an unauthorized future continuation under the deployed evidence level and trust assumptions?

TRP does not identify metaphysical originality, consciousness, personhood, or a unique physical original. It is a protocol-relative continuation problem.

## 2. Objects

For entity `id`, let the accepted canonical history through step `t` be

```text
T[0:t] = (S[0], X[1], S[1], ..., X[t], S[t])
```

where `S[t]` is the canonical state commitment and `X[t]` is the authenticated transition evidence defined by the IEPP core specification. A transition may bind a verifier challenge, entropy commitment, runtime/attestation commitments, counter, predecessor, domain and signing key.

The canonical registry head is

```text
H_t = (id, counter=t, S[t], key_id, policy_state)
```

Canonicality is selected by registry/policy. Entropy may cause two executions to diverge but does not determine which branch is canonical.

## 3. Adversary view

At compromise boundary `t`, the experiment declares an adversary view `V_t`. It MUST state exactly which of the following are available:

- public transcript and accepted checkpoints;
- application/configuration copy;
- historical challenges and evidence;
- current or historical state commitments;
- partial internal state;
- full process or VM snapshot;
- signing key access;
- entropy-source observation, prediction, bias or control;
- verifier challenge influence;
- registry read/write, race or equivocation capability;
- runtime/attestation compromise.

A result without an explicit `V_t` is not a TRP security result.

## 4. Canonical Continuation Game

The challenger enrolls an entity and advances it to a canonical head `H_t`. The adversary receives the declared `V_t` and may interact according to the attack profile. A fresh continuation opportunity is then created under the protocol policy.

The adversary wins `CCG(t, q, profile)` if it causes an unauthorized candidate transition or sequence to be accepted as canonical without satisfying the authority and evidence conditions of the profile.

```text
Win = 1 iff
  RegistryAccept(candidate) = CONTINUITY_VALID
  and candidate is unauthorized under profile
```

The experiment reports

```text
Adv_CCG(A) = Pr[Win = 1]
```

with trial count, confidence interval when meaningful, attack budget `q`, evidence level, entropy profile, registry model and compromise boundary.

For multi-step continuation, also report the probability that an attacker maintains unauthorized canonical acceptance for `m` consecutive transitions.

## 5. Adversary hierarchy

TRP 2.0 uses capability classes rather than one universal clone attacker.

| Class | Minimum capability | Intended question |
|---|---|---|
| A0 Observer | public transcript | Can observation enable replay/forgery? |
| A1 Software Clone | code/configuration copy | Can a copied implementation silently continue the canonical lineage? |
| A2 Partial-State | selected runtime state leakage | How does bounded leakage change continuation advantage? |
| A3 Snapshot | process/VM state at `t` | Can two successors both become canonical or can the snapshot silently replace the live branch? |
| A4 Entropy-Influence | bias/repeat/predict selected entropy inputs | Does degraded freshness invalidate or downgrade the evidence claim? |
| A5 Key+State | current state plus signing key | Can the attacker race the legitimate prover? This is not prevented at L1 by TRP alone. |
| A6 Platform/Registry | host, verifier or registry compromise | Security depends on L2/L3 mechanisms and explicit trust assumptions. |

Results MUST NOT be generalized from a weaker class to a stronger class.

## 6. Required security properties

### 6.1 Replay resistance
Previously accepted evidence or evidence bound to another challenge/domain must not advance the canonical head.

### 6.2 Predecessor continuity
A candidate whose predecessor is not the current canonical head must not replace that head under the single-successor policy.

### 6.3 Fork serialization
If two candidates race from the same canonical predecessor, at most one may be accepted as the next canonical successor in one consistent registry view.

### 6.4 Rollback resistance
Restoring prover state to an earlier step must not authorize replacement of a newer canonical head.

### 6.5 Evidence-level honesty
Entropy or platform degradation must not silently retain a stronger evidence claim than the deployed mechanism supports.

### 6.6 Equivocation detectability
Where L3 is claimed, conflicting registry views must become detectable through signed checkpoints plus the declared gossip/quorum/transparency/anchor mechanism.

## 7. Snapshot clarification

Snapshot divergence is not itself a proof of originality. If two copies begin with identical state and later receive different fresh inputs, their commitments should normally diverge. IEPP's security claim is instead that registry freshness, predecessor binding, authentication and atomic canonical selection prevent both branches from silently occupying the same canonical position.

If an attacker obtains both the current protected state and signing authority, the attacker may race the legitimate prover. At L1 this is a stated boundary, not a solved TRP instance. Stronger resistance requires protected keys/state, attestation, witnesses, recovery policy or physical binding according to the claimed evidence level.

## 8. Experimental metrics

Every TRP benchmark SHOULD report:

- `canonical_accept_rate_attacker`;
- `canonical_accept_rate_legitimate`;
- `dual_canonical_accept_rate`;
- `replay_accept_rate`;
- `rollback_accept_rate`;
- `stale_predecessor_accept_rate`;
- `first_divergence_step` as a diagnostic, not a proof;
- time to fork/conflict detection;
- attack budget and trials;
- evidence level and entropy profile;
- negative controls.

The primary security metric is unauthorized canonical acceptance, not statistical similarity between output streams.

## 9. Claims discipline

A conforming report distinguishes:

1. protocol invariant — enforced by construction or atomic state transition;
2. cryptographic assumption — dependent on hash/signature security;
3. platform assumption — dependent on key/state/entropy protection;
4. empirical result — an attack was not observed within a stated budget;
5. conjecture — a hardness statement without a reduction or proof.

The phrase `TRP-hard` MUST NOT be used as an unconditional theorem unless a formal model and proof justify it. Preferred wording is `resistant to the evaluated TRP attack profile under the stated assumptions and budget`.

## 10. Relationship to IEPP

TRP is the adversarial continuation problem. IEPP is a protocol construction intended to make unauthorized canonical continuation fail under explicitly declared assumptions. The canonical registry answers which branch is accepted; authenticated transition evidence answers whether the candidate satisfies the protocol; entropy commitments and runtime evidence can strengthen freshness and execution binding according to evidence level.

This separation is intentional: branch divergence is evidence about execution history, while canonical continuity is a verification and policy property.

## 11. Minimum TRP 2.0 benchmark suite

A release claiming TRP 2.0 evaluation SHOULD include at least:

1. replay with old and substituted challenges;
2. stale-predecessor rollback;
3. simultaneous fork race;
4. snapshot fork with independent fresh inputs;
5. partial-state leakage;
6. entropy repeat/freeze/degradation;
7. key+state compromise as an expected-boundary control;
8. registry equivocation where L3 is claimed;
9. negative control showing that output-distribution resemblance alone does not identify canonicality.

Passing items 1–6 does not imply resistance to items 7–8.

# IEPP Core Specification v0.2.1 — Research Working Draft

Status: research draft; not production ready  
Scope: anchored execution-lineage continuity verification

## 1. Protocol claim

For an enrolled entity with an authenticated key, a current canonical registry head, a fresh single-use verifier
challenge, a declared entropy source, and an atomic registry update, IEPP determines whether presented transition
evidence is the next accepted continuation of that canonical lineage.

The result is policy-relative. IEPP does not determine consciousness, personhood, metaphysical originality, or
canonicality without a registry and selection policy.

## 2. Transition

The prover commits to runtime entropy rather than revealing the raw bytes.

```text
EC[t] = H("IEPP-Entropy-v1" || E[t])

S[t] = H(
  "IEPP-State-vNext-1" || sid || domain || counter || S[t-1] ||
  challenge_id || challenge_nonce || EC[t] || entropy_source ||
  runtime_commitment || attestation_commitment
)
```

The prover signs all transition fields using the enrolled Ed25519 key. Length-prefixed domain-separated encoding is
used to avoid concatenation ambiguity.

## 3. Acceptance order

The registry accepts only when all conditions hold:

1. entity is enrolled;
2. protocol, domain and key identifier match enrollment;
3. signature is valid over every evidence field;
4. evidence has not already been accepted;
5. challenge exists, matches entity/domain/nonce/expiry, is unused and unexpired;
6. counter is exactly current counter plus one;
7. predecessor equals the current canonical head;
8. declared entropy source is allowed and the commitment is not an immediate repeat;
9. state transition recomputation matches;
10. challenge consumption, evidence insertion, audit append, canonical-head update, and audit-root update complete atomically.

An exact retry of evidence that has already committed returns `ALREADY_COMMITTED` without advancing state again.
This is an idempotent confirmation, not a second canonical acceptance and not an attack success.

## 4. Canonical fork policy

When multiple valid successors race from the same head, exactly one may win the atomic registry update. Other
successors are validly signed branches but are not canonical continuations. Entropy makes branches diverge; it does
not choose the winner.

## 5. Audit and equivocation

Every accepted transition or migration extends a hash-chained audit root. The registry signs checkpoints containing
registry ID, sequence, entity, counter, canonical head and audit root. Two different signed values for the same
registry/sequence/entity/counter constitute detectable equivocation when compared.

Detection requires checkpoint gossip, quorum, transparency logging or an external anchor. Isolated verifiers cannot
discover a split view by themselves.

## 6. Key migration

Migration binds the current canonical head and counter, old/new key identifiers, new public key and a fresh
challenge. Both old and new private keys sign the migration body. Policy-driven recovery when the old key is lost is
outside this core and requires a separately auditable authority process.

## 7. Evidence levels

- **L1 software:** process key, software state, declared software entropy, single registry.
- **L2 protected runtime:** TPM/TEE/secure element protects key/state and attests entropy/runtime measurements.
- **L3 witnessed registry:** quorum or transparency gossip detects registry equivocation.
- **L4 physical binding:** evaluated PUF/sensor/physical entropy and device lifecycle controls.

Claims must not exceed the deployed level.

## 8. Explicit limitations

- Unique entropy commitments do not prove unpredictability or source integrity.
- Full theft of current state and signing key allows an attacker to race as the entity.
- Loss or rollback of registry state can reauthorize an old branch.
- Two isolated registry replicas can accept different branches until checkpoints are compared.
- The full in-memory `AtomicRegistry` remains available for bounded protocol tests. The v0.2.1
  `DurableRegistry` integrates challenge consumption, evidence uniqueness, canonical-head advancement, entropy-health
  recording, and the global audit root in one SQLite WAL/FULL transaction. It is a single-host research profile, not
  a production or distributed registry. A separate `SQLiteCanonicalStore` remains a lower-level CAS test component.
- An internally consistent rollback of the entire SQLite database cannot be detected locally. External checkpoints,
  transparency, a quorum, or a protected monotonic anchor are required.

## 9. Durable result semantics

- `CONTINUITY_VALID`: this request committed one new canonical transition.
- `ALREADY_COMMITTED`: the identical evidence ID committed previously; no state change occurred on this retry.
- `REPLAY_DETECTED`: an already-consumed context was reused without matching a prior committed evidence ID.
- `ROLLBACK_OR_LOSING_FORK`: the candidate is older than, or lost a race against, the current canonical lineage.

Canonical decisions and entropy health are reported separately. v0.2.1 directly identifies only an allowed source
profile, immediate repetition, and source substitution. Predictability, bias, truncation, and physical origin require
versioned health profiles and stronger evidence, deferred to v0.3.

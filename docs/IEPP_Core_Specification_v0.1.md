# IEPP Core Specification v0.1

Status: Working Draft  
Scope: Anchored execution-lineage continuity verification  
Publication status: Research specification; not production ready

## 1. Purpose

The Individual Entity Proof Protocol (IEPP) is a continuity-verification layer for digital entities. It evaluates whether a presented execution lineage is a valid continuation of a previously accepted canonical lineage.

IEPP complements, rather than replaces, cryptographic identity, platform attestation, content provenance, and governance.

## 2. Controlling claim

Given an enrolled entity, an accepted canonical state, fresh verifier challenges, evolving protected state, and a declared entropy trust level, IEPP enables a verifier to detect invalid continuation attempts such as replay, rollback, and non-canonical fork continuation under the defined threat model.

## 3. Non-claims

IEPP does not by itself:

- prove consciousness, personhood, intention, or legal identity;
- establish that the initially enrolled entity is the metaphysical “original”;
- select a canonical branch without registry, consensus, or policy;
- replace signing keys, TPM/TEE/PUF attestation, FIDO-style authentication, or C2PA-style provenance;
- guarantee security after simultaneous compromise of all state, entropy, authentication, verifier, and registry trust anchors;
- reliably distinguish an original and an exact clone from output-distribution statistics alone.

## 4. Roles

- **Prover Entity (P):** evolves lineage state and produces evidence.
- **Verifier (V):** issues fresh challenges and verifies evidence.
- **Canonical Lineage Registry (CLR):** stores the last accepted canonical commitment and transition metadata.
- **Entropy Provider (EP):** supplies runtime entropy with a declared trust level.
- **Attestation Provider (AP):** optionally binds evidence to a platform, device, TPM, TEE, or PUF.
- **Policy Authority (PA):** defines enrollment, migration, recovery, quorum, and conflict policy.

## 5. Data model

Let:

- `sid` be the enrolled entity identifier;
- `S[t-1]` be the previous protected lineage state;
- `C[t]` be a fresh verifier challenge;
- `E[t]` be fresh runtime entropy plus source metadata;
- `M[t]` be a commitment to relevant runtime/internal state;
- `A[t]` be optional attestation evidence;
- `ctx[t]` contain protocol version, domain, counter, and time-window context.

Candidate state transition:

```text
S[t] = H(
  "IEPP-State-v1" || sid || S[t-1] || C[t] || E[t] ||
  M[t] || H(A[t]) || ctx[t]
)
```

Candidate response evidence:

```text
R[t] = Sign_SK(
  "IEPP-Evidence-v1" || sid || H(S[t-1]) || H(S[t]) ||
  C[t] || H(M[t]) || H(A[t]) || ctx[t]
)
```

The signing or attestation mechanism authenticates the enrolled prover or platform. The state transition and canonical registry establish the claimed lineage continuation. Runtime entropy causes independently executing forks to evolve differently, but entropy alone does not select the canonical branch.

## 6. State machine

```text
UNENROLLED -> ENROLLED -> ACTIVE -> {ACTIVE, FORKED, SUSPENDED}
FORKED -> {RECOVERY_REQUIRED, REVOKED}
SUSPENDED -> {ACTIVE, MIGRATION_REQUIRED, REVOKED}
MIGRATION_REQUIRED -> ACTIVE
RECOVERY_REQUIRED -> ACTIVE
```

### 6.1 Enrollment

The Policy Authority creates `sid`, authenticates the enrollment event, sets the evidence level, and records the genesis commitment in the CLR.

### 6.2 Challenge

The verifier issues an unpredictable challenge bound to a verifier domain and expiration window. A challenge is single-use for one `sid`.

### 6.3 Transition

The prover evolves protected state, commits to relevant runtime state, binds the transition to the challenge and previous commitment, and returns authenticated evidence.

### 6.4 Canonical acceptance

The CLR applies a compare-and-swap rule: a transition is accepted only if its `previous_commitment` equals the current canonical commitment. On success the current commitment is atomically replaced with `new_commitment`.

### 6.5 Conflict

If two transitions reference the same previous commitment, at most one can become canonical under the single-successor policy. Later candidates are recorded as a fork conflict rather than silently replacing the accepted successor.

### 6.6 Migration and recovery

Authorized migration and recovery are explicit policy events. They must preserve the audit record and must not be represented as uninterrupted ordinary transitions.

## 7. Verification outcomes

- `CONTINUITY_VALID`
- `LINEAGE_FORKED`
- `REPLAY_DETECTED`
- `ROLLBACK_DETECTED`
- `STALE_CANONICAL_STATE`
- `CHALLENGE_INVALID`
- `ENTROPY_TRUST_DEGRADED`
- `ATTESTATION_INVALID`
- `MIGRATION_REQUIRED`
- `RECOVERY_REQUIRED`
- `POLICY_REJECTED`

Each result must include a reason code and auditable metadata without exposing raw entropy or protected internal state.

## 8. Evidence levels

| Level | Minimum trust basis | Intended use |
|---|---|---|
| L1 Experimental | Software state, OS entropy, authenticated transcript | Research and low-risk testing |
| L2 Platform-bound | Isolated key and OS/platform attestation | General hosted agents |
| L3 Hardware-backed | TPM/TEE key plus rollback controls | Enterprise and high-value agents |
| L4 Physical-bound | Hardware identity plus PUF or protected physical entropy | Robots and safety-critical systems |

Claims and test results must identify the evidence level. Results from L1 must not be presented as hardware-backed security.

## 9. Security objectives

1. Old evidence cannot satisfy a fresh challenge.
2. Previously accepted evidence cannot be accepted as a new transition.
3. A restored prover cannot silently replace a later canonical state.
4. Two successors from one state cannot both be accepted under a single-successor policy.
5. Evidence cannot be transplanted across entities, versions, or verifier domains.
6. Authorized migration is distinguishable from unauthorized cloning.
7. Recovery leaves an auditable discontinuity or policy override record.

## 10. Open research questions

- formal definition and hardness evidence for the Trajectory Reconstruction Problem (TRP);
- minimum entropy quality and health-test requirements;
- registry equivocation and partition handling;
- VM snapshot, malicious hypervisor, and full-host compromise boundaries;
- TPM, TEE, monotonic counter, and PUF integration;
- privacy-preserving state commitments and selective disclosure;
- independent reproduction and adversarial evaluation.

## 11. Compatibility position

IEPP is intended to compose with established mechanisms:

- keys and signatures authenticate evidence;
- FIDO-style mechanisms authenticate principals and devices;
- TPM/TEE/PUF mechanisms strengthen runtime binding;
- provenance systems record content history;
- IEPP measures whether an anchored execution lineage continued according to policy.

## 12. Versioning

This document is v0.1. Wire formats, algorithms, cryptographic suites, entropy profiles, and registry consistency rules remain subject to formal review. Implementations must not claim interoperability until those elements are fixed in a later specification.

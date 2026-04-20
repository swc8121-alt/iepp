[README.md](https://github.com/user-attachments/files/26893455/README.md)
# IEPP — Intrinsic Entropy Proof of Presence

A research proposal for continuity-based identity verification  
for AI agents, avatars, robots, and digital entities.

> PCT patent application filed.  
> Concept documentation in progress.  
> Collaboration and feedback welcome.

IEPP explores a new approach to identity:

identity is not defined by static structure,  
but by continuity of existence over time.

---

## Whitepaper series

Concept evolution history:

| version | focus | link |
|---|---|---|
| v0.1 | Concept introduction | https://entropyproof.com/ |
| v0.2 | Experimental validation | https://entropyproof.com/ai-existence-proof/iepp-whitepaper-v0-2-experimental-validation/ |
| v0.3 | Continuity-based identity formulation | https://entropyproof.com/ai-existence-proof/iepp-whitepaper-v0-3/ |
| v0.4 | Canonical lineage & statistical limits | https://entropyproof.com/ai-existence-proof/iepp-whitepaper-v0-4/ |
| v0.5 | TRP formulation & policy layer proposal | https://entropyproof.com/ai-existence-proof/iepp-whitepaper-v0-5/ |

---

## What problem does IEPP try to solve?

As AI systems become autonomous, persistent, and replicable,  
a fundamental question emerges:

> How can we verify that a digital entity  
> is the same entity over time?

Future systems may include:

- AI agents
- autonomous software entities
- digital avatars
- physical AI systems (robots)
- long-running AI services
- digital assets with persistent identity

These systems may be copied, forked, reinstantiated,  
modified, simulated, or cloned.

Traditional identity mechanisms rely on static attributes:  
keys, signatures, model weights, architecture, stored identifiers.

However, these properties can be duplicated.  
**Copyable structure cannot reliably prove identity continuity.**

IEPP investigates identity defined by continuity of trajectory.

---

## Core concept

IEPP models identity as continuity of state evolution.

Each response is generated using intrinsic entropy  
combined with previous state continuity.

General representation:

```
R = H(E || C || T || S)

E = intrinsic entropy
C = external challenge
T = time
S = continuity state
```

Each response is linked to previous responses.  
Identity emerges as trajectory continuity.

---

## Security conjecture (TRP)

**Trajectory Reconstruction Problem (TRP)** — conjecture:

```
Pr[T_clone^(k+1:n) ≡ T_canonical^(k+1:n) | T_1:k] ≤ ε(n−k)
```

Even with full knowledge of the prefix trajectory T_1:k,  
no probabilistic polynomial-time adversary can reproduce  
the canonical continuation with non-negligible probability.

Formal proof is an open problem and a primary research objective.

---

## Experimental findings (so far)

Experiments conducted in reproducible Google Colab environments.

| metric | result |
|---|---|
| fork divergence rate | 100% (100 runs) |
| immediate divergence after clone | 100% |
| attacker success rate | 0.0% (50,000 attempts) |
| clone statistical separation | not achieved |
| canonical lineage separation | 100% / 0% (original / clone) |

**Key finding:**  
Statistical metrics successfully detect structural attackers.  
Clone discrimination requires canonical lineage verification,  
not statistical similarity measurement.

---

## Three-layer verification structure

```
Layer 1 — Challenge binding
  R_{n+1} = H(R_n || C_{n+1} || commitment(state_{n+1}))
  → prevents replay and precomputation attacks

Layer 2 — Commitment chain
  commitment_n = H(state_n)
  → structural integrity without exposing internal state

Layer 3 — Statistical continuity
  continuity_score from norm trajectory, entropy, autocorrelation
  → anomaly detection for structural attackers
```

---

## Why continuity matters

Two systems may share identical structure,  
yet follow different trajectories.

Even identical copies diverge immediately after forking.

```
original:  R_1 → R_2 → ... → R_k → R_{k+1} → R_{k+2} → ...
clone:     R_1 → R_2 → ... → R_k → R'_{k+1} → R'_{k+2} → ...
                                     ↑
                               diverges here (immediately)
```

Identity becomes an observable property of continuity,  
rather than a fixed structural attribute.

> Existence is not a state. It is a lineage.

---

## Scope and layer boundaries

IEPP defines the **measurement layer** only.

```
┌─────────────────────────────────────────┐
│  Governance / Policy layer              │
│  canonical selection, dispute resolution│
│  → decided by users and institutions   │
├─────────────────────────────────────────┤
│  Application layer                      │
│  branch management, canonical anchoring │
│  → decided by platforms and services   │
├─────────────────────────────────────────┤
│  IEPP Protocol layer                    │
│  continuity verification                │
│  divergence detection                   │
│  lineage auditability                   │
└─────────────────────────────────────────┘
```

IEPP does not determine which trajectory is canonical.  
IEPP provides the measurement.  
The application decides what to do with it.

---

## Potential applications

- AI agent identity verification
- persistent digital avatar identity
- robot identity continuity verification
- clone detection for AI systems
- runtime integrity verification
- tamper detection
- continuity verification for long-running AI processes
- identity persistence across system updates
- digital asset originality tracking
- synthetic content provenance

---

## Code

Experimental Colab notebooks:

| notebook | description |
|---|---|
| `iepp_v03_merged.py` | Three-layer trajectory plausibility verifier |
| `iepp_v04.py` | Autocorrelation-based clone detection experiment |

All experiments are reproducible.  
Results are documented in the whitepaper series.

---

## Open problems

- formal proof of TRP hardness
- clone discrimination via trajectory statistics
- minimum entropy source conditions
- hardware entropy integration (TPM, PUF)
- canonical lineage anchoring design
- genesis registry architecture

---

## Research status

- concept stage with experimental validation
- PCT patent application filed
- open research questions remain
- not production ready
- collaboration and peer review welcome

---

## Motivation

As AI becomes easier to replicate,  
identity verification becomes harder.

Future digital ecosystems may require:

- proof of originality
- proof of continuity  
- proof of non-cloning

IEPP explores trajectory-based identity as a possible foundation.

---

## Vision

Identity should not depend only on structure.  
Identity may emerge from continuity.

Traditional authentication asks:  
*does this entity know the secret?*

IEPP asks:  
*is this entity still on the same trajectory?*

Whether continuity can serve as a verifiable,  
forgery-resistant identity signal —  
is the central open question this protocol explores.

---

## Citation

If you reference this work:

```
IEPP — Intrinsic Entropy Proof of Presence
entropyproof.com
PCT patent application filed.
```

---

*Feedback, criticism, and collaboration proposals are welcome.*

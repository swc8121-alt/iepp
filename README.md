# IEPP — Individual Entity Proof Protocol

**Entropy-anchored execution-lineage continuity verification for AI agents and digital entities**

IEPP is an early-stage research protocol exploring how a verifier can determine whether an enrolled digital entity remains on an accepted execution lineage over time.

> Identity is not structure. Identity is continuity.

Earlier project materials use the expansion **Intrinsic Entropy Proof of Presence**. Those documents are retained as part of the research history. The current protocol-level name is **Individual Entity Proof Protocol**.

## Status

- Research specification: v0.2 working draft
- TRP security model: 2.0 working draft
- Experimental evidence: software-only simulations
- Production readiness: not production ready
- Formal security proof: not established; TRP hardness is a research conjecture
- Patent status: PCT application filed
- License: Apache-2.0

## The problem

AI agents, avatars, robots, and long-running software entities can be copied, snapshotted, rolled back, migrated, and forked. Static identifiers, keys, model weights, or architecture can authenticate a credential or structure, but they do not by themselves describe whether one execution remained the accepted continuation of an earlier execution.

IEPP asks:

> Is this entity presenting a valid continuation of its previously accepted execution lineage?

## What IEPP does

IEPP combines:

1. a fresh verifier challenge;
2. a commitment to evolving protected state;
3. runtime entropy with a declared trust level;
4. authenticated transition evidence;
5. a canonical lineage registry and acceptance policy.

The registry applies a single-successor rule: a candidate transition can advance the lineage only when its predecessor matches the current canonical commitment. Competing successors are treated as fork conflicts.

## TRP 2.0

The **Trajectory Reconstruction Problem (TRP)** asks whether an adversary, given a canonical trajectory prefix and the information available under an explicit leakage model, can construct future evidence that is accepted as canonical without satisfying the authorized continuation conditions of the claimed evidence level.

TRP 2.0 decomposes this question into continuation forgery, fork, rollback, replay, snapshot, entropy-degradation, registry-race, migration, and registry-equivocation games. It explicitly separates empirical divergence from protocol acceptance and from computational-hardness claims.

**Current claim discipline:** finite attack experiments are empirical evidence only. IEPP does not currently claim a formal proof that TRP is computationally hard. See [`docs/TRP_2_Security_Model.md`](docs/TRP_2_Security_Model.md).

## What IEPP does not claim

IEPP does not by itself:

- prove consciousness, personhood, intention, or legal identity;
- determine a metaphysical “original” after cloning;
- select a canonical branch without registry or governance policy;
- replace signatures, FIDO-style authentication, TPM/TEE/PUF attestation, or provenance systems;
- guarantee security after complete compromise of every trust anchor;
- identify the canonical clone from output statistics alone.

Runtime entropy helps independently executing forks diverge. **Entropy alone does not choose which branch is canonical.**

## Architecture

```text
Governance / Policy
  enrollment, canonical policy, migration, recovery, disputes
                         |
Application / Registry
  canonical head, atomic successor acceptance, audit history
                         |
IEPP Protocol
  challenge binding, state commitment, transition evidence
                         |
Platform Trust
  software entropy -> OS/platform attestation -> TPM/TEE/PUF
```

## Repository guide

| Area | Start here | Purpose |
|---|---|---|
| Core protocol | [`docs/IEPP_Core_Specification_v0.2.md`](docs/IEPP_Core_Specification_v0.2.md) | Executable protocol model, acceptance order, evidence levels, explicit limits |
| TRP 2.0 | [`docs/TRP_2_Security_Model.md`](docs/TRP_2_Security_Model.md) | Formalized TRP definition, leakage profiles, security-game family, hardness conjecture |
| Threat analysis | [`docs/IEPP_Threat_Model_v0.1.md`](docs/IEPP_Threat_Model_v0.1.md) | Trust assumptions, adversaries, attack games, limitations |
| Core validation | [`docs/IEPP_Core_Validation_v0.2.md`](docs/IEPP_Core_Validation_v0.2.md) | Positive tests, required negative results, performance, release limits |
| Reference core | [`reference/iepp_vnext/`](reference/iepp_vnext/) | Ed25519 evidence, one-time challenges, atomic registry, durable CAS tests |
| TRP game harness | [`reference/iepp_vnext/trp2_games.py`](reference/iepp_vnext/trp2_games.py) | Deterministic replay, rollback, fork, substitution and unauthorized-key invariant tests |
| Documentation index | [`docs/README.md`](docs/README.md) | Current and historical document map |
| Experiments | [`experiments/README.md`](experiments/README.md) | Reproduction instructions and interpretation rules |
| v0.3 code | [`experiments/iepp_v03_merged.py`](experiments/iepp_v03_merged.py) | Three-layer trajectory plausibility experiment |
| v0.4 code | [`experiments/iepp_v04_autocorrelation.py`](experiments/iepp_v04_autocorrelation.py) | Autocorrelation clone-separation experiment |
| Roadmap | [`ROADMAP.md`](ROADMAP.md) | Research and engineering milestones |
| Contributing | [`CONTRIBUTING.md`](CONTRIBUTING.md) | Reproduction, review, and contribution expectations |
| Security | [`SECURITY.md`](SECURITY.md) | Responsible reporting and current security boundary |

## Current experimental evidence

| Observation | Reported result | Correct interpretation |
|---|---:|---|
| Fork divergence | 100% in 100 runs | Forks diverged immediately in the tested simulation |
| Simulated attacker success | 0 / 50,000 | No success under the implemented attacker models; not a proof |
| Statistical original/fork separation | Not achieved | Statistics did not identify the canonical clone |
| Canonical lineage separation | 100% / 0% in reported runs | Registry-relative lineage checking distinguished accepted and non-accepted branches |
| Large uniqueness tests | 0 collisions in reported runs | Empirical collision observation, not a replacement for cryptographic bounds |
| v0.2 valid transitions | 50,000 / 50,000 accepted | In-memory Ed25519 reference core under the declared L1 model |
| v0.2 replay / rollback / substitution | 0 false accepts in 10,000 trials each | Finite empirical result; not a cryptographic proof |
| v0.2 concurrent fork races | 0 double accepts in 1,000 races | Atomic single-registry result; partitions require checkpoint gossip |

The most important negative result is preserved: statistical similarity metrics were insufficient for original-versus-fork discrimination. Canonical lineage verification is therefore the governing mechanism; statistical continuity remains an anomaly signal.

## Quick start

The current research implementation and validation material are under `reference/iepp_vnext/`. Run the repository CI workflow or the reference checks documented there. TRP 2.0 invariant checks can also be executed directly with:

```bash
python -m reference.iepp_vnext.trp2_games
```

## Research principle

IEPP treats identity continuity as a layered security claim. A stronger evidence level requires stronger assumptions and stronger roots of trust. Claims must not exceed the deployed level.

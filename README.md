# IEPP — Individual Entity Proof Protocol

**Entropy-anchored execution-lineage continuity verification for AI agents and digital entities**

IEPP is an early-stage research protocol exploring how a verifier can determine whether an enrolled digital entity remains on an accepted execution lineage over time.

> Identity is not structure. Identity is continuity.

**Conceived and developed by [Woocheol Seo](https://entropyproof.com/), independent researcher.**

Canonical one-sentence description:

> IEPP is an entropy-anchored protocol for testing whether an AI agent or other digital entity presents the next accepted continuation of a previously enrolled execution lineage.

Canonical attribution:

> Individual Entity Proof Protocol (IEPP), conceived and developed by Woocheol Seo. The foundational entropy-based challenge-response mechanism is subject to prior patent filings; the canonical-continuation framework and TRP 2.0 are released as open research for reproducibility, public scrutiny, and standards development.

Earlier project materials use the expansion **Intrinsic Entropy Proof of Presence**. Those documents are retained as part of the research history. The current protocol-level name is **Individual Entity Proof Protocol**.

## Status

- Research specification: v0.2 working draft
- Experimental evidence: software-only simulations
- Production readiness: not production ready
- Formal security proof: not established
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
| Threat analysis | [`docs/IEPP_Threat_Model_v0.1.md`](docs/IEPP_Threat_Model_v0.1.md) | Trust assumptions, adversaries, attack games, limitations |
| Core validation | [`docs/IEPP_Core_Validation_v0.2.md`](docs/IEPP_Core_Validation_v0.2.md) | Positive tests, required negative results, performance, release limits |
| Reference core | [`reference/iepp_vnext/`](reference/iepp_vnext/) | Ed25519 evidence, one-time challenges, atomic registry, and integrated durable-registry tests |
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
| v0.2.1 durable fault matrix | F00–F12 deterministic cases passed | Single-host SQLite transaction result; not distributed consensus or rollback-proof storage |

The most important negative result is preserved: statistical similarity metrics were insufficient for original-versus-fork discrimination. Canonical lineage verification is therefore the governing mechanism; statistical continuity remains an anomaly signal.

## Quick start

Requirements: Python 3.10 or later.

```bash
python -m venv .venv
```

Activate the environment:

```bash
# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies and run the experiments:

```bash
pip install -r requirements.txt
python experiments/iepp_v03_merged.py
python experiments/iepp_v04_autocorrelation.py
python -m unittest discover -s reference/iepp_vnext/tests -v
python reference/iepp_vnext/benchmark.py
```

The experiments use runtime entropy, so exact numeric values can vary. Claims should be based on aggregate results, declared configurations, and reproducible manifests.

## Evidence levels

| Level | Trust basis | Intended use |
|---|---|---|
| L1 Experimental | Software state, OS entropy, authenticated transcript | Research and low-risk tests |
| L2 Protected runtime | Isolated key/state plus TPM/TEE/secure-element platform attestation | Hosted and device-bound agents |
| L3 Witnessed registry | Quorum, transparency gossip, or external anchoring | Split-view/equivocation detection |
| L4 Physical binding | Evaluated hardware identity plus PUF or protected physical entropy | Robots and safety-critical systems |

Existing public experiments are L1 unless explicitly stated otherwise.

## Whitepaper history

The original root files are retained to preserve the evolution of the idea:

| Version | Focus | Repository document |
|---|---|---|
| v0.3 | Trajectory continuity and three-layer verification | [`IEPP Whitepaper v0.3`](IEPP%20Whitepaper%20v0.3) |
| v0.4 | Canonical lineage and limits of statistical identity | [`IEPP Whitepaper v0.4`](IEPP%20Whitepaper%20v0.4) |
| v0.5 | Policy and deployment proposal | [`IEPP Whitepaper v0.5`](IEPP%20Whitepaper%20v0.5) |
| Changelog | Research evolution | [`IEPP Changelog`](IEPP%20Changelog) |
| Experiment notes | Original experiment guide | [`IEPP Experiments`](IEPP%20Experiments) |

Website series: [entropyproof.com](https://entropyproof.com/)

## Open research questions

- Can the TRP 2.0 game be connected to a formal reduction and composable guarantees under defensible assumptions?
- What minimum entropy profiles and health checks are required?
- How should a canonical registry prevent or reveal equivocation and partitions?
- How should authorized migration differ from unauthorized cloning?
- Which security guarantees become possible with TPM, TEE, monotonic counters, or PUFs?
- How can lineage evidence remain auditable without revealing sensitive internal state?
- Can independent teams reproduce the reported results and break the proposed assumptions?

## Project discipline

- Separate empirical evidence from formal proof.
- Publish failed hypotheses and negative controls.
- Identify the evidence level for every result.
- Keep canonical selection and governance outside the measurement claim.
- Treat TRP hardness as a conjecture until formally supported.
- Do not expose credentials, raw entropy, private state, or patent-confidential material.

## Citation

Until a stable archival citation is assigned, cite:

```text
Seo, Woocheol. Individual Entity Proof Protocol (IEPP):
Entropy-Anchored Execution-Lineage Continuity Verification.
Research repository, 2026. https://github.com/swc8121-alt/iepp
```

BibTeX:

```bibtex
@software{seo_iepp_2026,
  author = {Woocheol Seo},
  title = {Individual Entity Proof Protocol (IEPP): Entropy-Anchored Execution-Lineage Continuity Verification},
  year = {2026},
  url = {https://github.com/swc8121-alt/iepp}
}
```

## Collaboration

Constructive criticism, independent reproduction, protocol review, and adversarial analysis are welcome. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`SECURITY.md`](SECURITY.md) before opening a public report.

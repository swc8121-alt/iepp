# IEPP Research Evolution

This document explains how the IEPP research question changed as evidence accumulated. It is an evidence map, not a claim that every earlier hypothesis was confirmed. Historical documents are preserved so that readers can distinguish the original hypotheses, the experiments that challenged them, and the narrower protocol claim used today.

## Current research question

IEPP currently asks:

> Under an explicit policy and registry view, does authenticated evidence advance the previously accepted execution lineage by one canonical transition?

This is not a test of consciousness, personhood, physical uniqueness, or metaphysical originality. It is also not a statistical classifier for deciding which of two copies is the “real” original.

## Development of the problem formulation

| Stage | Question investigated at the time | Evidence or outcome | What changed afterward |
|---|---|---|---|
| v0.1 concept | Can runtime entropy contribute an execution-specific identity signal? | A hash construction combined entropy, challenge, time, and state. No formal security claim was established. | Entropy was treated as one input to evolving evidence, not as identity by itself. |
| v0.2 experiments | Do generated responses remain unique, and do implemented attackers reproduce accepted responses? | Large software simulations reported no collisions and no successes for the implemented attacker cases. | Finite zero-event results were reclassified as empirical observations rather than proof of unclonability or general forgery resistance. |
| v0.3 trajectory model | Can continuity be represented as a challenge-bound commitment trajectory? | Forks diverged immediately in 100/100 reported runs; five implemented attacker classes had 0/50,000 successes. The original/fork statistical score gap was only 0.015. | Challenge binding and predecessor-linked state became central; statistical continuity remained diagnostic. |
| v0.4 statistical test | Can output or autocorrelation statistics identify an original after copying? | The reported original/fork score gap was -0.047 and did not provide reliable separation. | This negative result rejected statistical original-selection as the governing mechanism. Canonical acceptance required an external policy and registry. |
| v0.5 policy proposal | How should applications respond to valid, stale, or competing continuations? | Policy, registry, alerting, migration, and deployment concepts were separated from measurement. | Governance was treated as an explicit external input rather than a property inferred from entropy. |
| Core v0.1-v0.2.1 | What can a reproducible protocol and implementation actually verify? | Authenticated predecessor-bound transitions, one-time challenges, atomic single-successor acceptance, negative controls, bounded exploration, and single-host durability cases were implemented. | The claim narrowed to L1 registry-relative canonical continuation with explicit compromise and partition boundaries. |
| arXiv v1 manuscript | How should the contribution be stated for independent review? | The protocol, TRP 2.0 capability classes, reproducible results, negative findings, and limitations were consolidated. | Earlier “existence” and “originality” language is historical context, not the current security claim. |

## What the negative results changed

Three findings materially redirected the project:

1. **Divergence is not canonicality.** Independent inputs can make two copies diverge without identifying either as privileged.
2. **Statistics are not successor authority.** Output similarity and autocorrelation did not reliably distinguish an original from an exact fork.
3. **Credentials are not continuity after full copying.** A process with the current signing key and state can win the next L1 registry race. Stronger claims require protected state, attestation, witnessed registries, or hardware-backed evidence.

These are retained as first-class results. They are not exceptions to an otherwise universal claim.

## How to read the repository

For a current technical understanding, read in this order:

1. [`../paper/iepp_arxiv_v1.tex`](../paper/iepp_arxiv_v1.tex) — integrated manuscript and claim boundary;
2. [`IEPP_Core_Specification_v0.2.md`](IEPP_Core_Specification_v0.2.md) — protocol state machine and acceptance rule;
3. [`IEPP_Threat_Model_v0.1.md`](IEPP_Threat_Model_v0.1.md) — adversary capabilities and assumptions;
4. [`IEPP_Core_Validation_v0.2.md`](IEPP_Core_Validation_v0.2.md) — experiments and negative controls;
5. [`../reference/iepp_vnext/`](../reference/iepp_vnext/) — executable reference implementation and result artifacts.

For the historical record, then read:

- [`../IEPP Whitepaper v0.3`](../IEPP%20Whitepaper%20v0.3) — trajectory-continuity hypothesis and early experiments;
- [`../IEPP Whitepaper v0.4`](../IEPP%20Whitepaper%20v0.4) — failed statistical original/fork separation and canonical-lineage turn;
- [`../IEPP Whitepaper v0.5`](../IEPP%20Whitepaper%20v0.5) — policy and deployment proposals;
- [`../IEPP Changelog`](../IEPP%20Changelog) — chronological project record.

Historical terminology and claims should not be quoted as the current IEPP specification without the current evidence boundary.

## Evidence and claim discipline

- “No event observed” means no event occurred in the stated trials, not that the event is impossible.
- “Canonical” means accepted under an explicit policy and registry view, not objectively original.
- “Entropy commitment” binds declared entropy data; it does not attest to unpredictability or physical origin.
- L1 results assume one consistent registry view and do not provide partition safety.
- Key-plus-current-state compromise is an expected L1 failure boundary.
- TRP 2.0 is a capability-indexed evaluation framework, not an established hardness assumption.

## Publication strategy

The present protocol, threat model, L1 implementation, and research evolution belong to one integrated first paper. A separate follow-up paper should require a distinct contribution, such as hypervisor-level snapshot experiments, a hardware-backed L2 profile, a witnessed-registry L3 evaluation, post-compromise recovery, or a formal reduction.

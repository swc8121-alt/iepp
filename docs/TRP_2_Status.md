# TRP 2.0 Status

Status date: 2026-08-10

## Implemented on this branch

- canonical-continuation security-game definition;
- explicit attacker view and A0–A6 hierarchy;
- P1–P7 security properties and threat coverage;
- claims/terminology/reviewer guidance;
- 12-case adversarial test plan;
- bounded executable model;
- regression tests, metrics helpers and baseline vectors;
- dependency-free self-test and GitHub Actions definitions;
- formalization and follow-on experiment roadmaps.

## Validation status

The repository contains executable checks and CI definitions, but this status document does not claim that remote GitHub Actions have completed successfully until workflow-run evidence is available. The bounded model is intentionally distinct from the real `iepp_vnext` implementation and from real VM/concurrency/hardware experiments.

## Promotion gate

Before merging TRP 2.0 into the main public narrative, recommended gates are: remote CI success; direct integration tests against the actual vNext APIs; concurrent fork/crash-consistency testing; and reproducible snapshot testing. Stronger L2/L3/L4 claims require their corresponding mechanisms and experiments.

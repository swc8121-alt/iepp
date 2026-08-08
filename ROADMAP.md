# IEPP Roadmap

The roadmap prioritizes a narrow, testable continuity claim before broader identity, provenance, robotics, or standards positioning.

## M1 — Core specification

Status: In progress

- define terms, roles, state machine, and non-claims;
- specify canonical single-successor acceptance;
- define verification outcomes and evidence levels;
- separate protocol measurement from governance.

Exit criterion: reviewers can state exactly what IEPP verifies and what it does not.

## M2 — Threat model and test plan

Status: In progress

- formalize replay, rollback, fork-race, substitution, entropy degradation, migration, and registry-equivocation games;
- publish negative controls and success conditions;
- map every existing experiment to the claim it supports or does not support.

Exit criterion: an independent reviewer can implement the attack games without private assumptions.

## M3 — Reproducible reference implementation

Status: Planned

- prover, verifier, and canonical registry reference components;
- explicit message formats and versioning;
- deterministic test vectors plus runtime-entropy profiles;
- automated replay, rollback, and fork tests;
- machine-readable result manifests.

Exit criterion: clean installation and repeatable tests on at least two independent environments.

## M4 — Adversarial runtime validation

Status: Planned

- VM snapshot and simultaneous fork race;
- storage and process rollback;
- RNG freeze, substitution, and degradation;
- stale registry write and split-view simulation;
- authorized migration versus unauthorized clone.

Exit criterion: limitations and detection behavior are documented for every attack class.

## M5 — Hardware-backed profile

Status: Planned

- integrate one TPM or TEE first;
- bind keys and state to platform evidence;
- evaluate monotonic or rollback-resistant storage;
- measure latency, throughput, storage, recovery, and failure modes.

Exit criterion: one independently reproducible L3 prototype.

## M6 — Paper revision and external review

Status: Planned

- align the paper's central claim with the core specification;
- distinguish conjectures, empirical results, and formal properties;
- include failures and limitations;
- obtain independent security and systems review.

Exit criterion: submission-ready manuscript with a reproducibility package.

## M7 — Narrow MVP pilot

Status: Planned

Initial use case: AI-agent session continuity for a high-value workflow.

- SDK integration;
- verification API;
- canonical registry and audit view;
- fork, replay, rollback, migration, and recovery demonstrations.

Exit criterion: one bounded pilot with explicit threat and evidence levels.

## Standards direction

Standards work begins with vocabulary, message formats, result codes, evidence profiles, and test vectors. Broad infrastructure claims follow only after independent implementation and review.

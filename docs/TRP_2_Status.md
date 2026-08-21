# TRP 2.0 Status

Status date: 2026-08-21

## Merged and implemented

TRP 2.0 was merged into `main` by PR #5 on 2026-08-14.

- canonical-continuation security-game definition;
- explicit attacker view and A0–A6 hierarchy;
- P1–P7 security properties and threat coverage;
- claims/terminology/reviewer guidance;
- 12-case adversarial test plan;
- bounded executable model;
- regression tests, metrics helpers and baseline vectors;
- dependency-free self-test and GitHub Actions definitions;
- formalization and follow-on experiment roadmaps.
- actual vNext integration vectors for replay, rollback, substitution and fork races;
- SQLite CAS restart, concurrent-successor and pre-commit rollback tests;
- v0.2.1 integrated SQLite transaction and deterministic F00–F12 fault-matrix coverage.

## Validation status

The bounded model, actual in-memory core, lower-level durable CAS, and integrated durable registry are distinct test
targets. Local suites pass for the committed configurations. This document does not claim remote Actions success
without workflow-run evidence, distributed safety, hypervisor-level snapshot resistance, or hardware assurance.

## Promotion gate

The original PR #5 merge gates for bounded checks, actual-core integration, single-registry concurrency, and claim
language are complete. Remaining research promotion gates are reproducible VM snapshot/restore, high-repetition
process-crash and storage-fault runs, entropy fault/downgrade profiles, L3 gossip/quorum, and L2/L4 hardware tests.

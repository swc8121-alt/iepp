# IEPP Public Evidence Boundary v0.2.1

Status: public research disclosure policy  
Date: 2026-08-22

## Purpose

IEPP publishes evidence needed to inspect its narrow research claims without implying that every deployment detail
is part of the public protocol or a validated security guarantee. This boundary protects both scientific honesty and
the security of future operational deployments.

## Public evidence

The public package includes:

- the canonical-continuation problem and TRP 2.0 attacker classes;
- authenticated transition semantics and the single-successor invariant;
- L1 reference code, baseline vectors, reproduction commands, and reported trial budgets;
- positive results for valid transitions, replay, rollback/losing forks, signed-field substitution, and fork races;
- required negative controls for predictable entropy, key-plus-state compromise, isolated registries, and failed
  statistical original/fork separation;
- precise evidence levels and limitations.

## Supplemental v0.2.1 durability observation

A single-host SQLite research prototype completed deterministic F00-F12 cases covering pre-transaction state,
pre-commit write boundaries, commit-response loss and idempotent retry, a two-writer successor race, checkpoint
regeneration after restart, internally consistent old-snapshot restoration, and fail-closed corruption handling.

In the tested deterministic cases:

- no pre-commit fault left a partial canonical acceptance;
- commit-response loss did not cause a second state advance on exact retry;
- exactly one of two successors from one predecessor committed;
- restart validation rejected simulated corruption rather than silently creating a new genesis;
- an internally consistent rollback of the whole database was not locally detectable, as expected.

These are bounded observations, not proof of crash consistency across operating systems, filesystems, storage
hardware, process-kill schedules, or distributed registries. The public claim does not include production readiness.

## Deliberately non-public operational material

The following are outside the public L1 reproducibility package:

- deployment-specific entropy-health thresholds and downgrade rules;
- post-compromise recovery authority, revocation, and emergency procedures;
- quorum membership, gossip cadence, partition policy, and customer-specific risk settings;
- TPM/TEE/secure-element/PUF provisioning and manufacturing procedures;
- production keys, credentials, raw entropy, private state, internal telemetry, and detection thresholds.

These omissions do not convert unknown results into positive claims. If a public claim depends on one of these
mechanisms, the mechanism and evidence needed to evaluate that claim must be disclosed or the claim must remain
explicitly unsupported.

## Reporting rule

Every result must state the implementation, platform, attacker capability, trial or state-space budget, evidence
level, and observed failure boundary. Zero observed adverse events are finite empirical results, not an unconditional
TRP-hardness theorem, proof of originality, or guarantee after complete compromise.

# IEPP Documentation

This directory is the current technical source of truth. Root-level whitepapers remain available as historical research records.

## Current normative-direction drafts

1. [`IEPP_Core_Specification_v0.2.md`](IEPP_Core_Specification_v0.2.md)  
   Executable protocol model, signed evidence, single-use challenges, canonical acceptance, audit, migration, and explicit limits.

2. [`IEPP_Threat_Model_v0.1.md`](IEPP_Threat_Model_v0.1.md)  
   Trust assumptions, adversary classes, attack games, out-of-scope conditions, and reporting rules.

3. [`IEPP_Core_Validation_v0.2.md`](IEPP_Core_Validation_v0.2.md)  
   Reproduction commands, large-run results, performance measurements, and required negative findings.

These are working drafts. They guide implementation and experiments but do not yet define a stable interoperable wire protocol.

## Historical sequence

| Stage | Central question | Current interpretation |
|---|---|---|
| v0.1 | Can intrinsic entropy serve as an identity signal? | Entropy contributes divergence but does not select a canonical identity |
| v0.2 | Do simulated responses remain unique and attack-resistant? | Useful empirical baseline; finite failure counts are not proofs |
| v0.3 | Can continuity be measured as a trajectory? | Challenge binding and commitment chaining are core; statistics are auxiliary |
| v0.4 | Can statistics distinguish an original from a clone? | Reported negative result: canonical registry is required |
| v0.5 | How could policy and deployment use continuity evidence? | Governance and application policy must remain distinct from protocol measurement |
| Core v0.1 | What exactly is verified? | Valid continuation of an anchored canonical execution lineage |
| Core v0.2.1 | Can the controlling claim survive durable local faults? | Signed transitions and integrated SQLite acceptance have deterministic F00–F12 coverage; distributed and hardware boundaries remain explicit |

## Documentation rules

- Current technical claims must link to evidence or be labeled as conjecture/design work.
- “AI existence proof” is an explanatory umbrella, not an unrestricted cryptographic guarantee.
- “Clone detection” must specify whether it means divergence observation, anomaly detection, or canonical fork rejection.
- Statistical results must not be described as canonical identity decisions.
- Hardware-backed claims require hardware-backed tests and an identified evidence level.
- Migration and recovery must be visible, auditable policy events.

## Planned documents

- message and wire-format specification;
- canonical registry consistency profile;
- entropy source and health-test profile;
- migration and recovery profile;
- expanded interoperability vectors for independent implementations;
- TPM/TEE integration profile;
- privacy and selective-disclosure analysis.

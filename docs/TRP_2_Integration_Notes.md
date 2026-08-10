# TRP 2.0 Integration Notes

TRP 2.0 is designed to sit beside, not replace, the current IEPP core and threat model.

## Mapping to IEPP Core Specification v0.2

- challenge single use -> replay/substitution games;
- exact counter increment -> rollback/stale-counter games;
- current canonical predecessor -> predecessor-continuity game;
- authenticated evidence -> forgery/substitution games;
- atomic head update -> fork-serialization game;
- entropy commitment/profile -> evidence-level honesty and degradation tests;
- signed checkpoints -> L3 equivocation tests;
- migration evidence -> future authorized-boundary games.

## Mapping to IEPP Threat Model v0.1

The existing replay, rollback, fork race, challenge substitution, entropy degradation, registry equivocation and migration cases become concrete TRP profiles. TRP 2.0 adds a common success event and reporting language so results from these cases can be compared without conflating branch divergence with canonicality.

## Compatibility rule

No core protocol field is changed by this v0.1 TRP work. The new material is a security/evaluation layer. Protocol changes should be proposed only when an attack test demonstrates a missing invariant or when a stronger evidence level requires additional evidence.

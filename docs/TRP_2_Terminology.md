# TRP 2.0 Terminology

- **execution lineage** — ordered history of authenticated execution-state transitions.
- **canonical head** — registry-selected current commitment for an enrolled entity.
- **canonical continuation** — a transition accepted as the next successor of the canonical head.
- **unauthorized canonical continuation** — canonical acceptance obtained without satisfying the authority/evidence requirements of the declared profile.
- **compromise boundary** — step/time at which the attacker receives its declared view or capabilities.
- **adversary view `V_t`** — information and controls available to the attacker at the compromise boundary.
- **fork divergence** — two executions from a common predecessor produce different later commitments; diagnostic, not an originality proof.
- **evidence level** — L1–L4 deployment class defining which software/platform/registry/physical assumptions support a claim.
- **TRP resistance** — bounded resistance to a named TRP attack profile under stated assumptions; not shorthand for an unconditional theorem.

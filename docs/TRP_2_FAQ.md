# TRP 2.0 FAQ

### Does TRP 2.0 prove an AI cannot be copied?
No. It defines whether a named attacker can obtain unauthorized canonical continuation acceptance under stated assumptions.

### Why keep entropy?
Entropy/runtime evidence can bind a transition to fresh execution conditions and make independent forks diverge, but it is not a canonicality oracle.

### What decides which fork is canonical?
The registry and its selection/authority policy.

### What if an attacker steals both the current key and current state?
At L1, the attacker may race the legitimate prover. TRP 2.0 deliberately exposes this as an A5 boundary.

### Is TRP a proven hardness problem?
Not in the current repository. TRP 2.0 is a formalized security game/problem with bounded executable evaluation and a roadmap toward proofs for selected variants.

### Why is this stronger than reporting immediate fork divergence?
Because it defines the actual verifier failure an attacker wants: unauthorized canonical acceptance. Divergence can happen while the system is still insecure, or while neither branch has been established as canonical.

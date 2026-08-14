# Whitepaper insert — Trajectory Reconstruction Problem 2.0

## Trajectory Reconstruction as Canonical Continuation Security

IEPP treats execution continuity as a protocol-relative security property rather than a claim that stochastic behavior uniquely identifies an original process. We define the Trajectory Reconstruction Problem (TRP 2.0) as follows: after an adversary observes or compromises an execution lineage up to a declared boundary, can it cause an unauthorized future continuation to be accepted as the canonical continuation of the enrolled entity?

The adversary is parameterized by an explicit view that may include the public transcript, copied software, partial state, a runtime snapshot, signing authority, entropy influence, verifier influence or registry influence. The primary success event is unauthorized canonical acceptance. Fork divergence is reported only as a diagnostic property: two copies receiving different fresh inputs may diverge immediately, but that observation does not determine which branch is canonical.

Under the IEPP core model, continuity evidence is bound to the current canonical predecessor, a monotonic counter, fresh verifier context and authenticated transition fields. A single-successor atomic registry serializes competing continuations. These mechanisms target replay, rollback, substitution and fork-race attacks. Entropy commitments and runtime/attestation evidence may strengthen execution binding according to the declared evidence level, but entropy does not select the canonical branch.

TRP 2.0 also makes compromise boundaries explicit. In the software evidence profile, an attacker that possesses both current signing authority and current state may race the legitimate prover; this is a stated boundary, not a hidden exception. Stronger resistance requires protected state/key mechanisms, witnessed registries, recovery/refresh policies or physical binding as appropriate. Experimental failure to break a profile is reported as bounded evidence and is not described as a proof of a general computational hardness theorem.

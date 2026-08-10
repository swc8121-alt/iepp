# TRP 2.0 Standardization Notes

For a future standards-oriented document, normative requirements should focus on observable protocol behavior rather than asserting an intrinsic notion of originality.

Candidate normative language:

- An implementation **MUST** bind continuation evidence to the current canonical predecessor and declared entity/domain context.
- A verifier/registry **MUST NOT** accept a consumed challenge as authorization for a new ordinary continuation.
- Under a declared single-successor policy, a registry **MUST NOT** accept two distinct successors for the same canonical position in one consistent registry view.
- An implementation **MUST** state its evidence level and relevant key/state/entropy/registry assumptions.
- A report claiming TRP resistance **MUST** identify the evaluated attacker profile and compromise boundary.
- A deployment claiming witnessed-registry protection **MUST** specify the mechanism by which conflicting signed views are compared or detected.
- Entropy uniqueness **MUST NOT** by itself be described as proof of unpredictability, originality or canonicality.

Formal proof requirements, cryptographic suites and deployment profiles should be separate conformance layers rather than embedded as universal assumptions.

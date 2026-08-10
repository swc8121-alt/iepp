# TRP 2.0 Release Criteria

A public TRP 2.0 release should include four separately labeled evidence classes:

1. **Specification:** security game, attacker profiles, security properties and claim boundaries.
2. **Executable model:** source, vectors and deterministic invariant tests.
3. **Systems experiments:** real reference implementation, concurrency, crash/restart and snapshot results with environment metadata.
4. **Formal results:** only the properties for which a proof/reduction actually exists.

A release is incomplete if it reports fork divergence without canonical-acceptance results, omits the A5 boundary, or presents a bounded experiment as a general hardness proof.

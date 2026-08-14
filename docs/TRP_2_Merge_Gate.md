# TRP 2.0 Merge Gate

TRP 2.0 should be promoted from the working branch when all of the following are satisfied:

- [ ] aggregate bounded self-test passes in remote CI;
- [ ] baseline vectors/profile/metrics tests pass;
- [ ] actual `iepp_vnext` integration tests cover replay, rollback and fork race;
- [ ] concurrency test reports zero dual canonical acceptance for the tested registry implementation;
- [ ] crash/restart test confirms no stale reauthorization in the tested durable store;
- [ ] snapshot experiment is reproducible and reports divergence separately from canonical acceptance;
- [ ] README/whitepaper language follows `TRP_2_Claim_Language.md`;
- [ ] no statement upgrades empirical evidence into an unconditional TRP hardness theorem;
- [ ] L2/L3/L4 claims, if any, have corresponding mechanisms and tests.

Failure of a gate should narrow the claim or remain documented as open work rather than being hidden.

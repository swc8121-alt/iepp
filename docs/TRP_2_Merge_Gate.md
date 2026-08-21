# TRP 2.0 Merge Gate

TRP 2.0 was merged by PR #5 on 2026-08-14. The checklist now separates completed merge evidence from open research promotion work.

- [x] aggregate bounded self-test passes locally;
- [x] baseline vectors/profile/metrics tests pass;
- [x] actual `iepp_vnext` integration tests cover replay, rollback and fork race;
- [x] tested in-memory registry and SQLite components report zero dual canonical acceptance;
- [x] pre-commit failures roll back in the tested integrated SQLite registry;
- [x] README/whitepaper language follows `TRP_2_Claim_Language.md`;
- [x] no statement upgrades empirical evidence into an unconditional TRP hardness theorem;

## Open research promotion gates

- [ ] confirm remote GitHub Actions runs and preserve run URLs;
- [ ] run the F02–F09 matrix at the declared high-repetition and multiprocess budgets;
- [ ] reproduce real VM/hypervisor snapshot and restore behavior;
- [ ] complete entropy freeze/bias/substitution/unavailable policy tests;
- [ ] test L3 checkpoint gossip/quorum under partitions;
- [ ] support every L2/L4 claim with its corresponding mechanism and hardware test.

Failure of a gate should narrow the claim or remain documented as open work rather than being hidden.

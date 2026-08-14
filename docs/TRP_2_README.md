# TRP 2.0

TRP 2.0 reframes the Trajectory Reconstruction Problem as a canonical-continuation security problem for IEPP.

Start here:

- `TRP_2_Security_Model_v0.1.md` — definition, game, adversary hierarchy, metrics and claim discipline.
- `TRP_2_Test_Plan_v0.1.md` — 12-case adversarial validation matrix and staged validation plan.
- `TRP_2_Review_Notes_v0.1.md` — corrections to the older divergence-centric framing.
- `TRP_2_Formalization_Roadmap.md` — path from the current game to a future cryptographic proof.
- `TRP_2_CHANGELOG.md` — revision history.

Executable bounded model:

- `../reference/iepp_vnext/trp2_benchmark.py`
- `../reference/iepp_vnext/run_trp2_ci.py`
- `../reference/iepp_vnext/test_trp2_unittest.py`
- `../reference/iepp_vnext/TRP2_RESULTS.md`

The key rule is simple: **fork divergence is diagnostic evidence; unauthorized canonical acceptance is the security event.**

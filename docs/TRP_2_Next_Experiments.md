# TRP 2.0 Next Experiments

Priority order after the bounded model:

1. **Actual `iepp_vnext` API replay/rollback/fork integration tests.** Confirm the real reference implementation enforces the same invariants as the reduced model.
2. **Concurrent fork stress.** Multiple workers race from one head; target metric is dual canonical acceptance rate.
3. **Crash consistency.** Kill/restart around challenge consumption and head update using the durable store.
4. **Snapshot experiment.** Duplicate process/VM state, resume both copies, and distinguish divergence diagnostics from canonical acceptance.
5. **Partial leakage sweep.** Reveal selected state components without the signing key and measure attacker continuation advantage.
6. **Entropy degradation.** Freeze/repeat/bias declared entropy and verify explicit downgrade/failure behavior.
7. **A5 boundary and recovery.** Demonstrate key+state race at L1, then evaluate protected-key/state or refresh/recovery designs for stronger levels.
8. **L3 split-view test.** Run conflicting registry views and measure detection latency under the selected checkpoint witness mechanism.

Publication-quality claims should wait until items 1–4 are reproducible with recorded environment and commit identifiers. L2/L3 claims require the corresponding mechanisms, not extrapolation from L1.

# TRP 2.0 vs earlier TRP framing

| Earlier emphasis | TRP 2.0 |
|---|---|
| Can a clone reconstruct the same trajectory? | Can an attacker obtain unauthorized canonical continuation acceptance? |
| Fork divergence as central evidence | Fork divergence is diagnostic; registry acceptance is the security event |
| Broad clone attacker | Explicit A0–A6 capability profiles |
| Hidden/fresh entropy as primary intuition | Authentication + predecessor binding + challenge freshness + registry atomicity, with entropy/runtime evidence scoped by level |
| Hardness suggested from attack failure | Empirical failure, invariant and theorem are reported separately |
| Snapshot clone treated mainly as divergence experiment | Snapshot is a race/continuity experiment with explicit key/state assumptions |
| Original/copy language | Canonical/non-canonical language |

The change preserves the core continuity intuition while removing claims that cannot be justified from stochastic divergence alone.

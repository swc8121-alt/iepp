# TRP 2.0 Test Vector Format v0.1

Future machine-readable vectors should contain at least:

```json
{
  "trp_version": "2.0-v0.1",
  "profile": "A3",
  "evidence_level": "L1",
  "compromise_boundary": 10,
  "attacker_view": ["transcript", "snapshot"],
  "attack": "fork_race",
  "budget": 1000,
  "expected": "at_most_one_canonical_successor"
}
```

A result record should add implementation commit, platform, entropy profile, attempts, successes, detection latency and failure traces. Secrets, raw private keys and raw protected entropy must not be published in test vectors.

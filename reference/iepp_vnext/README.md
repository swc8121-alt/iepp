# IEPP vNext Private Core Lab

Status: research reference implementation; not production ready.

This is a clean implementation of anchored execution-lineage continuity. It
does not reuse the earlier statistical trajectory experiments and does not
include the paused Fingerprint work.

Implemented primitives:

- Ed25519-authenticated transition evidence;
- verifier-issued, entity/domain-bound, expiring, single-use challenges;
- committed runtime entropy with declared source policy;
- atomic single-successor canonical registry;
- replay, rollback, losing-fork and substitution rejection;
- append-only hash-chained audit events and signed checkpoints;
- authorized key migration and split-view checkpoint detection.
- integrated SQLite challenge/evidence/head/audit transaction with idempotent retry;
- deterministic F00–F12 durable fault-matrix coverage.

IEPP proves only the protocol claim under its trust assumptions. It does not
prove consciousness, personhood, metaphysical identity, or which exact clone
is the “original” without canonical registry policy.

## Run the validation

```bash
python -m unittest discover -s reference/iepp_vnext/tests -v
python reference/iepp_vnext/benchmark.py --valid-steps 50000 --attack-trials 10000 --fork-races 1000
python reference/iepp_vnext/negative_boundaries.py --predictable-steps 1000
python reference/iepp_vnext/performance.py --iterations 10000
```

See `PRIVATE_CORE_VALIDATION_REPORT_KO.md` for measured results and required negative findings.

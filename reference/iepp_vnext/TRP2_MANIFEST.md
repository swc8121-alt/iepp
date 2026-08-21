# TRP 2.0 validation manifest

This branch adds a bounded executable model for the new canonical-continuation security framing.

## Automated checks

```bash
cd reference/iepp_vnext
python run_trp2_ci.py
python -m unittest -v test_trp2_unittest.py
```

Expected bounded-model outcome:

```text
replay_accept_rate=0
rollback_accept_rate=0
unsigned_or_wrong_key_forgery_accept_rate=0
dual_canonical_accept_rate=0
key_plus_state_boundary_accept_rate=1
```

The final expected value is a deliberate boundary control for L1.

## Additional component evidence

- actual `iepp_vnext` integration covers replay, rollback, substitution, and fork race;
- `SQLiteCanonicalStore` covers restart, two-writer CAS, and injected pre-commit rollback;
- v0.2.1 `DurableRegistry` gives deterministic F00–F12 coverage for the integrated single-host transaction.

## Not yet claimed as validated

- real VM/process snapshot behavior;
- high-repetition multiprocess kill/crash budgets and storage-device faults;
- entropy-source quality or unpredictability;
- TEE/TPM/secure-element resistance;
- L3 checkpoint gossip/quorum split-view detection;
- physical/PUF binding;
- a cryptographic reduction proving a general TRP hardness theorem.

Those remain separate work items in the adversarial validation plan.

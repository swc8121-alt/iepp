# IEPP Experiments

This directory contains structured copies of the repository's original Colab-ready experiments. The original root files remain unchanged to preserve project history.

## Dated evidence packages

- [A3 two-VM VirtualBox, 2026-10-27](a3-virtualbox-2026-10-27/README.md): fixed 22-trial matrix, 42 registry decisions, 46 successful snapshot restores, and eight server-overlapped controlled races with one accepted successor each. L1 registry-relative harness evidence only; unsigned guest candidates and one local registry.
- [A3 VirtualBox, 2026-09-14](a3-virtualbox-2026-09-14/README.md): five cases / nine client records, including four paired trials and one actual rollback submission. Shared serial challenge decisions are corroborated by server records. Partial L1 evidence only; see the remaining matrix and provenance limits in the package.

## Files

- `iepp_v03_merged.py`: three-layer trajectory plausibility experiment.
- `iepp_v04_autocorrelation.py`: autocorrelation-based clone-separation experiment.

## Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Run:

```bash
python experiments/iepp_v03_merged.py
python experiments/iepp_v04_autocorrelation.py
```

## Interpretation discipline

- Fork divergence is an empirical property of these simulations.
- Zero successes in a finite attack simulation is not a cryptographic proof.
- Statistical metrics separated structural attackers in reported runs but did not reliably separate original and exact fork trajectories.
- Canonical lineage acceptance requires an external registry and policy; entropy alone does not choose the original branch.
- Results in this directory are software-only L1 evidence unless explicitly stated otherwise.

## Reproducibility improvements planned

- fixed experiment manifests and machine-readable result files;
- seeded negative controls alongside OS-entropy runs;
- independent-host reproduction with cryptographically authenticated guest submissions, building on the two-VM dated package above;
- confidence intervals and resource measurements;
- independent reproduction.

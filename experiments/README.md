# IEPP Experiments

This directory contains structured copies of the repository's original Colab-ready experiments. The original root files remain unchanged to preserve project history.

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
- VM snapshot, rollback, and fork-race tests;
- confidence intervals and resource measurements;
- independent reproduction.

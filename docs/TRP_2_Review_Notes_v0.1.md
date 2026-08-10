# TRP 2.0 Review Notes v0.1

## Why the older framing needed revision

The earlier TRP intuition — that copying structure/state does not reproduce future trajectory — remains useful, but it can overstate what entropy divergence proves. A fork can diverge simply because it receives different fresh inputs. Divergence alone does not identify an original branch and does not stop a fully authorized snapshot from racing.

TRP 2.0 therefore moves the primary outcome from `trajectory equality` or statistical clone separation to **unauthorized canonical continuation acceptance**.

## Corrections adopted

1. **Canonicality is externalized.** The registry/policy chooses the accepted successor; entropy does not choose an original.
2. **Attacker knowledge is explicit.** Every result declares the compromise boundary and adversary view.
3. **Full key+state theft is a boundary at L1.** The model deliberately contains a control where this attacker can win a race.
4. **Snapshot security is split into two questions.** Execution divergence is diagnostic; single canonical acceptance is the protocol property.
5. **Hardness language is constrained.** Failed attacks at finite budget are empirical evidence, not a reduction or theorem.
6. **Evidence levels bound claims.** Software, protected runtime, witnessed registry and physical binding cannot inherit one another's guarantees without the corresponding mechanisms.
7. **Negative results remain first-class.** Statistical resemblance of output streams is not a canonicality oracle.

## Research direction

A future formal treatment can define an ideal canonical-continuation functionality and prove selected protocol variants secure under cryptographic and registry assumptions. Until such a proof exists, the repository should use bounded claims tied to a named adversary profile, evidence level and attack budget.

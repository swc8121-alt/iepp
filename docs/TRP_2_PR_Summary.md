# TRP 2.0 implementation summary

This branch introduces TRP 2.0 as a security/evaluation layer over the current IEPP vNext design without changing core transition fields.

## Main change

The primary question changes from whether a clone reproduces the same stochastic trajectory to whether an adversary obtains **unauthorized canonical continuation acceptance**. The model defines a Canonical Continuation Game, explicit attacker views, A0–A6 capability profiles, evidence-level boundaries and claim discipline.

## Executable work

A dependency-free bounded model checks replay rejection, stale-predecessor rejection, wrong-key forgery rejection and single-successor fork serialization. A deliberate A5 negative control demonstrates that possession of current state plus signing authority can win a race at L1. Standard-library tests, machine-readable baseline vectors and GitHub Actions workflows are included.

## Scope boundary

This branch does not claim real-VM snapshot validation, production concurrency/crash consistency, entropy-source unpredictability, TEE/TPM guarantees, L3 split-view detection, physical binding or a formal cryptographic reduction. Those are explicitly scheduled as follow-on validation/formalization work.

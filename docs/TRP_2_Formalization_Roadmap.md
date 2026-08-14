# TRP 2.0 Formalization Roadmap

TRP 2.0 v0.1 is a security-game specification plus executable bounded model. It is not yet a formal cryptographic proof.

## Target theorem shape

For a named adversary class, evidence level and registry functionality, define a canonical-continuation experiment and bound

```text
Adv_CCG(A) = Pr[A causes unauthorized canonical acceptance].
```

A future proof should decompose this advantage into explicit terms, for example authentication forgery, hash failure, challenge-freshness failure, atomic-registry failure, protected-state compromise and policy/authority compromise. The exact decomposition depends on the protocol variant and must not be asserted before it is proved.

## Work packages

1. Specify an ideal single-successor canonical registry functionality.
2. Specify enrollment, challenge, transition, migration and recovery oracles.
3. Define A0–A6 games precisely, including corruption timing.
4. Prove replay and substitution resistance from challenge single-use plus authentication.
5. Prove stale-predecessor rejection from the ideal registry invariant.
6. Model fork races under concurrency and crash recovery.
7. Add protected-state/attestation assumptions for L2.
8. Add checkpoint consistency/gossip assumptions for L3.
9. Keep L4 physical claims outside the software proof unless a hardware model is explicitly introduced.
10. Validate the formal model against executable traces and negative controls.

## Publication rule

Until a proof is complete, publications should describe TRP 2.0 as a formalized security *problem/game* with empirical and invariant-based evaluation, not as a proven computational hardness theorem.

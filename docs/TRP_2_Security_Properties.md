# TRP 2.0 Security Properties

A deployment can claim only the properties its evidence level and registry actually enforce.

**P1 Challenge freshness.** A consumed, expired, mismatched or substituted challenge cannot authorize a new canonical transition.

**P2 Authenticated transition binding.** Modification of entity/domain/counter/predecessor/challenge/evidence fields invalidates authentication.

**P3 Canonical predecessor continuity.** Only a successor of the current canonical head is eligible for ordinary continuation.

**P4 Single-successor serialization.** In one consistent registry view, at most one competing successor occupies a canonical counter position.

**P5 Rollback exclusion.** Restoration of an older prover state does not roll back a newer canonical registry head.

**P6 Evidence honesty.** Loss of an assumed entropy/platform property causes failure or explicit evidence downgrade rather than an unchanged stronger claim.

**P7 Equivocation detectability (L3).** Conflicting signed registry views become detectable under the declared witness/gossip/quorum/anchor assumptions.

None of P1–P7 alone proves metaphysical originality. Together they define protocol-relative continuity properties.

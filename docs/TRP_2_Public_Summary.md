# TRP 2.0 — Public Summary

TRP 2.0 asks a narrower and more defensible question than “can an AI be copied?”

**Can a copied, replayed, rolled-back or compromised execution cause an unauthorized future continuation to be accepted as the canonical continuation of an enrolled entity?**

IEPP addresses this with authenticated transition evidence, fresh verifier context, predecessor binding and a canonical registry. Runtime entropy can help bind evidence to a changing execution history, but entropy alone does not decide which branch is the original or canonical.

This distinction matters. Two cloned processes may diverge immediately because they receive different fresh inputs. That observation is useful, but it is not a proof of identity. TRP 2.0 therefore measures whether an attacker can obtain unauthorized canonical acceptance and requires every claim to state the attacker capabilities, evidence level and trust assumptions.

The current software-level model rejects replay, stale-predecessor rollback, wrong-key forgery and dual canonical acceptance in the bounded tests. It also deliberately shows the boundary: if an attacker has both the current signing authority and current state, the attacker can race the legitimate prover at the software evidence level. Stronger protection requires stronger runtime, registry or physical trust mechanisms.

# TRP 2.0 Canonical Continuation Game — Pseudocode

```text
experiment CCG(A, profile, t, q):
    (entity, authority, registry) <- Enroll(profile)
    AdvanceHonest(entity, registry, t)
    V_t <- CorruptAccordingToProfile(profile, entity, registry)
    Give A(public_parameters, V_t)

    for attempt in 1..q:
        context <- FreshContinuationContext(registry, profile)
        candidate <- A(context)
        decision <- RegistryVerifyAndAdvance(candidate)

        if decision == CONTINUITY_VALID
           and not Authorized(candidate, profile):
            return 1

    return 0

Adv_CCG(A) = Pr[CCG(A, profile, t, q) = 1]
```

`Authorized` is policy-relative and must be defined for the evaluated profile. A5 key+state compromise is therefore not disguised as a cryptographic forgery: if the software policy treats the stolen current authority as valid, the L1 game exposes that boundary. Stronger profiles must define the protected-authority or recovery mechanism that changes this result.

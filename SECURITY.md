# Security Policy

IEPP is experimental security research and is not production ready.

## Supported research surface

Security review currently focuses on:

- replay and challenge substitution;
- rollback and stale-state acceptance;
- fork-race and canonical successor handling;
- entropy degradation and source substitution;
- registry equivocation and split views;
- migration and recovery abuse;
- exposure of protected state, raw entropy, keys, credentials, or personal data.

## Reporting

Do not place exploit details, credentials, private state, patent-confidential material, or active secrets in a public issue.

Use GitHub private vulnerability reporting when it is available for this repository. Otherwise contact the repository owner before public disclosure and provide only enough initial information to establish the affected component and impact.

## Expectations

Please include:

- affected file, version, or commit;
- attacker capability and trust assumptions;
- reproduction steps or proof of concept;
- success condition and observed result;
- suggested mitigation if known.

## Current limitations

- TRP hardness is a conjecture, not a proven security assumption.
- Existing experiments are primarily software-only L1 simulations.
- Statistical clone separation was not achieved in the reported original/fork tests.
- Canonical registry consistency, hardware rollback resistance, and malicious-host defense remain open work.
- A finite experiment with zero observed attacks does not establish cryptographic security.

Reports that clarify these boundaries are welcome and will be preserved in the research record.

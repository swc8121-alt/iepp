# TRP 2.0 Claim Language

## Recommended

> Under the stated attacker profile, evidence level, registry assumptions and evaluation budget, the evaluated IEPP construction rejected unauthorized canonical-continuation attempts in the tested cases.

> IEPP binds authenticated transition evidence to the current canonical predecessor and fresh verifier context. Under a single-successor atomic registry, competing forks cannot both occupy the same canonical position in one consistent registry view.

> Fresh execution inputs may make cloned executions diverge, but divergence alone does not identify an original. Canonicality is established by the registry and policy process.

## Avoid without a proof or stronger deployment assumptions

- `TRP is mathematically impossible to solve.`
- `IEPP makes cloning impossible.`
- `Entropy proves which AI is the original.`
- `A copied VM can never impersonate the entity.`
- `Zero successes in N trials proves zero attack probability.`

## L1 boundary statement

> In the software evidence profile, compromise of both current signing authority and current protected state can permit an attacker to race the legitimate prover. This is an explicit trust boundary rather than a property hidden by the benchmark.

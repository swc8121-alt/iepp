# IEPP Multi-Agent Orchestration Demo v0.1 — executable first slice

## Implementation target

This is the smallest local-only experiment that reuses `reference/iepp_vnext` rather than defining a second
continuity protocol. Three plain Python agents (`research`, `experiment`, and `audit`) each hold distinct IEPP
lineage state and an Ed25519 credential. The orchestrator binds a task receipt into `runtime_commitment`, issues a
fresh challenge, and submits the transition to the existing atomic canonical registry.

Run it from `reference/iepp_vnext`:

```bash
python orchestration_demo.py --output results/orchestration_demo_v0.1.jsonl
python -m unittest discover -s tests -v
```

The first command executes the normal A -> B -> C handoff and all required adversarial cases. It writes one JSON
object per verifier attempt. Tests assert the expected policy outcome deterministically; random hashes and wall-clock
timestamps are not golden test values.

## Cases and expected policy outcomes

| Case | Expected result |
|---|---|
| Normal continuation A -> B -> C | each `ACCEPT / CONTINUITY_VALID` |
| Restart from legitimately persisted current state | `ACCEPT / CONTINUITY_VALID` |
| Replay previously accepted evidence | `REJECT / REPLAY_DETECTED` |
| Copied credential with divergent state | `REJECT / STALE_CANONICAL_STATE` |
| Same-state fork B and B' | first submitted successor accepted; other rejected as losing fork |
| Snapshot/restore rollback | `REJECT / ROLLBACK_OR_LOSING_FORK` |
| Injected primary entropy failure with allowed fallback | `ACCEPT / CONTINUITY_VALID`, with fallback metadata |

The fork result demonstrates the configured single-successor registry policy. It does not identify a metaphysical
“original”; submission order selects the canonical winner in this deterministic harness.

## Evidence log contract

Every JSONL record includes the issue #10 minimum fields: run ID, UTC timestamp, monotonic lineage counter, task ID,
logical agent label, credential key ID, predecessor/current hashes, challenge nonce digest, declared entropy/fallback
metadata, harness branch/fork ID, verifier decision, reason code, and evidence level. Raw entropy and private key
material are never logged. A full claim-boundary statement is repeated in each record so logs remain self-describing.

## Claim and evidence boundary

This is **L1 software evidence** for controlled local Python-agent processes at the explicitly instrumented software
state, credential, single-registry, and declared entropy boundary. It does **not** prove ChatGPT or OpenAI
model-instance continuity. ChatGPT remains an orchestration/research layer outside the measured continuity claim.

Passing cases provide bounded mechanism-, platform-, and attack-budget-specific evidence only. They do not establish
universal TRP hardness, protected-runtime security, hardware-backed continuity, registry-compromise resistance, or
general compromise resistance. In particular, theft of both current state and signing key permits a race under the L1
model; stronger L2/L3/L4 claims require their corresponding mechanisms and experiments.

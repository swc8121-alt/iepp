"""Required negative results: cases the software-only IEPP core cannot solve alone."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import AtomicRegistry, ChallengeAuthority, Prover, checkpoints_conflict


def make_system(label: str, key: Ed25519PrivateKey | None = None, initial: bytes | None = None,
                registry_id: str | None = None, checkpoint_key: Ed25519PrivateKey | None = None):
    key = key or Ed25519PrivateKey.generate()
    initial = initial or sha256(b"initial").digest()
    ca = ChallengeAuthority()
    registry = AtomicRegistry(registry_id or f"registry-{label}", ca, checkpoint_key)
    registry.enroll("entity", "domain", initial, "key", key.public_key(), {"declared.os"})
    return Prover("entity", "domain", "key", key, initial), registry, ca


def run(predictable_steps: int = 1_000) -> dict:
    # Unique but fully predictable bytes pass the repeated-value check. A source
    # label is a declaration, not remote proof that OS entropy was actually used.
    prover, registry, ca = make_system("predictable")
    predictable_accepted = 0
    for tick in range(1, predictable_steps + 1):
        challenge = ca.issue("entity", "domain", now=tick, ttl=5,
                             nonce=sha256(f"c-{tick}".encode()).digest())
        entropy = tick.to_bytes(32, "big")
        evidence = prover.transition(challenge, entropy, "declared.os", b"runtime")
        predictable_accepted += int(registry.verify_and_advance(evidence, tick)[0])

    # A full snapshot includes key and state. Whichever clone reaches the
    # canonical registry first wins; IEPP cannot infer a metaphysical original.
    legitimate, race_registry, race_ca = make_system("compromise")
    attacker = legitimate.clone()
    ca = race_ca.issue("entity", "domain", now=1, ttl=5, nonce=b"a" * 32)
    cl = race_ca.issue("entity", "domain", now=1, ttl=5, nonce=b"l" * 32)
    attacker_result = race_registry.verify_and_advance(
        attacker.transition(ca, b"attacker-entropy", "declared.os", b"attacker-runtime"), 1)
    legitimate_result = race_registry.verify_and_advance(
        legitimate.transition(cl, b"legitimate-entropy", "declared.os", b"legitimate-runtime"), 1)

    # Isolated registries can each accept a different successor. Conflict is
    # detectable only when signed checkpoints are compared through gossip/anchor.
    shared_key, checkpoint_key = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    initial = sha256(b"split-initial").digest()
    branches = []
    for index in range(2):
        branch, reg, authority = make_system(str(index), shared_key, initial, "same-registry", checkpoint_key)
        challenge = authority.issue("entity", "domain", now=1, ttl=5, nonce=bytes([index + 1]) * 32)
        result = reg.verify_and_advance(branch.transition(
            challenge, f"branch-{index}".encode(), "declared.os", b"runtime"), 1)
        branches.append((result, reg.checkpoint("entity")))
    conflict = checkpoints_conflict(branches[0][1], branches[1][1])

    # Losing durable registry state recreates an old canonical view. A new
    # in-memory registry enrolled at genesis will accept a branch that the
    # original registry would regard as rollback.
    restart_key = Ed25519PrivateKey.generate()
    restart_initial = sha256(b"restart-initial").digest()
    live, live_registry, live_ca = make_system("live", restart_key, restart_initial)
    first_challenge = live_ca.issue("entity", "domain", now=1, ttl=5)
    live_registry.verify_and_advance(live.transition(
        first_challenge, b"live-entropy", "declared.os", b"runtime"), 1)
    stale = Prover("entity", "domain", "key", restart_key, restart_initial)
    lost_ca = ChallengeAuthority()
    lost_registry = AtomicRegistry("registry-after-state-loss", lost_ca)
    lost_registry.enroll("entity", "domain", restart_initial, "key", restart_key.public_key(), {"declared.os"})
    stale_challenge = lost_ca.issue("entity", "domain", now=2, ttl=5)
    state_loss_result = lost_registry.verify_and_advance(stale.transition(
        stale_challenge, b"stale-entropy", "declared.os", b"runtime"), 2)

    return {
        "schema": "iepp-negative-security-boundaries-v1",
        "predictable_entropy": {"steps": predictable_steps, "accepted": predictable_accepted,
                                "conclusion": "Uniqueness/repetition checks do not prove unpredictability or source integrity."},
        "full_snapshot_compromise": {"attacker_first": list(attacker_result),
                                     "legitimate_second": list(legitimate_result),
                                     "conclusion": "With valid key and current state, first canonical acceptance wins."},
        "isolated_registry_split_view": {"branch_acceptances": [list(x[0]) for x in branches],
                                         "checkpoint_conflict_detected_after_comparison": conflict,
                                         "conclusion": "Gossip, quorum or external anchoring is required for detection."},
        "registry_state_loss": {"stale_branch_accepted_by_reinitialized_registry": list(state_loss_result),
                                "conclusion": "Durable atomic state and anchored recovery checkpoints are mandatory."},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictable-steps", type=int, default=1_000)
    parser.add_argument("--output", type=Path, default=Path("results/negative_boundaries_v1.json"))
    args = parser.parse_args()
    result = run(args.predictable_steps)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))

"""Smallest executable IEPP multi-agent orchestration demo (L1 only).

The orchestrator and task payloads are deliberately simple.  The experiment
measures canonical execution-lineage decisions for controlled local Python
agents; it does not measure or prove ChatGPT/model-instance continuity.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

try:
    from .core import AtomicRegistry, Challenge, ChallengeAuthority, Prover, TransitionEvidence, hash_parts
except ImportError:  # Direct execution from reference/iepp_vnext.
    from core import AtomicRegistry, Challenge, ChallengeAuthority, Prover, TransitionEvidence, hash_parts


SCHEMA = "iepp-orchestration-demo-v0.1"
DOMAIN = "iepp.local-orchestration-demo"
EVIDENCE_LEVEL = "L1"
CLAIM_BOUNDARY = (
    "Controlled local Python-agent continuity at the explicitly instrumented software-state, "
    "credential, registry, and declared entropy boundary only. This does not prove ChatGPT/OpenAI "
    "model-instance continuity, universal TRP hardness, or general compromise resistance."
)


def _hex(value: bytes) -> str:
    return value.hex()


@dataclass
class LocalAgent:
    label: str
    prover: Prover

    def save(self, path: Path) -> None:
        private = self.prover.private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        path.write_text(json.dumps({
            "label": self.label,
            "sid": self.prover.sid,
            "domain": self.prover.domain,
            "key_id": self.prover.key_id,
            "private_key": private.hex(),
            "state": self.prover.state.hex(),
            "counter": self.prover.counter,
        }, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "LocalAgent":
        item = json.loads(path.read_text(encoding="utf-8"))
        key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(item["private_key"]))
        return cls(item["label"], Prover(item["sid"], item["domain"], item["key_id"], key,
                                         bytes.fromhex(item["state"]), item["counter"]))

class Demo:
    def __init__(self, output: Path, run_id: str | None = None,
                 entropy: Callable[[int], bytes] = os.urandom):
        self.output = output
        self.run_id = run_id or str(uuid.uuid4())
        self.entropy = entropy
        self.challenges = ChallengeAuthority()
        self.registry = AtomicRegistry("orchestration-demo-registry", self.challenges)
        self.agents: dict[str, LocalAgent] = {}
        self.records: list[dict[str, Any]] = []
        self._clock = 1_000
        self._enroll_agents()

    def _enroll_agents(self) -> None:
        for label in ("research", "experiment", "audit"):
            sid = f"local-agent:{label}"
            key = Ed25519PrivateKey.generate()
            initial = hash_parts(b"IEPP-Demo-Initial-v1", sid.encode())
            key_id = f"demo-key:{label}:1"
            self.registry.enroll(sid, DOMAIN, initial, key_id, key.public_key(),
                                 {"os.urandom", "fallback.os.urandom", "test.deterministic"})
            self.agents[label] = LocalAgent(label, Prover(sid, DOMAIN, key_id, key, initial))

    def _issue(self, agent: LocalAgent, task_id: str) -> Challenge:
        self._clock += 1
        nonce = self.entropy(32)
        return self.challenges.issue(agent.prover.sid, DOMAIN, now=self._clock, ttl=100, nonce=nonce)

    def _evidence(self, agent: LocalAgent, challenge: Challenge, task_id: str,
                  entropy_source: str, entropy_bytes: bytes | None = None) -> TransitionEvidence:
        receipt = hash_parts(b"IEPP-Orchestrator-Task-Receipt-v1", task_id.encode(), agent.label.encode())
        return agent.prover.transition(challenge, entropy_bytes or self.entropy(32), entropy_source, receipt)

    def _record(self, *, case: str, task_id: str, agent: LocalAgent, branch_id: str,
                evidence: TransitionEvidence, ok: bool, reason: str,
                entropy_metadata: dict[str, Any]) -> dict[str, Any]:
        record = {
            "schema": SCHEMA,
            "run_id": self.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "monotonic_counter": evidence.counter,
            "case": case,
            "orchestrator_task_id": task_id,
            "agent_id": agent.label,
            "credential_key_id": evidence.key_id,
            "predecessor_hash": _hex(evidence.previous),
            "current_hash": _hex(evidence.state),
            "challenge_nonce_digest": _hex(sha256(evidence.challenge_nonce).digest()),
            "entropy_metadata": entropy_metadata,
            "branch_fork_id": branch_id,
            "verifier_decision": "ACCEPT" if ok else "REJECT",
            "reason_code": reason,
            "evidence_level": EVIDENCE_LEVEL,
            "claim_boundary": CLAIM_BOUNDARY,
        }
        self.records.append(record)
        return record

    def submit(self, *, case: str, task_id: str, agent: LocalAgent, branch_id: str = "canonical",
               entropy_source: str = "os.urandom", entropy_bytes: bytes | None = None,
               entropy_metadata: dict[str, Any] | None = None) -> tuple[TransitionEvidence, dict[str, Any]]:
        challenge = self._issue(agent, task_id)
        evidence = self._evidence(agent, challenge, task_id, entropy_source, entropy_bytes)
        ok, reason = self.registry.verify_and_advance(evidence, now=self._clock)
        metadata = entropy_metadata or {"selected_source": entropy_source, "fallback_used": False}
        return evidence, self._record(case=case, task_id=task_id, agent=agent, branch_id=branch_id,
                                      evidence=evidence, ok=ok, reason=reason,
                                      entropy_metadata=metadata)

    def resubmit(self, *, case: str, task_id: str, agent: LocalAgent, branch_id: str,
                 evidence: TransitionEvidence) -> dict[str, Any]:
        ok, reason = self.registry.verify_and_advance(evidence, now=self._clock)
        return self._record(case=case, task_id=task_id, agent=agent, branch_id=branch_id,
                            evidence=evidence, ok=ok, reason=reason,
                            entropy_metadata={"selected_source": evidence.entropy_source,
                                              "fallback_used": False})

    def run(self) -> list[dict[str, Any]]:
        # Baseline handoff. Each task receipt is bound into its agent's transition.
        accepted: dict[str, TransitionEvidence] = {}
        for index, label in enumerate(("research", "experiment", "audit"), 1):
            evidence, record = self.submit(case="normal_continuation", task_id=f"handoff-{index}",
                                           agent=self.agents[label])
            assert record["verifier_decision"] == "ACCEPT"
            accepted[label] = evidence

        # A legitimate process restart reloads the current persisted state and credential.
        with tempfile.TemporaryDirectory() as directory:
            state_file = Path(directory) / "research-agent.json"
            self.agents["research"].save(state_file)
            restarted = LocalAgent.load(state_file)
            _, record = self.submit(case="persisted_process_restart", task_id="restart-1", agent=restarted)
            assert record["verifier_decision"] == "ACCEPT"
            self.agents["research"] = restarted

        replay = self.resubmit(case="old_proof_replay", task_id="replay-1",
                               agent=self.agents["research"], branch_id="replay",
                               evidence=accepted["research"])
        assert (replay["verifier_decision"], replay["reason_code"]) == ("REJECT", "REPLAY_DETECTED")

        # Same credential, deliberately divergent software state: identity is not continuity.
        source = self.agents["experiment"]
        divergent = LocalAgent(source.label, Prover(source.prover.sid, source.prover.domain,
            source.prover.key_id, source.prover.private_key, sha256(b"copied-divergent-state").digest(),
            source.prover.counter))
        _, copied = self.submit(case="copied_credential_divergent_state", task_id="credential-copy-1",
                                agent=divergent, branch_id="credential-copy")
        assert (copied["verifier_decision"], copied["reason_code"]) == ("REJECT", "STALE_CANONICAL_STATE")

        # Two same-state successors: submission order deterministically selects one canonical successor.
        left = LocalAgent(source.label, source.prover.clone())
        right = LocalAgent(source.label, source.prover.clone())
        _, left_record = self.submit(case="same_state_fork", task_id="fork-left", agent=left,
                                     branch_id="B")
        _, right_record = self.submit(case="same_state_fork", task_id="fork-right", agent=right,
                                      branch_id="B-prime")
        assert left_record["verifier_decision"] == "ACCEPT"
        assert (right_record["verifier_decision"], right_record["reason_code"]) == (
            "REJECT", "ROLLBACK_OR_LOSING_FORK")
        self.agents["experiment"] = left

        # A restored pre-advance snapshot cannot replace the later canonical head.
        audit = self.agents["audit"]
        snapshot = LocalAgent(audit.label, audit.prover.clone())
        _, advance = self.submit(case="snapshot_precondition_advance", task_id="snapshot-advance",
                                 agent=audit)
        assert advance["verifier_decision"] == "ACCEPT"
        _, rollback = self.submit(case="snapshot_restore_rollback", task_id="snapshot-restore",
                                  agent=snapshot, branch_id="restored-snapshot")
        assert (rollback["verifier_decision"], rollback["reason_code"]) == (
            "REJECT", "ROLLBACK_OR_LOSING_FORK")

        _, fallback = self.submit(
            case="entropy_source_fault_fallback", task_id="entropy-fallback-1", agent=audit,
            entropy_source="fallback.os.urandom",
            entropy_metadata={"primary_source": "demo.primary", "primary_status": "INJECTED_FAILURE",
                              "selected_source": "fallback.os.urandom", "fallback_used": True})
        assert fallback["verifier_decision"] == "ACCEPT"

        self.output.parent.mkdir(parents=True, exist_ok=True)
        with self.output.open("w", encoding="utf-8") as stream:
            for record in self.records:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
        return self.records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path("results/orchestration_demo_v0.1.jsonl"))
    args = parser.parse_args()
    records = Demo(args.output).run()
    accepted = sum(item["verifier_decision"] == "ACCEPT" for item in records)
    print(json.dumps({"schema": SCHEMA, "records": len(records), "accepted": accepted,
                      "rejected": len(records) - accepted, "output": str(args.output),
                      "evidence_level": EVIDENCE_LEVEL, "claim_boundary": CLAIM_BOUNDARY}, indent=2))


if __name__ == "__main__":
    main()

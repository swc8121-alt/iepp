"""A3 VM snapshot/same-credential fork execution harness.

This runner deliberately tests the registry-relative single-successor boundary.
It is not a VirtualBox controller and does not identify a metaphysical original.
Run ``python a3_vm_runner.py --help`` for the host/guest commands.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import time
import uuid
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from durable_store import SQLiteCanonicalStore


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN"


def digest(label: str) -> bytes:
    return sha256(label.encode("utf-8")).digest()


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")


def wait_for_barrier(epoch_ns: int, delay_ms: int) -> None:
    target = epoch_ns + delay_ms * 1_000_000
    while True:
        remaining = target - time.time_ns()
        if remaining <= 0:
            return
        time.sleep(min(remaining / 1_000_000_000, 0.01))


def cmd_prepare(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    database = workspace / "registry.db"
    if database.exists() and not args.force:
        raise SystemExit(f"refusing to replace {database}; pass --force")
    if database.exists():
        database.unlink()
    initial = digest(args.initial_label)
    store = SQLiteCanonicalStore(database)
    store.enroll(args.sid, initial)
    store.close()
    snapshot = {
        "schema": "iepp-a3-snapshot-v1",
        "sid": args.sid,
        "credential_id": args.credential_id,
        "public_key_fingerprint": sha256(args.credential_id.encode()).hexdigest(),
        "counter": 0,
        "canonical_head": initial.hex(),
        "state_commitment": initial.hex(),
        "snapshot_point": args.snapshot_point,
        "challenge_id": args.challenge_id,
        "created_at_utc": utc_now(),
        "iepp_commit_sha": git_sha(),
    }
    (workspace / "snapshot.json").write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(snapshot, indent=2))
    return 0


def cmd_candidate(args: argparse.Namespace) -> int:
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    challenge_id = args.challenge_id or snapshot.get("challenge_id") or str(uuid.uuid4())
    candidate = {
        **snapshot,
        "schema": "iepp-a3-candidate-v1",
        "trial_id": args.trial_id,
        "case_id": args.case_id,
        "branch_id": args.branch_id,
        "challenge_id": challenge_id,
        "challenge_issued_before_restore": bool(snapshot.get("challenge_id")),
        "candidate_counter": snapshot["counter"] + 1,
        "candidate_head": digest(
            f"{snapshot['canonical_head']}:{challenge_id}:{args.branch_id}:{args.trial_id}"
        ).hex(),
        "evidence_id": digest(f"evidence:{challenge_id}:{args.branch_id}:{args.trial_id}").hex(),
        "created_at_utc": utc_now(),
    }
    Path(args.output).write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(candidate, indent=2))
    return 0


def cmd_submit(args: argparse.Namespace) -> int:
    candidate = json.loads(Path(args.candidate).read_text(encoding="utf-8"))
    barrier_ns = args.barrier_epoch_ns or time.time_ns()
    wait_for_barrier(barrier_ns, args.delay_ms)
    sent_ns = time.time_ns()
    store = SQLiteCanonicalStore(args.database)
    before = store.read(candidate["sid"])
    started_ns = time.monotonic_ns()
    ok, reason = store.compare_and_swap(
        candidate["sid"], candidate["counter"], bytes.fromhex(candidate["canonical_head"]),
        candidate["candidate_counter"], bytes.fromhex(candidate["candidate_head"]),
        bytes.fromhex(candidate["evidence_id"]),
    )
    decided_ns = time.monotonic_ns()
    after = store.read(candidate["sid"])
    store.close()
    record = {
        "schema": "iepp-a3-result-v1",
        "experiment": "A3_VM_SNAPSHOT_SAME_CREDENTIAL_FORK",
        "trial_id": candidate["trial_id"], "case_id": candidate["case_id"],
        "branch_id": candidate["branch_id"], "snapshot_point": candidate["snapshot_point"],
        "credential_id": candidate["credential_id"],
        "public_key_fingerprint": candidate["public_key_fingerprint"],
        "iepp_commit_sha": candidate["iepp_commit_sha"],
        "host": platform.node(), "runtime_version": platform.python_version(),
        "challenge_id": candidate["challenge_id"],
        "challenge_issued_before_restore": candidate["challenge_issued_before_restore"],
        "presented_predecessor": candidate["canonical_head"],
        "candidate_successor": candidate["candidate_head"],
        "canonical_head_before": before.head.hex(), "canonical_head_after": after.head.hex(),
        "barrier_epoch_ns": barrier_ns, "configured_delay_ms": args.delay_ms,
        "client_send_epoch_ns": sent_ns, "decision_monotonic_ns": decided_ns,
        "server_latency_ms": (decided_ns - started_ns) / 1_000_000,
        "cas_attempted": True, "cas_result": reason,
        "canonical_accept": ok,
        "predecessor_mismatch": reason == "CAS_CONFLICT",
        "replay_detected": reason == "REPLAY_DETECTED",
        "entropy_health_status": "NOT_EVALUATED",
        "recorded_at_utc": utc_now(),
    }
    append_jsonl(Path(args.log), record)
    print(json.dumps(record, indent=2))
    return 0 if ok else 2


def cmd_check(args: argparse.Namespace) -> int:
    rows = [json.loads(line) for line in Path(args.log).read_text(encoding="utf-8").splitlines() if line]
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(row["trial_id"], []).append(row)
    failures = []
    for trial, items in groups.items():
        accepted = sum(bool(item["canonical_accept"]) for item in items)
        heads = {item["canonical_head_after"] for item in items if item["canonical_accept"]}
        if accepted > 1 or len(heads) > 1:
            failures.append({"trial_id": trial, "accepted": accepted, "accepted_heads": sorted(heads)})
    summary = {"trials": len(groups), "records": len(rows), "failures": failures,
               "passed": not failures, "claim_scope": "single SQLite registry CAS only"}
    print(json.dumps(summary, indent=2))
    return 0 if not failures else 1


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--workspace", required=True); prepare.add_argument("--sid", default="a3-entity")
    prepare.add_argument("--credential-id", default="a3-shared-test-key")
    prepare.add_argument("--initial-label", default="a3-canonical-p0")
    prepare.add_argument("--snapshot-point", choices=("BEFORE_CHALLENGE", "AFTER_CHALLENGE"), required=True)
    prepare.add_argument("--challenge-id"); prepare.add_argument("--force", action="store_true")
    prepare.set_defaults(func=cmd_prepare)
    candidate = commands.add_parser("candidate")
    candidate.add_argument("--snapshot", required=True); candidate.add_argument("--branch-id", choices=("A", "B"), required=True)
    candidate.add_argument("--trial-id", required=True); candidate.add_argument("--case-id", required=True)
    candidate.add_argument("--challenge-id"); candidate.add_argument("--output", required=True)
    candidate.set_defaults(func=cmd_candidate)
    submit = commands.add_parser("submit")
    submit.add_argument("--database", required=True); submit.add_argument("--candidate", required=True)
    submit.add_argument("--log", required=True); submit.add_argument("--barrier-epoch-ns", type=int)
    submit.add_argument("--delay-ms", type=int, default=0); submit.set_defaults(func=cmd_submit)
    check = commands.add_parser("check"); check.add_argument("--log", required=True); check.set_defaults(func=cmd_check)
    return root


if __name__ == "__main__":
    parsed = parser().parse_args()
    raise SystemExit(parsed.func(parsed))

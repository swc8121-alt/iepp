"""One-command loopback demonstration of the IEPP A3 safe-resume policy gate."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import time

from a3_registry_server import create_server
from a3_vm_runner import (
    build_candidate,
    check_rows,
    http_json,
    issue_challenge,
    prepare_workspace,
    snapshot_at_head,
    submit_candidate,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def result_row(candidate: dict, decision: dict, elapsed_ms: float) -> dict:
    evidence = candidate["evidence"]
    accepted = bool(decision.get("accepted"))
    return {
        "schema": "iepp-a3-client-result-v2",
        "experiment": candidate["experiment"],
        "trial_id": candidate["trial_id"],
        "case_id": candidate["case_id"],
        "branch_id": candidate["branch_id"],
        "snapshot_point": candidate["snapshot_point"],
        "challenge_issued_before_restore": candidate["challenge_issued_before_restore"],
        "public_key_fingerprint_sha256": candidate["public_key_fingerprint_sha256"],
        "iepp_source_revision": candidate["iepp_source_revision"],
        "challenge_id": evidence["challenge_id"],
        "evidence_id": evidence["evidence_id"],
        "signature_present": bool(evidence["signature"]),
        "presented_predecessor": evidence["previous"],
        "candidate_successor": evidence["state"],
        "transport_ok": True,
        "registry_reason": decision["reason"],
        "canonical_accept": accepted,
        "canonical_head_before": decision.get("canonical_head_before"),
        "canonical_head_after": decision.get("canonical_head_after"),
        "protected_action": "EXECUTED_SIMULATED" if accepted else "BLOCKED",
        "client_round_trip_ms": elapsed_ms,
        "entropy_health_status": "NOT_EVALUATED",
        "recorded_at_utc": utc_now(),
    }


def submit_timed(url: str, candidate: dict) -> dict:
    started = time.monotonic_ns()
    decision = submit_candidate(url, candidate)
    elapsed_ms = (time.monotonic_ns() - started) / 1_000_000
    return result_row(candidate, decision, elapsed_ms)


def run(workspace: Path, trials: int, force: bool = False) -> tuple[dict, list[dict]]:
    if trials < 2:
        raise ValueError("at least two trials are required to cover both challenge cases")
    prepared = prepare_workspace(
        workspace, "a3-safe-resume-agent", "iepp.a3.safe-resume",
        "a3-shared-test-key", "a3-safe-resume-p0", force,
    )
    client_log = workspace / "client-results.jsonl"
    server_log = workspace / "registry-events.jsonl"
    if force:
        for path in (client_log, server_log):
            if path.exists():
                path.unlink()
    snapshot = json.loads(Path(prepared["snapshot"]).read_text(encoding="utf-8"))
    server = create_server(prepared["database"], prepared["enrollment"],
                           "127.0.0.1", 0, str(server_log))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    rows: list[dict] = []
    try:
        for index in range(trials):
            head = http_json(url + "/v1/head?sid=a3-safe-resume-agent")
            trial_snapshot = snapshot_at_head(snapshot, head["counter"], head["canonical_head"])
            shared = index % 2 == 1
            if shared:
                challenge = issue_challenge(url, trial_snapshot["sid"], trial_snapshot["domain"])
                trial_snapshot["snapshot_point"] = "AFTER_CHALLENGE"
                trial_snapshot["challenge"] = challenge
                challenges = {"A": challenge, "B": challenge}
                case_id = "A3-SHARED-PRE-RESTORE-CHALLENGE"
            else:
                challenges = {
                    branch: issue_challenge(url, trial_snapshot["sid"], trial_snapshot["domain"])
                    for branch in ("A", "B")
                }
                case_id = "A3-FRESH-POST-RESTORE-CHALLENGE"
            trial_id = f"A3-{index + 1:04d}"
            candidates = {
                branch: build_candidate(trial_snapshot, branch, trial_id, case_id, challenges[branch])
                for branch in ("A", "B")
            }
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(submit_timed, url, candidates[branch]) for branch in ("A", "B")]
                trial_rows = [future.result() for future in futures]
            rows.extend(trial_rows)
            with client_log.open("a", encoding="utf-8") as stream:
                for row in trial_rows:
                    stream.write(json.dumps(row, sort_keys=True) + "\n")
    finally:
        server.shutdown()
        server.server_close()
        server.engine.close()
        thread.join(timeout=5)

    check = check_rows(rows)
    reasons = Counter(row["registry_reason"] for row in rows)
    winners = Counter(row["branch_id"] for row in rows if row["canonical_accept"])
    latencies = [row["client_round_trip_ms"] for row in rows]
    summary = {
        "schema": "iepp-a3-safe-resume-summary-v2",
        "experiment": "A3_SIGNED_SAME_CREDENTIAL_SAFE_RESUME",
        "generated_at_utc": utc_now(),
        "iepp_source_revision": snapshot["iepp_source_revision"],
        "trials": trials,
        "candidate_submissions": len(rows),
        "fresh_post_restore_challenge_trials": (trials + 1) // 2,
        "shared_pre_restore_challenge_trials": trials // 2,
        "canonical_accepts": sum(row["canonical_accept"] for row in rows),
        "double_accepts": sum(
            sum(row["canonical_accept"] for row in rows if row["trial_id"] == trial_id) > 1
            for trial_id in {row["trial_id"] for row in rows}
        ),
        "simulated_protected_actions": sum(
            row["protected_action"] == "EXECUTED_SIMULATED" for row in rows
        ),
        "registry_reasons": dict(sorted(reasons.items())),
        "winning_branches": dict(sorted(winners.items())),
        "client_round_trip_ms": {
            "minimum": min(latencies),
            "mean": sum(latencies) / len(latencies),
            "maximum": max(latencies),
        },
        "passed": check["passed"],
        "failures": check["failures"],
        "tested_invariant": check["invariant"],
        "claim_scope": "L1 single online registry; signed lab key; cooperative simulated action gate",
        "not_tested": [
            "VirtualBox or hypervisor isolation",
            "durable challenge state across registry restart",
            "registry partitions or equivocation",
            "TPM, TEE, secure element, or PUF binding",
            "malicious code that bypasses the policy gate",
            "consciousness, personhood, or metaphysical originality",
        ],
    }
    return summary, rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--trials", type=int, default=25)
    parser.add_argument("--output")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    workspace = Path(args.workspace)
    summary, _ = run(workspace, args.trials, args.force)
    output = Path(args.output) if args.output else workspace / "summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

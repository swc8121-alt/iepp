"""A3 signed same-credential snapshot/fork experiment client.

The runner creates a deliberately cloneable lab credential, prepares signed IEPP
transition evidence inside each restored branch, and submits it to the separate
HTTP registry. Only a registry-accepted branch records the simulated protected
action as executed. This is an L1 policy-gate experiment, not a VirtualBox
controller or a claim about metaphysical/physical originality.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from a3_registry import challenge_from_dict, evidence_to_dict
from core import Prover, hash_parts
from durable_store import SQLiteCanonicalStore


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_revision() -> str:
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], text=True, capture_output=True, check=True
        ).stdout.strip()
        return revision + ("-dirty" if dirty else "")
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN"


def digest(label: str) -> bytes:
    return sha256(label.encode("utf-8")).digest()


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def wait_for_barrier(epoch_ns: int, delay_ms: int) -> None:
    target = epoch_ns + delay_ms * 1_000_000
    while True:
        remaining = target - time.time_ns()
        if remaining <= 0:
            return
        time.sleep(min(remaining / 1_000_000_000, 0.01))


def http_json(url: str, value: dict | None = None, timeout: float = 10.0) -> dict:
    data = None if value is None else json.dumps(value).encode("utf-8")
    request = Request(url, data=data, method="GET" if value is None else "POST",
                      headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read())
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"registry-http-{error.code}: {detail}") from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"registry-unreachable: {error}") from error
    if not isinstance(result, dict):
        raise RuntimeError("registry-response-was-not-an-object")
    return result


def issue_challenge(registry_url: str, sid: str, domain: str, ttl: int = 30) -> dict:
    response = http_json(
        registry_url.rstrip("/") + "/v1/challenge",
        {"sid": sid, "domain": domain, "ttl": ttl},
    )
    if not response.get("ok") or "challenge" not in response:
        raise RuntimeError(f"challenge-rejected: {response}")
    return response["challenge"]


def prepare_workspace(workspace: Path, sid: str, domain: str, key_id: str,
                      initial_label: str, force: bool = False) -> dict:
    workspace.mkdir(parents=True, exist_ok=True)
    database = workspace / "registry.db"
    snapshot_path = workspace / "snapshot.json"
    enrollment_path = workspace / "enrollment.json"
    existing = [path for path in (database, snapshot_path, enrollment_path) if path.exists()]
    if existing and not force:
        raise ValueError(f"refusing to replace existing A3 workspace; pass --force: {existing[0]}")
    for path in existing:
        path.unlink()

    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    initial = digest(initial_label)
    fingerprint = sha256(public_bytes).hexdigest()
    created = utc_now()
    revision = git_revision()
    enrollment = {
        "schema": "iepp-a3-enrollment-v2",
        "sid": sid,
        "domain": domain,
        "key_id": key_id,
        "public_key": public_bytes.hex(),
        "public_key_fingerprint_sha256": fingerprint,
        "initial_state": initial.hex(),
        "allowed_entropy_sources": ["os.urandom"],
        "created_at_utc": created,
        "iepp_source_revision": revision,
    }
    snapshot = {
        "schema": "iepp-a3-test-snapshot-v2",
        "test_only_cloned_private_key": True,
        "warning": "LAB KEY ONLY. NEVER USE THIS FILE AS A PRODUCTION CREDENTIAL.",
        "sid": sid,
        "domain": domain,
        "key_id": key_id,
        "private_key": private_bytes.hex(),
        "public_key_fingerprint_sha256": fingerprint,
        "counter": 0,
        "canonical_head": initial.hex(),
        "snapshot_point": "BEFORE_CHALLENGE",
        "challenge": None,
        "created_at_utc": created,
        "iepp_source_revision": revision,
    }
    write_json(enrollment_path, enrollment)
    write_json(snapshot_path, snapshot)
    store = SQLiteCanonicalStore(database)
    store.enroll(sid, initial)
    store.close()
    return {"workspace": str(workspace), "database": str(database),
            "enrollment": str(enrollment_path), "snapshot": str(snapshot_path),
            "public_key_fingerprint_sha256": fingerprint}


def snapshot_at_head(snapshot: dict, counter: int, canonical_head: str) -> dict:
    return {**snapshot, "counter": counter, "canonical_head": canonical_head,
            "snapshot_point": "BEFORE_CHALLENGE", "challenge": None}


def build_candidate(snapshot: dict, branch_id: str, trial_id: str, case_id: str,
                    challenge_value: dict, entropy: bytes | None = None) -> dict:
    private_bytes = bytes.fromhex(snapshot["private_key"])
    if len(private_bytes) != 32:
        raise ValueError("invalid-test-private-key-length")
    private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)
    prover = Prover(
        snapshot["sid"], snapshot["domain"], snapshot["key_id"], private_key,
        bytes.fromhex(snapshot["canonical_head"]), int(snapshot["counter"]),
    )
    challenge = challenge_from_dict(challenge_value)
    if challenge.sid != prover.sid or challenge.domain != prover.domain:
        raise ValueError("snapshot-challenge-binding-mismatch")
    runtime_commitment = hash_parts(
        b"IEPP-A3-Runtime-v1",
        platform.node().encode(),
        platform.python_version().encode(),
        branch_id.encode(),
        trial_id.encode(),
    )
    evidence = prover.transition(
        challenge,
        entropy if entropy is not None else os.urandom(32),
        "os.urandom",
        runtime_commitment,
    )
    return {
        "schema": "iepp-a3-signed-candidate-v2",
        "experiment": "A3_VM_SNAPSHOT_SAME_CREDENTIAL_FORK",
        "trial_id": trial_id,
        "case_id": case_id,
        "branch_id": branch_id,
        "snapshot_point": snapshot["snapshot_point"],
        "challenge_issued_before_restore": snapshot["snapshot_point"] == "AFTER_CHALLENGE",
        "public_key_fingerprint_sha256": snapshot["public_key_fingerprint_sha256"],
        "iepp_source_revision": snapshot["iepp_source_revision"],
        "created_at_utc": utc_now(),
        "evidence": evidence_to_dict(evidence),
    }


def submit_candidate(registry_url: str, candidate: dict) -> dict:
    return http_json(registry_url.rstrip("/") + "/v1/transition", candidate["evidence"])


def cmd_prepare(args: argparse.Namespace) -> int:
    if args.snapshot_point != "BEFORE_CHALLENGE":
        raise SystemExit("prepare supports BEFORE_CHALLENGE; start the registry, then use bind-challenge")
    try:
        result = prepare_workspace(Path(args.workspace), args.sid, args.domain, args.key_id,
                                   args.initial_label, args.force)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_bind_challenge(args: argparse.Namespace) -> int:
    path = Path(args.snapshot)
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["challenge"] = issue_challenge(
        args.registry_url, snapshot["sid"], snapshot["domain"], args.ttl
    )
    snapshot["snapshot_point"] = "AFTER_CHALLENGE"
    snapshot["challenge_bound_at_utc"] = utc_now()
    target = Path(args.output) if args.output else path
    write_json(target, snapshot)
    print(json.dumps({"snapshot": str(target), "snapshot_point": "AFTER_CHALLENGE",
                      "challenge_id": snapshot["challenge"]["challenge_id"]}, indent=2))
    return 0


def cmd_candidate(args: argparse.Namespace) -> int:
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    challenge = snapshot.get("challenge")
    if challenge is None:
        if not args.registry_url:
            raise SystemExit("--registry-url is required for a post-restore challenge")
        challenge = issue_challenge(args.registry_url, snapshot["sid"], snapshot["domain"], args.ttl)
    entropy = bytes.fromhex(args.entropy_hex) if args.entropy_hex else None
    candidate = build_candidate(snapshot, args.branch_id, args.trial_id, args.case_id,
                                challenge, entropy)
    write_json(Path(args.output), candidate)
    print(json.dumps(candidate, indent=2, sort_keys=True))
    return 0


def cmd_submit(args: argparse.Namespace) -> int:
    candidate = json.loads(Path(args.candidate).read_text(encoding="utf-8"))
    barrier_ns = args.barrier_epoch_ns or time.time_ns()
    wait_for_barrier(barrier_ns, args.delay_ms)
    sent_ns = time.time_ns()
    started_ns = time.monotonic_ns()
    try:
        decision = submit_candidate(args.registry_url, candidate)
        transport_ok = True
        transport_error = None
    except RuntimeError as error:
        decision = {"accepted": False, "reason": "TRANSPORT_FAILURE"}
        transport_ok = False
        transport_error = str(error)
    decided_ns = time.monotonic_ns()
    accepted = bool(decision.get("accepted"))
    evidence = candidate["evidence"]
    record = {
        "schema": "iepp-a3-client-result-v2",
        "experiment": candidate["experiment"],
        "trial_id": candidate["trial_id"],
        "case_id": candidate["case_id"],
        "branch_id": candidate["branch_id"],
        "snapshot_point": candidate["snapshot_point"],
        "challenge_issued_before_restore": candidate["challenge_issued_before_restore"],
        "public_key_fingerprint_sha256": candidate["public_key_fingerprint_sha256"],
        "iepp_source_revision": candidate["iepp_source_revision"],
        "host": platform.node(),
        "runtime_version": platform.python_version(),
        "challenge_id": evidence["challenge_id"],
        "evidence_id": evidence["evidence_id"],
        "signature_present": bool(evidence["signature"]),
        "presented_predecessor": evidence["previous"],
        "candidate_successor": evidence["state"],
        "barrier_epoch_ns": barrier_ns,
        "configured_delay_ms": args.delay_ms,
        "client_send_epoch_ns": sent_ns,
        "client_round_trip_ms": (decided_ns - started_ns) / 1_000_000,
        "transport_ok": transport_ok,
        "transport_error": transport_error,
        "registry_reason": decision.get("reason"),
        "canonical_accept": accepted,
        "canonical_head_before": decision.get("canonical_head_before"),
        "canonical_head_after": decision.get("canonical_head_after"),
        "protected_action": "EXECUTED_SIMULATED" if accepted else "BLOCKED",
        "entropy_health_status": "NOT_EVALUATED",
        "recorded_at_utc": utc_now(),
    }
    append_jsonl(Path(args.log), record)
    print(json.dumps(record, indent=2, sort_keys=True))
    if not transport_ok:
        return 3
    return 0 if accepted else 2


def check_rows(rows: list[dict]) -> dict:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(row["trial_id"], []).append(row)
    failures = []
    for trial_id, items in groups.items():
        accepted = sum(bool(item.get("canonical_accept")) for item in items)
        executed = sum(item.get("protected_action") == "EXECUTED_SIMULATED" for item in items)
        transports = all(item.get("transport_ok") for item in items)
        branches = {item.get("branch_id") for item in items}
        accepted_heads = {item.get("canonical_head_after") for item in items
                          if item.get("canonical_accept")}
        if accepted != 1 or executed != 1 or not transports or branches != {"A", "B"} or len(accepted_heads) != 1:
            failures.append({
                "trial_id": trial_id,
                "records": len(items),
                "branches": sorted(str(branch) for branch in branches),
                "accepted": accepted,
                "protected_actions_executed": executed,
                "transport_ok": transports,
                "accepted_heads": sorted(str(head) for head in accepted_heads),
            })
    return {
        "schema": "iepp-a3-check-v2",
        "trials": len(groups),
        "records": len(rows),
        "failures": failures,
        "passed": bool(groups) and not failures,
        "invariant": "exactly one accepted branch and one simulated protected action per two-branch trial",
        "claim_scope": "L1 single online registry with cooperative policy gate",
    }


def cmd_check(args: argparse.Namespace) -> int:
    path = Path(args.log)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    summary = check_rows(rows)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


def cmd_head(args: argparse.Namespace) -> int:
    query = urlencode({"sid": args.sid})
    value = http_json(args.registry_url.rstrip("/") + "/v1/head?" + query)
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0 if value.get("ok") else 1


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare", help="create lab key, enrollment, snapshot, and registry DB")
    prepare.add_argument("--workspace", required=True)
    prepare.add_argument("--sid", default="a3-entity")
    prepare.add_argument("--domain", default="iepp.a3.safe-resume")
    prepare.add_argument("--key-id", "--credential-id", dest="key_id", default="a3-shared-test-key")
    prepare.add_argument("--initial-label", default="a3-canonical-p0")
    prepare.add_argument("--snapshot-point", choices=("BEFORE_CHALLENGE", "AFTER_CHALLENGE"),
                         default="BEFORE_CHALLENGE")
    prepare.add_argument("--force", action="store_true")
    prepare.set_defaults(func=cmd_prepare)

    bind = commands.add_parser("bind-challenge", help="store a real server challenge before VM snapshot")
    bind.add_argument("--snapshot", required=True)
    bind.add_argument("--registry-url", required=True)
    bind.add_argument("--ttl", type=int, default=900)
    bind.add_argument("--output")
    bind.set_defaults(func=cmd_bind_challenge)

    candidate = commands.add_parser("candidate", help="sign one branch's candidate transition")
    candidate.add_argument("--snapshot", required=True)
    candidate.add_argument("--branch-id", choices=("A", "B"), required=True)
    candidate.add_argument("--trial-id", required=True)
    candidate.add_argument("--case-id", required=True)
    candidate.add_argument("--registry-url")
    candidate.add_argument("--ttl", type=int, default=30)
    candidate.add_argument("--entropy-hex")
    candidate.add_argument("--output", required=True)
    candidate.set_defaults(func=cmd_candidate)

    submit = commands.add_parser("submit", help="submit to registry and gate a simulated action")
    submit.add_argument("--registry-url", required=True)
    submit.add_argument("--candidate", required=True)
    submit.add_argument("--log", required=True)
    submit.add_argument("--barrier-epoch-ns", type=int)
    submit.add_argument("--delay-ms", type=int, default=0)
    submit.set_defaults(func=cmd_submit)

    check = commands.add_parser("check")
    check.add_argument("--log", required=True)
    check.set_defaults(func=cmd_check)

    head = commands.add_parser("head")
    head.add_argument("--registry-url", required=True)
    head.add_argument("--sid", default="a3-entity")
    head.set_defaults(func=cmd_head)
    return root


if __name__ == "__main__":
    parsed = parser().parse_args()
    raise SystemExit(parsed.func(parsed))

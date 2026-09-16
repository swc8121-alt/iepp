#!/usr/bin/env python3
"""One-node live Azure CVM/MAA/vTPM smoke test with non-secret JSON output."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import time

from core import AtomicRegistry, ChallengeAuthority, Prover, hash_parts, public_bytes
from azure_cvm_attester import attest_snp_platform
from l2_attestation import AttestationBinding, AzureAttestationPolicy, AzureMaaJwtVerifier, L2AttestedRegistry
from tpm_sealed_key import TpmSealedKey, TpmSealedKeyError


def sealed_key_at(directory: Path) -> TpmSealedKey:
    return TpmSealedKey(directory / "iepp.pub", directory / "iepp.priv", directory / "primary.ctx")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issuer", required=True, help="MAA issuer base URL from the deployment output")
    parser.add_argument("--key-directory", type=Path, default=Path("/var/lib/iepp-l2/key"))
    parser.add_argument("--tool-root", type=Path, default=Path("/opt/cvm-attestation-tools/cvm-attestation"))
    parser.add_argument("--unseal-only", action="store_true", help="Probe whether copied sealed blobs unseal here")
    args = parser.parse_args()

    sealed = sealed_key_at(args.key_directory)
    if args.unseal_only:
        try:
            sealed.unseal()
        except TpmSealedKeyError:
            print(json.dumps({"probe": "copied-sealed-key", "unseal": "REJECTED"}, sort_keys=True))
            return 0
        print(json.dumps({"probe": "copied-sealed-key", "unseal": "UNEXPECTED_SUCCESS"}, sort_keys=True))
        return 3

    if sealed.public_blob.exists() or sealed.private_blob.exists():
        key = sealed.unseal()
        key_origin = "existing-vtpm-sealed"
        public = public_bytes(key.public_key())
    else:
        sealed, public = TpmSealedKey.seal_new(args.key_directory)
        key = sealed.unseal()
        key_origin = "new-vtpm-sealed"

    now = int(time.time())
    sid, domain = "azure-cvm-node", "iepp.azure.l2"
    initial = sha256(b"IEPP-L2-live-initial-v1" + public).digest()
    runtime = hash_parts(
        b"IEPP-L2-Runtime-v1",
        Path("/proc/version").read_bytes(),
        b"Azure/cvm-attestation-tools@d42eb2dad2335ab9e516bb69180a227d4a10f86c",
    )
    challenges = ChallengeAuthority()
    base = AtomicRegistry("live-smoke-registry", challenges)
    base.enroll(sid, domain, initial, "vtpm-sealed-ed25519-1", key.public_key(), {"os.urandom"})
    prover = Prover(sid, domain, "vtpm-sealed-ed25519-1", key, initial)
    challenge = challenges.issue(sid, domain, now=now, ttl=120)
    binding = AttestationBinding.for_transition(
        challenge, 1, initial, prover.key_id, public, runtime,
    )
    token = attest_snp_platform(binding, args.issuer, args.tool_root)
    evidence = prover.transition(challenge, os.urandom(32), "os.urandom", runtime, token.encode())
    verifier = AzureMaaJwtVerifier(AzureAttestationPolicy(args.issuer))
    accepted, reason = L2AttestedRegistry(base, verifier).verify_and_advance(evidence, token, int(time.time()))
    result = {
        "attestation_sha256": sha256(token.encode()).hexdigest(),
        "counter": evidence.counter,
        "evidence_id": evidence.evidence_id().hex(),
        "key_origin": key_origin,
        "result": reason,
        "token_not_exported": True,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())

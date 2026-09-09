from base64 import b64encode, urlsafe_b64encode
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa
from cryptography.x509.oid import NameOID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import AtomicRegistry, ChallengeAuthority, Prover, public_bytes
from l2_attestation import (
    AttestationBinding,
    AzureAttestationPolicy,
    AzureMaaJwtVerifier,
    L2AttestedRegistry,
)
from tpm_sealed_key import TpmSealedKey, TpmSealedKeyError


def b64url(value: bytes) -> str:
    return urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class TokenAuthority:
    def __init__(self, issuer: str):
        self.issuer = issuer
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "IEPP test MAA")])
        now = datetime.now(timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(self.key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=1))
            .sign(self.key, hashes.SHA256())
        )
        der = cert.public_bytes(serialization.Encoding.DER)
        self.keyset = {"keys": [{"kid": "test-key", "kty": "RSA", "x5c": [b64encode(der).decode()]}]}

    def issue(self, binding: AttestationBinding, now: int = 100, **updates) -> str:
        claims = {
            "iss": self.issuer,
            "iat": now,
            "nbf": now,
            "exp": now + 600,
            "x-ms-attestation-type": "sevsnpvm",
            "x-ms-compliance-status": "azure-compliant-cvm",
            "x-ms-runtime": {
                "user-data": binding.azure_user_data_digest(),
                "vm-configuration": {"secure-boot": True, "tpm-enabled": True, "tpm-persisted": True},
            },
        }
        for key, value in updates.items():
            if key == "runtime":
                claims["x-ms-runtime"] = value
            else:
                claims[key] = value
        header = {"alg": "RS256", "typ": "JWT", "kid": "test-key", "jku": self.issuer + "/certs"}
        encoded_header = b64url(json.dumps(header, separators=(",", ":")).encode())
        encoded_claims = b64url(json.dumps(claims, separators=(",", ":")).encode())
        signing_input = f"{encoded_header}.{encoded_claims}".encode("ascii")
        signature = self.key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        return f"{encoded_header}.{encoded_claims}.{b64url(signature)}"


def setup_l2():
    sid, domain = "entity-l2", "iepp.l2.test"
    initial = sha256(b"initial-l2").digest()
    key = ed25519.Ed25519PrivateKey.generate()
    challenges = ChallengeAuthority()
    base = AtomicRegistry("registry-l2", challenges)
    base.enroll(sid, domain, initial, "sealed-key-1", key.public_key(), {"test.entropy"})
    prover = Prover(sid, domain, "sealed-key-1", key, initial)
    issuer = "https://sharedkrc.krc.attest.azure.net"
    authority = TokenAuthority(issuer)
    verifier = AzureMaaJwtVerifier(AzureAttestationPolicy(issuer), lambda _: authority.keyset)
    return prover, L2AttestedRegistry(base, verifier), challenges, authority


def bound_token(prover, challenge, authority, runtime=b"runtime", now=100, **claims):
    binding = AttestationBinding.for_transition(
        challenge,
        prover.counter + 1,
        prover.state,
        prover.key_id,
        public_bytes(prover.private_key.public_key()),
        runtime,
    )
    return authority.issue(binding, now, **claims)


class L2AttestationTests(unittest.TestCase):
    def test_valid_hardware_bound_transition(self):
        prover, registry, challenges, authority = setup_l2()
        challenge = challenges.issue(prover.sid, prover.domain, now=100, ttl=30, nonce=b"a" * 32)
        token = bound_token(prover, challenge, authority)
        evidence = prover.transition(challenge, b"entropy", "test.entropy", b"runtime", token.encode())
        self.assertEqual(registry.verify_and_advance(evidence, token, 101), (True, "CONTINUITY_VALID"))

    def test_signature_tamper_is_rejected_without_consuming_challenge(self):
        prover, registry, challenges, authority = setup_l2()
        challenge = challenges.issue(prover.sid, prover.domain, now=100, ttl=30)
        token = bound_token(prover, challenge, authority)
        evidence = prover.transition(challenge, b"entropy", "test.entropy", b"runtime", token.encode())
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        replacement = "A" if encoded_signature[0] != "A" else "B"
        tampered = f"{encoded_header}.{encoded_payload}.{replacement}{encoded_signature[1:]}"
        self.assertEqual(registry.verify_and_advance(evidence, tampered, 101)[1], "ATTESTATION_COMMITMENT_MISMATCH")
        self.assertFalse(challenges.inspect(challenge.challenge_id)[1])

        forged_evidence = prover.clone().transition(challenge, b"other", "test.entropy", b"runtime", tampered.encode())
        self.assertEqual(registry.verify_and_advance(forged_evidence, tampered, 101)[1], "ATTESTATION_SIGNATURE_INVALID")
        self.assertFalse(challenges.inspect(challenge.challenge_id)[1])

    def test_wrong_binding_expiry_and_platform_are_rejected(self):
        cases = [
            ({"digest": "0" * 128}, "ATTESTATION_BINDING_INVALID"),
            ({"exp": 50}, "ATTESTATION_EXPIRED"),
            ({"x-ms-attestation-type": "azurevm"}, "ATTESTATION_PLATFORM_REJECTED"),
            ({"x-ms-compliance-status": "not-compliant"}, "ATTESTATION_PLATFORM_REJECTED"),
            ({"secure_boot": False}, "ATTESTATION_PLATFORM_REJECTED"),
            ({"tpm": False}, "ATTESTATION_PLATFORM_REJECTED"),
        ]
        for mutation, expected in cases:
            with self.subTest(mutation=mutation):
                prover, registry, challenges, authority = setup_l2()
                challenge = challenges.issue(prover.sid, prover.domain, now=100, ttl=30)
                binding = AttestationBinding.for_transition(
                    challenge, 1, prover.state, prover.key_id,
                    public_bytes(prover.private_key.public_key()), b"runtime",
                )
                updates = dict(mutation)
                digest = updates.pop("digest", binding.azure_user_data_digest())
                secure_boot = updates.pop("secure_boot", True)
                tpm = updates.pop("tpm", True)
                if "exp" in updates:
                    expiry = updates.pop("exp")
                    token_time = 0
                else:
                    expiry = 700
                    token_time = 100
                runtime = {
                    "user-data": digest,
                    "vm-configuration": {"secure-boot": secure_boot, "tpm-enabled": tpm},
                }
                token = authority.issue(binding, now=token_time, exp=expiry, runtime=runtime, **updates)
                evidence = prover.transition(challenge, b"entropy", "test.entropy", b"runtime", token.encode())
                self.assertEqual(registry.verify_and_advance(evidence, token, 101)[1], expected)
                self.assertFalse(challenges.inspect(challenge.challenge_id)[1])

    def test_wrong_issuer_and_unpinned_jku_are_rejected(self):
        prover, registry, challenges, authority = setup_l2()
        challenge = challenges.issue(prover.sid, prover.domain, now=100, ttl=30)
        binding = AttestationBinding.for_transition(
            challenge, 1, prover.state, prover.key_id,
            public_bytes(prover.private_key.public_key()), b"runtime",
        )
        token = authority.issue(binding, 100, iss="https://attacker.invalid")
        evidence = prover.transition(challenge, b"entropy", "test.entropy", b"runtime", token.encode())
        self.assertEqual(registry.verify_and_advance(evidence, token, 101)[1], "ATTESTATION_ISSUER_INVALID")

        valid = authority.issue(binding)
        header, payload, _ = valid.split(".")
        bad_header = {"alg": "RS256", "kid": "test-key", "jku": "https://attacker.invalid/certs"}
        encoded_header = b64url(json.dumps(bad_header).encode())
        signed = f"{encoded_header}.{payload}".encode()
        signature = authority.key.sign(signed, padding.PKCS1v15(), hashes.SHA256())
        bad_jku = f"{encoded_header}.{payload}.{b64url(signature)}"
        fresh_evidence = prover.clone().transition(challenge, b"entropy2", "test.entropy", b"runtime", bad_jku.encode())
        self.assertEqual(registry.verify_and_advance(fresh_evidence, bad_jku, 101)[1], "ATTESTATION_ISSUER_INVALID")

    def test_token_for_other_challenge_is_rejected(self):
        prover, registry, challenges, authority = setup_l2()
        original = challenges.issue(prover.sid, prover.domain, now=100, ttl=30, nonce=b"a" * 32)
        other = challenges.issue(prover.sid, prover.domain, now=100, ttl=30, nonce=b"b" * 32)
        token = bound_token(prover, original, authority)
        evidence = prover.transition(other, b"entropy", "test.entropy", b"runtime", token.encode())
        self.assertEqual(registry.verify_and_advance(evidence, token, 101)[1], "ATTESTATION_BINDING_INVALID")

    def test_attested_clone_fork_has_exactly_one_winner(self):
        prover, registry, challenges, authority = setup_l2()
        left, right = prover.clone(), prover.clone()
        cl = challenges.issue(prover.sid, prover.domain, now=100, ttl=30, nonce=b"l" * 32)
        cr = challenges.issue(prover.sid, prover.domain, now=100, ttl=30, nonce=b"r" * 32)
        tl = bound_token(left, cl, authority)
        tr = bound_token(right, cr, authority)
        el = left.transition(cl, b"left", "test.entropy", b"runtime", tl.encode())
        er = right.transition(cr, b"right", "test.entropy", b"runtime", tr.encode())
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda pair: registry.verify_and_advance(*pair, now=101), ((el, tl), (er, tr))))
        self.assertEqual(sum(ok for ok, _ in results), 1)
        self.assertIn("ROLLBACK_OR_LOSING_FORK", {reason for _, reason in results})


class TpmSealedKeyTests(unittest.TestCase):
    def test_secret_is_not_passed_in_command_arguments_and_unseals(self):
        calls = []
        sealed_inputs = []

        def runner(command, **kwargs):
            calls.append(tuple(command))
            if command[0] == "tpm2_create":
                sealed_inputs.append(kwargs.get("input"))
            output = b"s" * 32 if command[0] == "tpm2_unseal" else b""
            return subprocess.CompletedProcess(command, 0, output, b"")

        with tempfile.TemporaryDirectory() as directory:
            sealed, public = TpmSealedKey.seal_new(Path(directory), runner=runner)
            key = sealed.unseal(runner)
        self.assertEqual(len(public), 32)
        self.assertEqual(len(key.sign(b"test")), 64)
        flattened = " ".join(part for call in calls for part in call)
        self.assertNotIn((b"s" * 32).hex(), flattened)
        self.assertTrue(any(call[0] == "tpm2_create" and call[call.index("-i") + 1] == "-" for call in calls))
        self.assertEqual(len(sealed_inputs), 1)
        self.assertEqual(len(sealed_inputs[0]), 32)

    def test_bad_unseal_length_fails_closed(self):
        def runner(command, **kwargs):
            output = b"short" if command[0] == "tpm2_unseal" else b""
            return subprocess.CompletedProcess(command, 0, output, b"")

        sealed = TpmSealedKey(Path("pub"), Path("priv"), Path("primary"))
        with self.assertRaises(TpmSealedKeyError):
            sealed.unseal(runner)


if __name__ == "__main__":
    unittest.main()

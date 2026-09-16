"""Azure Confidential VM attestation policy gate for IEPP L2 experiments.

The Microsoft CVM attestation tool places SHA-512(json.dumps(user_claims)) in
the hardware-attested ``x-ms-runtime.user-data`` claim.  This module builds
that input deterministically and verifies the returned MAA JWT before the L1
atomic registry is allowed to consume a challenge or advance state.
"""

from __future__ import annotations

from base64 import b64decode
from binascii import Error as Base64Error
from dataclasses import dataclass
from hashlib import sha256, sha512
import json
import time
from typing import Any, Callable
from urllib.request import urlopen

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.hashes import SHA256

from core import AtomicRegistry, Challenge, TransitionEvidence, hash_parts, public_bytes


def _b64url_decode(value: str) -> bytes:
    return b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)


def _strict_integer(claims: dict[str, Any], name: str) -> int:
    value = claims.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AttestationError("ATTESTATION_TIME_INVALID", f"missing or invalid {name}")
    return int(value)


@dataclass(frozen=True)
class AttestationBinding:
    """The protocol values covered by the CVM hardware report."""

    sid: str
    domain: str
    challenge_id: bytes
    challenge_nonce: bytes
    challenge_expires_at: int
    counter: int
    previous: bytes
    key_id: str
    public_key_hash: bytes
    runtime_commitment: bytes

    @classmethod
    def for_transition(
        cls,
        challenge: Challenge,
        counter: int,
        previous: bytes,
        key_id: str,
        public_key: bytes,
        runtime_commitment: bytes,
    ) -> "AttestationBinding":
        return cls(
            challenge.sid,
            challenge.domain,
            challenge.challenge_id,
            challenge.nonce,
            challenge.expires_at,
            counter,
            previous,
            key_id,
            sha256(public_key).digest(),
            runtime_commitment,
        )

    @classmethod
    def for_evidence(cls, evidence: TransitionEvidence, public_key: bytes) -> "AttestationBinding":
        return cls(
            evidence.sid,
            evidence.domain,
            evidence.challenge_id,
            evidence.challenge_nonce,
            evidence.challenge_expires_at,
            evidence.counter,
            evidence.previous,
            evidence.key_id,
            sha256(public_key).digest(),
            evidence.runtime_commitment,
        )

    def user_claims(self) -> dict[str, dict[str, str]]:
        # Keep insertion order stable: Azure's reference tool hashes Python's
        # default json.dumps output rather than a canonical JSON encoding.
        return {
            "user-claims": {
                "iepp-binding-version": "IEPP-L2-Azure-v1",
                "sid": self.sid,
                "domain": self.domain,
                "challenge-id": self.challenge_id.hex(),
                "challenge-nonce": self.challenge_nonce.hex(),
                "challenge-expires-at": str(self.challenge_expires_at),
                "counter": str(self.counter),
                "previous": self.previous.hex(),
                "key-id": self.key_id,
                "public-key-sha256": self.public_key_hash.hex(),
                "runtime-commitment": self.runtime_commitment.hex(),
            }
        }

    def azure_user_data_digest(self) -> str:
        encoded = json.dumps(self.user_claims()).encode("utf-8")
        return sha512(encoded).hexdigest().upper()


@dataclass(frozen=True)
class AzureAttestationPolicy:
    issuer: str
    allowed_attestation_types: frozenset[str] = frozenset({"sevsnpvm"})
    required_compliance_status: str = "azure-compliant-cvm"
    require_secure_boot: bool = True
    require_tpm: bool = True
    maximum_token_age_seconds: int = 300
    clock_skew_seconds: int = 30
    audience: str | None = None

    @property
    def jwks_url(self) -> str:
        return self.issuer.rstrip("/") + "/certs"


class AttestationError(ValueError):
    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


JwksLoader = Callable[[str], dict[str, Any]]


def fetch_jwks(url: str) -> dict[str, Any]:
    """Fetch keys from the already policy-pinned MAA certificate endpoint."""

    with urlopen(url, timeout=5) as response:  # noqa: S310 - URL is policy-derived, not token-derived
        if response.status != 200:
            raise AttestationError("ATTESTATION_KEYS_UNAVAILABLE", f"HTTP {response.status}")
        return json.loads(response.read())


class AzureMaaJwtVerifier:
    def __init__(self, policy: AzureAttestationPolicy, jwks_loader: JwksLoader = fetch_jwks):
        self.policy = policy
        self.jwks_loader = jwks_loader

    @staticmethod
    def _decode_json(segment: str, reason: str) -> dict[str, Any]:
        try:
            value = json.loads(_b64url_decode(segment))
        except (Base64Error, ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AttestationError(reason, "invalid JWT JSON") from exc
        if not isinstance(value, dict):
            raise AttestationError(reason, "JWT section is not an object")
        return value

    @staticmethod
    def _rsa_key(jwk: dict[str, Any]) -> rsa.RSAPublicKey:
        try:
            x5c = jwk.get("x5c")
            if isinstance(x5c, list) and x5c:
                cert = x509.load_der_x509_certificate(b64decode(x5c[0], validate=True))
                key = cert.public_key()
                if not isinstance(key, rsa.RSAPublicKey):
                    raise ValueError("certificate key is not RSA")
                return key
            n = int.from_bytes(_b64url_decode(jwk["n"]), "big")
            e = int.from_bytes(_b64url_decode(jwk["e"]), "big")
            return rsa.RSAPublicNumbers(e, n).public_key()
        except (KeyError, ValueError, TypeError) as exc:
            raise AttestationError("ATTESTATION_KEYS_INVALID", "invalid RSA JWK") from exc

    def _verify_signature(
        self, encoded_header: str, encoded_payload: str, encoded_signature: str,
        header: dict[str, Any],
    ) -> None:
        if header.get("alg") != "RS256" or header.get("typ") not in (None, "JWT"):
            raise AttestationError("ATTESTATION_ALGORITHM_INVALID", "only RS256 JWT is allowed")
        if header.get("jku") != self.policy.jwks_url:
            raise AttestationError("ATTESTATION_ISSUER_INVALID", "jku is not the pinned issuer endpoint")
        kid = header.get("kid")
        if not isinstance(kid, str) or not kid:
            raise AttestationError("ATTESTATION_KEYS_INVALID", "missing kid")
        try:
            keyset = self.jwks_loader(self.policy.jwks_url)
        except AttestationError:
            raise
        except Exception as exc:
            raise AttestationError("ATTESTATION_KEYS_UNAVAILABLE", str(exc)) from exc
        keys = keyset.get("keys", keyset.get("certificates", []))
        if not isinstance(keys, list):
            raise AttestationError("ATTESTATION_KEYS_INVALID", "key set is not a list")
        matches = [item for item in keys if isinstance(item, dict) and item.get("kid") == kid]
        if len(matches) != 1:
            raise AttestationError("ATTESTATION_KEYS_INVALID", "kid did not identify exactly one key")
        try:
            signature = _b64url_decode(encoded_signature)
        except (Base64Error, ValueError) as exc:
            raise AttestationError("ATTESTATION_FORMAT_INVALID", "invalid JWT signature encoding") from exc
        signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
        try:
            self._rsa_key(matches[0]).verify(signature, signing_input, padding.PKCS1v15(), SHA256())
        except (InvalidSignature, ValueError) as exc:
            raise AttestationError("ATTESTATION_SIGNATURE_INVALID", "JWT signature mismatch") from exc

    def verify(self, token: str, binding: AttestationBinding, now: int | None = None) -> dict[str, Any]:
        now = int(time.time()) if now is None else now
        if not isinstance(token, str) or len(token) > 1024 * 1024:
            raise AttestationError("ATTESTATION_FORMAT_INVALID", "JWT type or size is invalid")
        parts = token.split(".")
        if len(parts) != 3:
            raise AttestationError("ATTESTATION_FORMAT_INVALID", "JWT must have three sections")
        header = self._decode_json(parts[0], "ATTESTATION_FORMAT_INVALID")
        claims = self._decode_json(parts[1], "ATTESTATION_FORMAT_INVALID")
        self._verify_signature(*parts, header)

        if claims.get("iss") != self.policy.issuer:
            raise AttestationError("ATTESTATION_ISSUER_INVALID", "iss does not match policy")
        if self.policy.audience is not None:
            audience = claims.get("aud", [])
            audience = [audience] if isinstance(audience, str) else audience
            if not isinstance(audience, list) or self.policy.audience not in audience:
                raise AttestationError("ATTESTATION_AUDIENCE_INVALID", "aud does not match policy")

        exp, nbf, iat = (_strict_integer(claims, name) for name in ("exp", "nbf", "iat"))
        skew = self.policy.clock_skew_seconds
        if iat > exp or nbf > exp:
            raise AttestationError("ATTESTATION_TIME_INVALID", "inconsistent JWT times")
        if exp < now - skew:
            raise AttestationError("ATTESTATION_EXPIRED")
        if nbf > now + skew or iat > now + skew:
            raise AttestationError("ATTESTATION_TIME_INVALID", "token is not yet valid")
        if now - iat > self.policy.maximum_token_age_seconds + skew:
            raise AttestationError("ATTESTATION_EXPIRED", "token exceeds maximum policy age")

        nested = claims.get("x-ms-isolation-tee")
        if nested is not None and not isinstance(nested, dict):
            raise AttestationError("ATTESTATION_PLATFORM_REJECTED", "invalid isolation claim")
        platform = nested or claims
        if nested:
            for name in ("x-ms-attestation-type", "x-ms-compliance-status"):
                if name in claims and claims[name] != nested.get(name):
                    raise AttestationError("ATTESTATION_PLATFORM_REJECTED", f"conflicting {name}")

        attestation_type = platform.get("x-ms-attestation-type")
        compliance = platform.get("x-ms-compliance-status")
        if attestation_type not in self.policy.allowed_attestation_types:
            raise AttestationError("ATTESTATION_PLATFORM_REJECTED", "attestation type is not allowed")
        if compliance != self.policy.required_compliance_status:
            raise AttestationError("ATTESTATION_PLATFORM_REJECTED", "CVM compliance status rejected")

        runtime = platform.get("x-ms-runtime")
        if not isinstance(runtime, dict):
            raise AttestationError("ATTESTATION_PLATFORM_REJECTED", "missing runtime claims")
        configuration = runtime.get("vm-configuration")
        if not isinstance(configuration, dict):
            raise AttestationError("ATTESTATION_PLATFORM_REJECTED", "missing VM configuration")
        if self.policy.require_secure_boot and configuration.get("secure-boot") is not True:
            raise AttestationError("ATTESTATION_PLATFORM_REJECTED", "Secure Boot is not attested")
        if self.policy.require_tpm and configuration.get("tpm-enabled") is not True:
            raise AttestationError("ATTESTATION_PLATFORM_REJECTED", "vTPM is not attested")
        actual_digest = runtime.get("user-data")
        if not isinstance(actual_digest, str) or actual_digest.upper() != binding.azure_user_data_digest():
            raise AttestationError("ATTESTATION_BINDING_INVALID", "hardware report is bound to other IEPP data")
        return claims


class L2AttestedRegistry:
    """Fail-closed L2 policy wrapper around the L1 atomic transition engine."""

    def __init__(self, registry: AtomicRegistry, attestation_verifier: AzureMaaJwtVerifier):
        self.registry = registry
        self.attestation_verifier = attestation_verifier

    def verify_and_advance(
        self, evidence: TransitionEvidence, attestation_token: str, now: int | None = None,
    ) -> tuple[bool, str]:
        enrollment = self.registry.enrollments.get(evidence.sid)
        if enrollment is None:
            return False, "UNKNOWN_ENTITY"
        expected = hash_parts(b"IEPP-Attestation-v1", attestation_token.encode("utf-8"))
        if evidence.attestation_commitment != expected:
            return False, "ATTESTATION_COMMITMENT_MISMATCH"
        binding = AttestationBinding.for_evidence(evidence, public_bytes(enrollment.public_key))
        try:
            self.attestation_verifier.verify(attestation_token, binding, now)
        except AttestationError as exc:
            return False, exc.reason
        return self.registry.verify_and_advance(evidence, now)

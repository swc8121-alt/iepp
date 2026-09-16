"""Thin adapter to Microsoft's pinned CVM attestation reference tool.

This module deliberately imports the upstream tool only when called, keeping
normal IEPP CI platform-independent.  The deployment runbook pins the exact
upstream commit used by the experiment.
"""

from __future__ import annotations

from pathlib import Path
import sys
from urllib.parse import urlparse

from l2_attestation import AttestationBinding


class AzureCvmAttesterError(RuntimeError):
    pass


class _QuietLogger:
    """Upstream client logger interface that prevents raw JWT disclosure."""

    def debug(self, *_args, **_kwargs) -> None:
        pass

    def info(self, *_args, **_kwargs) -> None:
        pass

    def warning(self, *_args, **_kwargs) -> None:
        pass

    def error(self, *_args, **_kwargs) -> None:
        pass


def _validate_maa_issuer(issuer: str) -> str:
    parsed = urlparse(issuer)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".attest.azure.net")
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise AzureCvmAttesterError("MAA issuer must be an HTTPS Azure Attestation base URL")
    return issuer.rstrip("/")


def attest_snp_platform(
    binding: AttestationBinding,
    issuer: str,
    tool_root: Path = Path("/opt/cvm-attestation-tools/cvm-attestation"),
) -> str:
    """Return a raw MAA JWT whose hardware report covers ``binding``."""

    issuer = _validate_maa_issuer(issuer)
    tool_root = tool_root.resolve()
    if not (tool_root / "src" / "attestation_client.py").is_file():
        raise AzureCvmAttesterError(f"pinned Microsoft attestation tool not found at {tool_root}")
    sys.path.insert(0, str(tool_root))
    try:
        from src.attestation_client import (  # type: ignore[import-not-found]
            AttestationClient,
            AttestationClientParameters,
            Verifier,
        )
        from src.isolation import IsolationType  # type: ignore[import-not-found]
        endpoint = issuer + "/attest/SevSnpVm?api-version=2022-08-01"
        parameters = AttestationClientParameters(
            endpoint=endpoint,
            verifier=Verifier.MAA,
            isolation_type=IsolationType.SEV_SNP,
            claims=binding.user_claims(),
        )
        token = AttestationClient(_QuietLogger(), parameters).attest_platform()
    except AzureCvmAttesterError:
        raise
    except Exception as exc:
        raise AzureCvmAttesterError("CVM evidence collection or MAA attestation failed") from exc
    finally:
        if sys.path and sys.path[0] == str(tool_root):
            sys.path.pop(0)
    if isinstance(token, bytes):
        token = token.decode("ascii")
    if not isinstance(token, str) or token.count(".") != 2:
        raise AzureCvmAttesterError("MAA did not return a JWT")
    return token

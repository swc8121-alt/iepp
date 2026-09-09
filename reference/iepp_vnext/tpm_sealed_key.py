"""Minimal TPM2 sealed-secret adapter for the IEPP L2 experiment.

Ed25519 is retained as IEPP's signing algorithm.  Its 32-byte raw private key
is sealed by the CVM vTPM to a PCR policy and only materialized in process
memory after a successful unseal.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Callable, Sequence

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat


class TpmSealedKeyError(RuntimeError):
    pass


Runner = Callable[..., subprocess.CompletedProcess[bytes]]


@dataclass(frozen=True)
class TpmSealedKey:
    public_blob: Path
    private_blob: Path
    primary_context: Path
    pcr_policy: str = "sha256:0,1,2,3,4,7"

    @staticmethod
    def _run(runner: Runner, command: Sequence[str], **kwargs) -> subprocess.CompletedProcess[bytes]:
        try:
            return runner(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise TpmSealedKeyError(f"TPM command failed: {command[0]}") from exc

    @classmethod
    def seal_new(
        cls,
        directory: Path,
        pcr_policy: str = "sha256:0,1,2,3,4,7",
        runner: Runner = subprocess.run,
    ) -> tuple["TpmSealedKey", bytes]:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(directory, 0o700)
        primary = directory / "primary.ctx"
        policy = directory / "pcr.policy"
        public_blob = directory / "iepp.pub"
        private_blob = directory / "iepp.priv"
        key = Ed25519PrivateKey.generate()
        raw = key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        try:
            cls._run(runner, [
                "tpm2_createprimary", "-C", "o", "-g", "sha256", "-G", "rsa", "-c", str(primary),
            ])
            cls._run(runner, ["tpm2_createpolicy", "--policy-pcr", "-l", pcr_policy, "-L", str(policy)])
            cls._run(runner, [
                "tpm2_create", "-C", str(primary), "-g", "sha256", "-L", str(policy), "-i", "-",
                "-u", str(public_blob), "-r", str(private_blob),
            ], input=raw)
            for output in (primary, policy, public_blob, private_blob):
                if output.exists():
                    os.chmod(output, 0o600)
        finally:
            try:
                cls._run(runner, ["tpm2_flushcontext", str(primary)])
            except TpmSealedKeyError:
                pass
        return cls(public_blob, private_blob, primary, pcr_policy), public

    def unseal(self, runner: Runner = subprocess.run) -> Ed25519PrivateKey:
        if runner is subprocess.run and (not self.public_blob.exists() or not self.private_blob.exists()):
            raise TpmSealedKeyError("sealed key blobs are missing")
        with tempfile.TemporaryDirectory(prefix="iepp-tpm-") as temp:
            temp_path = Path(temp)
            primary = temp_path / "primary.ctx"
            loaded = temp_path / "loaded.ctx"
            session = temp_path / "policy.session"
            # Recreate the deterministic owner-hierarchy primary so blobs remain
            # usable after a reboot instead of trusting a stale saved context.
            self._run(runner, [
                "tpm2_createprimary", "-C", "o", "-g", "sha256", "-G", "rsa",
                "-c", str(primary),
            ])
            self._run(runner, [
                "tpm2_load", "-C", str(primary), "-u", str(self.public_blob),
                "-r", str(self.private_blob), "-c", str(loaded),
            ])
            self._run(runner, ["tpm2_startauthsession", "--policy-session", "-S", str(session)])
            try:
                self._run(runner, ["tpm2_policypcr", "-S", str(session), "-l", self.pcr_policy])
                result = self._run(runner, ["tpm2_unseal", "-c", str(loaded), "-p", f"session:{session}"])
            finally:
                try:
                    self._run(runner, ["tpm2_flushcontext", str(session)])
                except TpmSealedKeyError:
                    pass
                for context in (loaded, primary):
                    try:
                        self._run(runner, ["tpm2_flushcontext", str(context)])
                    except TpmSealedKeyError:
                        pass
        if len(result.stdout) != 32:
            raise TpmSealedKeyError("TPM returned an invalid Ed25519 private-key length")
        return Ed25519PrivateKey.from_private_bytes(result.stdout)

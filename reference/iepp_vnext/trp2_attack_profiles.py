"""Machine-readable TRP 2.0 adversary profiles used by future benchmarks."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AttackProfile:
    name: str
    transcript: bool = True
    code_copy: bool = False
    partial_state: bool = False
    snapshot: bool = False
    signing_key: bool = False
    entropy_influence: bool = False
    verifier_influence: bool = False
    registry_influence: bool = False


PROFILES = {
    "A0": AttackProfile("observer"),
    "A1": AttackProfile("software_clone", code_copy=True),
    "A2": AttackProfile("partial_state", code_copy=True, partial_state=True),
    "A3": AttackProfile("snapshot", code_copy=True, partial_state=True, snapshot=True),
    "A4": AttackProfile("entropy_influence", code_copy=True, entropy_influence=True),
    "A5": AttackProfile("key_plus_state", code_copy=True, partial_state=True,
                        snapshot=True, signing_key=True),
    "A6": AttackProfile("platform_or_registry", code_copy=True, partial_state=True,
                        snapshot=True, signing_key=True, entropy_influence=True,
                        verifier_influence=True, registry_influence=True),
}

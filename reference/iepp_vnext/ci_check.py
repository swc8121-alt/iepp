"""Fast deterministic gate used by GitHub Actions."""

from benchmark import run as run_core
from bounded_model import check as check_model
from fault_injection import run as run_faults


def main() -> None:
    core = run_core(valid_steps=5_000, attack_trials=1_000, fork_races=100)
    assert core["valid_chain"]["accepted"] == 5_000
    assert core["valid_chain"]["audit_chain_valid"] is True
    assert core["attacks"]["continuity_false_accepts"] == 0
    assert core["fork_races"]["double_accept"] == 0

    faults = run_faults(steps=500)
    assert faults["shuffled_delivery"]["eventual_counter"] == 500
    assert faults["duplicate_redelivery"] == {"REPLAY_DETECTED": 500}
    assert faults["expired_delay"] == [False, "CHALLENGE_EXPIRED"]

    model = check_model(depth=6, challenge_count=6)
    assert model["all_invariants_hold"] is True
    assert model["violations"] == []

    print("IEPP CI gate passed")


if __name__ == "__main__":
    main()

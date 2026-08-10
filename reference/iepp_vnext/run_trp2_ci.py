"""Dependency-free CI entry point for the TRP 2.0 bounded security game."""

from trp2_benchmark import assert_expected, run


if __name__ == "__main__":
    result = run(trials=1000)
    assert_expected(result)
    print("TRP2 bounded security game: PASS")
    for metric in (
        "replay_accept_rate",
        "rollback_accept_rate",
        "unsigned_or_wrong_key_forgery_accept_rate",
        "dual_canonical_accept_rate",
        "key_plus_state_boundary_accept_rate",
    ):
        print(f"{metric}={result[metric]:.6f}")

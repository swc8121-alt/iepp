from trp2_benchmark import assert_expected, run


def test_trp2_security_game():
    result = run(trials=100)
    assert_expected(result)


def test_expected_boundary_is_explicit():
    result = run(trials=25)
    assert result["key_plus_state_boundary_accept_rate"] == 1.0
    assert result["dual_canonical_accept_rate"] == 0.0

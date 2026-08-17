from cardivex.calibration import domain_uncertainty, scenario_calibration_error, uncertainty_band


def test_uncertainty_band_stays_bounded():
    band = uncertainty_band([0.2, 0.4, 0.6])
    assert 0.0 <= band.lower <= band.mean <= band.upper <= 1.0
    assert band.count == 3


def test_domain_uncertainty_is_deterministic():
    result = domain_uncertainty([
        {"a": 0.2, "b": 0.5},
        {"a": 0.4, "b": 0.7},
    ])
    assert result["a"].mean == 0.3
    assert result["b"].mean == 0.6


def test_calibration_error_reports_mae_and_max():
    result = scenario_calibration_error({"a": 0.2, "b": 0.8}, {"a": 0.3, "b": 0.6})
    assert result["a"] == 0.1
    assert result["b"] == 0.2
    assert result["mae"] == 0.15
    assert result["max_error"] == 0.2

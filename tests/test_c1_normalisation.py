from config import ADDITIVE_METRICS


def test_unit_columns_in_additive_metrics():
    unit_cols = [
        "rogues",
        "fast_units",
        "heavy_units",
        "ranged_units",
        "artillery_units",
        "light_units",
        "next_age_fast_units",
        "next_age_heavy_units",
        "next_age_ranged_units",
        "next_age_artillery_units",
        "next_age_light_units",
    ]
    for col in unit_cols:
        assert col in ADDITIVE_METRICS, f"{col} missing from ADDITIVE_METRICS"


def test_population_in_additive_metrics():
    assert "Population" in ADDITIVE_METRICS


def test_unscored_boost_cols_in_additive_metrics():
    for col in ("Coin %", "Supplies %", "Medal Boost"):
        assert col in ADDITIVE_METRICS, f"{col} missing from ADDITIVE_METRICS"


def test_additive_metrics_subset_of_weightable_columns():
    """Every scoring column must also have a weight slider and era stat."""
    from config import WEIGHTABLE_COLUMNS

    for col in ADDITIVE_METRICS:
        assert (
            col in WEIGHTABLE_COLUMNS
        ), f"{col} is in ADDITIVE_METRICS but missing from WEIGHTABLE_COLUMNS"


def test_c1_score_multiplier_exists():
    from config import C1_SCORE_MULTIPLIER

    assert isinstance(C1_SCORE_MULTIPLIER, (int, float))
    assert C1_SCORE_MULTIPLIER > 0


def test_scoring_mode_session_key_exists():
    from config import SessionKeys

    assert hasattr(SessionKeys, "SCORING_MODE")
    assert SessionKeys.SCORING_MODE == "scoring_mode"

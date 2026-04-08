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


def test_era_stats_covers_all_additive_metrics():
    """calculate_era_stats must produce max values for every ADDITIVE_METRICS column present in df."""
    import pandas as pd
    import calculations

    sample_data = {
        "Era": ["SpaceAgeSpaceHub", "SpaceAgeSpaceHub", "BronzeAge"],
        "forge_points": [100.0, 576.0, 10.0],
        "Coin %": [0.0, 300.0, 0.0],
        "Medal Boost": [0.0, 50.0, 0.0],
        "Nbr of squares (Avg)": [9.0, 36.0, 4.0],
    }
    df = pd.DataFrame(sample_data)
    stats = calculations.calculate_era_stats(df)
    assert not stats.empty
    assert ("Coin %", "max") in stats.columns, "Coin % max missing from era stats"
    assert (
        "Medal Boost",
        "max",
    ) in stats.columns, "Medal Boost max missing from era stats"
    assert stats.loc["SpaceAgeSpaceHub", ("forge_points", "max")] == 576.0
    assert stats.loc["SpaceAgeSpaceHub", ("Coin %", "max")] == 300.0

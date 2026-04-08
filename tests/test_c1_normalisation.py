import pandas as pd

import calculations
from config import ADDITIVE_METRICS, C1_SCORE_MULTIPLIER


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
    assert isinstance(C1_SCORE_MULTIPLIER, (int, float))
    assert C1_SCORE_MULTIPLIER > 0


def test_scoring_mode_session_key_exists():
    from config import SessionKeys

    assert hasattr(SessionKeys, "SCORING_MODE")
    assert SessionKeys.SCORING_MODE == "scoring_mode"


def test_era_stats_covers_all_additive_metrics():
    """calculate_era_stats must produce max values for every ADDITIVE_METRICS column present in df."""
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


def _make_two_building_df():
    """Two buildings in the same era: one with era-max FP, one with half."""
    return pd.DataFrame(
        {
            "name": ["best_fp", "half_fp"],
            "Era": ["SpaceAgeSpaceHub", "SpaceAgeSpaceHub"],
            "forge_points": [576.0, 288.0],
            "goods": [0.0, 0.0],
            "Nbr of squares (Avg)": [9.0, 9.0],
        }
    )


def test_c1_normalised_score_max_building():
    """Best-in-era building scores weight * C1_SCORE_MULTIPLIER on that column."""
    df = _make_two_building_df()
    era_stats = calculations.calculate_era_stats(df)
    weights = {"forge_points": 1.0}
    result = calculations.calculate_direct_weighted_efficiency(
        df=df.copy(),
        user_weights=weights,
        user_context={},
        era_stats_df=era_stats,
    )
    best_row = result[result["name"] == "best_fp"].iloc[0]
    expected_score = 1.0 * C1_SCORE_MULTIPLIER  # norm=1.0, weight=1.0
    assert (
        abs(best_row["Total Score"] - expected_score) < 0.01
    ), f"Expected Total Score ~{expected_score}, got {best_row['Total Score']}"


def test_c1_normalised_score_half_building():
    """Half-of-era-max building scores weight * C1_SCORE_MULTIPLIER * 0.5."""
    df = _make_two_building_df()
    era_stats = calculations.calculate_era_stats(df)
    weights = {"forge_points": 1.0}
    result = calculations.calculate_direct_weighted_efficiency(
        df=df.copy(),
        user_weights=weights,
        user_context={},
        era_stats_df=era_stats,
    )
    half_row = result[result["name"] == "half_fp"].iloc[0]
    expected_score = 0.5 * C1_SCORE_MULTIPLIER
    assert (
        abs(half_row["Total Score"] - expected_score) < 0.01
    ), f"Expected Total Score ~{expected_score}, got {half_row['Total Score']}"


def test_classic_mode_unchanged():
    """When era_stats_df=None, raw values are used (classic behaviour)."""
    df = _make_two_building_df()
    weights = {"forge_points": 1.0}
    result = calculations.calculate_direct_weighted_efficiency(
        df=df.copy(),
        user_weights=weights,
        user_context={},
        era_stats_df=None,
    )
    best_row = result[result["name"] == "best_fp"].iloc[0]
    # Classic: total_score = 576 * 1 = 576 (no multiplier applied)
    assert (
        abs(best_row["Total Score"] - 576.0) < 0.1
    ), f"Expected Total Score ~576, got {best_row['Total Score']}"


def test_c1_zero_value_building_scores_zero():
    """A building with zero production scores zero regardless of era max."""
    df_with_max = pd.DataFrame(
        {
            "name": ["best", "no_fp"],
            "Era": ["SpaceAgeSpaceHub", "SpaceAgeSpaceHub"],
            "forge_points": [576.0, 0.0],
            "goods": [0.0, 0.0],
            "Nbr of squares (Avg)": [9.0, 4.0],
        }
    )
    era_stats = calculations.calculate_era_stats(df_with_max)
    df_zero = df_with_max[df_with_max["name"] == "no_fp"].copy()
    weights = {"forge_points": 5.0}
    result = calculations.calculate_direct_weighted_efficiency(
        df=df_zero,
        user_weights=weights,
        user_context={},
        era_stats_df=era_stats,
    )
    assert result.iloc[0]["Total Score"] == 0.0

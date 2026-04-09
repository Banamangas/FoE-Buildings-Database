import pandas as pd

from foe_buildings.data.calculations import (
    apply_per_square,
    calculate_era_stats,
    calculate_direct_weighted_efficiency,
    combine_army_with_ge_gbg,
)


def test_apply_per_square_divides_numeric_columns(sample_buildings_df):
    """Numeric non-excluded columns should be divided by the divisor."""
    divisor = sample_buildings_df["Nbr of squares (Avg)"]
    result = apply_per_square(sample_buildings_df.copy(), divisor)
    # forge_points for row 0: 100 / 9 ≈ 11.11
    assert abs(result.iloc[0]["forge_points"] - 100.0 / 9.0) < 0.01


def test_apply_per_square_skips_excluded_columns(sample_buildings_df):
    """Excluded columns like 'name' must not be modified."""
    divisor = sample_buildings_df["Nbr of squares (Avg)"]
    result = apply_per_square(sample_buildings_df.copy(), divisor)
    assert result.iloc[0]["name"] == "Test Building A"


def test_calculate_era_stats_returns_per_era_max(sample_buildings_df):
    """Era stats should include max for each era."""
    stats = calculate_era_stats(sample_buildings_df)
    assert not stats.empty
    assert stats.loc["SpaceAgeSpaceHub", ("forge_points", "max")] == 100.0
    assert stats.loc["BronzeAge", ("forge_points", "max")] == 5.0


def test_classic_scoring_uses_raw_values(sample_buildings_df):
    """Classic mode: Total Score = sum(value * weight)."""
    weights = {"forge_points": 2.0}
    result = calculate_direct_weighted_efficiency(
        df=sample_buildings_df.copy(),
        user_weights=weights,
        user_context={},
        era_stats_df=None,
    )
    row_a = result[result["name"] == "Test Building A"].iloc[0]
    assert abs(row_a["Total Score"] - 200.0) < 0.1


def test_combine_army_adds_base_to_ge_gbg():
    """Base army stats should be added to GE/GBG columns and base dropped."""
    df = pd.DataFrame(
        {
            "Red Attack": [10.0],
            "Red Defense": [5.0],
            "Blue Attack": [8.0],
            "Blue Defense": [3.0],
            "Red GE Attack": [20.0],
            "Red GE Defense": [10.0],
            "Blue GE Attack": [15.0],
            "Blue GE Defense": [7.0],
            "Red GBG Attack": [25.0],
            "Red GBG Defense": [12.0],
            "Blue GBG Attack": [18.0],
            "Blue GBG Defense": [9.0],
        }
    )
    result = combine_army_with_ge_gbg(df)
    assert "Red Attack" not in result.columns
    assert result.iloc[0]["Red GE Attack"] == 30.0  # 20 + 10
    assert result.iloc[0]["Red GBG Attack"] == 35.0  # 25 + 10

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

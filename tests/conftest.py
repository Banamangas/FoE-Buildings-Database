import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def keep_tooltip_icon_tests_offline(monkeypatch):
    monkeypatch.setattr(
        "foe_buildings.ui.tooltip_icons.load_forgehx_asset_map", lambda: {}
    )


@pytest.fixture
def sample_buildings_df():
    """A small DataFrame with representative buildings for testing."""
    return pd.DataFrame(
        {
            "name": ["Test Building A", "Test Building B", "Test Building C"],
            "Era": ["SpaceAgeSpaceHub", "SpaceAgeSpaceHub", "BronzeAge"],
            "forge_points": [100.0, 50.0, 5.0],
            "goods": [20.0, 0.0, 10.0],
            "next_age_goods": [0.0, 15.0, 0.0],
            "prev_age_goods": [0.0, 0.0, 0.0],
            "special_goods": [0.0, 0.0, 0.0],
            "guild_goods": [0.0, 0.0, 0.0],
            "coins": [1000.0, 500.0, 100.0],
            "supplies": [800.0, 400.0, 80.0],
            "medals": [50.0, 25.0, 5.0],
            "Nbr of squares (Avg)": [9.0, 4.0, 4.0],
            "Population": [-500.0, -200.0, -50.0],
            "Red Attack": [10.0, 0.0, 0.0],
            "Red Defense": [5.0, 0.0, 0.0],
            "Blue Attack": [10.0, 0.0, 0.0],
            "Blue Defense": [5.0, 0.0, 0.0],
            "Coin %": [0.0, 50.0, 0.0],
            "Supplies %": [0.0, 0.0, 0.0],
            "Medal Boost": [0.0, 0.0, 0.0],
        }
    )

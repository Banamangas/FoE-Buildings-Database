from unittest.mock import MagicMock, patch

import pandas as pd

from foe_buildings.tabs import event_tooltips
from foe_buildings.ui.tooltip import TooltipRow, TooltipSection


def test_parse_numeric_value_detects_plain_number():
    result = event_tooltips._parse_numeric_value("120")
    assert result == (120.0, "")


def test_parse_numeric_value_detects_percent():
    result = event_tooltips._parse_numeric_value("20%")
    assert result == (20.0, "%")


def test_parse_numeric_value_returns_none_for_time():
    assert event_tooltips._parse_numeric_value("1d 2h") is None


def test_format_numeric_range_collapses_equal_values():
    assert event_tooltips._format_numeric_range(15.0, 15.0, "") == "15"


def test_format_numeric_range_shows_range():
    assert event_tooltips._format_numeric_range(10.0, 30.0, "%") == "10 - 30%"


def test_aggregate_tooltip_sections_combines_numeric_rows():
    row = TooltipRow(icon=None, label="Coins", value="100")
    sections = {
        "era1": [TooltipSection(title="Provides", rows=[row], key="provides")],
        "era2": [TooltipSection(title="Provides", rows=[TooltipRow(icon=None, label="Coins", value="300")], key="provides")],
    }
    aggregated = event_tooltips._aggregate_tooltip_sections(sections)
    assert len(aggregated) == 1
    assert aggregated[0].rows[0].value == "100 - 300"


def test_aggregate_tooltip_sections_handles_identity_only_in_later_era():
    sections = {
        "era1": [TooltipSection(title="Provides", rows=[
            TooltipRow(icon=None, label="Coins", value="100"),
        ], key="provides")],
        "era2": [TooltipSection(title="Provides", rows=[
            TooltipRow(icon=None, label="Coins", value="300"),
            TooltipRow(icon=None, label="Supplies", value="50"),
        ], key="provides")],
    }
    aggregated = event_tooltips._aggregate_tooltip_sections(sections)
    assert len(aggregated) == 1
    labels = [row.label for row in aggregated[0].rows]
    assert labels == ["Coins", "Supplies"]
    assert aggregated[0].rows[0].value == "100 - 300"
    assert aggregated[0].rows[1].value == "50"


def test_aggregate_tooltip_rows_collapses_numeric_range():
    rows = [
        TooltipRow(icon=None, label="Coins", value="100"),
        TooltipRow(icon=None, label="Coins", value="300"),
    ]
    aggregated = event_tooltips._aggregate_tooltip_rows(rows)
    assert aggregated.value == "100 - 300"


def test_aggregate_tooltip_rows_collapses_equal_numeric_values():
    rows = [
        TooltipRow(icon=None, label="Coins", value="50"),
        TooltipRow(icon=None, label="Coins", value="50"),
    ]
    aggregated = event_tooltips._aggregate_tooltip_rows(rows)
    assert aggregated.value == "50"


def test_aggregate_tooltip_rows_joins_mixed_non_numeric_values():
    rows = [
        TooltipRow(icon=None, label="Reward", value="A"),
        TooltipRow(icon=None, label="Reward", value="B"),
    ]
    aggregated = event_tooltips._aggregate_tooltip_rows(rows)
    assert aggregated.value == "A / B"


def test_aggregate_tooltip_rows_collapses_identical_non_numeric_values():
    rows = [
        TooltipRow(icon=None, label="Reward", value="X"),
        TooltipRow(icon=None, label="Reward", value="X"),
    ]
    aggregated = event_tooltips._aggregate_tooltip_rows(rows)
    assert aggregated.value == "X"


def test_split_size_time_road_section_extracts_road_section():
    size_section = TooltipSection(title="Size", rows=[], key="size_time_road")
    other_section = TooltipSection(title="Provides", rows=[], key="provides")
    extracted, rest = event_tooltips._split_size_time_road_section([size_section, other_section])
    assert extracted is size_section
    assert rest == [other_section]


def test_get_sorted_building_eras_returns_distinct_eras_in_order():
    df = pd.DataFrame(
        {
            "id": ["B1", "B1", "B1"],
            "Era": ["IronAge", "BronzeAge", "IronAge"],
        }
    )
    eras = event_tooltips._get_sorted_building_eras(df, "B1")
    # ERAS_DICT orders newest eras first: IronAge (index 21) before BronzeAge (22).
    assert eras == ["IronAge", "BronzeAge"]


def test_deduplicate_buildings_keeps_one_row_per_id():
    df = pd.DataFrame(
        {
            "id": ["B1", "B1", "B2"],
            "name": ["Building 1", "Building 1", "Building 2"],
            "Event": ["Winter Event"] * 3,
            "Era": ["IronAge", "BronzeAge", "BronzeAge"],
            "Translated Era": ["Iron Age", "Bronze Age", "Bronze Age"],
            "asset_id": ["A1", "A1", "A2"],
        }
    )
    result = event_tooltips._deduplicate_buildings(df)
    assert len(result) == 2
    assert set(result["id"]) == {"B1", "B2"}
    # Keeps the most advanced era row (lowest ERAS_DICT index).
    b1_row = result[result["id"] == "B1"].iloc[0]
    assert b1_row["Era"] == "IronAge"


def test_render_event_tooltips_deduplicates_building_eras():
    df = pd.DataFrame(
        {
            "id": ["B1", "B1", "B2", "B2"],
            "name": ["Building 1", "Building 1", "Building 2", "Building 2"],
            "Event": ["Winter Event"] * 4,
            "Era": ["BronzeAge", "IronAge", "BronzeAge", "IronAge"],
            "Translated Era": ["Bronze Age", "Iron Age", "Bronze Age", "Iron Age"],
            "asset_id": ["A1", "A1", "A2", "A2"],
        }
    )
    image_manager = MagicMock()
    image_manager.has_image.return_value = False

    with patch(
        "foe_buildings.tabs.event_tooltips.data_loader.load_building_entity_lookup"
    ) as mock_lookup:
        mock_lookup.return_value = {
            "B1": {"name": "Building 1", "components": {"AllAge": {}}},
            "B2": {"name": "Building 2", "components": {"AllAge": {}}},
        }
        with patch.object(
            event_tooltips, "_resolve_building_sections"
        ) as mock_resolve:
            mock_resolve.return_value = []
            event_tooltips.render_event_tooltips(df, [], "Bronze Age", "en", image_manager)
            # Two buildings, two extreme eras each in All eras mode -> 4 calls, not 8.
            assert mock_resolve.call_count == 4
            called_eras = {call.args[1] for call in mock_resolve.call_args_list}
            assert called_eras == {"BronzeAge", "StellarAgeDiscovery"}


def test_render_event_tooltips_splits_into_rows_of_three():
    df = pd.DataFrame(
        {
            "id": ["B1", "B2", "B3", "B4"],
            "name": ["Building 1", "Building 2", "Building 3", "Building 4"],
            "Event": ["Winter Event", "Winter Event", "Winter Event", "Winter Event"],
            "Era": ["BronzeAge", "BronzeAge", "BronzeAge", "BronzeAge"],
            "Translated Era": ["Bronze Age"] * 4,
            "asset_id": ["A1", "A2", "A3", "A4"],
        }
    )
    image_manager = MagicMock()
    image_manager.has_image.return_value = False

    with patch(
        "foe_buildings.tabs.event_tooltips.data_loader.load_building_entity_lookup"
    ) as mock_lookup:
        mock_lookup.return_value = {
            "B1": {"name": "Building 1", "components": {"AllAge": {}}},
            "B2": {"name": "Building 2", "components": {"AllAge": {}}},
            "B3": {"name": "Building 3", "components": {"AllAge": {}}},
            "B4": {"name": "Building 4", "components": {"AllAge": {}}},
        }
        # Should not raise; we cannot easily assert Streamlit columns, but we verify no exception.
        event_tooltips.render_event_tooltips(df, [], "Bronze Age", "en", image_manager)

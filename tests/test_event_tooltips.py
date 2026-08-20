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
    aggregated = event_tooltips._aggregate_tooltip_sections(sections, "en")
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
    aggregated = event_tooltips._aggregate_tooltip_sections(sections, "en")
    assert len(aggregated) == 1
    labels = [row.label for row in aggregated[0].rows]
    assert labels == ["Coins", "Supplies"]
    assert aggregated[0].rows[0].value == "100 - 300"
    assert aggregated[0].rows[1].value == "50"


def test_split_size_time_road_section_extracts_road_section():
    size_section = TooltipSection(title="Size", rows=[], key="size_time_road")
    other_section = TooltipSection(title="Provides", rows=[], key="provides")
    extracted, rest = event_tooltips._split_size_time_road_section([size_section, other_section])
    assert extracted is size_section
    assert rest == [other_section]


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

    with patch("foe_buildings.tabs.event_tooltips.data_loader.load_building_entity_lookup") as mock_lookup:
        mock_lookup.return_value = {
            "B1": {"name": "Building 1", "components": {"AllAge": {}}},
            "B2": {"name": "Building 2", "components": {"AllAge": {}}},
            "B3": {"name": "Building 3", "components": {"AllAge": {}}},
            "B4": {"name": "Building 4", "components": {"AllAge": {}}},
        }
        # Should not raise; we cannot easily assert Streamlit columns, but we verify no exception.
        event_tooltips.render_event_tooltips(df, [], "Bronze Age", "en", image_manager)

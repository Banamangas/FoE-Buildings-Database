import pytest

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


def test_split_size_time_road_section_extracts_road_section():
    size_section = TooltipSection(title="Size", rows=[], key="size_time_road")
    other_section = TooltipSection(title="Provides", rows=[], key="provides")
    extracted, rest = event_tooltips._split_size_time_road_section([size_section, other_section])
    assert extracted is size_section
    assert rest == [other_section]

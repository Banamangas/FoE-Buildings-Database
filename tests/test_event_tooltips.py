from unittest.mock import MagicMock, patch

import pandas as pd

from foe_buildings.tabs import event_tooltips
from foe_buildings.ui.tooltip import (
    RandomOutcome,
    RandomProductionGroup,
    TooltipRow,
    TooltipSection,
)


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


def test_reorder_event_tooltip_sections_puts_ally_rooms_first():
    sections = [
        TooltipSection(title="Provides", rows=[], key="provides"),
        TooltipSection(title="Ally Rooms", rows=[], key="ally_rooms"),
        TooltipSection(title="Produces", rows=[], key="produces"),
        TooltipSection(title="Traits", rows=[], key="traits"),
    ]
    ordered = event_tooltips._reorder_event_tooltip_sections(sections)
    assert [s.key for s in ordered] == [
        "ally_rooms",
        "provides",
        "produces",
        "traits",
    ]


def test_is_fragment_row_detects_fragment_marker():
    from foe_buildings.ui.tooltip_icons import ResolvedIcon

    fragment_row = TooltipRow(
        icon=None,
        label="Test Fragments",
        value="5",
        markers=[ResolvedIcon("icon_tooltip_fragment", "frag.png", "Fragment")],
    )
    normal_row = TooltipRow(icon=None, label="Coins", value="100")
    assert event_tooltips._is_fragment_row(fragment_row) is True
    assert event_tooltips._is_fragment_row(normal_row) is False


def test_reformat_fragment_row_shows_name():
    from foe_buildings.ui.tooltip_icons import ResolvedIcon

    fragment_icon = ResolvedIcon("icon_tooltip_fragment", "frag.png", "Fragment")
    row = TooltipRow(
        icon=ResolvedIcon("kit", "kit.png", "Kit"),
        label="Test Selection Kit Fragments",
        value="10",
        markers=[fragment_icon],
    )
    reformatted = event_tooltips._reformat_fragment_row(row)
    assert "10" in reformatted.value
    assert "frag.png" in reformatted.value
    assert "of Test Selection Kit" in reformatted.value
    assert not any(
        marker.key == "icon_tooltip_fragment" for marker in reformatted.markers
    )


def test_building_id_html_escapes_value():
    html_output = event_tooltips._building_id_html("W_MultiAge_AgeBonus22stage")
    assert "ID: W_MultiAge_AgeBonus22stage" in html_output
    assert "<script>" not in html_output


def test_natural_building_id_key_sorts_numeric_suffixes():
    ids = [
        "W_MultiAge_FALL26A10",
        "W_MultiAge_FALL26A1",
        "W_MultiAge_FALL26A2",
        "W_MultiAge_FALL26A10b",
        "W_MultiAge_FALL26A10a",
    ]
    assert sorted(ids, key=event_tooltips._natural_building_id_key) == [
        "W_MultiAge_FALL26A1",
        "W_MultiAge_FALL26A2",
        "W_MultiAge_FALL26A10",
        "W_MultiAge_FALL26A10a",
        "W_MultiAge_FALL26A10b",
    ]


def test_render_event_tooltips_sorts_ids_naturally():
    df = pd.DataFrame(
        {
            "id": [
                "W_MultiAge_FALL26A10",
                "W_MultiAge_FALL26A1",
                "W_MultiAge_FALL26A2",
            ],
            "name": ["B10", "B1", "B2"],
            "Event": ["Fall Event"] * 3,
            "Era": ["BronzeAge"] * 3,
            "Translated Era": ["Bronze Age"] * 3,
            "asset_id": ["A10", "A1", "A2"],
        }
    )
    image_manager = MagicMock()
    image_manager.has_image.return_value = False

    with patch(
        "foe_buildings.tabs.event_tooltips.data_loader.load_building_entity_lookup"
    ) as mock_lookup:
        mock_lookup.return_value = {
            "W_MultiAge_FALL26A10": {"name": "B10", "components": {"AllAge": {}}},
            "W_MultiAge_FALL26A1": {"name": "B1", "components": {"AllAge": {}}},
            "W_MultiAge_FALL26A2": {"name": "B2", "components": {"AllAge": {}}},
        }
        with patch.object(
            event_tooltips, "_resolve_building_sections"
        ) as mock_resolve:
            mock_resolve.return_value = []
            event_tooltips.render_event_tooltips(df, [], "Bronze Age", "en", image_manager)
            rendered_ids = [call.args[0]["id"] for call in mock_resolve.call_args_list]
            # In All-eras mode each building is resolved for two extreme eras,
            # so deduplicate while preserving order.
            seen = []
            for bid in rendered_ids:
                if bid not in seen:
                    seen.append(bid)
            assert seen == [
                "W_MultiAge_FALL26A1",
                "W_MultiAge_FALL26A2",
                "W_MultiAge_FALL26A10",
            ]


def test_render_tooltip_section_html_reformats_fragment_outcomes_in_random_groups():
    from foe_buildings.ui.tooltip import RandomOutcome, RandomProductionGroup
    from foe_buildings.ui.tooltip_icons import ResolvedIcon

    fragment_icon = ResolvedIcon("icon_tooltip_fragment", "frag.png", "Fragment")
    kit_icon = ResolvedIcon("selection_kit", "kit.png", "Selection Kit")
    section = TooltipSection(
        title="Produces",
        rows=[],
        key="produces",
        random_groups=[
            RandomProductionGroup(
                outcomes=[
                    RandomOutcome(
                        row=TooltipRow(
                            icon=kit_icon,
                            label="Test Selection Kit fragments",
                            value="5",
                            markers=[fragment_icon],
                        ),
                        probability=100,
                    )
                ]
            )
        ],
    )
    html_output = event_tooltips._render_tooltip_section_html(section, "en")
    assert "5 <img" in html_output
    assert "of Test Selection Kit" in html_output


def test_render_tooltip_section_html_puts_random_markers_in_header():
    from foe_buildings.ui.tooltip import RandomOutcome, RandomProductionGroup
    from foe_buildings.ui.tooltip_icons import ResolvedIcon

    motivated = ResolvedIcon("when_motivated", "mot.png", "when motivated")
    section = TooltipSection(
        title="Produces",
        rows=[],
        key="produces",
        random_groups=[
            RandomProductionGroup(
                outcomes=[
                    RandomOutcome(
                        row=TooltipRow(icon=None, label="Coins", value="10"),
                        probability=50,
                    )
                ],
                markers=[motivated],
            )
        ],
    )
    html_output = event_tooltips._render_tooltip_section_html(section, "en")
    # Motivation marker should appear inside the random-production header, not below it.
    header_end = html_output.find("</div>", html_output.find("tooltip-random-header"))
    header = html_output[:header_end]
    assert "mot.png" in header
    assert html_output.count("tooltip-random-metadata") == 0 or "mot.png" not in html_output[header_end:]


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


def test_row_identity_groups_unit_rows_by_class():
    from foe_buildings.ui.tooltip_icons import ResolvedIcon

    row_a = TooltipRow(
        icon=ResolvedIcon("slinger", "slinger.png", "Slinger"),
        label="Slinger",
        value="12",
        group_key="short_ranged",
        group_icon_key="military",
    )
    row_b = TooltipRow(
        icon=ResolvedIcon("hover_hammer", "hover_hammer.png", "Hover Hammer"),
        label="Hover Hammer",
        value="12",
        group_key="short_ranged",
        group_icon_key="military",
    )
    assert event_tooltips._row_identity(row_a) == event_tooltips._row_identity(row_b)


def test_row_identity_includes_duration_to_keep_mixed_durations_separate():
    row_a = TooltipRow(icon=None, label="Supplies", value="10", duration=300)
    row_b = TooltipRow(icon=None, label="Supplies", value="30", duration=900)
    assert event_tooltips._row_identity(row_a) != event_tooltips._row_identity(row_b)


def test_aggregate_tooltip_sections_keeps_mixed_durations_separate():
    sections = {
        "BronzeAge": [
            TooltipSection(
                title="Produces",
                rows=[
                    TooltipRow(icon=None, label="Supplies", value="10", duration=300),
                    TooltipRow(icon=None, label="Supplies", value="30", duration=900),
                ],
                key="produces",
            )
        ],
        "StellarAgeDiscovery": [
            TooltipSection(
                title="Produces",
                rows=[
                    TooltipRow(icon=None, label="Supplies", value="100", duration=300),
                    TooltipRow(icon=None, label="Supplies", value="300", duration=900),
                ],
                key="produces",
            )
        ],
    }
    aggregated = event_tooltips._aggregate_tooltip_sections(sections)
    assert len(aggregated[0].rows) == 2
    values = {row.duration: row.value for row in aggregated[0].rows}
    assert values[300] == "10 - 100"
    assert values[900] == "30 - 300"


def test_infer_unit_era_token_detects_next_age_from_bronze_age():
    from foe_buildings.ui.tooltip_icons import ResolvedIcon

    sections = [
        TooltipSection(
            title="Produces",
            rows=[],
            key="produces",
            random_groups=[
                RandomProductionGroup(
                    outcomes=[
                        RandomOutcome(
                            row=TooltipRow(
                                icon=ResolvedIcon("next_age_fast_units", "", ""),
                                label="Next Age Fast Units",
                                value="10",
                                group_key="NextEra#fast",
                                display_label=True,
                            ),
                            probability=100,
                        )
                    ]
                )
            ],
        )
    ]
    assert event_tooltips._infer_unit_era_token(sections) == "NextEra"


def test_aggregate_tooltip_sections_forces_next_age_when_bronze_age_is_next_age():
    from foe_buildings.ui.tooltip_icons import ResolvedIcon

    sections = {
        "BronzeAge": [
            TooltipSection(
                title="Produces",
                rows=[
                    TooltipRow(
                        icon=ResolvedIcon("fast_units", "", ""),
                        label="Fast Units",
                        value="10",
                        group_key="NextEra#fast",
                        display_label=True,
                    )
                ],
                key="produces",
            )
        ],
        "StellarAgeDiscovery": [
            TooltipSection(
                title="Produces",
                rows=[
                    TooltipRow(
                        icon=ResolvedIcon("fast_units", "", ""),
                        label="Fast Units",
                        value="20",
                        group_key="CurrentEra#fast",
                        display_label=True,
                    )
                ],
                key="produces",
            )
        ],
    }
    aggregated = event_tooltips._aggregate_tooltip_sections(
        sections, lang_code="en", unit_era_token="NextEra"
    )
    prod = aggregated[0]
    assert len(prod.rows) == 1
    assert prod.rows[0].label == "Next Age Fast Units"
    assert prod.rows[0].value == "10 - 20"


def test_aggregate_tooltip_sections_keeps_era_order_for_negative_ranges():
    sections = {
        # Dict insertion order is newest-first, but the result should still
        # list BronzeAge on the left and StellarAgeDiscovery on the right.
        "StellarAgeDiscovery": [
            TooltipSection(
                title="Provides",
                rows=[TooltipRow(icon=None, label="Population", value="-20")],
                key="provides",
            )
        ],
        "BronzeAge": [
            TooltipSection(
                title="Provides",
                rows=[TooltipRow(icon=None, label="Population", value="-5")],
                key="provides",
            )
        ],
    }
    aggregated = event_tooltips._aggregate_tooltip_sections(sections)
    assert aggregated[0].rows[0].value == "-5 - -20"


def test_aggregate_tooltip_sections_merges_era_specific_units(monkeypatch):
    from foe_buildings.ui.tooltip_icons import ResolvedIcon

    def fake_resolve(key, accessible_name, entity_asset_id=None):
        return ResolvedIcon(key, f"{key}.png", accessible_name)

    monkeypatch.setattr(event_tooltips, "resolve_game_icon", fake_resolve)

    sections = {
        "BronzeAge": [
            TooltipSection(
                title="Produces",
                rows=[
                    TooltipRow(
                        icon=ResolvedIcon("slinger", "slinger.png", "Slinger"),
                        label="Slinger",
                        value="12",
                        group_key="short_ranged",
                        group_label="Ranged Units",
                        group_icon_key="ranged_units",
                    )
                ],
                key="produces",
            )
        ],
        "StellarAgeDiscovery": [
            TooltipSection(
                title="Produces",
                rows=[
                    TooltipRow(
                        icon=ResolvedIcon(
                            "hover_hammer", "hover_hammer.png", "Hover Hammer"
                        ),
                        label="Hover Hammer",
                        value="12",
                        group_key="short_ranged",
                        group_label="Ranged Units",
                        group_icon_key="ranged_units",
                    )
                ],
                key="produces",
            )
        ],
    }
    aggregated = event_tooltips._aggregate_tooltip_sections(sections)
    assert len(aggregated) == 1
    assert len(aggregated[0].rows) == 1
    assert aggregated[0].rows[0].label == "Ranged Units"
    assert aggregated[0].rows[0].value == "12"
    assert aggregated[0].rows[0].icon.key == "ranged_units"

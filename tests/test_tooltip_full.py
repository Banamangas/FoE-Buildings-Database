from copy import deepcopy

from foe_buildings.ui.tooltip import render_building_tooltip
from tests.fixtures.pendragon_tooltip import PENDRAGON_TOOLTIP_ENTITY


def _rows_by_section(sections):
    return {section.key: section.rows for section in sections if section.key}


def test_render_building_tooltip_returns_sections():
    entity = {
        "name": "Test Building",
        "components": {
            "AllAge": {
                "placement": {"size": {"x": 3, "y": 2}},
                "production": {
                    "options": [
                        {
                            "time": 3600,
                            "products": [
                                {
                                    "type": "resources",
                                    "playerResources": {"resources": {"coins": 10}},
                                }
                            ],
                        }
                    ]
                },
            }
        },
    }
    sections = render_building_tooltip(entity, "en")
    assert sections[0].key == "header"
    assert sections[0].header == "Test Building"
    assert [section.key for section in sections] == [
        "header",
        "size_time_road",
        "produces",
    ]


def test_render_building_tooltip_resolves_selected_era_without_mutation():
    entity = deepcopy(PENDRAGON_TOOLTIP_ENTITY)
    original = deepcopy(entity)

    sections = render_building_tooltip(entity, "en", era_key="StellarAgeDiscovery")

    assert entity == original
    by_section = _rows_by_section(sections)
    provides = {(row.label, row.value) for row in by_section["provides"]}
    production_section = next(
        section for section in sections if section.key == "produces"
    )
    produces = {(row.label, row.value) for row in production_section.rows}

    assert ("Population", "67000") in provides
    assert ("Happiness", "100480") in provides
    assert ("Att/Def Attacker/Defender", "246%") in provides
    assert ("Att/Def Attacker/Defender (Guild Battlegrounds)", "371%") in provides
    assert ("Att/Def Defender (Quantum Incursions)", "30%") in provides
    assert ("Quantum Actions per hour", "200") in provides
    assert ("Quantum Action capacity", "8000") in provides
    assert production_section.title == "Produces"
    assert production_section.shared_duration == 86400
    assert production_section.random_groups == []
    assert ("Coins", "776610") in produces
    assert ("Forge Points", "411") in produces
    assert ("Goods", "575") in produces
    assert any(
        label == "Legends of Camelot Selection Kit fragments" and value == "5"
        for label, value in produces
    )
    assert any(
        label == "Mass Self-Aid Kit fragments" and value == "10"
        for label, value in produces
    )
    motivated_rows = [row for row in production_section.rows if row.label != "Coins"]
    assert all(
        "when_motivated" in [marker.key for marker in row.markers]
        for row in motivated_rows
    )
    fragment_rows = [row for row in production_section.rows if "fragments" in row.label]
    assert all(
        [marker.key for marker in row.markers]
        == ["icon_tooltip_fragment", "when_motivated"]
        for row in fragment_rows
    )


def test_render_building_tooltip_unknown_era_falls_back_to_all_age():
    sections = render_building_tooltip(
        PENDRAGON_TOOLTIP_ENTITY, "en", era_key="UnknownEra"
    )

    by_section = _rows_by_section(sections)
    assert "size_time_road" in by_section
    assert "provides" not in by_section
    assert "produces" not in by_section


def test_render_building_tooltip_keeps_additive_all_age_provides():
    entity = {
        "components": {
            "AllAge": {
                "staticResources": {"resources": {"resources": {"medals": 100}}},
                "boosts": {"boosts": [{"type": "coin_production", "value": 10}]},
            },
            "BronzeAge": {
                "staticResources": {"resources": {"resources": {"supplies": 200}}},
                "boosts": {"boosts": [{"type": "goods_production", "value": 20}]},
            },
        }
    }

    sections = render_building_tooltip(entity, "en", era_key="BronzeAge")

    provides = {
        (row.label, row.value) for row in _rows_by_section(sections)["provides"]
    }
    assert ("Medals", "100") in provides
    assert ("Supplies", "200") in provides
    assert ("Coin %", "10%") in provides
    assert ("Goods Boost", "20%") in provides


def test_selected_era_static_resources_add_numeric_conflicts_without_mutation():
    entity = {
        "components": {
            "AllAge": {
                "staticResources": {
                    "resources": {
                        "resources": {
                            "medals": 100,
                            "shared_only": 7,
                            "conflict_label": "AllAge",
                        }
                    }
                }
            },
            "BronzeAge": {
                "staticResources": {
                    "resources": {
                        "resources": {
                            "medals": 25,
                            "selected_only": 9,
                            "conflict_label": "BronzeAge",
                        }
                    }
                }
            },
        }
    }
    original = deepcopy(entity)

    sections = render_building_tooltip(entity, "en", era_key="BronzeAge")

    provides = {
        row.icon.key: row.value for row in _rows_by_section(sections)["provides"]
    }
    assert provides == {
        "medals": "125",
        "shared_only": "7",
        "conflict_label": "BronzeAge",
        "selected_only": "9",
    }
    assert entity == original


def test_selected_empty_static_resources_retains_all_age_resources_without_mutation():
    entity = {
        "components": {
            "AllAge": {
                "staticResources": {"resources": {"resources": {"medals": 100}}}
            },
            "BronzeAge": {"staticResources": {}},
        }
    }
    original = deepcopy(entity)

    sections = render_building_tooltip(entity, "en", era_key="BronzeAge")

    rows_by_section = _rows_by_section(sections)
    assert "provides" in rows_by_section
    assert [(row.icon.key, row.value) for row in rows_by_section["provides"]] == [
        ("medals", "100")
    ]
    assert entity == original


def test_selected_empty_boost_list_does_not_erase_all_age_boosts():
    entity = {
        "components": {
            "AllAge": {
                "boosts": {"boosts": [{"type": "coin_production", "value": 10}]},
            },
            "BronzeAge": {"boosts": {"boosts": []}},
        }
    }

    sections = render_building_tooltip(entity, "en", era_key="BronzeAge")

    provides = _rows_by_section(sections)["provides"]
    assert any(row.label == "Coin %" and row.value == "10%" for row in provides)


def test_full_tooltip_preserves_accessible_labels_with_exact_icons():
    entity = {
        "components": {
            "AllAge": {
                "placement": {"size": {"x": 2, "y": 1}},
                "staticResources": {"resources": {"resources": {"money": 10}}},
                "chain": {"chainId": "MyChain"},
                "ally": {"rooms": [{"allyType": "diplomat"}]},
                "cityLimit": {"buildingFamily": "MyFamily"},
            }
        }
    }

    sections = render_building_tooltip(entity, "en")
    rows_by_section = _rows_by_section(sections)

    assert set(rows_by_section) == {
        "size_time_road",
        "provides",
        "chain_set",
        "ally_rooms",
        "traits",
    }
    money_row = rows_by_section["provides"][0]
    trait_row = rows_by_section["traits"][0]
    assert (money_row.icon.key, money_row.icon.accessible_name, money_row.label) == (
        "money",
        "Coins",
        "Coins",
    )
    assert money_row.show_label is False
    assert rows_by_section["chain_set"][0].icon.key == "MyChain"
    assert rows_by_section["ally_rooms"][0].icon.key == (
        "historical_allies_slot_tooltip_icon_empty"
    )
    assert trait_row.icon.key == "icon_unique_building"
    assert trait_row.show_label is True

from copy import deepcopy

from foe_buildings.ui.tooltip import render_building_tooltip
from tests.fixtures.pendragon_tooltip import PENDRAGON_TOOLTIP_ENTITY


def _rows_by_section(sections):
    return {section.title: section.rows for section in sections if section.title}


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
    assert sections[0].header == "Test Building"
    titles = [s.title for s in sections]
    assert "Size" in titles or "Road" in titles or any(t is not None for t in titles)
    assert len(sections) > 0


def test_render_building_tooltip_resolves_selected_era_without_mutation():
    entity = deepcopy(PENDRAGON_TOOLTIP_ENTITY)
    original = deepcopy(entity)

    sections = render_building_tooltip(entity, "en", era_key="StellarAgeDiscovery")

    assert entity == original
    by_section = _rows_by_section(sections)
    provides = {(row.label, row.value) for row in by_section["Provides"]}
    produces = {(row.label, row.value, row.suffix) for row in by_section["Produces"]}

    assert ("Population", "67000") in provides
    assert ("Happiness", "100480") in provides
    assert ("Att/Def Attacker/Defender", "246%") in provides
    assert ("Att/Def Attacker/Defender (Guild Battlegrounds)", "371%") in provides
    assert ("Att/Def Defender (Quantum Incursions)", "30%") in provides
    assert ("Quantum Actions per hour", "200") in provides
    assert ("Quantum Action capacity", "8000") in provides
    assert ("Coins", "776610 in 1d", None) in produces
    assert ("Forge Points", "411 in 1d", "when motivated") in produces
    assert ("Goods", "575 in 1d", "when motivated") in produces
    assert any(
        label == "Legends of Camelot Selection Kit fragments"
        and value.startswith("5 in 1d")
        for label, value, _ in produces
    )
    assert any(
        label == "Mass Self-Aid Kit fragments" and value.startswith("10 in 1d")
        for label, value, _ in produces
    )


def test_render_building_tooltip_unknown_era_falls_back_to_all_age():
    sections = render_building_tooltip(
        PENDRAGON_TOOLTIP_ENTITY, "en", era_key="UnknownEra"
    )

    by_section = _rows_by_section(sections)
    assert "Size / Time / Road" in by_section
    assert "Provides" not in by_section


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
        (row.label, row.value) for row in _rows_by_section(sections)["Provides"]
    }
    assert ("Medals", "100") in provides
    assert ("Supplies", "200") in provides
    assert ("Coin %", "10%") in provides
    assert ("Goods Boost", "20%") in provides


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

    provides = _rows_by_section(sections)["Provides"]
    assert any(row.label == "Coin %" and row.value == "10%" for row in provides)

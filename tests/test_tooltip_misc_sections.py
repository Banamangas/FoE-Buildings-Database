from foe_buildings.ui.tooltip import (
    _render_ally_rooms,
    _render_chain_set,
    _render_costs,
    _render_traits,
)


def test_chain_set():
    entity = {"components": {"AllAge": {"chain": {"chainId": "MyChain"}}}}
    rows = _render_chain_set(entity, "en")
    assert len(rows) == 1
    assert rows[0].value == "MyChain"
    assert rows[0].icon.key == "MyChain"
    assert rows[0].show_label is True


def test_chain_set_from_ability():
    entity = {
        "components": {"AllAge": {}},
        "abilities": [{"__class__": "ChainStartAbility", "chainId": "AbilityChain"}],
    }
    rows = _render_chain_set(entity, "en")
    assert any(r.value == "AbilityChain" for r in rows)


def test_building_set_from_ability():
    entity = {
        "components": {"AllAge": {}},
        "abilities": [{"__class__": "BuildingSetAbility", "setId": "MySet"}],
    }
    rows = _render_chain_set(entity, "en")
    assert any(r.label == "Set" and r.value == "MySet" for r in rows)


def test_ally_rooms():
    entity = {
        "components": {
            "AllAge": {
                "ally": {
                    "rooms": [
                        {"allyType": "diplomat"},
                        {"allyType": "merchant"},
                    ]
                }
            }
        }
    }
    rows = _render_ally_rooms(entity, "en")
    assert len(rows) == 2
    assert rows[0].value == "Diplomat"
    assert rows[1].value == "Merchant"
    assert all(
        row.icon.key == "historical_allies_slot_tooltip_icon_empty" for row in rows
    )
    assert all(row.show_label for row in rows)


def test_ally_room_military_is_translated():
    entity = {"components": {"AllAge": {"ally": {"rooms": [{"allyType": "military"}]}}}}

    rows = _render_ally_rooms(entity, "en")

    assert rows[0].value == "Military"


def test_traits_unique():
    entity = {"components": {"AllAge": {"cityLimit": {"buildingFamily": "MyFamily"}}}}
    rows = _render_traits(entity, "en")
    assert any(r.value == "Unique building" for r in rows)


def test_traits_auto_era():
    entity = {"components": {"AllAge": {"flags": {"flags": 4}}}}
    rows = _render_traits(entity, "en")
    assert any(r.value == "Upgrades automatically to current era" for r in rows)


def test_traits_fsp_disabled():
    entity = {"components": {"AllAge": {"flags": {"flags": 32}}}}
    rows = _render_traits(entity, "en")
    assert any(r.value == "Instant production finish disabled" for r in rows)


def test_traits_from_social_interaction():
    entity = {
        "components": {"AllAge": {"socialInteraction": {"interactionType": "motivate"}}}
    }

    rows = _render_traits(entity, "en")

    assert any(r.value == "Can be motivated" for r in rows)


def test_traits_from_abilities():
    entity = {
        "components": {"AllAge": {}},
        "abilities": [
            {"__class__": "PolishableAbility"},
            {"__class__": "MotivatableAbility"},
            {"__class__": "NotPlunderableAbility"},
            {"__class__": "AffectedByLifeSupportAbility"},
        ],
    }
    rows = _render_traits(entity, "en")
    values = [r.value for r in rows]
    assert "Can be polished" in values
    assert "Can be motivated" in values
    assert "Cannot be plundered" in values
    assert "Requires life support" in values
    icons_by_value = {row.value: row.icon.key for row in rows}
    assert icons_by_value["Can be polished"] == "when_motivated"
    assert icons_by_value["Can be motivated"] == "when_motivated"
    assert icons_by_value["Cannot be plundered"] == "eventwindow_plunder_repel"
    assert icons_by_value["Requires life support"] == "life_support"
    assert all(row.show_label for row in rows)


def test_traits_use_exact_semantic_icon_keys():
    entity = {
        "components": {
            "AllAge": {
                "cityLimit": {"buildingFamily": "MyFamily"},
                "flags": {"flags": 32},
            }
        }
    }

    rows = _render_traits(entity, "en")

    icons_by_value = {row.value: row.icon.key for row in rows}
    assert icons_by_value["Unique building"] == "icon_unique_building"
    assert icons_by_value["Instant production finish disabled"] == "icon_fsp_disabled"
    assert all(row.show_label for row in rows)


def test_costs():
    entity = {
        "components": {
            "AllAge": {
                "buildResourcesRequirement": {
                    "cost": {"resources": {"supplies": 500, "coins": 1000}}
                }
            }
        }
    }
    rows = _render_costs(entity, "en")
    assert any(r.value == "1000" for r in rows)
    assert any(r.value == "500" for r in rows)
    assert [row.icon.key for row in rows] == ["supplies", "coins"]
    assert all(row.show_label is False for row in rows)

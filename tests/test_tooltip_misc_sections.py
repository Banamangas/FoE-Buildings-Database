from foe_buildings.ui.tooltip import (
    _render_ally_rooms,
    _render_chain_set,
    _render_costs,
    _render_traits,
)


def test_chain_set():
    entity = {
        "components": {
            "AllAge": {
                "chain": {"chainId": "MyChain"}
            }
        }
    }
    rows = _render_chain_set(entity, "en")
    assert len(rows) == 1
    assert rows[0].value == "MyChain"


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
    assert rows[0].value == "diplomat"
    assert rows[1].value == "merchant"


def test_traits_unique():
    entity = {
        "components": {
            "AllAge": {
                "cityLimit": {"buildingFamily": "MyFamily"}
            }
        }
    }
    rows = _render_traits(entity, "en")
    assert any(r.value == "Unique building" for r in rows)


def test_traits_auto_era():
    entity = {
        "components": {
            "AllAge": {
                "flags": {"flags": 4}
            }
        }
    }
    rows = _render_traits(entity, "en")
    assert any(r.value == "Upgrades automatically to current era" for r in rows)


def test_traits_fsp_disabled():
    entity = {
        "components": {
            "AllAge": {
                "flags": {"flags": 32}
            }
        }
    }
    rows = _render_traits(entity, "en")
    assert any(r.value == "Cannot be accelerated by Forge Points" for r in rows)


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

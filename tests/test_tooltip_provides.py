from foe_buildings.ui.tooltip import _render_provides


def test_provides_combined_army_boosts():
    entity = {
        "components": {
            "AllAge": {
                "boosts": {
                    "boosts": [
                        {"type": "att_boost_attacker", "value": 15},
                        {"type": "def_boost_attacker", "value": 20},
                        {"type": "att_boost_defender", "value": 10},
                        {"type": "def_boost_defender", "value": 12},
                    ]
                }
            }
        }
    }
    rows = _render_provides(entity, "en")
    labels = [r.label for r in rows]
    assert "Att/Def Attacker" in labels
    assert "Att/Def Defender" in labels
    attacker_row = next(r for r in rows if r.label == "Att/Def Attacker")
    assert attacker_row.value == "35%"


def test_provides_static_resources():
    entity = {
        "components": {
            "AllAge": {
                "staticResources": {"resources": {"resources": {"medals": 100}}}
            }
        }
    }
    rows = _render_provides(entity, "en")
    assert any(r.label == "Medals" and r.value == "100" for r in rows)

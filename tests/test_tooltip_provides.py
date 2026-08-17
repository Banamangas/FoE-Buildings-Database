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


def test_provides_population_and_happiness():
    entity = {
        "components": {
            "AllAge": {
                "population": {"provided": 1234},
                "happiness": {"provided": 567},
            }
        }
    }
    rows = _render_provides(entity, "en")
    assert any(r.label == "Population" and r.value == "1234" for r in rows)
    assert any(r.label == "Happiness" and r.value == "567" for r in rows)


def test_provides_ranking_points():
    entity = {
        "components": {
            "AllAge": {
                "rankingPoints": {"provided": 890},
            }
        }
    }
    rows = _render_provides(entity, "en")
    assert any(r.label == "Ranking Points" and r.value == "890" for r in rows)


def test_provides_non_army_boosts():
    entity = {
        "components": {
            "AllAge": {
                "boosts": {
                    "boosts": [
                        {"type": "coin_production", "value": 100},
                        {"type": "forge_points_production", "targetedFeature": "battleground", "value": 25},
                    ]
                }
            }
        }
    }
    rows = _render_provides(entity, "en")
    labels = [r.label for r in rows]
    assert "Coin %" in labels
    assert any(r.label == "FP boost (battleground)" and r.value == "25%" for r in rows)

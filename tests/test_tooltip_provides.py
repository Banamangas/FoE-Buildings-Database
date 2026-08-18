from foe_buildings.ui.tooltip import _render_provides


def test_provides_splits_combined_army_boosts_when_part_values_differ():
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
    assert "Red Attack" in labels
    assert "Red Defense" in labels
    assert "Blue Attack" in labels
    assert "Blue Defense" in labels
    assert "Att/Def Attacker" not in labels
    assert "Att/Def Defender" not in labels
    assert any(r.label == "Red Attack" and r.value == "15%" for r in rows)
    assert any(r.label == "Red Defense" and r.value == "20%" for r in rows)
    assert any(r.label == "Blue Attack" and r.value == "10%" for r in rows)
    assert any(r.label == "Blue Defense" and r.value == "12%" for r in rows)


def test_provides_combines_army_boosts_when_part_values_are_equal():
    entity = {
        "components": {
            "AllAge": {
                "boosts": {
                    "boosts": [
                        {"type": "att_boost_attacker", "value": 25},
                        {"type": "def_boost_attacker", "value": 25},
                        {"type": "att_boost_defender", "value": 30},
                        {"type": "def_boost_defender", "value": 30},
                    ]
                }
            }
        }
    }
    rows = _render_provides(entity, "en")
    labels = [r.label for r in rows]
    assert "Att/Def Attacker" in labels
    assert "Att/Def Defender" in labels
    assert "Red Attack" not in labels
    assert "Blue Attack" not in labels
    attacker_row = next(r for r in rows if r.label == "Att/Def Attacker")
    defender_row = next(r for r in rows if r.label == "Att/Def Defender")
    assert attacker_row.value == "25%"
    assert defender_row.value == "30%"


def test_provides_direct_combined_army_boost():
    entity = {
        "components": {
            "AllAge": {
                "boosts": {
                    "boosts": [
                        {
                            "type": "att_def_boost_attacker_defender",
                            "value": 225,
                            "targetedFeature": "all",
                        }
                    ]
                }
            }
        }
    }
    rows = _render_provides(entity, "en")

    row = next(r for r in rows if r.label == "Att/Def Attacker/Defender")
    assert row.value == "225%"


def test_provides_static_resources():
    entity = {
        "components": {
            "AllAge": {"staticResources": {"resources": {"resources": {"medals": 100}}}}
        }
    }
    rows = _render_provides(entity, "en")
    assert any(r.label == "Medals" and r.value == "100" for r in rows)


def test_provides_keeps_exact_resource_and_boost_icon_keys():
    entity = {
        "components": {
            "AllAge": {
                "staticResources": {"resources": {"resources": {"money": 10}}},
                "boosts": {
                    "boosts": [
                        {
                            "type": "att_def_boost_attacker_defender",
                            "targetedFeature": "guild_expedition",
                            "value": 25,
                        }
                    ]
                },
            }
        }
    }

    rows = _render_provides(entity, "en")

    assert [row.icon.key for row in rows] == [
        "money",
        "att_def_boost_attacker_defender_gex",
    ]
    assert [row.show_label for row in rows] == [False, False]
    assert [row.label for row in rows] == [
        "Coins",
        "Att/Def Attacker/Defender (Guild Expedition)",
    ]


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
    row = next(r for r in rows if r.label == "Ranking Points")
    assert row.value == "890"
    assert row.icon.key == "rank"


def test_provides_non_army_boosts():
    entity = {
        "components": {
            "AllAge": {
                "boosts": {
                    "boosts": [
                        {"type": "coin_production", "value": 100},
                        {
                            "type": "forge_points_production",
                            "targetedFeature": "battleground",
                            "value": 25,
                        },
                    ]
                }
            }
        }
    }
    rows = _render_provides(entity, "en")
    labels = [r.label for r in rows]
    assert "Coin %" in labels
    assert any(
        r.label == "FP boost (Guild Battlegrounds)" and r.value == "25%" for r in rows
    )


def test_provides_preserves_repeated_and_unknown_boosts():
    entity = {
        "components": {
            "AllAge": {
                "boosts": {
                    "boosts": [
                        {"type": "coin_production", "value": 10},
                        {"type": "coin_production", "value": 20},
                        {"type": "new_event_resource_boost", "value": 7},
                    ]
                }
            }
        }
    }

    rows = _render_provides(entity, "en")

    assert [row.value for row in rows if row.label == "Coin %"] == ["10%", "20%"]
    assert any(
        row.label == "New Event Resource Boost" and row.value == "7%" for row in rows
    )


def test_provides_keeps_unpaired_army_boost():
    entity = {
        "components": {
            "AllAge": {
                "boosts": {
                    "boosts": [
                        {
                            "type": "att_boost_attacker",
                            "targetedFeature": "guild_expedition",
                            "value": 15,
                        }
                    ]
                }
            }
        }
    }

    rows = _render_provides(entity, "en")

    assert any(
        row.label == "Red Attack (Guild Expedition)" and row.value == "15%"
        for row in rows
    )

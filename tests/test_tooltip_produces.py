from foe_buildings.ui.tooltip import _render_produces


def test_produces_resources():
    entity = {
        "components": {
            "AllAge": {
                "production": {
                    "options": [
                        {
                            "time": 3600,
                            "products": [
                                {
                                    "type": "resources",
                                    "playerResources": {"resources": {"coins": 100}},
                                }
                            ],
                        }
                    ]
                }
            }
        }
    }
    rows = _render_produces(entity, "en")
    assert any("100" in r.value for r in rows)


def test_produces_random():
    entity = {
        "components": {
            "AllAge": {
                "production": {
                    "options": [
                        {
                            "time": 86400,
                            "products": [
                                {
                                    "type": "random",
                                    "products": [
                                        {
                                            "product": {
                                                "type": "resources",
                                                "playerResources": {
                                                    "resources": {"goods": 10}
                                                },
                                            },
                                            "dropChance": 0.5,
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                }
            }
        }
    }
    rows = _render_produces(entity, "en")
    assert any("50%" in r.value for r in rows)


def test_produces_generic_reward_resource():
    entity = {
        "components": {
            "AllAge": {
                "lookup": {
                    "rewards": {"reward_1": {"type": "resource", "subType": "medals"}}
                },
                "production": {
                    "options": [
                        {
                            "time": 3600,
                            "products": [
                                {
                                    "type": "genericReward",
                                    "reward": {"id": "reward_1", "amount": 50},
                                }
                            ],
                        }
                    ]
                },
            }
        }
    }
    rows = _render_produces(entity, "en")
    assert any(r.label == "Medals" and "50" in r.value for r in rows)


def test_produces_generic_reward_unknown():
    entity = {
        "components": {
            "AllAge": {
                "lookup": {"rewards": {}},
                "production": {
                    "options": [
                        {
                            "time": 3600,
                            "products": [
                                {
                                    "type": "genericReward",
                                    "reward": {"id": "unknown_reward", "amount": 1},
                                }
                            ],
                        }
                    ]
                },
            }
        }
    }
    rows = _render_produces(entity, "en")
    assert any(r.label == "unknown_reward" for r in rows)


def test_produces_generic_reward_uses_lookup_name_quantity():
    entity = {
        "components": {
            "AllAge": {
                "lookup": {
                    "rewards": {
                        "fragment_reward": {
                            "name": "10x Fragments of Test Selection Kit",
                            "type": "genericReward",
                            "iconAssetName": "icon_fragment",
                            "requiredAmount": 100,
                        }
                    }
                },
                "production": {
                    "options": [
                        {
                            "time": 86400,
                            "products": [
                                {
                                    "type": "genericReward",
                                    "reward": {"id": "fragment_reward"},
                                }
                            ],
                        }
                    ]
                },
            }
        }
    }

    rows = _render_produces(entity, "en")

    assert any(
        r.label == "Test Selection Kit fragments" and r.value == "10 in 1d"
        for r in rows
    )

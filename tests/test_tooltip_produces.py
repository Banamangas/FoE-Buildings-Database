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
                                                "playerResources": {"resources": {"goods": 10}},
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

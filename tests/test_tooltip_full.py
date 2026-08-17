from foe_buildings.ui.tooltip import render_building_tooltip


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
                                {"type": "resources", "playerResources": {"resources": {"coins": 10}}}
                            ],
                        }
                    ]
                },
            }
        },
    }
    sections = render_building_tooltip(entity, "en")
    titles = [s.title for s in sections]
    assert "Size" in titles or "Road" in titles or any(t is not None for t in titles)
    assert len(sections) > 0

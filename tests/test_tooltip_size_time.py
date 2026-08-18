from foe_buildings import i18n as translations
from foe_buildings.ui.tooltip import _render_size_time_road


def test_size_time_road_all_data():
    entity = {
        "components": {
            "AllAge": {
                "placement": {"size": {"x": 4, "y": 3}},
                "constructionTime": {"time": 3665},
                "streetConnectionRequirement": {"requiredLevel": 1},
            }
        }
    }
    rows = _render_size_time_road(entity, "en")
    assert len(rows) == 3
    assert "3x4" in rows[0].value
    assert "1h 1m 5s" in rows[1].value
    assert rows[0].icon.key == "size"
    assert rows[1].icon.key == "icon_time"
    assert rows[2].icon.key == "road_required"
    assert [row.show_label for row in rows] == [False, False, True]


def test_size_time_road_minimal():
    entity = {"components": {"AllAge": {"placement": {"size": {"x": 2, "y": 2}}}}}
    rows = _render_size_time_road(entity, "en")
    assert len(rows) == 2
    assert "2x2" in rows[0].value
    assert rows[1].label == translations.get_text("road", "en")
    assert rows[1].value == translations.get_text("no_road_required", "en")
    assert rows[1].icon.key == ("/shared/gui/buffbar/buffbar_icon_buff_unconnected.png")
    assert rows[1].show_label is True

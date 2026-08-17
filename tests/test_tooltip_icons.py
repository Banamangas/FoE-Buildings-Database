from foe_buildings.ui import tooltip_icons


def test_feature_slugs():
    assert tooltip_icons.FEATURE_SLUGS["battleground"] == "_gbg"
    assert tooltip_icons.FEATURE_SLUGS["guild_expedition"] == "_ge"
    assert tooltip_icons.FEATURE_SLUGS["guild_raids"] == "_qi"


def test_get_boost_icon_filename_base():
    assert tooltip_icons.get_boost_icon_filename("att_boost_attacker") == "red_attack.png"
    assert tooltip_icons.get_boost_icon_filename("def_boost_attacker") == "red_defense.png"
    assert tooltip_icons.get_boost_icon_filename("att_boost_defender") == "blue_attack.png"
    assert tooltip_icons.get_boost_icon_filename("def_boost_defender") == "blue_defense.png"


def test_get_boost_icon_filename_combined():
    assert tooltip_icons.get_boost_icon_filename("att_def_boost_attacker") == "att_def_boost_attacker.png"
    assert tooltip_icons.get_boost_icon_filename("att_def_boost_defender") == "att_def_boost_defender.png"


def test_get_boost_icon_filename_with_feature():
    assert tooltip_icons.get_boost_icon_filename("att_boost_attacker", "battleground") == "red_gbg_attack.png"
    assert tooltip_icons.get_boost_icon_filename("att_def_boost_attacker", "battleground") == "att_def_boost_attacker_gbg.png"


def test_get_boost_icon_filename_unknown():
    assert tooltip_icons.get_boost_icon_filename("unknown_boost") is None


def test_resolve_icon_returns_data_uri():
    result = tooltip_icons.resolve_icon("red_attack.png")
    assert result is not None
    assert result.startswith("data:image/png;base64,")


def test_resolve_icon_empty_input():
    assert tooltip_icons.resolve_icon(None) is None
    assert tooltip_icons.resolve_icon("") is None


def test_resolve_icon_missing_file():
    assert tooltip_icons.resolve_icon("definitely_missing_icon.png") is None

from foe_buildings.ui import tooltip_icons


def test_feature_suffixes_match_forge_hammer():
    assert tooltip_icons.FEATURE_SUFFIXES == {
        "all": "",
        "battleground": "_gbg",
        "guild_expedition": "_gex",
        "guild_raids": "_gr",
    }


def test_boost_icon_key_keeps_raw_type_and_exact_feature_suffix():
    assert tooltip_icons.boost_icon_key(
        "att_def_boost_attacker_defender", "guild_expedition"
    ) == "att_def_boost_attacker_defender_gex"
    assert tooltip_icons.boost_icon_key(
        "att_def_boost_defender", "guild_raids"
    ) == "att_def_boost_defender_gr"


def test_icon_candidates_match_forge_hammer_order():
    assert tooltip_icons.icon_candidates("selection_kit_2")[:6] == [
        "/shared/icons/selection_kit_2.png",
        "/shared/gui/upgrade/upgrade_icon_selection_kit_2.png",
        "/shared/icons/selection_kit.png",
        "/shared/icons/goods/icon_fine_selection_kit_2.png",
        "/shared/icons/reward_icons/reward_icon_selection_kit_2.png",
        "/shared/icons/reward_icons/reward_icon_selection_kit.png",
    ]


def test_icon_candidates_add_entity_asset_fallback():
    assert tooltip_icons.icon_candidates(
        "W_Test_2", entity_asset_id="W_MultiAge_Test"
    )[-1] == "/city/buildings/W_SS_MultiAge_Test.png"


def test_direct_asset_path_is_not_rewritten():
    path = "/shared/gui/buffbar/buffbar_icon_buff_unconnected.png"
    assert tooltip_icons.icon_candidates(path) == [path]


def test_resolve_game_icon_uses_first_matching_forgehx_path():
    assets = {"/shared/icons/money.png": "abc123"}
    result = tooltip_icons.resolve_game_icon("money", "Coins", asset_map=assets)
    assert result.key == "money"
    assert result.accessible_name == "Coins"
    assert result.url == (
        "https://foezz.innogamescdn.com/assets/shared/icons/money-abc123.png"
    )


def test_resolve_game_icon_falls_back_to_existing_local_icon(monkeypatch):
    monkeypatch.setattr(tooltip_icons, "get_icon_base64", lambda name: "encoded")
    result = tooltip_icons.resolve_game_icon("money", "Coins", asset_map={})
    assert result.url == "data:image/png;base64,encoded"


def test_resolve_game_icon_keeps_missing_icon_metadata():
    result = tooltip_icons.resolve_game_icon(
        "unknown_key", "Unknown reward", asset_map={}
    )
    assert result.url is None
    assert result.accessible_name == "Unknown reward"

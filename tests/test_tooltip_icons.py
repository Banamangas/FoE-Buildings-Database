from pathlib import Path

import pytest

from foe_buildings.ui import tooltip_icons


def test_feature_suffixes_match_forge_hammer():
    assert tooltip_icons.FEATURE_SUFFIXES == {
        "all": "",
        "battleground": "_gbg",
        "guild_expedition": "_gex",
        "guild_raids": "_gr",
    }


def test_boost_icon_key_keeps_raw_type_and_exact_feature_suffix():
    assert (
        tooltip_icons.boost_icon_key(
            "att_def_boost_attacker_defender", "guild_expedition"
        )
        == "att_def_boost_attacker_defender_gex"
    )
    assert (
        tooltip_icons.boost_icon_key("att_def_boost_defender", "guild_raids")
        == "att_def_boost_defender_gr"
    )


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
    assert (
        tooltip_icons.icon_candidates("W_Test_2", entity_asset_id="W_MultiAge_Test")[-1]
        == "/city/buildings/W_SS_MultiAge_Test.png"
    )


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


SAFE_LOCAL_ALIASES = {
    "guild_raids_action_points_collection": "qa_per_hour",
    "guild_raids_action_points_capacity": "qa_capacity",
    "att_boost_attacker_gbg": "red_gbg_attack",
    "def_boost_attacker_gbg": "red_gbg_defense",
    "att_boost_defender_gbg": "blue_gbg_attack",
    "def_boost_defender_gbg": "blue_gbg_defense",
    "att_boost_attacker_gex": "red_ge_attack",
    "def_boost_attacker_gex": "red_ge_defense",
    "att_boost_defender_gex": "blue_ge_attack",
    "def_boost_defender_gex": "blue_ge_defense",
    "att_boost_attacker_gr": "red_qi_attack",
    "def_boost_attacker_gr": "red_qi_defense",
    "att_boost_defender_gr": "blue_qi_attack",
    "def_boost_defender_gr": "blue_qi_defense",
    "next_age_random_goods": "next_age_goods",
    "random_goods_of_previous_age": "prev_age_goods",
    "random_goods_chest": "goods",
    "special_goods": "special_goods",
    "all_goods_of_next_age": "next_age_goods",
    "all_goods_of_previous_age": "prev_age_goods",
    "treasury_goods_of_next_age": "guild_goods",
    "treasury_goods_of_previous_age": "guild_goods",
}


@pytest.mark.parametrize("icon_key", SAFE_LOCAL_ALIASES)
def test_safe_aliases_resolve_to_existing_local_files(icon_key):
    result = tooltip_icons.resolve_game_icon(icon_key, icon_key, asset_map={})

    assert result.url is not None
    assert result.url.startswith("data:image/png;base64,")


def test_every_safe_alias_target_exists():
    icon_directory = Path(__file__).parents[1] / "assets" / "icons"

    assert tooltip_icons.LOCAL_ICON_FALLBACKS.items() >= SAFE_LOCAL_ALIASES.items()
    assert all(
        (icon_directory / f"{local_name}.png").is_file()
        for local_name in SAFE_LOCAL_ALIASES.values()
    )


def test_forgehx_candidate_beats_safe_local_alias(monkeypatch):
    def fail_if_local_icon_is_read(_name):
        raise AssertionError("local alias must follow all ForgeHX candidates")

    monkeypatch.setattr(tooltip_icons, "get_icon_base64", fail_if_local_icon_is_read)
    result = tooltip_icons.resolve_game_icon(
        "next_age_random_goods",
        "Next-age goods",
        asset_map={"/shared/icons/next_age_random_goods.png": "cdn-hash"},
    )

    assert result.url == (
        "https://foezz.innogamescdn.com/assets/shared/icons/"
        "next_age_random_goods-cdn-hash.png"
    )


@pytest.mark.parametrize(
    "icon_key",
    [
        f"{boost_type}{suffix}"
        for boost_type in (
            "att_def_boost_attacker",
            "att_def_boost_defender",
            "att_def_boost_attacker_defender",
        )
        for suffix in ("", "_gbg", "_gex", "_gr")
    ],
)
def test_combined_boost_keys_remain_unresolved_locally(icon_key):
    assert tooltip_icons.resolve_game_icon(icon_key, icon_key, asset_map={}).url is None


def test_unknown_military_key_remains_unresolved_locally():
    assert (
        tooltip_icons.resolve_game_icon("military", "Military", asset_map={}).url
        is None
    )


@pytest.mark.parametrize(
    "icon_name",
    [
        "supplies.png",
        "special_goods.png",
        "next_age_goods.png",
        "prev_age_goods.png",
        "red_attack.png",
    ],
)
def test_resolve_icon_keeps_existing_local_filenames(icon_name):
    result = tooltip_icons.resolve_icon(icon_name)
    assert result is not None
    assert result.startswith("data:image/png;base64,")


def test_resolve_icon_keeps_empty_input_empty():
    assert tooltip_icons.resolve_icon(None) is None
    assert tooltip_icons.resolve_icon("") is None


def test_resolve_icon_excludes_generated_combined_boost_icons():
    assert tooltip_icons.resolve_icon("att_def_boost_attacker.png") is None


def test_resolve_boost_icon_falls_back_to_base_local_icon():
    result = tooltip_icons.resolve_boost_icon("att_boost_attacker", "guild_raids")
    assert result is not None
    assert result.startswith("data:image/png;base64,")

import pytest

from foe_buildings.ui import tooltip
from foe_buildings.ui.tooltip import (
    _render_produces,
    render_building_tooltip,
)
from foe_buildings.ui.tooltip_icons import ResolvedIcon


def resource_product(resource, amount, **extra):
    return {
        "type": "resources",
        "playerResources": {"resources": {resource: amount}},
        **extra,
    }


def guild_resource_product(resource, amount, **extra):
    return {
        "type": "guildResources",
        "guildResources": {"resources": {resource: amount}},
        **extra,
    }


def option(duration, *products):
    return {"time": duration, "products": list(products)}


def production_entity(*options, rewards=None):
    all_age = {"production": {"options": list(options)}}
    if rewards is not None:
        all_age["lookup"] = {"rewards": rewards}
    return {"components": {"AllAge": all_age}}


def random_product(*outcomes, **extra):
    return {
        "type": "random",
        "products": [
            {"product": product, "dropChance": probability}
            for product, probability in outcomes
        ],
        **extra,
    }


def entity_with_two_random_products():
    return production_entity(
        option(
            86400,
            random_product(
                (resource_product("money", 10), 0.25),
                (resource_product("strategy_points", 2), 0.75),
            ),
            random_product(
                (resource_product("all_goods_of_age", 5), 0.5),
                (resource_product("medals", 20), 0.5),
            ),
        )
    )


def test_one_shared_duration_moves_to_produces_heading():
    entity = production_entity(
        option(86400, resource_product("money", 100)),
        option(86400, resource_product("strategy_points", 5)),
    )

    sections = render_building_tooltip(entity, "en")
    section = next(section for section in sections if section.key == "produces")

    assert section.title == "Produces"
    assert section.shared_duration == 86400
    assert [row.value for row in section.rows] == ["100", "5"]
    assert all(row.duration is None for row in section.rows)


def test_mixed_durations_stay_on_each_production_row():
    entity = production_entity(
        option(3600, resource_product("money", 100)),
        option(86400, resource_product("strategy_points", 5)),
    )

    sections = render_building_tooltip(entity, "en")
    section = next(section for section in sections if section.key == "produces")

    assert section.shared_duration is None
    assert [row.duration for row in section.rows] == [3600, 86400]
    assert [row.value for row in section.rows] == ["100", "5"]


def test_two_random_products_remain_two_independent_groups():
    result = _render_produces(entity_with_two_random_products(), "en")

    assert len(result.random_groups) == 2
    assert [len(group.outcomes) for group in result.random_groups] == [2, 2]
    assert [outcome.probability for outcome in result.random_groups[0].outcomes] == [
        25,
        75,
    ]
    assert [outcome.probability for outcome in result.random_groups[1].outcomes] == [
        50,
        50,
    ]
    assert [outcome.row.value for outcome in result.random_groups[0].outcomes] == [
        "10",
        "2",
    ]


def test_mixed_duration_random_groups_keep_their_parent_option_duration():
    entity = production_entity(
        option(
            3600,
            random_product((resource_product("money", 10), 0.333)),
        ),
        option(
            86400,
            random_product((resource_product("strategy_points", 2), 0.667)),
        ),
    )

    result = _render_produces(entity, "en")

    assert result.shared_duration is None
    assert [group.duration for group in result.random_groups] == [3600, 86400]
    assert [group.outcomes[0].probability for group in result.random_groups] == [
        33,
        66,
    ]


def test_shared_duration_is_not_repeated_on_random_groups():
    entity = production_entity(
        option(
            86400,
            random_product((resource_product("money", 10), 0.5)),
        ),
        option(
            86400,
            random_product((resource_product("strategy_points", 2), 0.5)),
        ),
    )

    result = _render_produces(entity, "en")

    assert result.shared_duration == 86400
    assert [group.duration for group in result.random_groups] == [None, None]


def test_generic_rewards_use_exact_primary_and_marker_icon_keys():
    rewards = {
        "goods_reward": {
            "name": "50 Goods",
            "type": "resource",
            "subType": "era_goods",
        },
        "normal_reward": {
            "name": "Mass Self-Aid Kit",
            "type": "genericReward",
            "iconAssetName": "mass_self_aid_kit",
        },
        "fragment_reward": {
            "name": "10x Fragments of Test Selection Kit",
            "type": "genericReward",
            "iconAssetName": "icon_fragment",
            "requiredAmount": 100,
            "assembledReward": {"iconAssetName": "test_selection_kit"},
        },
    }
    entity = production_entity(
        option(
            86400,
            {
                "type": "genericReward",
                "reward": {"id": "goods_reward", "amount": 50},
            },
            {
                "type": "genericReward",
                "reward": {"id": "normal_reward", "amount": 1},
            },
            {
                "type": "genericReward",
                "reward": {"id": "fragment_reward"},
                "onlyWhenMotivated": True,
            },
        ),
        rewards=rewards,
    )

    result = _render_produces(entity, "en")

    assert [(row.icon.key, row.value) for row in result.rows] == [
        ("era_goods", "50"),
        ("mass_self_aid_kit", "1"),
        ("test_selection_kit", "10"),
    ]
    assert [marker.key for marker in result.rows[2].markers] == [
        "icon_tooltip_fragment",
        "when_motivated",
    ]
    assert all(row.suffix is None for row in result.rows)


@pytest.mark.parametrize(
    ("reward", "reward_ref", "expected"),
    [
        (
            {"name": "3x Reward", "totalAmount": 10, "amount": 8},
            {"amount": 2},
            "10",
        ),
        ({"name": "3x Reward", "amount": 8}, {"amount": 2}, "8"),
        ({"name": "3x Reward"}, {"amount": 2}, "3"),
        ({"name": "Reward"}, {"amount": 2}, "2"),
        ({"name": "Reward"}, {}, "1"),
    ],
)
def test_generic_reward_quantity_uses_lookup_then_reference_precedence(
    reward, reward_ref, expected
):
    rewards = {"reward": {"type": "genericReward", **reward}}
    entity = production_entity(
        option(
            3600,
            {
                "type": "genericReward",
                "reward": {"id": "reward", **reward_ref},
            },
        ),
        rewards=rewards,
    )

    result = _render_produces(entity, "en")

    assert result.rows[0].value == expected


def test_generic_unit_rewards_use_normal_unit_icon_semantics(monkeypatch):
    def fake_resolve_game_icon(key, accessible_name, entity_asset_id=None):
        urls = {
            "rogue": "rogue.png",
            "chivalry": "chivalry.png",
            "future_scout": "future_scout.png",
            "military": "military.png",
        }
        return ResolvedIcon(key, urls.get(key), accessible_name)

    monkeypatch.setattr(tooltip, "resolve_game_icon", fake_resolve_game_icon)
    rewards = {
        "rogue_reward": {
            "name": "2x Rogue",
            "type": "unit",
            "subType": "rogue",
        },
        "champion_reward": {
            "name": "3x Future Champion",
            "type": "unit",
            "subType": "future_champion",
        },
        "scout_reward": {
            "name": "4x Future Scout",
            "type": "unit",
            "subType": "future_scout",
        },
    }
    entity = production_entity(
        option(
            86400,
            {"type": "genericReward", "reward": {"id": "rogue_reward"}},
            {"type": "genericReward", "reward": {"id": "champion_reward"}},
            {"type": "genericReward", "reward": {"id": "scout_reward"}},
        ),
        rewards=rewards,
    )

    rows = _render_produces(entity, "en").rows

    assert [(row.icon.key, row.icon.url, row.value) for row in rows] == [
        ("rogue", "rogue.png", "2"),
        ("chivalry", "chivalry.png", "3"),
        ("future_scout", "future_scout.png", "4"),
    ]
    assert [(row.label, row.icon.accessible_name) for row in rows] == [
        ("Rogue", "Rogue"),
        ("Future Champion", "Future Champion"),
        ("Future Scout", "Future Scout"),
    ]


def test_generic_unit_reward_carries_aggregation_group(monkeypatch):
    def fake_resolve_game_icon(key, accessible_name, entity_asset_id=None):
        return ResolvedIcon(key, f"{key}.png", accessible_name)

    monkeypatch.setattr(tooltip, "resolve_game_icon", fake_resolve_game_icon)
    reward_id = "era_unit#short_ranged#CurrentEra#12"
    rewards = {
        reward_id: {
            "name": "12x Slinger",
            "type": "unit",
            "subType": "slinger",
        },
    }
    entity = production_entity(
        option(
            86400,
            {"type": "genericReward", "reward": {"id": reward_id}},
        ),
        rewards=rewards,
    )

    row = _render_produces(entity, "en").rows[0]
    assert row.label == "Ranged Units"
    assert row.value == "12"
    assert row.group_key == "CurrentEra#short_ranged"
    assert row.group_label == "Ranged Units"
    assert row.group_icon_key == "ranged_units"


def test_chest_reward_uses_name_quantity_for_unit_chest(monkeypatch):
    def fake_resolve_game_icon(key, accessible_name, entity_asset_id=None):
        return ResolvedIcon(key, f"{key}.png", accessible_name)

    monkeypatch.setattr(tooltip, "resolve_game_icon", fake_resolve_game_icon)
    rewards = {
        "unit_chest": {
            "name": "+20 Random Next Age Units",
            "type": "chest",
            "iconAssetName": "military",
            "possible_rewards": [
                {
                    "drop_chance": 100,
                    "reward": {
                        "type": "unit",
                        "subType": "militiaman",
                        "amount": 20,
                        "name": "20x Soldier",
                        "id": "era_unit#light_melee#NextEra#20",
                    },
                }
            ],
        }
    }
    entity = production_entity(
        option(
            86400,
            {
                "type": "genericReward",
                "reward": {"id": "unit_chest"},
                "onlyWhenMotivated": True,
            },
        ),
        rewards=rewards,
    )

    row = _render_produces(entity, "en").rows[0]
    assert row.value == "20"
    assert row.label == "Random Units of the Next Age"
    assert row.icon.key == "military"
    assert any(marker.key == "when_motivated" for marker in row.markers)


@pytest.mark.parametrize(
    ("resource", "expected_icon"),
    [
        ("era_goods", "all_goods_of_age"),
        ("random_good_of_next_age", "next_age_random_goods"),
        ("random_good_of_previous_age", "random_goods_of_previous_age"),
        ("random_good_of_age", "random_goods_chest"),
        ("random_good_of_age_1", "random_goods_chest"),
        ("random_good_of_age_2", "random_goods_chest"),
        ("random_good_of_age_3", "random_goods_chest"),
        ("each_special_goods_up_to_age", "special_goods"),
    ],
)
def test_player_resources_use_forge_hammer_canonical_icons(resource, expected_icon):
    entity = production_entity(option(3600, resource_product(resource, 5)))

    row = _render_produces(entity, "en").rows[0]

    assert (row.icon.key, row.value) == (expected_icon, "5")


@pytest.mark.parametrize(
    ("resource", "expected_icon"),
    [
        ("era_goods", "treasury_goods"),
        ("all_goods_of_age", "treasury_goods"),
        ("random_good_of_age", "treasury_goods"),
        ("all_goods_of_next_age", "treasury_goods_of_next_age"),
        ("all_goods_of_previous_age", "treasury_goods_of_previous_age"),
        ("random_good_of_age_1", "random_good_of_age_1"),
    ],
)
def test_guild_resources_use_exact_treasury_canonical_icons(resource, expected_icon):
    entity = production_entity(option(3600, guild_resource_product(resource, 6)))

    row = _render_produces(entity, "en").rows[0]

    assert (row.icon.key, row.value) == (expected_icon, "6")


def test_player_and_guild_era_goods_use_different_canonical_icons():
    entity = production_entity(
        option(
            3600,
            resource_product("era_goods", 5),
            guild_resource_product("era_goods", 7),
        )
    )

    rows = _render_produces(entity, "en").rows

    assert [(row.icon.key, row.value) for row in rows] == [
        ("all_goods_of_age", "5"),
        ("treasury_goods", "7"),
    ]


def test_ordinary_and_nested_random_resources_keep_context_canonicalization():
    entity = production_entity(
        option(
            86400,
            resource_product("money", 10),
            random_product(
                (resource_product("random_good_of_next_age", 2), 0.25),
                (guild_resource_product("all_goods_of_previous_age", 3), 0.75),
            ),
        )
    )

    result = _render_produces(entity, "en")

    assert [(row.icon.key, row.value) for row in result.rows] == [("money", "10")]
    assert [
        (outcome.row.icon.key, outcome.row.value, outcome.probability)
        for outcome in result.random_groups[0].outcomes
    ] == [
        ("next_age_random_goods", "2", 25),
        ("treasury_goods_of_previous_age", "3", 75),
    ]


def test_motivated_random_product_marks_the_group():
    entity = production_entity(
        option(
            86400,
            random_product(
                (resource_product("money", 10), 1),
                onlyWhenMotivated=True,
            ),
        )
    )

    result = _render_produces(entity, "en")

    assert [marker.key for marker in result.random_groups[0].markers] == [
        "when_motivated"
    ]


def test_unit_icons_use_exact_id_then_bound_military_fallback():
    resolved_keys = []

    def fake_icon_resolver(key, accessible_name, entity_asset_id):
        resolved_keys.append(key)
        urls = {
            "rogue": "rogue.png",
            "chivalry": "chivalry.png",
            "military": "military.png",
        }
        return ResolvedIcon(key, urls.get(key), accessible_name)

    entity = production_entity(
        option(
            86400,
            {"type": "unit", "unitTypeId": "rogue", "amount": 1},
            {"type": "unit", "unitTypeId": "future_champion", "amount": 2},
            {"type": "unit", "unitTypeId": "future_scout", "amount": 3},
        )
    )

    result = _render_produces(entity, "en", fake_icon_resolver)

    assert [
        (row.icon.key, row.icon.url, row.icon.accessible_name) for row in result.rows
    ] == [
        ("rogue", "rogue.png", "rogue"),
        ("chivalry", "chivalry.png", "future_champion"),
        ("future_scout", "military.png", "future_scout"),
    ]
    assert resolved_keys == ["rogue", "chivalry", "future_scout", "military"]


def test_unknown_generic_reward_retains_reward_id_and_quantity():
    entity = production_entity(
        option(
            3600,
            {
                "type": "genericReward",
                "reward": {"id": "unknown_reward", "amount": 7},
            },
        ),
        rewards={},
    )

    result = _render_produces(entity, "en")

    assert [(row.label, row.value) for row in result.rows] == [("unknown_reward", "7")]

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
    assert [
        outcome.probability for outcome in result.random_groups[0].outcomes
    ] == [25, 75]
    assert [
        outcome.probability for outcome in result.random_groups[1].outcomes
    ] == [50, 50]
    assert [
        outcome.row.value for outcome in result.random_groups[0].outcomes
    ] == ["10", "2"]


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


def test_unit_icons_use_deterministic_mappings_then_exact_id_fallback(monkeypatch):
    def fake_resolve_game_icon(key, accessible_name, entity_asset_id=None):
        urls = {
            "rogue": "rogue.png",
            "chivalry": "chivalry.png",
            "military": "military.png",
        }
        return ResolvedIcon(key, urls.get(key), accessible_name)

    monkeypatch.setattr(tooltip, "resolve_game_icon", fake_resolve_game_icon)
    entity = production_entity(
        option(
            86400,
            {"type": "unit", "unitTypeId": "rogue", "amount": 1},
            {"type": "unit", "unitTypeId": "future_champion", "amount": 2},
            {"type": "unit", "unitTypeId": "future_scout", "amount": 3},
        )
    )

    result = _render_produces(entity, "en")

    assert [(row.icon.key, row.icon.url) for row in result.rows] == [
        ("rogue", "rogue.png"),
        ("chivalry", "chivalry.png"),
        ("future_scout", "military.png"),
    ]


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

    assert [(row.label, row.value) for row in result.rows] == [
        ("unknown_reward", "7")
    ]

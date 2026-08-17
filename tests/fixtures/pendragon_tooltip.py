"""Compact fixture matching Pendragon's live multi-era component layout."""

PENDRAGON_TOOLTIP_ENTITY = {
    "id": "W_MultiAge_ARTHUR26A10",
    "name": "Pendragon's Throne of Camelot",
    "components": {
        "AllAge": {
            "placement": {"size": {"x": 6, "y": 6}},
            "constructionTime": {"time": 5},
            "flags": {"flags": 51},
            "socialInteraction": {"interactionType": "motivate"},
            "ally": {"rooms": [{"allyType": "military"}]},
        },
        "StellarAgeDiscovery": {
            "staticResources": {"resources": {"resources": {"population": 67000}}},
            "happiness": {"provided": 100480},
            "boosts": {
                "boosts": [
                    {
                        "type": "att_def_boost_attacker_defender",
                        "value": 246,
                        "targetedFeature": "all",
                    },
                    {
                        "type": "att_def_boost_attacker_defender",
                        "value": 371,
                        "targetedFeature": "battleground",
                    },
                    {
                        "type": "att_def_boost_defender",
                        "value": 30,
                        "targetedFeature": "guild_raids",
                    },
                    {"type": "coin_production", "value": 40},
                    {"type": "forge_points_production", "value": 4},
                    {"type": "goods_production", "value": 2},
                    {"type": "guild_raids_action_points_collection", "value": 200},
                    {"type": "guild_raids_action_points_capacity", "value": 8000},
                ]
            },
            "lookup": {
                "rewards": {
                    "pendragon_fragment_5": {
                        "id": "pendragon_fragment_5",
                        "name": "5x Fragments of Legends of Camelot Selection Kit",
                        "type": "genericReward",
                        "iconAssetName": "icon_fragment",
                        "requiredAmount": 200,
                        "assembledReward": {"iconAssetName": "selection_kit_pendragon"},
                    },
                    "pendragon_fragment_10": {
                        "id": "pendragon_fragment_10",
                        "name": "10x Fragments of Mass Self-Aid Kit",
                        "type": "genericReward",
                        "iconAssetName": "icon_fragment",
                        "requiredAmount": 200,
                        "assembledReward": {"iconAssetName": "selection_kit_pendragon"},
                    },
                }
            },
            "production": {
                "options": [
                    {
                        "time": 86400,
                        "products": [
                            {
                                "type": "resources",
                                "playerResources": {"resources": {"money": 776610}},
                            },
                            {
                                "type": "resources",
                                "onlyWhenMotivated": True,
                                "playerResources": {
                                    "resources": {
                                        "strategy_points": 411,
                                        "all_goods_of_age": 575,
                                    }
                                },
                            },
                            {
                                "type": "genericReward",
                                "reward": {"id": "pendragon_fragment_5"},
                                "onlyWhenMotivated": True,
                            },
                            {
                                "type": "genericReward",
                                "reward": {"id": "pendragon_fragment_10"},
                                "onlyWhenMotivated": True,
                            },
                        ],
                    }
                ]
            },
        },
    },
}

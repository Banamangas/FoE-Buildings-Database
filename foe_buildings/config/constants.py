# --- Game Data Constants ---
ERAS_DICT = {
    "SpaceAgeSpaceHub": "Space Age: Space Hub",
    "SpaceAgeTitan": "Space Age: Titan",
    "SpaceAgeJupiterMoon": "Space Age: Jupiter Moon",
    "SpaceAgeVenus": "Space Age: Venus",
    "SpaceAgeAsteroidBelt": "Space Age: Asteroid Belt",
    "SpaceAgeMars": "Space Age: Mars",
    "VirtualFuture": "Virtual Future",
    "OceanicFuture": "Oceanic Future",
    "ArcticFuture": "Arctic Future",
    "FutureEra": "Future Era",
    "TomorrowEra": "Tomorrow Era",
    "ContemporaryEra": "Contemporary Era",
    "PostModernEra": "Post-Modern Era",
    "ModernEra": "Modern Era",
    "ProgressiveEra": "Progressive Era",
    "IndustrialAge": "Industrial Age",
    "ColonialAge": "Colonial Age",
    "LateMiddleAge": "Late Middle Age",
    "HighMiddleAge": "High Middle Age",
    "EarlyMiddleAge": "Early Middle Age",
    "IronAge": "Iron Age",
    "BronzeAge": "Bronze Age",
}

ERAS_LEVEL_MAP = {
    22: "SpaceAgeSpaceHub",
    21: "SpaceAgeTitan",
    20: "SpaceAgeJupiterMoon",
    19: "SpaceAgeVenus",
    18: "SpaceAgeAsteroidBelt",
    17: "SpaceAgeMars",
    16: "VirtualFuture",
    15: "OceanicFuture",
    14: "ArcticFuture",
    13: "FutureEra",
    12: "TomorrowEra",
    11: "ContemporaryEra",
    10: "PostModernEra",
    9: "ModernEra",
    8: "ProgressiveEra",
    7: "IndustrialAge",
    6: "ColonialAge",
    5: "LateMiddleAge",
    4: "HighMiddleAge",
    3: "EarlyMiddleAge",
    2: "IronAge",
    1: "BronzeAge",
}

# Define column groups
COLUMN_GROUPS = {
    "basic_info": {
        "columns": [
            "Event",
            "Weighted Efficiency",
            "Total Score",
            "size",
            "Nbr of squares (Avg)",
            "Road",
            "Limited",
            "Ally room",
            "Population",
            "Happiness",
            "Quantity",
            "Source",
        ]
    },
    "production": {
        "columns": [
            "coins",
            "supplies",
            "medals",
            "forge_points",
            "forgepoint_package",
            "goods",
            "next_age_goods",
            "prev_age_goods",
            "special_goods",
            "guild_goods",
        ]
    },
    "military": {
        "columns": [
            "rogues",
            "fast_units",
            "heavy_units",
            "ranged_units",
            "artillery_units",
            "light_units",
            "next_age_fast_units",
            "next_age_heavy_units",
            "next_age_ranged_units",
            "next_age_artillery_units",
            "next_age_light_units",
        ]
    },
    "base_army": {
        "columns": ["Red Attack", "Red Defense", "Blue Attack", "Blue Defense"]
    },
    "gbg": {
        "columns": [
            "Red GBG Attack",
            "Red GBG Defense",
            "Blue GBG Attack",
            "Blue GBG Defense",
        ]
    },
    "ge": {
        "columns": [
            "Red GE Attack",
            "Red GE Defense",
            "Blue GE Attack",
            "Blue GE Defense",
        ]
    },
    "qi": {
        "columns": [
            "Red QI Attack",
            "Red QI Defense",
            "Blue QI Attack",
            "Blue QI Defense",
            "QI Coin %",
            "QI Coin at start",
            "QI Supplies %",
            "QI Supplies at start",
            "QI Goods at start",
            "QI Units at start",
            "QA per hour",
            "QA Capacity",
        ]
    },
    "boosts": {
        "columns": [
            "Coin %",
            "Supplies %",
            "FP boost",
            "Guild Goods Production %",
            "Special Goods Production %",
            "Medal Boost",
            "Goods Boost",
        ]
    },
    "consumables": {
        "columns": [
            "finish_special_production",
            "finish_goods_production",
            "store_kit",
            "mass_self_aid_kit",
            "self_aid_kit",
            "one_up_kit",
            "renovation_kit",
            "finish_all_supplies",
        ]
    },
    "other": {"columns": ["Other productions"]},
}

# Predefined column presets for different analysis types
COLUMN_PRESETS = {
    "basic_analysis": {
        "name_key": "preset_basic_analysis",
        "columns": ["Event", "size", "Road", "Limited", "Ally room"],
    },
    "production_focus": {
        "name_key": "preset_production_focus",
        "columns": [
            "Weighted Efficiency",
            "forge_points",
            "goods",
            "prev_age_goods",
            "next_age_goods",
            "special_goods",
            "guild_goods",
        ],
    },
    "military_focus": {
        "name_key": "preset_military_focus",
        "columns": [
            "Weighted Efficiency",
            "rogues",
            "fast_units",
            "heavy_units",
            "ranged_units",
            "artillery_units",
            "light_units",
            "next_age_fast_units",
            "next_age_heavy_units",
            "next_age_ranged_units",
            "next_age_artillery_units",
            "next_age_light_units",
        ],
    },
    "ge_focus": {
        "name_key": "preset_ge_focus",
        "columns": [
            "Weighted Efficiency",
            "Red Attack",
            "Red Defense",
            "Blue Attack",
            "Blue Defense",
            "Red GE Attack",
            "Red GE Defense",
            "Blue GE Attack",
            "Blue GE Defense",
        ],
    },
    "gbg_focus": {
        "name_key": "preset_gbg_focus",
        "columns": [
            "Weighted Efficiency",
            "Red Attack",
            "Red Defense",
            "Blue Attack",
            "Blue Defense",
            "Red GBG Attack",
            "Red GBG Defense",
            "Blue GBG Attack",
            "Blue GBG Defense",
        ],
    },
    "qi_focus": {
        "name_key": "preset_qi_focus",
        "columns": [
            "Weighted Efficiency",
            "Red QI Attack",
            "Red QI Defense",
            "Blue QI Attack",
            "Blue QI Defense",
            "QI Coin %",
            "QI Coin at start",
            "QI Supplies %",
            "QI Supplies at start",
            "QI Goods at start",
            "QI Units at start",
            "QA per hour",
            "QA Capacity",
        ],
    },
    "consumables_focus": {
        "name_key": "preset_consumables_focus",
        "columns": [
            "Weighted Efficiency",
            "finish_special_production",
            "finish_goods_production",
            "rush_mass_supplies_24h",
            "store_kit",
            "mass_self_aid_kit",
            "self_aid_kit",
            "renovation_kit",
            "one_up_kit",
        ],
    },
    "fsp_usage": {
        "name_key": "preset_fsp_usage",
        "columns": [
            "Weighted Efficiency",
            "Total Score",
            "finish_special_production",
            "forge_points",
            "goods",
            "prev_age_goods",
            "next_age_goods",
            "guild_goods",
        ],
    },
}

# Columns to exclude from certain operations
ICON_EXCLUDED_COLUMNS = {
    "name",
    "Translated Era",
    "Total Score",
    "Unit type",
    "Next Age Unit type",
    "Weighted Efficiency",
    "Quantity",
    "Source",
}

PER_SQUARE_EXCLUDED_COLUMNS = {
    "name",
    "Event",
    "Translated Era",
    "Nbr of squares (Avg)",
    "Road",
    "Limited",
    "Ally room",
    "size",
    "Unit type",
    "Next Age Unit type",
    "Other productions",
    "Weighted Efficiency",
    "Total Score",
    "Quantity",
    "Source",
}

# --- Column Name Constants ---
# Use these instead of string literals to prevent typos and ease renaming.
COL_NAME = "name"
COL_ERA = "Era"
COL_TRANSLATED_ERA = "Translated Era"
COL_EVENT = "Event"
COL_LIMITED = "Limited"
COL_ALLY_ROOM = "Ally room"
COL_ROAD = "Road"
COL_SIZE = "Nbr of squares (Avg)"
COL_ASSET_ID = "asset_id"
COL_WEIGHTED_EFFICIENCY = "Weighted Efficiency"
COL_TOTAL_SCORE = "Total Score"

# Columns formatted as percentages
PERCENTAGE_COLUMNS = {
    "Red Attack",
    "Red Defense",
    "Blue Attack",
    "Blue Defense",
    "Red GBG Attack",
    "Red GBG Defense",
    "Blue GBG Attack",
    "Blue GBG Defense",
    "Red GE Attack",
    "Red GE Defense",
    "Blue GE Attack",
    "Blue GE Defense",
    "Red QI Attack",
    "Red QI Defense",
    "Blue QI Attack",
    "Blue QI Defense",
    "QI Coin %",
    "QI Supplies %",
    "Coin %",
    "Supplies %",
    "FP boost",
    "Guild Goods Production %",
    "Special Goods Production %",
    "Medal Boost",
    "Goods Boost",
}

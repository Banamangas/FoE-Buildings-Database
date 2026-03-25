import logging
import streamlit as st

# --- Logging Setup ---
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s - %(filename)s - %(lineno)d')
logger = logging.getLogger(__name__)

# --- File Paths ---
ASSETS_PATH = 'assets'
TRANSLATIONS_PATH = 'translations'
APP_ICON = 'assets/icons/icon.png'

# --- API Configuration ---
# Set these in .streamlit/secrets.toml:
#   [foe_api]
#   url = "https://your-subdomain.duckdns.org"
#   key = "foe_your_api_key_here"

def get_api_config() -> tuple:
    """Get API URL and key from Streamlit secrets."""
    try:
        api_url = st.secrets["foe_api"]["url"]
        api_key = st.secrets["foe_api"]["key"]
        return api_url.rstrip('/'), api_key
    except KeyError:
        st.error("API configuration not found in secrets. Please configure foe_api.url and foe_api.key in .streamlit/secrets.toml")
        st.stop()

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
    "BronzeAge": "Bronze Age"
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
    1: "BronzeAge"
}

# --- Column Name Constants ---
COL_ERA = 'Era'
COL_NAME = 'name'

# Columns that represent outputs for weighting
WEIGHTABLE_COLUMNS = [
    "forge_points", "forgepoint_package",
    "goods", "next_age_goods", "prev_age_goods", "special_goods", "guild_goods",
    "rogues", "fast_units", "heavy_units", "ranged_units", "artillery_units", "light_units",
    "next_age_fast_units", "next_age_heavy_units", "next_age_ranged_units", "next_age_artillery_units", "next_age_light_units",
    "Population",
    "Red Attack", "Red Defense", "Blue Attack", "Blue Defense",
    "Red GBG Attack", "Red GBG Defense", "Blue GBG Attack", "Blue GBG Defense",
    "Red GE Attack", "Red GE Defense", "Blue GE Attack", "Blue GE Defense",
    "Red QI Attack", "Red QI Defense", "Blue QI Attack", "Blue QI Defense",
    "finish_special_production"
]

# Define column groups
COLUMN_GROUPS = {
    "basic_info": {
        "key": "basic_info",
        "columns": ["Event", "Weighted Efficiency", "Total Score", "size", "Nbr of squares (Avg)", "Road", "Limited", "Ally room", "Population", "Happiness", "Quantity", "Source"]
    },
    "production": {
        "key": "production",
        "columns": ["coins", "supplies", "medals", "forge_points", "forgepoint_package", "goods",
                    "next_age_goods", "prev_age_goods", "special_goods", "guild_goods"]
    },
    "military": {
        "key": "military",
        "columns": ["rogues", "fast_units", "heavy_units", "ranged_units", "artillery_units", "light_units", "next_age_fast_units", "next_age_heavy_units", "next_age_ranged_units", "next_age_artillery_units", "next_age_light_units"]
    },
    "base_army": {
        "key": "base_army",
        "columns": ["Red Attack", "Red Defense", "Blue Attack", "Blue Defense"]
    },
    "gbg": {
        "key": "gbg",
        "columns": ["Red GBG Attack", "Red GBG Defense", "Blue GBG Attack", "Blue GBG Defense"]
    },
    "ge": {
        "key": "ge",
        "columns": ["Red GE Attack", "Red GE Defense", "Blue GE Attack", "Blue GE Defense"]
    },
    "qi": {
        "key": "qi",
        "columns": ["Red QI Attack", "Red QI Defense", "Blue QI Attack", "Blue QI Defense",
                    "QI Coin %", "QI Coin at start", "QI Supplies %", "QI Supplies at start", "QI Goods at start", "QI Units at start", "QA per hour", "QA Capacity"]
    },
    "boosts": {
        "key": "boosts",
        "columns": ["Coin %", "Supplies %", "FP boost", "Guild Goods Production %",
                    "Special Goods Production %", "Medal Boost", "Goods Boost"]
    },
    "consumables": {
        "key": "consumables",
        "columns": ["finish_special_production", "finish_goods_production", "store_kit", "mass_self_aid_kit", "self_aid_kit", "one_up_kit", "renovation_kit", "finish_all_supplies"]
    },
    "other": {
        "key": "other",
        "columns": ["Other productions"]
    }
}

# Predefined column presets for different analysis types
COLUMN_PRESETS = {
        "basic_analysis": {
            "name_key": "preset_basic_analysis",
            "columns": ["Event", "size", "Road", "Limited", "Ally room"]
        },
        "production_focus": {
            "name_key": "preset_production_focus",
            "columns": ["Weighted Efficiency", "forge_points", "goods", "prev_age_goods", "next_age_goods", "special_goods", "guild_goods"]
        },
        "military_focus": {
            "name_key": "preset_military_focus",
            "columns": ["Weighted Efficiency", "rogues",
                        "fast_units", "heavy_units", "ranged_units", "artillery_units", "light_units",
                        "next_age_fast_units", "next_age_heavy_units", "next_age_ranged_units", "next_age_artillery_units", "next_age_light_units"]
        },
        "ge_focus": {
            "name_key": "preset_ge_focus",
            "columns": ["Weighted Efficiency", "Red Attack", "Red Defense", "Blue Attack", "Blue Defense", "Red GE Attack", "Red GE Defense", "Blue GE Attack", "Blue GE Defense"]
        },
        "gbg_focus": {
            "name_key": "preset_gbg_focus",
            "columns": ["Weighted Efficiency", "Red Attack", "Red Defense", "Blue Attack", "Blue Defense","Red GBG Attack", "Red GBG Defense", "Blue GBG Attack", "Blue GBG Defense"]
        },
        "qi_focus": {
            "name_key": "preset_qi_focus",
            "columns": ["Weighted Efficiency", "Red QI Attack", "Red QI Defense", "Blue QI Attack", "Blue QI Defense",
                    "QI Coin %", "QI Coin at start", "QI Supplies %", "QI Supplies at start", "QI Goods at start", "QI Units at start", "QA per hour", "QA Capacity"]
        },
        "consumables_focus": {
            "name_key": "preset_consumables_focus",
            "columns": ["Weighted Efficiency", "finish_special_production", "finish_goods_production", "rush_mass_supplies_24h",
                        "store_kit", "mass_self_aid_kit", "self_aid_kit", "renovation_kit", "one_up_kit"]
        },
        "fsp_usage": {
            "name_key": "preset_fsp_usage",
            "columns": ["Weighted Efficiency", "Total Score", "finish_special_production", "forge_points", "goods", "prev_age_goods", "next_age_goods", "guild_goods"]
        }
    }

# Columns to exclude from certain operations
ICON_EXCLUDED_COLUMNS = {
    'name', 'Translated Era', 'Total Score',
    'Unit type', 'Next Age Unit type',
    'Weighted Efficiency', 'Quantity', 'Source'
}

PER_SQUARE_EXCLUDED_COLUMNS = [
    'name', 'Event', 'Translated Era', 'Nbr of squares (Avg)', 'Road', 'Limited', 'Ally room', 'size',
    'Unit type', 'Next Age Unit type', 'Other productions', 'Weighted Efficiency', 'Total Score', 'Quantity', 'Source'
]

# Columns formatted as percentages
PERCENTAGE_COLUMNS = {
    "Red Attack", "Red Defense", "Blue Attack", "Blue Defense",
    "Red GBG Attack", "Red GBG Defense", "Blue GBG Attack", "Blue GBG Defense",
    "Red GE Attack", "Red GE Defense", "Blue GE Attack", "Blue GE Defense",
    "Red QI Attack", "Red QI Defense", "Blue QI Attack", "Blue QI Defense",
    "QI Coin %", "QI Supplies %",
    "Coin %", "Supplies %", "FP boost", "Guild Goods Production %",
    "Special Goods Production %", "Medal Boost", "Goods Boost"
}

# Additive metrics
ADDITIVE_METRICS = [
    "coins", "supplies", "medals", "forge_points", "forgepoint_package", "goods",
    "next_age_goods", "prev_age_goods", "special_goods", "guild_goods", "Red Attack", "Red Defense", "Blue Attack", "Blue Defense",
    "Red GBG Attack", "Red GBG Defense", "Blue GBG Attack", "Blue GBG Defense",
    "Red GE Attack", "Red GE Defense", "Blue GE Attack", "Blue GE Defense",
    "Red QI Attack", "Red QI Defense", "Blue QI Attack", "Blue QI Defense",
    "QI Coin at start", "QI Supplies at start", "QI Goods at start", "QI Units at start", "QA per hour", "QA Capacity",
    "finish_special_production"
]

# Multiplicative metrics
BOOST_TO_BASE_MAPPING = {
    "FP boost": "forge_points",
    "Goods Boost": ["goods", "prev_age_goods", "next_age_goods"],
    "Guild Goods Production %": "guild_goods",
    "Special Goods Production %": "special_goods"
}

# User context configuration for multiplicative metrics
USER_CONTEXT_FIELDS = {
    "fp_daily_production": {
        "label_key": "fp_daily_production_label",
        "help_key": "fp_daily_production_help",
        "default": 0,
        "related_boosts": ["FP boost"]
    },
    "goods_current_production": {
        "label_key": "goods_current_production_label",
        "help_key": "goods_current_production_help",
        "default": 0,
        "related_boosts": ["Goods Boost"]
    },
    "goods_previous_production": {
        "label_key": "goods_previous_production_label",
        "help_key": "goods_previous_production_help",
        "default": 0,
        "related_boosts": ["Goods Boost"]
    },
    "goods_next_production": {
        "label_key": "goods_next_production_label",
        "help_key": "goods_next_production_help",
        "default": 0,
        "related_boosts": ["Goods Boost"]
    },
    "guild_goods_production": {
        "label_key": "guild_goods_production_label",
        "help_key": "guild_goods_production_help",
        "default": 0,
        "related_boosts": ["Guild Goods Production %"]
    },
    "special_goods_production": {
        "label_key": "special_goods_production_label",
        "help_key": "special_goods_production_help",
        "default": 0,
        "related_boosts": ["Special Goods Production %"]
    }
}

# User current boost percentages configuration
USER_BOOST_FIELDS = {
    "current_fp_boost": {
        "label_key": "current_fp_boost_label",
        "help_key": "current_fp_boost_help",
        "default": 0.0,
        "related_context": "fp_daily_production"
    },
    "current_goods_boost": {
        "label_key": "current_goods_boost_label",
        "help_key": "current_goods_boost_help",
        "default": 0.0,
        "related_context": ["goods_current_production", "goods_previous_production", "goods_next_production"]
    },
    "current_guild_goods_boost": {
        "label_key": "current_guild_goods_boost_label",
        "help_key": "current_guild_goods_boost_help",
        "default": 0.0,
        "related_context": "guild_goods_production"
    },
    "current_special_goods_boost": {
        "label_key": "current_special_goods_boost_label",
        "help_key": "current_special_goods_boost_help",
        "default": 0.0,
        "related_context": "special_goods_production"
    }
}

RANKING_POINTS_PER_RESOURCE = {
    "forge_points": 15,
    "goods": {
        "SpaceAgeSpaceHub": 69,
        "SpaceAgeTitan": 63,
        "SpaceAgeJupiterMoon": 55,
        "SpaceAgeVenus": 49.5,
        "SpaceAgeAsteroidBelt": 44.5,
        "SpaceAgeMars": 37.5,
        "VirtualFuture": 33,
        "OceanicFuture": 29,
        "ArcticFuture": 22.5,
        "FutureEra": 21,
        "TomorrowEra": 19.5,
        "ContemporaryEra": 13.5,
        "PostModernEra": 12.5,
        "ModernEra": 11.5,
        "ProgressiveEra": 6,
        "IndustrialAge": 5.5,
        "ColonialAge": 5,
        "LateMiddleAge": 4.5,
        "HighMiddleAge": 4,
        "EarlyMiddleAge": 3.5,
        "IronAge": 3,
        "BronzeAge": 2.5
    },
    "special_goods": {
        "SpaceAgeSpaceHub": 10,
        "SpaceAgeTitan": 10,
        "SpaceAgeJupiterMoon": 10,
        "SpaceAgeVenus": 10,
        "SpaceAgeAsteroidBelt": 10,
        "SpaceAgeMars": 10,
        "OceanicFuture": 42,
        "ArcticFuture": 42
    }
}

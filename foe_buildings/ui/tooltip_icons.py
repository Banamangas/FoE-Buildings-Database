from typing import Optional

from foe_buildings.ui.grid import get_icon_base64


FEATURE_SLUGS = {
    "all": "",
    "battleground": "_gbg",
    "guild_expedition": "_ge",
    "guild_raids": "_qi",
}

BOOST_ICON_MAP = {
    "att_boost_attacker": "red_attack.png",
    "def_boost_attacker": "red_defense.png",
    "att_boost_defender": "blue_attack.png",
    "def_boost_defender": "blue_defense.png",
    "att_def_boost_attacker": "att_def_boost_attacker.png",
    "att_def_boost_defender": "att_def_boost_defender.png",
    "att_def_boost_attacker_defender": "att_def_boost_attacker_defender.png",
    "coin_production": "coin_%.png",
    "supply_production": "supplies_%.png",
    "forge_points_production": "fp_boost.png",
    "goods_production": "goods_boost.png",
    "guild_goods_production": "guild_goods_production_%.png",
    "special_goods_production": "special_goods_production_%.png",
    "medals_boost": "medal_boost.png",
}


def get_boost_icon_filename(boost_type: str, feature: str = "all") -> Optional[str]:
    """Return the local icon filename for a boost key + feature context."""
    base_icon = BOOST_ICON_MAP.get(boost_type)
    if base_icon is None:
        return None
    if feature == "all":
        return base_icon
    slug = FEATURE_SLUGS.get(feature)
    if slug is None:
        return base_icon
    name, ext = base_icon.rsplit(".", 1)
    for suffix in ("_attack", "_defense"):
        if name.endswith(suffix):
            return f"{name[: -len(suffix)]}{slug}{suffix}.{ext}"
    return f"{name}{slug}.{ext}"


def resolve_icon(icon_name: Optional[str]) -> Optional[str]:
    """Return a base64 data URI for the given icon filename, or None."""
    if not icon_name:
        return None
    base64_str = get_icon_base64(icon_name.replace(".png", ""))
    if base64_str:
        return f"data:image/png;base64,{base64_str}"
    return None

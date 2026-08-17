from dataclasses import dataclass
import re
from typing import List, Mapping, Optional

from foe_buildings.data.loader import load_forgehx_asset_map
from foe_buildings.ui.grid import get_icon_base64
from foe_buildings.ui.images import FORGEHX_IMAGE_BASE


@dataclass(frozen=True)
class ResolvedIcon:
    key: str
    url: Optional[str]
    accessible_name: str


FEATURE_SUFFIXES = {
    "all": "",
    "battleground": "_gbg",
    "guild_expedition": "_gex",
    "guild_raids": "_gr",
}


LOCAL_ICON_FALLBACKS = {
    "money": "coins",
    "coins": "coins",
    "strategy_points": "forge_points",
    "forge_points": "forge_points",
    "all_goods_of_age": "goods",
    "era_goods": "goods",
    "goods": "goods",
    "treasury_goods": "guild_goods",
    "guild_goods": "guild_goods",
    "population": "population",
    "happiness": "happiness",
    "medals": "medals",
    "ranking_points": "medals",
    "rank": "medals",
    "size": "size",
    "road": "road",
    "rogue": "rogues",
    "rogues": "rogues",
    "fast_units": "fast_units",
    "heavy_units": "heavy_units",
    "light_units": "light_units",
    "ranged_units": "ranged_units",
    "artillery_units": "artillery_units",
    "next_age_fast_units": "next_age_fast_units",
    "next_age_heavy_units": "next_age_heavy_units",
    "next_age_light_units": "next_age_light_units",
    "next_age_ranged_units": "next_age_ranged_units",
    "next_age_artillery_units": "next_age_artillery_units",
    "self_aid_kit": "self_aid_kit",
    "mass_self_aid_kit": "mass_self_aid_kit",
    "renovation_kit": "renovation_kit",
    "one_up_kit": "one_up_kit",
    "store_kit": "store_kit",
    "finish_all_supplies": "finish_all_supplies",
    "finish_goods_production": "finish_goods_production",
    "finish_special_production": "finish_special_production",
    "forgepoint_package": "forgepoint_package",
    "ally_room": "ally_room",
    "qa_capacity": "qa_capacity",
    "qa_per_hour": "qa_per_hour",
    "att_boost_attacker": "red_attack",
    "def_boost_attacker": "red_defense",
    "att_boost_defender": "blue_attack",
    "def_boost_defender": "blue_defense",
    "coin_production": "coin_%",
    "supply_production": "supplies_%",
    "forge_points_production": "fp_boost",
    "goods_production": "goods_boost",
    "guild_goods_production": "guild_goods_production_%",
    "special_goods_production": "special_goods_production_%",
    "medals_boost": "medal_boost",
}


def boost_icon_key(boost_type: str, feature: str = "all") -> str:
    return f"{boost_type}{FEATURE_SUFFIXES.get(feature, '')}"


def _building_candidate(asset_id: str) -> Optional[str]:
    if "_" not in asset_id:
        return None
    prefix, suffix = asset_id.split("_", 1)
    return f"/city/buildings/{prefix}_SS_{suffix}.png"


def _append_unique(candidates: List[str], candidate: Optional[str]) -> None:
    if candidate and candidate not in candidates:
        candidates.append(candidate)


def icon_candidates(
    icon_key: str, entity_asset_id: Optional[str] = None
) -> List[str]:
    """Return Forge Hammer's ordered ForgeHX candidates without duplicates."""
    if icon_key.startswith("/"):
        return [icon_key]

    fallback_key = re.sub(r"_\d+$", "", icon_key)
    candidates: List[str] = []
    for candidate in (
        f"/shared/icons/{icon_key}.png",
        f"/shared/gui/upgrade/upgrade_icon_{icon_key}.png",
        f"/shared/icons/{fallback_key}.png",
        f"/shared/icons/goods/icon_fine_{icon_key}.png",
        f"/shared/icons/reward_icons/reward_icon_{icon_key}.png",
        f"/shared/icons/reward_icons/reward_icon_{fallback_key}.png",
        _building_candidate(icon_key),
        _building_candidate(fallback_key),
        _building_candidate(entity_asset_id) if entity_asset_id else None,
    ):
        _append_unique(candidates, candidate)
    return candidates


def _hashed_url(candidate: str, asset_hash: str) -> str:
    stem, extension = candidate.rsplit(".", 1)
    return f"{FORGEHX_IMAGE_BASE}{stem}-{asset_hash}.{extension}"


def resolve_game_icon(
    icon_key: str,
    accessible_name: str,
    *,
    entity_asset_id: Optional[str] = None,
    asset_map: Optional[Mapping[str, str]] = None,
) -> ResolvedIcon:
    """Resolve a raw game key to a trusted CDN URL or local data URI."""
    assets = load_forgehx_asset_map() if asset_map is None else asset_map
    for candidate in icon_candidates(icon_key, entity_asset_id):
        asset_hash = assets.get(candidate)
        if asset_hash:
            return ResolvedIcon(icon_key, _hashed_url(candidate, asset_hash), accessible_name)

    local_icon = LOCAL_ICON_FALLBACKS.get(icon_key)
    if local_icon:
        encoded = get_icon_base64(local_icon)
        if encoded:
            return ResolvedIcon(
                icon_key, f"data:image/png;base64,{encoded}", accessible_name
            )
    return ResolvedIcon(icon_key, None, accessible_name)


def resolve_icon(icon_name: Optional[str]) -> Optional[str]:
    key = (icon_name or "").removesuffix(".png")
    if not key:
        return None

    resolved = resolve_game_icon(key, key, asset_map={}).url
    if resolved or key.startswith("att_def_boost_"):
        return resolved

    encoded = get_icon_base64(key)
    return f"data:image/png;base64,{encoded}" if encoded else None


def resolve_boost_icon(boost_type: str, feature: str = "all") -> Optional[str]:
    key = boost_icon_key(boost_type, feature)
    context = resolve_game_icon(key, key, asset_map={}).url
    return context or resolve_game_icon(boost_type, boost_type, asset_map={}).url

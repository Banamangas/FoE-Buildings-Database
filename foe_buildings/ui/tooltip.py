from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from foe_buildings import i18n as translations
from foe_buildings.ui.tooltip_icons import get_boost_icon_filename, resolve_icon


_BOOST_LABEL_KEYS = {
    "att_def_boost_attacker": "att_def_boost_attacker",
    "att_def_boost_defender": "att_def_boost_defender",
    "att_def_boost_attacker_defender": "att_def_boost_attacker_defender",
}

_COMBO_DEFINITIONS = [
    ("att_def_boost_attacker", ["att_boost_attacker", "def_boost_attacker"]),
    ("att_def_boost_defender", ["att_boost_defender", "def_boost_defender"]),
    (
        "att_def_boost_attacker_defender",
        ["att_boost_attacker", "def_boost_attacker", "att_boost_defender", "def_boost_defender"],
    ),
]

_FEATURES = ["all", "battleground", "guild_expedition", "guild_raids"]


def format_time(seconds: int) -> str:
    """Format seconds as 'Xd Xh Xm Xs', omitting zero components."""
    if seconds <= 0:
        return "0s"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs:
        parts.append(f"{secs}s")
    return " ".join(parts)


def format_range(min_value, max_value) -> str:
    """Format a min/max range, collapsing when equal."""
    if min_value == max_value:
        return str(min_value)
    return f"{min_value} - {max_value}"


def percent_suffix(boost_type: str) -> str:
    """Return '%' for normal boosts, empty string for non-percentage boosts."""
    non_percent = {
        "diplomacy",
        "guild_raids_action_points_collection",
        "guild_raids_goods_start",
        "guild_raids_units_start",
        "guild_raids_supplies_start",
        "guild_raids_coins_start",
        "guild_raids_action_points_capacity",
    }
    return "" if boost_type in non_percent else "%"


@dataclass
class TooltipRow:
    icon: Optional[str]
    label: str
    value: str
    suffix: Optional[str] = None


def _render_size_time_road(entity: Dict[str, Any], lang_code: str) -> List[TooltipRow]:
    """Render size, construction time, and road requirement rows."""
    rows = []
    components = entity.get("components", {})
    all_age = components.get("AllAge", {})
    size = all_age.get("placement", {}).get("size", {})
    width = size.get("x")
    height = size.get("y")
    if width is not None and height is not None:
        rows.append(
            TooltipRow(
                icon=None,
                label=translations.get_text("size", lang_code),
                value=f"{height}x{width}",
            )
        )

    construction_time = all_age.get("constructionTime", {}).get("time")
    if construction_time:
        rows.append(
            TooltipRow(
                icon=None,
                label=translations.get_text("construction_time", lang_code),
                value=format_time(construction_time),
            )
        )

    road_level = all_age.get("streetConnectionRequirement", {}).get("requiredLevel", 0)
    if road_level == 2:
        road_label = translations.get_text("road_required_2", lang_code)
    elif road_level == 1:
        road_label = translations.get_text("road_required", lang_code)
    else:
        road_label = translations.get_text("no_road_required", lang_code)
    rows.append(
        TooltipRow(
            icon=None,
            label=translations.get_text("road", lang_code),
            value=road_label,
        )
    )

    return rows


def _collect_boosts(components: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Collect individual boosts keyed by 'feature-type' or just 'type'."""
    boosts = {}
    for boost in components.get("AllAge", {}).get("boosts", {}).get("boosts", []):
        btype = boost.get("type")
        feature = boost.get("targetedFeature", "all")
        key = f"{feature}-{btype}" if feature != "all" else btype
        boosts[key] = boost
    return boosts


def _make_combined_rows(boosts: Dict[str, Dict[str, Any]], lang_code: str) -> List[TooltipRow]:
    """Create combined army-boost rows for all contexts."""
    rows = []
    for feature in _FEATURES:
        for combined_key, parts in _COMBO_DEFINITIONS:
            total = 0
            has_any = False
            for part in parts:
                key = f"{feature}-{part}" if feature != "all" else part
                boost = boosts.get(key)
                if boost:
                    total += boost.get("value", 0)
                    has_any = True
            if not has_any:
                continue
            icon_name = get_boost_icon_filename(combined_key, feature)
            label_key = _BOOST_LABEL_KEYS.get(combined_key, combined_key)
            rows.append(
                TooltipRow(
                    icon=resolve_icon(icon_name),
                    label=translations.get_text(label_key, lang_code),
                    value=f"{total}{percent_suffix(combined_key)}",
                )
            )
    return rows


def _render_provides(entity: Dict[str, Any], lang_code: str) -> List[TooltipRow]:
    """Render the 'Provides' section."""
    rows = []
    components = entity.get("components", {})
    all_age = components.get("AllAge", {})

    static_resources = all_age.get("staticResources", {}).get("resources", {}).get("resources", {})
    for resource, amount in static_resources.items():
        if amount:
            rows.append(
                TooltipRow(
                    icon=resolve_icon(f"{resource}.png"),
                    label=translations.translate_column(resource, lang_code),
                    value=str(amount),
                )
            )

    happiness = all_age.get("happiness", {}).get("provided")
    if happiness:
        rows.append(
            TooltipRow(
                icon=resolve_icon("happiness.png"),
                label=translations.get_text("happiness", lang_code),
                value=str(happiness),
            )
        )

    boosts = _collect_boosts(components)
    rows.extend(_make_combined_rows(boosts, lang_code))
    return rows

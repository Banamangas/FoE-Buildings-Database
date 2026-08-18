from copy import deepcopy
from dataclasses import dataclass, field
import html
import re
from types import MappingProxyType
from typing import Any, Callable, Dict, List, Mapping, Optional

import streamlit as st

from foe_buildings import i18n as translations
from foe_buildings.ui import tooltip_icons
from foe_buildings.ui.styles import load_tooltip_css
from foe_buildings.ui.tooltip_icons import (
    ResolvedIcon,
    boost_icon_key,
    resolve_game_icon,
)


_BOOST_LABEL_KEYS = {
    "att_def_boost_attacker": "att_def_boost_attacker",
    "att_def_boost_defender": "att_def_boost_defender",
    "att_def_boost_attacker_defender": "att_def_boost_attacker_defender",
}

_NON_ARMY_BOOST_LABEL_KEYS = {
    "coin_production": "Coin %",
    "supply_production": "Supplies %",
    "forge_points_production": "FP boost",
    "goods_production": "Goods Boost",
    "guild_goods_production": "Guild Goods Production %",
    "special_goods_production": "Special Goods Production %",
    "medals_boost": "Medal Boost",
}

_BOOST_TEXT_KEYS = {
    "guild_raids_action_points_collection": "qi_action_points_collection",
    "guild_raids_action_points_capacity": "qi_action_points_capacity",
}

_ARMY_BOOST_LABEL_COLUMNS = {
    "att_boost_attacker": "Red Attack",
    "def_boost_attacker": "Red Defense",
    "att_boost_defender": "Blue Attack",
    "def_boost_defender": "Blue Defense",
}

_ARMY_BOOST_PARTNERS = {
    "att_boost_attacker": "def_boost_attacker",
    "def_boost_attacker": "att_boost_attacker",
    "att_boost_defender": "def_boost_defender",
    "def_boost_defender": "att_boost_defender",
}

_COMBO_DEFINITIONS = [
    ("att_def_boost_attacker", ["att_boost_attacker", "def_boost_attacker"]),
    ("att_def_boost_defender", ["att_boost_defender", "def_boost_defender"]),
]

_ALL_ARMY_COMBO = (
    "att_def_boost_attacker_defender",
    [
        "att_boost_attacker",
        "def_boost_attacker",
        "att_boost_defender",
        "def_boost_defender",
    ],
)

_FEATURES = ["all", "battleground", "guild_expedition", "guild_raids"]

_FEATURE_TEXT_KEYS = {
    "battleground": "tooltip_context_battleground",
    "guild_expedition": "tooltip_context_guild_expedition",
    "guild_raids": "tooltip_context_guild_raids",
}

_COMBINED_ARMY_TYPES = {
    definition[0] for definition in _COMBO_DEFINITIONS
} | {_ALL_ARMY_COMBO[0]}

_RESOURCE_LABEL_ALIASES = {
    "money": "coins",
    "strategy_points": "forge_points",
    "all_goods_of_age": "goods",
    "era_goods": "goods",
    "treasury_goods": "guild_goods",
}

_RESOURCE_ICON_KEYS = {
    "era_goods": "all_goods_of_age",
    "guild_goods": "treasury_goods",
}

_PLAYER_RESOURCE_ICON_KEYS = {
    "era_goods": "all_goods_of_age",
    "random_good_of_next_age": "next_age_random_goods",
    "random_good_of_previous_age": "random_goods_of_previous_age",
    "random_good_of_age": "random_goods_chest",
    "random_good_of_age_1": "random_goods_chest",
    "random_good_of_age_2": "random_goods_chest",
    "random_good_of_age_3": "random_goods_chest",
    "each_special_goods_up_to_age": "special_goods",
}

_TREASURY_RESOURCE_ICON_KEYS = {
    "era_goods": "treasury_goods",
    "all_goods_of_age": "treasury_goods",
    "random_good_of_age": "treasury_goods",
    "all_goods_of_next_age": "treasury_goods_of_next_age",
    "all_goods_of_previous_age": "treasury_goods_of_previous_age",
}

_RESOURCE_TEXT_KEYS = {
    "coins": "tooltip_resource_coins",
    "forge_points": "tooltip_resource_forge_points",
    "goods": "tooltip_resource_goods",
    "population": "tooltip_resource_population",
}

_ALLY_ROOM_TEXT_KEYS = {
    "diplomat": "ally_type_diplomat",
    "merchant": "ally_type_merchant",
    "military": "ally_type_military",
}


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
    icon: Optional[ResolvedIcon]
    label: str
    value: str
    suffix: Optional[str] = None
    show_label: bool = False
    duration: Optional[int] = None
    markers: List[ResolvedIcon] = field(default_factory=list)


@dataclass
class RandomOutcome:
    row: TooltipRow
    probability: int


@dataclass
class RandomProductionGroup:
    outcomes: List[RandomOutcome]
    duration: Optional[int] = None
    markers: List[ResolvedIcon] = field(default_factory=list)


@dataclass
class ProductionResult:
    rows: List[TooltipRow] = field(default_factory=list)
    random_groups: List[RandomProductionGroup] = field(default_factory=list)
    shared_duration: Optional[int] = None


@dataclass
class TooltipSection:
    title: Optional[str]
    rows: List[TooltipRow]
    header: Optional[str] = None
    image_url: Optional[str] = None
    key: Optional[str] = None
    random_groups: List[RandomProductionGroup] = field(default_factory=list)
    shared_duration: Optional[int] = None


def _resolve_entity_for_era(
    entity: Dict[str, Any], era_key: Optional[str]
) -> Dict[str, Any]:
    """Return an entity view with selected-era components overlaid on AllAge.

    Raw entity objects are cached and shared by Streamlit, so this helper always
    builds a deep copy instead of mutating the API payload.
    """
    resolved = deepcopy(entity)
    components = entity.get("components", {})
    all_age = deepcopy(components.get("AllAge", {}))
    era_components = components.get(era_key, {}) if era_key else {}

    if isinstance(era_components, dict):
        selected_lookup = era_components.get("lookup")
        all_age_lookup = all_age.get("lookup")
        shared_boost_component = deepcopy(all_age.get("boosts", {}))
        selected_boost_component = deepcopy(era_components.get("boosts", {}))
        shared_boosts = shared_boost_component.get("boosts", [])
        selected_boosts = selected_boost_component.get("boosts", [])
        shared_resource_component = deepcopy(all_age.get("staticResources", {}))
        selected_resource_component = deepcopy(
            era_components.get("staticResources", {})
        )
        shared_resources = deepcopy(
            shared_resource_component.get("resources", {}).get("resources", {})
        )
        selected_resources = deepcopy(
            selected_resource_component.get("resources", {}).get("resources", {})
        )
        all_age.update(deepcopy(era_components))

        if shared_boost_component and selected_boost_component:
            merged_boost_component = {
                **shared_boost_component,
                **selected_boost_component,
            }
            selected_keys = {
                (b.get("type"), b.get("targetedFeature") or "all")
                for b in selected_boosts
            }
            merged_boosts = [
                b
                for b in shared_boosts
                if (b.get("type"), b.get("targetedFeature") or "all")
                not in selected_keys
            ] + list(selected_boosts)
            merged_boost_component["boosts"] = merged_boosts
            all_age["boosts"] = merged_boost_component

        if shared_resource_component and isinstance(
            era_components.get("staticResources"), dict
        ):
            merged_resources = deepcopy(shared_resources)
            for resource, selected_value in selected_resources.items():
                shared_value = shared_resources.get(resource)
                both_numeric = (
                    isinstance(shared_value, (int, float))
                    and not isinstance(shared_value, bool)
                    and isinstance(selected_value, (int, float))
                    and not isinstance(selected_value, bool)
                )
                merged_resources[resource] = (
                    shared_value + selected_value
                    if both_numeric
                    else deepcopy(selected_value)
                )
            merged_resource_component = {
                **shared_resource_component,
                **selected_resource_component,
            }
            nested_resources = {
                **shared_resource_component.get("resources", {}),
                **selected_resource_component.get("resources", {}),
                "resources": merged_resources,
            }
            merged_resource_component["resources"] = nested_resources
            all_age["staticResources"] = merged_resource_component

        if isinstance(all_age_lookup, dict) and isinstance(selected_lookup, dict):
            merged_lookup = deepcopy(all_age_lookup)
            merged_lookup.update(deepcopy(selected_lookup))
            all_rewards = all_age_lookup.get("rewards", {})
            selected_rewards = selected_lookup.get("rewards", {})
            if isinstance(all_rewards, dict) and isinstance(selected_rewards, dict):
                merged_lookup["rewards"] = {
                    **deepcopy(all_rewards),
                    **deepcopy(selected_rewards),
                }
            all_age["lookup"] = merged_lookup

    resolved["components"] = {"AllAge": all_age}
    return resolved


def _humanize_identifier(identifier: str) -> str:
    return identifier.replace("_", " ").strip().title()


def _with_feature_context(label: str, feature: str, lang_code: str) -> str:
    text_key = _FEATURE_TEXT_KEYS.get(feature)
    if feature == "all":
        return label
    context = (
        translations.get_text(text_key, lang_code)
        if text_key
        else _humanize_identifier(feature)
    )
    return f"{label} ({context})"


def _resource_display(resource: str, lang_code: str) -> tuple[str, str]:
    label_key = _RESOURCE_LABEL_ALIASES.get(resource, resource)
    text_key = _RESOURCE_TEXT_KEYS.get(label_key)
    label = (
        translations.get_text(text_key, lang_code)
        if text_key
        else translations.translate_column(label_key, lang_code)
    )
    return label, _RESOURCE_ICON_KEYS.get(resource, resource)


IconResolver = Callable[[str, str, Optional[str]], ResolvedIcon]


def _make_icon_resolver(asset_map: Mapping[str, str]) -> IconResolver:
    """Bind one read-only ForgeHX map to all icon lookups in an assembly."""
    read_only_assets = MappingProxyType(asset_map)

    def resolve(key: str, label: str, entity_asset_id: Optional[str]) -> ResolvedIcon:
        return resolve_game_icon(
            key,
            label,
            entity_asset_id=entity_asset_id,
            asset_map=read_only_assets,
        )

    return resolve


def _icon(
    key: str,
    label: str,
    entity_asset_id: Optional[str] = None,
    icon_resolver: Optional[IconResolver] = None,
) -> ResolvedIcon:
    if icon_resolver is not None:
        return icon_resolver(key, label, entity_asset_id)
    return resolve_game_icon(key, label, entity_asset_id=entity_asset_id)


def _escaped(value: object) -> str:
    return html.escape(str(value), quote=True)


def _tooltip_icon_html(icon: Optional[ResolvedIcon], css_class: str) -> str:
    if icon is None or icon.url is None:
        return '<span class="tooltip-icon-missing" aria-hidden="true">?</span>'
    accessible_name = _escaped(icon.accessible_name)
    return (
        f'<img src="{_escaped(icon.url)}" class="{css_class}" '
        f'alt="{accessible_name}" title="{accessible_name}">'
    )


def _tooltip_row_html(row: TooltipRow, lang_code: str) -> str:
    """Return escaped HTML for one quantitative or semantic tooltip row."""
    del lang_code
    accessible_text = _escaped(f"{row.label}: {row.value}")
    parts = [
        _tooltip_icon_html(row.icon, "foe-tooltip-icon"),
        f'<span class="foe-tooltip-value">{_escaped(row.value)}</span>',
    ]
    if row.suffix:
        parts.append(f'<em class="foe-tooltip-suffix">{_escaped(row.suffix)}</em>')
    if row.duration:
        parts.append(
            '<span class="foe-tooltip-duration">'
            f"{_escaped(format_time(row.duration))}</span>"
        )
    parts.extend(
        _tooltip_icon_html(marker, "foe-tooltip-marker") for marker in row.markers
    )
    return (
        f'<div class="foe-tooltip-row" role="group" aria-label="{accessible_text}" '
        f'title="{accessible_text}">{"".join(parts)}</div>'
    )


def _random_group_html(group: RandomProductionGroup, lang_code: str) -> str:
    """Return escaped HTML for one independent random-production pool."""
    accessible_text = _escaped(translations.get_text("random_production", lang_code))
    header = (
        f'<div class="tooltip-random-header">{accessible_text}</div>'
    )
    outcomes = []
    for outcome in group.outcomes:
        probability = _escaped(f"{outcome.probability}%")
        outcomes.append(
            '<div class="tooltip-random-outcome">'
            '<div class="tooltip-random-outcome-value">'
            f"{_tooltip_row_html(outcome.row, lang_code)}</div>"
            f'<span class="tooltip-random-probability">{probability}</span>'
            "</div>"
        )

    metadata = []
    if group.duration:
        metadata.append(
            '<span class="foe-tooltip-duration">'
            f"{_escaped(format_time(group.duration))}</span>"
        )
    metadata.extend(
        _tooltip_icon_html(marker, "foe-tooltip-marker") for marker in group.markers
    )
    metadata_html = (
        f'<div class="tooltip-random-metadata">{"".join(metadata)}</div>'
        if metadata
        else ""
    )
    return (
        '<div class="tooltip-random-group" role="group" '
        f'aria-label="{accessible_text}" '
        f'title="{accessible_text}">{header}{"".join(outcomes)}{metadata_html}</div>'
    )


def _render_section_bodies(
    sections: List[TooltipSection], lang_code: str, first_class: str = ""
) -> None:
    """Render the title, rows, and random groups for a list of sections."""
    for index, section in enumerate(sections):
        if not (section.title or section.rows or section.random_groups):
            continue

        parts: List[str] = []
        if section.title:
            title = section.title
            if section.shared_duration:
                title = f"{title} ({format_time(section.shared_duration)})"
            parts.append(
                f'<div class="foe-tooltip-section-title">{_escaped(title)}</div>'
            )
        for row in section.rows:
            parts.append(_tooltip_row_html(row, lang_code))
        for group in section.random_groups:
            parts.append(_random_group_html(group, lang_code))

        margin_class = first_class if index == 0 else ""
        st.markdown(
            f'<div class="foe-tooltip-section{margin_class}">'
            f'{"".join(parts)}</div>',
            unsafe_allow_html=True,
        )


def render_tooltip_sections(sections: List[TooltipSection], lang_code: str) -> None:
    """Render tooltip sections with optional titles, icons, and suffixes.

    When a header section carries a building image, the image is placed in a
    right-hand column while the tooltip details flow in the left column.
    """
    st.markdown(load_tooltip_css(), unsafe_allow_html=True)

    header_section = (
        sections[0]
        if sections and (sections[0].header or sections[0].image_url)
        else None
    )
    content_sections = sections[1:] if header_section else sections

    if header_section and header_section.header:
        st.markdown(f"### {_escaped(header_section.header)}")

    if header_section and header_section.image_url and content_sections:
        info_col, image_col = st.columns([2, 1], gap="small")
        with info_col:
            _render_section_bodies(
                content_sections, lang_code, first_class=" foe-tooltip-section-first"
            )
        with image_col:
            st.image(header_section.image_url, width="content")
    else:
        if header_section and header_section.image_url:
            st.image(header_section.image_url, width="content")
        _render_section_bodies(
            content_sections,
            lang_code,
            first_class=" foe-tooltip-section-first",
        )


def _render_size_time_road(
    entity: Dict[str, Any],
    lang_code: str,
    icon_resolver: Optional[IconResolver] = None,
) -> List[TooltipRow]:
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
                icon=_icon(
                    "size",
                    translations.get_text("size", lang_code),
                    icon_resolver=icon_resolver,
                ),
                label=translations.get_text("size", lang_code),
                value=f"{height}x{width}",
            )
        )

    construction_time = all_age.get("constructionTime", {}).get("time")
    if construction_time:
        rows.append(
            TooltipRow(
                icon=_icon(
                    "icon_time",
                    translations.get_text("construction_time", lang_code),
                    icon_resolver=icon_resolver,
                ),
                label=translations.get_text("construction_time", lang_code),
                value=format_time(construction_time),
            )
        )

    road_level = all_age.get("streetConnectionRequirement", {}).get("requiredLevel", 0)
    if road_level == 2:
        road_label = translations.get_text("road_required_2", lang_code)
        road_icon_key = "street_required"
    elif road_level == 1:
        road_label = translations.get_text("road_required", lang_code)
        road_icon_key = "road_required"
    else:
        road_label = translations.get_text("no_road_required", lang_code)
        road_icon_key = "/shared/gui/buffbar/buffbar_icon_buff_unconnected.png"
    rows.append(
        TooltipRow(
            icon=_icon(
                road_icon_key,
                translations.get_text("road", lang_code),
                icon_resolver=icon_resolver,
            ),
            label=translations.get_text("road", lang_code),
            value=road_label,
            show_label=True,
        )
    )

    return rows


def _collect_boosts(components: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Collect boosts in API order without collapsing repeated type/context rows."""
    raw_boosts = components.get("AllAge", {}).get("boosts", {}).get("boosts", [])
    return [
        boost for boost in raw_boosts if isinstance(boost, dict) and boost.get("type")
    ]


def _feature_order(boosts: List[Dict[str, Any]]) -> List[str]:
    present = [boost.get("targetedFeature") or "all" for boost in boosts]
    return [*_FEATURES, *sorted(set(present) - set(_FEATURES))]


def _combined_army_row(
    combined_key: str,
    feature: str,
    value: int,
    lang_code: str,
    icon_resolver: Optional[IconResolver] = None,
) -> TooltipRow:
    """Build one combined army-boost row."""
    label_key = _BOOST_LABEL_KEYS.get(combined_key, combined_key)
    label = _with_feature_context(
        translations.get_text(label_key, lang_code), feature, lang_code
    )
    return TooltipRow(
        icon=_icon(
            boost_icon_key(combined_key, feature),
            label,
            icon_resolver=icon_resolver,
        ),
        label=label,
        value=f"{value}{percent_suffix(combined_key)}",
    )


def _single_army_row(
    boost_type: str,
    feature: str,
    value: int,
    lang_code: str,
    icon_resolver: Optional[IconResolver] = None,
) -> TooltipRow:
    """Build one individual army-boost row."""
    label = _with_feature_context(
        _boost_label(boost_type, lang_code), feature, lang_code
    )
    return TooltipRow(
        icon=_icon(
            boost_icon_key(boost_type, feature),
            label,
            icon_resolver=icon_resolver,
        ),
        label=label,
        value=f"{value}{percent_suffix(boost_type)}",
    )


def _make_combined_rows(
    boosts: List[Dict[str, Any]],
    lang_code: str,
    icon_resolver: Optional[IconResolver] = None,
) -> List[TooltipRow]:
    """Create direct or legacy-combined army boost rows for every context."""
    rows = []
    for feature in _feature_order(boosts):
        feature_boosts = [
            boost
            for boost in boosts
            if (boost.get("targetedFeature") or "all") == feature
        ]

        # Direct combined boosts take precedence over part-based inference.
        direct_rows: List[TooltipRow] = []
        for combined_key, _ in [_ALL_ARMY_COMBO, *_COMBO_DEFINITIONS]:
            for boost in feature_boosts:
                if boost.get("type") == combined_key:
                    direct_rows.append(
                        _combined_army_row(
                            combined_key,
                            feature,
                            boost.get("value", 0),
                            lang_code,
                            icon_resolver,
                        )
                    )
        if direct_rows:
            rows.extend(direct_rows)
            continue

        def _part_sum(part_type: str) -> int:
            return sum(
                b.get("value", 0) for b in feature_boosts if b.get("type") == part_type
            )

        def _has_part(part_type: str) -> bool:
            return any(b.get("type") == part_type for b in feature_boosts)

        sums = {
            "att_a": _part_sum("att_boost_attacker"),
            "def_a": _part_sum("def_boost_attacker"),
            "att_d": _part_sum("att_boost_defender"),
            "def_d": _part_sum("def_boost_defender"),
        }
        has = {
            "att_a": _has_part("att_boost_attacker"),
            "def_a": _has_part("def_boost_attacker"),
            "att_d": _has_part("att_boost_defender"),
            "def_d": _has_part("def_boost_defender"),
        }
        attacker_pair_complete = has["att_a"] and has["def_a"]
        defender_pair_complete = has["att_d"] and has["def_d"]
        all_four_complete = attacker_pair_complete and defender_pair_complete

        if (
            all_four_complete
            and sums["att_a"] == sums["def_a"] == sums["att_d"] == sums["def_d"]
        ):
            rows.append(
                _combined_army_row(
                    _ALL_ARMY_COMBO[0],
                    feature,
                    sums["att_a"],
                    lang_code,
                    icon_resolver,
                )
            )
            continue

        if attacker_pair_complete and sums["att_a"] == sums["def_a"]:
            rows.append(
                _combined_army_row(
                    "att_def_boost_attacker",
                    feature,
                    sums["att_a"],
                    lang_code,
                    icon_resolver,
                )
            )
        else:
            if has["att_a"]:
                rows.append(
                    _single_army_row(
                        "att_boost_attacker",
                        feature,
                        sums["att_a"],
                        lang_code,
                        icon_resolver,
                    )
                )
            if has["def_a"]:
                rows.append(
                    _single_army_row(
                        "def_boost_attacker",
                        feature,
                        sums["def_a"],
                        lang_code,
                        icon_resolver,
                    )
                )

        if defender_pair_complete and sums["att_d"] == sums["def_d"]:
            rows.append(
                _combined_army_row(
                    "att_def_boost_defender",
                    feature,
                    sums["att_d"],
                    lang_code,
                    icon_resolver,
                )
            )
        else:
            if has["att_d"]:
                rows.append(
                    _single_army_row(
                        "att_boost_defender",
                        feature,
                        sums["att_d"],
                        lang_code,
                        icon_resolver,
                    )
                )
            if has["def_d"]:
                rows.append(
                    _single_army_row(
                        "def_boost_defender",
                        feature,
                        sums["def_d"],
                        lang_code,
                        icon_resolver,
                    )
                )
    return rows


def _boost_label(boost_type: str, lang_code: str) -> str:
    army_column = _ARMY_BOOST_LABEL_COLUMNS.get(boost_type)
    if army_column:
        return translations.translate_column(army_column, lang_code)
    column_key = _NON_ARMY_BOOST_LABEL_KEYS.get(boost_type)
    if column_key:
        return translations.translate_column(column_key, lang_code)
    text_key = _BOOST_TEXT_KEYS.get(boost_type)
    if text_key:
        return translations.get_text(text_key, lang_code)
    return _humanize_identifier(boost_type)


def _make_non_army_rows(
    boosts: List[Dict[str, Any]],
    lang_code: str,
    icon_resolver: Optional[IconResolver] = None,
) -> List[TooltipRow]:
    """Render every non-combined boost, including future unknown API types."""
    rows = []
    for boost in boosts:
        boost_type = boost.get("type", "")
        if boost_type in _COMBINED_ARMY_TYPES or boost_type in _ARMY_BOOST_PARTNERS:
            continue
        feature = boost.get("targetedFeature") or "all"
        label = _with_feature_context(
            _boost_label(boost_type, lang_code), feature, lang_code
        )
        rows.append(
            TooltipRow(
                icon=_icon(
                    boost_icon_key(boost_type, feature),
                    label,
                    icon_resolver=icon_resolver,
                ),
                label=label,
                value=f"{boost.get('value', 0)}{percent_suffix(boost_type)}",
            )
        )
    return rows


def _render_provides(
    entity: Dict[str, Any],
    lang_code: str,
    icon_resolver: Optional[IconResolver] = None,
) -> List[TooltipRow]:
    """Render the 'Provides' section."""
    rows = []
    components = entity.get("components", {})
    all_age = components.get("AllAge", {})

    static_resources = (
        all_age.get("staticResources", {}).get("resources", {}).get("resources", {})
    )
    for resource, amount in static_resources.items():
        if amount:
            label, icon_key = _resource_display(resource, lang_code)
            rows.append(
                TooltipRow(
                    icon=_icon(icon_key, label, icon_resolver=icon_resolver),
                    label=label,
                    value=str(amount),
                )
            )

    population = all_age.get("population", {}).get("provided")
    if population:
        rows.append(
            TooltipRow(
                icon=_icon(
                    "population",
                    translations.translate_column("Population", lang_code),
                    icon_resolver=icon_resolver,
                ),
                label=translations.translate_column("Population", lang_code),
                value=str(population),
            )
        )

    happiness = all_age.get("happiness", {}).get("provided")
    if happiness:
        rows.append(
            TooltipRow(
                icon=_icon(
                    "happiness",
                    translations.get_text("happiness", lang_code),
                    icon_resolver=icon_resolver,
                ),
                label=translations.get_text("happiness", lang_code),
                value=str(happiness),
            )
        )

    ranking_points = all_age.get("rankingPoints", {}).get("provided") or all_age.get(
        "ranking_points", {}
    ).get("provided")
    if ranking_points:
        rows.append(
            TooltipRow(
                icon=_icon(
                    "rank",
                    translations.get_text("ranking_points", lang_code),
                    icon_resolver=icon_resolver,
                ),
                label=translations.get_text("ranking_points", lang_code),
                value=str(ranking_points),
            )
        )

    boosts = _collect_boosts(components)
    rows.extend(_make_combined_rows(boosts, lang_code, icon_resolver))
    rows.extend(_make_non_army_rows(boosts, lang_code, icon_resolver))
    return rows


def _render_resources(
    resources: Dict[str, Any],
    lang_code: str,
    resource_context: str,
    icon_resolver: Optional[IconResolver] = None,
) -> List[TooltipRow]:
    rows = []
    context_icon_keys = (
        _TREASURY_RESOURCE_ICON_KEYS
        if resource_context == "guildResources"
        else _PLAYER_RESOURCE_ICON_KEYS
    )
    for resource, amount in (resources or {}).items():
        if amount:
            label, default_icon_key = _resource_display(resource, lang_code)
            icon_key = context_icon_keys.get(resource, default_icon_key)
            rows.append(
                TooltipRow(
                    icon=_icon(icon_key, label, icon_resolver=icon_resolver),
                    label=label,
                    value=str(amount),
                )
            )
    return rows


def _render_chain_set(
    entity: Dict[str, Any],
    lang_code: str,
    icon_resolver: Optional[IconResolver] = None,
) -> List[TooltipRow]:
    rows = []
    chain = entity.get("components", {}).get("AllAge", {}).get("chain")
    if chain:
        chain_id = chain.get("chainId")
        if chain_id:
            rows.append(
                TooltipRow(
                    icon=_icon(
                        chain_id,
                        translations.get_text("chain", lang_code),
                        icon_resolver=icon_resolver,
                    ),
                    label=translations.get_text("chain", lang_code),
                    value=chain_id,
                    show_label=True,
                )
            )

    for ability in entity.get("abilities", []):
        ability_class = ability.get("__class__")
        if ability_class in ("ChainStartAbility", "ChainLinkAbility"):
            chain_id = ability.get("chainId")
            if chain_id:
                rows.append(
                    TooltipRow(
                        icon=_icon(
                            chain_id,
                            translations.get_text("chain", lang_code),
                            icon_resolver=icon_resolver,
                        ),
                        label=translations.get_text("chain", lang_code),
                        value=chain_id,
                        show_label=True,
                    )
                )
        elif ability_class == "BuildingSetAbility":
            set_id = ability.get("setId")
            if set_id:
                rows.append(
                    TooltipRow(
                        icon=_icon(
                            set_id,
                            translations.get_text("set", lang_code),
                            icon_resolver=icon_resolver,
                        ),
                        label=translations.get_text("set", lang_code),
                        value=set_id,
                        show_label=True,
                    )
                )
    return rows


def _render_ally_rooms(
    entity: Dict[str, Any],
    lang_code: str,
    icon_resolver: Optional[IconResolver] = None,
) -> List[TooltipRow]:
    rows = []
    rooms = (
        entity.get("components", {}).get("AllAge", {}).get("ally", {}).get("rooms", [])
    )
    for room in rooms:
        ally_type = room.get("allyType", "")
        text_key = _ALLY_ROOM_TEXT_KEYS.get(ally_type)
        value = (
            translations.get_text(text_key, lang_code)
            if text_key
            else _humanize_identifier(ally_type)
        )
        rows.append(
            TooltipRow(
                icon=_icon(
                    "historical_allies_slot_tooltip_icon_empty",
                    translations.get_text("ally_room", lang_code),
                    icon_resolver=icon_resolver,
                ),
                label=translations.get_text("ally_room", lang_code),
                value=value,
                show_label=True,
            )
        )
    return rows


_ABILITY_TRAITS = {
    "PolishableAbility": "can_be_polished",
    "MotivatableAbility": "can_be_motivated",
    "NotPlunderableAbility": "cannot_be_plundered",
    "AffectedByLifeSupportAbility": "requires_life_support",
}

TRAIT_ICON_KEYS = {
    "unique_building": "icon_unique_building",
    "upgrades_automatically": "icon_age",
    "fsp_disabled": "icon_fsp_disabled",
    "can_be_motivated": "when_motivated",
    "can_be_polished": "when_motivated",
    "cannot_be_plundered": "eventwindow_plunder_repel",
    "requires_life_support": "life_support",
}


def _render_traits(
    entity: Dict[str, Any],
    lang_code: str,
    icon_resolver: Optional[IconResolver] = None,
) -> List[TooltipRow]:
    rows = []
    all_age = entity.get("components", {}).get("AllAge", {})

    def add_trait(text_key: str) -> None:
        value = translations.get_text(text_key, lang_code)
        if not any(row.value == value for row in rows):
            rows.append(
                TooltipRow(
                    icon=_icon(
                        TRAIT_ICON_KEYS[text_key],
                        value,
                        icon_resolver=icon_resolver,
                    ),
                    label=translations.get_text("trait", lang_code),
                    value=value,
                    show_label=True,
                )
            )

    if all_age.get("cityLimit"):
        add_trait("unique_building")

    flags = all_age.get("flags", {}).get("flags", 0)
    if flags & 4:
        add_trait("upgrades_automatically")
    if flags & 32:
        add_trait("fsp_disabled")

    social_interaction = all_age.get("socialInteraction")
    if isinstance(social_interaction, dict):
        interaction_type = social_interaction.get(
            "interactionType"
        ) or social_interaction.get("type")
    else:
        interaction_type = social_interaction
    social_traits = {
        "motivate": "can_be_motivated",
        "polish": "can_be_polished",
    }
    if interaction_type in social_traits:
        add_trait(social_traits[interaction_type])

    for ability in entity.get("abilities", []):
        ability_class = ability.get("__class__")
        trait_key = _ABILITY_TRAITS.get(ability_class)
        if trait_key:
            add_trait(trait_key)
    return rows


def _render_costs(
    entity: Dict[str, Any],
    lang_code: str,
    icon_resolver: Optional[IconResolver] = None,
) -> List[TooltipRow]:
    rows = []
    resources = (
        entity.get("components", {})
        .get("AllAge", {})
        .get("buildResourcesRequirement", {})
        .get("cost", {})
        .get("resources", {})
    )
    for resource, amount in resources.items():
        if amount:
            label, icon_key = _resource_display(resource, lang_code)
            rows.append(
                TooltipRow(
                    icon=_icon(icon_key, label, icon_resolver=icon_resolver),
                    label=label,
                    value=str(amount),
                )
            )
    return rows


def _generic_reward_display(
    reward: Dict[str, Any],
    reward_ref: Dict[str, Any],
    reward_id: Optional[str],
    lang_code: str,
    icon_resolver: Optional[IconResolver] = None,
) -> TooltipRow:
    """Normalize an API generic reward into one stable tooltip row."""
    reward_name = str(reward.get("name") or reward_id or "")
    name_match = re.match(r"^([+\-]?\d+)x?\s+(.*)$", reward_name)
    parsed_amount = int(name_match.group(1)) if name_match else None
    parsed_name = name_match.group(2) if name_match else reward_name
    amount = next(
        (
            candidate
            for candidate in (
                reward.get("totalAmount"),
                reward.get("amount"),
                parsed_amount,
                reward_ref.get("amount"),
            )
            if candidate is not None
        ),
        1,
    )

    if reward.get("type") == "resource" and reward.get("subType"):
        subtype = reward["subType"]
        label, _ = _resource_display(subtype, lang_code)
        return TooltipRow(
            icon=_icon(subtype, label, icon_resolver=icon_resolver),
            label=label,
            value=str(amount),
        )

    if reward.get("type") == "unit" and reward.get("subType"):
        label = parsed_name or reward_id or ""
        return TooltipRow(
            icon=_unit_icon(str(reward["subType"]), label, icon_resolver=icon_resolver),
            label=label,
            value=str(amount),
        )

    icon_asset = reward.get("iconAssetName")
    markers = []
    label = parsed_name or reward_id or ""
    if icon_asset == "icon_fragment":
        label = re.sub(r"^Fragments? of\s+", "", label, flags=re.IGNORECASE)
        label = f"{label} {translations.get_text('fragments', lang_code)}".strip()
        assembled_reward = reward.get("assembledReward", {})
        icon_asset = assembled_reward.get("iconAssetName") or assembled_reward.get(
            "subType"
        )
        markers.append(
            _icon(
                "icon_tooltip_fragment",
                translations.get_text("fragments", lang_code),
                icon_resolver=icon_resolver,
            )
        )

    icon = _icon(icon_asset, label, icon_resolver=icon_resolver) if icon_asset else None
    return TooltipRow(
        icon=icon,
        label=label,
        value=str(amount),
        markers=markers,
    )


def _motivated_marker(
    lang_code: str, icon_resolver: Optional[IconResolver] = None
) -> ResolvedIcon:
    label = translations.get_text("when_motivated", lang_code)
    return _icon("when_motivated", label, icon_resolver=icon_resolver)


def _unit_icon(
    unit_type: str,
    label: str,
    icon_resolver: Optional[IconResolver] = None,
) -> ResolvedIcon:
    if unit_type == "rogue":
        icon_key = "rogue"
    elif "champion" in unit_type:
        icon_key = "chivalry"
    else:
        icon_key = unit_type

    icon = _icon(icon_key, label, icon_resolver=icon_resolver)
    if icon.url or icon_key != unit_type or icon_key == "military":
        return icon

    fallback = _icon("military", label, icon_resolver=icon_resolver)
    return ResolvedIcon(icon.key, fallback.url, icon.accessible_name)


def _render_product(
    product: Dict[str, Any],
    lookup: Dict[str, Any],
    lang_code: str,
    icon_resolver: Optional[IconResolver] = None,
) -> List[TooltipRow]:
    """Render one non-random product into zero or more ordinary rows."""
    rows = []
    ptype = product.get("type")

    if ptype == "resources":
        rows.extend(
            _render_resources(
                product.get("playerResources", {}).get("resources"),
                lang_code,
                "playerResources",
                icon_resolver,
            )
        )
    elif ptype == "guildResources":
        rows.extend(
            _render_resources(
                product.get("guildResources", {}).get("resources"),
                lang_code,
                "guildResources",
                icon_resolver,
            )
        )
    elif ptype == "genericReward":
        reward_ref = product.get("reward", {})
        reward_id = reward_ref.get("id") or product.get("rewardId")
        reward = lookup.get(reward_id, {}) if reward_id and lookup else {}
        fallback_reward = {"name": reward_id}
        rows.append(
            _generic_reward_display(
                reward or fallback_reward,
                reward_ref,
                reward_id,
                lang_code,
                icon_resolver,
            )
        )
    elif ptype == "unit":
        amount = product.get("amount", 0)
        if amount:
            unit_type = product.get("unitTypeId", "military")
            label = translations.translate_column(unit_type, lang_code)
            rows.append(
                TooltipRow(
                    icon=_unit_icon(unit_type, label, icon_resolver),
                    label=label,
                    value=str(amount),
                )
            )

    if product.get("onlyWhenMotivated"):
        marker = _motivated_marker(lang_code, icon_resolver)
        for row in rows:
            row.markers.append(marker)
    return rows


def _render_random_product(
    product: Dict[str, Any],
    lookup: Dict[str, Any],
    lang_code: str,
    icon_resolver: Optional[IconResolver] = None,
) -> RandomProductionGroup:
    """Preserve one raw random product as one independent outcome group."""
    outcomes = []
    for random_product in product.get("products", []):
        rows = _render_product(
            random_product.get("product", {}), lookup, lang_code, icon_resolver
        )
        drop_chance = random_product.get("dropChance", 0)
        probability = int(drop_chance * 100)
        outcomes.extend(RandomOutcome(row=row, probability=probability) for row in rows)

    markers = (
        [_motivated_marker(lang_code, icon_resolver)]
        if product.get("onlyWhenMotivated")
        else []
    )
    return RandomProductionGroup(outcomes=outcomes, markers=markers)


def _render_produces(
    entity: Dict[str, Any],
    lang_code: str,
    icon_resolver: Optional[IconResolver] = None,
) -> ProductionResult:
    """Extract production rows, random groups, and timing metadata."""
    components = entity.get("components", {})
    all_age = components.get("AllAge", {})
    lookup = all_age.get("lookup", {}).get("rewards", {})
    options = all_age.get("production", {}).get("options", [])
    durations = {option.get("time") for option in options if option.get("time")}
    shared_duration = next(iter(durations)) if len(durations) == 1 else None
    result = ProductionResult(shared_duration=shared_duration)

    for option in options:
        duration = None if shared_duration is not None else option.get("time")
        for product in option.get("products", []):
            if product.get("type") == "random":
                group = _render_random_product(
                    product, lookup, lang_code, icon_resolver
                )
                group.duration = duration
                result.random_groups.append(group)
                continue

            rows = _render_product(product, lookup, lang_code, icon_resolver)
            for row in rows:
                row.duration = duration
            result.rows.extend(rows)
    return result


def render_building_tooltip(
    entity: Dict[str, Any],
    lang_code: str,
    building_name: Optional[str] = None,
    image_url: Optional[str] = None,
    era_key: Optional[str] = None,
    asset_map: Optional[Mapping[str, str]] = None,
) -> List[TooltipSection]:
    """Render a full in-game-style tooltip from a raw building entity."""
    assets = tooltip_icons.load_forgehx_asset_map() if asset_map is None else asset_map
    icon_resolver = _make_icon_resolver(assets)
    resolved_entity = _resolve_entity_for_era(entity, era_key)
    sections = []

    header = building_name or entity.get("name")
    if header or image_url:
        sections.append(
            TooltipSection(
                title=None,
                rows=[],
                header=header,
                image_url=image_url,
                key="header",
            )
        )

    size_rows = _render_size_time_road(resolved_entity, lang_code, icon_resolver)
    if size_rows:
        sections.append(
            TooltipSection(
                title=translations.get_text("size_time_road", lang_code),
                rows=size_rows,
                key="size_time_road",
            )
        )

    provides = _render_provides(resolved_entity, lang_code, icon_resolver)
    if provides:
        sections.append(
            TooltipSection(
                title=translations.get_text("provides", lang_code),
                rows=provides,
                key="provides",
            )
        )

    production = _render_produces(resolved_entity, lang_code, icon_resolver)
    if production.rows or production.random_groups:
        sections.append(
            TooltipSection(
                title=translations.get_text("produces", lang_code),
                rows=production.rows,
                key="produces",
                random_groups=production.random_groups,
                shared_duration=production.shared_duration,
            )
        )

    chain_rows = _render_chain_set(resolved_entity, lang_code, icon_resolver)
    if chain_rows:
        sections.append(
            TooltipSection(
                title=translations.get_text("chain_set", lang_code),
                rows=chain_rows,
                key="chain_set",
            )
        )

    ally_rows = _render_ally_rooms(resolved_entity, lang_code, icon_resolver)
    if ally_rows:
        sections.append(
            TooltipSection(
                title=translations.get_text("ally_rooms", lang_code),
                rows=ally_rows,
                key="ally_rooms",
            )
        )

    costs = _render_costs(resolved_entity, lang_code, icon_resolver)
    if costs:
        sections.append(
            TooltipSection(
                title=translations.get_text("costs", lang_code),
                rows=costs,
                key="costs",
            )
        )

    traits = _render_traits(resolved_entity, lang_code, icon_resolver)
    if traits:
        sections.append(
            TooltipSection(
                title=translations.get_text("traits", lang_code),
                rows=traits,
                key="traits",
            )
        )

    return sections

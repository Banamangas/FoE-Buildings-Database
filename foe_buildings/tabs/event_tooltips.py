from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from foe_buildings import config
from foe_buildings import i18n as translations
from foe_buildings.config import SessionKeys
from foe_buildings.data import loader as data_loader
from foe_buildings.ui import tooltip as tooltip_renderer
from foe_buildings.ui import tooltip_icons
from foe_buildings.ui.styles import load_tooltip_css
from foe_buildings.ui.tooltip import (
    RandomOutcome,
    RandomProductionGroup,
    TooltipRow,
    TooltipSection,
)
from foe_buildings.ui.tooltip_icons import resolve_game_icon
from foe_buildings.ui.tooltip import (
    _unit_class_icon_key as _tooltip_unit_class_icon_key,
    _unit_group_label as _tooltip_unit_group_label,
)

_ALL_ERAS_SENTINEL = "__all_eras__"
# Extreme eras used for the fast "All eras" overview. Rendering only two eras
# per building keeps initial load responsive; specific eras load on demand.
_MIN_ERA_KEY = "BronzeAge"
_MAX_ERA_KEY = "StellarAgeDiscovery"

_ERA_KEYS = list(config.ERAS_DICT.keys())


def _era_sort_rank(era_key: str) -> int:
    """Return a rank where the oldest era sorts first.

    ``config.ERAS_DICT`` is ordered newest-first, so we reverse that order.
    """
    try:
        return _ERA_KEYS.index(era_key)
    except ValueError:
        return -1


_UNIT_GROUP_KEY_RE = re.compile(r"^(?P<era>[^#]+)#(?P<unit_class>.+)$")


def _unit_class_from_group_key(group_key: Optional[str]) -> Optional[str]:
    """Return the unit class part of a group key like ``NextEra#fast``."""
    if not group_key:
        return None
    match = _UNIT_GROUP_KEY_RE.match(group_key)
    return match.group("unit_class") if match else None


def _infer_unit_era_token(
    sections: List[TooltipSection],
) -> Optional[str]:
    """Return the era token (CurrentEra/NextEra) used by unit rows, if any."""
    for section in sections:
        for row in section.rows:
            token = _unit_era_token_from_group_key(row.group_key)
            if token in ("CurrentEra", "NextEra"):
                return token
        for group in section.random_groups:
            for outcome in group.outcomes:
                token = _unit_era_token_from_group_key(outcome.row.group_key)
                if token in ("CurrentEra", "NextEra"):
                    return token
    return None


def _unit_era_token_from_group_key(group_key: Optional[str]) -> Optional[str]:
    if not group_key:
        return None
    match = _UNIT_GROUP_KEY_RE.match(group_key)
    return match.group("era") if match else None


def _normalize_unit_row_for_all_eras(
    row: TooltipRow,
    unit_era_token: str,
    lang_code: str,
) -> TooltipRow:
    """Force a unit row to use the given era token for label/icon/grouping."""
    unit_class = _unit_class_from_group_key(row.group_key)
    if unit_class is None:
        return row
    label = _tooltip_unit_group_label(unit_class, lang_code, era_token=unit_era_token)
    icon = resolve_game_icon(
        _tooltip_unit_class_icon_key(unit_class, era_token=unit_era_token),
        label,
    )
    return TooltipRow(
        icon=icon,
        label=label,
        value=row.value,
        suffix=row.suffix,
        show_label=row.show_label,
        display_label=row.display_label,
        duration=row.duration,
        markers=row.markers,
        group_key=unit_class,
        group_label=label,
        group_icon_key=_tooltip_unit_class_icon_key(
            unit_class, era_token=unit_era_token
        ),
    )


_NATURAL_SORT_RE = re.compile(r"^(.*?)(\d+)([a-zA-Z]?)$")


def _natural_building_id_key(building_id: Any) -> Tuple[str, int, str]:
    """Return a sort key that orders numeric suffixes naturally.

    Examples:
        W_MultiAge_FALL26A1   -> ("W_MultiAge_FALL26A", 1, "")
        W_MultiAge_FALL26A10  -> ("W_MultiAge_FALL26A", 10, "")
        W_MultiAge_FALL26A10a -> ("W_MultiAge_FALL26A", 10, "a")
    """
    text = str(building_id) if building_id is not None else ""
    match = _NATURAL_SORT_RE.match(text)
    if not match:
        return (text, 0, "")
    prefix, number, suffix = match.groups()
    return (prefix, int(number), suffix.lower())


def _parse_numeric_value(value: str) -> Optional[Tuple[float, str]]:
    """Return (number, suffix) for simple numeric or percent values, else None."""
    value = value.strip()
    match = re.match(r"^([+\-]?\d+(?:\.\d+)?)\s*(%?)$", value)
    if not match:
        return None
    number = float(match.group(1))
    suffix = match.group(2)
    return (number, suffix)


def _format_numeric_range(left: float, right: float, suffix: str) -> str:
    """Format a numeric range, collapsing identical values.

    ``left`` and ``right`` are expected to be in era order (earliest era on
    the left, latest era on the right), not min/max order.
    """
    if left == right:
        formatted = f"{int(left)}" if left == int(left) else f"{left}"
        return f"{formatted}{suffix}"
    left_str = f"{int(left)}" if left == int(left) else f"{left}"
    right_str = f"{int(right)}" if right == int(right) else f"{right}"
    return f"{left_str} - {right_str}{suffix}"


def _aggregate_tooltip_rows(rows: List[TooltipRow]) -> TooltipRow:
    """Aggregate rows with the same label/icon into a range or unique list."""
    if not rows:
        return TooltipRow(icon=None, label="", value="")

    first = rows[0]
    if len(rows) == 1:
        return first

    numeric_values: List[Tuple[float, str]] = []
    non_numeric_values: List[str] = []

    for row in rows:
        parsed = _parse_numeric_value(row.value)
        if parsed is not None:
            numeric_values.append(parsed)
        else:
            non_numeric_values.append(row.value)

    if numeric_values and len(numeric_values) == len(rows):
        # Rows are expected to be sorted from earliest era to latest era.
        left = numeric_values[0][0]
        right = numeric_values[-1][0]
        suffixes = {v[1] for v in numeric_values}
        suffix = next(iter(suffixes)) if len(suffixes) == 1 else ""
        aggregated_value = _format_numeric_range(left, right, suffix)
    else:
        unique_values = []
        seen = set()
        for value in (row.value for row in rows):
            if value not in seen:
                seen.add(value)
                unique_values.append(value)
        aggregated_value = " / ".join(unique_values)

    # For era-variant rewards (units) render a generic label/icon in All eras.
    group_key = first.group_key
    if group_key and all(row.group_key == group_key for row in rows):
        label = first.group_label or first.label
        icon = (
            resolve_game_icon(first.group_icon_key, label)
            if first.group_icon_key
            else first.icon
        )
    else:
        label = first.label
        icon = first.icon

    return TooltipRow(
        icon=icon,
        label=label,
        value=aggregated_value,
        suffix=first.suffix,
        show_label=first.show_label,
        display_label=first.display_label,
        duration=first.duration,
        markers=first.markers,
        group_key=group_key,
        group_label=first.group_label,
        group_icon_key=first.group_icon_key,
    )


def _row_identity(row: TooltipRow) -> Tuple:
    """Return a hashable identity for grouping equivalent rows across eras.

    Rows that carry a ``group_key`` (e.g. era-specific units) are grouped by
    that key so the All-eras view can collapse them into a single generic row.
    Duration is part of the identity so that mixed-duration productions do not
    get merged into a single misleading range.
    """
    icon_key = row.icon.key if row.icon is not None else None
    marker_keys = tuple(m.key if m is not None else None for m in row.markers)
    return (
        row.group_key or row.label,
        row.group_icon_key if row.group_key else icon_key,
        row.suffix,
        row.duration,
        marker_keys,
    )


def _aggregate_tooltip_sections(
    sections_per_era: Dict[str, List[TooltipSection]],
    lang_code: str = "en",
    unit_era_token: Optional[str] = None,
) -> List[TooltipSection]:
    """Merge per-era sections, aggregating matching rows into ranges."""
    if not sections_per_era:
        return []

    section_order: List[str] = []
    rows_by_section: Dict[str, Dict] = {}

    for era, sections in sections_per_era.items():
        for section in sections:
            section_key = section.key if section.key is not None else ""
            if section_key not in rows_by_section:
                rows_by_section[section_key] = {
                    "title": section.title,
                    "rows": {},
                    "random_groups": [],
                    "shared_duration": section.shared_duration,
                    "order": len(section_order),
                }
                section_order.append(section_key)

            bucket = rows_by_section[section_key]
            for row in section.rows:
                if unit_era_token is not None and row.group_key is not None:
                    row = _normalize_unit_row_for_all_eras(
                        row, unit_era_token, lang_code
                    )
                identity = _row_identity(row)
                bucket["rows"].setdefault(identity, []).append((era, row))

            # Random groups are not aggregated in the MVP; keep the first era's groups.
            if section.random_groups and not bucket["random_groups"]:
                normalized_groups = []
                for group in section.random_groups:
                    normalized_outcomes = []
                    for outcome in group.outcomes:
                        row = outcome.row
                        if unit_era_token is not None and row.group_key is not None:
                            row = _normalize_unit_row_for_all_eras(
                                row, unit_era_token, lang_code
                            )
                        normalized_outcomes.append(
                            RandomOutcome(row=row, probability=outcome.probability)
                        )
                    normalized_groups.append(
                        RandomProductionGroup(
                            outcomes=normalized_outcomes,
                            duration=group.duration,
                            markers=group.markers,
                        )
                    )
                bucket["random_groups"] = normalized_groups

    aggregated: List[TooltipSection] = []
    first_era_sections = next(iter(sections_per_era.values()))
    for key in section_order:
        bucket = rows_by_section[key]
        aggregated_rows = []
        for era_rows in bucket["rows"].values():
            era_rows_sorted = sorted(
                era_rows,
                key=lambda pair: _era_sort_rank(pair[0]),
                reverse=True,
            )
            aggregated_rows.append(
                _aggregate_tooltip_rows([row for _, row in era_rows_sorted])
            )
        # Preserve original row order from the first era that introduced each identity.
        first_section = next(
            (s for s in first_era_sections if (s.key if s.key is not None else "") == key),
            None,
        )
        if first_section is not None:
            identity_order = [_row_identity(r) for r in first_section.rows]
            identity_index = {
                identity: idx for idx, identity in enumerate(identity_order)
            }
            aggregated_rows.sort(
                key=lambda r: identity_index.get(
                    _row_identity(r), len(identity_order)
                )
            )

        aggregated.append(
            TooltipSection(
                title=bucket["title"],
                rows=aggregated_rows,
                key=key,
                random_groups=bucket["random_groups"],
                shared_duration=bucket["shared_duration"],
            )
        )

    return aggregated


def _split_size_time_road_section(
    sections: List[TooltipSection],
) -> Tuple[Optional[TooltipSection], List[TooltipSection]]:
    """Extract the size/time/road section from a list of tooltip sections."""
    size_section: Optional[TooltipSection] = None
    other_sections: List[TooltipSection] = []
    for section in sections:
        if section.key == "size_time_road":
            size_section = section
        else:
            other_sections.append(section)
    return size_section, other_sections


def _get_sorted_event_eras(df: pd.DataFrame, event: str) -> List[str]:
    """Return the distinct eras of buildings for an event, in game order."""
    event_eras = df.loc[df[config.COL_EVENT] == event, config.COL_ERA].unique()
    era_order = {era: idx for idx, era in enumerate(config.ERAS_DICT.keys())}
    return sorted(event_eras, key=lambda era: era_order.get(era, len(era_order)))


def _get_sorted_building_eras(df: pd.DataFrame, building_id: str) -> List[str]:
    """Return the distinct eras for a single building, in game order."""
    building_eras = df.loc[df["id"] == building_id, config.COL_ERA].unique()
    era_order = {era: idx for idx, era in enumerate(config.ERAS_DICT.keys())}
    return sorted(building_eras, key=lambda era: era_order.get(era, len(era_order)))


def _deduplicate_buildings(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per building id, keeping the lowest-era row."""
    era_order = {era: idx for idx, era in enumerate(config.ERAS_DICT.keys())}
    df = df.copy()
    df["_era_order"] = df[config.COL_ERA].map(
        lambda era: era_order.get(era, len(era_order))
    )
    df = df.sort_values(by=["id", "_era_order"])
    df = df.drop_duplicates(subset=["id"], keep="first")
    df = df.drop(columns=["_era_order"])
    return df


def _render_tooltip_rows_html(rows: List[TooltipRow], lang_code: str) -> str:
    """Render tooltip rows as compact HTML."""
    from foe_buildings.ui.tooltip import _tooltip_row_html

    return "".join(_tooltip_row_html(row, lang_code) for row in rows)


_SECTION_ORDER = {
    "ally_rooms": 0,
    "provides": 1,
    "produces": 2,
    "chain_set": 3,
    "costs": 4,
    "traits": 5,
}


def _reorder_event_tooltip_sections(
    sections: List[TooltipSection],
) -> List[TooltipSection]:
    """Return sections in the order preferred by the event tooltip view."""
    return sorted(
        sections,
        key=lambda s: _SECTION_ORDER.get(s.key if s.key is not None else "", 99),
    )


def _is_fragment_row(row: TooltipRow) -> bool:
    """Return True if the row represents a fragment reward."""
    return any(
        marker is not None and marker.key == "icon_tooltip_fragment"
        for marker in row.markers
    )


def _reformat_fragment_row(row: TooltipRow) -> TooltipRow:
    """Rewrite a fragment row to 'value [fragment_icon] of [name] [markers]'."""
    fragment_marker = next(
        marker
        for marker in row.markers
        if marker is not None and marker.key == "icon_tooltip_fragment"
    )
    remaining_markers = [
        marker
        for marker in row.markers
        if marker is not None and marker.key != "icon_tooltip_fragment"
    ]
    # Label currently ends with " Fragments"; strip that to recover the item name.
    item_name = re.sub(r"\s+[Ff]ragments$", "", row.label).strip()
    inline_fragment = (
        f'<img src="{html.escape(fragment_marker.url)}" '
        f'class="foe-tooltip-marker" alt="{html.escape(fragment_marker.accessible_name)}">'
        if fragment_marker.url
        else ""
    )
    new_value = f"{html.escape(str(row.value))} {inline_fragment} of {html.escape(item_name)}"
    return TooltipRow(
        icon=row.icon,
        label=row.label,
        value=new_value,
        suffix=row.suffix,
        show_label=False,
        duration=row.duration,
        markers=remaining_markers,
        value_is_html=True,
    )


def _render_tooltip_rows_html(rows: List[TooltipRow], lang_code: str) -> str:
    """Render tooltip rows as compact HTML."""
    from foe_buildings.ui.tooltip import _tooltip_row_html

    processed_rows = [
        _reformat_fragment_row(row) if _is_fragment_row(row) else row for row in rows
    ]
    return "".join(_tooltip_row_html(row, lang_code) for row in processed_rows)


def _render_tooltip_section_html(section: TooltipSection, lang_code: str) -> str:
    """Render one tooltip section as compact HTML."""
    from foe_buildings.ui.tooltip import _random_group_html

    parts: List[str] = []
    if section.title:
        title = section.title
        if section.shared_duration:
            title = f"{title} ({tooltip_renderer.format_time(section.shared_duration)})"
        parts.append(
            f'<div class="foe-tooltip-section-title">{html.escape(title)}</div>'
        )
    parts.append(_render_tooltip_rows_html(section.rows, lang_code))
    for group in section.random_groups:
        reformatted_group = RandomProductionGroup(
            outcomes=[
                RandomOutcome(
                    row=_reformat_fragment_row(outcome.row)
                    if _is_fragment_row(outcome.row)
                    else outcome.row,
                    probability=outcome.probability,
                )
                for outcome in group.outcomes
            ],
            duration=group.duration,
            markers=group.markers,
        )
        parts.append(_random_group_html(reformatted_group, lang_code))
    return f'<div class="foe-tooltip-section foe-tooltip-section-first">{"".join(parts)}</div>'


def _building_id_html(building_id: str) -> str:
    """Return a compact HTML row displaying the building id."""
    escaped_id = html.escape(str(building_id))
    return (
        f'<div class="foe-tooltip-row" role="group" '
        f'aria-label="ID: {escaped_id}" title="ID: {escaped_id}">'
        f'ID: {escaped_id}</div>'
    )


def _render_building_card_html(
    building_data: pd.Series,
    sections: List[TooltipSection],
    lang_code: str,
    image_manager: Any,
) -> str:
    """Return the HTML for one building card with left and right panels."""
    size_section, other_sections = _split_size_time_road_section(sections)
    other_sections = _reorder_event_tooltip_sections(other_sections)
    building_name = building_data.get(config.COL_NAME, "")

    left_parts: List[str] = []
    building_asset_id = building_data.get(config.COL_ASSET_ID)
    if (
        building_asset_id
        and image_manager is not None
        and image_manager.has_image(building_asset_id)
    ):
        image_url = image_manager.get_building_image_url(building_asset_id)
        if image_url:
            left_parts.append(
                f'<img src="{html.escape(image_url)}" '
                f'alt="{html.escape(str(building_name))}">'
            )

    if size_section is not None:
        left_parts.append(_render_tooltip_rows_html(size_section.rows, lang_code))

    building_id = building_data.get("id")
    if building_id:
        left_parts.append(_building_id_html(building_id))

    right_parts: List[str] = []
    for section in other_sections:
        if not (section.title or section.rows or section.random_groups):
            continue
        right_parts.append(_render_tooltip_section_html(section, lang_code))

    return (
        f'<div class="foe-event-tooltip-card">'
        f'<div class="foe-event-tooltip-name">{html.escape(str(building_name))}</div>'
        f'<div class="foe-event-tooltip-body">'
        f'<div class="foe-event-tooltip-left">{"".join(left_parts)}</div>'
        f'<div class="foe-event-tooltip-right">{"".join(right_parts)}</div>'
        f"</div></div>"
    )


def _render_building_card(
    building_data: pd.Series,
    sections: List[TooltipSection],
    lang_code: str,
    image_manager: Any,
) -> None:
    """Render one building card with left and right panels."""
    st.markdown(
        _render_building_card_html(building_data, sections, lang_code, image_manager),
        unsafe_allow_html=True,
    )


def _resolve_building_sections(
    building_data: pd.Series,
    era_key: str,
    lang_code: str,
    lookup: Dict[str, Any],
    asset_map: Optional[Dict[str, str]] = None,
) -> List[TooltipSection]:
    """Return tooltip sections for a building, using preloaded data and assets."""
    building_id = building_data.get("id")
    building_name = building_data.get(config.COL_NAME)
    entity = lookup.get(building_id)
    if not entity or not entity.get("components"):
        return []
    return tooltip_renderer.render_building_tooltip(
        entity,
        lang_code,
        building_name=str(building_name),
        image_url=None,
        era_key=era_key if era_key else None,
        asset_map=asset_map,
    )


_CSS_LOADED_KEY = "_event_tooltip_css_loaded"
_CARDS_CACHE_KEY = "_event_tooltip_cards_cache"


def _building_card_cache_key(
    selected_event: str,
    selected_era_key: str,
    lang_code: str,
    event_buildings: pd.DataFrame,
) -> Tuple[str, str, str, Tuple[Tuple[str, str, str], ...]]:
    """Return a stable key for the rendered card list."""
    building_keys = tuple(
        (
            str(row.get("id", "")),
            str(row.get(config.COL_NAME, "")),
            str(row.get(config.COL_ASSET_ID, "")),
        )
        for _, row in event_buildings.iterrows()
    )
    return (selected_event, selected_era_key, lang_code, building_keys)


def _no_tooltip_data_card_html(building_data: pd.Series, lang_code: str) -> str:
    """Return a placeholder card when no tooltip data is available."""
    building_name = building_data.get(config.COL_NAME, "")
    message = translations.get_text("no_tooltip_data", lang_code)
    return (
        f'<div class="foe-event-tooltip-card">'
        f'<div class="foe-event-tooltip-name">{html.escape(str(building_name))}</div>'
        f'<div class="foe-event-tooltip-body">{html.escape(message)}</div>'
        f"</div>"
    )


def _resolve_all_eras_sections(
    building_data: pd.Series,
    lang_code: str,
    lookup: Dict[str, Any],
    asset_map: Optional[Dict[str, str]] = None,
) -> List[TooltipSection]:
    """Resolve and aggregate the two extreme-era section sets for a building."""
    sections_per_era: Dict[str, List[TooltipSection]] = {}
    for era_key in (_MAX_ERA_KEY, _MIN_ERA_KEY):
        sections = _resolve_building_sections(
            building_data, era_key, lang_code, lookup, asset_map=asset_map
        )
        if sections:
            sections_per_era[era_key] = sections
    unit_era_token = _infer_unit_era_token(
        sections_per_era.get(_MIN_ERA_KEY, [])
    )
    return _aggregate_tooltip_sections(
        sections_per_era,
        lang_code=lang_code,
        unit_era_token=unit_era_token,
    )


def _generate_event_cards_html(
    event_buildings: pd.DataFrame,
    selected_era_key: str,
    lang_code: str,
    image_manager: Any,
    lookup: Dict[str, Any],
    asset_map: Optional[Dict[str, str]] = None,
) -> List[str]:
    """Generate one HTML card per building for the selected event and era."""
    cards: List[str] = []
    for _, building_data in event_buildings.iterrows():
        if selected_era_key == _ALL_ERAS_SENTINEL:
            sections = _resolve_all_eras_sections(
                building_data, lang_code, lookup, asset_map=asset_map
            )
        else:
            sections = _resolve_building_sections(
                building_data,
                selected_era_key,
                lang_code,
                lookup,
                asset_map=asset_map,
            )

        if not sections:
            cards.append(_no_tooltip_data_card_html(building_data, lang_code))
        else:
            cards.append(
                _render_building_card_html(
                    building_data, sections, lang_code, image_manager
                )
            )
    return cards


def render_event_tooltips(
    df_original: pd.DataFrame,
    selected_events: List[str],
    selected_translated_era: str,
    lang_code: str,
    image_manager: Any,
) -> None:
    """Render the Event Tooltips tab."""
    # Inject tooltip CSS once per session; it is harmless to keep in the DOM.
    if not st.session_state.get(_CSS_LOADED_KEY):
        st.markdown(load_tooltip_css(), unsafe_allow_html=True)
        st.session_state[_CSS_LOADED_KEY] = True

    st.header(translations.get_text("event_tooltips", lang_code))

    available_events = sorted(df_original[config.COL_EVENT].unique())
    if selected_events:
        available_events = [e for e in available_events if e in selected_events]

    if not available_events:
        st.info(translations.get_text("no_event_selected", lang_code))
        return

    default_event = ""
    if SessionKeys.SELECTED_EVENT_TOOLTIP_EVENT in st.session_state:
        default_event = st.session_state[SessionKeys.SELECTED_EVENT_TOOLTIP_EVENT]
    if default_event not in available_events and len(available_events) == 1:
        default_event = available_events[0]
    if default_event not in available_events:
        default_event = available_events[0]

    col_event, col_era, col_layout = st.columns([2, 1, 1])
    with col_event:
        selected_event = st.selectbox(
            translations.get_text("select_event", lang_code),
            options=available_events,
            index=available_events.index(default_event),
            key="event_tooltip_event_selector",
        )
    st.session_state[SessionKeys.SELECTED_EVENT_TOOLTIP_EVENT] = selected_event

    event_buildings = df_original[df_original[config.COL_EVENT] == selected_event].copy()
    event_buildings = _deduplicate_buildings(event_buildings)
    event_buildings = event_buildings.sort_values(
        by="id",
        ascending=True,
        key=lambda series: series.map(_natural_building_id_key),
    )

    event_eras = _get_sorted_event_eras(df_original, selected_event)
    era_options = [translations.get_text("all_eras", lang_code)] + [
        translations.translate_era_key(era, lang_code) for era in event_eras
    ]

    default_era = translations.get_text("all_eras", lang_code)
    stored_era = st.session_state.get(SessionKeys.SELECTED_EVENT_TOOLTIP_ERA, "")
    if stored_era in era_options:
        default_era = stored_era

    with col_era:
        selected_era_label = st.selectbox(
            translations.translate_column("Era", lang_code),
            options=era_options,
            index=era_options.index(default_era),
            key="event_tooltip_era_selector",
        )
    st.session_state[SessionKeys.SELECTED_EVENT_TOOLTIP_ERA] = selected_era_label

    with col_layout:
        num_columns = st.slider(
            translations.get_text("columns", lang_code),
            min_value=1,
            max_value=4,
            value=2,
            step=1,
            key="event_tooltip_columns_slider",
        )

    if event_buildings.empty:
        st.info(translations.get_text("no_buildings_for_event", lang_code))
        return

    if selected_era_label == translations.get_text("all_eras", lang_code):
        selected_era_key = _ALL_ERAS_SENTINEL
    else:
        # Map translated label back to raw era key.
        selected_era_key = next(
            era for era in event_eras
            if translations.translate_era_key(era, lang_code) == selected_era_label
        )

    # Load shared data once per render so that the per-building loop does not
    # repeatedly hit the Streamlit cache machinery.
    lookup = data_loader.load_building_entity_lookup()
    asset_map = tooltip_icons.load_forgehx_asset_map()

    cache_key = _building_card_cache_key(
        selected_event, selected_era_key, lang_code, event_buildings
    )
    cached = st.session_state.get(_CARDS_CACHE_KEY)
    if cached is not None and cached[0] == cache_key:
        cards_html = cached[1]
    else:
        cards_html = _generate_event_cards_html(
            event_buildings,
            selected_era_key,
            lang_code,
            image_manager,
            lookup,
            asset_map=asset_map,
        )
        st.session_state[_CARDS_CACHE_KEY] = (cache_key, cards_html)

    grid_html = (
        f'<div class="foe-event-tooltip-grid" '
        f'style="grid-template-columns: repeat({num_columns}, minmax(0, 1fr));"'
        f'>{"".join(cards_html)}</div>'
    )
    st.markdown(grid_html, unsafe_allow_html=True)

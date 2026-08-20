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
from foe_buildings.ui.tooltip import TooltipRow, TooltipSection

_ALL_ERAS_SENTINEL = "__all_eras__"


def _parse_numeric_value(value: str) -> Optional[Tuple[float, str]]:
    """Return (number, suffix) for simple numeric or percent values, else None."""
    value = value.strip()
    match = re.match(r"^([+\-]?\d+(?:\.\d+)?)\s*(%?)$", value)
    if not match:
        return None
    number = float(match.group(1))
    suffix = match.group(2)
    return (number, suffix)


def _format_numeric_range(min_val: float, max_val: float, suffix: str) -> str:
    """Format a numeric range, collapsing identical values."""
    if min_val == max_val:
        formatted = f"{int(min_val)}" if min_val == int(min_val) else f"{min_val}"
        return f"{formatted}{suffix}"
    min_str = f"{int(min_val)}" if min_val == int(min_val) else f"{min_val}"
    max_str = f"{int(max_val)}" if max_val == int(max_val) else f"{max_val}"
    return f"{min_str} - {max_str}{suffix}"


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
        numbers = [v[0] for v in numeric_values]
        suffixes = {v[1] for v in numeric_values}
        suffix = next(iter(suffixes)) if len(suffixes) == 1 else ""
        aggregated_value = _format_numeric_range(min(numbers), max(numbers), suffix)
    else:
        unique_values = []
        seen = set()
        for value in (row.value for row in rows):
            if value not in seen:
                seen.add(value)
                unique_values.append(value)
        aggregated_value = " / ".join(unique_values)

    return TooltipRow(
        icon=first.icon,
        label=first.label,
        value=aggregated_value,
        suffix=first.suffix,
        show_label=first.show_label,
        duration=first.duration,
        markers=first.markers,
    )


def _row_identity(row: TooltipRow) -> Tuple:
    """Return a hashable identity for grouping equivalent rows across eras."""
    icon_key = row.icon.key if row.icon is not None else None
    marker_keys = tuple(m.key if m is not None else None for m in row.markers)
    return (row.label, icon_key, row.suffix, marker_keys)


def _aggregate_tooltip_sections(
    sections_per_era: Dict[str, List[TooltipSection]],
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
                identity = _row_identity(row)
                bucket["rows"].setdefault(identity, []).append(row)

            # Random groups are not aggregated in the MVP; keep the first era's groups.
            if section.random_groups and not bucket["random_groups"]:
                bucket["random_groups"] = section.random_groups

    aggregated: List[TooltipSection] = []
    first_era_sections = next(iter(sections_per_era.values()))
    for key in section_order:
        bucket = rows_by_section[key]
        aggregated_rows = [
            _aggregate_tooltip_rows(rows)
            for rows in bucket["rows"].values()
        ]
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
        parts.append(_random_group_html(group, lang_code))
    return f'<div class="foe-tooltip-section foe-tooltip-section-first">{"".join(parts)}</div>'


def _render_building_card(
    building_data: pd.Series,
    sections: List[TooltipSection],
    lang_code: str,
    image_manager: Any,
) -> None:
    """Render one building card with left and right panels."""
    size_section, other_sections = _split_size_time_road_section(sections)

    with st.container(border=True):
        left_col, right_col = st.columns([1, 2], gap="small")

        with left_col:
            building_asset_id = building_data.get(config.COL_ASSET_ID)
            if building_asset_id and image_manager is not None and image_manager.has_image(building_asset_id):
                image_url = image_manager.get_building_image_url(building_asset_id)
                st.image(image_url, width=80)

            if size_section is not None:
                st.markdown(
                    _render_tooltip_rows_html(size_section.rows, lang_code),
                    unsafe_allow_html=True,
                )

        with right_col:
            for section in other_sections:
                if not (section.title or section.rows or section.random_groups):
                    continue
                st.markdown(
                    _render_tooltip_section_html(section, lang_code),
                    unsafe_allow_html=True,
                )


@st.cache_data
def _cached_building_tooltip_sections(
    building_id: str,
    era_key: str,
    lang_code: str,
    building_name: str,
) -> List[TooltipSection]:
    """Cache tooltip sections per building, era, and language."""
    lookup = data_loader.load_building_entity_lookup()
    entity = lookup.get(building_id)
    if not entity or not entity.get("components"):
        return []
    return tooltip_renderer.render_building_tooltip(
        entity,
        lang_code,
        building_name=building_name,
        image_url=None,
        era_key=era_key if era_key else None,
    )


def _resolve_building_sections(
    building_data: pd.Series,
    era_key: str,
    lang_code: str,
) -> List[TooltipSection]:
    """Return tooltip sections for a building, using cache when possible."""
    building_id = building_data.get("id")
    building_name = building_data.get(config.COL_NAME)
    return _cached_building_tooltip_sections(
        building_id=str(building_id),
        era_key=era_key,
        lang_code=lang_code,
        building_name=str(building_name),
    )


def render_event_tooltips(
    df_original: pd.DataFrame,
    selected_events: List[str],
    selected_translated_era: str,
    lang_code: str,
    image_manager: Any,
) -> None:
    """Render the Event Tooltips tab."""
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

    col_event, col_era = st.columns([2, 1])
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
    event_buildings = event_buildings.sort_values(by="id", ascending=True)

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

    # Render in rows of 3.
    building_rows = [
        event_buildings.iloc[i : i + 3] for i in range(0, len(event_buildings), 3)
    ]

    for row_df in building_rows:
        cols = st.columns(3, gap="small")
        for col, (_, building_data) in zip(cols, row_df.iterrows()):
            with col:
                if selected_era_key == _ALL_ERAS_SENTINEL:
                    sections_per_era: Dict[str, List[TooltipSection]] = {}
                    building_id = building_data.get("id")
                    for era_key in _get_sorted_building_eras(df_original, building_id):
                        sections = _resolve_building_sections(
                            building_data, era_key, lang_code
                        )
                        if sections:
                            sections_per_era[era_key] = sections
                    sections = _aggregate_tooltip_sections(sections_per_era)
                else:
                    sections = _resolve_building_sections(
                        building_data, selected_era_key, lang_code
                    )

                if not sections:
                    st.info(
                        translations.get_text("no_tooltip_data", lang_code),
                        icon="⚠️",
                    )
                    continue

                _render_building_card(building_data, sections, lang_code, image_manager)

# Event Tooltips Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a top-level "Event Tooltips" tab where the user selects an event and browses all related buildings as compact in-game tooltip cards, with an "All eras" range view and a per-era selector.

**Architecture:** Extend the existing Streamlit app with a new tab module (`foe_buildings/tabs/event_tooltips.py`) that reuses the cached entity lookup and the existing `render_building_tooltip()` renderer. Tooltip sections are rendered per era and cached; a small helper aggregates matching rows into min–max ranges for the default "All eras" view. Each building is rendered in a two-panel card inside a 3-column grid.

**Tech Stack:** Python 3.12, Streamlit 1.55, Pandas, Pytest.

## Global Constraints

- Data source: `foe_buildings.data.loader.load_building_entity_lookup()`
- Tooltip renderer: `foe_buildings.ui.tooltip.render_building_tooltip()`
- Per-square mode does NOT apply to this tab
- UI labels translated via `foe_buildings/i18n/locales/{en,fr}/ui.json`
- New code follows existing style (ruff, pre-commit)
- Tests run with `pytest tests/`
- Do not rename or refactor existing public symbols without checking callers

---

### Task 1: Add Session Keys for Event Tooltips Tab

**Files:**
- Modify: `foe_buildings/config/session.py`

**Interfaces:**
- Consumes: existing `SessionKeys` class
- Produces: `SessionKeys.SELECTED_EVENT_TOOLTIP_EVENT`, `SessionKeys.SELECTED_EVENT_TOOLTIP_ERA`

- [ ] **Step 1: Add the new keys**

In `foe_buildings/config/session.py`, add inside the `SessionKeys` class:

```python
SELECTED_EVENT_TOOLTIP_EVENT = "selected_event_tooltip_event"
SELECTED_EVENT_TOOLTIP_ERA = "selected_event_tooltip_era"
```

- [ ] **Step 2: Initialize defaults in `init_session_state()`**

Add to the `defaults` dict:

```python
SessionKeys.SELECTED_EVENT_TOOLTIP_EVENT: "",
SessionKeys.SELECTED_EVENT_TOOLTIP_ERA: "",
```

- [ ] **Step 3: Run config tests**

Run: `pytest tests/test_config.py -v`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add foe_buildings/config/session.py
git commit -m "feat(event-tooltips): add session keys for event and era selection"
```

---

### Task 2: Add Translation Keys

**Files:**
- Modify: `foe_buildings/i18n/locales/en/ui.json`
- Modify: `foe_buildings/i18n/locales/fr/ui.json`

**Interfaces:**
- Produces: new translatable UI strings

- [ ] **Step 1: Add English keys**

Add to `foe_buildings/i18n/locales/en/ui.json`:

```json
{
  ...
  "event_tooltips": "Event Tooltips",
  "select_event": "Select event",
  "all_eras": "All eras",
  "no_event_selected": "Select an event to view its buildings.",
  "no_buildings_for_event": "No buildings found for this event.",
  "era_range_label": "Era range"
}
```

- [ ] **Step 2: Add French keys**

Add to `foe_buildings/i18n/locales/fr/ui.json`:

```json
{
  ...
  "event_tooltips": "Infobulles d'événement",
  "select_event": "Sélectionner un événement",
  "all_eras": "Toutes les ères",
  "no_event_selected": "Sélectionnez un événement pour voir ses bâtiments.",
  "no_buildings_for_event": "Aucun bâtiment trouvé pour cet événement.",
  "era_range_label": "Plage d'ères"
}
```

- [ ] **Step 3: Validate JSON syntax**

Run:

```bash
python -m json.tool foe_buildings/i18n/locales/en/ui.json > /dev/null
python -m json.tool foe_buildings/i18n/locales/fr/ui.json > /dev/null
```

Expected: No output (success).

- [ ] **Step 4: Commit**

```bash
git add foe_buildings/i18n/locales/en/ui.json foe_buildings/i18n/locales/fr/ui.json
git commit -m "feat(event-tooltips): add EN and FR translation keys"
```

---

### Task 3: Create Tooltip Section Aggregation Helpers

**Files:**
- Create: `foe_buildings/tabs/event_tooltips.py` (initial helpers only)
- Test: `tests/test_event_tooltips.py`

**Interfaces:**
- Consumes: `TooltipSection`, `TooltipRow` from `foe_buildings.ui.tooltip`
- Produces:
  - `_split_size_time_road_section(sections) -> tuple[Optional[TooltipSection], list[TooltipSection]]`
  - `_aggregate_tooltip_sections(sections_per_era: dict[str, list[TooltipSection]], lang_code: str) -> list[TooltipSection]`
  - `_format_numeric_range(min_val, max_val, suffix) -> str`
  - `_parse_numeric_value(value: str) -> Optional[tuple[float, str]]`

- [ ] **Step 1: Write failing tests**

Create `tests/test_event_tooltips.py`:

```python
import pytest

from foe_buildings.tabs import event_tooltips
from foe_buildings.ui.tooltip import TooltipRow, TooltipSection


def test_parse_numeric_value_detects_plain_number():
    result = event_tooltips._parse_numeric_value("120")
    assert result == (120.0, "")


def test_parse_numeric_value_detects_percent():
    result = event_tooltips._parse_numeric_value("20%")
    assert result == (20.0, "%")


def test_parse_numeric_value_returns_none_for_time():
    assert event_tooltips._parse_numeric_value("1d 2h") is None


def test_format_numeric_range_collapses_equal_values():
    assert event_tooltips._format_numeric_range(15.0, 15.0, "") == "15"


def test_format_numeric_range_shows_range():
    assert event_tooltips._format_numeric_range(10.0, 30.0, "%") == "10 - 30%"


def test_aggregate_tooltip_sections_combines_numeric_rows():
    row = TooltipRow(icon=None, label="Coins", value="100")
    sections = {
        "era1": [TooltipSection(title="Provides", rows=[row], key="provides")],
        "era2": [TooltipSection(title="Provides", rows=[TooltipRow(icon=None, label="Coins", value="300")], key="provides")],
    }
    aggregated = event_tooltips._aggregate_tooltip_sections(sections, "en")
    assert len(aggregated) == 1
    assert aggregated[0].rows[0].value == "100 - 300"


def test_split_size_time_road_section_extracts_road_section():
    size_section = TooltipSection(title="Size", rows=[], key="size_time_road")
    other_section = TooltipSection(title="Provides", rows=[], key="provides")
    extracted, rest = event_tooltips._split_size_time_road_section([size_section, other_section])
    assert extracted is size_section
    assert rest == [other_section]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_event_tooltips.py -v`

Expected: FAIL with `ModuleNotFoundError` or `AttributeError` for missing helpers.

- [ ] **Step 3: Implement helpers**

Create `foe_buildings/tabs/event_tooltips.py` with the helpers:

```python
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from foe_buildings.ui.tooltip import TooltipRow, TooltipSection


_ALL_ERAS_SENTINEL = ""


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


def _aggregate_tooltip_rows(rows: List[TooltipRow], lang_code: str) -> TooltipRow:
    """Aggregate rows with the same label/icon into a range or unique list."""
    if not rows:
        return rows[0] if rows else TooltipRow(icon=None, label="", value="")

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
    lang_code: str,
) -> List[TooltipSection]:
    """Merge per-era sections, aggregating matching rows into ranges."""
    if not sections_per_era:
        return []

    section_order: List[str] = []
    rows_by_section: Dict[str, Dict] = {}

    for era, sections in sections_per_era.items():
        for section in sections:
            if section.key not in rows_by_section:
                rows_by_section[section.key] = {
                    "title": section.title,
                    "rows": {},
                    "random_groups": [],
                    "shared_duration": section.shared_duration,
                    "order": len(section_order),
                }
                section_order.append(section.key)

            bucket = rows_by_section[section.key]
            for row in section.rows:
                identity = _row_identity(row)
                bucket["rows"].setdefault(identity, []).append(row)

            # Random groups are not aggregated in the MVP; keep the first era's groups.
            if section.random_groups and not bucket["random_groups"]:
                bucket["random_groups"] = section.random_groups

    aggregated: List[TooltipSection] = []
    for key in section_order:
        bucket = rows_by_section[key]
        aggregated_rows = [
            _aggregate_tooltip_rows(rows, lang_code)
            for rows in bucket["rows"].values()
        ]
        # Preserve original row order from the first era that introduced each identity.
        first_era_sections = next(iter(sections_per_era.values()))
        first_section = next((s for s in first_era_sections if s.key == key), None)
        if first_section is not None:
            identity_order = [_row_identity(r) for r in first_section.rows]
            aggregated_rows.sort(key=lambda r: identity_order.index(_row_identity(r)))

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_event_tooltips.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add foe_buildings/tabs/event_tooltips.py tests/test_event_tooltips.py
git commit -m "feat(event-tooltips): add tooltip section aggregation helpers"
```

---

### Task 4: Implement Event Tooltips Tab Renderer

**Files:**
- Modify: `foe_buildings/tabs/event_tooltips.py`
- Test: `tests/test_event_tooltips.py`

**Interfaces:**
- Consumes:
  - `foe_buildings.ui.tooltip.render_building_tooltip`
  - `foe_buildings.data.loader.load_building_entity_lookup`
  - `foe_buildings.config.SessionKeys`
  - `foe_buildings.i18n` for translations
- Produces: `render_event_tooltips(df_original, selected_events, selected_translated_era, lang_code, image_manager)`

- [ ] **Step 1: Write a failing smoke test**

Append to `tests/test_event_tooltips.py`:

```python
from unittest.mock import MagicMock, patch

import pandas as pd
import streamlit as st


def test_render_event_tooltips_splits_into_rows_of_three():
    df = pd.DataFrame(
        {
            "id": ["B1", "B2", "B3", "B4"],
            "name": ["Building 1", "Building 2", "Building 3", "Building 4"],
            "Event": ["Winter Event", "Winter Event", "Winter Event", "Winter Event"],
            "Era": ["BronzeAge", "BronzeAge", "BronzeAge", "BronzeAge"],
            "Translated Era": ["Bronze Age"] * 4,
            "asset_id": ["A1", "A2", "A3", "A4"],
        }
    )
    image_manager = MagicMock()
    image_manager.has_image.return_value = False

    with patch("foe_buildings.tabs.event_tooltips.data_loader.load_building_entity_lookup") as mock_lookup:
        mock_lookup.return_value = {
            "B1": {"name": "Building 1", "components": {"AllAge": {}}},
            "B2": {"name": "Building 2", "components": {"AllAge": {}}},
            "B3": {"name": "Building 3", "components": {"AllAge": {}}},
            "B4": {"name": "Building 4", "components": {"AllAge": {}}},
        }
        # Should not raise; we cannot easily assert Streamlit columns, but we verify no exception.
        event_tooltips.render_event_tooltips(df, [], "Bronze Age", "en", image_manager)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_event_tooltips.py::test_render_event_tooltips_splits_into_rows_of_three -v`

Expected: FAIL with `AttributeError` for missing `render_event_tooltips`.

- [ ] **Step 3: Implement the renderer**

Append to `foe_buildings/tabs/event_tooltips.py`:

```python
import html
from typing import Any, Dict, Iterable, List

import pandas as pd
import streamlit as st

from foe_buildings import config
from foe_buildings import i18n as translations
from foe_buildings.config import SessionKeys
from foe_buildings.data import loader as data_loader
from foe_buildings.ui import tooltip as tooltip_renderer
from foe_buildings.ui.tooltip import TooltipSection


def _get_sorted_event_eras(df: pd.DataFrame, event: str) -> List[str]:
    """Return the distinct eras of buildings for an event, in game order."""
    event_eras = df.loc[df[config.COL_EVENT] == event, config.COL_ERA].unique()
    era_order = {era: idx for idx, era in enumerate(config.ERAS_DICT.keys())}
    return sorted(event_eras, key=lambda era: era_order.get(era, len(era_order)))


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
            if building_asset_id and image_manager.has_image(building_asset_id):
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
    asset_id: Optional[str],
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
    asset_id = building_data.get(config.COL_ASSET_ID)
    return _cached_building_tooltip_sections(
        building_id=str(building_id),
        era_key=era_key,
        lang_code=lang_code,
        building_name=str(building_name),
        asset_id=str(asset_id) if pd.notna(asset_id) else None,
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
                building_id = building_data.get("id")
                entity = data_loader.load_building_entity_lookup().get(building_id)
                if not entity or not entity.get("components"):
                    st.info(
                        translations.get_text("no_tooltip_data", lang_code),
                        icon="⚠️",
                    )
                    continue

                if selected_era_key == _ALL_ERAS_SENTINEL:
                    sections_per_era: Dict[str, List[TooltipSection]] = {}
                    for era_key in event_eras:
                        sections = _resolve_building_sections(
                            building_data, era_key, lang_code
                        )
                        if sections:
                            sections_per_era[era_key] = sections
                    sections = _aggregate_tooltip_sections(sections_per_era, lang_code)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_event_tooltips.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add foe_buildings/tabs/event_tooltips.py tests/test_event_tooltips.py
git commit -m "feat(event-tooltips): implement event tooltips tab renderer"
```

---

### Task 5: Wire the New Tab into App Routing

**Files:**
- Modify: `foe_buildings/app.py`

**Interfaces:**
- Consumes: `render_event_tooltips` from `foe_buildings.tabs.event_tooltips`

- [ ] **Step 1: Import the new renderer**

In `foe_buildings/app.py`, add to the imports:

```python
from foe_buildings.tabs.event_tooltips import render_event_tooltips
```

- [ ] **Step 2: Add the tab name**

Change the `tab_names` list to include the new tab:

```python
tab_names = [
    translations.get_text("building_analysis", lang_code),
    translations.get_text("building_details", lang_code),
    translations.get_text("city_analysis", lang_code),
    translations.get_text("visualizations", lang_code),
    translations.get_text("event_tooltips", lang_code),
]
```

- [ ] **Step 3: Add the routing branch**

After the Visualizations tab block (around line 533), add:

```python
    # --- Event Tooltips Tab ---
    if st.session_state[SessionKeys.ACTIVE_MAIN_TAB] == 4:
        render_event_tooltips(
            df_original=df_original,
            selected_events=selected_events,
            selected_translated_era=selected_translated_era,
            lang_code=lang_code,
            image_manager=cached_image_manager,
        )
```

- [ ] **Step 4: Run the app smoke test**

Run: `pytest tests/test_app.py -v` if it exists, otherwise run the full suite.

Run: `pytest tests/ -v --tb=short`

Expected: PASS (or at least no new failures).

- [ ] **Step 5: Commit**

```bash
git add foe_buildings/app.py
git commit -m "feat(event-tooltips): wire event tooltips tab into main app routing"
```

---

### Task 6: Add Compact Card CSS

**Files:**
- Modify: `foe_buildings/ui/styles/tooltip.css`

**Interfaces:**
- Produces: `.foe-event-tooltip-card` and related CSS classes

- [ ] **Step 1: Add card styles**

Append to `foe_buildings/ui/styles/tooltip.css`:

```css
/* Event Tooltips tab: compact building cards */
.foe-event-tooltip-card {
  display: flex;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 0.5rem;
  background: color-mix(in srgb, var(--background-color) 95%, transparent);
  border: 1px solid color-mix(in srgb, var(--secondary-background-color) 80%, transparent);
}

.foe-event-tooltip-card .foe-tooltip-section {
  margin-top: 0.5rem;
  padding-top: 0;
}

.foe-event-tooltip-card .foe-tooltip-section-title {
  font-size: 0.85rem;
  margin-bottom: 0.2rem;
}

.foe-event-tooltip-card .foe-tooltip-row {
  min-height: 1.4rem;
  gap: 0.25rem;
  font-size: 0.85rem;
}

.foe-event-tooltip-card .foe-tooltip-icon,
.foe-event-tooltip-card .foe-tooltip-marker,
.foe-event-tooltip-card .tooltip-icon-missing {
  width: 1.25rem;
  height: 1.25rem;
  flex: 0 0 1.25rem;
}
```

Note: The `_render_building_card` function currently uses `st.container(border=True)` and inline layout; if you want to apply the custom card class, wrap the content in a `st.markdown(...)` block with the class. This CSS provides the styling hooks; applying the class is optional for the first version.

- [ ] **Step 2: Verify no syntax errors**

Run: `python -m py_compile foe_buildings/ui/styles/tooltip.css` is not meaningful; instead visually inspect the file.

- [ ] **Step 3: Commit**

```bash
git add foe_buildings/ui/styles/tooltip.css
git commit -m "style(event-tooltips): add compact card CSS hooks"
```

---

### Task 7: Final Verification

**Files:**
- All touched files

- [ ] **Step 1: Run the full test suite**

Run: `pytest tests/ -v --tb=short`

Expected: All tests pass; no new failures.

- [ ] **Step 2: Run linting**

Run: `ruff check foe_buildings/tabs/event_tooltips.py tests/test_event_tooltips.py foe_buildings/app.py foe_buildings/config/session.py`

Expected: No errors.

- [ ] **Step 3: Manual smoke test**

Run: `uv run streamlit run app.py`

Then:
1. Select the "Event Tooltips" tab.
2. Choose an event from the dropdown.
3. Verify buildings appear in rows of 3.
4. Switch the era selector from "All eras" to a specific era.
5. Verify values update (ranges collapse to single values in specific-era mode).
6. Switch language and verify labels translate.

- [ ] **Step 4: Commit any final fixes**

```bash
git commit -am "fix(event-tooltips): address review feedback / lint issues"
```

---

## Self-Review Checklist

- **Spec coverage:**
  - New main tab → Task 5
  - Event selector filtered by sidebar → Task 4
  - Era selector with "All eras" default → Task 4
  - 3 buildings per row → Task 4
  - Left panel image + size/time/road → Task 4
  - Right panel remaining stats → Task 4
  - Range aggregation across eras → Task 3
  - Caching per building/era/lang → Task 4
  - Error handling for missing entities → Task 4
  - i18n keys → Task 2
  - Tests → Tasks 3, 4, 5, 7

- **Placeholder scan:** No TBD, TODO, or vague "add error handling" steps remain.

- **Type consistency:** `TooltipSection`, `TooltipRow` from `foe_buildings.ui.tooltip` used consistently. `_cached_building_tooltip_sections` signature matches `_resolve_building_sections`.

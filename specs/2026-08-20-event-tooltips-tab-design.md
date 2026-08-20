# Event Tooltips Tab — Design Spec

> Status: Approved for implementation<br>
> Scope: Add a top-level "Event Tooltips" tab that lets the user select an event and browse all related buildings in an in-game tooltip layout, with optional era filtering and per-era range display.

## 1. Goal

Provide a dedicated gallery view where a player can pick an event and see every related building rendered as a compact in-game tooltip card. The view supports an "All eras" mode that shows each stat as a min–max range across the event's eras, and a single-era mode that shows the exact values for one era.

## 2. Constraints & Decisions

- **Data source**: Reuses the existing building entity lookup (`data/loader.py::load_building_entity_lookup()`) and the existing tooltip renderer (`ui/tooltip.py::render_building_tooltip()`).
- **Caching**: Per-era tooltip sections are cached with `@st.cache_data` keyed by building id, era key, and language code. Range aggregation happens after cache retrieval so it is cheap in "All eras" mode.
- **Per-square mode**: Does **not** apply to this tab (raw in-game values only).
- **Language**: UI labels are translated via existing `ui.json`; raw entity data keys remain in English.
- **Ordering**: Buildings are ordered by the DataFrame `id` column, ascending.
- **Layout**: 3 building cards per row. Each card has a left panel (image + size/time/road) and a right panel (all remaining tooltip sections).
- **Era selector**: Local to the tab. Default is "All eras". The dropdown lists every era that appears in the selected event's buildings.
- **Event selector**: Local to the tab. The sidebar event filter narrows the available events; if the sidebar has exactly one event selected, the tab pre-selects it.

## 3. Architecture & Data Flow

```text
┌──────────────────────────────────────────────┐
│  foe_buildings/app.py                        │
│  - tab routing                               │
│  - passes df_original + image_manager        │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  foe_buildings/tabs/event_tooltips.py        │
│  render_event_tooltips()                     │
│  - event selector (filtered by sidebar)      │
│  - era selector                              │
│  - build rows of 3 building cards each       │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  foe_buildings/ui/tooltip.py                 │
│  render_building_tooltip()                   │
│  - cached per (building_id, era, lang)       │
│  → List[TooltipSection]                      │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  event_tooltips.py helpers                   │
│  - split size_time_road section              │
│  - aggregate sections into ranges            │
│  - render 2-panel card HTML/CSS              │
└──────────────────────────────────────────────┘
```

## 4. File & Module Structure

### New files

- `foe_buildings/tabs/event_tooltips.py` — Main tab renderer, card layout, and range aggregation helpers.
- `tests/test_event_tooltips.py` — Unit tests for range aggregation and card rendering helpers.

### Modified files

- `foe_buildings/app.py` — Add "Event Tooltips" to the main tab bar and route to the new renderer.
- `foe_buildings/config/session.py` — Add session keys for the tab's selected event and era.
- `foe_buildings/ui/styles/tooltip.css` — Add compact card styles (optional; may use inline styles first).
- `foe_buildings/i18n/locales/en/ui.json` — New UI keys.
- `foe_buildings/i18n/locales/fr/ui.json` — French translations of new keys.

### Untouched

- Scoring engine, AG-Grid logic, and existing Building Details tooltip sub-tab.

## 5. Tab Renderer Structure

Entry point:

```python
def render_event_tooltips(
    df_original: pd.DataFrame,
    selected_events: list[str],
    selected_translated_era: str,
    lang_code: str,
    image_manager,
) -> None:
    ...
```

Responsibilities:

1. **Header** — tab title and event/era selectors.
2. **Event selection** — dropdown populated from `df_original[COL_EVENT].unique()` intersected with the sidebar's `selected_events` (if any). If the sidebar has exactly one event selected, that event is pre-selected; otherwise the dropdown defaults to the first available event.
3. **Era selection** — dropdown with "All eras" plus the sorted distinct eras of the selected event's buildings.
4. **Building list** — filter `df_original` to the selected event, sort by `id` ascending.
5. **Grid** — split buildings into chunks of 3 and render one `st.columns(3)` row per chunk.
6. **Per-card layout** — for each building:
   - Resolve entity from `load_building_entity_lookup()`.
   - Render tooltip sections for each relevant era (cached).
   - In "All eras" mode, aggregate matching rows into ranges.
   - Render a card with left panel (image + size/time/road) and right panel (remaining sections).

## 6. Card Layout

Each building card is a bordered container with two panels side-by-side.

### Left panel (narrow)

- Building image at the top-left, capped to a small width (e.g. 80 px).
- Below the image, the rows from the tooltip's `size_time_road` section:
  - Size (e.g. `3x3`)
  - Construction time (e.g. `20s`)
  - Road requirement (e.g. `Road required` / `No road required`)

### Right panel (wider)

- All remaining tooltip sections rendered compactly without section titles when possible, or with small bold titles when needed for clarity.
- Sections: Provides, Produces, Chain/Set, Ally Rooms, Costs, Traits.
- Random-production groups keep their bordered purple box style but scaled down.

### Responsive behavior

- The card starts as a tight square.
- If the right panel content exceeds the square height, the card grows vertically into a rectangle.
- The row of three cards is top-aligned so cards with different stat counts do not misalign neighbors.

## 7. Era Aggregation Logic

When "All eras" is selected:

1. For each building, render tooltip sections for every era present in the event's building set.
2. Group rows by `(section_key, label, icon_key, suffix, markers)`.
3. For each group:
   - If all values are numeric, compute `min` and `max` and display `min - max`. If min == max, display the single value.
   - If values are non-numeric (e.g. road labels), display the unique values joined by ` / `.
4. Keep section order: Size/Time/Road, Provides, Produces, Chain/Set, Ally Rooms, Costs, Traits.

When a specific era is selected:

1. Render tooltip sections for that era only.
2. No aggregation; values are shown exactly as rendered.

## 8. UI / Tab Integration

In `foe_buildings/app.py`:

```python
tab_names = [
    translations.get_text("building_analysis", lang_code),
    translations.get_text("building_details", lang_code),
    translations.get_text("city_analysis", lang_code),
    translations.get_text("visualizations", lang_code),
    translations.get_text("event_tooltips", lang_code),
]
```

Route:

```python
if st.session_state[SessionKeys.ACTIVE_MAIN_TAB] == 4:
    render_event_tooltips(
        df_original=df_original,
        selected_events=selected_events,
        selected_translated_era=selected_translated_era,
        lang_code=lang_code,
        image_manager=cached_image_manager,
    )
```

New translation keys:

- `event_tooltips`
- `select_event`
- `all_eras`
- `era_range_label` (optional, for the header showing e.g. "SAAB - SAV")
- `no_event_selected`
- `no_buildings_for_event`

## 9. Error Handling & Fallbacks

| Scenario | Behavior |
|---|---|
| No event selected | Show an info message prompting the user to select an event. |
| Sidebar event filter empty | Show all events in the dropdown. |
| Building entity missing from lookup | Render a compact "No tooltip data" placeholder inside that card; other cards still render. |
| Entity exists but has no components | Same as above. |
| Era has no data for a building | Skip that era when aggregating; if no eras have data, show placeholder. |
| Invalid numeric value during aggregation | Treat as non-numeric and join unique string values. |
| Missing translation | Falls back to English via existing i18n logic. |

## 10. Testing Plan

### Unit tests (`tests/test_event_tooltips.py`)

- `aggregate_tooltip_rows()`:
  - Numeric range (`[10, 20, 30]` → `"10 - 30"`).
  - Equal numeric values (`[15, 15]` → `"15"`).
  - Mixed non-numeric values (`["Road", "No road"]` → `"Road / No road"`).
  - Identical non-numeric values (`["Road", "Road"]` → `"Road"`).
- `split_size_time_road_section()`:
  - Extracts size/time/road rows from a sections list.
  - Returns empty list when section is missing.
- `render_event_tooltips()` smoke test:
  - With a sample DataFrame containing 4 buildings for one event, verify 2 rows are produced (3 + 1 cards).

### Manual verification

- Select an event with buildings across multiple eras → "All eras" shows ranges.
- Select a single era → only that era's values appear.
- Switch language → labels translate.
- Resize browser → cards stay at 3 per row on wide layouts.

## 11. Future Improvements

- Add a search box inside the tab to filter event buildings by name.
- Add a "compact / detailed" toggle that hides section titles for even tighter cards.
- Cache the full aggregated "All eras" sections after first computation.
- Allow exporting the event gallery as an image or PDF.

# In-Game Building Tooltip Tab — Design Spec

> Status: Approved for implementation  
> Scope: Add an "In-Game Tooltip" sub-tab inside Building Details that renders building information as close as possible to the Forge of Empires in-game tooltip.

## 1. Goal

Provide a new view in the Building Details tab that displays a building’s stats, production, traits, and metadata the way they appear in-game, rather than as a flat list of database columns. The database breaks combined in-game stats (e.g., `att_def_boost_defender`) into separate columns (e.g., Blue Attack + Blue Defense). This tab reads the original 40 MB building entity JSON from the API and renders values in their original combined form.

## 2. Constraints & Decisions

- **Data source**: Original building entity JSON served at `GET /data/download/building_entity_lookup.json`.
- **Caching**: Download once and cache with `@st.cache_data(ttl=82800)` (same 23-hour TTL used for `/buildings`). The cache is shared across Streamlit sessions and refreshes only when the TTL expires or the user clears it.
- **Per-square mode**: Does **not** apply to the tooltip tab (raw in-game values only).
- **Language**: UI labels are translated via existing `ui.json`; raw entity data keys remain in English.
- **Icons**: Extract combined-stat icons from the Forge Hammer sprite sheet; user will add any missing icons manually.
- **Army stats**: Render combined rows for attacker, defender, and all-army boosts, including GBG/GE/QI variants.
- **Random productions**: Display each possible reward with its drop chance.

## 3. Architecture & Data Flow

```text
┌─────────────────────────────────────┐
│  foe_buildings/data/loader.py       │  load_building_entity_lookup()
│  @st.cache_data(ttl=82800)          │  → Dict[str, dict]
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  foe_buildings/tabs/building_details.py
│  - Select building id from DataFrame column "id"
│  - entity = lookup.get(building_id)
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  foe_buildings/ui/tooltip.py        │  render_building_tooltip(entity, lang)
│  - Size/road/time                   │  → list[TooltipSection]
│  - Provides / Produces              │
│  - Chain / set / ally / traits      │
│  - Costs                            │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Streamlit UI (building_details.py) │
│  st.tabs(["Stats", "In-Game Tooltip"])
└─────────────────────────────────────┘
```

## 4. File & Module Structure

### New files

- `foe_buildings/ui/tooltip.py` — Core tooltip renderer; pure functions from raw entity → structured sections. Includes a private `_render_tooltip_sections()` Streamlit helper.
- `foe_buildings/ui/tooltip_icons.py` — Icon key → local filename mapping; helper to resolve icons for boosts/resources.
- `tests/test_tooltip.py` — Unit tests for renderer, formatting helpers, and icon mapping.

### Modified files

- `foe_buildings/data/loader.py` — Add `load_building_entity_lookup()`.
- `foe_buildings/tabs/building_details.py` — Add sub-tab switcher and wire tooltip renderer.
- `foe_buildings/i18n/locales/en/ui.json` — New UI keys.
- `foe_buildings/i18n/locales/fr/ui.json` — French translations of new keys.
- `assets/icons/` — New combined-stat and context-badge icons.

### Untouched

- `app.py`, scoring engine, AG-Grid logic, and session state.

## 5. Tooltip Renderer Structure

Entry point:

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class TooltipRow:
    icon: Optional[str]      # base64 data URI or None
    label: str
    value: str
    suffix: Optional[str]    # e.g., "when motivated"

@dataclass
class TooltipSection:
    title: Optional[str]
    rows: List[TooltipRow]
    layout: str = "normal"   # normal | multi_col | centered

def render_building_tooltip(entity: dict, lang_code: str) -> List[TooltipSection]:
    ...
```

Rendered sections (in order):

1. **Header** — building name (use the already-translated name from the DataFrame) + image (reuse existing `image_manager`).
2. **Size / Construction / Road** — `components.AllAge.placement.size`, `constructionTime.time`, `streetConnectionRequirement.requiredLevel`.
3. **Provides** — static resources, population, happiness, ranking points, and boosts. The JSON stores individual boosts (`att_boost_attacker`, `def_boost_attacker`, etc.). The renderer groups them into combined rows:
   - `att_def_boost_attacker` = `att_boost_attacker` + `def_boost_attacker` (Red Attack + Red Defense)
   - `att_def_boost_defender` = `att_boost_defender` + `def_boost_defender` (Blue Attack + Blue Defense)
   - `att_def_boost_attacker_defender` = all four base army stats
   - GBG/GE/QI variants are grouped the same way using the feature-prefixed keys (`battleground-att_boost_attacker`, `guild_expedition-att_boost_attacker`, `guild_raids-att_boost_attacker`, etc.) and shown with the matching context badge.
4. **Produces** — iterate `production.options`. Handle:
   - `resources` (coins, supplies, goods, …)
   - `unit`
   - `genericReward`
   - `random` with per-reward drop chances
   - motivation indicators (`onlyWhenMotivated`).
5. **Chain / Set bonuses** — `components.AllAge.chain` and abilities such as `ChainStartAbility`.
6. **Ally rooms** — `components.AllAge.ally.rooms`.
7. **Traits** — flags, unique limit, polish/motivate, plunderable, life support, auto-era.
8. **Costs** — `components.AllAge.buildResourcesRequirement.cost.resources`.

Formatting helpers:

- `format_time(seconds: int) -> str` → `1d 02h 03m`
- `format_range(min, max) -> str` → `10 - 20` when different, `10` when equal
- `percent_suffix(boost_type: str) -> str` → `%` or empty for special resources

## 6. Icon Extraction & Mapping

### Icons to extract from Forge Hammer

From `js/web/productions/images/productions.png`:

- `att_def_boost_attacker.png` (citymap.css offset `-340px 1px`)
- `att_def_boost_defender.png` (citymap.css offset `-362px 1px`)

From `js/web/x_img/`:

- `gbg_badge.png` from `gbg-green.png`
- `ge_badge.png` from `ge.png`
- `qi_badge.png` from `guild_raids.png`

The GBG/GE/QI badge is rendered as a small overlay in the bottom-right corner of the base/combined army icon. If composite rendering is too complex for the first version, a simple side-by-side layout (base icon + badge icon) is acceptable.

### Icons expected from user

If not available in the sprite sheet, the user will add them following this naming convention:

- Base combined icons: `att_def_boost_attacker.png`, `att_def_boost_defender.png`, `att_def_boost_attacker_defender.png`
- Context variants: insert the context slug before the final `.png`:
  - GBG: `att_def_boost_attacker_gbg.png`, `att_def_boost_defender_gbg.png`, `att_def_boost_attacker_defender_gbg.png`
  - GE: `att_def_boost_attacker_ge.png`, `att_def_boost_defender_ge.png`, `att_def_boost_attacker_defender_ge.png`
  - QI: `att_def_boost_attacker_qi.png`, `att_def_boost_defender_qi.png`, `att_def_boost_attacker_defender_qi.png`

### Mapping strategy

`tooltip_icons.py` exposes:

```python
FEATURE_SLUGS = {
    "all": "",
    "battleground": "_gbg",
    "guild_expedition": "_ge",
    "guild_raids": "_qi",
}

BOOST_ICON_MAP = {
    "att_boost_attacker": "red_attack.png",
    "def_boost_attacker": "red_defense.png",
    "att_def_boost_attacker": "att_def_boost_attacker.png",
    "att_def_boost_attacker_defender": "att_def_boost_attacker_defender.png",
    ...
}

def get_boost_icon_filename(boost_type: str, feature: str = "all") -> Optional[str]:
    """Return the local icon filename for a boost key + feature context."""
    ...

def resolve_icon(icon_name: str) -> Optional[str]:
    """Return a base64 data URI for the given icon filename, or None."""
    ...
```

If an icon is missing, the renderer omits the image and shows text only.

## 7. UI / Tab Integration

Inside `render_building_details()`:

```python
tab_stats, tab_tooltip = st.tabs([
    translations.get_text("complete_stats_table", lang_code),
    translations.get_text("in_game_tooltip", lang_code),
])

with tab_stats:
    # existing complete stats table
    ...

with tab_tooltip:
    lookup = data_loader.load_building_entity_lookup()
    building_id = building_data.get("id")
    entity = lookup.get(building_id)
    if entity:
        sections = tooltip_renderer.render_building_tooltip(entity, lang_code)
        _render_tooltip_sections(sections, building_data, image_manager, lang_code)
    else:
        st.info(translations.get_text("no_tooltip_data", lang_code))
```

Layout:

- Left column: building image.
- Right column: stacked tooltip sections.
- Each section rendered as a bordered container.

New translation keys:

- `in_game_tooltip`
- `no_tooltip_data`
- `provides`
- `produces`
- `traits`
- `costs`
- `size_time_road`
- `when_motivated`
- `road_required`
- `road_required_2`
- `no_road_required`
- `size_format` (e.g., `{width}x{length}`)

## 8. Error Handling & Fallbacks

| Scenario | Behavior |
|---|---|
| JSON download fails | `load_building_entity_lookup()` returns `{}`; tooltip tab shows warning; stats table still works. |
| Building ID missing from JSON | Tooltip tab shows `no_tooltip_data` info message. |
| Malformed nested entity data | Renderer uses `.get()` and guards; uncaught exceptions are caught at tab level and shown as `st.error`. |
| Missing icon | Text label shown without image. |
| Missing translation | Falls back to English via existing i18n logic. |

## 9. Testing Plan

### Unit tests (`tests/test_tooltip.py`)

- Icon mapping for every boost key (base, GBG, GE, QI, combined).
- `format_time` for seconds, minutes, hours, days, and zero.
- `format_range` for equal and different values.
- Renderer section extraction on sample entities for:
  - static resources
  - production options
  - random production with drop chances
  - chain bonuses
  - missing optional fields

### Integration

- Add a raw building entity fixture in `conftest.py`.
- Verify `render_building_tooltip()` returns sections without raising.

### Manual verification

- Select a building with army boosts → combined rows visible.
- Select a building with random productions → drop chances visible.
- Switch language → labels translate.
- Disconnect JSON → graceful fallback message.

## 10. Future Improvements

- **Approach 3 (API endpoint)**: Add `/data/building-entity/{building_id}` to the backend so the Streamlit app can fetch a single building entity instead of the full 40 MB file.
- Extend the renderer to show great-building-specific details if ever needed.
- Add era-slider support for multi-era buildings (show min/max ranges).

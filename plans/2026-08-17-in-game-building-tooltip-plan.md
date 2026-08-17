# In-Game Building Tooltip Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an "In-Game Tooltip" sub-tab to Building Details that renders a building's raw entity data from the API as an in-game-style tooltip.

**Architecture:** Fetch `building_entity_lookup.json` once and cache it with Streamlit's `@st.cache_data`. Build a pure Python renderer (`foe_buildings/ui/tooltip.py`) that converts raw entity dicts into structured sections. Add icon mapping (`foe_buildings/ui/tooltip_icons.py`) and wire the renderer into `foe_buildings/tabs/building_details.py` behind a new sub-tab.

**Tech Stack:** Python 3.12, Streamlit 1.55, Pandas, Pillow, Requests, Pytest.

## Global Constraints

- Data source: `GET /data/download/building_entity_lookup.json`
- Cache TTL: 82800 seconds (23 hours), same as existing `/buildings` loader
- Per-square mode does NOT apply to tooltip tab
- UI labels translated via `foe_buildings/i18n/locales/{en,fr}/ui.json`
- New icons go in `assets/icons/`
- All code follows existing style (ruff, pre-commit)
- Tests run with `pytest tests/`

---

### Task 1: Add Building Entity Lookup Loader

**Files:**
- Modify: `foe_buildings/data/loader.py`
- Test: `tests/test_tooltip_loader.py`

**Interfaces:**
- Consumes: `_make_request()` from `foe_buildings/data/loader.py`
- Produces: `load_building_entity_lookup() -> Dict[str, Any]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tooltip_loader.py`:

```python
from unittest.mock import patch

from foe_buildings.data import loader


def test_load_building_entity_lookup_returns_dict():
    with patch.object(loader, "_make_request") as mock_make_request:
        mock_make_request.return_value = {"B1": {"name": "Building One"}}
        result = loader.load_building_entity_lookup()
        assert result == {"B1": {"name": "Building One"}}
        mock_make_request.assert_called_once_with(
            "/data/download/building_entity_lookup.json", fatal=False
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tooltip_loader.py -v`

Expected: FAIL with `AttributeError: module 'foe_buildings.data.loader' has no attribute 'load_building_entity_lookup'`

- [ ] **Step 3: Write minimal implementation**

Ensure `foe_buildings/data/loader.py` imports `Any`:

```python
from typing import Dict, Any, Optional
```

Add after `get_forgehx_data`:

```python
@st.cache_data(ttl=_CACHE_TTL)
def load_building_entity_lookup() -> Dict[str, Any]:
    """Fetch the raw building entity lookup JSON from the API.

    Returns a dict mapping building ID (e.g. ``W_MultiAge_HAL19A1``) to the
    original game entity dict. Cached for 23 hours to match the daily data
    refresh cadence.

    Returns:
        Dict[str, Any]: empty dict if the request fails or returns nothing.
    """
    data = _make_request("/data/download/building_entity_lookup.json", fatal=False)
    if not data:
        return {}
    return data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tooltip_loader.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add foe_buildings/data/loader.py tests/test_tooltip_loader.py
git commit -m "feat(tooltip): add cached loader for building entity lookup JSON"
```

---

### Task 2: Extract Combined-Stat Icons from Forge Hammer

**Files:**
- Create: `scripts/extract_tooltip_icons.py`
- Create: `assets/icons/att_def_boost_attacker.png`
- Create: `assets/icons/att_def_boost_defender.png`
- Create: `assets/icons/gbg_badge.png`
- Create: `assets/icons/ge_badge.png`
- Create: `assets/icons/qi_badge.png`

**Interfaces:**
- Consumes: Forge Hammer sprite sheet and badge images
- Produces: PNG files in `assets/icons/`

- [ ] **Step 1: Create extraction script**

Create `scripts/extract_tooltip_icons.py`:

```python
from pathlib import Path
from PIL import Image

FORGE_HAMMER = Path.home() / "Github" / "forge-hammer"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "icons"
OUTPUT.mkdir(parents=True, exist_ok=True)

SPRITE = FORGE_HAMMER / "js" / "web" / "productions" / "images" / "productions.png"
sprite = Image.open(SPRITE).convert("RGBA")

ICONS = [
    ("att_def_boost_attacker.png", 340, 1, 22, 24),
    ("att_def_boost_defender.png", 362, 1, 22, 24),
]

for filename, left, top, width, height in ICONS:
    box = (left, top, left + width, top + height)
    icon = sprite.crop(box)
    icon.save(OUTPUT / filename)
    print(f"Saved {filename}")

BADGES = [
    ("gbg_badge.png", FORGE_HAMMER / "js" / "web" / "x_img" / "gbg-green.png"),
    ("ge_badge.png", FORGE_HAMMER / "js" / "web" / "x_img" / "ge.png"),
    ("qi_badge.png", FORGE_HAMMER / "js" / "web" / "x_img" / "guild_raids.png"),
]

for filename, src in BADGES:
    img = Image.open(src).convert("RGBA")
    img.thumbnail((16, 16))
    img.save(OUTPUT / filename)
    print(f"Saved {filename}")
```

- [ ] **Step 2: Run the script and verify**

Run:

```bash
uv run python scripts/extract_tooltip_icons.py
ls -la assets/icons/att_def_boost_attacker.png assets/icons/att_def_boost_defender.png assets/icons/gbg_badge.png assets/icons/ge_badge.png assets/icons/qi_badge.png
```

Expected: All five files exist and are non-empty.

- [ ] **Step 3: Commit**

```bash
git add scripts/extract_tooltip_icons.py assets/icons/*.png
git commit -m "feat(tooltip): extract combined-stat icons from Forge Hammer"
```

---

### Task 3: Create Tooltip Icon Mapping Module

**Files:**
- Create: `foe_buildings/ui/tooltip_icons.py`
- Test: `tests/test_tooltip_icons.py`

**Interfaces:**
- Consumes: `foe_buildings.ui.grid.get_icon_base64`
- Produces: `FEATURE_SLUGS`, `BOOST_ICON_MAP`, `get_boost_icon_filename(...)`, `resolve_icon(...)`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tooltip_icons.py`:

```python
from foe_buildings.ui import tooltip_icons


def test_feature_slugs():
    assert tooltip_icons.FEATURE_SLUGS["battleground"] == "_gbg"
    assert tooltip_icons.FEATURE_SLUGS["guild_expedition"] == "_ge"
    assert tooltip_icons.FEATURE_SLUGS["guild_raids"] == "_qi"


def test_get_boost_icon_filename_base():
    assert tooltip_icons.get_boost_icon_filename("att_boost_attacker") == "red_attack.png"
    assert tooltip_icons.get_boost_icon_filename("def_boost_attacker") == "red_defense.png"
    assert tooltip_icons.get_boost_icon_filename("att_boost_defender") == "blue_attack.png"
    assert tooltip_icons.get_boost_icon_filename("def_boost_defender") == "blue_defense.png"


def test_get_boost_icon_filename_combined():
    assert tooltip_icons.get_boost_icon_filename("att_def_boost_attacker") == "att_def_boost_attacker.png"
    assert tooltip_icons.get_boost_icon_filename("att_def_boost_defender") == "att_def_boost_defender.png"


def test_get_boost_icon_filename_with_feature():
    assert tooltip_icons.get_boost_icon_filename("att_boost_attacker", "battleground") == "red_gbg_attack.png"
    assert tooltip_icons.get_boost_icon_filename("att_def_boost_attacker", "battleground") == "att_def_boost_attacker_gbg.png"


def test_get_boost_icon_filename_unknown():
    assert tooltip_icons.get_boost_icon_filename("unknown_boost") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tooltip_icons.py -v`

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Create `foe_buildings/ui/tooltip_icons.py`:

```python
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
    return f"{name}{slug}.{ext}"


def resolve_icon(icon_name: Optional[str]) -> Optional[str]:
    """Return a base64 data URI for the given icon filename, or None."""
    if not icon_name:
        return None
    base64_str = get_icon_base64(icon_name.replace(".png", ""))
    if base64_str:
        return f"data:image/png;base64,{base64_str}"
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tooltip_icons.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add foe_buildings/ui/tooltip_icons.py tests/test_tooltip_icons.py
git commit -m "feat(tooltip): add icon mapping for in-game boosts"
```

---

### Task 4: Add Formatting Helpers

**Files:**
- Modify: `foe_buildings/ui/tooltip.py`
- Test: `tests/test_tooltip_formatting.py`

**Interfaces:**
- Produces: `format_time(seconds)`, `format_range(min_value, max_value)`, `percent_suffix(boost_type)`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tooltip_formatting.py`:

```python
from foe_buildings.ui.tooltip import format_range, format_time, percent_suffix


def test_format_time_seconds():
    assert format_time(45) == "45s"


def test_format_time_minutes():
    assert format_time(125) == "2m 5s"


def test_format_time_hours():
    assert format_time(3665) == "1h 1m 5s"


def test_format_time_days():
    assert format_time(90061) == "1d 1h 1m 1s"


def test_format_time_zero():
    assert format_time(0) == "0s"


def test_format_range_equal():
    assert format_range(10, 10) == "10"


def test_format_range_different():
    assert format_range(10, 20) == "10 - 20"


def test_percent_suffix_normal():
    assert percent_suffix("att_boost_attacker") == "%"


def test_percent_suffix_special():
    assert percent_suffix("guild_raids_action_points_collection") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tooltip_formatting.py -v`

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Create `foe_buildings/ui/tooltip.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tooltip_formatting.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add foe_buildings/ui/tooltip.py tests/test_tooltip_formatting.py
git commit -m "feat(tooltip): add time, range, and percent formatting helpers"
```

---

### Task 5: Implement Size / Road / Time Section

**Files:**
- Modify: `foe_buildings/ui/tooltip.py`
- Test: `tests/test_tooltip_size_time.py`

**Interfaces:**
- Consumes: `format_time()`
- Produces: `_render_size_time_road(entity, lang_code) -> List[TooltipRow]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tooltip_size_time.py`:

```python
from foe_buildings.ui.tooltip import _render_size_time_road


def test_size_time_road_all_data():
    entity = {
        "components": {
            "AllAge": {
                "placement": {"size": {"x": 4, "y": 3}},
                "constructionTime": {"time": 3665},
                "streetConnectionRequirement": {"requiredLevel": 1},
            }
        }
    }
    rows = _render_size_time_road(entity, "en")
    assert len(rows) == 3
    assert "3x4" in rows[0].value
    assert "1h 1m 5s" in rows[1].value


def test_size_time_road_minimal():
    entity = {"components": {"AllAge": {"placement": {"size": {"x": 2, "y": 2}}}}}
    rows = _render_size_time_road(entity, "en")
    assert len(rows) == 1
    assert "2x2" in rows[0].value
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tooltip_size_time.py -v`

Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

Add to `foe_buildings/ui/tooltip.py`:

```python
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from foe_buildings import i18n as translations


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tooltip_size_time.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add foe_buildings/ui/tooltip.py tests/test_tooltip_size_time.py
git commit -m "feat(tooltip): add size/construction/road section renderer"
```

---

### Task 6: Implement Provides Section with Combined Army Boosts

**Files:**
- Modify: `foe_buildings/ui/tooltip.py`
- Test: `tests/test_tooltip_provides.py`

**Interfaces:**
- Consumes: `tooltip_icons.get_boost_icon_filename`, `tooltip_icons.resolve_icon`, `percent_suffix`
- Produces: `_render_provides(entity, lang_code) -> List[TooltipRow]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tooltip_provides.py`:

```python
from foe_buildings.ui.tooltip import _render_provides


def test_provides_combined_army_boosts():
    entity = {
        "components": {
            "AllAge": {
                "boosts": {
                    "boosts": [
                        {"type": "att_boost_attacker", "value": 15},
                        {"type": "def_boost_attacker", "value": 20},
                        {"type": "att_boost_defender", "value": 10},
                        {"type": "def_boost_defender", "value": 12},
                    ]
                }
            }
        }
    }
    rows = _render_provides(entity, "en")
    labels = [r.label for r in rows]
    assert "Att/Def Attacker" in labels
    assert "Att/Def Defender" in labels
    attacker_row = next(r for r in rows if r.label == "Att/Def Attacker")
    assert attacker_row.value == "35%"


def test_provides_static_resources():
    entity = {
        "components": {
            "AllAge": {
                "staticResources": {"resources": {"resources": {"medals": 100}}}
            }
        }
    }
    rows = _render_provides(entity, "en")
    assert any(r.label == "medals" and r.value == "100" for r in rows)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tooltip_provides.py -v`

Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

Add to `foe_buildings/ui/tooltip.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tooltip_provides.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add foe_buildings/ui/tooltip.py tests/test_tooltip_provides.py
git commit -m "feat(tooltip): add provides section with combined army boosts"
```

---

### Task 7: Implement Produces Section

**Files:**
- Modify: `foe_buildings/ui/tooltip.py`
- Test: `tests/test_tooltip_produces.py`

**Interfaces:**
- Consumes: `format_range`, `resolve_icon`
- Produces: `_render_produces(entity, lang_code) -> List[TooltipRow]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tooltip_produces.py`:

```python
from foe_buildings.ui.tooltip import _render_produces


def test_produces_resources():
    entity = {
        "components": {
            "AllAge": {
                "production": {
                    "options": [
                        {
                            "time": 3600,
                            "products": [
                                {
                                    "type": "resources",
                                    "playerResources": {"resources": {"coins": 100}},
                                }
                            ],
                        }
                    ]
                }
            }
        }
    }
    rows = _render_produces(entity, "en")
    assert any("100" in r.value for r in rows)


def test_produces_random():
    entity = {
        "components": {
            "AllAge": {
                "production": {
                    "options": [
                        {
                            "time": 86400,
                            "products": [
                                {
                                    "type": "random",
                                    "products": [
                                        {
                                            "product": {
                                                "type": "resources",
                                                "playerResources": {"resources": {"goods": 10}},
                                            },
                                            "dropChance": 0.5,
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                }
            }
        }
    }
    rows = _render_produces(entity, "en")
    assert any("50%" in r.value for r in rows)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tooltip_produces.py -v`

Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

Add to `foe_buildings/ui/tooltip.py`:

```python
def _render_resources(resources: Dict[str, Any], lang_code: str) -> List[TooltipRow]:
    rows = []
    for resource, amount in (resources or {}).items():
        if amount:
            rows.append(
                TooltipRow(
                    icon=resolve_icon(f"{resource}.png"),
                    label=translations.translate_column(resource, lang_code),
                    value=str(amount),
                )
            )
    return rows


def _render_product(product: Dict[str, Any], lookup: Dict[str, Any], lang_code: str) -> List[TooltipRow]:
    """Render a single product. Returns zero or more rows."""
    rows = []
    suffix = translations.get_text("when_motivated", lang_code) if product.get("onlyWhenMotivated") else None
    ptype = product.get("type")

    if ptype == "resources":
        rows.extend(_render_resources(product.get("playerResources", {}).get("resources"), lang_code))
    elif ptype == "guildResources":
        rows.extend(_render_resources(product.get("guildResources", {}).get("resources"), lang_code))
    elif ptype == "unit":
        amount = product.get("amount", 0)
        if amount:
            unit_type = product.get("unitTypeId", "military")
            rows.append(
                TooltipRow(
                    icon=resolve_icon(f"{unit_type}.png"),
                    label=translations.translate_column(unit_type, lang_code),
                    value=str(amount),
                    suffix=suffix,
                )
            )
    elif ptype == "random":
        for random_product in product.get("products", []):
            sub = random_product.get("product", {})
            chance = random_product.get("dropChance", 0)
            sub_rows = _render_product(sub, lookup, lang_code)
            for row in sub_rows:
                row.value = f"{row.value} ({int(chance * 100)}%)"
                rows.append(row)

    for row in rows:
        if suffix and not row.suffix:
            row.suffix = suffix
    return rows


def _render_produces(entity: Dict[str, Any], lang_code: str) -> List[TooltipRow]:
    """Render the 'Produces' section."""
    rows = []
    components = entity.get("components", {})
    all_age = components.get("AllAge", {})
    lookup = all_age.get("lookup", {}).get("rewards", {})
    options = all_age.get("production", {}).get("options", [])

    for option in options:
        time_label = format_time(option.get("time", 0))
        for product in option.get("products", []):
            for row in _render_product(product, lookup, lang_code):
                row.value = f"{row.value} in {time_label}"
                rows.append(row)
    return rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tooltip_produces.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add foe_buildings/ui/tooltip.py tests/test_tooltip_produces.py
git commit -m "feat(tooltip): add produces section with random production support"
```

---

### Task 8: Implement Chain, Set, Ally, Traits, and Costs Sections

**Files:**
- Modify: `foe_buildings/ui/tooltip.py`
- Test: `tests/test_tooltip_misc_sections.py`

**Interfaces:**
- Produces: `_render_chain_set(...)`, `_render_ally_rooms(...)`, `_render_traits(...)`, `_render_costs(...)`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tooltip_misc_sections.py`:

```python
from foe_buildings.ui.tooltip import _render_costs, _render_traits


def test_traits_unique():
    entity = {
        "components": {
            "AllAge": {
                "cityLimit": {"buildingFamily": "MyFamily"}
            }
        }
    }
    rows = _render_traits(entity, "en")
    assert any("Unique" in r.label for r in rows)


def test_costs():
    entity = {
        "components": {
            "AllAge": {
                "buildResourcesRequirement": {
                    "cost": {"resources": {"supplies": 500, "coins": 1000}}
                }
            }
        }
    }
    rows = _render_costs(entity, "en")
    assert any(r.value == "1000" for r in rows)
    assert any(r.value == "500" for r in rows)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tooltip_misc_sections.py -v`

Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

Add to `foe_buildings/ui/tooltip.py`:

```python
def _render_chain_set(entity: Dict[str, Any], lang_code: str) -> List[TooltipRow]:
    rows = []
    chain = entity.get("components", {}).get("AllAge", {}).get("chain")
    if chain:
        chain_id = chain.get("chainId")
        if chain_id:
            rows.append(
                TooltipRow(
                    icon=resolve_icon(f"{chain_id}.png"),
                    label=translations.get_text("chain", lang_code),
                    value=chain_id,
                )
            )
    return rows


def _render_ally_rooms(entity: Dict[str, Any], lang_code: str) -> List[TooltipRow]:
    rows = []
    rooms = entity.get("components", {}).get("AllAge", {}).get("ally", {}).get("rooms", [])
    for room in rooms:
        rows.append(
            TooltipRow(
                icon=resolve_icon("ally_room.png"),
                label=translations.get_text("ally_room", lang_code),
                value=room.get("allyType", ""),
            )
        )
    return rows


def _render_traits(entity: Dict[str, Any], lang_code: str) -> List[TooltipRow]:
    rows = []
    all_age = entity.get("components", {}).get("AllAge", {})
    if all_age.get("cityLimit"):
        rows.append(
            TooltipRow(
                icon=None,
                label=translations.get_text("trait", lang_code),
                value=translations.get_text("unique_building", lang_code),
            )
        )

    flags = all_age.get("flags", {}).get("flags", 0)
    if flags & 4:
        rows.append(
            TooltipRow(
                icon=None,
                label=translations.get_text("trait", lang_code),
                value=translations.get_text("upgrades_automatically", lang_code),
            )
        )
    if flags & 32:
        rows.append(
            TooltipRow(
                icon=None,
                label=translations.get_text("trait", lang_code),
                value=translations.get_text("fsp_disabled", lang_code),
            )
        )
    return rows


def _render_costs(entity: Dict[str, Any], lang_code: str) -> List[TooltipRow]:
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
            rows.append(
                TooltipRow(
                    icon=resolve_icon(f"{resource}.png"),
                    label=translations.translate_column(resource, lang_code),
                    value=str(amount),
                )
            )
    return rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tooltip_misc_sections.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add foe_buildings/ui/tooltip.py tests/test_tooltip_misc_sections.py
git commit -m "feat(tooltip): add chain, ally, traits, and costs sections"
```

---

### Task 9: Assemble Full Tooltip Renderer

**Files:**
- Modify: `foe_buildings/ui/tooltip.py`
- Test: `tests/test_tooltip_full.py`

**Interfaces:**
- Produces: `render_building_tooltip(entity, lang_code) -> List[TooltipSection]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tooltip_full.py`:

```python
from foe_buildings.ui.tooltip import render_building_tooltip


def test_render_building_tooltip_returns_sections():
    entity = {
        "name": "Test Building",
        "components": {
            "AllAge": {
                "placement": {"size": {"x": 3, "y": 2}},
                "production": {
                    "options": [
                        {
                            "time": 3600,
                            "products": [
                                {"type": "resources", "playerResources": {"resources": {"coins": 10}}}
                            ],
                        }
                    ]
                },
            }
        },
    }
    sections = render_building_tooltip(entity, "en")
    titles = [s.title for s in sections]
    assert "Size" in titles or "Road" in titles or any(t is not None for t in titles)
    assert len(sections) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tooltip_full.py -v`

Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

Add to `foe_buildings/ui/tooltip.py`:

```python
@dataclass
class TooltipSection:
    title: Optional[str]
    rows: List[TooltipRow]
    layout: str = "normal"


def render_building_tooltip(entity: Dict[str, Any], lang_code: str) -> List[TooltipSection]:
    """Render a full in-game-style tooltip from a raw building entity."""
    sections = []

    size_rows = _render_size_time_road(entity, lang_code)
    if size_rows:
        sections.append(
            TooltipSection(title=translations.get_text("size_time_road", lang_code), rows=size_rows)
        )

    provides = _render_provides(entity, lang_code)
    if provides:
        sections.append(
            TooltipSection(title=translations.get_text("provides", lang_code), rows=provides)
        )

    produces = _render_produces(entity, lang_code)
    if produces:
        sections.append(
            TooltipSection(title=translations.get_text("produces", lang_code), rows=produces)
        )

    chain_rows = _render_chain_set(entity, lang_code)
    if chain_rows:
        sections.append(
            TooltipSection(title=translations.get_text("chain_set", lang_code), rows=chain_rows)
        )

    ally_rows = _render_ally_rooms(entity, lang_code)
    if ally_rows:
        sections.append(
            TooltipSection(title=translations.get_text("ally_rooms", lang_code), rows=ally_rows)
        )

    costs = _render_costs(entity, lang_code)
    if costs:
        sections.append(
            TooltipSection(title=translations.get_text("costs", lang_code), rows=costs)
        )

    traits = _render_traits(entity, lang_code)
    if traits:
        sections.append(
            TooltipSection(title=translations.get_text("traits", lang_code), rows=traits)
        )

    return sections
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tooltip_full.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add foe_buildings/ui/tooltip.py tests/test_tooltip_full.py
git commit -m "feat(tooltip): assemble full building tooltip renderer"
```

---

### Task 10: Add Translations

**Files:**
- Modify: `foe_buildings/i18n/locales/en/ui.json`
- Modify: `foe_buildings/i18n/locales/fr/ui.json`

**Interfaces:**
- Produces: translated strings for all new UI keys.

- [ ] **Step 1: Add English translations**

Insert into `foe_buildings/i18n/locales/en/ui.json` (keep alphabetically sorted):

```json
    "ally_rooms": "Ally Rooms",
    "att_def_boost_attacker": "Att/Def Attacker",
    "att_def_boost_attacker_defender": "Att/Def Attacker/Defender",
    "att_def_boost_defender": "Att/Def Defender",
    "chain_set": "Chain / Set",
    "construction_time": "Construction Time",
    "costs": "Costs",
    "fsp_disabled": "Cannot be accelerated by Forge Points",
    "in_game_tooltip": "In-Game Tooltip",
    "no_road_required": "No road required",
    "no_tooltip_data": "No raw tooltip data available for this building.",
    "produces": "Produces",
    "provides": "Provides",
    "road": "Road",
    "road_required": "Road required",
    "road_required_2": "Street required",
    "size": "Size",
    "size_time_road": "Size / Time / Road",
    "traits": "Traits",
    "unique_building": "Unique building",
    "upgrades_automatically": "Upgrades automatically to current era",
    "when_motivated": "when motivated",
```

- [ ] **Step 2: Add French translations**

Insert into `foe_buildings/i18n/locales/fr/ui.json`:

```json
    "ally_rooms": "Salles d'alliés",
    "att_def_boost_attacker": "Att/Déf Attaquant",
    "att_def_boost_attacker_defender": "Att/Déf Attaquant/Défenseur",
    "att_def_boost_defender": "Att/Déf Défenseur",
    "chain_set": "Chaîne / Ensemble",
    "construction_time": "Temps de construction",
    "costs": "Coûts",
    "fsp_disabled": "Ne peut pas être accéléré par points de forge",
    "in_game_tooltip": "Infobulle en jeu",
    "no_road_required": "Aucune route requise",
    "no_tooltip_data": "Aucune donnée brute d'infobulle disponible pour ce bâtiment.",
    "produces": "Produit",
    "provides": "Fournit",
    "road": "Route",
    "road_required": "Route requise",
    "road_required_2": "Rue requise",
    "size": "Taille",
    "size_time_road": "Taille / Temps / Route",
    "traits": "Traits",
    "unique_building": "Bâtiment unique",
    "upgrades_automatically": "Évolue automatiquement vers l'ère actuelle",
    "when_motivated": "lorsque motivé",
```

- [ ] **Step 3: Validate JSON**

Run:

```bash
python -m json.tool foe_buildings/i18n/locales/en/ui.json > /dev/null
python -m json.tool foe_buildings/i18n/locales/fr/ui.json > /dev/null
```

Expected: No output (valid JSON).

- [ ] **Step 4: Commit**

```bash
git add foe_buildings/i18n/locales/en/ui.json foe_buildings/i18n/locales/fr/ui.json
git commit -m "i18n(tooltip): add English and French tooltip translations"
```

---

### Task 11: Wire Tooltip into Building Details Tab

**Files:**
- Modify: `foe_buildings/tabs/building_details.py`
- Test: Manual / smoke test

**Interfaces:**
- Consumes: `data_loader.load_building_entity_lookup()`, `tooltip.render_building_tooltip()`
- Produces: UI rendering of the new sub-tab.

- [ ] **Step 1: Add imports**

At the top of `foe_buildings/tabs/building_details.py`, add:

```python
from foe_buildings.data import loader as data_loader
from foe_buildings.ui import tooltip as tooltip_renderer
```

- [ ] **Step 2: Add helper to render sections**

Add inside `render_building_details` (or as a module-level helper):

```python
def _render_tooltip_sections(sections, lang_code):
    for section in sections:
        with st.container():
            if section.title:
                st.markdown(f"**{section.title}**")
            for row in section.rows:
                icon_html = (
                    f'<img src="{row.icon}" style="width:20px;height:20px;vertical-align:middle;margin-right:6px;">'
                    if row.icon else ""
                )
                suffix = f" <em>{row.suffix}</em>" if row.suffix else ""
                st.markdown(
                    f"{icon_html}{row.label}: **{row.value}**{suffix}",
                    unsafe_allow_html=True,
                )
```

- [ ] **Step 3: Add sub-tabs**

Replace the single `st.subheader(...)` and stats table block with tabs. Locate where `_render_stats_table` is called and wrap it:

```python
        tab_stats, tab_tooltip = st.tabs([
            translations.get_text("complete_stats_table", lang_code),
            translations.get_text("in_game_tooltip", lang_code),
        ])

        with tab_stats:
            # existing complete stats table rendering
            ...

        with tab_tooltip:
            lookup = data_loader.load_building_entity_lookup()
            building_id = building_data.get("id")
            entity = lookup.get(building_id)
            if entity:
                sections = tooltip_renderer.render_building_tooltip(entity, lang_code)
                _render_tooltip_sections(sections, lang_code)
            else:
                st.info(translations.get_text("no_tooltip_data", lang_code))
```

Keep the existing image layout (left table / right image) inside the `tab_stats` block.

- [ ] **Step 4: Run the app**

Run:

```bash
uv run streamlit run app.py
```

Manually verify:
- Select a building.
- The "In-Game Tooltip" tab appears.
- Combined army rows are visible for buildings with army boosts.
- Random production drop chances display.

- [ ] **Step 5: Commit**

```bash
git add foe_buildings/tabs/building_details.py
git commit -m "feat(tooltip): add in-game tooltip sub-tab to building details"
```

---

## Plan Self-Review

- [ ] **Spec coverage**: Each section of the design spec maps to a task:
  - JSON loader → Task 1
  - Icons → Task 2
  - Icon mapping → Task 3
  - Formatting helpers → Task 4
  - Size/road/time → Task 5
  - Provides (combined boosts) → Task 6
  - Produces (random) → Task 7
  - Chain/set/ally/traits/costs → Task 8
  - Full renderer assembly → Task 9
  - Translations → Task 10
  - UI integration → Task 11
- [ ] **Placeholder scan**: No TBD/TODO placeholders; every step includes code or exact commands.
- [ ] **Type consistency**: `TooltipRow` and `TooltipSection` dataclasses are defined in Task 5 and reused in Tasks 6–11. `render_building_tooltip` signature is consistent. `load_building_entity_lookup()` returns `Dict[str, Any]`.

---

## Execution Handoff

Plan complete and saved to `plans/2026-08-17-in-game-building-tooltip-plan.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — I execute tasks in this session using the executing-plans skill, with checkpoints for review.

Which approach do you prefer?

# Tooltip Icon and Production Presentation Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render the In-Game Tooltip with Forge Hammer-compatible exact-key icons, compact icon/value statistics, consolidated production durations, and distinct random-production pools.

**Architecture:** Load the complete ForgeHX path/hash map behind the existing API cache, then resolve raw game keys through Forge Hammer's ordered candidate paths with local files as fallbacks. Keep tooltip data extraction separate from HTML presentation by adding explicit icon references, semantic/quantitative row kinds, production timing metadata, and random-production groups.

**Tech Stack:** Python 3, Streamlit, requests, pytest, Ruff, mypy, ForgeHX path/hash data, GitNexus.

## Global Constraints

- Use `docs/superpowers/specs/2026-08-17-tooltip-icon-production-redesign-design.md` as the source of truth.
- Do not use `productions.png` for building-tooltip icons.
- Preserve raw icon keys until the Forge Hammer-compatible resolver boundary.
- Quantitative Provides, Produces, Boosts, and Costs rows show icon plus value without a visible stat name.
- Semantic road, trait, ally-room, chain, and set rows retain concise translated text.
- A single production duration appears only in `Produces (<duration>)`; mixed durations appear per row or random group.
- Each raw random product remains a separate styled group with independent probabilities.
- ForgeHX and icon failures degrade to local assets and then a neutral marker without stopping tooltip rendering.
- The current API exposes no `unit_types` metadata and raw building products contain no `unitClass`. Resolve ordinary unit IDs as exact ForgeHX keys first, then use the generic `military` local fallback; keep Forge Hammer's deterministic `rogue` and champion-to-`chivalry` mappings.
- Add no runtime dependencies.
- Preserve unrelated user changes in `AGENTS.md`, `CLAUDE.md`, and `foe_buildings/config/constants.py`.
- Before editing a symbol, run GitNexus upstream impact analysis and report LOW/MEDIUM risk or warn before HIGH/CRITICAL edits.
- Before every commit, stage only the task's files and run GitNexus change detection with `scope="staged"`.

---

### Task 1: Expose the complete cached ForgeHX asset map

**Files:**
- Modify: `foe_buildings/data/loader.py:153-171,217-222`
- Modify: `tests/test_tooltip_loader.py`

**Interfaces:**
- Consumes: `_make_request(endpoint: str, params: Optional[Dict] = None, fatal: bool = True, timeout: int = _API_TIMEOUT) -> Optional[Any]`
- Produces: `load_forgehx_asset_map() -> Dict[str, str]`
- Preserves: `get_forgehx_data() -> Dict[str, str]` as the city-building-only view used by `BuildingImageManager`

- [ ] **Step 1: Run pre-edit impact analysis**

Run GitNexus upstream impact for `get_forgehx_data` and `clear_cache` in
`foe_buildings/data/loader.py`. Record direct callers and affected flows in
`tasks/todo.md`; stop and warn before editing if either risk is HIGH or CRITICAL.

- [ ] **Step 2: Write failing full-map and compatibility tests**

Add these contract tests to `tests/test_tooltip_loader.py`:

```python
def test_load_forgehx_asset_map_keeps_all_asset_paths():
    payload = {
        "/shared/icons/money.png": "money-hash",
        "/shared/icons/icon_unique_building.png": "trait-hash",
        "/city/buildings/W_SS_Test.png": "building-hash",
    }
    with patch.object(loader, "_make_request", return_value=payload) as request:
        result = loader.load_forgehx_asset_map.__wrapped__()

    assert result == payload
    request.assert_called_once_with("/data/forgehx", fatal=False)


def test_load_forgehx_asset_map_rejects_non_mapping_payload():
    with patch.object(loader, "_make_request", return_value=["bad"]):
        assert loader.load_forgehx_asset_map.__wrapped__() == {}


def test_get_forgehx_data_remains_building_only():
    payload = {
        "/shared/icons/money.png": "money-hash",
        "/city/buildings/W_SS_Test.png": "building-hash",
        "/city/buildings/textures/W_Test.png": "texture-hash",
    }
    with patch.object(loader, "load_forgehx_asset_map", return_value=payload):
        result = loader.get_forgehx_data.__wrapped__()

    assert result == {"/city/buildings/W_SS_Test.png": "building-hash"}
```

Extend the cache test so both ForgeHX caches are invalidated:

```python
def test_clear_cache_invalidates_full_forgehx_map():
    with patch.object(loader.load_forgehx_asset_map, "clear") as clear:
        loader.clear_cache()
    clear.assert_called_once_with()
```

- [ ] **Step 3: Run the tests and verify RED**

Run:

```bash
.venv/bin/pytest -q tests/test_tooltip_loader.py
```

Expected: failures because `load_forgehx_asset_map` does not exist and
`get_forgehx_data` still fetches/filter the endpoint itself.

- [ ] **Step 4: Implement the minimal cached full-map loader**

Add this boundary to `foe_buildings/data/loader.py` and derive the legacy filtered
view from it:

```python
@st.cache_data(ttl=_CACHE_TTL)
def load_forgehx_asset_map() -> Dict[str, str]:
    """Return the complete ForgeHX asset-path to cache-hash mapping."""
    data = _make_request("/data/forgehx", fatal=False)
    if not isinstance(data, dict):
        if data is not None:
            logger.warning(
                "Unexpected ForgeHX response type: %s", type(data).__name__
            )
        return {}
    return {
        str(path): str(asset_hash)
        for path, asset_hash in data.items()
        if isinstance(path, str) and isinstance(asset_hash, (str, int))
    }


@st.cache_data(ttl=_CACHE_TTL)
def get_forgehx_data() -> Dict[str, str]:
    data = load_forgehx_asset_map()
    return {
        path: asset_hash
        for path, asset_hash in data.items()
        if path.startswith("/city/buildings/")
        and path.endswith(".png")
        and "/textures/" not in path
    }
```

Add `load_forgehx_asset_map.clear()` to `clear_cache()`.

- [ ] **Step 5: Run focused and compatibility tests**

Run:

```bash
.venv/bin/pytest -q tests/test_tooltip_loader.py tests/test_tooltip_full.py
```

Expected: all tests pass and existing building image behavior remains unchanged.

- [ ] **Step 6: Detect scope and commit**

Stage only `foe_buildings/data/loader.py` and `tests/test_tooltip_loader.py`, run
GitNexus staged change detection, then commit:

```bash
git commit -m "feat(tooltip): expose full ForgeHX asset map"
```

---

### Task 2: Add the Forge Hammer-compatible exact-key icon resolver

**Files:**
- Replace implementation: `foe_buildings/ui/tooltip_icons.py`
- Replace tests: `tests/test_tooltip_icons.py`
- Modify test isolation: `tests/conftest.py`

**Interfaces:**
- Consumes: `load_forgehx_asset_map() -> Dict[str, str]`, `get_icon_base64(name: str) -> Optional[str]`, and `FORGEHX_IMAGE_BASE`
- Produces: `ResolvedIcon`, `icon_candidates`, `boost_icon_key`, and `resolve_game_icon`
- Preserves temporarily: `resolve_icon` and `resolve_boost_icon` for existing tooltip call sites until Task 3 migrates them

- [ ] **Step 1: Run pre-edit impact analysis**

Run GitNexus upstream impact for `get_boost_icon_filename`, `resolve_icon`, and
`resolve_boost_icon` in `foe_buildings/ui/tooltip_icons.py`. Report their direct
callers and risk before editing.

- [ ] **Step 2: Write failing candidate-order and key tests**

Replace obsolete sprite-filename expectations with tests equivalent to:

```python
def test_feature_suffixes_match_forge_hammer():
    assert tooltip_icons.FEATURE_SUFFIXES == {
        "all": "",
        "battleground": "_gbg",
        "guild_expedition": "_gex",
        "guild_raids": "_gr",
    }


def test_boost_icon_key_keeps_raw_type_and_exact_feature_suffix():
    assert tooltip_icons.boost_icon_key(
        "att_def_boost_attacker_defender", "guild_expedition"
    ) == "att_def_boost_attacker_defender_gex"
    assert tooltip_icons.boost_icon_key(
        "att_def_boost_defender", "guild_raids"
    ) == "att_def_boost_defender_gr"


def test_icon_candidates_match_forge_hammer_order():
    assert tooltip_icons.icon_candidates("selection_kit_2")[:6] == [
        "/shared/icons/selection_kit_2.png",
        "/shared/gui/upgrade/upgrade_icon_selection_kit_2.png",
        "/shared/icons/selection_kit.png",
        "/shared/icons/goods/icon_fine_selection_kit_2.png",
        "/shared/icons/reward_icons/reward_icon_selection_kit_2.png",
        "/shared/icons/reward_icons/reward_icon_selection_kit.png",
    ]


def test_icon_candidates_add_entity_asset_fallback():
    assert tooltip_icons.icon_candidates(
        "W_Test_2", entity_asset_id="W_MultiAge_Test"
    )[-1] == "/city/buildings/W_SS_MultiAge_Test.png"


def test_direct_asset_path_is_not_rewritten():
    path = "/shared/gui/buffbar/buffbar_icon_buff_unconnected.png"
    assert tooltip_icons.icon_candidates(path) == [path]
```

Add URL and fallback tests using an injected mapping:

```python
def test_resolve_game_icon_uses_first_matching_forgehx_path():
    assets = {"/shared/icons/money.png": "abc123"}
    result = tooltip_icons.resolve_game_icon(
        "money", "Coins", asset_map=assets
    )
    assert result.key == "money"
    assert result.accessible_name == "Coins"
    assert result.url == (
        "https://foezz.innogamescdn.com/assets/shared/icons/money-abc123.png"
    )


def test_resolve_game_icon_falls_back_to_existing_local_icon(monkeypatch):
    monkeypatch.setattr(tooltip_icons, "get_icon_base64", lambda name: "encoded")
    result = tooltip_icons.resolve_game_icon("money", "Coins", asset_map={})
    assert result.url == "data:image/png;base64,encoded"


def test_resolve_game_icon_keeps_missing_icon_metadata():
    result = tooltip_icons.resolve_game_icon(
        "unknown_key", "Unknown reward", asset_map={}
    )
    assert result.url is None
    assert result.accessible_name == "Unknown reward"
```

- [ ] **Step 3: Run the tests and verify RED**

Run:

```bash
.venv/bin/pytest -q tests/test_tooltip_icons.py
```

Expected: failures for missing exact suffixes, candidates, and `ResolvedIcon` API.

- [ ] **Step 4: Implement candidate generation and resolution**

Implement these public shapes in `tooltip_icons.py`:

```python
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


def boost_icon_key(boost_type: str, feature: str = "all") -> str:
    return f"{boost_type}{FEATURE_SUFFIXES.get(feature, '')}"


def icon_candidates(
    icon_key: str, entity_asset_id: Optional[str] = None
) -> List[str]:
    """Return Forge Hammer's ordered ForgeHX candidates without duplicates."""


def resolve_game_icon(
    icon_key: str,
    accessible_name: str,
    *,
    entity_asset_id: Optional[str] = None,
    asset_map: Optional[Mapping[str, str]] = None,
) -> ResolvedIcon:
    """Resolve a raw game key to a trusted CDN URL or local data URI."""
```

When `icon_key` starts with `/`, treat it as a direct ForgeHX path and return it as
the only candidate. This is required for Forge Hammer's no-road icon. Otherwise use
the exact candidate order from the approved spec. Strip only a trailing numeric
suffix (`_<digits>`) for fallback candidates. Convert building IDs to `_SS_` paths
using the first underscore. Build hashed URLs by removing the candidate extension,
appending `-{hash}`, then restoring the extension.

Define an explicit `LOCAL_ICON_FALLBACKS` mapping for already useful local files,
including `money -> coins`, `strategy_points -> forge_points`,
`all_goods_of_age -> goods`, `treasury_goods -> guild_goods`, population,
happiness, medals/rank, size, road, unit-class, and current consumable icons. Do not
map incorrect generated combined icons. Values are local stems because
`get_icon_base64` adds `.png` itself.

Keep small compatibility wrappers so Task 2 is independently green:

```python
def resolve_icon(icon_name: Optional[str]) -> Optional[str]:
    key = (icon_name or "").removesuffix(".png")
    return resolve_game_icon(key, key, asset_map={}).url if key else None


def resolve_boost_icon(boost_type: str, feature: str = "all") -> Optional[str]:
    key = boost_icon_key(boost_type, feature)
    context = resolve_game_icon(key, key, asset_map={}).url
    return context or resolve_game_icon(
        boost_type, boost_type, asset_map={}
    ).url
```

Import `load_forgehx_asset_map` directly into `tooltip_icons.py`. Add an autouse
fixture in `tests/conftest.py` that monkeypatches only that imported binding to
`lambda: {}`. This keeps all model/rendering unit tests offline without replacing
the loader module's real function, while resolver contract tests inject their own
`asset_map` explicitly:

```python
@pytest.fixture(autouse=True)
def keep_tooltip_icon_tests_offline(monkeypatch):
    monkeypatch.setattr(
        "foe_buildings.ui.tooltip_icons.load_forgehx_asset_map", lambda: {}
    )
```

- [ ] **Step 5: Run focused and full compatibility tests**

Run:

```bash
.venv/bin/pytest -q tests/test_tooltip_icons.py tests/test_tooltip_provides.py tests/test_tooltip_produces.py
```

Expected: all pass; existing callers work through compatibility wrappers.

- [ ] **Step 6: Detect scope and commit**

Stage only `foe_buildings/ui/tooltip_icons.py`, `tests/test_tooltip_icons.py`, and
`tests/conftest.py`, run GitNexus staged change detection, then commit:

```bash
git commit -m "feat(tooltip): resolve exact game icon keys"
```

---

### Task 3: Assign exact icon keys to tooltip metadata and statistics

**Files:**
- Modify: `foe_buildings/ui/tooltip.py:130-665`
- Modify: `tests/test_tooltip_provides.py`
- Modify: `tests/test_tooltip_misc_sections.py`
- Modify: `tests/test_tooltip_size_time.py`
- Modify: `tests/test_tooltip_full.py`

**Interfaces:**
- Consumes: `ResolvedIcon`, `boost_icon_key`, and `resolve_game_icon`
- Produces: `TooltipRow.icon: Optional[ResolvedIcon]` and explicit quantitative/semantic row intent
- Preserves: existing translated `TooltipRow.label` values as accessible descriptions and test/debug metadata

- [ ] **Step 1: Run pre-edit impact analysis**

Run GitNexus upstream impact for `TooltipRow`, `_resource_display`,
`_render_size_time_road`, `_make_combined_rows`, `_make_non_army_rows`,
`_render_provides`, `_render_chain_set`, `_render_ally_rooms`, `_render_traits`,
and `_render_costs`. Report risk and affected tooltip flows before editing.

- [ ] **Step 2: Write failing exact-key metadata tests**

Add representative assertions without requiring the live CDN:

```python
def test_provides_keeps_exact_resource_and_boost_icon_keys():
    entity = {
        "components": {
            "AllAge": {
                "staticResources": {
                    "resources": {"resources": {"money": 10}}
                },
                "boosts": {
                    "boosts": [
                        {
                            "type": "att_def_boost_attacker_defender",
                            "targetedFeature": "guild_expedition",
                            "value": 25,
                        }
                    ]
                },
            }
        }
    }
    rows = _render_provides(entity, "en")
    assert [row.icon.key for row in rows] == [
        "money",
        "att_def_boost_attacker_defender_gex",
    ]
```

Add size/road/trait/ally assertions:

```python
assert size_row.icon.key == "size"
assert time_row.icon.key == "icon_time"
assert no_road_row.icon.key == (
    "/shared/gui/buffbar/buffbar_icon_buff_unconnected.png"
)
assert unique_trait.icon.key == "icon_unique_building"
assert fsp_trait.icon.key == "icon_fsp_disabled"
assert no_plunder_trait.icon.key == "eventwindow_plunder_repel"
assert ally_row.icon.key == "historical_allies_slot_tooltip_icon_empty"
```

Assert quantitative rows set `show_label=False` while semantic rows set
`show_label=True`.

- [ ] **Step 3: Run the tests and verify RED**

Run:

```bash
.venv/bin/pytest -q tests/test_tooltip_provides.py tests/test_tooltip_misc_sections.py tests/test_tooltip_size_time.py
```

Expected: failures because rows currently contain URL strings, generic local
filenames, or no trait icons.

- [ ] **Step 4: Evolve `TooltipRow` without discarding accessibility metadata**

Use this row shape:

```python
@dataclass
class TooltipRow:
    icon: Optional[ResolvedIcon]
    label: str
    value: str
    suffix: Optional[str] = None
    show_label: bool = False
    duration: Optional[int] = None
    markers: List[ResolvedIcon] = field(default_factory=list)
```

Add a focused helper so all call sites resolve consistently:

```python
def _icon(key: str, label: str, entity_asset_id: Optional[str] = None) -> ResolvedIcon:
    return resolve_game_icon(key, label, entity_asset_id=entity_asset_id)
```

- [ ] **Step 5: Migrate resources, boosts, and semantic metadata to raw keys**

Change `_resource_display` to return `(translated_label, raw_icon_key)`, using only
Forge Hammer's category mappings (`era_goods -> all_goods_of_age`, treasury goods
to treasury keys). Do not translate `money` to a local filename before resolution.

For boosts, resolve `boost_icon_key(boost_type, targeted_feature)` directly. Remove
the static `_BOOST_ICON_NAMES` URL handling. Preserve labels for accessibility and
tests, but set quantitative rows to `show_label=False`.

Use these semantic keys and set `show_label=True`:

```python
TRAIT_ICON_KEYS = {
    "unique_building": "icon_unique_building",
    "upgrades_automatically": "icon_age",
    "fsp_disabled": "icon_fsp_disabled",
    "can_be_motivated": "when_motivated",
    "can_be_polished": "when_motivated",
    "cannot_be_plundered": "eventwindow_plunder_repel",
    "requires_life_support": "life_support",
}
```

Use `size`, `icon_time`, `street_required`, `road_required`, and the direct path
`/shared/gui/buffbar/buffbar_icon_buff_unconnected.png` for size/time/road. Use exact chain/set IDs and
`historical_allies_slot_tooltip_icon_empty` for ally-room requirements.

- [ ] **Step 6: Run metadata and full-tooltip tests**

Run:

```bash
.venv/bin/pytest -q tests/test_tooltip_size_time.py tests/test_tooltip_provides.py tests/test_tooltip_misc_sections.py tests/test_tooltip_full.py
```

Expected: all pass with existing labels preserved and exact icon keys asserted.

- [ ] **Step 7: Detect scope and commit**

Stage only the Task 3 implementation and tests, run GitNexus staged change
detection, then commit:

```bash
git commit -m "feat(tooltip): map stats to exact game icons"
```

---

### Task 4: Model shared durations and independent random-production pools

**Files:**
- Modify: `foe_buildings/ui/tooltip.py:626-824`
- Rewrite production cases: `tests/test_tooltip_produces.py`
- Modify Pendragon expectations: `tests/test_tooltip_full.py`
- Extend fixture if needed: `tests/fixtures/pendragon_tooltip.py`

**Interfaces:**
- Consumes: exact-key `TooltipRow` and selected-era reward lookup
- Produces: `RandomProductionGroup`, `ProductionResult`, marker icons, and production-section duration metadata
- Preserves: source option order, reward quantities, motivated-only state, and translated accessible labels

- [ ] **Step 1: Run pre-edit impact analysis**

Run GitNexus upstream impact for `_generic_reward_display`, `_render_product`,
`_render_produces`, `TooltipSection`, and `render_building_tooltip`. Report risk and
affected processes before editing.

- [ ] **Step 2: Write failing shared-duration tests**

Replace substring-only checks with explicit model assertions:

```python
def test_one_shared_duration_moves_to_produces_heading():
    entity = production_entity(
        option(86400, resource_product("money", 100)),
        option(86400, resource_product("strategy_points", 5)),
    )
    sections = render_building_tooltip(entity, "en")
    section = next(s for s in sections if s.key == "produces")

    assert section.title == "Produces"
    assert section.shared_duration == 86400
    assert [row.value for row in section.rows] == ["100", "5"]
    assert all(row.duration is None for row in section.rows)


def test_mixed_durations_stay_on_each_production_row():
    entity = production_entity(
        option(3600, resource_product("money", 100)),
        option(86400, resource_product("strategy_points", 5)),
    )
    sections = render_building_tooltip(entity, "en")
    section = next(s for s in sections if s.key == "produces")

    assert section.shared_duration is None
    assert [row.duration for row in section.rows] == [3600, 86400]
```

- [ ] **Step 3: Write failing multiple-random-pool tests**

Use one production option containing two separate `type: "random"` products and
assert they remain separate:

```python
def test_two_random_products_remain_two_independent_groups():
    result = _render_produces(entity_with_two_random_products(), "en")

    assert len(result.random_groups) == 2
    assert [len(group.outcomes) for group in result.random_groups] == [2, 2]
    assert [outcome.probability for outcome in result.random_groups[0].outcomes] == [25, 75]
    assert [outcome.probability for outcome in result.random_groups[1].outcomes] == [50, 50]
```

Add a mixed-duration case proving a random group's parent option duration is shown
only when section durations differ.

- [ ] **Step 4: Run the production tests and verify RED**

Run:

```bash
.venv/bin/pytest -q tests/test_tooltip_produces.py tests/test_tooltip_full.py
```

Expected: failures because durations are embedded in values and random outcomes are
flattened.

- [ ] **Step 5: Add explicit production result types**

Add these dataclasses:

```python
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
```

Extend `TooltipSection` with:

```python
key: Optional[str] = None
random_groups: List[RandomProductionGroup] = field(default_factory=list)
shared_duration: Optional[int] = None
```

- [ ] **Step 6: Separate product extraction from timing and grouping**

Make `_render_product` return ordinary rows only for non-random products. Add
`_render_random_product` that creates exactly one `RandomProductionGroup` per raw
random product. Convert `dropChance` to a rounded integer percentage without
appending it to `TooltipRow.value`.

For generic rewards:

- resource reward icon key is `subType`;
- normal reward icon key is `iconAssetName`;
- fragment reward primary key is the assembled reward's icon key and its marker is
  `icon_tooltip_fragment`;
- motivated products add a `when_motivated` marker;
- unit icon key is `rogue`, `chivalry` for champion IDs, otherwise the exact
  `unitTypeId`; when that exact ForgeHX key is absent, its explicit local fallback is
  `military.png`. Do not guess a unit class from its name.

Change `_render_produces` to return `ProductionResult`. Compute the set of positive
option durations before assigning timing:

```python
durations = {option.get("time") for option in options if option.get("time")}
shared_duration = next(iter(durations)) if len(durations) == 1 else None
```

When `shared_duration` is present, leave row/group durations `None`; otherwise copy
each option's duration onto every row and random group from that option.

In `render_building_tooltip`, keep translated display titles separate from stable
section identity. Set `key="produces"` and carry the shared duration as data:

```python
TooltipSection(
    key="produces",
    title=translations.get_text("produces", lang_code),
    rows=production.rows,
    random_groups=production.random_groups,
    shared_duration=production.shared_duration,
)
```

Give every other section a stable untranslated key (`header`, `size_time_road`,
`provides`, `chain_set`, `ally_rooms`, `costs`, or `traits`) so tests and consumers
never use a translated or duration-qualified heading as identity.

- [ ] **Step 7: Run focused and era-regression tests**

Run:

```bash
.venv/bin/pytest -q tests/test_tooltip_produces.py tests/test_tooltip_full.py
```

Expected: Pendragon's production section carries key `produces` and shared duration
`86400`; the eventual display heading is `Produces (1d)`, values contain no
repeated `in 1d`, fragment/motivated markers retain exact keys, and two random pools
remain separate.

- [ ] **Step 8: Detect scope and commit**

Stage only Task 4 files, run GitNexus staged change detection, then commit:

```bash
git commit -m "feat(tooltip): group timed and random productions"
```

---

### Task 5: Render accessible icon/value rows and styled random groups

**Files:**
- Modify: `foe_buildings/ui/tooltip.py:243-264`
- Create: `foe_buildings/ui/styles/tooltip.css`
- Modify: `foe_buildings/ui/styles/__init__.py`
- Create: `tests/test_tooltip_rendering.py`
- Modify translations: `foe_buildings/i18n/locales/en/ui.json`
- Modify translations: `foe_buildings/i18n/locales/fr/ui.json`

**Interfaces:**
- Consumes: `TooltipRow`, `RandomProductionGroup`, `TooltipSection`, and `ResolvedIcon`
- Produces: `_tooltip_row_html`, `_random_group_html`, and `load_tooltip_css`
- Preserves: Streamlit `render_tooltip_sections(sections, lang_code)` entry point

- [ ] **Step 1: Run pre-edit impact analysis**

Run GitNexus upstream impact for `render_tooltip_sections` and `load_tab_css`.
Report risk before editing and do not alter existing tab styling behavior.

- [ ] **Step 2: Write failing pure HTML rendering tests**

Create `tests/test_tooltip_rendering.py` with exact structural assertions:

```python
def test_quantitative_row_hides_visible_label_but_keeps_accessible_name():
    row = TooltipRow(
        icon=ResolvedIcon("money", "https://cdn/money.png", "Coins"),
        label="Coins",
        value="1,000",
    )
    html = _tooltip_row_html(row, "en")

    assert '<img src="https://cdn/money.png"' in html
    assert ">1,000<" in html
    assert "Coins:" not in html
    assert 'aria-label="Coins: 1,000"' in html
    assert 'title="Coins: 1,000"' in html


def test_semantic_row_keeps_visible_text():
    row = TooltipRow(
        icon=ResolvedIcon("icon_unique_building", None, "Trait"),
        label="Trait",
        value="Unique building",
        show_label=True,
    )
    html = _tooltip_row_html(row, "en")

    assert "Unique building" in html
    assert "tooltip-icon-missing" in html


def test_rendering_escapes_api_derived_accessible_text():
    row = TooltipRow(None, '<script>alert("x")</script>', "1")
    html = _tooltip_row_html(row, "en")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
```

Add a two-group test:

```python
def test_random_groups_have_separate_styled_containers_and_probabilities():
    first = random_group("money", 10, 25)
    second = random_group("strategy_points", 2, 75)
    html = _random_group_html(first, "en") + _random_group_html(second, "en")

    assert html.count('class="tooltip-random-group"') == 2
    assert ">25%<" in html
    assert ">75%<" in html
    assert html.count('aria-label="Random production') == 2
```

- [ ] **Step 3: Run rendering tests and verify RED**

Run:

```bash
.venv/bin/pytest -q tests/test_tooltip_rendering.py
```

Expected: collection fails because the pure HTML helpers and tooltip stylesheet do
not exist.

- [ ] **Step 4: Implement escaped pure HTML helpers**

Use `html.escape(..., quote=True)` for every label, value, suffix, URL, and title.
Render section headings as `section.title`, appending
`f" ({format_time(section.shared_duration)})"` only when a shared duration exists.
Render quantitative rows as icon, value, optional formatted duration, and marker
icons. Render semantic rows as icon and value; do not emit the generic `label:`
prefix. When `ResolvedIcon.url is None`, emit:

```html
<span class="tooltip-icon-missing" aria-hidden="true">?</span>
```

`_random_group_html` renders one outer container per group, outcome icon/value on
the left, and probability on the right. Add translated accessible text keys
`random_production` in English and French, used only in `aria-label` and `title`.

- [ ] **Step 5: Add focused tooltip styling**

Create `foe_buildings/ui/styles/tooltip.css` with scoped classes:

```css
.foe-tooltip-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 1.75rem;
}

.foe-tooltip-icon,
.tooltip-icon-missing {
  width: 1.5rem;
  height: 1.5rem;
  flex: 0 0 1.5rem;
}

.tooltip-random-group {
  margin: 0.35rem 0;
  padding: 0.35rem 0.5rem;
  border: 2px solid color-mix(in srgb, #c694ff 70%, transparent);
  border-radius: 0.45rem;
  background: color-mix(in srgb, #7d4ca5 16%, transparent);
}

.tooltip-random-outcome {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.tooltip-random-probability {
  min-width: 3rem;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
```

Add `load_tooltip_css()` beside `load_tab_css()` and inject it once at the start of
`render_tooltip_sections`. Keep every selector under tooltip-specific classes so
other Streamlit tabs are unaffected.

- [ ] **Step 6: Render section rows and random groups**

Replace label/value Markdown assembly with the pure helpers. Keep the building name
and image header behavior. Render `section.random_groups` immediately after ordinary
production rows. Duration text appears only when `row.duration` or `group.duration`
is set.

- [ ] **Step 7: Run rendering, tooltip, lint, and type checks**

Run:

```bash
.venv/bin/pytest -q tests/test_tooltip_rendering.py tests/test_tooltip_*.py
.venv/bin/ruff check foe_buildings/ui/tooltip.py foe_buildings/ui/styles tests/test_tooltip_rendering.py
.venv/bin/ruff format --check foe_buildings/ui/tooltip.py foe_buildings/ui/styles/__init__.py tests/test_tooltip_rendering.py
.venv/bin/mypy foe_buildings/ui/tooltip.py foe_buildings/ui/tooltip_icons.py
```

Expected: all checks pass; generated HTML has no visible quantitative names and no
unescaped API-derived content.

- [ ] **Step 8: Detect scope and commit**

Stage only Task 5 files, run GitNexus staged change detection, then commit:

```bash
git commit -m "feat(tooltip): style compact and random production rows"
```

---

### Task 6: Remove incorrect extracted icons and verify representative buildings

**Files:**
- Delete: `scripts/extract_tooltip_icons.py`
- Delete: `assets/icons/att_def_boost_attacker.png`
- Delete: `assets/icons/att_def_boost_attacker_gbg.png`
- Delete: `assets/icons/att_def_boost_attacker_ge.png`
- Delete: `assets/icons/att_def_boost_attacker_qi.png`
- Delete: `assets/icons/att_def_boost_defender.png`
- Delete: `assets/icons/att_def_boost_defender_gbg.png`
- Delete: `assets/icons/att_def_boost_defender_ge.png`
- Delete: `assets/icons/att_def_boost_defender_qi.png`
- Delete: `assets/icons/att_def_boost_attacker_defender.png`
- Delete: `assets/icons/att_def_boost_attacker_defender_gbg.png`
- Delete: `assets/icons/att_def_boost_attacker_defender_ge.png`
- Delete: `assets/icons/att_def_boost_attacker_defender_qi.png`
- Modify: `tasks/todo.md`

**Interfaces:**
- Consumes: completed resolver and renderer from Tasks 1-5
- Produces: a clean branch with no tooltip dependency on incorrectly extracted sprite assets

- [ ] **Step 1: Prove the obsolete assets have no remaining consumers**

Run:

```bash
rg -n "extract_tooltip_icons|att_def_boost_.*\.png|productions\.png" foe_buildings tests scripts assets
```

Expected: only the obsolete script/files themselves match. If product code or tests
still reference them, fix that dependency under the relevant earlier task before
deleting anything.

- [ ] **Step 2: Delete only the enumerated obsolete tooltip assets**

Remove the extraction script and the twelve `att_def_boost_*` files listed above.
Do not delete existing generic resource, unit-class, army, road, badge, or consumable
icons because they remain valid local fallbacks elsewhere in the application.

- [ ] **Step 3: Run the complete automated verification**

Run:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check foe_buildings tests
.venv/bin/ruff format --check foe_buildings tests
.venv/bin/mypy foe_buildings/data/loader.py foe_buildings/ui/images.py foe_buildings/ui/tooltip_icons.py foe_buildings/ui/tooltip.py foe_buildings/tabs/building_details.py
```

Expected: the complete suite and every static check pass.

- [ ] **Step 4: Perform live representative checks**

Using the normal authenticated API and the Streamlit app, verify:

- Pendragon's Throne of Camelot resolves the selected-era Provides and
  `Produces (1d)` values with exact ForgeHX icons.
- Its guild expedition and guild raids boosts request `_gex` and `_gr` assets.
- A building with mixed production times shows durations per line.
- A building with two random products shows two separate bordered groups.
- Merlin's Counsel still resolves from the list-shaped entity lookup and renders
  without exposing raw exceptions.

Capture the building IDs, observed section headings, random-group counts, and any
fallback icon keys in `tasks/todo.md`.

- [ ] **Step 5: Run final GitNexus and diff review**

Stage only the intended Task 6 deletions and `tasks/todo.md`. Run GitNexus staged
change detection, then inspect:

```bash
git diff --cached --check
git diff --cached --stat
git status --short
```

Confirm `AGENTS.md`, `CLAUDE.md`, and `foe_buildings/config/constants.py` remain
unstaged and unchanged by this feature work.

- [ ] **Step 6: Commit cleanup and verification evidence**

Commit:

```bash
git commit -m "chore(tooltip): remove incorrect sprite extractions"
```

- [ ] **Step 7: Request final code review**

Use `superpowers:requesting-code-review` on the entire branch diff from the design
commit's parent through `HEAD`. Address every Critical and Important finding, rerun
the complete verification, and update the Review section of `tasks/todo.md` with
the final evidence.

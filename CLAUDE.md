# FoE Buildings Database — Claude Guide

## Project Overview

A Streamlit web app for analyzing and comparing Forge of Empires buildings. Players use it to rank buildings by efficiency based on their personal city context (daily production, boosts) and playstyle preferences (weighted scoring).

**Run locally:** `streamlit run app.py`
**API config:** `.streamlit/secrets.toml` → `[foe_api]` section with `url` and `key`

---

## Module Map

| Path | Purpose |
|---|---|
| `app.py` | Thin entry point — calls `foe_buildings.app.main()` |
| `foe_buildings/app.py` | Orchestrator: page config, data load, sidebar filters, tab routing |
| `foe_buildings/config/api.py` | Logging setup, `get_api_config()`, file path constants |
| `foe_buildings/config/constants.py` | `ERAS_DICT`, `ERAS_LEVEL_MAP`, `COLUMN_GROUPS`, `COLUMN_PRESETS`, column name constants |
| `foe_buildings/config/scoring.py` | `WEIGHTABLE_COLUMNS`, `BOOST_TO_BASE_MAPPING`, `ADDITIVE_METRICS`, `RANKING_POINTS_PER_RESOURCE`, `WEIGHT_PRESETS` |
| `foe_buildings/config/session.py` | `SessionKeys` class, `init_session_state()` helper |
| `foe_buildings/data/loader.py` | Fetches buildings from the VPS API (paginated, cached 23h) |
| `foe_buildings/data/calculations.py` | Scoring engine: boost algorithm, weighted efficiency, per-square, army combination |
| `foe_buildings/tabs/building_analysis/__init__.py` | Building Analysis tab: subtab routing and efficiency caching |
| `foe_buildings/tabs/building_analysis/weights.py` | Weights subtab: weight/context/boost inputs, presets, profile import/export |
| `foe_buildings/tabs/building_analysis/table.py` | Table subtab: AG-Grid display, export, credits |
| `foe_buildings/tabs/building_analysis/consumables.py` | Consumables Analysis subtab |
| `foe_buildings/tabs/building_analysis/qi_boosts.py` | QI Boosts Analysis subtab |
| `foe_buildings/tabs/building_details.py` | Building Details tab: per-building stats and images |
| `foe_buildings/tabs/city_analysis.py` | City Analysis tab: building recommendations for player city context |
| `foe_buildings/tabs/visualizations.py` | Visualizations tab: charts, heatmaps, building comparison, greedy optimizer |
| `foe_buildings/ui/grid.py` | AG-Grid configuration, column formatters, heatmap styling, icon loading |
| `foe_buildings/ui/filters.py` | AND/OR advanced filter logic with numeric/categorical operators |
| `foe_buildings/ui/columns.py` | Sidebar column group toggles and preset selection |
| `foe_buildings/ui/images.py` | ForgeHX asset ID → CDN image URL resolution |
| `foe_buildings/ui/styles/tabs.css` | CSS for tab-styled radio buttons |
| `foe_buildings/i18n/__init__.py` | Translation engine: JSON loading, fallback, all translate_* functions |
| `foe_buildings/i18n/locales/{en,fr}/` | Translation JSON files per language |

---

## Architecture Notes

### Data Flow
1. `foe_buildings/data/loader.py` fetches paginated JSON from the VPS API → returns DataFrame
2. `foe_buildings/data/calculations.py` enriches it with weighted efficiency scores
3. `foe_buildings/app.py` applies session-state filters (era, event, name search, advanced filters)
4. `foe_buildings/ui/grid.py` renders the AG-Grid table with heatmap styling

### API
Building data is served from a private VPS (not GitHub raw files). Configure in `.streamlit/secrets.toml`:
```toml
[foe_api]
url = "https://your-subdomain.duckdns.org"
key = "foe_your_api_key_here"
```

### Translation System
JSON files in `foe_buildings/i18n/locales/<lang>/` — `en/` is canonical. Keys missing in `fr/` fall back to English. Files:
- `ui.json` — sidebar labels, button text, tab names
- `columns.json` — column header display names
- `building_names.json` — localized building names
- `events.json` / `eras.json` — game terminology
- `messages.json` — error and info messages

---

## Boost Algorithm (`foe_buildings/data/calculations.py:apply_boosts_to_base_metrics`)

The 3-step pipeline converts boost-percentage buildings into equivalent production units:

**Step 1 — Reverse-engineer true base production.**
The user's reported daily production already includes existing city boosts. To find the "raw base" we divide by `(1 + current_boost/100)`. This is needed because a new building's boost applies to the raw base, not the already-boosted value — otherwise boost buildings would be double-counted.

**Step 2 — Apply the new building's boost to the true base.**
`effective_production = true_base × (boost_percentage / 100)` — this is the production equivalent the boost building adds.

**Step 3 — Score the equivalent production.**
The equivalent production is treated like a direct production value and multiplied by the user's weight for that resource type.

**Why `Goods Boost` maps to a list:** `BOOST_TO_BASE_MAPPING["Goods Boost"]` maps to `["goods", "prev_age_goods", "next_age_goods"]` because a goods boost applies to all three age tiers simultaneously, whereas FP/Guild Goods/Special Goods boosts each target a single column.

---

## Per-Square Mode

`PER_SQUARE_EXCLUDED_COLUMNS` lists columns excluded when "per square" mode is active. These are non-numeric metadata columns (`name`, `Event`, `Era`, `size`, etc.) and pre-computed scores (`Weighted Efficiency`, `Total Score`) that would be meaningless or misleading when divided by tile count.

---

## Key Constants (`foe_buildings/config/scoring.py` and `foe_buildings/config/constants.py`)

- `RANKING_POINTS_PER_RESOURCE` — points assigned per unit of resource for City Analysis ranking. Goods values are era-scaled (higher eras = more points per good). `special_goods` only has entries for eras where special goods exist in-game (Arctic Future, Oceanic Future, and Space Ages).
- `ERAS_LEVEL_MAP` — maps integer era level (1–22) to era key string; used for era-filtered analysis in `foe_buildings/tabs/city_analysis.py`
- `PER_SQUARE_EXCLUDED_COLUMNS` — see Per-Square Mode above

---

## Development Conventions

- **Session state keys** are centralised in `foe_buildings/config/session.py` as `SessionKeys` class attributes. Use `SessionKeys.FOO` rather than bare string literals.
- **Column name literals** (`'name'`, `'Era'`, `'Weighted Efficiency'`, etc.) are defined as constants in `foe_buildings/config/constants.py` (TODO #009). Treat remaining bare literals as known debt.
- **Error handling** is intentionally inconsistent by layer: `foe_buildings/data/loader.py` calls `st.stop()` (fatal — no data, no app), `foe_buildings/data/calculations.py` returns an empty/zeroed DataFrame (recoverable — show table without scores), `foe_buildings/tabs/city_analysis.py` logs and continues (best-effort — partial results acceptable). Match the pattern of the surrounding code when adding new error paths; a unification refactor is tracked as TODO #019.
- **QI Optimizer** tab is commented out in `foe_buildings/app.py` — dead code pending evaluation (TODO #038). Do not enable without completing the module.
- **`foe_buildings/i18n/locales/fr/messages.json`** exists but `foe_buildings/i18n/locales/en/messages.json` does not — asymmetry tracked as TODO #035.

---

## Running Tests

```bash
.venv/bin/python -m pytest tests/ -v
```

Test files:
- `tests/test_c1_normalisation.py` — C1 normalised scoring, era stats, source code integrity checks
- `tests/test_calculations.py` — scoring engine unit tests (per-square, era stats, army combination)
- `tests/test_config.py` — config integrity checks (era maps, session key uniqueness)
- `tests/conftest.py` — shared fixtures (sample buildings DataFrame)

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **FoE-Buildings-Database** (774 symbols, 1071 relationships, 18 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/FoE-Buildings-Database/context` | Codebase overview, check index freshness |
| `gitnexus://repo/FoE-Buildings-Database/clusters` | All functional areas |
| `gitnexus://repo/FoE-Buildings-Database/processes` | All execution flows |
| `gitnexus://repo/FoE-Buildings-Database/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

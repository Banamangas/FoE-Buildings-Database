# FoE Buildings Database — Claude Guide

## Project Overview

A Streamlit web app for analyzing and comparing Forge of Empires buildings. Players use it to rank buildings by efficiency based on their personal city context (daily production, boosts) and playstyle preferences (weighted scoring).

**Run locally:** `streamlit run app.py`
**API config:** `.streamlit/secrets.toml` → `[foe_api]` section with `url` and `key`

---

## Module Map

| File | Purpose |
|---|---|
| `app.py` | Entry point. Orchestrates tabs (Home, Weights, City Analysis, Visualizations), session state, filters, and AG-Grid rendering |
| `config.py` | All constants: `ERAS_DICT`, `ERAS_LEVEL_MAP`, `COLUMN_GROUPS`, `COLUMN_PRESETS`, `WEIGHTABLE_COLUMNS`, `BOOST_TO_BASE_MAPPING`, `RANKING_POINTS_PER_RESOURCE`, `PER_SQUARE_EXCLUDED_COLUMNS`, etc. |
| `data_loader.py` | Fetches buildings from the VPS API (paginated, `_PAGE_SIZE=1000`). Caches with a 23-hour TTL (tied to the 18:00 daily API refresh). Returns a processed pandas DataFrame |
| `calculations.py` | Efficiency scoring engine. `apply_boosts_to_base_metrics()` is the core function — see Boost Algorithm below |
| `translations.py` | Loads JSON translation files, resolves keys with fallback to English, handles yes/no keys and dynamic key construction |
| `ui_components.py` | AG-Grid configuration, column formatters, heatmap styling, icon loading/base64 encoding |
| `column_selector.py` | Sidebar column group toggles and preset selection |
| `advanced_filters.py` | AND/OR filter logic with numeric operators (between, gt, gte, lt, lte, eq, neq) and categorical/text filters |
| `building_images.py` | Resolves ForgeHX asset IDs to image URLs using `_SS_` path convention |
| `city_analysis.py` | Tab that recommends top buildings for a player's city context. Includes era-aware filtering and ranking via `RANKING_POINTS_PER_RESOURCE` |
| `data_visualizations.py` | Charts (Plotly), heatmaps, building comparison tables, and the greedy building placement optimizer |

---

## Architecture Notes

### Data Flow
1. `data_loader.py` fetches paginated JSON from the VPS API → returns DataFrame
2. `calculations.py` enriches it with weighted efficiency scores
3. `app.py` applies session-state filters (era, event, name search, advanced filters)
4. `ui_components.py` renders the AG-Grid table with heatmap styling

### API
Building data is served from a private VPS (not GitHub raw files). Configure in `.streamlit/secrets.toml`:
```toml
[foe_api]
url = "https://your-subdomain.duckdns.org"
key = "foe_your_api_key_here"
```

### Translation System
JSON files in `translations/<lang>/` — `en/` is canonical. Keys missing in `fr/` fall back to English. Files:
- `ui.json` — sidebar labels, button text, tab names
- `columns.json` — column header display names
- `building_names.json` — localized building names
- `events.json` / `eras.json` — game terminology
- `messages.json` — error and info messages

---

## Boost Algorithm (`calculations.py:apply_boosts_to_base_metrics`)

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

## Key Constants (`config.py`)

- `RANKING_POINTS_PER_RESOURCE` — points assigned per unit of resource for City Analysis ranking. Goods values are era-scaled (higher eras = more points per good). `special_goods` only has entries for eras where special goods exist in-game (Arctic Future, Oceanic Future, and Space Ages).
- `ERAS_LEVEL_MAP` — maps integer era level (1–22) to era key string; used for era-filtered analysis in `city_analysis.py`
- `PER_SQUARE_EXCLUDED_COLUMNS` — see Per-Square Mode above

---

## Development Conventions

- **Session state keys** are bare strings scattered across files (tracked as tech debt in TODO #010). Centralizing them in `config.py` is a pending refactor.
- **Column name literals** (`'name'`, `'Era'`, `'Weighted Efficiency'`, etc.) appear across multiple files (TODO #009). Treat as known debt.
- **Error handling** is intentionally inconsistent by layer: `data_loader.py` calls `st.stop()` (fatal — no data, no app), `calculations.py` returns an empty/zeroed DataFrame (recoverable — show table without scores), `city_analysis.py` logs and continues (best-effort — partial results acceptable). Match the pattern of the surrounding code when adding new error paths; a unification refactor is tracked as TODO #019.
- **QI Optimizer** tab is commented out (`app.py:24,647,1364`) — dead code pending evaluation (TODO #038). Do not enable without completing the module.
- **`translations/fr/messages.json`** exists but `translations/en/messages.json` does not — asymmetry tracked as TODO #035.

---

## Running Tests

There is currently no test suite beyond `test.py` (ad-hoc / exploratory). When adding tests, place them in a `tests/` directory and use `pytest`.

# FoE Buildings Database

A Streamlit web app for analysing and comparing buildings from Forge of Empires. Players use it to rank buildings by efficiency based on their personal city context (daily production, boost percentages) and playstyle weights.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app requires API credentials in `.streamlit/secrets.toml`:

```toml
[foe_api]
url = "https://your-subdomain.duckdns.org"
key = "foe_your_api_key_here"
```

Building data is served from a private VPS REST API (not local files). Without valid credentials the app will not start.

## Features

### Home Tab
- AG-Grid table with heatmap colour-coding and sorting
- Filter by era, event, building name, or advanced AND/OR conditions
- Per-square mode: all numeric columns divided by tile count
- Column selector: pick any combination of columns, or apply presets
- Export filtered view as CSV or JSON

### Weights Tab
- Assign point values to each production type (FP, goods, military units, army bonuses, …)
- Enter your current daily production and boost percentages for accurate boost-building valuation
- Scores update live — return to Home to see Weighted Efficiency and Total Score columns

### City Analysis Tab
- Import your inventory and city layout from ForgeDB (JSON paste)
- Ranks owned buildings by their contribution to your city's scoring
- Era-aware: each building is evaluated at the era it was placed

### Visualizations Tab
- Production charts (bar, scatter, radar)
- Side-by-side building comparison
- Greedy building placement optimiser: given a tile budget, finds the highest-scoring combination

### Analysis Subtabs (Advanced Mode)
- **Consumables**: rank buildings by finish-kit or instant-supply production, with a frequency-format toggle (units/day ↔ days/unit)
- **QI Boosts**: rank buildings by Quantum Incursion bonuses

## Languages

English and French. Building names fall back to English when a French translation is not available.

## Project Structure

```
app.py                 — Entry point; orchestrates tabs, session state, filters, AG-Grid
config.py              — All constants (ERAS_DICT, COLUMN_GROUPS, WEIGHTABLE_COLUMNS, …)
data_loader.py         — VPS API client with 23-hour Streamlit cache
calculations.py        — Efficiency scoring engine and boost conversion
translations.py        — JSON translation loader with English fallback
ui_components.py       — AG-Grid configuration, heatmap styling, icon helpers
column_selector.py     — Sidebar column group toggles and presets
advanced_filters.py    — AND/OR filter logic with numeric and categorical operators
building_images.py     — Resolves asset IDs to CDN image URLs via ForgeHX map
city_analysis.py       — City Analysis tab: import, rank, and display owned buildings
data_visualizations.py — Charts, building comparison, and placement optimiser
translations/          — en/ and fr/ JSON files: ui, columns, building_names, events, eras
assets/                — Icons and event-tag JSON files
```

## Notes

- This application is not affiliated with InnoGames or Forge of Empires. It is a community tool.
- Column auto-sizing is sometimes not working.
- Unique buildings are not differentiated from other buildings.

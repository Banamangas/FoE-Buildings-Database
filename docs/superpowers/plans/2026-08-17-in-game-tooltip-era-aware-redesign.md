# In-Game Tooltip Era-Aware Redesign Implementation Plan

> Execute with test-driven development and verify GitNexus impact before symbol edits.

**Goal:** Make the Building Details tooltip faithfully render selected-era raw API
statistics, with Pendragon's Throne of Camelot as the representative regression.

**Architecture:** Resolve `AllAge` and selected-era component data once at the
tooltip boundary, then reuse the existing pure section renderers on that resolved
entity. Normalize resources, rewards, boosts, and traits at their rendering
boundaries while preserving safe fallbacks for unknown API values.

**Stack:** Python, Streamlit, pytest, project i18n JSON, GitNexus.

## Task 1: Lock the raw schema into regression tests

**Files:**
- Create: `tests/fixtures/pendragon_tooltip.py`
- Modify: `tests/test_tooltip_full.py`
- Modify: `tests/test_tooltip_provides.py`
- Modify: `tests/test_tooltip_produces.py`
- Modify: `tests/test_tooltip_misc_sections.py`
- Modify: `tests/test_tooltip_size_time.py`

1. Add a compact two-tier Pendragon entity fixture.
2. Assert era resolution does not mutate the source.
3. Assert selected-era population, happiness, all/GBG/QI boosts, QI action points,
   base and motivated production, and 5/10 fragment rewards.
4. Assert the corrected trait, translated ally room, road omission semantics, and
   rectangular size order.
5. Run focused tests and confirm failures describe the current AllAge-only behavior.

## Task 2: Add centralized era resolution and wire the caller

**Files:**
- Modify: `foe_buildings/ui/tooltip.py`
- Modify: `foe_buildings/tabs/building_details.py`

1. Add a pure `_resolve_entity_for_era` helper.
2. Extend `render_building_tooltip` with optional `era_key` and resolve once.
3. Pass `building_data[config.COL_ERA]` from Building Details.
4. Preserve AllAge-only and unknown-era fallback behavior.
5. Run the era-resolution and full-tooltip tests.

## Task 3: Preserve and render complete boost data

**Files:**
- Modify: `foe_buildings/ui/tooltip.py`
- Modify: `foe_buildings/ui/tooltip_icons.py` only if mapping support is needed
- Modify: `foe_buildings/i18n/locales/en/ui.json`
- Modify: `foe_buildings/i18n/locales/fr/ui.json`

1. Replace dictionary-based boost collection with ordered list handling.
2. Preserve direct combined rows and legacy pair combination.
3. Add readable labels for known non-army and QI boosts.
4. Render unknown boost types with a humanized fallback rather than dropping them.
5. Run focused boost tests.

## Task 4: Normalize productions, resources, and rewards

**Files:**
- Modify: `foe_buildings/ui/tooltip.py`
- Modify: `foe_buildings/i18n/locales/en/ui.json`
- Modify: `foe_buildings/i18n/locales/fr/ui.json`

1. Introduce shared resource aliases and icon filenames.
2. Resolve generic reward metadata and quantity from the era lookup.
3. Preserve motivated suffixes and random-product probability.
4. Add context-sensitive labels for production options.
5. Run focused production tests.

## Task 5: Correct metadata, traits, and presentation

**Files:**
- Modify: `foe_buildings/ui/tooltip.py`
- Modify: `foe_buildings/i18n/locales/en/ui.json`
- Modify: `foe_buildings/i18n/locales/fr/ui.json`

1. Match the reference size order and absent-component no-road semantics.
2. Translate ally room identifiers.
3. Correct flag 32 and recognize social interaction metadata.
4. Remove duplicate image caption text.
5. Run all tooltip tests.

## Task 6: Verify scope and production readiness

**Files:**
- Modify: `tasks/todo.md`

1. Run the complete test suite.
2. Run compile/static checks configured by the repository.
3. Run `gitnexus_detect_changes(scope="all")` and inspect affected flows.
4. Review `git diff` for accidental changes and preserve unrelated user edits.
5. Record commands and results in `tasks/todo.md`.

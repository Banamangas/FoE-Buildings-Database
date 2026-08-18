# In-Game Tooltip Redesign

- [x] Review the live Pendragon schema and identify root causes.
- [x] Approve the era-aware renderer architecture.
- [x] Run GitNexus impact analysis for planned symbol edits.
- [x] Add realistic failing regression tests.
- [x] Add centralized selected-era component resolution.
- [x] Render complete boosts, productions, and reward quantities.
- [x] Correct resources, traits, ally rooms, road semantics, and presentation.
- [x] Run focused and full verification.
- [x] Run GitNexus change detection and final diff review.

## Review

Implemented an immutable, selected-era entity view that keeps additive AllAge boosts
and static resources. Building Details now passes the selected raw era key. The
renderer normalizes API resources and generic rewards, preserves repeated and future
boost types, labels feature contexts, translates ally rooms, and correctly describes
flag 32 as disabling instant production finish.

Verification:

- `.venv/bin/pytest -q` — 78 passed.
- Ruff lint — passed for all changed Python files.
- Ruff format check — 10 changed Python files already formatted.
- Mypy — no issues in loader, Building Details, or tooltip renderer.
- Live API validation — Pendragon's Stellar Age: Discovery tooltip rendered size,
  construction, no-road status, population, happiness, eight boost rows, five
  production/reward rows, military ally room, and corrected traits.
- GitNexus change detection — aggregate HIGH because the dirty worktree includes
  55 indexed symbols in 13 files; affected processes are limited to tooltip rendering
  and icon loading. Pre-existing AGENTS/CLAUDE/era edits remain excluded from the
  feature commit.

# Tooltip Icon and Production Presentation Redesign

## Task 1: Expose the complete cached ForgeHX asset map

- [x] Run pre-edit GitNexus upstream impact analysis.
- [x] Add failing full-map and compatibility tests.
- [x] Implement the minimal cached full-map loader.
- [x] Run focused and compatibility tests.
- [x] Run full-suite verification.
- [x] Detect staged scope, commit only Task 1 files, and self-review.

Impact analysis (2026-08-17): `get_forgehx_data` — LOW, 0 indexed direct callers,
0 affected flows; `clear_cache` — LOW, 0 indexed direct callers, 0 affected flows.
GitNexus reported no callers/flows, so the partial result is supplemented by the
required `get_forgehx_data` building-only compatibility test.

Task 1 review: completed in commit `df00800`. Focused tests: 13 passed. Full
suite: 82 passed. Staged GitNexus detection found 2 files, 7 symbols, 0 affected
processes, LOW risk. Only `foe_buildings/data/loader.py` and
`tests/test_tooltip_loader.py` were staged and committed.

- [x] Trace Forge Hammer's custom-tooltip icon resolution pipeline.
- [x] Verify the role of `productions.png` and identify the incorrect extraction.
- [x] Inventory reusable icons in this repository.
- [x] Approve the exact-key icon-source and fallback design.
- [x] Write and commit the approved design specification.
- [x] Produce a TDD implementation plan with GitNexus impact checkpoints.
- [x] Add failing contract and presentation tests.
- [x] Implement exact-key icon resolution and local fallback behavior.
- [x] Render stat rows as icon plus value while retaining accessible descriptions.
- [x] Consolidate identical production durations into the section heading.
- [x] Visually group each random-production pool, including multiple pools.
- [x] Verify representative buildings, full tests, lint, types, and affected flows.

## Review

Design approved and committed as `72bb92a`. The implementation plan is stored at
`docs/superpowers/plans/2026-08-17-tooltip-icon-production-redesign.md`.

Planning verification found that `/data/download/unit_types.json` is not exposed by
the current API allowlist and none of the 220 unit products in the live building
lookup contains `unitClass`. The approved resolver therefore uses deterministic
`rogue`/champion mappings, exact unit IDs when ForgeHX provides them, and a generic
military local fallback without guessing classes from unit names.

## Task 6 Review

Worker handoff status: `DONE_WITH_CONCERNS` on base `6cdc62d`. The controller
subsequently committed Task 6 as `e74cbc0`.

Cleanup proof:

- Pre-deletion `rg -n "extract_tooltip_icons|att_def_boost_.*\.png|productions\.png" foe_buildings tests scripts assets` found only the extraction script and the deliberate negative sentinel in `tests/test_tooltip_icons.py`.
- Deleted only `scripts/extract_tooltip_icons.py` and the twelve enumerated
  `assets/icons/att_def_boost_*.png` files. The binary PNGs were zeroed only after
  `apply_patch` rejected their non-UTF-8 contents, then all thirteen targets were
  deleted through `apply_patch`.
- Post-deletion `rg --files assets/icons | rg '/att_def_boost_'` returned no files.
  Repeating the consumer search returned only
  `tests/test_tooltip_icons.py:92`, the preserved negative sentinel.
- `AGENTS.md` and `CLAUDE.md` retain pre-existing worktree changes;
  `foe_buildings/config/constants.py` was not changed. At worker handoff, nothing
  was staged or committed; the controller subsequently committed Task 6 as
  `e74cbc0`.

Automated verification:

- `.venv/bin/pytest -q` — 105 passed in 0.26s.
- `.venv/bin/ruff check foe_buildings tests` — passed.
- `.venv/bin/ruff format --check foe_buildings tests` — failed because 16 files
  already present at base `6cdc62d` would be reformatted: `constants.py`,
  `loader.py`, `table.py`, `weights.py`, `visualizations.py`, `filters.py`,
  `images.py`, `kofi.py`, `tooltip_icons.py`, and seven test files. Task 6 has no
  modifications under `foe_buildings/` or `tests/`; its only Python-path change is
  deleting the enumerated extraction script. Formatting the protected or unrelated
  files was out of scope.
- `.venv/bin/mypy foe_buildings/data/loader.py foe_buildings/ui/images.py foe_buildings/ui/tooltip_icons.py foe_buildings/ui/tooltip.py foe_buildings/tabs/building_details.py` — success, no issues in 5 source files (one informational unchecked-body note for `images.py:49`).
- `git diff --check` — passed in the final command sweep.
- GitNexus unstaged change detection — LOW risk, 0 affected execution flows. It
  reported only pre-existing instruction/config symbols; the Task 6 asset and
  evidence paths do not map to indexed execution flows. GitNexus listed
  `constants.py` as touched despite no Git diff for that file, so that entry is an
  index-baseline artifact rather than a Task 6 change.

Deterministic fixture/model/HTML proof (not live API/browser proof):

- Pendragon fixture `W_MultiAge_ARTHUR26A10`, selected era
  `StellarAgeDiscovery`: heading `Produces (1d)`; Population `67000`, Happiness
  `100480`, Coins `776610`, Forge Points `411`, and Goods `575`; no row-level
  duration; guild-raids key `att_def_boost_defender_gr`.
- Dedicated guild-expedition fixture: key
  `att_def_boost_attacker_defender_gex`.
- Mixed-duration fixture: heading `Produces`; `money` shows `1h` and
  `strategy_points` shows `1d` at row level.
- `entity_with_two_random_products`: 2 groups, 2 outcomes each, probabilities
  `25/75` and `50/50`, and 2 rendered `.tooltip-random-group` containers.
- Merlin fixture `merlin-list-shaped-fixture`: a list-shaped API payload normalized
  to a keyed lookup and rendered header `Merlin's Counsel`; an injected
  `raw-secret-exception` produced only `Unable to render tooltip` plus the generic
  no-data message in the UI, with no raw exception text exposed.
- With the deterministic empty ForgeHX map, Pendragon used local fallbacks for
  `population`, `happiness`, `money`, `strategy_points`, `all_goods_of_age`, and
  the three production boost keys. Exact combined/context boost, guild-raids,
  fragment-selection-kit, and guild-raids action-point keys correctly reached the
  neutral missing-icon path instead of the deleted generated assets.

Live limitation: `.streamlit/secrets.toml` and `FOE_API_KEY` were absent, and no
Streamlit app was already running. An authenticated API/CDN or browser render was
therefore not available without new credentials/authority; no live result is
claimed.

## Final whole-branch review fixes

- [x] Make Building Details tabs stateful/lazy so the 40 MB lookup loads only when
  the In-Game Tooltip tab is open.
- [x] Load the ForgeHX asset map once per tooltip assembly instead of once per icon.
- [x] Additively merge overlapping AllAge and selected-era static resources.
- [x] Prefer resolved generic-reward quantities over product-reference fallback
  quantities and support unit-type generic rewards.
- [x] Implement player-versus-treasury resource icon mappings from Forge Hammer.
- [x] Wire existing QI and single-stat GE/GBG/QI local fallbacks to raw game keys;
  keep combined boosts and military neutral when no semantically valid local asset
  exists.
- [x] Retain the approved rows-before-random-groups renderer contract; the final
  review's interleaving Minor was not adopted because it conflicts with Task 5's
  approved ordering and would materially expand the model.
- [x] Add representative French model/HTML coverage and remove range whitespace.
- [ ] Run focused tests after each group, then full tests, lint, types, locale JSON,
  range `git diff --check`, GitNexus detection, and final re-review.

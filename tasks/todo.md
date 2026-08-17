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

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

- [x] Trace Forge Hammer's custom-tooltip icon resolution pipeline.
- [x] Verify the role of `productions.png` and identify the incorrect extraction.
- [x] Inventory reusable icons in this repository.
- [x] Approve the exact-key icon-source and fallback design.
- [x] Write and commit the approved design specification.
- [x] Produce a TDD implementation plan with GitNexus impact checkpoints.
- [ ] Add failing contract and presentation tests.
- [ ] Implement exact-key icon resolution and local fallback behavior.
- [ ] Render stat rows as icon plus value while retaining accessible descriptions.
- [ ] Consolidate identical production durations into the section heading.
- [ ] Visually group each random-production pool, including multiple pools.
- [ ] Verify representative buildings, full tests, lint, types, and affected flows.

## Review

Design approved and committed as `72bb92a`. The implementation plan is stored at
`docs/superpowers/plans/2026-08-17-tooltip-icon-production-redesign.md`.

Planning verification found that `/data/download/unit_types.json` is not exposed by
the current API allowlist and none of the 220 unit products in the live building
lookup contains `unitClass`. The approved resolver therefore uses deterministic
`rogue`/champion mappings, exact unit IDs when ForgeHX provides them, and a generic
military local fallback without guessing classes from unit names.

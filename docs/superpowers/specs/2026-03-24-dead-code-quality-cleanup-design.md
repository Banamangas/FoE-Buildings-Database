# Design: Dead Code & Code Quality Cleanup

**Date:** 2026-03-24
**Scope:** TODO items #080, #081, #082, #086, #088, #090
**Category:** Dead code removal + targeted code quality fixes
**Risk:** Low — deletions only in Commit 1; minimal edits in Commit 2

---

## Goal

Remove dead code and fix the six highest-signal code quality issues identified in the 2026-03-24 code review pass. No behavioral changes, no refactoring, no new features.

---

## Commit 1 — Dead Code Sweep

Pure deletions. No logic is affected.

### #080 — Dead import in `calculations.py`

**File:** `calculations.py:8`

Remove:
```python
from translations import translate_era_key  # Needed for reverse mapping
```

`translate_era_key` is never called in this file. The comment is misleading. If reverse-mapping is needed in future, it will be tracked separately.

---

### #081 — Five unused imports in `app.py`

**File:** `app.py:8-12`

Remove the following imports (all confirmed unused by the code review):
- `ColumnsAutoSizeMode` and `GridUpdateMode` — **partial edit** of their import line, which also contains used symbols (`AgGrid`, `AgGridTheme`, `DataReturnMode`, `JsCode`). Remove only these two names; do not delete the whole line.
- `GridOptionsBuilder` (`from st_aggrid.grid_options_builder import GridOptionsBuilder`) — full line deletion
- `DynamicFilters` (`from streamlit_dynamic_filters import DynamicFilters`) — full line deletion
- `np` (`import numpy as np`) — full line deletion

---

### #082 — Dead function and dict in `translations.py`

**File:** `translations.py:62-68`

Remove:
- `PER_SQUARE_TRANSLATIONS` dict — only referenced by `get_per_square_text`
- `get_per_square_text` function — never called anywhere in the codebase

If per-square label translation is needed in future, it should be added to `translations/en/ui.json` and resolved via `get_text()` like all other UI strings.

---

## Commit 2 — Code Quality Fixes

Small, targeted edits. No behavioral changes except log verbosity.

### #086 — Incorrect type hints on `user_boosts` parameter

**File:** `calculations.py:194, 253`

`user_boosts: Dict[str, float] = None` is an incorrect annotation — the correct type for a parameter with a `None` default is `Optional[Dict[str, float]]`.

Fix both affected signatures:
- `calculate_direct_weighted_efficiency` (line 194)
- `calculate_weighted_efficiency` (line 253)

Also add `Optional` to the existing `from typing import ...` import at the top of the file.

---

### #088 — Inline imports inside a render function

**File:** `city_analysis.py`

`from io import BytesIO` and `from datetime import datetime` appear inside `render_city_analysis_tab`. `datetime` is already imported at module level (line 5). These imports execute on every Streamlit rerender.

Move both to module-level imports. Since `datetime` is already present, only `BytesIO` needs to be added to the top-of-file imports (from `io`).

---

### #090 — `logger.info` fires on every render cycle

**File:** `app.py:769`

```python
logger.info(f"Main Analysis: Weights active: {weights_active}, User weights: {user_weights}")
```

This fires on every Streamlit interaction, producing high-volume noise at INFO level and serializing the full weights dict each time. Change to `logger.debug`.

---

## Out of Scope

All other items in the 080–097 range (TODO #083–085, #087, #089, #091–097) are explicitly excluded from this plan and remain Pending in TODO.md.

---

## Success Criteria

- All six TODO items (#080, #081, #082, #086, #088, #090) marked Resolved in TODO.md
- App runs with `streamlit run app.py` without errors after both commits
- No new imports introduced; no logic changed

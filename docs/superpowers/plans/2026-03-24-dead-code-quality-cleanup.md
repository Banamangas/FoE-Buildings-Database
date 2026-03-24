# Dead Code & Code Quality Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove 3 dead code items and fix 3 code quality issues across 4 files in two clean commits.

**Architecture:** No new code. Commit 1 is pure deletions (dead import, unused imports, dead function+dict). Commit 2 is targeted edits (type hint corrections, inline import relocation, log level downgrade). Each commit is independently verifiable with `python -m py_compile`.

**Tech Stack:** Python 3.8+, Streamlit, pandas — no new dependencies introduced.

---

## Files Modified

| File | Tasks | Changes |
|------|-------|---------|
| `calculations.py` | 1, 5 | Remove 1 dead import; add `Optional` to typing imports; fix 2 type hints |
| `app.py` | 2, 7 | Remove 4 import lines (2 full deletions, 1 partial, 1 full); downgrade 1 log call |
| `translations.py` | 3 | Remove 1 dict + 1 function (7 lines total) |
| `city_analysis.py` | 6 | Remove 2 inline imports; add `BytesIO` to module-level imports |
| `TODO.md` | 8 | Mark 6 items Resolved |

---

## Commit 1 — Dead Code Sweep

### Task 1: Remove dead import from `calculations.py`

**Files:** Modify `calculations.py:8`

- [ ] **Verify the symbol is unused**

```bash
grep -n "translate_era_key" /home/born/Github/FoE-Buildings-Database/calculations.py
```

Expected: only 1 hit (the import line itself). If more hits appear, stop and re-evaluate.

- [ ] **Delete line 8**

Remove this exact line from `calculations.py`:
```python
from translations import translate_era_key # Needed for reverse mapping
```

The file should go from:
```python
from config import WEIGHTABLE_COLUMNS, ADDITIVE_METRICS, BOOST_TO_BASE_MAPPING, USER_CONTEXT_FIELDS, logger
from translations import translate_era_key # Needed for reverse mapping
```
to:
```python
from config import WEIGHTABLE_COLUMNS, ADDITIVE_METRICS, BOOST_TO_BASE_MAPPING, USER_CONTEXT_FIELDS, logger
```

- [ ] **Verify syntax**

```bash
cd /home/born/Github/FoE-Buildings-Database && python -m py_compile calculations.py && echo "OK"
```

Expected: `OK`

---

### Task 2: Remove unused imports from `app.py`

**Files:** Modify `app.py:8-12`

- [ ] **Verify each symbol is unused before editing**

```bash
grep -n "ColumnsAutoSizeMode\|GridUpdateMode\|GridOptionsBuilder\|DynamicFilters\|numpy\| np\b" /home/born/Github/FoE-Buildings-Database/app.py
```

Expected: only hits in the import lines (lines 8-12), none in the function body.

- [ ] **Edit line 8 — partial removal**

Line 8 currently reads:
```python
from st_aggrid import AgGrid, ColumnsAutoSizeMode, AgGridTheme, GridUpdateMode, DataReturnMode, JsCode
```

Change to (remove `ColumnsAutoSizeMode` and `GridUpdateMode`, keep the rest):
```python
from st_aggrid import AgGrid, AgGridTheme, DataReturnMode, JsCode
```

- [ ] **Delete lines 9, 10, and 12 — full line removals**

Remove these three lines entirely:
```python
from st_aggrid.grid_options_builder import GridOptionsBuilder
from streamlit_dynamic_filters import DynamicFilters
import numpy as np
```

After both edits, the import block should read:
```python
import logging
import os
from io import BytesIO
from datetime import datetime

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, AgGridTheme, DataReturnMode, JsCode
import json
```

- [ ] **Verify syntax**

```bash
cd /home/born/Github/FoE-Buildings-Database && python -m py_compile app.py && echo "OK"
```

Expected: `OK`

---

### Task 3: Remove dead function and dict from `translations.py`

**Files:** Modify `translations.py:62-68`

- [ ] **Verify the symbols are unused**

```bash
grep -rn "get_per_square_text\|PER_SQUARE_TRANSLATIONS" /home/born/Github/FoE-Buildings-Database/ --include="*.py"
```

Expected: only hits inside `translations.py` itself (the definition lines). No hits in any other file.

- [ ] **Delete lines 62–68**

Remove this entire block:
```python
PER_SQUARE_TRANSLATIONS = {
    "en": "Display values per square",
    "fr": "Afficher les valeurs par case"
}

def get_per_square_text(lang_code: str) -> str:
    return PER_SQUARE_TRANSLATIONS.get(lang_code, PER_SQUARE_TRANSLATIONS["en"])
```

The line immediately before (`from config import ERAS_DICT, logger`) and after (`# --- Column Name Translations ---`) should now be adjacent with a blank line between.

- [ ] **Verify syntax**

```bash
cd /home/born/Github/FoE-Buildings-Database && python -m py_compile translations.py && echo "OK"
```

Expected: `OK`

---

### Task 4: Commit the dead code sweep

- [ ] **Final compile check across all modified files**

```bash
cd /home/born/Github/FoE-Buildings-Database && python -m py_compile calculations.py app.py translations.py && echo "All OK"
```

Expected: `All OK`

- [ ] **Commit**

```bash
cd /home/born/Github/FoE-Buildings-Database
git add calculations.py app.py translations.py
git commit -m "$(cat <<'EOF'
chore: remove dead imports and unused code (#080, #081, #082)

- calculations.py: remove unused translate_era_key import
- app.py: remove ColumnsAutoSizeMode, GridUpdateMode, GridOptionsBuilder,
  DynamicFilters, numpy imports (all confirmed unused)
- translations.py: remove PER_SQUARE_TRANSLATIONS dict and
  get_per_square_text function (no callers found)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Commit 2 — Code Quality Fixes

### Task 5: Fix `Optional` type hints in `calculations.py`

**Files:** Modify `calculations.py:2, 194, 253`

- [ ] **Add `Optional` to the typing import (line 2)**

Change:
```python
from typing import Dict
```
To:
```python
from typing import Dict, Optional
```

- [ ] **Fix the type hint on `calculate_direct_weighted_efficiency` (line 194)**

The function signature currently contains:
```python
user_boosts: Dict[str, float] = None
```

Change that parameter to:
```python
user_boosts: Optional[Dict[str, float]] = None
```

Full signature for reference (only `user_boosts` changes):
```python
def calculate_direct_weighted_efficiency(df: pd.DataFrame, user_weights: Dict[str, float], user_context: Dict[str, float], user_boosts: Optional[Dict[str, float]] = None) -> pd.DataFrame:
```

- [ ] **Fix the type hint on `calculate_weighted_efficiency` (line ~253)**

Find the legacy wrapper function with this signature:
```python
def calculate_weighted_efficiency(df: pd.DataFrame, user_weights: Dict[str, float], era_stats_df: pd.DataFrame, df_original: pd.DataFrame, selected_translated_era: str, lang_code: str, user_context: Dict[str, float] = None, user_boosts: Dict[str, float] = None) -> pd.DataFrame:
```

Change **both** `= None` parameters to use `Optional`:
```python
def calculate_weighted_efficiency(df: pd.DataFrame, user_weights: Dict[str, float], era_stats_df: pd.DataFrame, df_original: pd.DataFrame, selected_translated_era: str, lang_code: str, user_context: Optional[Dict[str, float]] = None, user_boosts: Optional[Dict[str, float]] = None) -> pd.DataFrame:
```

- [ ] **Verify syntax**

```bash
cd /home/born/Github/FoE-Buildings-Database && python -m py_compile calculations.py && echo "OK"
```

Expected: `OK`

---

### Task 6: Move inline imports to module level in `city_analysis.py`

**Files:** Modify `city_analysis.py:3` (add `BytesIO`) and `city_analysis.py:889-890` (remove inline imports)

- [ ] **Add `BytesIO` to the module-level import at line 3**

Line 3 currently reads:
```python
import json
```

The file already has `from datetime import datetime` at line 5. Only `BytesIO` needs adding. Add it on a new line after the existing `import json` using stdlib grouping:

```python
from io import BytesIO
```

Place it near the other stdlib imports. The top of the file should look like:
```python
import streamlit as st
import pandas as pd
import json
import logging
import os
from io import BytesIO
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
```

- [ ] **Remove the two inline imports from inside `render_city_analysis_tab`**

Find and remove these two lines (around line 889-890 inside the render function):
```python
                    from io import BytesIO
                    from datetime import datetime
```

Leave the surrounding code untouched. The buffer creation line immediately following (`buffer_csv = BytesIO()`) stays in place — it now resolves via the module-level import.

- [ ] **Verify syntax**

```bash
cd /home/born/Github/FoE-Buildings-Database && python -m py_compile city_analysis.py && echo "OK"
```

Expected: `OK`

---

### Task 7: Downgrade log level in `app.py`

**Files:** Modify `app.py:769`

- [ ] **Change `logger.info` to `logger.debug`**

Find this line (around line 769):
```python
        logger.info(f"Main Analysis: Weights active: {weights_active}, User weights: {user_weights}")
```

Change to:
```python
        logger.debug(f"Main Analysis: Weights active: {weights_active}, User weights: {user_weights}")
```

- [ ] **Verify syntax**

```bash
cd /home/born/Github/FoE-Buildings-Database && python -m py_compile app.py && echo "OK"
```

Expected: `OK`

---

### Task 8: Commit the quality fixes

- [ ] **Final compile check across all modified files**

```bash
cd /home/born/Github/FoE-Buildings-Database && python -m py_compile calculations.py city_analysis.py app.py && echo "All OK"
```

Expected: `All OK`

- [ ] **Commit**

```bash
cd /home/born/Github/FoE-Buildings-Database
git add calculations.py city_analysis.py app.py
git commit -m "$(cat <<'EOF'
chore: fix Optional type hints, inline imports, and log level (#086, #088, #090)

- calculations.py: add Optional to typing import; fix user_boosts
  parameter annotation on both public functions
- city_analysis.py: move BytesIO and datetime imports to module level
  (were re-imported inside render function on every rerender)
- app.py: downgrade weights logger.info to logger.debug (fires on
  every Streamlit interaction)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Update TODO.md

- [ ] **Mark the 6 resolved items in `TODO.md`**

Change `| Pending |` to `| Resolved |` for items #080, #081, #082, #086, #088, #090.

- [ ] **Commit**

```bash
cd /home/born/Github/FoE-Buildings-Database
git add TODO.md
git commit -m "$(cat <<'EOF'
chore: mark TODO items #080-082, #086, #088, #090 as resolved

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

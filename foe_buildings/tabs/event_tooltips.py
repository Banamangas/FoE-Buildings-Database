from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from foe_buildings.ui.tooltip import TooltipRow, TooltipSection


def _parse_numeric_value(value: str) -> Optional[Tuple[float, str]]:
    """Return (number, suffix) for simple numeric or percent values, else None."""
    value = value.strip()
    match = re.match(r"^([+\-]?\d+(?:\.\d+)?)\s*(%?)$", value)
    if not match:
        return None
    number = float(match.group(1))
    suffix = match.group(2)
    return (number, suffix)


def _format_numeric_range(min_val: float, max_val: float, suffix: str) -> str:
    """Format a numeric range, collapsing identical values."""
    if min_val == max_val:
        formatted = f"{int(min_val)}" if min_val == int(min_val) else f"{min_val}"
        return f"{formatted}{suffix}"
    min_str = f"{int(min_val)}" if min_val == int(min_val) else f"{min_val}"
    max_str = f"{int(max_val)}" if max_val == int(max_val) else f"{max_val}"
    return f"{min_str} - {max_str}{suffix}"


def _aggregate_tooltip_rows(rows: List[TooltipRow]) -> TooltipRow:
    """Aggregate rows with the same label/icon into a range or unique list."""
    if not rows:
        return TooltipRow(icon=None, label="", value="")

    first = rows[0]
    if len(rows) == 1:
        return first

    numeric_values: List[Tuple[float, str]] = []
    non_numeric_values: List[str] = []

    for row in rows:
        parsed = _parse_numeric_value(row.value)
        if parsed is not None:
            numeric_values.append(parsed)
        else:
            non_numeric_values.append(row.value)

    if numeric_values and len(numeric_values) == len(rows):
        numbers = [v[0] for v in numeric_values]
        suffixes = {v[1] for v in numeric_values}
        suffix = next(iter(suffixes)) if len(suffixes) == 1 else ""
        aggregated_value = _format_numeric_range(min(numbers), max(numbers), suffix)
    else:
        unique_values = []
        seen = set()
        for value in (row.value for row in rows):
            if value not in seen:
                seen.add(value)
                unique_values.append(value)
        aggregated_value = " / ".join(unique_values)

    return TooltipRow(
        icon=first.icon,
        label=first.label,
        value=aggregated_value,
        suffix=first.suffix,
        show_label=first.show_label,
        duration=first.duration,
        markers=first.markers,
    )


def _row_identity(row: TooltipRow) -> Tuple:
    """Return a hashable identity for grouping equivalent rows across eras."""
    icon_key = row.icon.key if row.icon is not None else None
    marker_keys = tuple(m.key if m is not None else None for m in row.markers)
    return (row.label, icon_key, row.suffix, marker_keys)


def _aggregate_tooltip_sections(
    sections_per_era: Dict[str, List[TooltipSection]],
    lang_code: str,
) -> List[TooltipSection]:
    """Merge per-era sections, aggregating matching rows into ranges."""
    if not sections_per_era:
        return []

    section_order: List[str] = []
    rows_by_section: Dict[str, Dict] = {}

    for era, sections in sections_per_era.items():
        for section in sections:
            section_key = section.key if section.key is not None else ""
            if section_key not in rows_by_section:
                rows_by_section[section_key] = {
                    "title": section.title,
                    "rows": {},
                    "random_groups": [],
                    "shared_duration": section.shared_duration,
                    "order": len(section_order),
                }
                section_order.append(section_key)

            bucket = rows_by_section[section_key]
            for row in section.rows:
                identity = _row_identity(row)
                bucket["rows"].setdefault(identity, []).append(row)

            # Random groups are not aggregated in the MVP; keep the first era's groups.
            if section.random_groups and not bucket["random_groups"]:
                bucket["random_groups"] = section.random_groups

    aggregated: List[TooltipSection] = []
    first_era_sections = next(iter(sections_per_era.values()))
    for key in section_order:
        bucket = rows_by_section[key]
        aggregated_rows = [
            _aggregate_tooltip_rows(rows)
            for rows in bucket["rows"].values()
        ]
        # Preserve original row order from the first era that introduced each identity.
        first_section = next((s for s in first_era_sections if s.key == key), None)
        if first_section is not None:
            identity_order = [_row_identity(r) for r in first_section.rows]
            identity_index = {
                identity: idx for idx, identity in enumerate(identity_order)
            }
            aggregated_rows.sort(
                key=lambda r: identity_index.get(
                    _row_identity(r), len(identity_order)
                )
            )

        aggregated.append(
            TooltipSection(
                title=bucket["title"],
                rows=aggregated_rows,
                key=key,
                random_groups=bucket["random_groups"],
                shared_duration=bucket["shared_duration"],
            )
        )

    return aggregated


def _split_size_time_road_section(
    sections: List[TooltipSection],
) -> Tuple[Optional[TooltipSection], List[TooltipSection]]:
    """Extract the size/time/road section from a list of tooltip sections."""
    size_section: Optional[TooltipSection] = None
    other_sections: List[TooltipSection] = []
    for section in sections:
        if section.key == "size_time_road":
            size_section = section
        else:
            other_sections.append(section)
    return size_section, other_sections

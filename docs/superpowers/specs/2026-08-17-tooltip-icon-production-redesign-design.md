# Tooltip Icon and Production Presentation Redesign

## Context

The current tooltip treats Forge Hammer's `productions.png` as the source of
building-tooltip icons. That sprite is used by Forge Hammer's production filter
and city tables, not by its custom building tooltip. The custom tooltip calls
`srcLinks.icons(raw_key)`, which resolves each production, boost, reward, trait,
and metadata key against the current ForgeHX asset map.

The current implementation consequently displays incorrect combined army icons,
constructs invalid feature suffixes (`_ge` and `_qi` instead of `_gex` and `_gr`),
cannot resolve many reward and trait icons, repeats identical production durations,
and flattens random-production pools into ordinary rows.

## Goals

- Resolve tooltip icons from the same raw keys and candidate path order used by
  Forge Hammer.
- Retain existing local icons as deterministic offline fallbacks.
- Show quantitative rows as icon plus formatted value without a visible stat name.
- Keep concise visible text for semantic rows that have no meaningful number, such
  as road requirements, traits, ally rooms, and set descriptions.
- Show a shared production duration once in the `Produces (<duration>)` heading.
- Show row-level durations only when productions have different durations.
- Preserve every random-production pool as a distinct visual group, including when
  one building has multiple pools.
- Keep the tooltip header, selected-era data resolution, translations, and graceful
  error handling introduced by the existing implementation.

## Non-goals

- Do not download or commit the complete Forge of Empires icon library.
- Do not reuse `productions.png` for custom-tooltip rows.
- Do not redesign the Building Details page outside the In-Game Tooltip sub-tab.
- Do not change per-square calculations; the tooltip continues to show raw values.
- Do not display generic-reward names in quantitative production rows. Their exact
  icon and accessible description identify them without adding visual text.

## Reference Behavior

For an icon key `x`, Forge Hammer probes ForgeHX paths in this order:

1. `/shared/icons/{x}.png`
2. `/shared/gui/upgrade/upgrade_icon_{x}.png`
3. `/shared/icons/{x_without_numeric_suffix}.png`
4. `/shared/icons/goods/icon_fine_{x}.png`
5. `/shared/icons/reward_icons/reward_icon_{x}.png`
6. The reward-icon path using `x_without_numeric_suffix`
7. `/city/buildings/{x_with_SS_infix}.png`
8. The city-building path using `x_without_numeric_suffix`
9. A city-building path derived from the referenced entity's `asset_id`

The first candidate present in ForgeHX becomes a hashed CDN URL. Missing ForgeHX
data or a missing exact candidate is not fatal; the application falls back to a
local icon and finally to a neutral missing-icon marker.

Raw keys are preserved until this resolution step. Display-specific mappings match
Forge Hammer where the raw schema represents a category rather than an asset key:

- `era_goods` -> `all_goods_of_age`
- next-, previous-, and current-age random goods -> their corresponding chest icon
- treasury goods -> the corresponding treasury-goods icon
- units -> unit class, with `rogue` and champion/chivalry handling
- fragment rewards -> assembled reward icon plus `icon_tooltip_fragment`
- boost feature suffixes: all `""`, battleground `_gbg`, guild expedition `_gex`,
  and guild raids `_gr`

## Architecture

### ForgeHX asset data

Add a cached full-map loader for `/data/forgehx`. Keep the existing
`get_forgehx_data()` city-building contract by deriving its filtered result from
the full map. Both use the existing 23-hour cache policy and authenticated API
client. Cache clearing clears both functions.

The full map is read-only application data. A malformed or unavailable response
returns an empty mapping and logs a non-fatal warning, allowing local fallbacks to
continue rendering the tab.

### Exact-key icon resolver

Replace the static boost-filename synthesis in `tooltip_icons.py` with a focused
resolver that:

- accepts a game asset key and optional entity asset ID;
- generates the ordered Forge Hammer candidate paths;
- looks up the first path in the full ForgeHX map;
- constructs the hashed URL with the existing trusted InnoGames CDN base;
- falls back to an explicit raw-key-to-local-file map;
- returns an accessible description separately from the visual URL.

The resolver never downloads icons into the repository and never creates new icons
by cropping or compositing sprites. The old extraction script and incorrect
generated combined icons are removed from the feature branch. Existing unrelated
icons remain available to the rest of the application.

### Tooltip presentation model

Evolve the tooltip model so presentation intent is explicit instead of encoded in
labels and suffix strings:

- A quantitative row contains `icon_key`, resolved icon URL, formatted value,
  accessible label, optional duration, and optional markers such as motivated or
  fragment.
- A semantic row may retain visible text where an icon and number cannot communicate
  the meaning.
- A random-production group contains its own list of outcome rows, probability per
  outcome, parent duration, and motivated state.
- A section can carry a shared duration used to form its heading.

Labels remain available as escaped `title` and `aria-label` attributes even when
they are not visible. No raw API text is interpolated into unsafe HTML without
escaping.

### Production duration rules

Collect production options before rendering their products.

- If all timed options have one duration, the section heading is
  `Produces (<formatted duration>)`; rows and random groups omit the duration.
- If two or more durations are present, the heading is `Produces`; each ordinary
  row and random group displays its own duration.
- If no option supplies a duration, the heading is simply `Produces`.

This rule applies across ordinary resources, guild resources, units, generic
rewards, and random pools. A one-day duration is formatted as `1d`.

### Random-production groups

Each raw `type == "random"` product produces one independent group. Outcomes are
not merged with ordinary production rows and separate raw random products are not
merged with each other.

The group uses a subtle tinted background, a two-pixel accent border, rounded
corners, and compact spacing. Each outcome shows its icon and quantity on the left
and its probability on the right. The border and background communicate the random
relationship without adding a visible `Random` label. A descriptive `aria-label`
and `title` provide the same meaning for assistive technology and hover inspection.

## Rendering Rules

- Quantitative Provides, Produces, Boosts, and Costs rows display icon plus value.
- Percent boosts include `%`; non-percent boost units keep their existing formatting.
- Generic reward names are hidden visually but retained in accessible text.
- Fragment markers and motivated-only markers use their own exact game icons.
- Size and construction time use `size` and `icon_time`; road states use the exact
  road or unconnected icon and retain concise text.
- Traits and ally rooms use exact keys and retain their translated semantic text.
- Missing icons use a consistent neutral marker instead of exposing a filename or
  silently turning the value into an unlabeled line.
- Building name and image remain inside the tooltip renderer's header section.

## Error Handling

- ForgeHX fetch failures are non-fatal and logged without exposing exception text to
  users.
- A missing icon candidate falls through to local assets and then to the neutral
  marker.
- Unknown production and reward types are logged and skipped without preventing
  other tooltip sections from rendering.
- Existing selected-era entity resolution remains immutable and unchanged unless a
  failing regression test proves an integration defect.

## Testing

Tests use contract-shaped fixtures and mocked ForgeHX maps; they do not depend on
the live CDN.

- Verify the full ForgeHX loader, city-image filtering, caching boundary, and cache
  clearing.
- Verify candidate ordering, numeric-suffix fallback, hashed URL construction, exact
  `_gbg`/`_gex`/`_gr` boost keys, entity asset fallback, and local fallback.
- Verify resource, treasury-good, unit, fragment, motivated, trait, road, and ally
  icon-key selection.
- Verify quantitative HTML contains icon and value but no visible stat label, while
  retaining escaped accessible descriptions.
- Verify one shared duration produces `Produces (1d)` and no row-level `1d`.
- Verify mixed durations remain on their respective rows or random groups.
- Verify two random products render as two distinct styled groups with independent
  outcomes and probabilities.
- Run the focused tooltip suite, full pytest suite, Ruff, mypy, and a live Pendragon
  render check before completion.

Before any implementation edit, run GitNexus upstream impact analysis for every
changed function, class, or method. Before each commit, run GitNexus change detection
on the staged changes and review all affected execution flows.

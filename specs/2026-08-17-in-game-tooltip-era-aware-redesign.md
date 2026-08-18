# Era-Aware In-Game Tooltip Redesign

## Problem

The raw `building_entity_lookup.json` schema separates shared building metadata under
`components.AllAge` from level-dependent statistics under era keys such as
`components.StellarAgeDiscovery`. The first tooltip implementation reads only
`AllAge`, so multi-era buildings such as Pendragon's Throne of Camelot lose their
population, happiness, boosts, production, and reward amounts.

Several secondary normalization errors make the partial output misleading:

- flag 32 is described as a Forge Point acceleration restriction, although it means
  instant production finish is disabled;
- raw resource identifiers such as `money`, `strategy_points`, and
  `all_goods_of_age` are exposed instead of in-game labels and icons;
- generic reward quantities are taken from the product reference instead of the
  resolved lookup reward;
- a whitelist silently discards valid boost types, including Quantum Incursion
  action-point collection and capacity;
- boosts are collapsed into a dictionary, losing repeated entries;
- population supplied through `staticResources` is displayed as a raw identifier;
- ally room identifiers are displayed without translation.

## Approved Design

### 1. Central component resolution

Add a pure resolver that returns a new entity-shaped dictionary. It copies
`components.AllAge` and overlays each top-level component supplied by the selected
era. If the era is absent or unknown, the resolver safely falls back to `AllAge`.
The source API object must not be mutated.

`render_building_tooltip` accepts an optional `era_key`. Building Details passes the
raw era identifier from the selected row. Existing helper functions continue to
accept entity-shaped dictionaries so current callers and focused tests remain valid.

### 2. Raw-first boost rendering

Preserve boost entries as a list. Render direct combined army boosts exactly as
provided. Where legacy data only contains separate attack and defence values,
retain the existing attacker/defender combined rows for compatibility. Never drop an
otherwise valid boost merely because it is absent from a whitelist; known boost
types receive translated labels and icons, while unknown types receive a readable
fallback label.

Targeted contexts (all, Guild Battlegrounds, Guild Expedition, and Quantum
Incursions) remain distinct in both label and icon.

### 3. Resource and reward normalization

Use one normalization table for static resources, production resources, costs, and
generic rewards. At minimum:

- `money` -> Coins
- `strategy_points` -> Forge Points
- `all_goods_of_age` -> Goods

Resolve generic rewards through the selected era's lookup. The lookup reward's
quantity, name, subtype, and icon metadata take precedence over incomplete product
references. Unknown rewards still render a stable fallback row instead of failing.

### 4. Accurate metadata and traits

Treat an absent `streetConnectionRequirement` as no road required, matching the
game/reference implementation, and preserve its `y` by `x` size ordering. Translate
ally room types. Interpret flag 32 as "Instant production finish disabled".
Recognize `socialInteraction` as an authoritative source for motivate/polish traits
in addition to legacy abilities.

### 5. Presentation and error handling

Keep the building name and image inside the tooltip renderer. Avoid duplicating the
name as an image caption. Building Details logs full exceptions but displays only a
localized, user-safe error.

### 6. Verification fixture

Add a compact fixture matching Pendragon's real shape: shared `AllAge` placement,
flags, road, and ally data plus `StellarAgeDiscovery` population, happiness, boosts,
production, and reward lookup. Assertions must verify the concrete rows that were
missing, not merely that some section exists.

## Out of Scope

- Per-square calculations; the tooltip always shows raw in-game values.
- Downloading per-building API files.
- Fabricating unavailable building-set or chain descriptions.
- Requiring all context-specific icon files; missing icons degrade to text while the
  manually supplied icon assets remain supported.

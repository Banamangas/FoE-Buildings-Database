# Lessons

- When an API loader's declared shape differs from the live payload, inspect the live
  top-level type and add a contract test before integrating it into UI code.
- Do not assume `components.AllAge` contains level-dependent building statistics.
  Real Forge of Empires entities split shared metadata and selected-era components;
  fixtures must model that split.
- Never infer an acronym's meaning from adjacent domain terminology. Confirm raw flag
  semantics against the game/reference implementation before translating it.
- When raw component absence may itself encode a default, compare the reference
  renderer before treating absence as unknown. Here, no street component explicitly
  means no road and the reference intentionally renders the API's `y` by `x` order.
- Preserve user-owned or explicitly scoped repository files. If project instructions
  and a prior cleanup request conflict, follow the latest explicit project
  instructions and keep task metadata isolated from product code.
- When reproducing another application's icons, trace the complete runtime resolver
  before extracting sprite coordinates. Forge Hammer's building tooltip resolves raw
  game keys through ForgeHX/CDN paths; `productions.png` belongs to a separate generic
  production-filter UI and is not the tooltip's icon source.
- Preserve raw domain keys and their exact feature suffixes when resolving assets.
  Do not invent aliases such as `_ge` or `_qi` when the reference uses `_gex` and
  `_gr`; add contract tests for representative production, boost, reward, and trait
  keys before wiring the resolver into rendering.

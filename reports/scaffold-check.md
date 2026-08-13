# Scaffold verification — 2026-08-12

Preview: http://localhost:8162 (launch config `network-map`, py http.server on
`C:\dev\livingston-network-map`).

## Rings mode (default)
- 89/89 nodes at fixed positions; hub at (0, 34, 0); listed nodes on
  drive-time rings (spot check: East Port Marina at r≈224, y=3).
- Decor present: ground disc, 26-block courthouse-square centerpiece,
  4 drive-time ring lines + labels.
- 368 meshes, 16 sprites (12 node labels in `focus` density + 4 ring labels).
- Console: zero errors.

## Force mode (data-mode="force")
- Fixed positions cleared (0/89), decor removed (0 ring lines), reheat called.
- **Residual:** actual node motion could not be observed headless — the layout
  ticks inside requestAnimationFrame, and the Browser pane was not compositing
  (hidden), so rAF is suspended. State transitions verified; motion itself needs
  the pane visible. Initial ring placement DID render, so the rAF loop works
  when the pane is shown.

## Palette switch (data-palette="print" → back to "midnight")
- backgroundColor followed the axis both ways (#faf8f4 ↔ #0a0f1e); node/link
  colors and decor rebuilt through the same applyAll path.

## Switcher
- PresetSwitcher panel present (bottom-right), five axes (mode, palette, glyph,
  labels, motion), combo persisted to localStorage + URL hash. Attribute writes
  on <html> drive the scene via MutationObserver — verified by setting the same
  attributes directly.

## Gotcha logged
- python http.server + browser heuristic caching served a stale module during
  dev; the module script tag now carries `?v=N`, bump on edit (same rule as the
  vault SW-cache memory).

## Label pass (S3) — 2026-08-12
- All 89 nodes carry halo-label sprites (93 sprites total incl. 4 ring labels).
- Focus density: 16 visible at overview distance; probe zoom to Standing Stone
  State Park revealed its label (<150 units), zoom-out hid it again.
- Proximity math uses data coords, so it verifies headless and is tick-independent.
- +4 road meshes in the town centerpiece (372 meshes total).

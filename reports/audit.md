# S5 audit — 2026-08-12

Code-sweep by sonnet subagent over index.html, src/app.js, src/style.css,
scripts/build_network.py; runtime probes by main session. 13 findings,
0 blockers. **All 13 fixed** — five were fixed mid-run before the sweep
reported (it read the pre-fix files), and its independent discovery of the
same five confirms they were real.

| # | Severity | Defect | Outcome |
|---|---|---|---|
| 1 | HIGH | Tooltip HTML built from unescaped source-data strings (XSS) | Fixed — `esc()` helper on every interpolated field |
| 2 | MEDIUM | Dedupe keyed on name only; same-named places in different towns would merge | Fixed — merge requires city agreement (or a missing city); current 3 dedupes unchanged |
| 3 | MEDIUM | Duplicate source rows would emit parallel `lists` edges | Fixed — emitted-edge set guards |
| 4 | LOW | Slug-collision suffix applied once, could still collide | Fixed — incrementing suffix loop |
| 5 | LOW | `ringRadius` used `\|\|`, treating a legit 0-minute drive as missing | Fixed — `??` |
| 6 | MEDIUM | Search surfaced nodes hidden by active filters; click flew camera to empty space | Fixed — hits pass `nodeVisible`; probe: "marina" 3 hits → 0 with listed off |
| 7 | MEDIUM | Unknown drive time hidden under band filters (reads as data gap) | Fixed — null distance always shows |
| 8 | HIGH | Title and search box overlapped at phone widths | Fixed — mobile breakpoint stacks them; geometry probe clean at 375px |
| 9 | MEDIUM | Legend chips wrapped up into the stats line on phones | Fixed — same breakpoint; probe clean |
| 10 | LOW | Print palette missing kicker colors for hub/built panel | Fixed — overrides added |
| 11 | MEDIUM | Search results had no listbox semantics or arrow-key path | Fixed — role=listbox/option + roving focus (Arrow/Enter/Escape), probe-verified |
| 12 | MEDIUM | Panel never took focus; no Escape to dismiss | Fixed — focus moves to close button, Escape closes, probe-verified |
| 13 | MEDIUM | `buildDecor` rebuilt without disposing geometries/materials/textures (GPU leak on every axis change) | Fixed — dispose walk before removal; scene object count stable at 644 across 6 palette cycles |

Post-fix: `scripts/build_network.py` output byte-identical intent (89 nodes /
92 edges / same 3 dedupes), `scripts/verify.py` 12/12, console error-free.

# S4 interactivity verification — 2026-08-12

All probes run against http://localhost:8162 (?v=4), console error-free.

## Info panel — 3 node probes
| Node | Result |
|---|---|
| Standing Stone State Park (listed) | Panel opened via search→click; meta "Hilham · Overton County · 20 min from the square"; cross-directory dedupe surfaces: "On our directories: Livingston Outdoors · Visit Livingston TN"; visit link → tnstateparks.com/parks/standing-stone |
| Oliver Printing Company (built) | Kicker "Built by Barnraised"; listed-in shows Middle TN Printers (the built+listed cross-link works) |
| Barnraised (hub) | Kicker "The studio", panel opens with camera fly-to |

## Search
- "Standing Stone State Park" → 1 hit; click focuses camera and opens panel.
- Enter selects first hit; Escape closes results.

## Filters
- Type chips: toggling "listed" off drops visible nodes 89 → 12 (exactly the
  hub+directories+built set); toggling back restores 89.
- Drive band ≤15 min: 38 visible (built/hub/directories exempt by design —
  the band filters listed places only).
- Stats bar renders: "4 directories · 7 sites built · 77 businesses & places
  connected · 92 links" and re-computes on filter change.

## Blurbs
- reports/blurb-check.json: 89 nodes, 0 empty blurbs (built-site copy authored
  in build_network.py, listed copy from source data files).

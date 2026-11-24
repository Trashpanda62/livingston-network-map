# Livingston network map

Live page: https://trashpanda62.github.io/livingston-network-map/

One page that maps the sites we built, the local directories we run, the places those directories list, and the businesses that still need a website. GitHub Pages serves the `main` branch.

## Status: static since 2026-11-24

The monthly prospect refresh is retired (owner decision, 2026-11-24). The map now stays on the last good data.

- The scheduled task `Vault Network Map Refresh` is disabled. It ran `C:\dev\ObsidianVault\ObsidianVault\scripts\network_map_refresh.py`.
- These files are frozen at the last good pull: `data/prospects.json`, `data/prospects-geocode.json`, `data/traffic.json`, `data/history/`.
- Do not run `scripts/find_prospects.py` or `scripts/fetch_traffic.py --refresh`. Their data provider rejects the old key, and a failed run writes empty results over good data.

## What still works without the refresh

These steps read only local files:

- `python -X utf8 scripts/build_network.py` rebuilds `data/network.json` from the directory repos. Run it when a directory adds or removes a listing.
- `python -X utf8 scripts/verify.py` checks the map and writes `reports/verify.md`. Push only when it is fully green.
- `python -X utf8 scripts/build_call_sheet.py` rebuilds the call sheet from `data/prospects.json`.

## To bring the refresh back

Add a working data-provider key, enable the scheduled task, and run the refresh once by hand. The refresh keeps the last good data and refuses to push when rows or phone numbers drop by half or when verify is red.

# Source data shapes (verified 2026-08-12)

## C:\dev\livingston-outdoors\data\livingston-outdoors.json
List of 40 place dicts. Fields used: `name`, `county`, `town`, `url`,
`drive_minutes` (routed, OSRM; `drive_source` says which), `drive_miles`,
`activities`, `best_for`, `blurb`. No lat/lon in this file;
`geocode-cache.json` is nominatim-URL-keyed and mostly empty hits — not used.
Ring placement uses `drive_minutes` + county wedge bearing.

## C:\dev\visit-livingston\data\places.json
Dict; list at `places` (29 items). Fields used: `name`, `category`, `city`,
`website` (falls back to `source_url`), `what_it_is`, `blurb`, `featured`.
No drive time — assigned from city lookup (nearly all Livingston/Overton).

## C:\dev\mtn-printers\data\mtn-printers.json
List of 11 shop dicts. Fields used: `name`, `city`, `county`, `url`, `blurb`,
`best_for`, `founded`, `featured`, `publisher_relationship`. No drive time —
assigned from city lookup (Nashville ~100 min, etc.).

## Built-sites roster (from vault: MMG Web Portfolio, Barnraised Owned Channels)
Hardcoded in `scripts/build_network.py::BUILT_SITES` — barnraised.design hub,
3 directories, bestmomcars.com, and 7 built sites incl. Oliver Printing
(also a middletnprinters listing → cross-edge).

## Dedupe rule
Cross-source match by normalized name (lowercase, alnum only). Same place in
two directories = one node, two `lists` edges. Domain is NOT the dedupe key:
recreation.gov / tnstateparks.com / cityoflivingston.net each host several
distinct places.

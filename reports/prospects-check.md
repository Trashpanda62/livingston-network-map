# Prospect sweep — spot check (2026-08-13)

Sweep result: 24 existing listed nodes flagged weak-web, 39 new no/weak-website
businesses found (Overton County, Bright Data SERP local packs, each candidate
verified against its Google knowledge panel — the panel carries a `site` key
exactly when Google shows a Website button). All geocoded rows within 55 km of
the square; 13 rows fall back to town-center placement.

## 5 verified rows (knowledge-panel evidence, from data/prospects.json `_kp`)

| Business | Panel found | Panel site | Verdict | Address |
|---|---|---|---|---|
| The Coop (944 reviews, 4.3) | yes | none | no-website ✓ | 209 S Spring St, Livingston |
| Waterloo Tire Service (135, 4.7) | yes | none | no-website ✓ | 519 W Main St, Livingston |
| The Coffee Shop (94, 4.8) | yes | facebook.com/acsquaredbakery | facebook-only ✓ | 101 S Court Square, Livingston |
| The Emporium (26, 4.8) | yes | facebook.com/livingstonemporium | facebook-only ✓ | 108 N Court Square, Livingston |
| Livingston Flower Basket (34, 4.7) | yes | livingstonflowerbasket.square.site | rented-subdomain ✓ | Livingston (town-center) |

## Reason distribution

- new: 27 no-website · 10 facebook-only · 2 rented-subdomain
- flagged existing: 13 dead-site (own domain, no CrUX traffic) · 10 aggregator-listing · 1 rented-subdomain

## Known limits

- "no-website" for a business with no knowledge panel at all is a best-effort
  call (5 rows), not panel-proven.
- 13 rows geocode to town-center jitter, not a street address.
- Zero-result categories (plumbers, electricians in Livingston; most satellite
  town/category pairs) returned no Google local pack — not evidence there are
  no such businesses.

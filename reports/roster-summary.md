# Seed rosters — proposed online-only properties

Harvested live from Google local packs via the Bright Data SERP zone
(`scripts/build_rosters.py`), then repaired by `scripts/verify_rosters.py`.

Two corrections are applied to the raw harvest. Records whose knowledge panel
resolves to a business outside Tennessee are dropped from every count (the
Byrdstown auto sweep pulled back a NAPA store in La Pine, Oregon). And a business
whose panel lookup failed outright is counted as **unconfirmed**, not as a web gap,
because a lookup that did not resolve is not evidence that no website exists.

`proven gap` therefore counts only businesses positively confirmed to lack a real
site of their own: no website at all, a Facebook page, a rented builder subdomain,
or nothing but an aggregator listing. Chains are recorded but flagged, not filtered.

| Concept | Businesses | In Overton Co. | Independents | Has own site | Proven gap | Unconfirmed | Dropped, out of state |
|---|---|---|---|---|---|---|---|
| Upper Cumberland Auto | 46 | 25 | 46 | 20 | 20 | 6 | 1 |
| Eat Livingston TN | 19 | 19 | 18 | 8 | 9 | 2 | 0 |
| Upper Cumberland Home Pros | 48 | 9 | 48 | 39 | 8 | 1 | 0 |
| Upper Cumberland Weddings | 33 | 12 | 33 | 23 | 7 | 3 | 0 |
| Livingston Events | 6 | 6 | 6 | 4 | 2 | 0 | 0 |

## Proven gap by reason

| Concept | no site at all | facebook only | rented subdomain | aggregator only |
|---|---|---|---|---|
| Upper Cumberland Auto | 16 | 4 | 0 | 0 |
| Eat Livingston TN | 6 | 3 | 0 | 0 |
| Upper Cumberland Home Pros | 8 | 0 | 0 | 0 |
| Upper Cumberland Weddings | 3 | 3 | 1 | 0 |
| Livingston Events | 1 | 1 | 0 | 0 |

## Harvest coverage

Google's local pack returns at most three businesses per query, so every roster
here is a seed from a fixed query grid, not a census of the category. Empty-pack
queries are listed so the build knows exactly which ground was walked and found
bare, as opposed to never walked.

| Concept | Queries run | Empty packs | Which came back empty |
|---|---|---|---|
| Upper Cumberland Auto | 19 | 3 | `oil change|Livingston`, `tire shops|Monroe`, `tire shops|Celina` |
| Eat Livingston TN | 14 | 7 | `breakfast|Livingston`, `diner|Livingston`, `ice cream|Livingston`, `restaurants|Rickman`, `restaurants|Hilham`, `restaurants|Alpine`, `restaurants|Allons` |
| Upper Cumberland Home Pros | 24 | 7 | `electricians|Livingston`, `plumbers|Livingston`, `septic tank service|Livingston`, `plumbers|Byrdstown`, `electricians|Jamestown`, `HVAC|Celina`, `plumbers|Celina` |
| Upper Cumberland Weddings | 16 | 5 | `wedding venues|Livingston`, `caterers|Livingston`, `wedding venues|Byrdstown`, `wedding venues|Celina`, `wedding venues|Gainesboro` |
| Livingston Events | 6 | 3 | `community centers|Livingston`, `banquet hall|Livingston`, `fairgrounds|Livingston` |

## Upper Cumberland Auto — top independents by review count

| Business | Town | Categories | Reviews | Own site? |
|---|---|---|---|---|
| CAR FIX Cookeville | Cookeville | auto repair | 2200 | yes, teamcarfix.com |
| Philly Auto | Byrdstown | auto repair | 2000 | unconfirmed |
| Strickland Brothers 10 Minute Oil Change | Livingston | auto repair | 739 | yes, sboilchange.com |
| Christian Brothers Automotive Celina | Celina | auto repair | 686 | yes, cbac.com |
| Tire Discounters | Cookeville | tire shops | 667 | yes, tirediscounters.com |
| Kent's Wholesale Tire | Rickman | tire shops | 495 | yes, kents-wholesale-tire.edan.io |
| Maggart Tire | Cookeville | tire shops | 386 | yes, maggarttire.com |
| Independent Auto and Diesel Repair | Livingston | diesel repair, auto repair | 207 | yes, independentautodieselrepair.com |
| Waterloo Tire Service | Livingston | tire shops | 135 | **no** (no-website) |
| Doc's Auto & Tire Center | Cookeville | auto repair | 126 | **no** (no-website) |
| Doug Freeman Tire Company LLC | Rickman | tire shops | 109 | yes, dougfreemantire.com |
| Kingdom Mobile Auto Repair | Monroe | auto repair | 108 | yes, kingdommobilerepair.com |

## Eat Livingston TN — top independents by review count

| Business | Town | Categories | Reviews | Own site? |
|---|---|---|---|---|
| The Coop | Livingston | restaurants, mexican restaurant | 944 | **no** (no-website) |
| Casa Mexicana | Livingston | mexican restaurant | 527 | yes, casamexicanalivingston.com |
| Casa Nueva Mexican Bar & Grill Inc. | Livingston | mexican restaurant | 445 | yes, casanuevatn.com |
| Brazen Que | Livingston | mexican restaurant, barbecue | 321 | yes, brazenque.com |
| Wired Coffee Co. | Livingston | coffee shops | 252 | **no** (no-website) |
| Maria Mezcal Grill and Cantina | Livingston | mexican restaurant | 230 | yes, mariamezcalgrillandcantinala.com |
| 1806 BBQ | Livingston | barbecue | 189 | yes, 1806bbq.com |
| Main & Monroe | Monroe | restaurants | 144 | yes, mainmonroelex.com |
| Scratch Kitchen | Monroe | restaurants | 114 | **no** (no-website) |
| The Sunset Restaurant by The Steel Coop | Monroe | restaurants | 102 | **no** (no-website) |
| The Coffee Shop | Livingston | coffee shops | 94 | **no** (facebook-only) |
| Southern Dreams Bakery | Livingston | bakeries | 91 | **no** (facebook-only) |

## Upper Cumberland Home Pros — top independents by review count

| Business | Town | Categories | Reviews | Own site? |
|---|---|---|---|---|
| Charles Stone Mechanical | Gainesboro | HVAC | 11000 | yes, charlesstonemechanical.com |
| Hiller Plumbing, Heating, Cooling & Electrical | Cookeville | plumbers | 3000 | yes, happyhiller.com |
| Tramont Heating Cooling Plumbing | Cookeville | HVAC | 787 | yes, tramonthvac.com |
| Pioneer Heating, Cooling, Electrical & Plumbing | Cookeville | HVAC | 782 | yes, pioneercomfort.com |
| One Hour Heating and Air Conditioning of Cookeville | Cookeville | HVAC | 705 | yes, onehourheatandair.com |
| Risher Roofing | Cookeville | roofing contractors | 433 | yes, risherroofing.com |
| Eco Home Solutions, Inc. | Livingston | HVAC | 387 | yes, ecohomesolutions.com |
| Henry Brothers Roofing, Inc. | Cookeville | roofing contractors | 384 | yes, henrybrothersroofing.com |
| Kindred Plumbing LLC | Jamestown | plumbers | 384 | yes, kindredplumbing.com |
| Putnam Plumbing | Cookeville | plumbers | 351 | yes, putnamplumbing.com |
| Modern Roofing Group | Cookeville | roofing contractors | 295 | yes, modernroofing-group.com |
| Speck Family Electric LLC - Your Preferred Electricians in Sparta & Cookeville | Cookeville | electricians | 246 | yes, speckfamilyelectric.com |

## Upper Cumberland Weddings — top independents by review count

| Business | Town | Categories | Reviews | Own site? |
|---|---|---|---|---|
| The White Dove Barn | Cookeville | wedding venues | 282 | yes, thewhitedovebarn.com |
| White Fox Wedding Photography | Livingston | wedding photographers | 214 | yes, whitefoxweddingphotography.com |
| 123 Bounce Party | Cookeville | event rentals | 197 | yes, 123bounceparty.com |
| Photography | Livingston | wedding photographers | 158 | yes, zachandsarahphotography.com |
| Towne & Country Flowers | Cookeville | florists | 149 | yes, towneandcountryflowers.com |
| Nashville DJ - Randy Spencer - Wedding DJ - Event DJ - Mobile DJ | Livingston | wedding DJ | 142 | **no** (no-website) |
| CookevilleDJ 5diamondproductions | Livingston | wedding DJ | 140 | yes, 5diamondproductions.com |
| Grade-A Catering | Cookeville | caterers | 135 | yes, gradeacatering.com |
| Go DJs Entertainment | Cookeville | wedding DJ | 116 | yes, godjsentertainment.com |
| The Estate at Sweetwater Creek | Jamestown | wedding venues | 106 | yes, sweetwatercreek.net |
| The Right Choice Catering & Gifts | Cookeville | caterers | 105 | yes, therightchoicecatering.com |
| Lanes' Bend | Cookeville | wedding venues | 102 | yes, lanesbend.com |

## Livingston Events — top independents by review count

| Business | Town | Categories | Reviews | Own site? |
|---|---|---|---|---|
| The Coop | Livingston | live music venues | 944 | **no** (no-website) |
| Central Park Livingston | Livingston | live music venues | 505 | yes, centralparklivingston.com |
| Empire Twin Theatre | Livingston | theater | 191 | yes, livingstonmovies.com |
| The Barn at Bilbrey’s Crossing | Livingston | event venues | 40 | yes, bilbreyscrossing.com |
| Bilbrey's Crossing Weddings & Events | Livingston | event venues | 29 | yes, bilbreyscrossing.com |
| Iron & Oak Event Center | Livingston | event venues, live music venues, theater | 25 | **no** (facebook-only) |

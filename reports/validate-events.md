# Concept E Validation — "Livingston Events"

VERDICT: BUILD-WITH-CHANGES — the gap is real (the county's own site says "no upcoming events," the regional Upper Cumberland calendar explicitly excludes Overton County, and the Fair's own site still shows a 2021 cancellation notice), but build it as a thin, *verifiably-current* calendar fed by the existing three-site network's authority and a weekly Facebook-sourcing routine — not as a "comprehensive aggregator," which Facebook's walled garden makes structurally impossible.

## Sources

| Source | URL | Maintained? | Machine-readable? |
|---|---|---|---|
| Livingston-Overton County Chamber of Commerce | https://discoverlivingstontn.com/events-calendar/ | Unconfirmed — page shell has no events in a static fetch (JS-rendered widget); a specific member event page (Little Patriots Parade) is indexed, so *something* is live. Runs on GrowthZone/ChamberMaster (URL pattern `eventcalendar/Details/...`) | The member subdomain (`members.discoverlivingstontn.com`) has a broken/mismatched SSL certificate (resolves to a generic `catchall-server-default.s417.sureserver.com`), so it could not be fetched at all by automated tools. GrowthZone calendars typically support per-event iCal export, but this could not be confirmed working here. |
| City of Livingston | https://www.cityoflivingston.net/ (Resources & Quick Links → Community Events Calendar) | Poor — the specific event URL found in search, `cityoflivingston.net/event/overton-county-fair/`, returned a plain 404. Homepage references a calendar but depth could not be verified. | HTML only, unconfirmed |
| Livingston Enterprise (newspaper) | https://www.livingstonenterprise.net/ | Unknown — site returned HTTP 403 (blocks automated fetch); has an active Facebook page (facebook.com/Livingston.Enterprise) | Blocked to fetch tools; no RSS found |
| Overton County News (newspaper) | https://www.overtoncountynews.com/calendar/ | **Yes** — real dated listings for the current week (Aug 13–19, 2026): meetings, a touring musical, library programs, recovery-meeting listings | HTML only (BLOX CMS). No RSS/iCal link found. |
| Standing Stone State Park / TN State Parks | https://tnstateparks.com/parks/standing-stone (event detail: https://tnstateparks.com/parks/event_details/standing-stone/) | Appears active — a search snippet surfaced a specific Aug 28, 2026 program and named annual events (Rolley Hole Marbles Championship, Spring Naturalist Rally, Car Show). Direct fetch returned HTTP 403 (bot-blocked), so this could not be independently confirmed by page inspection. Note: the campground is under renovation through late 2026 per the same search result. | Unconfirmed — site blocks automated fetching, so JSON-LD/RSS presence could not be checked |
| Overton County Fairgrounds / Overton County Fair | http://overtoncountyfair.com/events.html | Mixed — 2026 fair dates (July 16–26) and a full day-by-day schedule are posted, but the page also still displays a leftover "the 2021 Overton County Fair has been cancelled" banner that was never cleaned up | HTML only, no RSS/iCal |
| Livingston Academy athletics | https://www.livingstonwildcats.net/o/las/events (site runs on Apptegy CMS) | Unconfirmed — page content was truncated in fetch; MaxPreps (https://www.maxpreps.com/tn/livingston/livingston-academy-wildcats/football/) independently lists a Wildcats football schedule | HTML only on the school site; MaxPreps has structured schedule data but is a third party subject to its own terms |
| Overton County government | https://overtoncountytn.gov/events/ and /all-your-county-events-in-once-place/ | **No** — the county's own events page explicitly states "There are no upcoming events at this time," and the site displays an "UNDER CONSTRUCTION" banner. The "all your events in one place" page turned out to just link to a generic Outlook calendar. | Not applicable — no content |
| This Week In The Upper Cumberland (regional calendar) | https://theucnow.com/events/ | Yes, actively maintained (dated Aug 14–19, 2026 at fetch time) | HTML only; no RSS/iCal found. **Confirmed: it does not cover Livingston or Overton County at all** — every listed event was in Cookeville, Franklin, McMinnville, or Crossville |
| Central Park Livingston (town's flagship venue — concerts/festivals) | https://www.centralparklivingston.com/events-1 | Yes — real named acts with dates through Aug 29, 2026 (The SteelDrivers, The Wildflowers, Mixtape 80s tribute, Pioneer Days) | HTML only (Squarespace). No RSS/iCal/JSON-LD found. |
| Discover Livingston TN (Facebook) | https://www.facebook.com/discoverlivingstontn/ | Active — surfaced events (SteelDrivers May 30, Casino Night for a Cause June 13) that do not appear reliably on the Chamber's own website calendar | Not crawlable/scrapable per Facebook ToS |
| Eventbrite (incumbent aggregator) | https://www.eventbrite.com/d/tn--livingston/events/ | Thin — only 2 genuine Livingston-area events found; the other 8 listed were backfilled from Cookeville and unspecified locations | N/A (incumbent, not a source) |
| Patch (incumbent aggregator) | https://new.patch.com/tennessee/livingston-tn/calendar | Moderately active — a real mix (coalition meetings, two "Dry County ContraBand" concerts, a football game) but sparse and leans on user submissions | N/A (incumbent, not a source) |
| AmericanTowns.com (incumbent aggregator) | https://www.americantowns.com/overton-county-tn/events/ | **Dead** — homepage shows a farewell/"undergoing an evolution" message, no live events | N/A (incumbent, not a source) |

## Demand

I could not run a keyword-volume tool, so this is an **estimate**, based on: (a) the fact that Eventbrite, Patch, AllEvents.in, AmericanTowns, and TripAdvisor have all generated indexed pages specifically targeting "Livingston TN events / things to do" queries — platforms don't build landing pages for zero-volume terms — and (b) the population base (town ~4,000, county ~22,000). For a market this size, realistic monthly search volume for head terms like "things to do in Livingston TN" or "Overton County events" is very low — plausibly low tens to a couple hundred searches/month nationally, with real local intent concentrated into spikes around specific named events (Fair week in July, "Live in Livingston" concert dates, Christmas parade season) rather than steady "what's on" browsing. This is a long-tail/local-utility play, not a volume play — consistent with the brief's own framing that the strategic value is recurring traffic and standing outreach, not lead gen. Be aware: the honest read is that a meaningful share of real-time "what's happening" behavior in this county is not search behavior at all — it's asking in a Facebook group or checking a church/school Facebook page directly, which no search-volume estimate can capture.

## Incumbents

None of the ranking incumbents are good. Confirmed by direct inspection:
- **AmericanTowns.com** — the Overton County events page is dead (organizational farewell notice, zero events).
- **Eventbrite** — only 2 real Livingston events surfaced; padded with Cookeville-area events to look populated.
- **Patch** — the most credible of the third-party aggregators, but sparse and submission-dependent.
- **Overton County's own .gov site** — explicitly says no upcoming events and is flagged "under construction."
- **Overton County Fair's own site** — has a stale 2021 cancellation banner still live in 2026, undermining trust in an otherwise-current page.
- **The regional Upper Cumberland calendar (theucnow.com)** — actively maintained, but confirmed to not include Overton County at all, meaning the county isn't just underserved by weak sites, it's actively excluded from the one calendar that does the region well.

No incumbent is both current and complete. The bar to be the best listing for Livingston/Overton events specifically is low; the bar to rank above these domains in Google (Eventbrite/Patch carry real domain authority even with thin local content) is a separate, harder problem that content quality alone won't solve quickly.

## The Facebook problem

Real, and it cuts both ways as the brief anticipated. Evidence found in this research: the Chamber's own Facebook page (Discover Livingston TN) was the only source that surfaced "Casino Night For A Cause" (June 13, 2026) — that event did not appear in any of the website sources checked (Chamber website, Central Park Livingston, Overton County News calendar, city site). That is direct confirmation that some real, promoted local events exist *only* in Facebook posts.

This does not kill the concept, but it does mean:
- A "complete" aggregator is not achievable — Facebook groups/pages cannot legally be scraped and there is no API access for arbitrary group content.
- It does create the opening the brief hypothesizes: if you are not already in the right Facebook group (or a member's friend, or the church's specific page), you cannot find the event by searching. A human-curated weekly pass across the known local Facebook pages, republished as plain indexed web content, is a genuine service — but it is a *manual curation* product, not an automated aggregation product.
- The realistic ceiling is "best available public list," not "everything happening," and the site's positioning/marketing should say so rather than imply completeness it can't deliver.

## Maintenance cost

Split between what's genuinely automatable and what requires a human, based on the sources actually confirmed above:

- **Overton County News `/calendar/`** — real structured HTML with dated listings; a purpose-built scraper could pull this weekly in effectively zero ongoing human time once built (one-time build cost only).
- **Central Park Livingston** — updates seasonally (a handful of named events per season, not weekly); checking it is ~5 min/week amortized.
- **Overton County Fairgrounds/Fair** — effectively one big annual push plus occasional other bookings; ~5 min/week amortized outside of fair season.
- **Standing Stone State Park / TN State Parks** — the site actively blocks automated fetching (403s hit twice in this research), so this is realistically a **manual weekly check**, ~10 min/week.
- **Livingston Academy athletics** — schedules are published per season and rarely change week to week; a quick manual/scrape check is ~5 min/week.
- **Chamber calendar (GrowthZone)** — currently unreliable to access at all due to the broken SSL cert on the member subdomain; until that's fixed (which may require asking the Chamber directly, itself a good relationship-building excuse), this is a **manual check**, ~10–15 min/week.
- **Facebook-only events** (church suppers, yard sales, one-off community fundraisers like the Casino Night example found above) — this is the irreducible manual core. Scanning the 5–8 relevant pages/groups (Chamber, Discover Livingston TN, Overton County News, Overton County Fair, school boosters, a couple of community/yard-sale groups) at roughly 5 minutes each is **30–40 min/week** for a lean pass, more like 45–60 min/week for genuinely thorough sourcing plus data entry into the site.

**Total realistic estimate: roughly 60–90 minutes per week**, ongoing, forever — weighted toward the manual Facebook-sourcing step, which is also the step that doubles as the outreach mechanism the brief wants (scanning a business's Facebook page for their event is a natural lead-in to "want it on the calendar directly next time / want a listing on the site").

## Risk

- **The 60–90 min/week is permanent, not a launch cost.** For a one-person shop already running three other sites, this is the real risk: the same staleness that makes every incumbent here look bad (AmericanTowns dead, county .gov empty, Fair site's 2021 leftover banner) is the default failure mode for this site too if the weekly cadence slips even for a month.
- **Structural incompleteness will draw complaints.** Someone will notice their church supper or yard sale is missing because it only existed in a Facebook group that wasn't checked that week. This is unavoidable given the Facebook problem above, not a fixable bug.
- **No direct monetization path.** This concept explicitly isn't lead-gen; if it doesn't get tied back into the outreach/upsell motion for the other three Barnraised sites in practice (not just in theory), it's pure unpaid overhead.
- **New-domain authority problem.** Eventbrite and Patch already outrank a brand-new site on raw domain authority even though their Livingston-specific content is thin (confirmed above). Winning "best content" doesn't automatically win the SERP without deliberate internal linking from the existing three sites.
- **Bot-blocking on key sources.** Two of the most credible sources (TN State Parks, the Chamber's own member calendar) actively resisted or broke automated access during this research. Any plan to "mostly automate" this calendar should assume those two stay manual indefinitely.
- **Thin genuine local demand.** If the population-based volume estimate above is roughly right, there's a real possibility total traffic stays low regardless of execution quality — the win condition may need to be "the businesses cooperate because you asked directly," not "the site itself pulls meaningful search traffic."

## What the site must have to win

1. **A real submission path** (a simple form or a plainly listed email/text number) prominently on every page — since the actual strategic value is the standing excuse to contact every venue, the product needs to make "let me add your event" trivially easy to say yes to.
2. **Automated ingestion only where it's genuinely available** — Overton County News's calendar is the one confirmed source worth building a scraper for; Central Park Livingston, the Fairgrounds, and LA athletics are low-frequency enough to check manually without much cost. Don't invest in scraping Standing Stone or the Chamber calendar given the confirmed bot-blocking/SSL breakage — budget those as manual line items instead.
3. **A visible "last updated" timestamp**, per event and on the page as a whole. Given that literally every incumbent checked here (county .gov, Fair site, AmericanTowns) has an obvious staleness or dead-content problem, verifiable freshness — not comprehensiveness — is the actual differentiator available to claim.
4. **The weekly update run as a fixed outreach routine**, not a content chore — the Monday Facebook scan doubles as the sales-relationship touchpoint the brief describes; treat it as calendar time on the business side, not just dev/content time.
5. **Coverage of the low-competition "always on" long tail** (farmers market days/hours, recurring meetings, library story time) — this is exactly the kind of content none of the incumbents bother with and it's cheap to keep current once entered.
6. **Immediate cross-linking from livingstonoutdoors.com, visitlivingstontn.com, and middletnprinters.com** at launch. A brand-new fourth domain starts with zero authority; it should launch already wired into whatever local search equity the existing three sites carry rather than competing alone against Eventbrite/Patch's domain age.

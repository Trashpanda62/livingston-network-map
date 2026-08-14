"""Prospect sweep for the Livingston TN web-network map.

Two things, written to data/prospects.json:

1. FLAG existing "listed" nodes in network.json that have a weak web
   presence -- Facebook-only, an aggregator/directory listing, a rented
   site-builder subdomain, a duplicate host shared by other listed nodes,
   or a domain with no CrUX traffic data (data/traffic.json). Parks,
   public land, and events are not customers and are skipped.

2. SWEEP Google (via the Bright Data SERP zone, same pattern as
   fetch_traffic.py) for small businesses in Livingston + five outlying
   Overton County communities that are NOT already on the map and appear
   to have no website of their own.

Parser note: Bright Data's brd_json=1 parse of Google's local 3-pack (key
"snack_pack") is NOT a stable schema -- verified by hand against two live
queries before writing this. "restaurants in Livingston TN" came back with
only {address, cid, name, rank, rating, reviews_cnt, tags, type} and no site
field at all. "hair salons in Livingston TN" came back with an extra
{work_status, maps_link, site} on top of that, "site" being the business's
own URL when Google shows a Website button. The "address" field is also
unreliable: for the hair-salon-shaped response it's an attribute string like
"3+ years in business (dot) Livingston, TN, United States", not a street
address -- the real street address is embedded in "maps_link" instead
(".../maps/dir//<Name>,+<Street>,+<City>,+<ST Zip>,+United States/data=...").
This script therefore: (1) treats biz["site"] as authoritative "has a
website" when present; (2) when "site" is absent, resolves the question with
a per-candidate knowledge-panel query ('"<name>" <town> TN') -- the panel
carries a "site" key exactly when Google shows a Website button (verified
live: Brazen Que -> present, The Coop -> absent), and its full street
address, cached under "_kp" in the output file; (3) prefers the panel
address, then the street address parsed out of maps_link, then the raw
"address" field only when it starts with a house number. A site that is
just a Facebook page, a rented builder subdomain, or an aggregator listing
still counts as a prospect, with the more specific reason.

Idempotent: categories already swept (tracked in the "_done" key, as
"<category>|<town>" strings) are skipped unless --refresh. Geocoding results
are cached in data/prospects-geocode.json so reruns cost nothing there.

Secrets: BRIGHTDATA_API_KEY from .llm-system/orchestrator/secrets.local.env.
Run with: py -X utf8 find_prospects.py [--refresh]
"""
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SECRETS = Path(r"C:\dev\ObsidianVault\ObsidianVault\.llm-system\orchestrator\secrets.local.env")
NETWORK = ROOT / "data" / "network.json"
TRAFFIC = ROOT / "data" / "traffic.json"
OUT = ROOT / "data" / "prospects.json"
GEOCACHE = ROOT / "data" / "prospects-geocode.json"

LIVINGSTON_LAT = 36.3839
LIVINGSTON_LON = -85.3227
MAX_KM = 55

AGGREGATORS = {
    "facebook.com", "restaurantji.com", "tripadvisor.com", "tnstateparks.com",
    "exploremontereytn.com", "tngenweb.org", "recreation.gov", "courthouses.co",
    "cumberlandriverbasin.org", "cookevillebites.com", "ucbjournal.com",
    "overtoncountynews.com", "discoverlivingstontn.com", "picktnproducts.org",
    "overtoncountyarts.org", "explorejctn.com",
}
RENTED_SUFFIXES = (".square.site", ".wixsite.com", ".business.site", ".godaddysites.com")
PARK_CATEGORIES = {
    "hiking", "camping", "swimming", "boating", "fishing", "wildlife",
    "overlook", "waterfall", "biking", "playground", "history",
}

CATEGORIES = [
    "restaurants", "hair salons", "barber shops", "auto repair", "tire shops",
    "plumbers", "electricians", "HVAC", "landscaping", "gift shops", "boutiques",
    "hardware stores", "pharmacies", "dentists", "chiropractors", "veterinarians",
    "gyms", "daycares", "roofing contractors", "towing", "bakeries", "florists",
    "pet grooming", "real estate agents", "insurance agents",
]
SATELLITE_TOWNS = ["Monroe", "Allons", "Alpine", "Hilham", "Rickman"]
SATELLITE_CATEGORIES = ["restaurants", "auto repair", "hair salons"]

CHAIN_BLACKLIST = {
    "mcdonald's", "sonic", "subway", "taco bell", "kfc", "pizza hut", "domino's",
    "hardee's", "wendy's", "burger king", "dollar general", "dollar tree",
    "walmart", "autozone", "o'reilly", "advance auto", "napa", "walgreens",
    "cvs", "shell", "exxon", "marathon", "bp", "dairy queen", "little caesars",
    "huddle house", "cracker barrel", "waffle house", "arby's", "family dollar",
    "tractor supply", "verizon", "at&t", "t-mobile", "h&r block", "edward jones",
    "state farm", "farm bureau", "shoney's", "el tapatio",
}

# Organic-result hosts that are directories/aggregators rather than a
# business's own site -- used when deciding whether a snack-pack business
# "has a website" (see module docstring).
ORGANIC_AGGREGATOR_HOSTS = {
    "facebook.com", "yelp.com", "tripadvisor.com", "cookevillebites.com",
    "discoverlivingstontn.com", "restaurantji.com", "mapquest.com", "bbb.org",
    "yellowpages.com", "manta.com", "instagram.com", "linkedin.com",
    "opentable.com", "doordash.com", "grubhub.com", "ubereats.com",
    "google.com", "apple.com", "chamberofcommerce.com", "angi.com",
    "thumbtack.com", "nextdoor.com", "indeed.com", "glassdoor.com",
    "expedia.com", "booking.com", "tiktok.com", "twitter.com", "x.com",
    "loc8nearme.com", "cylex-usa.com", "hotfrog.com", "showmelocal.com",
}


def secret(name):
    for line in SECRETS.read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    raise KeyError(name)


def host_of(url):
    h = (urlparse(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def normalize_name(name):
    name = (name or "").lower()
    name = name.replace("&", " and ")
    name = re.sub(r"'s\b", "", name)
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def fuzzy_match(a, b):
    if not a or not b or len(a) < 3 or len(b) < 3:
        return a == b
    return a in b or b in a


def is_chain(name):
    n = normalize_name(name)
    for c in CHAIN_BLACKLIST:
        cn = normalize_name(c)
        if cn and re.search(r"\b" + re.escape(cn) + r"\b", n):
            return True
    return False


def slugify(name):
    n = normalize_name(name).strip().replace(" ", "-")
    return n or "prospect"


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def serp_raw(query, token):
    body = json.dumps({
        "zone": "serp_api1",
        "url": "https://www.google.com/search?q=" + urllib.parse.quote(query) + "&brd_json=1",
        "format": "raw",
    }).encode()
    req = urllib.request.Request(
        "https://api.brightdata.com/request", data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


STREET_RE = re.compile(r"^\d{1,6}\s+\S")


def address_from_maps_link(maps_link):
    """Pull the real street address out of a snack_pack maps_link, which
    embeds it as .../maps/dir//<Name>,+<Street>,+<City>,+<ST Zip>,+United
    States/data=... -- ground truth, unlike the free-text "address" field."""
    if not maps_link:
        return None
    m = re.search(r"maps/dir//(.+?)/data=", maps_link)
    if not m:
        return None
    decoded = urllib.parse.unquote_plus(m.group(1))
    parts = [p.strip() for p in decoded.split(",")]
    if len(parts) >= 2 and STREET_RE.match(parts[1]):
        return parts[1]
    return None


def business_address(biz):
    addr = address_from_maps_link(biz.get("maps_link"))
    if addr:
        return addr
    raw = (biz.get("address") or "").strip()
    if STREET_RE.match(raw):
        return raw
    return None


def kp_site_lookup(name, town, token, kp_cache):
    """Knowledge-panel website check: the panel carries a "site" key exactly
    when Google shows a Website button for the business (verified live:
    Brazen Que -> site present; The Coop -> absent). Authoritative where the
    snack_pack schema is not. Cached under "_kp" in the output file so
    reruns are free."""
    key = f"{normalize_name(name)}|{town}"
    if key in kp_cache:
        return kp_cache[key]
    entry = {"found": False, "site": None, "address": None,
             "reviews": None, "rating": None, "phone": None}
    try:
        data = serp_raw(f'"{name}" {town} TN', token)
        k = data.get("knowledge") or {}
        if k.get("name"):
            entry = {"found": True, "site": k.get("site"),
                     "address": k.get("address"), "phone": k.get("phone"),
                     "reviews": k.get("reviews_cnt"), "rating": k.get("rating")}
    except Exception as e:  # noqa: BLE001
        print(f"    kp error for {name}: {e}", flush=True)
    kp_cache[key] = entry
    time.sleep(0.5)
    return entry


def prospect_reason(site_url):
    """Classify a website link into a prospect reason, or None when the
    business has a real site of its own (not a prospect)."""
    if not site_url:
        return "no-website"
    host = host_of(site_url)
    if host == "facebook.com":
        return "facebook-only"
    if host.endswith(RENTED_SUFFIXES):
        return "rented-subdomain"
    if host in AGGREGATORS or host in ORGANIC_AGGREGATOR_HOSTS:
        return "aggregator-listing"
    return None


# Civic/public-lands hosts are never customers, whatever the category.
PUBLIC_HOST_RE = re.compile(r"(\.gov$|\.mil$|^recreation\.gov$|^tnstateparks\.com$"
                            r"|corpslakes|^cityoflivingston\.net$)")
# Places that aren't businesses no matter who hosts their page.
NON_BUSINESS_NAME_RE = re.compile(r"\b(cemetery|church|byway|wma|wildlife management"
                                  r"|mural trail|rail trail|central trail)\b", re.I)


def flag_listed(net, traffic):
    listed = [n for n in net["nodes"] if n.get("type") == "listed" and n.get("url")]
    # Events share their host with the org that runs them; counting them would
    # wrongly flag the owner's real site as "shared host".
    host_counts = Counter(host_of(n["url"]) for n in listed
                          if n.get("category") != "events")
    flagged = {}
    for n in listed:
        cat = n.get("category")
        if cat == "events":
            continue
        host = host_of(n["url"])
        if PUBLIC_HOST_RE.search(host):
            continue
        if NON_BUSINESS_NAME_RE.search(n.get("name") or ""):
            continue
        reason = None
        if host == "facebook.com":
            reason = "facebook-only"
        elif host in AGGREGATORS:
            reason = "aggregator-listing"
        elif host.endswith(RENTED_SUFFIXES):
            reason = "rented-subdomain"
        elif host_counts.get(host, 0) > 1:
            reason = "aggregator-listing"
        elif traffic.get(n["id"], {}).get("crux") is False:
            reason = "dead-site"
        # Parks/trails/water spots on an aggregator page are public places,
        # not customers; a park-category node only counts when it owns (or
        # rents) a domain -- a marina or resort operator with a dead site.
        if reason in ("aggregator-listing", "facebook-only") and cat in PARK_CATEGORIES:
            continue
        if reason:
            flagged[n["id"]] = {"reason": reason, "reviews": traffic.get(n["id"], {}).get("reviews")}
    return flagged


def geocode(address, city, cache):
    if not address:
        return {"lat": None, "lon": None}
    # Knowledge-panel addresses are already fully qualified.
    key = address if ("," in address and " TN" in address) else f"{address}, {city} TN"
    if key in cache:
        return {"lat": cache[key]["lat"], "lon": cache[key]["lon"]}
    q = urllib.parse.quote(key)
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={q}"
    req = urllib.request.Request(url, headers={"User-Agent": "livingston-network-map/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            hits = json.load(r)
        result = {"lat": None, "lon": None, "method": "town-center"}
        if hits:
            lat, lon = float(hits[0]["lat"]), float(hits[0]["lon"])
            if haversine_km(lat, lon, LIVINGSTON_LAT, LIVINGSTON_LON) <= MAX_KM:
                result = {"lat": lat, "lon": lon, "method": "address"}
        cache[key] = result
    except Exception as e:  # noqa: BLE001
        print(f"    geocode error for {key}: {e}", flush=True)
        cache[key] = {"lat": None, "lon": None, "method": "town-center"}
    time.sleep(1.1)
    return {"lat": cache[key]["lat"], "lon": cache[key]["lon"]}


def sweep_new(token, net, out_data, geocache, refresh):
    kp_cache = out_data.setdefault("_kp", {})
    net_names = [normalize_name(n["name"]) for n in net["nodes"]]
    tasks = [(cat, "Livingston") for cat in CATEGORIES]
    for town in SATELLITE_TOWNS:
        for cat in SATELLITE_CATEGORIES:
            tasks.append((cat, town))

    done = set(out_data.get("_done", []))
    seen_ids = {p["id"] for p in out_data["new"]}
    zero_result = []

    for cat, town in tasks:
        tag = f"{cat}|{town}"
        if tag in done and not refresh:
            continue
        if refresh:
            out_data["new"] = [p for p in out_data["new"] if not (p["category"] == cat and p["city"] == town)]
            seen_ids = {p["id"] for p in out_data["new"]}

        query = f"{cat} in {town} TN"
        try:
            data = serp_raw(query, token)
        except Exception as e:  # noqa: BLE001
            print(f"  ! {tag}: {e}", flush=True)
            time.sleep(0.5)
            continue

        local = data.get("snack_pack") or []
        if not local:
            zero_result.append(tag)

        added = 0
        for biz in local:
            name = biz.get("name")
            if not name or is_chain(name):
                continue
            norm = normalize_name(name)
            if any(fuzzy_match(norm, nn) for nn in net_names):
                continue
            site = biz.get("site") or biz.get("website")
            kp = None
            if site:
                reason = prospect_reason(site)
            else:
                kp = kp_site_lookup(name, town, token, kp_cache)
                reason = prospect_reason(kp["site"]) if kp["found"] else "no-website"
            if not reason:
                continue

            base_id = slugify(name)
            pid, n2 = base_id, 2
            while pid in seen_ids:
                pid = f"{base_id}-{n2}"
                n2 += 1
            seen_ids.add(pid)

            address = (kp and kp.get("address")) or business_address(biz)
            geo = geocode(address, town, geocache)
            out_data["new"].append({
                "id": pid,
                "name": name,
                "category": cat,
                "city": town,
                "address": address,
                "lat": geo["lat"],
                "lon": geo["lon"],
                "reviews": (kp and kp.get("reviews")) or biz.get("reviews_cnt"),
                "rating": (kp and kp.get("rating")) or biz.get("rating"),
                "reason": reason,
            })
            added += 1

        done.add(tag)
        out_data["_done"] = sorted(done)
        OUT.write_text(json.dumps(out_data, indent=1), encoding="utf-8")
        GEOCACHE.write_text(json.dumps(geocache, indent=1), encoding="utf-8")
        print(f"  {tag}: local={len(local)} new={added}", flush=True)
        time.sleep(0.5)

    return zero_result


def phones_pass(token, net, out_data):
    """Fill phone (and any missing address) for every prospect — new rows and
    flagged listed nodes — from their knowledge panels, for the call sheet.
    Cached entries without a phone key predate this pass and are re-queried."""
    kp_cache = out_data.setdefault("_kp", {})
    listed_by_id = {n["id"]: n for n in net["nodes"]}
    jobs = [(row["name"], row["city"], row) for row in out_data["new"]]
    for pid, entry in out_data["flagged"].items():
        n = listed_by_id.get(pid)
        if n:
            entry["name"] = n["name"]
            jobs.append((n["name"], n.get("city") or "Livingston", entry))
    done = 0
    for name, town, target in jobs:
        key = f"{normalize_name(name)}|{town}"
        e = kp_cache.get(key)
        if e is None or "phone" not in e:
            kp_cache.pop(key, None)
            e = kp_site_lookup(name, town, token, kp_cache)
        if e.get("phone"):
            target["phone"] = e["phone"]
        if e.get("address") and not target.get("address"):
            target["address"] = e["address"]
        done += 1
        if done % 10 == 0:
            OUT.write_text(json.dumps(out_data, indent=1), encoding="utf-8")
            print(f"  phones {done}/{len(jobs)}", flush=True)
    OUT.write_text(json.dumps(out_data, indent=1), encoding="utf-8")
    with_phone = sum(1 for _, _, t in jobs if t.get("phone"))
    print(f"phones: {with_phone}/{len(jobs)} filled", flush=True)


def main() -> int:
    refresh = "--refresh" in sys.argv
    net = json.loads(NETWORK.read_text(encoding="utf-8"))
    traffic = json.loads(TRAFFIC.read_text(encoding="utf-8")) if TRAFFIC.exists() else {}
    token = secret("BRIGHTDATA_API_KEY")

    if OUT.exists() and not refresh:
        out_data = json.loads(OUT.read_text(encoding="utf-8"))
    else:
        out_data = {}
    out_data.setdefault("flagged", {})
    out_data.setdefault("new", [])
    out_data.setdefault("_done", [])

    geocache = json.loads(GEOCACHE.read_text(encoding="utf-8")) if GEOCACHE.exists() else {}

    if "--phones" in sys.argv:
        phones_pass(token, net, out_data)
        return 0

    print("Flagging weak-presence listed nodes...", flush=True)
    out_data["flagged"] = flag_listed(net, traffic)
    OUT.write_text(json.dumps(out_data, indent=1), encoding="utf-8")
    print(f"  flagged={len(out_data['flagged'])}", flush=True)

    print("Sweeping for new prospects...", flush=True)
    zero_result = sweep_new(token, net, out_data, geocache, refresh)

    # Cross-category/town dedupe: the same shop answers several queries
    # ("T & M Automotive" for both Livingston and Rickman; case variants of
    # one bakery). Keep the geocoded row, else the first seen.
    by_name = {}
    for row in out_data["new"]:
        key = normalize_name(row["name"])
        keep = by_name.get(key)
        if keep is None or (not keep.get("lat") and row.get("lat")):
            by_name[key] = row
    if len(by_name) != len(out_data["new"]):
        print(f"  deduped {len(out_data['new']) - len(by_name)} repeat rows", flush=True)
    out_data["new"] = list(by_name.values())

    # Satellite-town rows with no street geocode get their town center plus a
    # deterministic sub-km jitter, marked geo_method town-approx so the panel
    # can say the position is approximate. Livingston rows stay null: the map
    # already has an honest fallback ring at the edge of downtown for those.
    import hashlib
    for row in out_data["new"]:
        if row.get("lat") or row.get("city") == "Livingston":
            row.setdefault("geo_method", "address" if row.get("lat") else None)
            continue
        tc = geocode(f"{row['city']}, Overton County", "", geocache)
        if tc["lat"]:
            h = int(hashlib.sha1(row["id"].encode()).hexdigest()[:8], 16)
            row["lat"] = tc["lat"] + ((h % 1000) / 1000 - 0.5) * 0.008
            row["lon"] = tc["lon"] + ((h // 1000 % 1000) / 1000 - 0.5) * 0.008
            row["geo_method"] = "town-approx"
    OUT.write_text(json.dumps(out_data, indent=1), encoding="utf-8")
    GEOCACHE.write_text(json.dumps(geocache, indent=1), encoding="utf-8")

    print(f"done: flagged={len(out_data['flagged'])} new={len(out_data['new'])}", flush=True)
    if zero_result:
        print("zero-result categories: " + ", ".join(zero_result), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

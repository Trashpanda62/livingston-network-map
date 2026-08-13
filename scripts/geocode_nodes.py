"""Geocode in-town nodes (city == Livingston) via Nominatim, cached.

Writes data/geocode.json: {node_id: {lat, lon, method}}. Nodes that fail all
attempts are recorded with null coords so the map places them at a fallback
ring and the gap is visible rather than silent. 1 req/s per Nominatim policy.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "livingston-network-map/1.0 (steve@maxfieldmanagementgroup.com)"}
VIEWBOX = "-85.346,36.401,-85.299,36.366"  # lon,lat,lon,lat — Livingston bbox

# Street addresses known from source data (visit places carry their own).
KNOWN_ADDR = {
    "oliver-printing": "415 West Main Street, Livingston, TN 38570",
    # Verified NAP from the vault (Livingston SERP Fixes 2026-06).
    "livingston-garden-center": "1133 Byrdstown Hwy, Livingston, TN 38570",
}

# Venue grounding for events/places whose own name will never geocode. Facts
# from the visit-livingston copy: square events happen on the courthouse
# square; the fair at the county fairgrounds.
VENUE_HINTS = {
    "overton-county-fair": "Overton County Fairgrounds, Livingston, TN",
    "fall-o-ween-in-livingston": "Court Square, Livingston, TN",
    "paint-livingston": "Court Square, Livingston, TN",
    "livingston-overton-county-farmers-market": "Overton County Fairgrounds, Livingston, TN",
    "central-park-livingston": "South Spring Street, Livingston, TN",
}

STREET_WORDS = {"st": "Street", "ave": "Avenue", "dr": "Drive", "rd": "Road",
                "hwy": "Highway", "blvd": "Boulevard", "ln": "Lane", "ct": "Court"}


def street_of(addr):
    """'140 S Spring St, Livingston, TN 38570' -> 'S Spring Street, Livingston, TN'."""
    first = addr.split(",")[0].strip()
    parts = first.split()
    if parts and parts[0].isdigit():
        parts = parts[1:]
    if not parts:
        return None
    if parts[-1].rstrip(".").lower() in STREET_WORDS:
        parts[-1] = STREET_WORDS[parts[-1].rstrip(".").lower()]
    return " ".join(parts) + ", Livingston, TN"


def query(q, bounded):
    url = ("https://nominatim.openstreetmap.org/search?format=json&limit=1"
           f"&countrycodes=us&viewbox={VIEWBOX}&bounded={int(bounded)}"
           f"&q={urllib.parse.quote(q)}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        hits = json.load(r)
    time.sleep(1.1)
    return (float(hits[0]["lat"]), float(hits[0]["lon"])) if hits else None


def main() -> int:
    net = json.loads((ROOT / "data" / "network.json").read_text(encoding="utf-8"))
    visit = json.loads(Path(r"C:\dev\visit-livingston\data\places.json").read_text(encoding="utf-8"))
    printers = json.loads(Path(r"C:\dev\mtn-printers\data\mtn-printers.json").read_text(encoding="utf-8"))
    addr_by_name = {p["name"].lower(): p.get("address") for p in visit["places"]}
    addr_by_name.update({p["name"].lower(): p.get("address") for p in printers})

    cache_path = ROOT / "data" / "geocode.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    # Every node is a target now that the map covers the 30-mile region, not
    # just downtown. Virtual web properties (hub/directories) stay un-geocoded
    # — they live on the campus card, not at a street address.
    VIRTUAL = {"barnraised", "livingston-outdoors", "visit-livingston-tn",
               "middle-tn-printers", "best-mom-cars", "tapestry-acres",
               "to-the-max-rv", "oak-ridge-peptides", "ridgeline-aerial",
               "obscura-studio"}
    targets = [n for n in net["nodes"] if n["id"] not in VIRTUAL]
    ok = fail = 0
    for n in targets:
        if n["id"] in cache and cache[n["id"]].get("lat"):
            ok += 1
            continue
        city = (n.get("city") or "").strip()
        in_town = city.lower() == "livingston"
        addr = KNOWN_ADDR.get(n["id"]) or addr_by_name.get(n["name"].lower())
        attempts = []
        if addr:
            attempts.append((addr, False, "address"))
        if in_town:
            attempts.append((f'{n["name"]}, Livingston, Tennessee', True, "name-bounded"))
            attempts.append((f'{n["name"]}, Livingston, TN', False, "name-open"))
        else:
            if city:
                attempts.append((f'{n["name"]}, {city}, Tennessee', False, "name-city"))
            attempts.append((f'{n["name"]}, Tennessee', False, "name-state"))
        if n["id"] in VENUE_HINTS:
            attempts.append((VENUE_HINTS[n["id"]], True, "venue-approx"))
        if addr and street_of(addr) and in_town:
            attempts.append((street_of(addr), True, "street-approx"))
        hit = None
        for q, bounded, method in attempts:
            try:
                hit = query(q, bounded)
            except Exception as e:  # noqa: BLE001 — keep going, record the gap
                print(f"  ! {n['id']}: {e}", flush=True)
                hit = None
            if hit:
                cache[n["id"]] = {"lat": hit[0], "lon": hit[1], "method": method}
                ok += 1
                break
        if not hit:
            cache[n["id"]] = {"lat": None, "lon": None, "method": "failed"}
            fail += 1
        print(f"  {n['id']}: {cache[n['id']]['method']}", flush=True)

    cache_path.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    print(f"geocoded ok={ok} failed={fail} of {len(targets)} nodes -> {cache_path}")
    return 0 if ok > 15 else 1


if __name__ == "__main__":
    sys.exit(main())

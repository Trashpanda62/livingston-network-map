"""Second-chance geocoding for nodes the main pass failed.

Pass 1: retry Nominatim with simplified names (suffixes like "Recreation
Area" / "and Resort" stripped). Pass 2: fall back to the node's town center
with a small deterministic jitter, recorded as method "town-approx" so the
approximation is visible in the data, never silent.
"""
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "livingston-network-map/1.0 (steve@maxfieldmanagementgroup.com)"}

STRIP = re.compile(
    r"\s*\(.*?\)|\b(and resort|resort|recreation area( and campground)?|"
    r"primitive camping|campground and day use|day use|usace.*|wma|"
    r"wildlife management area|damsite|overlook|segment)\b", re.I)


import math

# Reject hits farther than ~34 miles from the square — a simplified name that
# matches some other Tennessee town is worse than the town-center fallback.
SQ_LAT, SQ_LON = 36.3839, -85.3227
MAX_KM = 55.0


def km_from_square(lat, lon):
    dlat = (lat - SQ_LAT) * 110.54
    dlon = (lon - SQ_LON) * 111.32 * math.cos(math.radians(SQ_LAT))
    return math.hypot(dlat, dlon)


def query(q):
    url = ("https://nominatim.openstreetmap.org/search?format=json&limit=1"
           f"&countrycodes=us&q={urllib.parse.quote(q)}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        hits = json.load(r)
    time.sleep(1.1)
    return (float(hits[0]["lat"]), float(hits[0]["lon"])) if hits else None


def main() -> int:
    net = json.loads((ROOT / "data" / "network.json").read_text(encoding="utf-8"))
    cache_path = ROOT / "data" / "geocode.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    by_id = {n["id"]: n for n in net["nodes"]}

    failed = [nid for nid, v in cache.items()
              if not v.get("lat") and nid in by_id
              and by_id[nid]["type"] == "listed"]
    print(f"{len(failed)} failed nodes to rescue", flush=True)
    town_cache = {}
    rescued = approx = still = 0
    for nid in failed:
        n = by_id[nid]
        city = (n.get("city") or "").strip()
        simple = STRIP.sub("", n["name"]).strip(" ,-")
        hit = None
        method = None
        attempts = []
        if simple and simple.lower() != n["name"].lower():
            if city:
                attempts.append((f"{simple}, {city}, Tennessee", "name-simplified"))
            attempts.append((f"{simple}, Tennessee", "name-simplified"))
        for q, m in attempts:
            try:
                hit = query(q)
            except Exception as e:  # noqa: BLE001
                print(f"  ! {nid}: {e}", flush=True)
                hit = None
            if hit and km_from_square(*hit) > MAX_KM and (n.get("drive_min") or 0) < 60:
                print(f"  ~ {nid}: rejected far hit {hit}", flush=True)
                hit = None
            if hit:
                method = m
                break
        if not hit and not city and (n.get("county") or "") == "Overton":
            city = "Livingston"  # rural Overton County per the source data
        if not hit and city:
            # Town-center fallback with deterministic jitter (< ~1 km).
            if city not in town_cache:
                try:
                    town_cache[city] = query(f"{city}, Tennessee")
                except Exception:  # noqa: BLE001
                    town_cache[city] = None
            base = town_cache[city]
            if base:
                h = hashlib.sha1(nid.encode()).digest()
                jlat = (h[0] / 255 - 0.5) * 0.016
                jlon = (h[1] / 255 - 0.5) * 0.016
                hit = (base[0] + jlat, base[1] + jlon)
                method = "town-approx"
        if hit:
            cache[nid] = {"lat": hit[0], "lon": hit[1], "method": method}
            if method == "town-approx":
                approx += 1
            else:
                rescued += 1
        else:
            still += 1
        print(f"  {nid}: {method or 'still-failed'}", flush=True)

    cache_path.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    print(f"rescued={rescued} town-approx={approx} still-failed={still}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

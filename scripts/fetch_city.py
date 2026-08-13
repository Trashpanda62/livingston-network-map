"""Fetch Livingston TN street/building/water geometry from Overpass API.

Writes data/osm-raw.json. Re-runnable; one POST, ~1-3 MB response.
"""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Bbox around Livingston: courthouse square 36.3839, -85.3227
BBOX = "36.366,-85.346,36.401,-85.299"
QUERY = f"""
[out:json][timeout:90];
(
  way["highway"]({BBOX});
  way["building"]({BBOX});
  way["waterway"]({BBOX});
  way["natural"="water"]({BBOX});
);
out geom;
"""


def main() -> int:
    req = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=QUERY.encode(),
        headers={"User-Agent": "livingston-network-map/1.0 (steve@maxfieldmanagementgroup.com)"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    ways = [e for e in data.get("elements", []) if e.get("type") == "way"]
    out = ROOT / "data" / "osm-raw.json"
    out.write_text(json.dumps(data), encoding="utf-8")
    kinds = {}
    for w in ways:
        t = w.get("tags", {})
        k = "highway" if "highway" in t else "building" if "building" in t else "water"
        kinds[k] = kinds.get(k, 0) + 1
    print(f"ways={len(ways)} {kinds} -> {out}")
    return 0 if len(ways) > 100 else 1


if __name__ == "__main__":
    sys.exit(main())

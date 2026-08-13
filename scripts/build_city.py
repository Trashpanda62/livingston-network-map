"""Convert data/osm-raw.json into data/city.json for the 3D city base map.

Local coordinate frame: meters east/north of the courthouse square, then
scaled to scene units (1 unit = 12 m). +x = east, +z = south (three.js ground
plane, north = -z).
"""
import json
import sys
from pathlib import Path

from geo import LAT0, LON0, M_PER_UNIT, to_local

ROOT = Path(__file__).resolve().parent.parent

KEEP_HIGHWAY = {
    "motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
    "residential", "living_street", "service", "footway", "path", "track",
    "primary_link", "secondary_link", "tertiary_link",
}


def est_height(tags):
    if "height" in tags:
        try:
            return min(float(tags["height"].split()[0]), 20.0) / M_PER_UNIT
        except ValueError:
            pass
    lvl = tags.get("building:levels")
    if lvl:
        try:
            return max(1.0, float(lvl)) * 3.2 / M_PER_UNIT
        except ValueError:
            pass
    b = tags.get("building", "yes")
    if b in ("church", "commercial", "retail", "public", "school", "courthouse"):
        return 7.0 / M_PER_UNIT
    return 4.5 / M_PER_UNIT


def main() -> int:
    raw = json.loads((ROOT / "data" / "osm-raw.json").read_text(encoding="utf-8"))
    streets, buildings, water = [], [], []
    for w in raw.get("elements", []):
        if w.get("type") != "way" or "geometry" not in w:
            continue
        tags = w.get("tags", {})
        pts = [to_local(g["lat"], g["lon"]) for g in w["geometry"]]
        if len(pts) < 2:
            continue
        if "highway" in tags:
            cls = tags["highway"]
            if cls in KEEP_HIGHWAY:
                streets.append({"class": cls, "pts": pts, "name": tags.get("name", "")})
        elif "building" in tags:
            buildings.append({"pts": pts, "h": round(est_height(tags), 3)})
        elif "waterway" in tags or tags.get("natural") == "water":
            water.append({"pts": pts, "area": tags.get("natural") == "water"})
    out = {
        "meters_per_unit": M_PER_UNIT,
        "center": {"lat": LAT0, "lon": LON0},
        "streets": streets, "buildings": buildings, "water": water,
    }
    dest = ROOT / "data" / "city.json"
    dest.write_text(json.dumps(out), encoding="utf-8")
    print(f"streets={len(streets)} buildings={len(buildings)} water={len(water)} "
          f"-> {dest} ({dest.stat().st_size // 1024} KB)")
    return 0 if streets and buildings else 1


if __name__ == "__main__":
    sys.exit(main())

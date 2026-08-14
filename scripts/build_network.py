"""Build network.json for the Livingston Network Map.

Reads the two directory data files plus the hardcoded built-sites roster,
dedupes places that appear in more than one directory, and emits
data/network.json (nodes + edges) and reports/network-stats.json.

Re-runnable: run again after any directory grows and redeploy the map.
"""
import json
import re
import sys
from pathlib import Path

from geo import to_local

ROOT = Path(__file__).resolve().parent.parent
OUTDOORS = Path(r"C:\dev\livingston-outdoors\data\livingston-outdoors.json")
VISIT = Path(r"C:\dev\visit-livingston\data\places.json")

# Approximate drive minutes from the Livingston square, by city, for sources
# that carry no routed time. Stylized ring placement only — not navigation.
CITY_MINUTES = {
    "livingston": 2, "monroe": 15, "allons": 12, "alpine": 15, "hilham": 15,
    "cookeville": 25, "algood": 25, "baxter": 35, "gainesboro": 30,
    "celina": 30, "byrdstown": 35, "jamestown": 40, "allardt": 45,
    "crawford": 25, "rickman": 15, "nashville": 100, "franklin": 115,
    "la vergne": 90, "lavergne": 90, "gallatin": 85, "clarksville": 145,
}

# Bearing wedges (degrees, compass-ish) per county for the rings view, so
# nodes fan out in roughly the true direction from Livingston.
COUNTY_BEARING = {
    "Overton": (150, 260), "Clay": (315, 355), "Pickett": (10, 50),
    "Fentress": (60, 110), "Putnam": (170, 220), "Jackson": (250, 300),
    "Davidson": (230, 250), "Williamson": (225, 240), "Rutherford": (200, 220),
    "Sumner": (250, 270), "Montgomery": (270, 290),
}

BR = "barnraised"
BUILT_SITES = [
    # id, name, url, city, county, type, blurb
    (BR, "Barnraised", "https://barnraised.design", "Livingston", "Overton", "hub",
     "Steve's web studio — small-business websites, photography, drone. Every site on this map traces back here."),
    ("livingston-outdoors", "Livingston Outdoors", "https://livingstonoutdoors.com", "Livingston", "Overton", "directory",
     "Photo-led directory of 40 outdoor places within 45 minutes of Livingston."),
    ("visit-livingston-tn", "Visit Livingston TN", "https://visitlivingstontn.com", "Livingston", "Overton", "directory",
     "First-timer's editorial guide to Livingston and Overton County — 29 places."),
    ("livingston-garden-center", "Livingston Garden Center", "https://livingstongardencenter.com", "Livingston", "Overton", "built",
     "Client build — pickup-ordering garden center site, order by 5 PM for next-day pickup."),
    ("tapestry-acres", "Tapestry Acres", "https://tapestryacres.com", "Monroe", "Overton", "built",
     "Own venture — alpaca farm and glamping stays outside Livingston."),
    ("to-the-max-rv", "To The Max RV", "https://sites.obscurastudio.design/s/to-the-max-rv", "Monroe", "Overton", "built",
     "Own venture — RV rental based at the Tapestry Acres farm."),
    ("ridgeline-aerial", "Ridgeline Aerial", "https://sites.obscurastudio.design/s/ridgeline-aerial", "Livingston", "Overton", "built",
     "Client build — drone and aerial photography, credited to Barnraised."),
    ("oliver-printing", "Oliver Printing Company", "https://oliverprintingcompany.com", "Livingston", "Overton", "built",
     "Livingston print shop since 1967 — Barnraised sample site built; also featured on Middle TN Printers."),
]


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def city_minutes(city: str):
    return CITY_MINUTES.get((city or "").strip().lower())


def main() -> int:
    nodes, edges = [], []
    by_norm = {}

    def add_node(n):
        nodes.append(n)
        by_norm[norm(n["name"])] = n["id"]
        return n["id"]

    for nid, name, url, city, county, ntype, blurb in BUILT_SITES:
        add_node({
            "id": nid, "name": name, "type": ntype, "url": url,
            "city": city, "county": county, "drive_min": city_minutes(city),
            "blurb": blurb, "listed_in": [],
        })

    DIRECTORY_IDS = ("livingston-outdoors", "visit-livingston-tn")
    for site_id in DIRECTORY_IDS:
        edges.append({"source": BR, "target": site_id, "kind": "operates"})
    for nid, *_ in [(r[0],) for r in BUILT_SITES]:
        if nid != BR and nid not in DIRECTORY_IDS:
            edges.append({"source": BR, "target": nid, "kind": "built"})
    edges.append({"source": "livingston-outdoors", "target": "visit-livingston-tn",
                  "kind": "sister"})

    dedup = []
    emitted_lists = set()

    def add_listing(directory_id, name, url, city, county, drive_min, blurb, category):
        key = norm(name)
        existing = None
        if key in by_norm:
            candidate = next(n for n in nodes if n["id"] == by_norm[key])
            # Same normalized name only merges when the cities agree or one
            # side has no city — two same-named places in different towns
            # stay distinct nodes.
            c1, c2 = norm(candidate.get("city") or ""), norm(city or "")
            if not c1 or not c2 or c1 == c2:
                existing = candidate
        if existing is not None:
            nid = existing["id"]
            if directory_id not in existing["listed_in"]:
                existing["listed_in"].append(directory_id)
                dedup.append(f"{name} -> existing node {nid} (+{directory_id})")
        else:
            nid = slug(name)
            suffix = 2
            while any(n["id"] == nid for n in nodes):
                nid = f"{slug(name)}-{suffix}"
                suffix += 1
            add_node({
                "id": nid, "name": name, "type": "listed", "url": url,
                "city": city, "county": county, "drive_min": drive_min,
                "blurb": blurb, "category": category,
                "listed_in": [directory_id],
            })
        if (directory_id, nid) not in emitted_lists:
            emitted_lists.add((directory_id, nid))
            edges.append({"source": directory_id, "target": nid, "kind": "lists"})

    outdoors = json.loads(OUTDOORS.read_text(encoding="utf-8"))
    for p in outdoors:
        add_listing("livingston-outdoors", p["name"], p["url"], p.get("town", ""),
                    p.get("county", ""), p.get("drive_minutes"),
                    p.get("blurb") or p.get("why", ""),
                    (p.get("activities") or ["outdoors"])[0])

    visit = json.loads(VISIT.read_text(encoding="utf-8"))["places"]
    for p in visit:
        url = p.get("website") or p.get("source_url")
        # A null city means rural Overton County; 20 minutes is the honest
        # middle of the county for ring placement.
        add_listing("visit-livingston-tn", p["name"], url, p.get("city") or "",
                    "Overton", city_minutes(p.get("city") or "") or 20,
                    p.get("what_it_is") or p.get("blurb", ""),
                    p.get("category", "town"))

    # Bearing assignment: spread nodes inside their county wedge, ordered by id
    # so the layout is deterministic run-to-run.
    from collections import defaultdict
    wedge_members = defaultdict(list)
    for n in nodes:
        wedge_members[n.get("county") or "Overton"].append(n)
    for county, members in wedge_members.items():
        lo, hi = COUNTY_BEARING.get(county, (0, 360))
        members.sort(key=lambda n: n["id"])
        span = (hi - lo) % 360 or 360
        for i, n in enumerate(members):
            n["bearing"] = round((lo + span * (i + 0.5) / len(members)) % 360, 1)

    # Merge geocoded scene coords (scripts/geocode_nodes.py output). Any node
    # inside the 30-mile regional map gets its real spot; farther places
    # (out-of-region places) keep the ring fallback past the map edge.
    REGION = {"S": 35.9471, "W": -85.8614, "N": 36.8207, "E": -84.7840}  # sync with fetch_region.py
    geo_path = ROOT / "data" / "geocode.json"
    geo_ok = 0
    if geo_path.exists():
        gc = json.loads(geo_path.read_text(encoding="utf-8"))
        for n in nodes:
            hit = gc.get(n["id"])
            if (hit and hit.get("lat")
                    and REGION["S"] <= hit["lat"] <= REGION["N"]
                    and REGION["W"] <= hit["lon"] <= REGION["E"]):
                n["geo"] = to_local(hit["lat"], hit["lon"])
                n["geo_method"] = hit["method"]
                geo_ok += 1

    net = {"generated_from": [str(OUTDOORS), str(VISIT)],
           "nodes": nodes, "edges": edges}
    out = ROOT / "data" / "network.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(net, indent=1), encoding="utf-8")

    stats = {
        "nodes_total": len(nodes),
        "by_type": {t: sum(1 for n in nodes if n["type"] == t)
                    for t in ("hub", "directory", "built", "listed")},
        "edges_total": len(edges),
        "edges_by_kind": {k: sum(1 for e in edges if e["kind"] == k)
                          for k in ("operates", "built", "lists", "sister")},
        "source_counts": {"outdoors": len(outdoors), "visit": len(visit)},
        "deduped": dedup,
        "missing_url": [n["id"] for n in nodes if not n["url"]],
        "missing_drive_min": [n["id"] for n in nodes if n["drive_min"] is None],
        "geo_placed": geo_ok,
    }
    rep = ROOT / "reports" / "network-stats.json"
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_text(json.dumps(stats, indent=1), encoding="utf-8")
    print(json.dumps(stats, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

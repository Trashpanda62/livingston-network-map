"""Verification suite for the Livingston Network Map.

File-level checks only (no browser): data integrity against the three source
files, asset self-containment, palette contrast, byte budget, lock state.
Exits non-zero on any FAIL. Writes reports/verify.md.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = {
    "outdoors": Path(r"C:\dev\livingston-outdoors\data\livingston-outdoors.json"),
    "visit": Path(r"C:\dev\visit-livingston\data\places.json"),
    "printers": Path(r"C:\dev\mtn-printers\data\mtn-printers.json"),
}

results = []


def check(name, ok, evidence):
    results.append((name, bool(ok), evidence))


def rel_lum(hexcolor):
    r, g, b = (int(hexcolor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a, b):
    la, lb = rel_lum(a), rel_lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def main() -> int:
    net = json.loads((ROOT / "data" / "network.json").read_text(encoding="utf-8"))
    nodes, edges = net["nodes"], net["edges"]

    # 1-3: node counts derive from the live source files.
    src_counts = {k: (len(json.loads(p.read_text(encoding="utf-8"))["places"])
                      if k == "visit" else
                      len(json.loads(p.read_text(encoding="utf-8"))))
                  for k, p in SOURCES.items()}
    listing_edges = [e for e in edges if e["kind"] == "lists"]
    expected_listings = sum(src_counts.values())
    check("listing edges match source rows",
          len(listing_edges) == expected_listings,
          f"{len(listing_edges)} lists edges vs {src_counts} = {expected_listings}")
    listed_nodes = [n for n in nodes if n["type"] == "listed"]
    built_or_dir = [n for n in nodes if n["type"] in ("hub", "directory", "built")]
    check("node total = listed + our properties",
          len(nodes) == len(listed_nodes) + len(built_or_dir),
          f"{len(nodes)} = {len(listed_nodes)} + {len(built_or_dir)}")

    # 4-7: every node complete.
    for field in ("url", "blurb", "drive_min", "bearing"):
        missing = [n["id"] for n in nodes if n.get(field) in (None, "")]
        check(f"every node has {field}", not missing, f"missing: {missing[:5] or 'none'}")

    # 8: every edge endpoint resolves.
    ids = {n["id"] for n in nodes}
    dangling = [e for e in edges if e["source"] not in ids or e["target"] not in ids]
    check("all edges resolve to nodes", not dangling, f"dangling: {dangling[:3] or 'none'}")

    # City base map: real OSM geometry present and nodes geo-placed on it.
    city = json.loads((ROOT / "data" / "city.json").read_text(encoding="utf-8"))
    check("city map has real street grid", len(city["streets"]) > 100,
          f"{len(city['streets'])} streets, {len(city['buildings'])} buildings, "
          f"{len(city['water'])} waterways")
    geo_nodes = [n for n in nodes if n.get("geo")]
    check("at least 20 nodes geo-placed on the city map", len(geo_nodes) >= 20,
          f"{len(geo_nodes)} geo-placed "
          f"({sum(1 for n in geo_nodes if n['geo_method'] in ('address', 'name-bounded'))} exact, "
          f"{sum(1 for n in geo_nodes if n['geo_method'].endswith('approx'))} approx)")

    # 9: index.html references only local assets, and they exist.
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    refs = re.findall(r'(?:src|href)="([^"]+)"', html)
    external = [r for r in refs if r.startswith(("http://", "https://", "//"))]
    check("zero external asset references in index.html", not external, str(external or "all local"))
    missing_files = [r for r in refs if not (ROOT / r.split("?")[0]).exists()]
    check("every referenced local asset exists", not missing_files, str(missing_files or "all present"))

    # 10: palette contrast — label color vs background per palette.
    app = (ROOT / "src" / "app.js").read_text(encoding="utf-8")
    pal_block = re.findall(r"(\w+):\s*\{([^}]+)\}", app.split("const PALETTES")[1].split("};")[0])
    ratios = {}
    for pname, body in pal_block:
        vals = dict(re.findall(r"(\w+):\s*'(#[0-9a-fA-F]{6})'", body))
        if "bg" in vals and "label" in vals:
            ratios[pname] = round(contrast(vals["label"], vals["bg"]), 2)
    check("label contrast >= 4.5 in every palette",
          ratios and all(v >= 4.5 for v in ratios.values()), str(ratios))

    # 11: byte budget — raised 2 MB -> 8 MB on 2026-08-12 when the satellite
    # imagery ground (data/satellite.jpg, USGS z17 mosaic) replaced the vector
    # drawing. osm-raw.json is a build intermediate but still counted; the
    # budget errs on the honest side.
    total = sum(f.stat().st_size for d in ("vendor", "src", "data")
                for f in (ROOT / d).rglob("*") if f.is_file())
    total += (ROOT / "index.html").stat().st_size
    check("total payload under 8 MB", total < 8 * 1024 * 1024, f"{total/1024:.0f} KB")

    # Satellite ground + visitor data present.
    sat_meta = ROOT / "data" / "satellite.json"
    check("satellite imagery + bounds exist",
          (ROOT / "data" / "satellite.jpg").exists() and sat_meta.exists(),
          "data/satellite.jpg + data/satellite.json")
    vis = json.loads((ROOT / "data" / "visitors.json").read_text(encoding="utf-8"))
    check("visitors.json covers owned domains", len(vis) >= 10,
          f"{len(vis)} domains, {sum(1 for v in vis.values() if v.get('uniques') is not None)} with data")

    # Prospect layer: prospects.json internal consistency.
    ppath = ROOT / "data" / "prospects.json"
    if ppath.exists():
        pros = json.loads(ppath.read_text(encoding="utf-8"))
        new_rows = pros.get("new", [])
        pids = [r["id"] for r in new_rows]
        check("prospect ids unique", len(pids) == len(set(pids)),
              f"{len(pids)} rows, {len(set(pids))} unique")
        bad_geo = [r["id"] for r in new_rows if r.get("lat") is not None
                   and not (35.9 < r["lat"] < 36.9 and -86.0 < r["lon"] < -84.7)]
        check("prospect coords inside region", not bad_geo, f"outside: {bad_geo[:3] or 'none'}")
        flagged_ids = set(pros.get("flagged", {}))
        node_ids = {n["id"] for n in nodes}
        orphan_flags = sorted(flagged_ids - node_ids)
        check("flagged prospect ids resolve to nodes", not orphan_flags,
              f"orphans: {orphan_flags[:3] or 'none'}")
        with_phone = sum(1 for r in new_rows if r.get("phone")) + \
            sum(1 for v in pros.get("flagged", {}).values() if v.get("phone"))
        check("prospects carry phone numbers", with_phone >= (len(new_rows) + len(flagged_ids)) * 0.6,
              f"{with_phone}/{len(new_rows) + len(flagged_ids)} have phones")

    # 12: lock state (informational until locked; FAIL only if half-locked).
    baked = re.search(r"<html[^>]*data-mode", html)
    switcher = "preset-switcher" in html
    if baked and switcher:
        check("lock state consistent", False, "combo baked but switcher still shipped")
    else:
        check("lock state consistent", True,
              "locked, switcher stripped" if baked else "pre-lock: switcher live, nothing baked")

    n_pass = sum(1 for _, ok, _ in results if ok)
    lines = [f"# Verify — {n_pass}/{len(results)} passing", ""]
    for name, ok, ev in results:
        lines.append(f"- {'PASS' if ok else 'FAIL'} — {name} · {ev}")
    lines.append("")
    lines.append(f"Summary: {n_pass}/{len(results)} checks passing")
    rep = ROOT / "reports" / "verify.md"
    rep.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

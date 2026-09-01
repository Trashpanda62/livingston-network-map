"""Seed-roster harvest for the five proposed online-only directory properties.

Unlike find_prospects.py -- which only keeps businesses WITHOUT a real site --
a directory roster needs every business in the category, site or no site. This
sweeps a concept-specific (category x town) grid through the Bright Data SERP
zone, records each business once, and resolves "does it have its own website"
the same authoritative way find_prospects.py does: the snack_pack "site" key
when present, otherwise a per-business knowledge-panel query (the panel carries
"site" exactly when Google shows a Website button).

Writes data/roster-<slug>.json per concept plus reports/roster-summary.md.

Resumable: completed (category|town) pairs are recorded in each roster's
"_done" list and skipped on re-run, and the knowledge-panel cache is shared
across concepts in data/roster-kp.json. Re-run after a timeout to continue.

Run: py -X utf8 scripts/build_rosters.py [--refresh]
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from find_prospects import (  # noqa: E402  reuse the verified SERP + parsing layer
    business_address,
    host_of,
    is_chain,
    normalize_name,
    prospect_reason,
    secret,
    serp_raw,
    slugify,
)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
KP_CACHE = DATA / "roster-kp.json"

# Overton County proper. "Upper Cumberland" adds the ring of county seats a
# rural customer will actually drive to.
OVERTON = ["Livingston", "Monroe", "Rickman", "Hilham", "Allons", "Alpine"]

CONCEPTS = {
    "auto": {
        "title": "Upper Cumberland Auto",
        "scope": "regional",
        "grid": (
            [
                (c, "Livingston")
                for c in (
                    "auto repair",
                    "tire shops",
                    "auto body shop",
                    "towing",
                    "transmission repair",
                    "oil change",
                    "diesel repair",
                )
            ]
            + [(c, t) for t in ("Monroe", "Rickman") for c in ("auto repair", "tire shops")]
            + [
                (c, t)
                for t in ("Byrdstown", "Jamestown", "Celina", "Cookeville")
                for c in ("auto repair", "tire shops")
            ]
        ),
    },
    "food": {
        "title": "Eat Livingston TN",
        "scope": "overton",
        "grid": (
            [
                (c, "Livingston")
                for c in (
                    "restaurants",
                    "bakeries",
                    "coffee shops",
                    "pizza",
                    "barbecue",
                    "mexican restaurant",
                    "breakfast",
                    "diner",
                    "ice cream",
                )
            ]
            + [("restaurants", t) for t in ("Monroe", "Rickman", "Hilham", "Allons", "Alpine")]
        ),
    },
    "homepros": {
        "title": "Upper Cumberland Home Pros",
        "scope": "regional",
        "grid": (
            [
                (c, t)
                for t in ("Livingston", "Cookeville")
                for c in (
                    "electricians",
                    "HVAC",
                    "plumbers",
                    "roofing contractors",
                    "septic tank service",
                    "excavating contractors",
                )
            ]
            + [
                (c, t)
                for t in ("Byrdstown", "Jamestown", "Celina", "Gainesboro")
                for c in ("electricians", "HVAC", "plumbers")
            ]
        ),
    },
    "weddings": {
        "title": "Upper Cumberland Weddings",
        "scope": "regional",
        "grid": (
            [
                (c, t)
                for t in ("Livingston", "Cookeville")
                for c in (
                    "wedding venues",
                    "wedding photographers",
                    "florists",
                    "caterers",
                    "wedding DJ",
                    "event rentals",
                )
            ]
            + [("wedding venues", t) for t in ("Byrdstown", "Jamestown", "Celina", "Gainesboro")]
        ),
    },
    "events": {
        "title": "Livingston Events",
        "scope": "overton",
        "grid": [
            ("event venues", "Livingston"),
            ("live music venues", "Livingston"),
            ("community centers", "Livingston"),
            ("banquet hall", "Livingston"),
            ("theater", "Livingston"),
            ("fairgrounds", "Livingston"),
        ],
    },
}


def load(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def kp_lookup(name: str, town: str, token: str, cache: dict) -> dict:
    key = f"{normalize_name(name)}|{town}"
    if key in cache:
        return cache[key]
    entry = {"found": False, "site": None, "address": None, "phone": None,
             "reviews": None, "rating": None}
    try:
        data = serp_raw(f'"{name}" {town} TN', token)
        k = data.get("knowledge") or {}
        if k.get("name"):
            entry = {
                "found": True,
                "site": k.get("site"),
                "address": k.get("address"),
                "phone": k.get("phone"),
                "reviews": k.get("reviews_cnt"),
                "rating": k.get("rating"),
            }
    except Exception as exc:  # noqa: BLE001
        print(f"    kp error for {name}: {exc}", flush=True)
    cache[key] = entry
    KP_CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    time.sleep(0.4)
    return entry


def harvest(slug: str, spec: dict, token: str, kp_cache: dict, refresh: bool) -> dict:
    path = DATA / f"roster-{slug}.json"
    roster = load(path, {"concept": spec["title"], "scope": spec["scope"],
                         "businesses": [], "_done": [], "_zero": []})
    if refresh:
        roster = {"concept": spec["title"], "scope": spec["scope"],
                  "businesses": [], "_done": [], "_zero": []}
    done = set(roster["_done"])
    by_id = {b["id"]: b for b in roster["businesses"]}
    today = date.today().isoformat()

    for cat, town in spec["grid"]:
        tag = f"{cat}|{town}"
        if tag in done:
            continue
        try:
            data = serp_raw(f"{cat} in {town} TN", token)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {slug} {tag}: {exc}", flush=True)
            time.sleep(1)
            continue

        local = data.get("snack_pack") or []
        if not local:
            roster["_zero"].append(tag)

        added = 0
        for biz in local:
            name = biz.get("name")
            if not name:
                continue
            bid = slugify(name)
            if bid in by_id:
                # Same business surfacing under a second query: keep the first
                # record, note the extra category so the spec knows it overlaps.
                cats = by_id[bid].setdefault("categories", [])
                if cat not in cats:
                    cats.append(cat)
                continue

            site = biz.get("site") or biz.get("website")
            kp = None
            if not site:
                kp = kp_lookup(name, town, token, kp_cache)
                site = kp["site"] if kp["found"] else None

            reason = prospect_reason(site)  # None => owns a real site
            record = {
                "id": bid,
                "name": name,
                "categories": [cat],
                "city": town,
                "address": (kp and kp.get("address")) or business_address(biz),
                "phone": (kp and kp.get("phone")),
                "site": site,
                "site_host": host_of(site) if site else None,
                "has_own_site": reason is None,
                "web_gap": reason,
                "reviews": (kp and kp.get("reviews")) or biz.get("reviews_cnt"),
                "rating": (kp and kp.get("rating")) or biz.get("rating"),
                "is_chain": is_chain(name),
                "in_overton": town in OVERTON,
                "found_by": tag,
                "verified": today,
            }
            by_id[bid] = record
            added += 1

        done.add(tag)
        roster["_done"] = sorted(done)
        roster["businesses"] = list(by_id.values())
        path.write_text(json.dumps(roster, indent=1), encoding="utf-8")
        print(f"  {slug} {tag}: local={len(local)} new={added} total={len(by_id)}", flush=True)
        time.sleep(0.4)

    roster["businesses"] = list(by_id.values())
    path.write_text(json.dumps(roster, indent=1), encoding="utf-8")
    return roster


def summarize(rosters: dict) -> None:
    lines = [
        "# Seed rosters — proposed online-only properties",
        "",
        "Harvested live from Google local packs via the Bright Data SERP zone",
        "(`scripts/build_rosters.py`). `has own site` counts businesses with a real",
        "website of their own; the gap column counts the rest — no site at all, a",
        "Facebook page, a rented builder subdomain, or nothing but an aggregator",
        "listing. Chains are recorded but flagged, not filtered.",
        "",
        "| Concept | Businesses | In Overton Co. | Independents | Has own site | Web gap | Queries run | Empty queries |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for slug, r in rosters.items():
        biz = r["businesses"]
        indie = [b for b in biz if not b["is_chain"]]
        lines.append(
            f"| {r['concept']} | {len(biz)} | {sum(1 for b in biz if b['in_overton'])} | "
            f"{len(indie)} | {sum(1 for b in biz if b['has_own_site'])} | "
            f"{sum(1 for b in biz if not b['has_own_site'])} | {len(r['_done'])} | "
            f"{len(r['_zero'])} |"
        )

    lines += ["", "## Web gap by reason", "", "| Concept | no site | facebook only | rented subdomain | aggregator only |", "|---|---|---|---|---|"]
    for slug, r in rosters.items():
        counts = {k: 0 for k in ("no-website", "facebook-only", "rented-subdomain", "aggregator-listing")}
        for b in r["businesses"]:
            if b["web_gap"] in counts:
                counts[b["web_gap"]] += 1
        lines.append(
            f"| {r['concept']} | {counts['no-website']} | {counts['facebook-only']} | "
            f"{counts['rented-subdomain']} | {counts['aggregator-listing']} |"
        )

    for slug, r in rosters.items():
        top = sorted(
            (b for b in r["businesses"] if not b["is_chain"]),
            key=lambda b: -(b.get("reviews") or 0),
        )[:12]
        lines += ["", f"## {r['concept']} — top independents by review count", "",
                  "| Business | Town | Categories | Reviews | Own site? |", "|---|---|---|---|---|"]
        for b in top:
            cats = ", ".join(b["categories"])
            own = "yes" if b["has_own_site"] else f"**no** ({b['web_gap']})"
            lines.append(f"| {b['name']} | {b['city']} | {cats} | {b.get('reviews') or '—'} | {own} |")

    out = REPORTS / "roster-summary.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {out}")


def main() -> int:
    refresh = "--refresh" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    token = secret("BRIGHTDATA_API_KEY")
    kp_cache = load(KP_CACHE, {})
    rosters = {}
    for slug, spec in CONCEPTS.items():
        if only and slug not in only:
            path = DATA / f"roster-{slug}.json"
            if path.exists():
                rosters[slug] = json.loads(path.read_text(encoding="utf-8"))
            continue
        print(f"== {slug} ({len(spec['grid'])} queries)", flush=True)
        rosters[slug] = harvest(slug, spec, token, kp_cache, refresh)
    summarize(rosters)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

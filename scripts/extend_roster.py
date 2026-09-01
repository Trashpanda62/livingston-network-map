"""Second-pass roster extension for the two properties going to build.

The seed harvest (build_rosters.py) ran a narrow grid to size the opportunity.
This runs the wide grid the specs actually call for, resolves every record whose
site status is still unconfirmed, and re-checks each claimed website by fetching
it, so `has_own_site` rests on a live response rather than on the presence of a
knowledge-panel key.

Three passes:

1. WIDEN   -- more categories across more towns, per --target.
2. RESOLVE -- retry every "unconfirmed" record with a fresh knowledge-panel
              query. A retry that fails twice is recorded as "unresolved" and
              is still never counted as a proven gap.
3. CONFIRM -- HEAD/GET every claimed site URL. Records http_status and
              live_verified. A claimed site that does not answer is demoted out
              of has_own_site, because a dead site is a prospect too.

Writes the extended roster to the target project's data/roster.json.

Run: py -X utf8 scripts/extend_roster.py --target auto|food
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from find_prospects import (  # noqa: E402
    AGGREGATORS,
    ORGANIC_AGGREGATOR_HOSTS,
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
KP_CACHE = DATA / "roster-kp.json"

OVERTON = {"Livingston", "Monroe", "Rickman", "Hilham", "Allons", "Alpine"}

# The town a query was ISSUED for is not where the business turned out to be.
# "restaurants in Livingston TN" returned a place in Livingston, LOUISIANA, plus
# others in Pickett, Clay, Campbell and Macon counties, and every one of them was
# being counted as Overton because the query town was the only thing consulted.
# in_overton is therefore derived from the harvested street address, and is left
# None (unknown) rather than guessed when no address came back.
OVERTON_ADDRESS_TOWNS = (
    "livingston", "monroe", "rickman", "hilham", "allons", "alpine", "windle",
)


def overton_from_address(address: str | None, town: str) -> bool | None:
    if not address:
        return None
    lowered = address.lower()
    if " tn" not in lowered and "tennessee" not in lowered:
        return False
    return any(t in lowered for t in OVERTON_ADDRESS_TOWNS)

# Codes that mean "this server refused an automated client", not "this site is gone".
BLOCKED_CODES = {401, 403, 405, 406, 429}

TARGETS = {
    "auto": {
        "seed": DATA / "roster-auto.json",
        "out": Path(r"C:\dev\overton-auto\data\roster.json"),
        # Six Upper Cumberland counties by their seats and largest towns.
        "grid": [
            (c, t)
            for t in (
                "Livingston", "Monroe", "Rickman", "Hilham",
                "Cookeville", "Algood", "Monterey",
                "Byrdstown", "Jamestown", "Celina", "Gainesboro",
            )
            for c in ("auto repair", "tire shops")
        ]
        + [
            (c, t)
            for t in ("Livingston", "Cookeville", "Jamestown")
            for c in ("auto body shop", "towing", "transmission repair", "diesel repair")
        ],
    },
    "food": {
        "seed": DATA / "roster-food.json",
        "out": Path(r"C:\dev\eat-livingston\data\roster.json"),
        "grid": [
            (c, "Livingston")
            for c in (
                "restaurants", "bakeries", "coffee shops", "pizza", "barbecue",
                "mexican restaurant", "breakfast", "diner", "ice cream",
                "sandwich shop", "chinese restaurant", "steakhouse", "food trucks",
                "catering", "delis", "cafe", "burgers", "wings", "seafood",
            )
        ]
        + [
            (c, t)
            for t in ("Monroe", "Rickman", "Hilham", "Allons", "Alpine")
            for c in ("restaurants", "cafe", "barbecue")
        ],
    },
}


def load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def kp_query(name: str, town: str, token: str) -> dict:
    entry = {"found": False, "site": None, "address": None, "phone": None,
             "reviews": None, "rating": None}
    try:
        data = serp_raw(f'"{name}" {town} TN', token)
        k = data.get("knowledge") or {}
        if k.get("name"):
            entry = {"found": True, "site": k.get("site"), "address": k.get("address"),
                     "phone": k.get("phone"), "reviews": k.get("reviews_cnt"),
                     "rating": k.get("rating")}
    except Exception as exc:  # noqa: BLE001
        print(f"    kp error {name}: {exc}", flush=True)
    time.sleep(0.4)
    return entry


def kp_lookup(name: str, town: str, token: str, cache: dict) -> dict:
    key = f"{normalize_name(name)}|{town}"
    if key in cache and cache[key].get("found"):
        return cache[key]
    entry = kp_query(name, town, token)
    cache[key] = entry
    KP_CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return entry


def check_url(url: str) -> tuple[int | None, str | None]:
    """Fetch a claimed site. Returns (status, final host) or (None, None)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # a bad cert is a site problem, not a 404
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) barnraised-roster-check"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
            return resp.status, host_of(resp.geturl())
    except urllib.error.HTTPError as exc:
        return exc.code, host_of(url)
    except Exception:  # noqa: BLE001
        return None, None


def widen(spec: dict, records: dict, token: str, kp_cache: dict, done: set) -> None:
    today = date.today().isoformat()
    for cat, town in spec["grid"]:
        tag = f"{cat}|{town}"
        if tag in done:
            continue
        try:
            data = serp_raw(f"{cat} in {town} TN", token)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {tag}: {exc}", flush=True)
            time.sleep(1)
            continue
        local = data.get("snack_pack") or []
        added = 0
        for biz in local:
            name = biz.get("name")
            if not name:
                continue
            bid = slugify(name)
            if bid in records:
                cats = records[bid].setdefault("categories", [])
                if cat not in cats:
                    cats.append(cat)
                continue
            site = biz.get("site") or biz.get("website")
            kp = None
            if not site:
                kp = kp_lookup(name, town, token, kp_cache)
                site = kp["site"] if kp["found"] else None
            reason = prospect_reason(site)
            records[bid] = {
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
                "site_status": "has-site" if reason is None and site else (
                    "weak-web" if site else ("no-website" if (kp and kp["found"]) else "unconfirmed")
                ),
                "reviews": (kp and kp.get("reviews")) or biz.get("reviews_cnt"),
                "rating": (kp and kp.get("rating")) or biz.get("rating"),
                "is_chain": is_chain(name),
                "in_overton": overton_from_address(
                    (kp and kp.get("address")) or business_address(biz), town
                ),
                "found_by": tag,
                "verified": today,
            }
            added += 1
        done.add(tag)
        print(f"  {tag}: local={len(local)} new={added} total={len(records)}", flush=True)
        time.sleep(0.4)


def organic_own_site(name: str, town: str, token: str) -> str | None:
    """Read organic results for '<name> <town> TN' and return the first host
    that looks like the business's own site rather than an aggregator. Used only
    when no knowledge panel exists, which is common for very small businesses."""
    try:
        data = serp_raw(f"{name} {town} TN", token)
    except Exception as exc:  # noqa: BLE001
        print(f"    organic error {name}: {exc}", flush=True)
        return None
    time.sleep(0.4)
    wanted = {w for w in normalize_name(name).split() if len(w) > 3}
    for item in (data.get("organic") or [])[:8]:
        url = item.get("link") or item.get("url")
        if not url:
            continue
        host = host_of(url)
        if not host or host in ORGANIC_AGGREGATOR_HOSTS or host in AGGREGATORS:
            continue
        # Require the host to actually echo part of the business name, so a
        # random local blog post about the place is not mistaken for its site.
        flat = host.replace("-", "").replace(".", "")
        if any(w.replace("'", "") in flat for w in wanted):
            return url
    return None


def resolve(records: dict, token: str, kp_cache: dict) -> None:
    # "unresolved" is included deliberately: the first pass renamed failures, so
    # filtering on "unconfirmed" alone made every retry a silent no-op.
    pending = [r for r in records.values()
               if r.get("site_status") in ("unconfirmed", "unresolved")]
    print(f"resolving {len(pending)} unconfirmed/unresolved", flush=True)
    for r in pending:
        entry = kp_query(r["name"], r["city"], token)
        kp_cache[f"{normalize_name(r['name'])}|{r['city']}"] = entry
        if entry["found"]:
            site = entry["site"]
            reason = prospect_reason(site)
            r.update(
                site=site,
                site_host=host_of(site) if site else None,
                has_own_site=reason is None,
                web_gap=reason,
                site_status="has-site" if reason is None else ("weak-web" if site else "no-website"),
                address=r.get("address") or entry.get("address"),
                phone=r.get("phone") or entry.get("phone"),
            )
            print(f"    resolved {r['name']}: {r['site_status']}", flush=True)
        else:
            # No knowledge panel exists for this business. Looping the same query
            # will never help, so fall back to reading organic results: if the
            # business owns a site, it almost always ranks for its own name.
            site = organic_own_site(r["name"], r["city"], token)
            if site:
                reason = prospect_reason(site)
                r.update(
                    site=site,
                    site_host=host_of(site),
                    has_own_site=reason is None,
                    web_gap=reason,
                    site_status="has-site" if reason is None else "weak-web",
                    site_source="organic",
                )
                print(f"    resolved-organic {r['name']}: {host_of(site)}", flush=True)
            else:
                r["site_status"] = "unresolved"
                r["has_own_site"] = False
                r["web_gap"] = None
                print(f"    UNRESOLVED {r['name']}", flush=True)
    KP_CACHE.write_text(json.dumps(kp_cache, indent=1), encoding="utf-8")


def confirm(records: dict) -> None:
    claimed = [r for r in records.values() if r.get("site")]
    print(f"confirming {len(claimed)} claimed sites", flush=True)
    today = date.today().isoformat()
    for r in claimed:
        status, final_host = check_url(r["site"])
        r["http_status"] = status
        r["live_verified"] = bool(status and status < 400)
        r["checked_at"] = today
        if r["has_own_site"] and not r["live_verified"]:
            if status in BLOCKED_CODES:
                # 403/406/429 means the site refused OUR request, not that it is
                # gone. A human with a browser very likely sees a working site.
                # Calling that dead in front of the owner would be both wrong and
                # embarrassing, so it stays a real site and gets flagged instead.
                r["check_note"] = "blocked-to-automated-check"
                print(f"    blocked {r['name']}: {r['site']} -> {status}", flush=True)
            else:
                # No answer at all, or a 404/410/5xx: not a site a customer reaches.
                r["has_own_site"] = False
                r["web_gap"] = "dead-site"
                r["site_status"] = "dead-site"
                print(f"    DEAD {r['name']}: {r['site']} -> {status}", flush=True)
        elif final_host and r["site_host"] and final_host != r["site_host"]:
            r["redirects_to"] = final_host
            print(f"    redirect {r['name']}: {r['site_host']} -> {final_host}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, choices=sorted(TARGETS))
    ap.add_argument("--skip-widen", action="store_true")
    args = ap.parse_args()

    spec = TARGETS[args.target]
    token = secret("BRIGHTDATA_API_KEY")
    kp_cache = load(KP_CACHE, {})

    out = spec["out"]
    if out.exists():
        prev = json.loads(out.read_text(encoding="utf-8"))
        records = {r["id"]: r for r in prev["businesses"]}
        done = set(prev.get("_done", []))
    else:
        seed = json.loads(spec["seed"].read_text(encoding="utf-8"))
        records = {r["id"]: r for r in seed["businesses"] if not r.get("out_of_state")}
        done = set(seed.get("_done", []))
        prev = seed

    if not args.skip_widen:
        widen(spec, records, token, kp_cache, done)
    resolve(records, token, kp_cache)
    confirm(records)

    payload = {
        "concept": prev.get("concept"),
        "scope": prev.get("scope"),
        "generated": date.today().isoformat(),
        "_done": sorted(done),
        "businesses": sorted(records.values(), key=lambda r: -(r.get("reviews") or 0)),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1), encoding="utf-8")

    biz = payload["businesses"]
    print(f"\nwrote {out}")
    print(f"  {len(biz)} businesses, {sum(1 for b in biz if b['in_overton'])} in Overton County")
    print(f"  has own site: {sum(1 for b in biz if b['has_own_site'])}")
    print(f"  proven gap  : {sum(1 for b in biz if b['web_gap'])}")
    print(f"  unresolved  : {sum(1 for b in biz if b['site_status'] == 'unresolved')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

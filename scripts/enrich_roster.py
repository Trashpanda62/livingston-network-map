"""Enrich a built roster with the facts the knowledge panel actually carries.

The panel returns more than the site link the earlier passes used: a full
week of opening hours, a price band, a street address, a phone number and a
rating. Those are the fields the Eat Livingston spec's hours surface needs, and
they are real data rather than anything invented, so they are worth a dedicated
pass.

Every field lands with its own provenance: `hours_source` and `hours_checked`
sit beside `hours`, so the site can state when it last verified rather than
implying the hours are live. Anything the panel does not carry stays absent.
A business with no panel hours renders as "hours not verified", never as a
guess.

Run: py -X utf8 scripts/enrich_roster.py --target auto|food [--only <id>]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from find_prospects import secret, serp_raw  # noqa: E402

OVERTON_ADDRESS_TOWNS = (
    "livingston", "monroe", "rickman", "hilham", "allons", "alpine", "windle",
)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

TARGETS = {
    "auto": Path(r"C:\dev\overton-auto\data\roster.json"),
    "food": Path(r"C:\dev\eat-livingston\data\roster.json"),
}


def panel(name: str, town: str, token: str) -> dict | None:
    try:
        data = serp_raw(f'"{name}" {town} TN', token)
    except Exception as exc:  # noqa: BLE001
        print(f"    error {name}: {exc}", flush=True)
        return None
    finally:
        time.sleep(0.4)
    k = data.get("knowledge") or {}
    return k if k.get("name") else None


def normalize_hours(raw: object) -> dict[str, str] | None:
    """Panel hours arrive as a list of {day, hours} starting on an arbitrary
    weekday. Return a Monday-first dict, or None when nothing usable came back."""
    if not isinstance(raw, list) or not raw:
        return None
    found = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        day = str(item.get("day") or "").strip()
        hours = str(item.get("hours") or "").strip()
        if day in DAYS and hours:
            found[day] = hours
    if len(found) < 5:  # a partial week is not an hours claim worth publishing
        return None
    return {d: found[d] for d in DAYS if d in found}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, choices=sorted(TARGETS))
    ap.add_argument("--only", help="enrich a single record id")
    ap.add_argument("--refresh", action="store_true", help="re-fetch already-enriched records")
    args = ap.parse_args()

    path = TARGETS[args.target]
    data = json.loads(path.read_text(encoding="utf-8"))
    token = secret("BRIGHTDATA_API_KEY")
    today = date.today().isoformat()

    todo = [
        r for r in data["businesses"]
        if (args.only in (None, r["id"])) and (args.refresh or "panel_checked" not in r)
    ]
    print(f"enriching {len(todo)} of {len(data['businesses'])} records", flush=True)

    hit = 0
    for i, r in enumerate(todo, 1):
        k = panel(r["name"], r["city"], token)
        r["panel_checked"] = today
        if not k:
            print(f"  [{i}/{len(todo)}] {r['name']}: no panel", flush=True)
            continue
        hit += 1
        hours = normalize_hours(k.get("open_hours"))
        if hours:
            r["hours"] = hours
            r["hours_source"] = "google-business-profile"
            r["hours_checked"] = today
        for field, key in (("address", "address"), ("phone", "phone"),
                           ("rating", "rating"), ("price_band", "price")):
            value = k.get(key)
            if value and not r.get(field):
                r[field] = value
        if k.get("reviews_cnt"):
            r["reviews"] = k["reviews_cnt"]
        if k.get("subtitle"):
            r["google_category"] = k["subtitle"]
        # The panel address is the first hard evidence of where the business
        # actually is, so re-derive in_overton from it rather than leaving the
        # query town's guess standing.
        if r.get("address"):
            lowered = r["address"].lower()
            r["in_overton"] = (
                (" tn" in lowered or "tennessee" in lowered)
                and any(t in lowered for t in OVERTON_ADDRESS_TOWNS)
            )
        print(
            f"  [{i}/{len(todo)}] {r['name']}: "
            f"hours={'yes' if hours else 'no'} addr={'yes' if r.get('address') else 'no'}",
            flush=True,
        )
        path.write_text(json.dumps(data, indent=1), encoding="utf-8")

    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    biz = data["businesses"]
    print(f"\nwrote {path}")
    print(f"  panels found : {hit}/{len(todo)}")
    print(f"  with hours   : {sum(1 for r in biz if r.get('hours'))}/{len(biz)}")
    print(f"  with address : {sum(1 for r in biz if r.get('address'))}/{len(biz)}")
    print(f"  with phone   : {sum(1 for r in biz if r.get('phone'))}/{len(biz)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

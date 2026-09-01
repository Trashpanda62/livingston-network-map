"""Repair pass over the seed rosters: separate evidence from absence.

Two defects in the first harvest, both found by spot-check rather than by the
harvester:

1. A knowledge-panel query ('"<name>" <town> TN') returns whatever panel Google
   thinks matches, with no guarantee the entity is in Tennessee at all. The
   Byrdstown sweep pulled back "NAPA Auto Parts - La Pine Auto Supply" carrying
   a 541 area code, which is La Pine, OREGON. Any record whose panel address
   and phone both fail a Tennessee test is marked out_of_state and dropped from
   every count.

2. When the panel lookup failed outright (found=False), the harvester recorded
   the business as "no-website". That is absence of evidence recorded as
   evidence of absence. Those become site_status "unconfirmed": still a
   candidate, but never counted as a proven web gap.

Rewrites data/roster-*.json in place and regenerates reports/roster-summary.md.
Idempotent: safe to re-run.

Run: py -X utf8 scripts/verify_rosters.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
KP_CACHE = DATA / "roster-kp.json"

SLUGS = ["auto", "food", "homepros", "weddings", "events"]

# Every area code assigned to Tennessee.
TN_AREA = {"423", "615", "629", "731", "865", "901", "931"}
AREA_RE = re.compile(r"(?:\+1[\s-]*)?\(?(\d{3})\)?[\s.-]")


def normalize_key(name: str) -> str:
    n = (name or "").lower().replace("&", " and ")
    n = re.sub(r"'s\b", "", n)
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def in_tennessee(address: str | None, phone: str | None) -> bool | None:
    """True when something proves TN, False when something disproves it,
    None when there is nothing to judge on."""
    addr = address or ""
    if " TN" in addr or "Tennessee" in addr:
        return True
    m = AREA_RE.search(phone or "")
    if m:
        return m.group(1) in TN_AREA
    if addr.strip():
        return False  # an address that names no TN is evidence against
    return None


def main() -> int:
    kp = json.loads(KP_CACHE.read_text(encoding="utf-8")) if KP_CACHE.exists() else {}
    # The cache is keyed "<normalized name>|<town>"; index by name alone so a
    # record can be matched whichever town query surfaced it.
    by_name: dict[str, dict] = {}
    for key, entry in kp.items():
        by_name.setdefault(key.split("|")[0], entry)

    rosters = {}
    for slug in SLUGS:
        path = DATA / f"roster-{slug}.json"
        roster = json.loads(path.read_text(encoding="utf-8"))
        for b in roster["businesses"]:
            entry = by_name.get(normalize_key(b["name"]))
            b.pop("out_of_state", None)

            # Defect 1: panel resolved to a business outside Tennessee.
            if entry and entry.get("found"):
                verdict = in_tennessee(entry.get("address"), entry.get("phone"))
                b["out_of_state"] = verdict is False
            else:
                b["out_of_state"] = False

            # Defect 2: "no site" asserted off a panel lookup that never resolved.
            panel_decided = entry is not None and not b.get("site")
            if panel_decided and not entry.get("found"):
                b["site_status"] = "unconfirmed"
                b["has_own_site"] = False
                b["web_gap"] = None
            elif b.get("site"):
                b["site_status"] = "has-site" if b["has_own_site"] else "weak-web"
            else:
                b["site_status"] = "no-website"
        roster["businesses"].sort(key=lambda x: -(x.get("reviews") or 0))
        path.write_text(json.dumps(roster, indent=1), encoding="utf-8")
        rosters[slug] = roster

    lines = [
        "# Seed rosters — proposed online-only properties",
        "",
        "Harvested live from Google local packs via the Bright Data SERP zone",
        "(`scripts/build_rosters.py`), then repaired by `scripts/verify_rosters.py`.",
        "",
        "Two corrections are applied to the raw harvest. Records whose knowledge panel",
        "resolves to a business outside Tennessee are dropped from every count (the",
        "Byrdstown auto sweep pulled back a NAPA store in La Pine, Oregon). And a business",
        "whose panel lookup failed outright is counted as **unconfirmed**, not as a web gap,",
        "because a lookup that did not resolve is not evidence that no website exists.",
        "",
        "`proven gap` therefore counts only businesses positively confirmed to lack a real",
        "site of their own: no website at all, a Facebook page, a rented builder subdomain,",
        "or nothing but an aggregator listing. Chains are recorded but flagged, not filtered.",
        "",
        "| Concept | Businesses | In Overton Co. | Independents | Has own site | Proven gap | Unconfirmed | Dropped, out of state |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for slug in SLUGS:
        r = rosters[slug]
        biz = [b for b in r["businesses"] if not b["out_of_state"]]
        dropped = len(r["businesses"]) - len(biz)
        lines.append(
            f"| {r['concept']} | {len(biz)} | {sum(1 for b in biz if b['in_overton'])} | "
            f"{sum(1 for b in biz if not b['is_chain'])} | "
            f"{sum(1 for b in biz if b['has_own_site'])} | "
            f"{sum(1 for b in biz if b['web_gap'])} | "
            f"{sum(1 for b in biz if b['site_status'] == 'unconfirmed')} | {dropped} |"
        )

    lines += [
        "",
        "## Proven gap by reason",
        "",
        "| Concept | no site at all | facebook only | rented subdomain | aggregator only |",
        "|---|---|---|---|---|",
    ]
    for slug in SLUGS:
        r = rosters[slug]
        counts = dict.fromkeys(
            ("no-website", "facebook-only", "rented-subdomain", "aggregator-listing"), 0
        )
        for b in r["businesses"]:
            if not b["out_of_state"] and b["web_gap"] in counts:
                counts[b["web_gap"]] += 1
        lines.append(
            f"| {r['concept']} | {counts['no-website']} | {counts['facebook-only']} | "
            f"{counts['rented-subdomain']} | {counts['aggregator-listing']} |"
        )

    lines += [
        "",
        "## Harvest coverage",
        "",
        "Google's local pack returns at most three businesses per query, so every roster",
        "here is a seed from a fixed query grid, not a census of the category. Empty-pack",
        "queries are listed so the build knows exactly which ground was walked and found",
        "bare, as opposed to never walked.",
        "",
        "| Concept | Queries run | Empty packs | Which came back empty |",
        "|---|---|---|---|",
    ]
    for slug in SLUGS:
        r = rosters[slug]
        empties = ", ".join(f"`{z}`" for z in r["_zero"]) or "—"
        lines.append(f"| {r['concept']} | {len(r['_done'])} | {len(r['_zero'])} | {empties} |")

    for slug in SLUGS:
        r = rosters[slug]
        top = [b for b in r["businesses"] if not b["is_chain"] and not b["out_of_state"]][:12]
        lines += [
            "",
            f"## {r['concept']} — top independents by review count",
            "",
            "| Business | Town | Categories | Reviews | Own site? |",
            "|---|---|---|---|---|",
        ]
        for b in top:
            if b["site_status"] == "unconfirmed":
                own = "unconfirmed"
            elif b["has_own_site"]:
                own = f"yes, {b['site_host']}"
            else:
                own = f"**no** ({b['web_gap']})"
            lines.append(
                f"| {b['name']} | {b['city']} | {', '.join(b['categories'])} | "
                f"{b.get('reviews') or '—'} | {own} |"
            )

    out = REPORTS / "roster-summary.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    for slug in SLUGS:
        r = rosters[slug]
        biz = [b for b in r["businesses"] if not b["out_of_state"]]
        print(
            f"  {r['concept']:30s} n={len(biz):3d} gap={sum(1 for b in biz if b['web_gap']):3d} "
            f"unconfirmed={sum(1 for b in biz if b['site_status']=='unconfirmed'):3d} "
            f"dropped={len(r['businesses'])-len(biz)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

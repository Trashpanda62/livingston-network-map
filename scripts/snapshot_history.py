"""Monthly review/traffic snapshot for trend arrows on the map.

Writes data/history/traffic-YYYYMM.json — {node_id: {reviews, crux}} for
every listed node and prospect — and maintains data/history/index.json
(ordered list of {month, file}). One file per calendar month; re-running in
the same month overwrites that month's snapshot. The map shows trend arrows
once two snapshots exist.

Run: py -X utf8 scripts/snapshot_history.py
"""
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HIST = ROOT / "data" / "history"


def main() -> int:
    traffic = json.loads((ROOT / "data" / "traffic.json").read_text(encoding="utf-8"))
    pros = json.loads((ROOT / "data" / "prospects.json").read_text(encoding="utf-8"))

    snap = {}
    for nid, t in traffic.items():
        snap[nid] = {"reviews": t.get("reviews"), "crux": t.get("crux")}
    for r in pros.get("new", []):
        snap["p-" + r["id"]] = {"reviews": r.get("reviews"), "crux": None}

    month = datetime.date.today().strftime("%Y%m")
    HIST.mkdir(exist_ok=True)
    fname = f"traffic-{month}.json"
    (HIST / fname).write_text(json.dumps(snap, indent=1), encoding="utf-8")

    idx_path = HIST / "index.json"
    idx = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else []
    idx = [e for e in idx if e["month"] != month] + [{"month": month, "file": fname}]
    idx.sort(key=lambda e: e["month"])
    idx_path.write_text(json.dumps(idx, indent=1), encoding="utf-8")
    print(f"snapshot {fname}: {len(snap)} nodes; {len(idx)} snapshot(s) in index")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

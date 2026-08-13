"""Traffic-proxy sweep for listed (not-ours) businesses on the network map.

Two signals, both written to data/traffic.json keyed by node id:
- Google review count + rating from the search knowledge panel, via the
  Bright Data SERP zone (works for essentially every real business).
- CrUX field-data presence via the keyless PageSpeed Insights API (`--psi`
  pass): "Chrome measures real users here" — the honest yes/no that a site
  has meaningful traffic. Slow (~30s/site, Lighthouse), so it runs as a
  separate second pass and tolerates quota errors.

Idempotent: node ids already in traffic.json are skipped unless --refresh.
Secrets: BRIGHTDATA_API_KEY from .llm-system/orchestrator/secrets.local.env.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRETS = Path(r"C:\dev\ObsidianVault\ObsidianVault\.llm-system\orchestrator\secrets.local.env")
OUT = ROOT / "data" / "traffic.json"


def secret(name):
    for line in SECRETS.read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    raise KeyError(name)


def serp_knowledge(query, token):
    body = json.dumps({
        "zone": "serp_api1",
        "url": "https://www.google.com/search?q=" + urllib.parse.quote(query) + "&brd_json=1",
        "format": "raw",
    }).encode()
    req = urllib.request.Request(
        "https://api.brightdata.com/request", data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.load(r)
    return data.get("knowledge") or {}


def psi_has_crux(url):
    """None = quota/error (unknown), True/False = CrUX origin data present."""
    q = ("https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url="
         + urllib.parse.quote(url, safe="") + "&category=performance")
    try:
        with urllib.request.urlopen(q, timeout=120) as r:
            data = json.load(r)
        return bool(data.get("originLoadingExperience", {}).get("metrics"))
    except Exception as e:  # noqa: BLE001 — quota 429s expected keyless
        print(f"    psi error: {e}", flush=True)
        return None


def main() -> int:
    do_psi = "--psi" in sys.argv
    refresh = "--refresh" in sys.argv
    net = json.loads((ROOT / "data" / "network.json").read_text(encoding="utf-8"))
    cache = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    listed = [n for n in net["nodes"] if n["type"] == "listed"]

    if not do_psi:
        token = secret("BRIGHTDATA_API_KEY")
        done = fail = 0
        for n in listed:
            if not refresh and cache.get(n["id"], {}).get("reviews"):
                continue
            city = n.get("city") or ""
            # Quoted first (precision), unquoted fallback (recall — names with
            # punctuation or long official titles miss the quoted match).
            queries = [f'"{n["name"]}" {city} TN', f'{n["name"]} {city} Tennessee']
            k = {}
            for q in queries:
                try:
                    k = serp_knowledge(q.replace("  ", " "), token)
                except Exception as e:  # noqa: BLE001
                    print(f"  ! {n['id']}: {e}", flush=True)
                    k = {}
                if k.get("reviews_cnt"):
                    break
            entry = cache.setdefault(n["id"], {})
            if k.get("reviews_cnt"):
                entry.update({"reviews": k["reviews_cnt"], "rating": k.get("rating"),
                              "source": "Google reviews"})
                done += 1
            else:
                entry.update({"reviews": None, "rating": None, "source": None})
                fail += 1
            print(f"  {n['id']}: {entry.get('reviews')}", flush=True)
            OUT.write_text(json.dumps(cache, indent=1), encoding="utf-8")
            time.sleep(0.5)
        print(f"reviews: found={done} none={fail} of {len(listed)}", flush=True)
    else:
        done = 0
        for n in listed:
            if not n.get("url"):
                continue
            entry = cache.setdefault(n["id"], {})
            if not refresh and "crux" in entry and entry["crux"] is not None:
                continue
            entry["crux"] = psi_has_crux(n["url"])
            done += 1
            print(f"  {n['id']}: crux={entry['crux']}", flush=True)
            OUT.write_text(json.dumps(cache, indent=1), encoding="utf-8")
            time.sleep(2)
        print(f"psi checked {done}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

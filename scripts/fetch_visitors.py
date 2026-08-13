"""Pull 7-day visitor counts for owned zones from Cloudflare GraphQL and
merge data/visitors-overrides.json (manual numbers, e.g. the Obscura
first-party beacon). Writes data/visitors.json keyed by domain:
{domain: {"uniques": n|null, "pageviews": n|null, "source": str}}.

Tokens come from the orchestrator secrets file; zones are discovered per
token, so new domains appear automatically.
"""
import json
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRETS = Path(r"C:\dev\ObsidianVault\ObsidianVault\.llm-system\orchestrator\secrets.local.env")
TOKEN_KEYS = ["CLOUDFLARE_ANALYTICS_TOKEN", "CLOUDFLARE_API_TOKEN",
              "CLOUDFLARE_OBSCURA_API_TOKEN"]


def read_tokens():
    toks = {}
    for line in SECRETS.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in TOKEN_KEYS:
                toks[k.strip()] = v.strip()
    return toks


def api(url, token, payload=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode() if payload else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def zones_for(token):
    out = []
    page = 1
    while True:
        d = api(f"https://api.cloudflare.com/client/v4/zones?per_page=50&page={page}", token)
        out.extend(d.get("result") or [])
        info = d.get("result_info") or {}
        if page >= (info.get("total_pages") or 1):
            return out
        page += 1


GQL = """
query($zone: String!, $since: Date!, $until: Date!) {
  viewer { zones(filter: {zoneTag: $zone}) {
    httpRequests1dGroups(limit: 10, filter: {date_geq: $since, date_leq: $until}) {
      sum { pageViews }
      uniq { uniques }
    }
  } }
}
"""


def weekly(token, zone_id):
    until = date.today() - timedelta(days=1)
    since = until - timedelta(days=6)
    d = api("https://api.cloudflare.com/client/v4/graphql", token,
            {"query": GQL, "variables": {"zone": zone_id,
                                         "since": since.isoformat(),
                                         "until": until.isoformat()}})
    if d.get("errors"):
        raise RuntimeError(str(d["errors"])[:200])
    groups = d["data"]["viewer"]["zones"][0]["httpRequests1dGroups"]
    return (sum(g["sum"]["pageViews"] for g in groups),
            sum(g["uniq"]["uniques"] for g in groups))


def main() -> int:
    visitors = {}
    for key, token in read_tokens().items():
        try:
            zones = zones_for(token)
        except Exception as e:  # noqa: BLE001
            print(f"{key}: zone list failed: {e}")
            continue
        for z in zones:
            name = z["name"]
            if visitors.get(name, {}).get("uniques") is not None:
                continue  # an earlier token already delivered data
            try:
                pv, uq = weekly(token, z["id"])
                visitors[name] = {"uniques": uq, "pageviews": pv,
                                  "source": "cloudflare 7d"}
                print(f"  {name}: uniques={uq} pageviews={pv}")
            except Exception as e:  # noqa: BLE001
                visitors[name] = {"uniques": None, "pageviews": None,
                                  "source": f"cloudflare error: {e}"[:120]}
                print(f"  {name}: FAILED {e}")

    ov_path = ROOT / "data" / "visitors-overrides.json"
    if ov_path.exists():
        for dom, entry in json.loads(ov_path.read_text(encoding="utf-8")).items():
            cur = visitors.get(dom)
            if not cur or cur.get("uniques") is None:
                visitors[dom] = entry
                print(f"  {dom}: override -> {entry.get('uniques')}")

    out = ROOT / "data" / "visitors.json"
    out.write_text(json.dumps(visitors, indent=1), encoding="utf-8")
    print(f"{len(visitors)} domains -> {out}")
    return 0 if visitors else 1


if __name__ == "__main__":
    sys.exit(main())

"""Check Porkbun availability + price for the expansion-concept domain candidates.

Writes reports/domains.md. Porkbun rate-limits checkDomain hard (roughly one call
per 10 s), so this sleeps between calls and retries once on a rate-limit reply.
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

PB_API = "https://api.porkbun.com/api/json/v3"
ENV_PATH = r"C:\dev\webstudio\.env"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports", "domains.md")

CANDIDATES = [
    ("Upper Cumberland Auto", "uppercumberlandauto.com"),
    ("Upper Cumberland Auto", "overtoncountyauto.com"),
    ("Upper Cumberland Auto", "livingstontnauto.com"),
    ("Eat Livingston TN", "eatlivingstontn.com"),
    ("Eat Livingston TN", "eatlivingston.com"),
    ("Eat Livingston TN", "livingstontneats.com"),
    ("Upper Cumberland Home Pros", "uppercumberlandhomepros.com"),
    ("Upper Cumberland Home Pros", "overtoncountyhomepros.com"),
    ("Upper Cumberland Home Pros", "uppercumberlandtrades.com"),
    ("Upper Cumberland Weddings", "uppercumberlandweddings.com"),
    ("Upper Cumberland Weddings", "cumberlandbarnweddings.com"),
    ("Upper Cumberland Weddings", "overtoncountyweddings.com"),
    ("Livingston Events", "livingstontnevents.com"),
    ("Livingston Events", "overtoncountyevents.com"),
    ("Livingston Events", "thisweekinlivingston.com"),
]


def load_env(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{PB_API}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=45, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace")
        try:
            return json.loads(body_text)
        except Exception:
            return {"status": "ERROR", "message": f"HTTP {exc.code}: {body_text[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "ERROR", "message": str(exc)}


def check(domain: str, keys: dict[str, str]) -> dict:
    body = {"apikey": keys["PORKBUN_API_KEY"], "secretapikey": keys["PORKBUN_SECRET_KEY"]}
    for attempt in (1, 2):
        res = post(f"/domain/checkDomain/{domain}", body)
        msg = (res.get("message") or "").lower()
        if res.get("status") == "SUCCESS" or "limit" not in msg:
            return res
        time.sleep(20)
    return res


def main() -> int:
    keys = load_env(ENV_PATH)
    if not keys.get("PORKBUN_API_KEY") or not keys.get("PORKBUN_SECRET_KEY"):
        print(f"missing Porkbun keys in {ENV_PATH}", file=sys.stderr)
        return 1

    rows = []
    for i, (concept, domain) in enumerate(CANDIDATES):
        res = check(domain, keys)
        resp = res.get("response") or {}
        avail = resp.get("avail")
        price = resp.get("price")
        renewal = resp.get("regularPrice") or resp.get("renewal")
        if res.get("status") != "SUCCESS":
            state = "error"
            note = res.get("message", "")[:120]
        elif avail == "yes":
            state = "available"
            note = ""
        else:
            state = "taken"
            note = ""
        rows.append(
            {
                "concept": concept,
                "domain": domain,
                "state": state,
                "price": price,
                "renewal": renewal,
                "note": note,
            }
        )
        print(f"{domain:34s} {state:10s} {price or '':>8} {note}", flush=True)
        if i < len(CANDIDATES) - 1:
            time.sleep(11)

    lines = [
        "# Domain candidates — Livingston online-layer expansion",
        "",
        "Live Porkbun `checkDomain` results. `first year` is the promotional first-year price,",
        "`renewal` the standing annual rate. Nothing here has been purchased.",
        "",
        "| Concept | Domain | Status | First year | Renewal | Note |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        price = f"${r['price']}" if r["price"] else "—"
        renew = f"${r['renewal']}" if r["renewal"] else "—"
        lines.append(
            f"| {r['concept']} | `{r['domain']}` | {r['state']} | {price} | {renew} | {r['note']} |"
        )

    avail_rows = [r for r in rows if r["state"] == "available"]
    lines += [
        "",
        f"Checked {len(rows)} candidates: {len(avail_rows)} available, "
        f"{sum(1 for r in rows if r['state'] == 'taken')} taken, "
        f"{sum(1 for r in rows if r['state'] == 'error')} errored.",
    ]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

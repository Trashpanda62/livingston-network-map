"""Publish a single self-contained HTML document to Obscura Sites.

Both new directory properties render to ONE file with no external assets (inline
SVG hero, inline CSS, inline JS), so this is much simpler than the
visit-livingston deploy: no asset upload pass and no path rewriting. Auth, create
or reuse the site, PATCH customHtml, publish, then fetch the public URL and
confirm the document actually served.

Auth order matches the visit-livingston script's hard-won findings: a
container-minted session token if one is on disk, otherwise the login route. A
browser User-Agent is mandatory or Cloudflare's WAF answers 403 in front of the
app, and no HTTPCookieProcessor is installed because it rewrites the Cookie
header and drops the session.

Nothing here touches DNS.

Run: py -X utf8 scripts/deploy_obscura_page.py --html <file> --slug <slug> --name "<name>" --state <file>
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://sites.obscurastudio.design"
SECRETS = Path(r"C:\dev\ObsidianVault\ObsidianVault\.llm-system\orchestrator\secrets.local.env")
TOKEN_FILE = Path(r"C:\dev\visit-livingston\.secrets\session.token")

opener = urllib.request.build_opener()
opener.addheaders = [
    ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
]

TOKEN = TOKEN_FILE.read_text(encoding="utf-8").strip() if TOKEN_FILE.exists() else ""


def secret(*names: str) -> str | None:
    for n in names:
        if os.environ.get(n):
            return os.environ[n]
    if SECRETS.exists():
        values = {}
        for line in SECRETS.read_text(encoding="utf-8", errors="replace").splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip().strip('"').strip("'")
        for n in names:
            if values.get(n):
                return values[n]
    return None


def call(method: str, path: str, body=None):
    url = path if path.startswith("http") else BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if TOKEN:
        req.add_header("Cookie", f"obscura_session={TOKEN}")
    try:
        with opener.open(req, timeout=180) as r:
            text = r.read().decode("utf-8", "replace")
            return r.status, (json.loads(text) if text.strip().startswith(("{", "[")) else text)
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")
        return e.code, (json.loads(text) if text.strip().startswith(("{", "[")) else text)


def authenticate() -> bool:
    global TOKEN
    if TOKEN:
        status, body = call("GET", "/api/sites")
        if status < 400:
            n = len(body) if isinstance(body, list) else "?"
            print(f"  authenticated with the minted session ({n} sites visible)")
            return True
        print(f"  minted session rejected: {status}")
        TOKEN = ""
    email = secret("OBSCURA_STUDIO_EMAIL", "OBSCURA_DEMO_EMAIL")
    for password in dict.fromkeys(filter(None, [
        secret("OBSCURA_STUDIO_PASSWORD"), secret("WEBSTUDIO_PASSWORD"),
        secret("OBSCURA_DEMO_PASSWORD"),
    ])):
        status, body = call("POST", "/api/auth/login", {"email": email, "password": password})
        if status < 400:
            print(f"  login ok as {email}")
            return True
        print(f"  login as {email} -> {status} {str(body)[:80]}")
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--state", required=True)
    args = ap.parse_args()

    page = Path(args.html).read_text(encoding="utf-8")
    if 'src="' in page and "data:" not in page.split('src="', 1)[1][:20]:
        # Only a warning: an inline SVG has no src at all, which is the expected shape.
        print("  note: the document references a src attribute; confirm it is a data URI")
    print(f"document: {len(page)/1024:.0f}KB")

    print("auth")
    if not authenticate():
        raise SystemExit("could not authenticate against Obscura Sites")

    state_path = Path(args.state)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    site_id, slug = state.get("site_id"), state.get("slug", args.slug)

    if not site_id:
        print("create site")
        status, body = call("POST", "/api/sites/custom", {
            "name": args.name, "slug": args.slug,
            "html": "<!doctype html><html><body>placeholder</body></html>",
        })
        print("  ->", status, str(body)[:200])
        if status >= 400:
            raise SystemExit("site creation failed")
        site_id, slug = body["id"], body["slug"]
        state.update({"site_id": site_id, "slug": slug})
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    print(f"site {site_id} slug {slug}")

    status, body = call("PATCH", f"/api/sites/{site_id}", {"customHtml": page})
    print("  patch ->", status, str(body)[:140])
    if status >= 400:
        raise SystemExit("failed to update the site html")

    status, body = call("POST", f"/api/sites/{site_id}/publish", {})
    print("  publish ->", status, str(body)[:140])
    if status >= 400:
        raise SystemExit("publish failed")

    url = f"{BASE}/s/{slug}"
    status, served = call("GET", f"/s/{slug}")
    served_text = served if isinstance(served, str) else json.dumps(served)
    print(f"  live check {url} -> {status}, {len(served_text)/1024:.0f}KB")
    if status >= 400:
        raise SystemExit("the published URL did not serve")
    if "placeholder" in served_text[:400]:
        raise SystemExit("the placeholder document is still being served")

    state["url"] = url
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"\nLIVE: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

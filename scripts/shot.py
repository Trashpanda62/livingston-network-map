"""Headless-Chrome screenshot helper over the DevTools protocol.

The in-app Browser pane does not composite frames unless the pane is actually
displayed, so `computer{action:"screenshot"}` times out in a headless session.
This drives a throwaway Chrome directly instead: launch with a remote debugging
port, open the URL, set the device metrics, capture, exit.

Also returns the page's own answer to the two questions a screenshot cannot:
`documentElement.clientWidth` versus `scrollWidth` (horizontal overflow) and the
count of rendered listing nodes.

Run: py -X utf8 scripts/shot.py <url> <out.png> [width] [height]
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from base64 import b64decode
from pathlib import Path

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_browser() -> str:
    for path in CHROME_CANDIDATES:
        if os.path.exists(path):
            return path
    for name in ("chrome", "msedge"):
        found = shutil.which(name)
        if found:
            return found
    raise SystemExit("no Chrome or Edge binary found")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def ws_url(port: int, timeout: float = 25.0) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
                return json.load(r)["webSocketDebuggerUrl"]
        except Exception:  # noqa: BLE001
            time.sleep(0.3)
    raise SystemExit("browser never exposed a debugging endpoint")


def main() -> int:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    url, out = sys.argv[1], Path(sys.argv[2])
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1400
    height = int(sys.argv[4]) if len(sys.argv) > 4 else 900

    try:
        from websockets.sync.client import connect  # noqa: PLC0415
    except ImportError:
        raise SystemExit("pip install websockets") from None

    port = free_port()
    profile = tempfile.mkdtemp(prefix="shot-profile-")
    proc = subprocess.Popen(
        [
            find_browser(),
            "--headless=new",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile}",
            f"--window-size={width},{height}",
            "--hide-scrollbars",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        endpoint = ws_url(port)
        with connect(endpoint, max_size=64 * 1024 * 1024) as ws:
            counter = iter(range(1, 10_000))

            def call(method: str, params: dict | None = None) -> dict:
                mid = next(counter)
                ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
                while True:
                    msg = json.loads(ws.recv())
                    if msg.get("id") == mid:
                        if "error" in msg:
                            raise SystemExit(f"{method}: {msg['error']}")
                        return msg.get("result", {})

            targets = call("Target.getTargets")["targetInfos"]
            page = next(t for t in targets if t["type"] == "page")
            session = call("Target.attachToTarget",
                           {"targetId": page["targetId"], "flatten": True})["sessionId"]

            def send(method: str, params: dict | None = None) -> dict:
                mid = next(counter)
                ws.send(json.dumps({"id": mid, "method": method,
                                    "params": params or {}, "sessionId": session}))
                while True:
                    msg = json.loads(ws.recv())
                    if msg.get("id") == mid:
                        if "error" in msg:
                            raise SystemExit(f"{method}: {msg['error']}")
                        return msg.get("result", {})

            send("Page.enable")
            send("Emulation.setDeviceMetricsOverride", {
                "width": width, "height": height,
                "deviceScaleFactor": 1,
                "mobile": width < 768,
            })
            send("Page.navigate", {"url": url})
            time.sleep(3.0)

            probe = send("Runtime.evaluate", {
                "returnByValue": True,
                "expression": """(() => {
                    const d = document.documentElement;
                    return {
                        clientWidth: d.clientWidth,
                        scrollWidth: d.scrollWidth,
                        overflow: d.scrollWidth - d.clientWidth,
                        title: document.title,
                        headings: document.querySelectorAll('h1,h2,h3').length,
                        links: document.querySelectorAll('a[href]').length,
                        tel: document.querySelectorAll('a[href^="tel:"]').length,
                        jsonld: document.querySelectorAll('script[type="application/ld+json"]').length,
                        height: d.scrollHeight,
                    };
                })()""",
            })["result"]["value"]

            shot = send("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b64decode(shot["data"]))
            print(json.dumps({"out": str(out), "viewport": [width, height], **probe}, indent=1))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

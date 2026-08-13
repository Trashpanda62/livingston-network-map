"""Static server for the network map with sane cache headers.

HTML/JS/CSS/JSON: no-cache (revalidate every load — kills the stale-module
class of bug that blanked the page on 2026-08-13). Images: cache 1 day.
Usage: python serve.py [port]  (default 8162)
"""
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        if self.path.split("?")[0].endswith((".jpg", ".png", ".ttf")):
            self.send_header("Cache-Control", "public, max-age=86400")
        else:
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8162
    server = ThreadingHTTPServer(
        ("0.0.0.0", port), partial(Handler, directory=str(ROOT)))
    print(f"serving {ROOT} on 0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

"""Fetch aerial imagery for the Livingston bbox and stitch it into
data/satellite.jpg + data/satellite.json (geo bounds).

Tiles: Esri World Imagery, zoom 17, with required attribution (carried in the
metadata and shown in the app HUD). The USGS National Map tile service was
tried first but 404s at z17 for this area.
"""
import io
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
# Same bbox as fetch_city.py: (S, W, N, E)
S, W, N, E = 36.366, -85.346, 36.401, -85.299
Z = 17
URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
UA = {"User-Agent": "livingston-network-map/1.0 (steve@maxfieldmanagementgroup.com)"}
MAX_PX = 4096


def deg2num(lat, lon, z):
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n
    return x, y


def num2deg(x, y, z):
    n = 2 ** z
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon


def main() -> int:
    x0f, y0f = deg2num(N, W, Z)   # top-left
    x1f, y1f = deg2num(S, E, Z)   # bottom-right
    x0, y0 = int(x0f), int(y0f)
    x1, y1 = int(x1f), int(y1f)
    cols, rows = x1 - x0 + 1, y1 - y0 + 1
    print(f"z{Z}: {cols}x{rows} = {cols*rows} tiles")
    mosaic = Image.new("RGB", (cols * 256, rows * 256))
    fetched = failed = 0
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            url = URL.format(z=Z, y=ty, x=tx)
            for attempt in range(3):
                try:
                    req = urllib.request.Request(url, headers=UA)
                    with urllib.request.urlopen(req, timeout=30) as r:
                        tile = Image.open(io.BytesIO(r.read())).convert("RGB")
                    mosaic.paste(tile, ((tx - x0) * 256, (ty - y0) * 256))
                    fetched += 1
                    break
                except Exception as e:  # noqa: BLE001
                    if attempt == 2:
                        failed += 1
                        print(f"  tile {tx},{ty} failed: {e}")
                    else:
                        time.sleep(1.5)
    # Geographic bounds of the stitched mosaic (tile-aligned, wider than bbox).
    n_lat, w_lon = num2deg(x0, y0, Z)
    s_lat, e_lon = num2deg(x1 + 1, y1 + 1, Z)[0], num2deg(x1 + 1, y1 + 1, Z)[1]
    if mosaic.width > MAX_PX:
        scale = MAX_PX / mosaic.width
        mosaic = mosaic.resize((MAX_PX, round(mosaic.height * scale)), Image.LANCZOS)
    out_img = ROOT / "data" / "satellite.jpg"
    mosaic.save(out_img, quality=80, optimize=True)
    meta = {
        "north": n_lat, "south": s_lat, "west": w_lon, "east": e_lon,
        "zoom": Z, "px": [mosaic.width, mosaic.height],
        "credit": "Imagery: Esri, Maxar, Earthstar Geographics",
    }
    (ROOT / "data" / "satellite.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"fetched={fetched} failed={failed} -> {out_img} "
          f"{mosaic.width}x{mosaic.height} {out_img.stat().st_size//1024} KB", flush=True)
    print(json.dumps(meta), flush=True)
    if failed or not fetched:
        # A holed or empty mosaic must not masquerade as a good one.
        out_img.unlink(missing_ok=True)
        (ROOT / "data" / "satellite.json").unlink(missing_ok=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

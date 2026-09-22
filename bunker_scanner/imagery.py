"""Aerial orthophotos, for cross-checking candidates against what is on the surface.

Optical imagery cannot *confirm* anything under canopy — that is the whole reason
this project uses LiDAR. It is useful in the other direction: as a negative
check. A candidate that coincides with a visible track, ditch, building, quarry
or field boundary has a mundane explanation. And seeing whether the spot is under
closed canopy or in open ground tells a reviewer whether "invisible from the air"
is even the expected state.

Source: MML's orthophoto archive on the same Funet/CSC mirror as the elevation
model, in the same TM35FIN sheet grid, so `sheets.py` applies unchanged. Tiles
are 0.5 m RGB JPEG2000, 6 x 6 km, EPSG:3067, and are read in place over
/vsicurl — they are ~100 MB each and nothing needs the whole tile.

Coverage is per campaign and per year, and no single year covers the country, so
a lookup walks the campaigns newest-first until it finds the sheet.
"""

from __future__ import annotations

import json
import pathlib
import re
import urllib.error
import urllib.request

import numpy as np
import rasterio
from rasterio.windows import from_bounds

from .sheets import tile_name

BASE = "https://www.nic.funet.fi/index/geodata/mml/orto/normal_color_3067"
# Newest, highest-resolution campaigns first.
CAMPAIGNS = ("smk_v_15000_50", "mavi_v_25000_50", "mara_v_25000_50", "mara_v_20000_50")
CACHE = pathlib.Path(__file__).resolve().parent.parent / "data" / "imagery-index.json"

_index: dict | None = None


def _listing(url: str) -> list[str]:
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            body = response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError):
        return []
    entries = re.findall(r'href="([^"?/][^"]*)"', body)
    return [e for e in entries if not e.startswith("http")]


def _load_index() -> dict:
    global _index
    if _index is None:
        _index = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    return _index


def _save_index() -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(_load_index(), indent=0, sort_keys=True))


def find_tile(name: str) -> tuple[str, str] | None:
    """(url, year) of the newest orthophoto covering this level-5 sheet, or None.

    Directory listings are cached, because finding one tile otherwise costs a
    handful of requests and a regional run asks for hundreds.
    """
    index = _load_index()
    if name in index:
        entry = index[name]
        return (entry["url"], entry["year"]) if entry else None

    sheet2 = name[:3]
    found = None
    for campaign in CAMPAIGNS:
        years = sorted((y for y in _listing(f"{BASE}/{campaign}/") if y.rstrip("/").isdigit()),
                       key=lambda y: int(y.rstrip("/")), reverse=True)
        for year in years:
            year = year.rstrip("/")
            for resolution in _listing(f"{BASE}/{campaign}/{year}/{sheet2}/"):
                resolution = resolution.rstrip("/")
                for subdir in _listing(f"{BASE}/{campaign}/{year}/{sheet2}/{resolution}/"):
                    subdir = subdir.rstrip("/")
                    if subdir.endswith(".jp2"):
                        continue
                    files = _listing(
                        f"{BASE}/{campaign}/{year}/{sheet2}/{resolution}/{subdir}/")
                    if f"{name}.jp2" in files:
                        found = {
                            "url": f"{BASE}/{campaign}/{year}/{sheet2}/{resolution}/"
                                   f"{subdir}/{name}.jp2",
                            "year": year, "campaign": campaign,
                        }
                        break
                if found:
                    break
            if found:
                break
        if found:
            break

    index[name] = found
    _save_index()
    return (found["url"], found["year"]) if found else None


def read_window(west: float, south: float, east: float, north: float
                ) -> tuple[np.ndarray | None, str | None]:
    """RGB array (rows, cols, 3) for a TM35FIN box, plus the imagery year.

    Returns (None, None) when no campaign covers the box. Boxes that straddle a
    sheet edge are mosaicked — a candidate crop landing on a tile boundary would
    otherwise come back half black, which reads as "nothing there" rather than
    "no data here".
    """
    from rasterio.merge import merge

    from .sheets import TILE_SIZE

    corners = {tile_name(x, y)
               for x in (west, east - 1e-6) for y in (south, north - 1e-6)}
    located = [(name, find_tile(name)) for name in sorted(corners)]
    available = [(name, hit) for name, hit in located if hit is not None]
    if not available:
        return None, None

    years = sorted({hit[1] for _, hit in available}, reverse=True)
    try:
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                          CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".jp2"):
            handles = [rasterio.open(f"/vsicurl/{hit[0]}") for _, hit in available]
            try:
                if len(handles) == 1:
                    window = from_bounds(west, south, east, north, handles[0].transform)
                    data = handles[0].read(window=window, boundless=True, fill_value=0)
                else:
                    data, _ = merge(handles, bounds=(west, south, east, north))
            finally:
                for handle in handles:
                    handle.close()
        return np.transpose(data[:3], (1, 2, 0)), years[0]
    except Exception:
        return None, None

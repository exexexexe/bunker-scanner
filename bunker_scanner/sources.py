"""Terrain data sources, one per country.

A source knows its CRS and pixel size, and can list the tiles covering a
bounding box given in its own CRS. Tiles are either downloaded and cached
(small tiles, Finland) or read in place over HTTP as COGs (large tiles, Sweden).
"""

from __future__ import annotations

import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from .config import load_env
from .sheets import TILE_SIZE, tile_bounds, tile_name, tile_path


def fetch_json(url: str, attempts: int = 5, timeout: int = 60):
    """GET JSON, backing off on rate limits and transient server errors.

    Lantmäteriet's STAC returns 429 readily when a run resolves tiles for many
    boxes in a row, so a bulk pass has to wait rather than give up.
    """
    delay = 2.0
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            retryable = error.code == 429 or 500 <= error.code < 600
            if not retryable or attempt == attempts:
                raise
            wait = float(error.headers.get("Retry-After") or delay)
            time.sleep(wait)
            delay = min(delay * 2, 60.0)
        except (urllib.error.URLError, TimeoutError):
            if attempt == attempts:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 60.0)
    raise RuntimeError(f"gave up fetching {url}")


@dataclass(frozen=True)
class Tile:
    name: str
    url: str
    bounds: tuple[float, float, float, float]  # west, south, east, north, source CRS


@dataclass
class Source:
    key: str
    label: str
    crs: str
    resolution: float
    attribution: str
    stream: bool  # True = read the remote COG in place, False = download and cache
    auth_env: tuple[str, str] | None = None  # (user var, password var)

    def credentials(self) -> tuple[str, str] | None:
        if not self.auth_env:
            return None
        load_env()
        user = os.environ.get(self.auth_env[0])
        password = os.environ.get(self.auth_env[1])
        return (user, password) if user and password else None

    def tiles(self, west, south, east, north) -> list[Tile]:  # pragma: no cover
        raise NotImplementedError


# --------------------------------------------------------------------------- Finland

FUNET = "https://www.nic.funet.fi/index/geodata/mml/dem2m/2008_latest"


@dataclass
class FinlandKM2(Source):
    key: str = "fi"
    label: str = "MML Korkeusmalli 2 m"
    crs: str = "EPSG:3067"
    resolution: float = 2.0
    attribution: str = "Korkeusmalli 2 m © Maanmittauslaitos, CC BY 4.0 (Funet/CSC mirror)"
    stream: bool = False

    def tiles(self, west, south, east, north) -> list[Tile]:
        # Step from the corner of the tile containing the south-west of the box.
        # Stepping from the box's own edge instead skips interior tiles whenever
        # the box is not tile-aligned, which silently drops data from the mosaic.
        origin_west, origin_south, _, _ = tile_bounds(tile_name(west, south))
        names: list[str] = []
        north_edge = origin_south
        while north_edge < north:
            east_edge = origin_west
            while east_edge < east:
                names.append(tile_name(east_edge + 1.0, north_edge + 1.0))
                east_edge += TILE_SIZE
            north_edge += TILE_SIZE
        return [Tile(n, f"{FUNET}/{tile_path(n)}", tile_bounds(n)) for n in sorted(set(names))]


# ---------------------------------------------------------------------------- Sweden

STAC = "https://api.lantmateriet.se/stac-hojd/v1"


@dataclass
class SwedenMHM1(Source):
    key: str = "se"
    label: str = "Lantmäteriet Markhöjdmodell 1 m"
    # Tiles are EPSG:5845 (SWEREF99 TM + RH2000); horizontally that is EPSG:3006.
    crs: str = "EPSG:3006"
    resolution: float = 1.0
    attribution: str = "Markhöjdmodell © Lantmäteriet, CC BY 4.0"
    stream: bool = True
    auth_env: tuple[str, str] | None = ("LANTMATERIET_USER", "LANTMATERIET_PASSWORD")
    collection: str = "dtm-cog"

    def tiles(self, west, south, east, north) -> list[Tile]:
        from rasterio.warp import transform_bounds

        wgs = transform_bounds(self.crs, "EPSG:4326", west, south, east, north)
        query = urllib.parse.urlencode({
            "bbox": ",".join(f"{v:.6f}" for v in wgs),
            "limit": "100",
        })
        url = f"{STAC}/collections/{self.collection}/items?{query}"
        payload = fetch_json(url)
        tiles = []
        for feature in payload.get("features", []):
            asset = feature.get("assets", {}).get("data")
            if not asset:
                continue
            tiles.append(Tile(feature["id"], asset["href"], tuple(feature["bbox"])))
        return sorted(tiles, key=lambda t: t.name)


SOURCES = {"fi": FinlandKM2(), "se": SwedenMHM1()}


def get_source(key: str) -> Source:
    try:
        return SOURCES[key]
    except KeyError:
        raise SystemExit(f"unknown source {key!r}; choose from {sorted(SOURCES)}") from None

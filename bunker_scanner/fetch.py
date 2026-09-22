"""Getting tile pixels, either by caching the file or reading it in place."""

from __future__ import annotations

import contextlib
import pathlib
import urllib.request

import rasterio

from .sources import Source, Tile


def cache_tile(tile: Tile, dest_dir: pathlib.Path) -> pathlib.Path:
    """Download a tile unless it is already on disk. Returns the local path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{tile.name}.tif"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    partial = dest.with_suffix(".tif.part")
    with urllib.request.urlopen(tile.url, timeout=180) as response, partial.open("wb") as handle:
        while chunk := response.read(1 << 20):
            handle.write(chunk)
    partial.rename(dest)
    return dest


@contextlib.contextmanager
def gdal_env(source: Source):
    """rasterio/GDAL environment for this source, carrying credentials if it needs them."""
    options: dict[str, str] = {}
    if source.stream:
        # Only fetch the blocks a window actually touches.
        options.update(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif")
        credentials = source.credentials()
        if credentials:
            options.update(GDAL_HTTP_AUTH="BASIC", GDAL_HTTP_USERPWD=":".join(credentials))
    with rasterio.Env(**options):
        yield


def open_tile(tile: Tile, source: Source, dem_dir: pathlib.Path):
    """Open a tile for reading: remote COG in place, or cached local file."""
    if source.stream:
        return rasterio.open(f"/vsicurl/{tile.url}")
    return rasterio.open(cache_tile(tile, dem_dir))

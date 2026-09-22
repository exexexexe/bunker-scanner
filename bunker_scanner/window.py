"""Read an arbitrary bounding box out of a terrain source, mosaicking as needed."""

from __future__ import annotations

import math
import pathlib

import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.windows import from_bounds

from .fetch import gdal_env, open_tile
from .sources import Source


def snap_to_grid(source, west, south, east, north):
    """Expand a box to whole pixels of the source grid.

    A box with fractional pixel edges makes rasterio's merge lay out a grid whose
    last row/column falls outside every tile, which comes back as a one-pixel
    nodata seam along the edge of the render. Tile corners sit on whole multiples
    of the pixel size, so rounding outward to that grid removes the seam.
    """
    step = source.resolution
    return (
        math.floor(west / step) * step,
        math.floor(south / step) * step,
        math.ceil(east / step) * step,
        math.ceil(north / step) * step,
    )


class NoCoverage(RuntimeError):
    """The source has no tiles for this box — usually sea, or outside the country."""


def read_bbox(
    source: Source,
    west: float,
    south: float,
    east: float,
    north: float,
    dem_dir: pathlib.Path,
) -> tuple[np.ndarray, rasterio.Affine, float, dict]:
    """Returns (elevation in metres, transform, pixel size, a report dict).

    The report carries a boolean `void_mask` of the pixels that were filled. Any
    later pass that hunts straight edges must mask those out: the fill boundary
    is itself a hard straight edge and would read as a perfect false positive.

    The box is in the source's own CRS. Missing tiles and nodata voids are
    filled with the window median and counted in the report, so a partially
    covered box still renders instead of failing.
    """
    west, south, east, north = snap_to_grid(source, west, south, east, north)
    tiles = source.tiles(west, south, east, north)
    if not tiles:
        raise NoCoverage(f"{source.label}: no tiles cover ({west}, {south}, {east}, {north})")

    report = {"source": source.key, "bbox": [west, south, east, north],
              "tiles": [t.name for t in tiles], "missing": []}
    with gdal_env(source):
        handles = []
        try:
            for tile in tiles:
                try:
                    handles.append(open_tile(tile, source, dem_dir))
                except Exception as error:  # a tile listed but not served, or auth refused
                    report["missing"].append(f"{tile.name}: {type(error).__name__}")
            if not handles:
                raise NoCoverage(
                    f"{source.label}: none of {len(tiles)} tiles could be opened "
                    f"({'; '.join(report['missing'])})"
                )
            nodata = handles[0].nodata
            if len(handles) == 1:
                window = from_bounds(west, south, east, north, handles[0].transform)
                data = handles[0].read(1, window=window, boundless=True, fill_value=nodata)
                transform = handles[0].window_transform(window)
            else:
                data, transform = merge(handles, bounds=(west, south, east, north), nodata=nodata)
                data = data[0]
            resolution = handles[0].res[0]
        finally:
            for handle in handles:
                handle.close()

    array = np.asarray(data, dtype="float64")
    void = ~np.isfinite(array)
    if nodata is not None:
        void |= array == nodata
    report["void_pixels"] = int(void.sum())
    report["void_fraction"] = float(void.mean())
    if void.all():
        raise NoCoverage(f"{source.label}: every pixel in the box is nodata")
    if void.any():
        # Leaving voids in would poison both the gradient and the smoothing pass.
        array[void] = float(np.median(array[~void]))
    report["shape"] = tuple(array.shape)
    report["elevation_range"] = (float(array.min()), float(array.max()))
    report["void_mask"] = void
    return array, transform, resolution, report

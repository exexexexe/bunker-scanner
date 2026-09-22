"""Terrain visualisations tuned to make subtle earthworks readable.

Everything here works on a bare-earth DTM array in metres with a square pixel
size, so it is source-agnostic (Finland 2 m today, Sweden 1 m later).
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage


def _gradients(dem: np.ndarray, res: float, z_factor: float):
    dy, dx = np.gradient(dem.astype("float64") * z_factor, res, res)
    # Row 0 is the north edge, so a positive dy means the surface falls northward.
    return dx, -dy


def hillshade(
    dem: np.ndarray,
    res: float,
    azimuth: float = 315.0,
    altitude: float = 45.0,
    z_factor: float = 1.0,
) -> np.ndarray:
    """Classic Lambertian hillshade, returned as float in [0, 1]."""
    dx, dy = _gradients(dem, res, z_factor)
    slope = np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(dy, -dx)
    zenith = np.radians(90.0 - altitude)
    az = np.radians(360.0 - azimuth + 90.0)
    shaded = np.cos(zenith) * np.cos(slope) + np.sin(zenith) * np.sin(slope) * np.cos(az - aspect)
    return np.clip(shaded, 0.0, 1.0)


def multidirectional_hillshade(
    dem: np.ndarray,
    res: float,
    azimuths=(315.0, 45.0, 135.0, 225.0),
    altitude: float = 35.0,
    z_factor: float = 1.0,
) -> np.ndarray:
    """Mean of several illumination directions — no earthwork hides in the shadow
    of a single sun angle, which is the usual failure mode of a plain hillshade."""
    stack = [hillshade(dem, res, az, altitude, z_factor) for az in azimuths]
    return np.mean(stack, axis=0)


def local_relief_model(dem: np.ndarray, res: float, kernel_m: float = 20.0) -> np.ndarray:
    """DTM minus a smoothed copy of itself: strips the landform-scale slope and
    leaves only relief smaller than `kernel_m`, in metres (positive = raised)."""
    sigma = max(kernel_m / res / 2.0, 0.5)
    return dem.astype("float64") - ndimage.gaussian_filter(dem.astype("float64"), sigma)


def stretch(array: np.ndarray, low: float = 2.0, high: float = 98.0) -> np.ndarray:
    """Percentile contrast stretch to [0, 1] — LRM values are tiny and would
    otherwise render as flat grey."""
    lo, hi = np.percentile(array, [low, high])
    if hi <= lo:
        return np.zeros_like(array, dtype="float64")
    return np.clip((array - lo) / (hi - lo), 0.0, 1.0)


def sky_view_factor(
    dem: np.ndarray, res: float, radius_m: float = 20.0, directions: int = 16
) -> np.ndarray:
    """Fraction of the sky hemisphere visible from each pixel, in [0, 1].

    Ditches, trench cuts and bunker entrances sit low against their own walls and
    come out dark; mounds and parapets come out bright. Unlike a hillshade it has
    no illumination direction at all, so nothing can hide in a shadow.

    Zaksek et al. (2011): average of (1 - sin(horizon angle)) over `directions`
    evenly spaced azimuths, searching out to `radius_m`.
    """
    steps = max(int(round(radius_m / res)), 1)
    height, width = dem.shape
    padded = np.pad(dem, steps, mode="edge")
    total = np.zeros((height, width), dtype="float64")

    for index in range(directions):
        azimuth = 2.0 * np.pi * index / directions
        dx, dy = np.cos(azimuth), np.sin(azimuth)
        highest = np.zeros((height, width), dtype="float64")
        for step in range(1, steps + 1):
            offset_x, offset_y = int(round(dx * step)), int(round(dy * step))
            distance = np.hypot(offset_x, offset_y) * res
            if distance == 0:
                continue
            # Row indices grow southward, so north is a negative row offset.
            row = steps - offset_y
            col = steps + offset_x
            neighbour = padded[row:row + height, col:col + width]
            np.maximum(highest, (neighbour - dem) / distance, out=highest)
        total += 1.0 - np.sin(np.arctan(np.maximum(highest, 0.0)))

    return total / directions

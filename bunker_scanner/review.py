"""Build a self-contained candidate review page from a detection run.

Everything is embedded — terrain crops as data URIs, candidates as inline JSON —
so the page is one file that works offline, opened from disk or published.
Deliberately no slippy map: third-party tiles do not load in a published
artifact, and the sky-view render of the window is better material than a road
map for judging earthworks anyway.
"""

from __future__ import annotations

import base64
import html
import io
import json
import pathlib

import numpy as np
from matplotlib.image import imsave

from .imagery import read_window as read_ortho
from .render import hillshade, local_relief_model, sky_view_factor, stretch
from .sources import get_source
from .window import read_bbox

TEMPLATE = pathlib.Path(__file__).resolve().parent / "review_template.html"


def _png_data_uri(array: np.ndarray, cmap: str = "gray") -> str:
    buffer = io.BytesIO()
    imsave(buffer, array, cmap=cmap, vmin=0.0, vmax=1.0, origin="upper", format="png")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _jpeg_data_uri(rgb: np.ndarray, size: int = 200, quality: int = 78) -> str:
    """Photographs as JPEG, not PNG.

    A 160 m aerial crop at 0.5 m is 320 x 320 of photographic detail; as lossless
    PNG that is ~330 KB, and twenty of them took the review page from 0.9 MB to
    7.8 MB. The card displays it at about 70 px.
    """
    from PIL import Image

    image = Image.fromarray(rgb.astype("uint8"), mode="RGB")
    if max(image.size) > size:
        image = image.resize((size, size), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _crop(array: np.ndarray, row: float, col: float, half_px: int) -> np.ndarray:
    top = int(round(row)) - half_px
    left = int(round(col)) - half_px
    padded = np.pad(array, half_px, mode="edge")
    return padded[top + half_px:top + 3 * half_px, left + half_px:left + 3 * half_px]


def build(detection_dir: pathlib.Path, dem_dir: pathlib.Path,
          crop_m: float = 160.0, imagery: bool = True) -> tuple[str, dict]:
    payload = json.loads((detection_dir / "candidates.geojson").read_text())
    if "window" not in payload:
        raise SystemExit(
            f"{detection_dir.name} was produced before detect_bbox.py recorded its "
            "window; re-run the detection for this box and try again.")
    window = payload["window"]
    features = payload["features"]

    source = get_source(window["country"])
    west, south, east, north = window["bbox"]
    dem, transform, res, report = read_bbox(source, west, south, east, north, dem_dir)
    lrm = local_relief_model(dem, res, 15.0)
    svf = stretch(sky_view_factor(dem, res, 20.0), 1, 99)
    shade = hillshade(dem, res, 315, 30, z_factor=3)

    overview = _png_data_uri(svf)
    half_px = max(int(round(crop_m / 2 / res)), 8)

    from rasterio.transform import rowcol
    from rasterio.warp import transform as warp_transform

    candidates = []
    imagery_years: set[str] = set()
    for feature in features:
        props = dict(feature["properties"])
        lon, lat = props["centre_lon"], props["centre_lat"]
        xs, ys = warp_transform("EPSG:4326", source.crs, [lon], [lat])
        row, col = rowcol(transform, xs[0], ys[0])
        props["lrm_crop"] = _png_data_uri(
            stretch(_crop(lrm, row, col, half_px), 1, 99))
        props["svf_crop"] = _png_data_uri(_crop(svf, row, col, half_px))
        props["shade_crop"] = _png_data_uri(_crop(shade, row, col, half_px))
        if imagery:
            half_m = crop_m / 2
            photo, year = read_ortho(xs[0] - half_m, ys[0] - half_m,
                                     xs[0] + half_m, ys[0] + half_m)
            if photo is not None:
                props["ortho_crop"] = _jpeg_data_uri(photo)
                props["ortho_year"] = year
                imagery_years.add(year)
        # Position within the overview image, as a percentage.
        props["x_pct"] = round(100.0 * (xs[0] - west) / (east - west), 3)
        props["y_pct"] = round(100.0 * (north - ys[0]) / (north - south), 3)
        coords = feature["geometry"]["coordinates"]
        path_x, path_y = warp_transform("EPSG:4326", source.crs,
                                        [c[0] for c in coords], [c[1] for c in coords])
        props["path"] = [[round(100.0 * (x - west) / (east - west), 3),
                          round(100.0 * (north - y) / (north - south), 3)]
                         for x, y in zip(path_x, path_y)]
        candidates.append(props)

    context = {
        "window": window,
        "candidates": candidates,
        "overview": overview,
        "crop_m": crop_m,
        "elevation_range": report["elevation_range"],
        "void_pixels": report["void_pixels"],
        "imagery_years": sorted(imagery_years),
    }
    page = TEMPLATE.read_text()
    page = page.replace("/*__DATA__*/null", json.dumps(context))
    page = page.replace("__WINDOW_NAME__", html.escape(window["name"]))
    return page, context

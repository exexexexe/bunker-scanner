"""Validate a render against published coordinates, for any country with a register.

    scripts/validate_cluster.py --country fi --target miehikkala
    scripts/validate_cluster.py --country se --target skanelinjen

The check is whether a structure sits *at* each published coordinate, not whether
the frame contains anthropogenic-looking texture somewhere. Local relief at each
point is reported against the distribution over random points in the same window,
so a weak hit shows up as a weak hit.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
from rasterio.transform import rowcol

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bunker_scanner import reference
from bunker_scanner.plot import save_map
from bunker_scanner.render import hillshade, local_relief_model, sky_view_factor, stretch
from bunker_scanner.sources import get_source
from bunker_scanner.window import NoCoverage, read_bbox

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEM_DIR = ROOT / "data" / "dem"


def relief_amplitude(lrm, transform, east, north, radius_m, res):
    radius_px = max(int(round(radius_m / res)), 2)
    row, col = rowcol(transform, east, north)
    if not (radius_px <= row < lrm.shape[0] - radius_px
            and radius_px <= col < lrm.shape[1] - radius_px):
        return None
    patch = lrm[row - radius_px:row + radius_px + 1, col - radius_px:col + radius_px + 1]
    return float(patch.max() - patch.min())


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", default="fi", choices=sorted(reference.REGISTERS))
    parser.add_argument("--target", default=None)
    parser.add_argument("--half", type=float, default=400.0, help="half-width in metres")
    parser.add_argument("--probe-radius", type=float, default=16.0,
                        help="metres around each point to measure relief over")
    parser.add_argument("--out", default=None, help="output directory")
    parser.add_argument("--crops", action="store_true", help="also write 120 m per-point crops")
    args = parser.parse_args(argv)

    register = reference.register(args.country)
    target = args.target or sorted(register.targets)[0]
    source = get_source(args.country)
    if source.crs != register.crs:
        raise SystemExit(f"register CRS {register.crs} != source CRS {source.crs}")
    if source.stream and not source.credentials():
        user, password = source.auth_env
        raise SystemExit(f"{source.label} needs {user} and {password} in the environment.")

    out_dir = pathlib.Path(args.out) if args.out else ROOT / "verification" / f"{args.country}-{target}"
    box = reference.target_box(args.country, target, args.half)

    try:
        dem, transform, res, report = read_bbox(source, *box, DEM_DIR)
    except NoCoverage as error:
        raise SystemExit(str(error)) from None

    extent = (box[0], box[2], box[1], box[3])
    points = reference.within(reference.points(args.country), *box)
    lines = reference.lines(args.country)
    print(f"{args.country}/{target}: {report['shape']} px @ {res} m, "
          f"{len(report['tiles'])} tile(s), {report['void_pixels']} void px, "
          f"{len(points)} documented structures in frame")
    print(f"  {register.targets[target].note}")

    lrm_raw = local_relief_model(dem, res, 15.0)
    renders = {
        "lrm-k15m": stretch(lrm_raw, 1, 99),
        "hillshade-az315-alt30-z3": hillshade(dem, res, 315, 30, z_factor=3),
        "svf-r20m": stretch(sky_view_factor(dem, res, 20.0), 1, 99),
    }
    for tag, array in renders.items():
        save_map(out_dir / f"{tag}.png", array, extent, f"{target} — {tag}", points, lines, size=11)

    rng = np.random.default_rng(0)
    margin = max(int(round(args.probe_radius / res)), 2)
    background = []
    for _ in range(4000):
        row = int(rng.integers(margin, lrm_raw.shape[0] - margin))
        col = int(rng.integers(margin, lrm_raw.shape[1] - margin))
        patch = lrm_raw[row - margin:row + margin + 1, col - margin:col + margin + 1]
        background.append(float(patch.max() - patch.min()))
    background = np.array(background)
    print(f"  background local relief over {2 * args.probe_radius:.0f} m: "
          f"median {np.median(background):.2f} m, 90th pct {np.percentile(background, 90):.2f} m")
    for east_p, north_p, name in sorted(points, key=lambda p: (p[2], p[0])):
        amplitude = relief_amplitude(lrm_raw, transform, east_p, north_p, args.probe_radius, res)
        if amplitude is None:
            continue
        percentile = 100.0 * (background < amplitude).mean()
        print(f"    {name or '(unnamed)':32s} {amplitude:5.2f} m  {percentile:5.1f}th pct")

    if args.crops:
        for east_p, north_p, name in points:
            slug = (name or f"{east_p:.0f}-{north_p:.0f}").lower().replace(" ", "-").replace("/", "-")
            crop_box = (east_p - 60, north_p - 60, east_p + 60, north_p + 60)
            crop, _, crop_res, _ = read_bbox(source, *crop_box, DEM_DIR)
            crop_extent = (crop_box[0], crop_box[2], crop_box[1], crop_box[3])
            save_map(out_dir / f"crop-{slug}-120m-lrm.png",
                     stretch(local_relief_model(crop, crop_res, 15.0), 1, 99),
                     crop_extent, None, [(east_p, north_p, "")], labels=False)
    print(f"  wrote to {out_dir}")


if __name__ == "__main__":
    main()

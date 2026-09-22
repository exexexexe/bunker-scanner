"""Phase 1 — render terrain derivatives for an arbitrary bounding box.

    # by centre and radius, in lon/lat
    scripts/render_bbox.py --centre 27.6658,60.6806 --radius 400 --name miehikkala

    # by explicit box, in the source's own CRS
    scripts/render_bbox.py --bbox 536000,6726600,536800,6727400 --crs native

    # Sweden (needs LANTMATERIET_USER / LANTMATERIET_PASSWORD)
    scripts/render_bbox.py --country se --centre 18.05,59.35 --radius 400
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from rasterio.warp import transform as warp_transform

from bunker_scanner.plot import save_raw
from bunker_scanner.render import (
    hillshade,
    local_relief_model,
    multidirectional_hillshade,
    sky_view_factor,
    stretch,
)
from bunker_scanner.sources import get_source
from bunker_scanner.window import NoCoverage, read_bbox

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEM_DIR = ROOT / "data" / "dem"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--country", default="fi", choices=("fi", "se"))
    parser.add_argument("--bbox", help="west,south,east,north")
    parser.add_argument("--centre", help="lon,lat (or east,north with --crs native)")
    parser.add_argument("--radius", type=float, default=400.0, help="metres, with --centre")
    parser.add_argument("--crs", default="wgs84", choices=("wgs84", "native"))
    parser.add_argument("--name", help="output basename (default: derived from the box)")
    parser.add_argument("--out", default=str(ROOT / "output"), help="output directory")
    parser.add_argument("--lrm-kernel", type=float, default=15.0)
    parser.add_argument("--svf-radius", type=float, default=20.0)
    parser.add_argument("--geotiff", action="store_true", help="also write the DEM crop")
    args = parser.parse_args(argv)
    if bool(args.bbox) == bool(args.centre):
        parser.error("give exactly one of --bbox or --centre")
    return args


def to_native(source, values, crs_mode):
    """Project a flat [x, y, ...] list into the source CRS if it came in as lon/lat."""
    if crs_mode == "native":
        return values
    xs = values[0::2]
    ys = values[1::2]
    projected_x, projected_y = warp_transform("EPSG:4326", source.crs, xs, ys)
    out = []
    for x, y in zip(projected_x, projected_y):
        out.extend((x, y))
    return out


def resolve_bbox(args, source):
    if args.bbox:
        values = [float(v) for v in args.bbox.split(",")]
        if len(values) != 4:
            raise SystemExit("--bbox needs west,south,east,north")
        west, south, east, north = to_native(source, values, args.crs)
        if west > east or south > north:
            raise SystemExit("--bbox is inverted: expected west,south,east,north")
        return west, south, east, north
    values = [float(v) for v in args.centre.split(",")]
    if len(values) != 2:
        raise SystemExit("--centre needs lon,lat")
    east, north = to_native(source, values, args.crs)
    return east - args.radius, north - args.radius, east + args.radius, north + args.radius


def main(argv=None):
    args = parse_args(argv)
    source = get_source(args.country)

    if source.stream and not source.credentials():
        user, password = source.auth_env
        raise SystemExit(
            f"{source.label} needs credentials. Register a free account at "
            f"geotorget.lantmateriet.se, then set {user} and {password}."
        )

    west, south, east, north = resolve_bbox(args, source)
    name = args.name or f"{source.key}-{west:.0f}-{south:.0f}-{east - west:.0f}m"
    out_dir = pathlib.Path(args.out) / name
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        dem, transform, res, report = read_bbox(source, west, south, east, north, DEM_DIR)
    except NoCoverage as error:
        raise SystemExit(str(error)) from None

    report.update(name=name, crs=source.crs,
                  resolution=res, attribution=source.attribution)
    print(f"{name}: {report['shape'][1]}x{report['shape'][0]} px @ {res} m from "
          f"{len(report['tiles'])} tile(s); elevation "
          f"{report['elevation_range'][0]:.1f}-{report['elevation_range'][1]:.1f} m")
    if report["missing"]:
        print(f"  missing tiles: {', '.join(report['missing'])}")
    if report["void_pixels"]:
        print(f"  nodata voids filled: {report['void_pixels']} px "
              f"({report['void_fraction'] * 100:.2f}%)")

    renders = {
        "hillshade-az315-alt30-z3": hillshade(dem, res, 315, 30, z_factor=3),
        "hillshade-multidirectional": multidirectional_hillshade(dem, res, altitude=25),
        f"lrm-k{args.lrm_kernel:.0f}m": stretch(local_relief_model(dem, res, args.lrm_kernel), 1, 99),
        f"svf-r{args.svf_radius:.0f}m": stretch(
            sky_view_factor(dem, res, args.svf_radius), 1, 99),
    }
    for render_name, array in renders.items():
        save_raw(out_dir / f"{render_name}.png", array)
    report["renders"] = sorted(renders)

    void_mask = report.pop("void_mask")
    if report["void_pixels"]:
        # The fill boundary is a hard straight edge; Phase 2 has to be able to mask it.
        save_raw(out_dir / "void-mask.png", void_mask.astype("float64"))
        report["void_mask_image"] = "void-mask.png"

    if args.geotiff:
        import rasterio
        path = out_dir / "dem.tif"
        with rasterio.open(path, "w", driver="GTiff", height=dem.shape[0], width=dem.shape[1],
                           count=1, dtype="float32", crs=source.crs, transform=transform,
                           compress="deflate") as sink:
            sink.write(dem.astype("float32"), 1)
        report["geotiff"] = path.name

    (out_dir / "report.json").write_text(json.dumps(report, indent=2))
    print(f"  wrote {len(renders)} renders to {out_dir}")
    return report


if __name__ == "__main__":
    main()

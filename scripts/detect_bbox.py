"""Phase 2 — run the heuristic detector over a box and write reviewable output.

    scripts/detect_bbox.py --country fi --target miehikkala --half 420
    scripts/detect_bbox.py --bbox 536000,6726600,536800,6727400 --crs native

Writes a numbered annotated render, candidates.geojson (WGS84) and
candidates.csv, so every candidate can be looked at and judged by eye.
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from rasterio.warp import transform as warp_transform

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bunker_scanner import reference
from bunker_scanner.heritage import Register
from bunker_scanner.detect import detect
from bunker_scanner.plot import draw
from bunker_scanner.render import local_relief_model, sky_view_factor, stretch
from bunker_scanner.sources import get_source
from bunker_scanner.window import read_bbox

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEM_DIR = ROOT / "data" / "dem"


def pixel_to_crs(transform, x, y):
    return transform * (x + 0.5, y + 0.5)


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", default="fi")
    parser.add_argument("--target", default=None)
    parser.add_argument("--bbox", default=None, help="west,south,east,north")
    parser.add_argument("--crs", default="wgs84", choices=("wgs84", "native"))
    parser.add_argument("--half", type=float, default=420.0)
    parser.add_argument("--name", default=None)
    parser.add_argument("--out", default=str(ROOT / "output" / "detect"))
    parser.add_argument("--min-score", type=float, default=0.0)
    parser.add_argument("--min-beads", type=int, default=6)
    parser.add_argument("--min-length", type=float, default=60.0)
    parser.add_argument("--max-gap", type=float, default=20.0)
    parser.add_argument("--min-relief", type=float, default=0.35)
    parser.add_argument("--heritage", action="store_true",
                        help="classify candidates against the national heritage register")
    parser.add_argument("--heritage-distance", type=float, default=50.0,
                        help="metres from a registered site to count as documented")
    parser.add_argument("--undocumented-only", action="store_true",
                        help="keep only candidates the register does not already cover")
    parser.add_argument("--reference", action="store_true",
                        help="draw the published register alongside the candidates")
    return parser.parse_args(argv)


def resolve_box(args, source):
    if args.bbox:
        values = [float(v) for v in args.bbox.split(",")]
        if args.crs == "wgs84":
            xs, ys = warp_transform("EPSG:4326", source.crs,
                                    [values[0], values[2]], [values[1], values[3]])
            return xs[0], ys[0], xs[1], ys[1]
        return tuple(values)
    target = args.target or sorted(reference.register(args.country).targets)[0]
    return reference.target_box(args.country, target, args.half)


def main(argv=None):
    args = parse_args(argv)
    source = get_source(args.country)
    box = resolve_box(args, source)
    name = args.name or args.target or f"{args.country}-{box[0]:.0f}-{box[1]:.0f}"
    out_dir = pathlib.Path(args.out) / name
    out_dir.mkdir(parents=True, exist_ok=True)

    dem, transform, res, report = read_bbox(source, *box, DEM_DIR)
    lrm = local_relief_model(dem, res, 15.0)
    svf = stretch(sky_view_factor(dem, res, 20.0), 1, 99)
    exclude = report["void_mask"]

    chains, beads = detect(lrm, res, exclude=exclude,
                           min_relief=args.min_relief, max_gap_m=args.max_gap,
                           min_beads=args.min_beads, min_length_m=args.min_length)
    chains = [c for c in chains if c.score >= args.min_score]
    print(f"{name}: {report['shape']} px @ {res} m — {len(beads)} beads, "
          f"{len(chains)} candidate chains")

    register = None
    if args.heritage:
        register = Register.for_box(args.country, *box)
        print(f"  heritage register: {len(register.entries)} sites near this box")

    rows = []
    for index, chain in enumerate(chains, 1):
        coords = [pixel_to_crs(transform, b.x, b.y) for b in chain.beads]
        lons, lats = warp_transform(source.crs, "EPSG:4326",
                                    [c[0] for c in coords], [c[1] for c in coords])
        centre_x, centre_y = pixel_to_crs(transform, *chain.centroid)
        centre_lon, centre_lat = warp_transform(source.crs, "EPSG:4326",
                                                [centre_x], [centre_y])
        verdict = {}
        if register is not None:
            from shapely.geometry import LineString, Point
            geometry = (LineString(coords) if len(coords) > 1 else Point(coords[0]))
            verdict = register.classify(geometry, args.heritage_distance)
        rows.append({
            "id": index, "score": chain.score, "polarity": chain.polarity,
            "beads": len(chain.beads),
            "length_m": round(chain.length_m, 1),
            "straightness": round(chain.straightness, 3),
            "spacing_cv": round(chain.spacing_cv, 3),
            "beadedness": round(chain.beadedness, 3),
            "roughness": round(chain.roughness, 3),
            "demoted": chain.demoted,
            "mean_relief_m": round(chain.mean_relief_m, 2),
            "centre_lat": round(centre_lat[0], 6), "centre_lon": round(centre_lon[0], 6),
            **verdict,
            "geometry": [[round(lo, 6), round(la, 6)] for lo, la in zip(lons, lats)],
        })
        print(f"  #{index:2d} {chain.score:.3f} {chain.polarity:6s} {len(chain.beads):3d} beads "
              f"{chain.length_m:6.1f} m  rough {chain.roughness:.3f}  "
              f"{'DEMOTED ' if chain.demoted else ''}"
              f"{centre_lat[0]:.5f},{centre_lon[0]:.5f}"
              + (f"  [{verdict['status']}"
                 + (f": {verdict.get('site_name','')}" if verdict.get('site_name') else "")
                 + "]" if verdict else ""))

    if register is not None:
        tally = {}
        for row in rows:
            tally[row.get("status", "unclassified")] = tally.get(row.get("status", "unclassified"), 0) + 1
        print("  register verdict: " + ", ".join(f"{k} {v}" for k, v in sorted(tally.items())))
        if args.undocumented_only:
            keep = {r["id"] for r in rows if r.get("status") == "undocumented"}
            rows = [r for r in rows if r["id"] in keep]
            chains = [c for i, c in enumerate(chains, 1) if i in keep]
            print(f"  kept {len(rows)} undocumented candidate(s)")

    (out_dir / "candidates.geojson").write_text(json.dumps({
        "type": "FeatureCollection",
        "note": "Heuristic shortlist, not confirmed finds. Score is a ranking "
                "indicator, not a probability.",
        "window": {"country": args.country, "crs": source.crs, "name": name,
                   "bbox": [round(v, 2) for v in box],
                   "resolution_m": res, "tiles": report["tiles"],
                   "source": source.label, "attribution": source.attribution},
        "features": [{
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": r["geometry"]},
            "properties": {k: v for k, v in r.items() if k != "geometry"},
        } for r in rows],
    }, indent=2))

    with (out_dir / "candidates.csv").open("w", newline="") as handle:
        fields = [k for k in rows[0].keys() if k != "geometry"] if rows else ["id"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: v for k, v in row.items() if k != "geometry"})

    extent = (box[0], box[2], box[1], box[3])
    points = reference.within(reference.points(args.country), *box) if args.reference else []
    lines = reference.lines(args.country) if args.reference else []
    fig, ax = plt.subplots(figsize=(13, 13), dpi=150)
    draw(ax, svf, extent, f"{name} — SVF; magenta = raised chain, green = cut chain ({len(chains)} candidates)",
         points, lines, labels=False)
    for index, chain in enumerate(chains, 1):
        coords = [pixel_to_crs(transform, b.x, b.y) for b in chain.beads]
        status = rows[index - 1].get("status") if index <= len(rows) else None
        if chain.demoted:
            colour = "#888888"
        elif status == "known_military":
            colour = "#1e90ff"
        elif status == "known_other":
            colour = "#ffa500"
        else:
            colour = "#ff00ff" if chain.polarity == "raised" else "#00ff66"
        ax.plot([c[0] for c in coords], [c[1] for c in coords],
                color=colour, linewidth=1.3, alpha=0.9)
        ax.scatter([c[0] for c in coords], [c[1] for c in coords],
                   s=9, facecolors="none", edgecolors=colour, linewidths=0.7)
        ax.annotate(f"{index}", coords[0], textcoords="offset points", xytext=(6, 5),
                    color=colour, fontsize=9, weight="bold")
    fig.tight_layout()
    fig.savefig(out_dir / "candidates.png")
    plt.close(fig)
    print(f"  wrote {out_dir}")
    return rows


if __name__ == "__main__":
    main()

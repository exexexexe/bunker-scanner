"""Phase 2 gate — measure the detector, don't just run it.

Reports, for a labelled window and a set of control windows with no known
fortifications, how many candidates survive each score threshold per km², and
how many of the labelled window's candidates land on published Salpa Line
geometry.

Caveat carried into the output: the register is *incomplete*. The barrier is
visibly longer than the mapped ways, so an unmatched candidate is not
automatically a false positive — it has to be looked at. That is why this script
reports "matched / unmatched" rather than "true / false".
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bunker_scanner import reference
from bunker_scanner.detect import detect
from bunker_scanner.render import local_relief_model
from bunker_scanner.sources import get_source
from bunker_scanner.window import read_bbox

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEM_DIR = ROOT / "data" / "dem"

CONTROLS = {
    "forest-keski": (25.50, 62.50, 25.53, 62.515),
    "farmland-pohjanmaa": (22.80, 63.00, 22.83, 63.015),
    "forest-hame": (24.50, 61.20, 24.53, 61.215),
}
THRESHOLDS = (0.3, 0.4, 0.5, 0.6)


def run(source, box, params):
    dem, transform, res, report = read_bbox(source, *box, DEM_DIR)
    lrm = local_relief_model(dem, res, 15.0)
    chains, beads = detect(lrm, res, exclude=report["void_mask"], **params)
    area_km2 = (box[2] - box[0]) * (box[3] - box[1]) / 1e6
    return chains, beads, transform, area_km2, report


def densify(lines, box, step=2.0):
    points = []
    for coords, _ in lines:
        for (x0, y0), (x1, y1) in zip(coords, coords[1:]):
            steps = max(int(math.hypot(x1 - x0, y1 - y0) / step), 1)
            for k in range(steps + 1):
                x = x0 + (x1 - x0) * k / steps
                y = y0 + (y1 - y0) * k / steps
                if box[0] <= x <= box[2] and box[1] <= y <= box[3]:
                    points.append((x, y))
    return np.array(points) if points else np.empty((0, 2))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--half", type=float, default=420.0)
    parser.add_argument("--tolerance", type=float, default=20.0,
                        help="metres from a mapped feature to count as matched")
    parser.add_argument("--out", default=str(ROOT / "verification" / "phase-2"))
    args = parser.parse_args(argv)

    source = get_source("fi")
    params = {"min_relief": 0.35, "max_gap_m": 20.0, "min_beads": 6, "min_length_m": 60.0}
    summary = {"params": params, "tolerance_m": args.tolerance, "windows": {}}

    # ---- labelled window
    box = reference.target_box("fi", "miehikkala", args.half)
    chains, beads, transform, area, _ = run(source, box, params)
    truth = densify(reference.lines("fi"), box)
    truth = np.vstack([truth, np.array([[p[0], p[1]] for p in
                                        reference.within(reference.points("fi"), *box)])]) \
        if len(truth) else truth
    print(f"labelled window: {area:.2f} km2, {len(beads)} beads, {len(chains)} chains, "
          f"{len(truth)} ground-truth samples")

    rows = []
    for index, chain in enumerate(sorted(chains, key=lambda c: -c.score), 1):
        centres = np.array([list(transform * (b.x + 0.5, b.y + 0.5)) for b in chain.beads])
        if len(truth):
            distances = [np.min(np.hypot(truth[:, 0] - x, truth[:, 1] - y)) for x, y in centres]
            matched = float(np.median(distances)) <= args.tolerance
            nearest = float(np.min(distances))
        else:
            matched, nearest = False, float("nan")
        rows.append({"rank": index, "score": chain.score, "polarity": chain.polarity,
                     "length_m": round(chain.length_m, 1), "demoted": chain.demoted,
                     "matched": matched, "nearest_truth_m": round(nearest, 1)})
    summary["windows"]["miehikkala"] = {
        "area_km2": round(area, 3), "chains": len(chains), "candidates": rows}

    print(f"\n{'rank':>4} {'score':>5} {'pol':6} {'len':>6} {'nearest':>8}  matched  demoted")
    for row in rows:
        print(f"{row['rank']:4d} {row['score']:5.3f} {row['polarity']:6} "
              f"{row['length_m']:6.1f} {row['nearest_truth_m']:8.1f}  "
              f"{'yes' if row['matched'] else ' no':>7}  {'yes' if row['demoted'] else ''}")

    # ---- controls
    print("\ncandidates per km2 above score threshold")
    header = "  ".join(f">={t:.1f}" for t in THRESHOLDS)
    print(f"{'window':28} {'area':>6}  {header}")
    density = {}
    from rasterio.warp import transform as warp_transform
    windows = [("miehikkala (labelled)", None)] + list(CONTROLS.items())
    for label, corners in windows:
        if corners is None:
            window_chains, window_area = chains, area
        else:
            w, s, e, n = corners
            xs, ys = warp_transform("EPSG:4326", source.crs, [w, e], [s, n])
            window_chains, _, _, window_area, _ = run(
                source, (xs[0], ys[0], xs[1], ys[1]), params)
        counts = [sum(1 for c in window_chains if c.score >= t) / window_area
                  for t in THRESHOLDS]
        density[label] = {"area_km2": round(window_area, 3),
                          "per_km2": {f"{t:.1f}": round(c, 1)
                                      for t, c in zip(THRESHOLDS, counts)}}
        print(f"{label:28} {window_area:6.2f}  " +
              "  ".join(f"{c:4.1f}" for c in counts))
    summary["density_per_km2"] = density

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "evaluation.json").write_text(json.dumps(summary, indent=2))
    print(f"\nwrote {out_dir / 'evaluation.json'}")


if __name__ == "__main__":
    main()

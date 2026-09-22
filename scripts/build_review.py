"""Build the candidate review page for a detection run.

    scripts/build_review.py --run miehikkala
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bunker_scanner.review import build

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="name under output/detect/")
    parser.add_argument("--crop", type=float, default=160.0, help="crop width in metres")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    detection_dir = ROOT / "output" / "detect" / args.run
    if not (detection_dir / "candidates.geojson").exists():
        raise SystemExit(f"no detection run at {detection_dir}; run detect_bbox.py first")

    page, context = build(detection_dir, ROOT / "data" / "dem", crop_m=args.crop)
    out = pathlib.Path(args.out) if args.out else detection_dir / "review.html"
    out.write_text(page)
    size_mb = len(page.encode()) / 1e6
    print(f"{args.run}: {len(context['candidates'])} candidates -> {out} ({size_mb:.1f} MB)")
    return out


if __name__ == "__main__":
    main()

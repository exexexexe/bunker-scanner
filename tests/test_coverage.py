"""Tile enumeration must cover every point of a requested box, with no gaps.

Regression: stepping by one tile width from the box's own edge (rather than from
the enclosing tile's corner) skipped interior tiles whenever the box was not
tile-aligned, leaving a rectangular hole in the middle of the mosaic.

Run: .venv/bin/python tests/test_coverage.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bunker_scanner.sources import get_source

CASES = [
    ("unaligned 10 km box", 196_000, 6_706_000, 206_000, 6_716_000),
    ("exactly one tile", 536_000, 6_720_000, 542_000, 6_726_000),
    ("sub-tile box", 536_300, 6_726_900, 536_500, 6_727_100),
    ("four-way sheet corner", 499_000, 6_761_000, 501_000, 6_763_000),
    ("tall thin box", 536_100, 6_714_000, 536_300, 6_732_000),
    ("wide flat box", 520_000, 6_726_100, 560_000, 6_726_300),
]

source = get_source("fi")
failures = 0

for label, west, south, east, north in CASES:
    tiles = source.tiles(west, south, east, north)
    holes = []
    step = 200.0
    y = south + step / 2
    while y < north:
        x = west + step / 2
        while x < east:
            if not any(t.bounds[0] <= x < t.bounds[2] and t.bounds[1] <= y < t.bounds[3]
                       for t in tiles):
                holes.append((x, y))
            x += step
        y += step
    status = "ok" if not holes else f"FAIL {len(holes)} uncovered point(s), e.g. {holes[0]}"
    if holes:
        failures += 1
    print(f"{label:24s} {len(tiles):3d} tiles  {status}")

print(f"{len(CASES)} boxes checked, {failures} failure(s)")
sys.exit(1 if failures else 0)

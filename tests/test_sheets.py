"""Round-trip the sheet index against tile geotransforms read off the mirror.

Run: .venv/bin/python tests/test_sheets.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bunker_scanner.sheets import tile_bounds, tile_name, tile_path

# (name, west, south) as reported by rasterio for the real tile on the mirror.
KNOWN = [
    ("L4311A", 404_000, 6_666_000),
    ("L4311B", 404_000, 6_672_000),
    ("L4312A", 404_000, 6_678_000),
    ("L4321A", 404_000, 6_690_000),
    ("L4111A", 308_000, 6_666_000),
    ("L4211A", 308_000, 6_714_000),
    ("L4411A", 404_000, 6_714_000),
    ("M4111A", 308_000, 6_762_000),
    ("L5213F", 536_000, 6_720_000),
    ("L5214C", 530_000, 6_726_000),
    ("L5214E", 536_000, 6_726_000),
]

failures = 0
for name, west, south in KNOWN:
    bounds = tile_bounds(name)
    if bounds != (west, south, west + 6_000, south + 6_000):
        print(f"FAIL bounds {name}: {bounds}")
        failures += 1
    for dx, dy in ((1, 1), (5_999, 5_999), (3_000, 3_000)):
        got = tile_name(west + dx, south + dy)
        if got != name:
            print(f"FAIL name at ({west + dx}, {south + dy}): {got} != {name}")
            failures += 1

if tile_path("L5213F") != "L5/L52/L5213F.tif":
    print("FAIL tile_path")
    failures += 1

print(f"{len(KNOWN)} sheets checked, {failures} failure(s)")
sys.exit(1 if failures else 0)

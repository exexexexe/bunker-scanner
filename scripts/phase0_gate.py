"""Phase 0 gate figure — plain render beside the same render with the register on top.

Regenerates the evidence in verification/phase-0/. Unchanged in intent since
Phase 0; ported onto the Phase 1 source/plot modules.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bunker_scanner import reference
from bunker_scanner.plot import save_comparison
from bunker_scanner.render import (
    hillshade,
    local_relief_model,
    sky_view_factor,
    stretch,
)
from bunker_scanner.sources import get_source
from bunker_scanner.window import read_bbox

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEM_DIR = ROOT / "data" / "dem"
OUT_DIR = ROOT / "verification" / "phase-0"

HALF = 420.0
OVERLAY_TITLE = ("documented Salpa Line geometry overlaid\n"
                 "red = military=bunker, cyan = barrier=tank_trap, yellow = military=trench")


def main():
    source = get_source("fi")
    box = reference.target_box("fi", "miehikkala", HALF)
    dem, _, res, report = read_bbox(source, *box, DEM_DIR)
    extent = (box[0], box[2], box[1], box[3])
    print(f"gate window {report['shape']} px @ {res} m, {len(report['tiles'])} tiles, "
          f"{report['void_pixels']} void px")

    points = reference.within(reference.points("fi"), *box)
    lines = reference.lines("fi")

    renders = {
        "hillshade-az315-alt30-z3": hillshade(dem, res, 315, 30, z_factor=3),
        "lrm-k15m": stretch(local_relief_model(dem, res, 15.0), 1, 99),
        "svf-r20m": stretch(sky_view_factor(dem, res, 20.0), 1, 99),
    }
    for tag, array in renders.items():
        path = save_comparison(
            OUT_DIR / f"GATE-{tag}.png", array, extent,
            f"{source.label} — {tag}, Miehikkälä", OVERLAY_TITLE, points, lines)
        print("wrote", path.name)


if __name__ == "__main__":
    main()

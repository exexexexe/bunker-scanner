# Bunker Scanner

Processes national LiDAR terrain data for Finland (Sweden to follow) to surface
Cold War / WWII-era bunkers, trenches and military structures hidden under
forest canopy. Planning doc: `bunker-scanner-plan.md`. Working rules:
`bunker-scanner-workflow.md`. Session log: `PROGRESS.md`.

## Status

Phase 0 (proof of concept) complete — gate passed. See `PROGRESS.md` and
`verification/phase-0/GATE-*.png`.

Phase 1 (bulk terrain rendering) complete for Finland — gate passed. Any
bounding box renders on demand via `scripts/render_bbox.py`.

Phase 2 (heuristic detection) complete — gate passed, ~7x enrichment over
control terrain, false-positive rate measured rather than asserted.

Phase 3 (heritage-registry filtering) complete for Finland — gate passed.
Candidates are classified against Museovirasto's register; `--undocumented-only`
keeps just the ones nobody has recorded.

Phase 5 (review UI) complete — `build_review.py` turns any run into a single
self-contained HTML triage page with terrain crops, filters and register status.

The Swedish adapter is written but unverified: it needs Geotorget credentials
for the ordered *Markhöjdmodell Nedladdning* product. Tracked as Phase 1b.

## Setup

```sh
python3 -m venv .venv
.venv/bin/pip install numpy rasterio matplotlib scipy
```

## Run

```sh
# render any box: hillshade, multi-directional hillshade, LRM, sky-view factor
.venv/bin/python scripts/render_bbox.py --centre 27.6658,60.6806 --radius 400
.venv/bin/python scripts/render_bbox.py --bbox 536000,6726600,536800,6727400 --crs native

# Sweden — needs a free Geotorget account; see Credentials below
.venv/bin/python scripts/render_bbox.py --country se --centre 18.05,59.35 --radius 400

# check a source is reachable (and credentials work) before anything else
.venv/bin/python scripts/check_access.py

# validate a render against published coordinates
.venv/bin/python scripts/validate_cluster.py --country fi --target miehikkala
.venv/bin/python scripts/validate_cluster.py --country se --target skanelinjen

# detect candidates, filtered against the national heritage register
.venv/bin/python scripts/detect_bbox.py --country fi --target miehikkala --heritage
.venv/bin/python scripts/detect_bbox.py --bbox 27.54,60.52,27.56,60.53 \
    --heritage --undocumented-only --min-score 0.4

# build the review page for a detection run (one self-contained HTML file)
.venv/bin/python scripts/build_review.py --run miehikkala

# measure the detector against controls
.venv/bin/python scripts/evaluate_detector.py

# Phase 0 gate evidence
.venv/bin/python scripts/phase0_gate.py
```

Renders land in `output/<name>/` with a `report.json` recording the tiles used,
any nodata filled, and the attribution. Finnish tiles cache in `data/dem/`
(~26 MB each); Swedish tiles are read remotely and never downloaded whole.
Both directories are gitignored.

## Credentials

Finland needs none — the Funet/CSC mirror is open. Sweden does:

```sh
cp .env.example .env    # then fill in LANTMATERIET_USER / LANTMATERIET_PASSWORD
.venv/bin/python scripts/check_access.py --country se
```

Lookup order is process environment first, then `BUNKER_SCANNER_ENV_FILE`, then
`.env` beside this README. Nothing overwrites a variable that is already set, so
an explicit `export` always wins. `.env` is gitignored.

Geotorget issues credentials **per ordered product**. Credentials for a
different Lantmäteriet dataset will authenticate and then return `403` on the
elevation tiles — order "Markhöjdmodell Nedladdning" and use the pair issued for
it. `check_access.py` tells the two cases apart.

## Layout

| path | what |
| --- | --- |
| `bunker_scanner/sheets.py` | TM35FIN map-sheet index ↔ EPSG:3067 coordinates |
| `bunker_scanner/sources.py` | per-country sources: CRS, tiles for a box, credentials |
| `bunker_scanner/fetch.py` | cache a tile, or open a remote COG with the right GDAL env |
| `bunker_scanner/window.py` | read/mosaic an arbitrary box; snap to grid, report voids |
| `bunker_scanner/render.py` | hillshade, multi-directional hillshade, LRM, sky-view factor |
| `bunker_scanner/plot.py` | raw images, annotated maps, plain-vs-overlay comparisons |
| `bunker_scanner/reference.py` | per-country registers of published validation geometry |
| `bunker_scanner/detect.py` | beaded-chain candidate detection and scoring |
| `bunker_scanner/heritage.py` | Museovirasto lookup: is this candidate already documented? |
| `bunker_scanner/review.py` | builds the self-contained triage page for a run |
| `data/reference/` | published coordinates used for validation, with their queries |
| `verification/phase-0/` | rendered evidence for the Phase 0 gate |

## Data and attribution

- Elevation: **Korkeusmalli 2 m, © Maanmittauslaitos, CC BY 4.0**, via the
  Funet/CSC mirror. No API key or registration required.
- Elevation (Sweden): **Markhöjdmodell © Lantmäteriet, CC BY 4.0** — free, but
  the download endpoint requires a Geotorget account.
- Validation coordinates: **OpenStreetMap contributors, ODbL**.
- Heritage register (Finland): **Museovirasto, Kulttuuriympäristön
  paikkatietoaineistot**, CC BY 4.0.

Scope is Finland and Sweden only. See the plan doc's guardrails.

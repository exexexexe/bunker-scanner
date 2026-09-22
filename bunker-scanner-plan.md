# Bunker Scanner — Planning Doc

**One-liner:** A tool that processes national LiDAR terrain data for Sweden and Finland to surface undocumented Cold War / WWII-era bunkers, trenches, and military structures hidden under forest canopy.

**Why LiDAR, not satellite photos:** Optical satellite/aerial imagery only shows the treetop canopy — camouflaged or forested structures are invisible in it. Airborne LiDAR pulses pass through gaps in the canopy and hit the ground, so a bare-earth terrain model reveals unnatural bumps, pits, and dead-straight edges (bunker walls, trench lines) that no aerial photo can show. This is an established academic method (used by Finnish researchers — Seitsonen & Ikäheimo on Sápmi military remains; Anttiroiko et al. 2023 on ALS + deep learning for boreal-forest structures under canopy) and is the whole reason this is worth building instead of just reusing an existing satellite-photo abandoned-building tool.

## Goals
- Given a bounding box (or region name) in Sweden or Finland, produce a ranked list of candidate coordinates likely to contain a bunker, trench network, or other concealed military structure.
- Filter out candidates that match already-documented heritage sites, so the output is skewed toward genuinely undocumented finds.
- Make the terrain visualizations themselves inspectable (hillshade/relief images), so candidates can be eyeballed before physically visiting anywhere.

## Non-goals (v1)
- Not attempting to cover Russian territory (Kola Peninsula etc.) — LiDAR coverage doesn't exist publicly there anyway, and it's active/restricted military land.
- Not building a general abandoned-building finder (that's a separate, easier problem solvable with regular satellite imagery — see OSM Overpass approach discussed separately).
- Not doing real-time processing — this is a batch pipeline: pick a region, run it, review results.

## Data sources (both free, open, no API keys needed for bulk download)
- **Sweden** — Lantmäteriet, via Geotorget open data:
  - "Laserdata Skog" — raw classified point clouds (~1–2 pts/m²)
  - "Nationell höjdmodell" — pre-built 1m-resolution ground-classified DTM grid (easier starting point, skip point-cloud processing entirely for v1)
- **Finland** — Maanmittauslaitos (NLS) open data portal:
  - "Laserkeilausaineisto" — raw LiDAR point clouds
  - "Korkeusmalli" — pre-built elevation models (2m and 0.5m), CC 4.0 BY licensed
- **Heritage registries for filtering out known sites:**
  - Sweden: Riksantikvarieämbetet — Fornsök / Kulturmiljöregistret
  - Finland: Museovirasto — muinaisjäännösrekisteri
- **Known-bunker seed data for training/validation:** Finland's Salpa Line has public, documented WWII bunker coordinates — good positive-example source for the detection model.

## Pipeline

### Stage 1 — Acquire
Download DTM/point-cloud tiles for a chosen bounding box from Lantmäteriet or Maanmittauslaitos.

### Stage 2 — Terrain rendering
From the bare-earth DTM, generate the standard archaeological relief visualizations:
- Multi-directional hillshade
- Sky-View Factor (SVF)
- Local Relief Model (LRM)
These are specifically tuned to make subtle earthworks pop out of otherwise flat/natural terrain.

### Stage 3 — Candidate detection
Two approaches, can run both and compare:
- **Heuristic pass (cheap, ship first):** OpenCV edge/line detection tuned to flag long, unnaturally straight segments or sharp rectilinear outlines. Natural drainage curves and follows slope; bunkers and trenches don't.
- **ML pass (better recall, more setup):** small CNN or YOLO-style detector trained on labeled LRM/hillshade patches. Bootstrap positive examples from Salpa Line coordinates; negative examples from random forest tiles with no known structures.

### Stage 4 — Filter against known sites
Cross-reference candidate coordinates against the Fornsök and Museovirasto registries. Anything matching a listed site gets dropped or flagged "known." What's left is the genuinely-undocumented shortlist.

### Stage 5 — Review UI
A simple map/gallery view (probably a web app, could reuse patterns from other projects) showing each candidate as a pin with its hillshade/LRM crop, sorted by confidence score, so candidates can be visually triaged before deciding whether any are worth a field visit.

## Suggested tech stack
- Point cloud / raster processing: `laspy` or PDAL, `rasterio`/GDAL
- Terrain derivatives: `whitebox` or `richdem` for hillshade/SVF/LRM
- Detection: OpenCV for the heuristic pass; PyTorch + `ultralytics` (YOLO) if going the ML route
- Review UI: lightweight web app (map + image gallery), stack TBD — could be a Railway-hosted app consistent with other projects, or a local tool if this stays a personal hobby project rather than something shipped

## Phased roadmap
- **Phase 0 — Prove the concept.** Pick one small test region with a *known* documented bunker (e.g. somewhere on the Salpa Line). Download the DTM, generate a hillshade, and confirm the known structure is visible. This validates the whole approach before any detection code is written.
- **Phase 1 — Bulk terrain rendering.** Script the download + hillshade/SVF/LRM generation for an arbitrary bounding box, so any region of interest can be rendered on demand.
- **Phase 2 — Heuristic detection.** Ship the OpenCV straight-line/rectilinear detector over rendered tiles. Manually review output on a few regions to gauge false-positive rate.
- **Phase 3 — Heritage-registry filtering.** Wire in Fornsök/Museovirasto lookups to suppress known sites from results.
- **Phase 4 — ML detector (optional, only if Phase 2's false-positive rate is too high to be useful).** Train on Salpa Line positives.
- **Phase 5 — Review UI.** Map-based candidate browser.

## Open questions / decisions still needed
- Which region to use as the Phase 0 test case (needs a documented bunker with known coordinates for validation).
- Whether this stays a personal/local tool or becomes something hosted (affects Stage 5 stack choice).
- How aggressive to make the heuristic thresholds — tighter thresholds miss things, looser ones flood the shortlist with natural terrain noise (old riverbeds, esker ridges, windthrow).

## Risks / cautions
- Legal: entirely fine for Sweden/Finland (open data, decommissioned/historical sites); anything found should still be treated with normal trespassing/private-land caution before a physical visit.
- Do not extend this toward Russian territory — no legal public LiDAR coverage exists there, and it's a real safety/legal risk zone, not just a data problem.

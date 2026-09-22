# Bunker Scanner — Progress

Append-only. One entry per session, per the protocol in `bunker-scanner-workflow.md`.

---

## Session 2026-09-21 — Phase 0: Proof of concept

### Done
- Derived and implemented the TM35FIN map-sheet index MML uses for its raster
  products (`bunker_scanner/sheets.py`) — coordinate → 6 × 6 km tile name and back.
- Wrote a tile downloader against the Funet/CSC mirror of MML open data
  (`bunker_scanner/fetch.py`) — no API key, no registration.
- Wrote a bounding-box reader that downloads and mosaics whatever tiles a box
  spans and fills nodata voids (`bunker_scanner/window.py`).
- Wrote the terrain renderers (`bunker_scanner/render.py`): Lambertian hillshade
  with azimuth/altitude/z-factor, multi-directional hillshade, Local Relief Model
  (Gaussian high-pass), percentile contrast stretch.
- `scripts/phase0.py` — parameter sweep around a coordinate.
- `scripts/validate_osm_cluster.py` — renders a cluster of documented bunkers with
  each published coordinate marked, plus per-bunker 120 m crops.
- `scripts/phase0_gate.py` — the gate figure: plain render beside the same render
  with published Salpa Line geometry overlaid.

### Test target and coordinate source
Two passes, because the first target turned out to be weak evidence:

1. **First attempt — Salpa Line Museum, Miehikkälä**, 60.65072 N, 27.69277 E
   (Wikidata Q7405733, P625). Renders show heavy anthropogenic ground — a 120 m
   cut pit, terraced lines, a dense cluster of small mounds — but this is a
   *street address*, so "a structure is visible near the point" proves little.
   Kept as `verification/phase-0/miehikkala-*`.

2. **Actual gate target — the mapped Salpa Line bunker chain at Miehikkälä**,
   centred 60.6806 N, 27.6658 E. Source: OpenStreetMap nodes tagged
   `military=bunker`, each individually named with its wartime designation
   (Korsu 329, 330, 437, 333/332, Pallokorsu 612/613/615/616, Mehikkala
   Pallokorsu C611 …), plus ways tagged `military=trench` and
   `barrier=tank_trap` — two of the latter named "Salpalinja". Queries and raw
   responses committed to `data/reference/` so the check is reproducible.
   101 bunker nodes returned for the Virolahti–Miehikkälä box; the densest
   cluster holds 11 inside 400 m.

### Data access — what it actually took
- **No registration, no key, no payment.** MML's own `avoin-paikkatieto` endpoint
  returns 401 without an API key, but the Funet/CSC mirror
  (`nic.funet.fi/index/geodata/mml/dem2m/2008_latest/`) serves the identical
  Korkeusmalli 2 m GeoTIFFs over plain HTTPS. Same CC BY 4.0 licence.
- **CRS needed no reprojection.** Tiles are already EPSG:3067 (TM35FIN); only the
  WGS84 target coordinates get projected in, via `rasterio.warp.transform`.
- **Tile indexing is not documented on the mirror** — it had to be reverse-engineered.
  Sheets are named `<letter><digit>` at level 1 (192 × 96 km), then three digits
  and a letter. Every subdivision is column-major (1 = SW, 2 = NW, 3 = SE, 4 = NE;
  A–H = four columns × two rows). Sheet L4's south-west corner is
  (308000, 6666000). Verified by reading the geotransforms of eight known tiles
  and reproducing all eight from the formula.
- Tiles are 3000 × 3000 float32, 2 m pixels, 26 MB each, nodata −9999. The gate
  window needed two tiles (L5214C + L5214E); the first sweep used L5213F.
- Verified before rendering: CRS EPSG:3067, 2.0 m resolution, elevations
  9.4–68.8 m, zero nodata pixels in every tile used.

### Verified — what is visible
Gate figures: `verification/phase-0/GATE-hillshade-az315-alt30-z3.png` and
`GATE-lrm-k15m.png` (840 m window, left panel unannotated, right panel with the
published geometry drawn on).

- **A continuous beaded line of discrete blocks** runs diagonally across the whole
  840 m frame — individual lumps roughly 2–4 m across, spaced in a regular row,
  in straight runs joined by sharp angular turns. It crosses slope and drainage
  instead of following them. Where OSM has mapped trench and tank-trap ways, the
  yellow/cyan overlay lands directly on it; the feature then continues for
  several hundred metres beyond where the register stops. This is the Salpa Line
  anti-tank stone barrier and its connected trench run.
- **Individual bunkers read as raised blocky masses with a cut beside them.**
  Korsu 330 (120 m crop): a bright ~10 × 10 m block sitting on the barrier line,
  with an adjacent dark rectangular cut — concrete mass plus entrance trench.
  Korsu 437, 329 and 333/332 show the same signature.
- Quantified against the same window for honesty: local relief range within 16 m
  of each published bunker point, versus 4000 random points in the frame
  (background median 0.74 m, 90th pct 2.39 m):
  Korsu 437 4.08 m (98th pct) · Korsu 330 3.55 m (97th) · Korsu 329 3.29 m (96th)
  · Korsu 333/332 3.20 m (96th) · Mehikkala 2.78 m (93rd) · Pallokorsu 612 2.39 m
  (90th) · Pallokorsu 613 1.46 m (78th) · Pallokorsu 615 1.45 m (77th)
  · Mehikkala Pallokorsu C611 1.31 m (74th) · **Pallokorsu 616 0.50 m (32nd)**.
- The one miss is informative and is recorded as a finding, not smoothed over:
  **ball bunkers ("pallokorsu" — a small steel cupola set nearly flush with the
  ground) do not resolve at 2 m.** Pallokorsu 616's 120 m crop is genuinely flat
  ground (2.2 m of relief across the whole crop). Every clear hit is a concrete
  *korsu*. Concrete bunkers are visible at 2 m; cupolas are not.
- Parameter sweep, for the record: plain hillshade at azimuth 315 / altitude 45
  is too flat on this low-relief terrain to show anything. Altitude 25–30 with
  z-factor 3 is what makes the barrier line pop. Multi-directional hillshade at
  altitude 25 is comparable and less direction-biased. LRM is the strongest of
  the three; kernel 15 m is best for bunker-scale objects, 20–30 m for the
  barrier line, 40 m starts pulling in landform-scale noise.

### Decisions made (no need to revisit unless something breaks)
- **Funet/CSC mirror over MML's own API** — identical open data, no API key, so
  nothing in the pipeline needs a credential. If the mirror ever lags a data
  release, switch to `avoin-paikkatieto` with a key at that point.
- **Pre-built Korkeusmalli 2 m, not point clouds** — as the kickoff directed.
  Confirmed sufficient for concrete bunkers; revisit for 0.5 m or raw point
  clouds only if Phase 2 needs to catch cupolas.
- **Sheet index reimplemented in-repo rather than scraped** — the mirror exposes
  no index file, and the formula is exact and now test-verified.
- **LRM via Gaussian high-pass** (scipy), not a whitebox/richdem dependency —
  one fewer binary dependency, and the result is the standard LRM definition.
- **Hillshade computed in numpy**, not via `gdaldem` — GDAL is not installed as a
  CLI here and rasterio's bundled build has no binaries.
- **OpenStreetMap as the validation register, not Museovirasto.** `kartta.nba.fi`
  (the Museovirasto WFS) does not respond from this machine, and OSM has the
  Salpa Line mapped bunker-by-bunker with wartime designations. Museovirasto is
  still the right source for Phase 3's "is this already known" filter; OSM was
  used here only to get published coordinates to validate against.
- **Verification PNGs committed (~12 MB), DEM tiles gitignored (~102 MB).** The
  images are the evidence the workflow asks for; the tiles are re-downloadable.
- Layout: `bunker_scanner/` library, `scripts/` entry points, `data/dem/`
  (ignored), `data/reference/` (committed), `verification/<phase>/`.

### Escalations
None. Nothing is blocked.

### Gate
**PASSED.** The documented bunkers and the barrier line connecting them are
plainly distinguishable from surrounding natural terrain, at named,
independently published coordinates, in both hillshade and LRM. Qualified in one
respect, stated above: concrete bunkers resolve at 2 m, steel ball-cupolas do not.

### Next up (Phase 1 — bulk terrain rendering)
- Generalise to an arbitrary bounding box: the mosaic path already works
  (`window.read_bbox` handled a two-tile box), but it has only been exercised on
  small windows — test it across a level-1 sheet boundary and on a box that hits
  a genuine nodata void.
- Add Sweden. Lantmäteriet's "Nationell höjdmodell" is 1 m and in EPSG:3006
  (SWEREF99 TM), with a different sheet scheme — expect a second `sheets`-style
  module rather than a parameterisation of the Finnish one. Check first whether
  Lantmäteriet has an open mirror equivalent to Funet, or whether Geotorget
  registration is unavoidable; if it is, that is an escalation under the
  workflow's data-access rule.
- Add Sky-View Factor to `render.py` — the plan names it, Phase 0 skipped it, and
  it is the visualisation least sensitive to illumination direction.
- Consolidate the three scripts: `phase0.py`, `validate_osm_cluster.py` and
  `phase0_gate.py` each carry their own copy of the plot/marker code.
- Carry the Phase 0 numbers forward as the Phase 2 baseline: a true positive here
  is roughly 3–4 m of local relief within 16 m against a 0.74 m background
  median, and the barrier line is a far stronger signal than any single bunker —
  the heuristic pass should probably hunt the lines first and read bunkers off
  them, rather than hunting isolated rectangles.

---

## Session 2026-09-22 — Phase 1: Bulk terrain rendering

### Done
- `bunker_scanner/sources.py` — per-country source abstraction. A source knows its
  CRS, pixel size, attribution and credential requirements, and lists the tiles
  covering a box in its own CRS. Two implementations: Finland (MML via the
  Funet/CSC mirror, download-and-cache) and Sweden (Lantmäteriet STAC, read the
  remote COG in place).
- `bunker_scanner/window.py` rewritten around sources: snaps the box to the pixel
  grid, mosaics however many tiles it spans, fills and *reports* nodata voids, and
  raises `NoCoverage` rather than returning a blank raster.
- `bunker_scanner/fetch.py` reduced to two jobs: cache a tile, or open one over
  `/vsicurl` with the right GDAL environment and credentials.
- `bunker_scanner/render.py` — added **Sky-View Factor** (Zakšek et al. 2011,
  16 directions, configurable radius). It is now the best of the three: the
  barrier line reads as a crisp dark chain against near-white flat ground, with
  no illumination direction to hide behind. ~0.05 s on a 400 × 400 window.
- `bunker_scanner/plot.py` and `bunker_scanner/reference.py` — the plotting and
  register-loading code that the three Phase 0 scripts each carried their own
  copy of, now in one place.
- `scripts/render_bbox.py` — the Phase 1 deliverable. Arbitrary box by
  `--bbox` or `--centre/--radius`, in lon/lat or native CRS, `--country fi|se`,
  writes hillshade / multi-directional hillshade / LRM / SVF plus a
  `report.json` and optionally the DEM crop as GeoTIFF.
- `scripts/phase0.py` deleted — `render_bbox.py` does strictly more. The Phase 0
  gate and cluster scripts were ported onto the new modules and still reproduce
  the Phase 0 numbers exactly.

### Verified
- **Bug found and fixed: the tile enumeration was dropping tiles.** Stepping by
  one tile width from the *box's* south-west corner skips interior tiles whenever
  the box is not tile-aligned. A 10 × 10 km test box came back with a clean
  rectangular hole of 3 000 000 filled pixels (12% of the frame) in the middle of
  the mosaic — and, because the hole was median-filled, it rendered as plausible
  flat ground rather than failing. Fixed by stepping from the corner of the tile
  containing the box's south-west point. Same box now returns 6 tiles, zero
  voids, and an elevation range of −0.1 to 46.7 m instead of −0.1 to 35.9 m —
  real terrain had been missing. `tests/test_coverage.py` covers six box shapes
  and asserts every point of the box falls inside some returned tile.
- **Correction to the Phase 0 write-up.** The dark strip along the right edge of
  the Phase 0 gate images was dismissed there as a plotting artefact. It was not
  — it was a one-pixel nodata seam from requesting a box whose edges did not fall
  on the pixel grid. `snap_to_grid` in `window.py` fixes it; the regenerated gate
  images have 0 void pixels where they previously had 400.
- Sheet seams: a box crossing the L4/L5 level-1 boundary (2 tiles) and one on the
  four-way L4/L5/M4/M5 corner (4 tiles) both mosaic continuously — inspected, no
  seam line in the render.
- No-coverage: an open-water box in the Bothnian Sea exits cleanly naming the
  tile that 404ed, instead of rendering an empty frame.
- Both test suites pass: `tests/test_sheets.py` (11 sheets), `tests/test_coverage.py`
  (6 boxes).

### Decisions made (no need to revisit unless something breaks)
- **Sweden streams, Finland caches.** Finnish tiles are 26 MB, so caching is
  cheap and repeat runs are free. Swedish tiles are 10 000 × 10 000 at 1 m —
  roughly 400 MB — but they are COGs, so a window read over `/vsicurl` fetches
  only the blocks it touches. Worth the asymmetry.
- **Voids are filled with the window median, and the mask is exported.** Filling
  keeps a partially covered box renderable; the mask matters because the fill
  boundary is itself a hard straight edge and would be a perfect false positive
  for Phase 2's straight-line detector. `render_bbox.py` writes `void-mask.png`
  whenever any pixel was filled.
- **Boxes are snapped outward to whole pixels** before reading, rather than
  resampling to the exact box. Avoids the seam above and keeps output on the
  source grid.
- **`output/` is gitignored.** Bulk rendering would otherwise fill a notes vault
  with binaries. `verification/` stays committed — it is the phase-gate evidence.
- Swedish credentials come from `LANTMATERIET_USER` / `LANTMATERIET_PASSWORD`;
  nothing is stored in the repo.

### Escalations (needs the maintainer's input before proceeding past this point)
- **Sweden requires a free Lantmäteriet account, so Phase 1's gate is only half
  met.** The STAC catalogue at `api.lantmateriet.se/stac-hojd/v1` is fully open
  and item search works unauthenticated — the code already resolves the right
  COGs for a box. But the tiles themselves, on `dl1.lantmateriet.se`, return
  `401` with `WWW-Authenticate: Basic`. There is no open mirror equivalent to
  Finland's Funet; I looked. The data is free and CC BY 4.0 — this is
  registration, not payment — but an account can only be created by a person.
  Options, with my leaning first:
  1. **Register at geotorget.lantmateriet.se and set the two env vars.** The
     adapter is written and waiting. Likely worth it beyond just coverage: the
     Swedish model is 1 m, and 1 m may well resolve the ball-cupolas that 2 m
     missed in Phase 0.
  2. Declare Phase 1 Finland-only, merge it, and make Sweden its own phase.
  Per the workflow's phase-gate rule this branch is **not merged to master** — a
  half-passed gate is an escalation, not something to patch later. Either answer
  unblocks the merge immediately.

### Next up
- On answer to the escalation: either wire in the credentials and verify a
  Swedish render end-to-end against a known Swedish site, or merge Finland-only.
- Phase 2 (heuristic detection) should hunt the *lines* first. The barrier line
  is a far stronger and more continuous signal than any single bunker, and in
  this terrain the bunkers sit on it — finding the line and reading structures
  off it is a better shape than scanning for isolated rectangles.
- SVF should probably be the detector's primary input rather than LRM, on the
  strength of the gate images.
- Phase 2 must consume `void-mask.png` and suppress candidates on fill edges.

### Continued, same session — Sweden made ready while the account is being created

Everything below is unblocked work done while waiting on the Geotorget
registration. The escalation above still stands; nothing here resolves it.

#### Done
- **Swedish validation targets found and cached.** Same method as Finland:
  OpenStreetMap structures with published per-point coordinates, query and raw
  response committed to `data/reference/`. Two clusters, both confirmed to have
  1 m Lantmäteriet DTM coverage by a STAC query:
  - `skanelinjen` — 6 coastal bunkers of the Per Albin line strung along ~1 km of
    the Skåne south coast (55.3600 N, 13.2170 E). Tile 613_38, scanned 2025-02-14.
  - `backastrand` — 5 named coastal-artillery positions in Blekinge, incl.
    Batteri Ellenabben and Batteri Hytterna (56.0994 N, 15.5500 E). Tile 621_53,
    scanned 2019-04-04.
- `bunker_scanner/reference.py` generalised from "the Salpa Line files" to a
  register per country: CRS, a points file, an optional lines file, and named
  targets. Finland and Sweden both registered.
- `scripts/validate_osm_cluster.py` → `scripts/validate_cluster.py`, now
  `--country`/`--target` driven and usable for either country. Finland
  reproduces its Phase 0 numbers exactly through the generalised path.
- `scripts/check_access.py` — preflight. Resolves a real tile for each source and
  reads its header, so one command says whether a source is actually usable.
  Finland passes end to end; Sweden passes tile indexing and stops at the
  credential wall with the registration URL.
- **Retry with backoff on the Lantmäteriet STAC** (`fetch_json` in `sources.py`).
  Resolving tiles for a dozen boxes in a row earns a 429 quickly; a bulk pass has
  to wait and retry rather than fail. Honours `Retry-After`, exponential to 60 s.

#### Decisions made
- **Denmark is excluded explicitly, not incidentally.** The first Swedish search
  box reached across the Øresund and the Baltic, and the two densest "Swedish"
  clusters it found were Copenhagen and Bornholm. The Lantmäteriet STAC returns
  no tiles for either, so a coverage query doubles as a scope filter — that check
  is what `check_access.py` and the target selection now rest on. Worth
  remembering for Phase 2: dense bunker clusters near a border are as likely to
  be another country's as a find.
- Swedish targets are coastal rather than forested. They validate the Swedish
  *pipeline*; the under-canopy claim was already settled in Phase 0 on Finnish
  forest, and re-proving it is not what this step is for.

#### Verified
- Full chain for Sweden up to the credential wall: target lon/lat → EPSG:3006 →
  STAC item search → correct tile URL (`m613_38.tif`, `m621_53.tif`), 1 tile per
  target box. Only the authenticated GET is untested.
- Finland regression after the refactor: gate figures and all 11 cluster
  amplitudes byte-for-byte the same as Phase 0.
- Both test suites still pass.

#### The moment credentials exist
```sh
export LANTMATERIET_USER=... LANTMATERIET_PASSWORD=...
.venv/bin/python scripts/check_access.py --country se
.venv/bin/python scripts/validate_cluster.py --country se --target skanelinjen --crops
```
One known risk, untestable until then: the Swedish COGs declare EPSG:5845
(SWEREF99 TM + RH2000, a compound CRS) while the code works in EPSG:3006. The
horizontal axes are identical so the window maths is right, but rasterio's merge
may object to a compound CRS. If it does, the fix is to override the CRS on open
rather than to reproject.

### Escalation resolved — 2026-09-22

The maintainer ordered **Markhöjdmodell Nedladdning** on Geotorget; the credentials are
quoted at roughly three working days, so expect them around **2026-09-25**.
Decision: **Phase 1 ships Finland-only and is merged now.** Sweden becomes its
own phase rather than holding the gate open for three days.

Diagnosis behind the wait, for the record: the `LANTMATERIET_USER` /
`LANTMATERIET_PASSWORD` already on the machine authenticate against Lantmäteriet
but return `403` on the elevation tiles. Geotorget issues credentials **per
ordered product**, and the existing pair is a portal login (it is an email
address) provisioned for a different dataset. A new pair will arrive with the
order; it goes in `Bunker-Scanner/.env`.

#### Phase 1 gate — PASSED for Finland
Any bounding box in Finland renders on demand: `scripts/render_bbox.py` takes
lon/lat or native coordinates, mosaics however many tiles the box spans across
sheet boundaries, and writes hillshade, multi-directional hillshade, LRM and SVF
plus a `report.json`. Verified on single-tile, two-tile, four-way-sheet-corner,
partial-coverage and no-coverage boxes; both test suites pass.

The Swedish adapter is written and everything up to the authenticated GET is
verified — target → EPSG:3006 → STAC item search → correct tile URL. It is
shipped unverified and explicitly **not** counted towards this gate.

### Next up (Phase 2 — heuristic detection, now open)
- Hunt **lines first**. The anti-tank barrier is a far stronger and more
  continuous signal than any single bunker, and in Phase 0's terrain the bunkers
  sit on it. Find the line, then read structures off it — a better shape than
  scanning for isolated rectangles.
- Use **SVF as the primary input**, on the strength of the gate images: the
  barrier reads as a crisp dark chain with no illumination direction to hide
  behind.
- Consume `void-mask.png` and suppress candidates on fill edges — the fill
  boundary is a hard straight edge and a perfect false positive.
- Baseline to beat, from Phase 0: a true positive is ~3-4 m of local relief
  within 16 m against a 0.74 m background median; ball-cupolas at ~1.3 m are at
  the noise floor and 2 m data will not catch them.
- Report false-positive/true-positive counts against a manually reviewed sample,
  per the workflow's audit rule — not "the detector found N candidates".

### Phase 1b (Sweden) — blocked until credentials arrive, ~2026-09-25
- `scripts/check_access.py --country se` must go green first.
- Then `scripts/validate_cluster.py --country se --target skanelinjen --crops`
  and the same for `backastrand`.
- Known risk: the Swedish COGs declare EPSG:5845 (compound, SWEREF99 TM +
  RH2000) while the code works in EPSG:3006. Horizontal axes are identical so
  the window maths is right, but rasterio's merge may object to a compound CRS.
  Fix by overriding the CRS on open, not by reprojecting.
- Worth checking at 1 m: whether ball-cupolas resolve where 2 m missed them.

---

## Session 2026-09-22 — Phase 2: Heuristic detection

### Done
- `bunker_scanner/detect.py` — the detector. Finds compact relief anomalies
  ("beads") in both polarities, links them into chains that keep a heading, and
  scores each chain.
- `scripts/detect_bbox.py` — run it over any box; writes a numbered annotated
  render, `candidates.geojson` (WGS84) and `candidates.csv`.
- `scripts/evaluate_detector.py` — the gate. Matches candidates against published
  geometry in a labelled window and measures candidate density per km² against
  three control windows with no known fortifications.
- Evidence in `verification/phase-2/`, including `manual-review.md` — a
  candidate-by-candidate verdict, written from the images.

### The central finding
**A straight-line detector is the wrong tool for this landscape, and my first
version proved it by ranking a field drainage ditch first.** Finnish farmland and
managed forest are full of dead-straight anthropogenic lines: drainage, plough
furrows, parcel edges, roads. Straightness is not evidence — over 100 m of
farmland it is evidence of a *machine*. A defensive line bends with the terrain
it defends.

What actually discriminates, measured on the labelled window:
- **Corridor roughness** — relief variability in a ring *around* the chain,
  excluding the chain itself. True positives median 0.216, drainage 0.088. Field
  drainage sits in smooth ploughed ground; a defensive line sits in broken
  terrain among boulders, cuts and spoil. This was the strongest single signal.
- **Beadedness** — the share of between-bead ground that is *ordinary*. A ditch
  is a continuous groove and scores low (0.55 median); a row of stones has
  normal ground between the blocks (0.69). Real but weak on its own, and it
  overlaps: kept as a 0.20 weight, not a filter.
- **Too-straight-and-too-smooth** — straightness ≥ 0.985 *and* roughness < 0.16
  together are near-diagnostic of drainage. Applied as a ×0.35 demotion rather
  than a drop, so demoted candidates stay reviewable.
- **Parallel companions** was tested and *rejected* — no separation at all
  (median 1.0 for both classes). Recorded so it is not tried again.

### Verified
Manual review, `verification/phase-2/manual-review.md`:
- Labelled window (Miehikkälä, 0.71 km², 21 candidates): of the 15 not demoted,
  **13 are on the fortification system, 2 ambiguous, 0 clear false positives**.
  All 6 demoted candidates are field drainage, 56-341 m from any mapped feature.
- Candidate density per km² at score ≥ 0.5: **labelled 18.4, controls 1.6, 2.7,
  3.0** — roughly a 7× enrichment over background terrain. At ≥ 0.6: labelled
  8.5, controls 0.0-1.2.
- Only 5 of 21 candidates match published geometry within 20 m. That is the
  *register* being incomplete, not the detector being wrong: eight of the
  thirteen genuine chains sit on unmapped barrier. Worth carrying into Phase 3 —
  these are exactly the candidates a heritage filter should not suppress.

### Honest limits
- **Forest false positives are a different and unsolved class.** In farmland the
  culprit is straight drainage, which the demotion rule catches. In forest it is
  *curving* ditches around drained peatland parcels, mire edges and stream banks
  — genuinely linear anomalies in genuinely rough ground, so neither roughness
  nor straightness separates them. This is the main remaining weakness.
- At 1.6-3.0 candidates/km² above 0.5, a 1 000 km² sweep would yield roughly
  2 000 candidates to review. This is a useful shortlisting tool over a chosen
  region; it is not yet a national survey.
- The score is a ranking indicator, not a probability, and the GeoJSON says so
  in a `note` field.
- Rank 19 in the labelled window may be a genuine feature wrongly demoted; it is
  flagged in the review table rather than quietly counted as a success.

### Decisions made (no need to revisit unless something breaks)
- **The detector does not use OpenCV**, though the plan named it and it is
  installed. Canny + probabilistic Hough was tried during exploration and is the
  wrong shape for this problem: it finds continuous straight edges, which here
  are overwhelmingly drainage. Blob extraction plus graph linking over the LRM
  (scipy/numpy) directly expresses the beaded signature that matters. OpenCV can
  be dropped from the dependencies.
- **Both polarities, chains kept polarity-pure.** Stone barriers and parapets are
  raised; trenches, ditches and entrance cuts are cuts. Mixing them would let
  noise bridge unrelated features.
- **Chains grow in both directions from a seed.** Growing one way truncated every
  chain at its seed and fragmented one 800 m barrier into eight ~70 m stubs.
- Parameters, tuned from measurements rather than guessed: `min_relief` 0.35 m,
  `max_gap` 20 m (bead spacing on the mapped line measured at 7.4 m median,
  15.8 m at the 90th percentile), `min_beads` 6, `min_length` 60 m.
- **Demote, never drop.** Everything stays in the output with its reasons
  attached, so a wrong rule costs ranking rather than recall.

### Escalations
None.

### Phase 2 gate — PASSED
The detector ships, runs over an arbitrary box, and its false-positive rate has
been measured against manually reviewed samples rather than asserted: 13/15
genuine in the labelled window, ~7× enrichment over three control windows, with
the residual forest false-positive class characterised rather than hidden.

### Next up
- **Phase 3 — heritage-registry filtering.** Museovirasto's `kartta.nba.fi` WFS
  did not respond from this machine in Phase 0; retry, and fall back to the
  GeoPackage published on avoindata.fi. The Phase 2 result sharpens the point of
  this phase: with only 5 of 21 genuine candidates present in OpenStreetMap, the
  filter's job is as much "what is *not* recorded" as "what is".
- **Phase 2b, if Phase 3's output is still too noisy** — the forest ditch class
  needs a discriminator. Worth trying: ditches connect into drainage *networks*
  with junctions and consistent downslope flow; a barrier does not. A flow-
  direction check against the DEM may separate them where geometry cannot.
- Phase 1b (Sweden) still pending credentials, ~2026-09-25.

---

## Session 2026-09-22 — Phase 3: Heritage-registry filtering

### Done
- `bunker_scanner/heritage.py` — queries Museovirasto's Kulttuuriympäristön
  paikkatietoaineistot WFS for a box, caches the response, indexes it with an
  STRtree, and classifies a candidate as `known_military`, `known_other` or
  `undocumented`.
- `scripts/detect_bbox.py` gained `--heritage`, `--heritage-distance` and
  `--undocumented-only`; candidates are colour-coded by register verdict and the
  verdict travels into `candidates.geojson` / `.csv`.
- Evidence in `verification/phase-3/`.

### Two findings worth keeping
- **The Phase 0 failure was a dead hostname, not a network problem.**
  `kartta.nba.fi`, which the plan and my Phase 0 notes both name, is now
  `NXDOMAIN`. The live service is `geoserver.museovirasto.fi`. I recorded it in
  Phase 0 as "does not respond from this machine", which was the wrong
  diagnosis — it does not exist for anyone.
- **Salpa Line works are not in the ancient-monuments layer.** They sit in
  `muu_kulttuuriperintokohde_*` typed `puolustusvarustukset` (defensive works),
  subtype `taistelukaivannot` (battle trenches). A filter consulting only
  `muinaisjaannos_*` would report every documented WWII fortification in Finland
  as an undocumented find — the exact failure this phase exists to prevent.

### Verified
| window | candidates | known_military | undocumented |
| --- | ---: | ---: | ---: |
| Miehikkälä (Salpa Line) | 21 | 19 | 2 |
| Virolahti C10 (Salpa Line, 15 km away) | 14 | 13 | 1 |
| control forest-keski | 41 | 0 | 41 |
| control farmland-pohjanmaa | 32 | 0 | 32 |
| control forest-hame | 19 | 0 | 19 |

The filter suppresses ~90% on documented ground and **nothing** on the three
controls. Both directions matter: a filter that suppressed nothing would be
useless, and one that suppressed everything would be worse than useless.
Checking a second Salpa Line segment 15 km from the museum confirmed the
register's coverage is not just dense around the museum — 52 registered sites
near that box.

### Honest limits
- **`known_military` means "inside an area somebody has surveyed", not "this
  exact feature is recorded".** Much of the register is broad area polygons
  covering a whole fortification zone, so at Miehikkälä even the drainage false
  positives inside the "Laajanpohja" polygon come back as known. Right behaviour
  for the goal, wrong thing to call per-feature identification.
- The filter only removes noise where things are already recorded. Over
  unsurveyed terrain it passes everything, which is precisely what the controls
  show. Its contribution is negative evidence.
- It does nothing about the Phase 2 forest-ditch false positives — those are not
  in any register either.

### Decisions made
- **Both registers queried, not just ancient monuments** — see above.
- **50 m default match distance**, configurable. Chosen because register
  geometry is a mix of points and coarse polygons; tighter would miss
  point-recorded sites, looser would swallow neighbouring terrain.
- **Classify and tag by default, suppress only on request**
  (`--undocumented-only`). The plan says "dropped or flagged"; flagging keeps the
  register's own gaps visible, which is itself information — eight of Phase 2's
  thirteen genuine chains were on barrier that OpenStreetMap does not map.
- **Responses cached per box** under `data/heritage/` (gitignored) so evaluation
  runs do not hammer a public service.
- **Sweden's Fornsök is deliberately not wired up.** There are no Swedish
  candidates to filter until Phase 1b delivers Swedish terrain, so it would be
  untestable code. `Register.for_box` raises `NotImplementedError` with a pointer
  rather than pretending to support it.

### Escalations
None.

### Phase 3 gate — PASSED (Finland)
Known sites are correctly identified and can be suppressed; unknown terrain is
correctly left alone; verified in both directions across five windows.

### Next up
- **Phase 4 is optional by the plan** — an ML detector, only if Phase 2's
  false-positive rate proves too high to be useful. Current honest read: the
  farmland case is solved, the forest-ditch case is not. Before reaching for a
  CNN, try the cheaper idea recorded in Phase 2: ditches form drainage
  *networks* with junctions and consistent downslope flow, and a flow-direction
  check against the DEM may separate them where geometry cannot.
- **Phase 5 — review UI.** The pipeline now emits ranked, register-filtered
  GeoJSON, which is exactly the input a map/gallery browser needs.
- Phase 1b (Sweden) still pending credentials, ~2026-09-25. When it lands, Phase
  3 will need Fornsök wired up to match.

---

## Session 2026-09-22 — Phase 5: Review UI

### Done
- `bunker_scanner/review.py` + `bunker_scanner/review_template.html` +
  `scripts/build_review.py` — turn any detection run into **one self-contained
  HTML file**: terrain crops as data URIs, candidates as inline JSON, no external
  assets. Opens from disk, works offline, and can be published unchanged.
- The page: summary tiles, the window's sky-view render with clickable candidate
  tracks drawn over it, filters (undocumented / known / not-demoted, minimum
  score), and a card per candidate showing relief, sky-view and hillshade crops
  side by side with its metrics, register verdict and copyable coordinates.
- `detect_bbox.py` now records the window (bbox, CRS, tiles, resolution,
  attribution) inside `candidates.geojson`, so a run is self-describing and the
  review page can rebuild its own terrain.
- A populated instance published for the Miehikkälä run:
  https://claude.ai/artifact/DsVUnAmaX7TyHTnugwaHDd

### Decision on the plan's open question
The plan asked whether this stays a local tool or becomes hosted, noting it
affects the Stage 5 stack. **Resolved by making the question moot**: the output
is a single file with no server, no build step and no external requests, so the
same artefact works opened from disk *and* published to a URL. No Railway app,
no framework. If a hosted browser over many runs is ever wanted, that is an
additive step, not a rewrite.

### Other decisions
- **No slippy map.** A published page cannot load third-party map tiles, and for
  judging earthworks the sky-view render of the window is better material than a
  road map anyway. Candidate tracks are drawn in percentage space over the
  render itself, which keeps the page self-contained and on-subject.
- **Three crops per candidate, not one.** Relief, sky-view and hillshade disagree
  usefully — a feature that only appears in one of them is worth a second look,
  and Phase 0 showed each has a different blind spot.
- Crops are 160 m across, at the source resolution, rendered with
  `image-rendering: pixelated` so nothing is smoothed into looking realer than
  it is.
- **Known-site cards carry the Phase 3 caveat inline**, not just in the docs:
  "already-surveyed ground, not that this exact feature is recorded".
- The page opens with a standing caveat that these are candidates, not finds,
  with the trespass note from the plan's risk section.

### Verified
- Built for three runs: Miehikkälä (21 candidates, 0.95 MB), Virolahti C10 (14,
  0.6 MB), control forest-keski (41, 2.5 MB).
- Checked the generated file structurally: no template placeholders left, all 21
  candidates present with crops, every marker path inside the 0–100% overview
  space, every CSS custom property declared on bare `:root` so both themes
  resolve.
- **Size limit worth knowing**: ~60 KB per candidate, so ~250 candidates is the
  practical ceiling for one page. A bulk regional run will need paging or
  smaller crops.
- A stale run from before the window block produced a `KeyError`; the builder now
  fails with an instruction to re-run the detection instead.

### Escalations
None.

### Phase 5 gate — PASSED
Candidates are reviewable by eye, ranked, filterable, with the terrain evidence
and the register verdict attached to each.

### Where the project stands
Phases 0, 1 (Finland), 2, 3 (Finland) and 5 are done and merged. The pipeline
runs end to end: give it a bounding box in Finland and it returns a ranked,
register-filtered, visually reviewable shortlist.

### Next up
- **Phase 1b (Sweden)** — credentials expected ~2026-09-25. Then Fornsök needs
  wiring into `heritage.py` to match Finland.
- **Phase 4 (ML) remains optional and not yet justified.** The honest blocker is
  the forest-ditch false-positive class from Phase 2. Try the cheap idea first:
  ditches form drainage *networks* with junctions and consistent downslope flow;
  a flow-direction check against the DEM may separate them where geometry cannot.
- A real regional run is now possible and is the obvious way to find out whether
  this actually surfaces anything undocumented. Worth picking a stretch of the
  Salpa Line's less-surveyed sections and letting it run.

---

## Session 2026-09-22 — Phase 6: Aerial cross-check

### Done
- `bunker_scanner/imagery.py` — MML orthophotos from the same Funet/CSC mirror as
  the elevation model, in the **same TM35FIN sheet grid**, so `sheets.py` applies
  unchanged. 0.5 m RGB JPEG2000, 6 × 6 km tiles, read in place over `/vsicurl`
  (they are ~100 MB each and a thumbnail needs a few hundred pixels).
- Review cards now carry a fourth frame: relief, sky-view, hillshade, **aerial**.
- Directory listings cached to `data/imagery-index.json`; coverage is per campaign
  and per year with no single year covering the country, so a lookup walks
  campaigns newest-first. Miehikkälä resolved to 2021 imagery.

### What this is and is not
Stated plainly on the page itself, because it is easy to misread: **optical
imagery cannot confirm a structure under canopy.** That is the entire reason this
project uses LiDAR. The aerial frame is a *negative* check —
- a candidate coinciding with a visible track, ditch, shed, quarry or field edge
  has a mundane explanation;
- and seeing whether the spot is under closed canopy tells a reviewer whether
  "invisible from the air" is the expected state or a red flag.

### Decisions made
- **JPEG, not PNG, for photographs.** A 160 m crop at 0.5 m is 320 × 320 of
  photographic detail; as lossless PNG twenty of them took the review page from
  0.9 MB to 7.8 MB. Resampled to 200 px and encoded as quality-78 JPEG, the page
  is 1.3 MB. Terrain renders stay PNG — they are flat-toned and compress well,
  and JPEG artefacts on a relief model would be actively misleading.
- **Crops that straddle a sheet edge are mosaicked.** A half-black frame reads as
  "nothing there" rather than "no data here", which is the worse failure for a
  tool whose whole job is judging whether something is there.
- **No automatic canopy classifier.** A greenness heuristic over RGB would be
  pseudo-precision; the reviewer can see the frame and judge.

### Better idea recorded for later
For the unsolved forest-ditch false positives from Phase 2, imagery is not
actually the strongest lever — **MML's topographic database** (`maastotietokanta`,
on the same mirror) is. It has mapped ditches, streams, roads, buildings and
field parcels as vectors. A candidate that coincides with a mapped ditch is
explained outright, with no image interpretation. Worth trying before any ML.

# Kickoff Prompt — Bunker Scanner: Phase 0 (Proof of Concept)

Paste this to Claude Code to start the build.

---

You're building **Bunker Scanner**, a tool that processes national LiDAR terrain
data for Sweden and Finland to surface undocumented Cold War/WWII-era bunkers,
trenches, and military structures hidden under forest canopy. The full plan is
in `bunker-scanner-plan.md` in this repo — read it before starting.

**Before writing any code, read `bunker-scanner-workflow.md` in this repo and
follow it for the whole session** — decide and log instead of stopping, verify
before advancing, phase-gate discipline. Set up `PROGRESS.md` if it doesn't
exist yet.

## Why this works (context, not something to re-derive)

Optical satellite/aerial photos only show the treetop canopy. Airborne LiDAR
pulses pass through gaps in the canopy and hit the ground, so a bare-earth
terrain model reveals unnatural bumps, pits, and dead-straight edges (bunker
walls, trench lines) invisible in any aerial photo. This dispatch only needs to
prove that pipeline works end-to-end on one known example — no detection
algorithm yet.

## What you're building (this dispatch = Phase 0 only)

Prove the core method works before investing in anything else: pick one small
test region in Finland with a **documented, known** Salpa Line bunker (public
WWII defensive line with published coordinates — search for a specific bunker
or strongpoint with known lat/lon to use as the validation target), download
the LiDAR/DTM tile covering it from Maanmittauslaitos, and render a hillshade
that should show its footprint.

### Phase 0 — Proof of concept

- Find a specific, real Salpa Line bunker/strongpoint with public coordinates
  to use as the test target. Log which one and the source for its coordinates.
- Register/access Maanmittauslaitos's open data portal and figure out the tile
  indexing for their pre-built elevation model ("Korkeusmalli," 2m or 0.5m) —
  use the pre-built DTM, not raw point clouds, for this phase to avoid
  unnecessary point-cloud-processing complexity up front.
- Download the tile(s) covering the test coordinates.
- Generate a hillshade render (try a couple of sun azimuth/altitude values) and
  a Local Relief Model render of the same area.
- Crop the render tightly around the known bunker's coordinates and inspect it.

**Gate:** the known bunker's footprint (or trench lines connecting to it) is
visibly distinguishable from surrounding natural terrain in at least one of the
renders. Describe specifically what's visible — a rectangular outline, a linear
trench, a mound — not just "the image rendered." If it is NOT visible after
trying both hillshade and LRM with a couple of parameter variations, this is an
escalation per the workflow doc, not a reason to quietly move to Phase 1.

## Explicit non-goals for this dispatch

- No Sweden/Lantmäteriet work yet — Finland only, one known test case, for this
  dispatch.
- No arbitrary-bounding-box generalization yet (that's Phase 1).
- No detection algorithm (OpenCV heuristics or ML) — that's Phase 2. This
  dispatch is purely "can a human see the bunker in the render," done by eye.
- No heritage-registry integration yet (Phase 3).
- No UI — command-line/scripts and saved image outputs are enough.

## When you're done with this dispatch

Update `PROGRESS.md` with: which bunker was used as the test target and its
coordinate source, what the download/CRS process actually required, what
parameters produced the clearest render, and what's visible in it (with the
image saved to `/verification/phase-0/`). State clearly whether the gate
passed. If it passed, note what Phase 1 (arbitrary bounding box + Sweden
support) should pick up. Push to GitHub per the workflow doc's git discipline.

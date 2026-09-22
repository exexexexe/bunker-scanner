# Bunker Scanner — Autonomous Claude Code Workflow

Purpose: let Claude Code run unattended on the Bunker Scanner pipeline build without
stalling on avoidable check-ins. Read this at the start of every session before
touching code. Same operating model as the Little Contraptions workflow doc —
reused here rather than reinvented.

## 1. Default stance: decide and log, don't ask

The maintainer is not watching the session live. The default for any reversible/low-stakes
decision is: make the call, write it into `PROGRESS.md`, keep going.

Examples of "decide and log, don't stop":
- Which specific Lantmäteriet/Maanmittauslaitos tile-naming scheme or download
  endpoint to target, once one is found to work
- Choice of Python libraries within the stack named in the plan doc (e.g. `laspy`
  vs `PDAL` for point-cloud reads, `richdem` vs `whitebox` for terrain derivatives)
- Exact hillshade azimuth/altitude parameters, LRM kernel size, edge-detection
  thresholds — tune by eye and log the values chosen
- File/folder layout for downloaded tiles, rendered outputs, candidate lists
- Naming for internal functions, config fields, output schemas

Examples of "actually stop":
- The test region's known bunker does NOT show up in the hillshade/LRM after
  reasonable parameter tuning — this calls the whole approach into question for
  that terrain type and needs a decision on whether to pick a different test
  region or investigate further
- Data licensing/access terms turn out to require registration, payment, or
  restrict redistribution in a way the plan assumed was free/open
- A coordinate reference system mismatch that can't be resolved with standard
  reprojection (rare, but would indicate something wrong with the source data)
- Anything that would involve downloading data for, or analyzing terrain in,
  Russian territory — out of scope per the plan doc, full stop, escalate rather
  than quietly proceeding if this ever seems tempting for "more coverage"

## 2. PROGRESS.md protocol

One `PROGRESS.md`, appended-to, never rewritten. Per entry:

```
## Session <date/time> — Phase <N>: <phase name>

### Done
- <what was built, one line each>

### Decisions made (no need to revisit unless something breaks)
- <decision> — <one-line rationale>

### Verified
- <what was tested and how>

### Escalations (needs the maintainer's input before proceeding past this point)
- <question, with the options I'd pick between and my leaning>

### Next up
- <what the next session should start with>
```

Keep working on anything not blocked by an escalation rather than stopping the
whole session.

## 3. Phase-gate discipline

Phases and their gates are defined in the plan doc (`bunker-scanner-plan.md`) and
kickoff prompts. Do not start a phase's work until the previous phase's gate is
checked off in `PROGRESS.md`. A half-passed gate is an escalation, not a reason to
move on and patch it later.

## 4. Audit-before-advance ("done ≠ verified")

- **Download/data steps:** confirm the file actually opened and has the expected
  CRS, extent, and point/pixel count — don't assume a 200 response means valid data.
- **Terrain rendering:** actually view the output image (save to
  `/verification/<phase>/<name>.png` and look at it) before claiming a hillshade
  or LRM "looks right." A render with no visible relief anywhere is a bug, not a
  flat region, unless the source tile is independently confirmed to be genuinely
  flat.
- **Phase 0 specifically:** the gate is not "the script ran without errors," it's
  "a human (or a described visual inspection) can see the known bunker's
  footprint in the rendered image." Describe what's visible in the render, not
  just that the render completed.
- **Detection heuristics (later phases):** report false-positive/true-positive
  counts against a manually-reviewed sample, not just "the detector found N
  candidates."

## 5. Git and rollback discipline

- One branch per phase, merged to `main` only after that phase's gate passes.
- Commit at meaningful checkpoints within a phase.
- Never force-push over `main`.
- Push to GitHub after each merge to `main`.

## 6. How to escalate without stopping everything

1. Write the escalation into `PROGRESS.md`, phrased as a concrete choice with a
   stated leaning.
2. Keep working on anything else not dependent on that decision.
3. Only end the session early if everything remaining depends on the blocked
   decision.

## 7. Data and scope guardrails

- Sweden and Finland only. No Russian territory, ever — not for "more coverage,"
  not as a stretch goal. This is a hard boundary from the plan doc, not a
  soft preference.
- Free/open data sources only (Lantmäteriet, Maanmittauslaitos, Fornsök,
  Museovirasto). If a step seems to require a paid API or commercial imagery
  license, that's an escalation — don't substitute one silently.
- Output is a research/candidate shortlist, not a claim of certainty. Candidate
  outputs should carry a confidence indicator, not be presented as confirmed finds.

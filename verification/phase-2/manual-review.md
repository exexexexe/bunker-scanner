# Phase 2 — manual review of detector output

Reviewed by eye from `labelled-miehikkala-candidates.png` and
`control-forest-keski-candidates.png`. Rank and score as of the run recorded in
`evaluation.json`. "On the system" means the chain follows the anti-tank stone
barrier, its trench run, or the fortification cluster around the mapped bunkers.

## Labelled window — Miehikkälä, 0.71 km², 21 candidates

| rank | polarity | verdict | note |
| ---: | --- | --- | --- |
| 1 | raised | on the system | museum fortification cluster, beside two mapped bunkers |
| 2 | raised | on the system | barrier, beside a mapped bunker |
| 3 | raised | on the system | barrier, central run |
| 4 | cut | on the system | follows the beaded line into the rock outcrop, NE corner |
| 5 | cut | on the system | barrier, lower-centre run |
| 6 | raised | **ambiguous** | tracks a dead-straight dark cut in the museum area; reconstruction or modern ditch, cannot tell from terrain alone |
| 7 | raised | on the system | sits on a mapped trench way |
| 8 | cut | on the system | barrier, beside mapped bunkers |
| 9 | raised | on the system | sits on a mapped trench way |
| 10 | cut | on the system | follows a mapped trench way for its whole length |
| 11 | cut | on the system | barrier, central run |
| 12 | raised | on the system | barrier, upper run |
| 13 | cut | **ambiguous** | museum area, close to a road cut |
| 14 | raised | on the system | short, on a mapped trench way |
| 15 | cut | on the system | barrier, lower-centre |
| 16-21 | cut | drainage (demoted) | all in ploughed farmland; 56-341 m from any mapped feature |

**Non-demoted: 13 of 15 on the system, 2 ambiguous, 0 clear false positives.**
**Demoted: 6 of 6 are field drainage** — correctly demoted.

One caveat against over-reading the demotions: rank 19 (length 97.6 m,
straightness 0.99, roughness 0.117) sits near the barrier corridor rather than
squarely in open field. It may be a genuine feature wrongly demoted. Counted
here as a correct demotion, but flagged as the single most likely error in this
table.

## Register agreement

Only **5 of 21** candidates match published geometry within 20 m (median
distance over their beads). That is not a 24% precision figure — it is the
register being incomplete. The barrier is visibly continuous across the whole
frame while OpenStreetMap maps only its lower-left and upper-right ends. Eight
of the thirteen "on the system" chains sit on **unmapped** barrier.

That gap is itself the Phase 3 signal: these are exactly the candidates a
heritage-registry filter should be expected *not* to suppress.

## Control window — forest-keski, 2.59 km²

Residual false positives in forest are **not** the same class as in farmland.
They are:
- forest drainage ditches around peatland parcels, which *curve* and therefore
  escape the straight-and-smooth demotion rule;
- mire and parcel edges;
- stream banks and road cuts.

None resemble a beaded stone barrier on inspection, but the scorer cannot yet
tell them apart, because they are genuinely linear anomalies in rough ground.
This is the main remaining weakness and the obvious target for Phase 2b or the
ML pass.

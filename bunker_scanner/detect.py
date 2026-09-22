"""Heuristic candidate detection over terrain derivatives.

The guiding observation from Phase 0: in this landscape a bare "straight line"
detector is useless. Finnish farmland and managed forest are full of dead-straight
anthropogenic lines — field drainage, plough furrows, ditches, roads, property
boundaries. What actually distinguishes an anti-tank stone barrier is that it is
*beaded*: a row of discrete, compact, similarly sized blocks at regular spacing.
Ditches and furrows are continuous grooves; natural boulder fields are irregular.

So the primary detector finds compact positive anomalies ("beads") and links the
ones that form straight, regularly spaced chains. Spacing regularity does most of
the discriminating work.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage


@dataclass
class Bead:
    x: float  # column, pixels
    y: float  # row, pixels
    area_m2: float
    relief_m: float


@dataclass
class Chain:
    beads: list[Bead]
    length_m: float
    straightness: float      # end-to-end distance / path length, 1.0 = perfectly straight
    spacing_cv: float        # coefficient of variation of gaps; low = engineered
    mean_relief_m: float
    polarity: str = "raised"  # "raised" (stones, parapets) or "cut" (trench, ditch)
    beadedness: float = 0.0   # share of between-bead ground that is ordinary
    roughness: float = 0.0    # relief variability in a ring around the chain
    demoted: bool = False     # matched the drainage-ditch signature
    score: float = 0.0

    @property
    def centroid(self) -> tuple[float, float]:
        return (float(np.mean([b.x for b in self.beads])),
                float(np.mean([b.y for b in self.beads])))


def find_beads(
    lrm: np.ndarray,
    res: float,
    min_relief: float = 0.4,
    min_area_m2: float = 4.0,
    max_area_m2: float = 400.0,
    max_extent_m: float = 30.0,
    exclude: np.ndarray | None = None,
) -> list[Bead]:
    """Compact positive relief anomalies. `exclude` masks out filled nodata."""
    mask = lrm > min_relief
    if exclude is not None:
        mask &= ~exclude
    labels, count = ndimage.label(mask)
    if count == 0:
        return []

    index = np.arange(1, count + 1)
    areas = np.asarray(ndimage.sum_labels(mask, labels, index)) * res * res
    boxes = ndimage.find_objects(labels)
    peaks = np.asarray(ndimage.maximum(lrm, labels, index))
    centres = ndimage.center_of_mass(mask, labels, index)

    beads = []
    for i, (area, box, peak, centre) in enumerate(zip(areas, boxes, peaks, centres)):
        if not (min_area_m2 <= area <= max_area_m2):
            continue
        height = (box[0].stop - box[0].start) * res
        width = (box[1].stop - box[1].start) * res
        if max(height, width) > max_extent_m:
            continue  # a long ridge is not a bead
        beads.append(Bead(x=float(centre[1]), y=float(centre[0]),
                          area_m2=float(area), relief_m=float(peak)))
    return beads


def _heading(a: Bead, b: Bead) -> float:
    return math.atan2(b.y - a.y, b.x - a.x)


def _angle_gap(a: float, b: float) -> float:
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def link_chains(
    beads: list[Bead],
    res: float,
    max_gap_m: float = 20.0,
    max_turn_deg: float = 40.0,
    min_beads: int = 6,
    min_length_m: float = 60.0,
) -> list[Chain]:
    """Grow chains of beads that keep going in roughly the same direction.

    Each seed grows in *both* directions. Growing one way only truncates every
    chain at its seed, which fragmented a single 800 m barrier into eight
    unrelated 70 m stubs on the first run.
    """
    if len(beads) < min_beads:
        return []

    coords = np.array([[b.x, b.y] for b in beads]) * res
    max_turn = math.radians(max_turn_deg)
    neighbours: list[list[int]] = []
    for i in range(len(beads)):
        distance = np.hypot(coords[:, 0] - coords[i, 0], coords[:, 1] - coords[i, 1])
        near = np.where((distance > 0) & (distance <= max_gap_m))[0]
        neighbours.append(sorted(near, key=lambda j: distance[j]))

    def walk(start: int, heading: float, blocked: set[int]) -> list[int]:
        path = [start]
        while True:
            last = path[-1]
            best, best_turn = None, max_turn
            for candidate in neighbours[last]:
                if candidate in path or candidate in blocked:
                    continue
                turn = _angle_gap(_heading(beads[last], beads[candidate]), heading)
                if turn < best_turn:
                    best, best_turn = candidate, turn
            if best is None:
                return path
            # Ease the heading toward the new segment so gentle curves survive.
            new_heading = _heading(beads[last], beads[best])
            heading = math.atan2(0.5 * (math.sin(heading) + math.sin(new_heading)),
                                 0.5 * (math.cos(heading) + math.cos(new_heading)))
            path.append(best)

    def both_ways(start: int, neighbour: int, used: set[int]) -> list[int]:
        forward = walk(start, _heading(beads[start], beads[neighbour]), used)
        backward = walk(start, _heading(beads[neighbour], beads[start]),
                        used | set(forward))
        return list(reversed(backward[1:])) + forward

    chains: list[Chain] = []
    used: set[int] = set()
    for i in range(len(beads)):
        if i in used:
            continue
        best_path: list[int] = []
        for j in neighbours[i]:
            if j in used:
                continue
            path = both_ways(i, j, used)
            if len(path) > len(best_path):
                best_path = path
        if len(best_path) < min_beads:
            continue
        chain = _measure([beads[k] for k in best_path], res)
        if chain.length_m < min_length_m:
            continue
        chains.append(chain)
        used.update(best_path)
    return chains


def _measure(members: list[Bead], res: float) -> Chain:
    points = np.array([[b.x, b.y] for b in members]) * res
    gaps = np.hypot(np.diff(points[:, 0]), np.diff(points[:, 1]))
    path_length = float(gaps.sum())
    span = float(np.hypot(*(points[-1] - points[0])))
    spacing_cv = float(gaps.std() / gaps.mean()) if gaps.mean() > 0 else 1.0
    return Chain(
        beads=members,
        length_m=path_length,
        straightness=span / path_length if path_length else 0.0,
        spacing_cv=spacing_cv,
        mean_relief_m=float(np.mean([b.relief_m for b in members])),
    )


def beadedness(chain: Chain, field: np.ndarray, threshold: float) -> float:
    """Share of the between-bead path that is *not* anomalous.

    A machine-cut drainage ditch is a continuous groove — thresholding it yields
    blobs that link into a tidy chain, but the ground between them is still part
    of the ditch. A row of anti-tank stones has ordinary ground between the
    blocks. This is what actually separates the two.
    """
    samples = []
    for a, b in zip(chain.beads, chain.beads[1:]):
        steps = max(int(math.hypot(b.x - a.x, b.y - a.y)), 2)
        for k in range(1, steps):
            row = int(round(a.y + (b.y - a.y) * k / steps))
            col = int(round(a.x + (b.x - a.x) * k / steps))
            if 0 <= row < field.shape[0] and 0 <= col < field.shape[1]:
                samples.append(field[row, col])
    if not samples:
        return 0.0
    return float(np.mean(np.asarray(samples) < threshold))


def corridor_roughness(chain: Chain, lrm: np.ndarray, res: float,
                       inner_m: float = 6.0, outer_m: float = 25.0) -> float:
    """Relief variability in a ring around the chain, excluding the chain itself.

    Field drainage sits in smooth ploughed ground; a defensive line sits in
    broken terrain among boulders, cuts and spoil. Measured on the surroundings
    so it says something about context rather than about the feature.
    """
    height, width = lrm.shape
    ys, xs = np.mgrid[0:height, 0:width]
    distance = np.full((height, width), np.inf)
    for bead in chain.beads:
        np.minimum(distance, np.hypot(xs - bead.x, ys - bead.y), out=distance)
    ring = (distance > inner_m / res) & (distance < outer_m / res)
    if ring.sum() < 20:
        return 0.0
    return float(np.std(np.abs(lrm)[ring]))


def score_chain(chain: Chain) -> tuple[float, bool]:
    """0-1 confidence, plus whether the chain matched the drainage signature.

    Deliberately blunt and readable: a shortlisting heuristic, not a calibrated
    probability, reported as a confidence indicator rather than a claim.

    Note what is *not* rewarded: straightness. The first version treated it as
    evidence, which put a field drainage ditch at rank 1. Perfect straightness
    over 100 m of Finnish farmland is a machine at work; a defensive line bends
    with the terrain it is defending.
    """
    regularity = max(0.0, 1.0 - chain.spacing_cv / 0.6)
    extent = min(1.0, chain.length_m / 300.0)
    context = min(1.0, chain.roughness / 0.25)
    score = (0.30 * regularity + 0.20 * extent
             + 0.20 * chain.beadedness + 0.30 * context)

    # Dead straight and sitting in smooth ground: almost always drainage.
    # Demote rather than drop, so it stays reviewable.
    demoted = chain.straightness >= 0.985 and chain.roughness < 0.16
    if demoted:
        score *= 0.35
    return round(score, 3), demoted


def detect(
    lrm: np.ndarray,
    res: float,
    exclude: np.ndarray | None = None,
    **kwargs,
) -> tuple[list[Chain], list[Bead]]:
    """Find beaded chains in both polarities.

    Stone barriers and parapets read as raised anomalies; trenches, ditches and
    bunker entrance cuts read as cuts. Chains are kept polarity-pure — a row of
    stones is consistently raised, and mixing the two would let noise bridge
    unrelated features.
    """
    bead_keys = {"min_relief", "min_area_m2", "max_area_m2", "max_extent_m"}
    link_keys = {"max_gap_m", "max_turn_deg", "min_beads", "min_length_m"}
    bead_args = {k: v for k, v in kwargs.items() if k in bead_keys}
    link_args = {k: v for k, v in kwargs.items() if k in link_keys}

    all_chains: list[Chain] = []
    all_beads: list[Bead] = []
    for polarity, field_array in (("raised", lrm), ("cut", -lrm)):
        beads = find_beads(field_array, res, exclude=exclude, **bead_args)
        all_beads.extend(beads)
        threshold = bead_args.get("min_relief", 0.4)
        for chain in link_chains(beads, res, **link_args):
            chain.polarity = polarity
            chain.beadedness = beadedness(chain, field_array, threshold)
            chain.roughness = corridor_roughness(chain, lrm, res)
            chain.score, chain.demoted = score_chain(chain)
            all_chains.append(chain)

    all_chains.sort(key=lambda c: c.score, reverse=True)
    return all_chains, all_beads

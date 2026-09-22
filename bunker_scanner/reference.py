"""Published military-structure coordinates used to validate renders.

Source: OpenStreetMap (ODbL) — nodes tagged military=bunker and friends, plus
military=trench / barrier=tank_trap ways where they are mapped. Raw responses and
the Overpass queries that produced them live in data/reference/, so every
validation claim can be re-derived rather than taken on trust.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field

from rasterio.warp import transform as warp_transform

REF_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "reference"

TRENCH_COLOUR = "#ffd400"
TANK_TRAP_COLOUR = "#00d1ff"


@dataclass(frozen=True)
class Target:
    """A named place to validate against, as lon/lat."""
    lon: float
    lat: float
    note: str = ""


@dataclass(frozen=True)
class Register:
    crs: str
    points_file: str
    targets: dict[str, Target]
    lines_file: str | None = None


REGISTERS: dict[str, Register] = {
    "fi": Register(
        crs="EPSG:3067",
        points_file="osm-salpa-bunkers-virolahti-miehikkala.json",
        lines_file="osm-salpa-lines-miehikkala.json",
        targets={
            "miehikkala": Target(27.6658, 60.6806,
                                 "Salpa Line bunker chain, 11 mapped within 400 m"),
        },
    ),
    "se": Register(
        crs="EPSG:3006",
        points_file="osm-bunkers-sweden-skane-blekinge.json",
        targets={
            "skanelinjen": Target(13.2170, 55.3600,
                                  "Per Albin line coastal bunkers, Skane south coast"),
            "backastrand": Target(15.5500, 56.0994,
                                  "Backastrand coastal artillery, Blekinge"),
        },
    ),
}


def register(country: str) -> Register:
    try:
        return REGISTERS[country]
    except KeyError:
        raise SystemExit(
            f"no validation register for {country!r}; have {sorted(REGISTERS)}") from None


def project(lon: float, lat: float, crs: str) -> tuple[float, float]:
    xs, ys = warp_transform("EPSG:4326", crs, [lon], [lat])
    return xs[0], ys[0]


def _elements(filename: str) -> list[dict]:
    return json.loads((REF_DIR / filename).read_text())["elements"]


def points(country: str) -> list[tuple[float, float, str]]:
    """(easting, northing, name) for every mapped structure, in the register's CRS."""
    reg = register(country)
    out = []
    for element in _elements(reg.points_file):
        lat = element.get("lat") or element.get("center", {}).get("lat")
        lon = element.get("lon") or element.get("center", {}).get("lon")
        if lat is None or lon is None:
            continue
        east, north = project(lon, lat, reg.crs)
        out.append((east, north, element.get("tags", {}).get("name", "")))
    return out


def lines(country: str) -> list[tuple[list[tuple[float, float]], str]]:
    """(coordinates, colour) for every mapped trench and tank-trap way."""
    reg = register(country)
    if not reg.lines_file:
        return []
    out = []
    for element in _elements(reg.lines_file):
        geometry = element.get("geometry") or []
        if len(geometry) < 2:
            continue
        coords = [project(p["lon"], p["lat"], reg.crs) for p in geometry]
        is_trap = element.get("tags", {}).get("barrier") == "tank_trap"
        out.append((coords, TANK_TRAP_COLOUR if is_trap else TRENCH_COLOUR))
    return out


def target_box(country: str, name: str, half: float) -> tuple[float, float, float, float]:
    reg = register(country)
    if name not in reg.targets:
        raise SystemExit(f"{country}: no target {name!r}; have {sorted(reg.targets)}")
    target = reg.targets[name]
    east, north = project(target.lon, target.lat, reg.crs)
    return east - half, north - half, east + half, north + half


def within(items, west, south, east, north):
    return [p for p in items if west <= p[0] <= east and south <= p[1] <= north]

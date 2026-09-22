"""Heritage registers — deciding whether a candidate is already documented.

Finland: Museovirasto's Kulttuuriympäristön paikkatietoaineistot WFS. Note the
host: the old `kartta.nba.fi` used in Phase 0 is now NXDOMAIN, which is why that
lookup appeared to "not respond from this machine". The live service is
`geoserver.museovirasto.fi`.

Two registers matter and they are different things:

  muinaisjaannos_*              statutory ancient monuments
  muu_kulttuuriperintokohde_*   other cultural heritage sites

Salpa Line works sit in the *second* one, typed `puolustusvarustukset`
(defensive works) with subtypes such as `taistelukaivannot` (battle trenches).
A filter that only consulted the ancient-monument layer would report every
documented WWII fortification in Finland as an undocumented find.
"""

from __future__ import annotations

import json
import pathlib
import urllib.parse
import urllib.request
from dataclasses import dataclass

from shapely.geometry import shape
from shapely.strtree import STRtree

CACHE_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "heritage"

FINLAND_WFS = "https://geoserver.museovirasto.fi/geoserver/rajapinta_suojellut/wfs"
FINLAND_LAYERS = (
    "muinaisjaannos_piste",
    "muinaisjaannos_alue",
    "muu_kulttuuriperintokohde_piste",
    "muu_kulttuuriperintokohde_alue",
)
# Types that mean "this is a known military structure", not just any heritage.
MILITARY_TYPES = {"puolustusvarustukset"}


@dataclass(frozen=True)
class Site:
    id: str
    name: str
    kind: str          # tyyppi
    subkind: str       # alatyyppi / typin_tarkenne
    dating: str        # ajoitus
    layer: str
    url: str

    @property
    def military(self) -> bool:
        return self.kind in MILITARY_TYPES


def _clean(value) -> str:
    return str(value).strip() if value is not None else ""


def fetch_finland(west, south, east, north, refresh: bool = False) -> list[tuple]:
    """(shapely geometry, Site) for every registered site intersecting the box.

    Cached per box so repeated runs and evaluation passes do not hammer the WFS.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = f"fi-{west:.0f}-{south:.0f}-{east:.0f}-{north:.0f}.json"
    cache = CACHE_DIR / key

    if cache.exists() and not refresh:
        payload = json.loads(cache.read_text())
    else:
        payload = {}
        for layer in FINLAND_LAYERS:
            query = urllib.parse.urlencode({
                "service": "WFS", "version": "2.0.0", "request": "GetFeature",
                "typeNames": f"rajapinta_suojellut:{layer}",
                "srsName": "EPSG:3067",
                "bbox": f"{west},{south},{east},{north},EPSG:3067",
                "outputFormat": "application/json", "count": "1000",
            })
            with urllib.request.urlopen(f"{FINLAND_WFS}?{query}", timeout=120) as response:
                payload[layer] = json.load(response).get("features", [])
        cache.write_text(json.dumps(payload))

    out = []
    for layer, features in payload.items():
        for feature in features:
            geometry = feature.get("geometry")
            if not geometry:
                continue
            props = feature.get("properties", {})
            site = Site(
                id=_clean(props.get("mjtunnus")),
                name=_clean(props.get("kohdenimi")),
                kind=_clean(props.get("tyyppi")),
                subkind=_clean(props.get("alatyyppi") or props.get("tyypin_tarkenne")),
                dating=_clean(props.get("ajoitus")),
                layer=layer,
                url=_clean(props.get("url")),
            )
            out.append((shape(geometry), site))
    return out


class Register:
    """Spatial index over registered sites, for classifying candidates."""

    def __init__(self, entries: list[tuple]):
        self.entries = entries
        self.geometries = [g for g, _ in entries]
        self.tree = STRtree(self.geometries) if self.geometries else None

    @classmethod
    def for_box(cls, country: str, west, south, east, north, pad: float = 500.0,
                refresh: bool = False) -> "Register":
        if country != "fi":
            # Sweden: Riksantikvarieambetet Fornsok. Not wired up — there are no
            # Swedish candidates to filter until the Lantmateriet product arrives
            # (Phase 1b), so this would be untestable code.
            raise NotImplementedError(
                "only the Finnish register is wired up; see Phase 1b in PROGRESS.md")
        return cls(fetch_finland(west - pad, south - pad, east + pad, north + pad,
                                 refresh=refresh))

    def nearest(self, geometry, max_distance: float):
        """(Site, distance) for the closest registered site, or (None, inf)."""
        if self.tree is None:
            return None, float("inf")
        index = self.tree.nearest(geometry)
        if index is None:
            return None, float("inf")
        candidate_geometry, site = self.entries[int(index)]
        distance = geometry.distance(candidate_geometry)
        if distance > max_distance:
            return None, distance
        return site, distance

    def classify(self, geometry, max_distance: float = 50.0) -> dict:
        """known_military / known_other / undocumented, with what matched."""
        site, distance = self.nearest(geometry, max_distance)
        if site is None:
            return {"status": "undocumented", "distance_m": round(distance, 1)
                    if distance != float("inf") else None}
        return {
            "status": "known_military" if site.military else "known_other",
            "distance_m": round(distance, 1),
            "site_id": site.id, "site_name": site.name,
            "site_kind": site.kind, "site_subkind": site.subkind,
            "site_dating": site.dating, "site_layer": site.layer,
            "site_url": site.url,
        }

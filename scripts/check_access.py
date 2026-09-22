"""Confirm a source is reachable and, where needed, that credentials work.

    scripts/check_access.py             # every source
    scripts/check_access.py --country se

Run this first after setting LANTMATERIET_USER / LANTMATERIET_PASSWORD: it
resolves a real tile and reads its header, so a pass means the whole path works.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bunker_scanner import reference
from bunker_scanner.fetch import gdal_env
from bunker_scanner.sources import SOURCES, get_source

# A box known to have coverage, in each source's own CRS.
PROBES = {
    "fi": (536_000, 6_726_600, 536_400, 6_727_000),
    "se": reference.target_box("se", "skanelinjen", 200.0),
}


def check(key: str) -> bool:
    source = get_source(key)
    print(f"{source.label} ({source.crs}, {source.resolution} m)")

    if source.auth_env:
        user_var, password_var = source.auth_env
        if source.credentials():
            print(f"  credentials: {user_var} and {password_var} are set")
        else:
            print(f"  credentials: MISSING — set {user_var} and {password_var}")
            print("    free account: https://geotorget.lantmateriet.se")

    try:
        tiles = source.tiles(*PROBES[key])
    except Exception as error:
        print(f"  tile index: FAILED — {type(error).__name__}: {error}")
        return False
    if not tiles:
        print("  tile index: FAILED — no tiles returned for the probe box")
        return False
    print(f"  tile index: ok — {tiles[0].name}")

    if source.auth_env and not source.credentials():
        print("  data read: skipped, no credentials\n")
        return False

    import rasterio
    try:
        with gdal_env(source):
            target = (f"/vsicurl/{tiles[0].url}" if source.stream
                      else tiles[0].url.replace("https://", "/vsicurl/https://"))
            with rasterio.open(target) as handle:
                print(f"  data read: ok — {handle.width}x{handle.height} px, "
                      f"{handle.crs}, nodata {handle.nodata}")
    except Exception as error:
        message = str(error).strip().splitlines()[0] if str(error) else type(error).__name__
        print(f"  data read: FAILED — {message}")
        if "401" in message or "Unauthorized" in message:
            print("    no credentials reached the server")
        elif "403" in message or "Forbidden" in message:
            print("    credentials were sent but rejected for this product.")
            print("    Geotorget issues credentials per ordered product: credentials for")
            print("    one dataset do not work for another. Order 'Markhojdmodell")
            print("    Nedladdning' at geotorget.lantmateriet.se and use the credentials")
            print("    issued for that product.")
        print()
        return False

    print("  ready\n")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", choices=sorted(SOURCES), default=None)
    args = parser.parse_args(argv)
    keys = [args.country] if args.country else sorted(SOURCES)
    results = [check(key) for key in keys]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())

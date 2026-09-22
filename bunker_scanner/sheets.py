"""TM35FIN (EPSG:3067) map-sheet index used by Maanmittauslaitos raster products.

Derived empirically in Phase 0 by reading the geotransforms of known tiles off the
Funet MML mirror; see PROGRESS.md. Verified against L4311A/B, L4312A, L4321A,
L4111A, L4211A, L4411A, M4111A.

Sheet hierarchy, all subdivisions ordered column-major (west->east outer,
south->north inner):

    level 1  "L4"        192 x 96 km   letter = northing band, digit = easting band
    level 2  "L42"        96 x 48 km   1=SW 2=NW 3=SE 4=NE
    level 3  "L421"       48 x 24 km   same ordering
    level 4  "L4213"      24 x 12 km   same ordering
    level 5  "L4213F"      6 x  6 km   A..H = 4 columns x 2 rows, column-major
"""

# No "O": the Finnish sheet letters skip it.
ROW_LETTERS = "KLMNPQRSTUVWX"
ROW_HEIGHT = 96_000
COL_WIDTH = 192_000

# Anchor: sheet L4 has its south-west corner at (308000, 6666000) in EPSG:3067.
_ANCHOR_ROW = ROW_LETTERS.index("L")
_ANCHOR_COL = 4
_ANCHOR_E = 308_000
_ANCHOR_N = 6_666_000

LEVEL5_LETTERS = "ABCDEFGH"
TILE_SIZE = 6_000  # level-5 tile edge, metres


def _sheet1_origin(letter: str, digit: int) -> tuple[int, int]:
    row = ROW_LETTERS.index(letter)
    east = _ANCHOR_E + (digit - _ANCHOR_COL) * COL_WIDTH
    north = _ANCHOR_N + (row - _ANCHOR_ROW) * ROW_HEIGHT
    return east, north


def tile_name(easting: float, northing: float) -> str:
    """Return the level-5 (6 x 6 km) sheet name covering a TM35FIN coordinate."""
    col = (easting - _ANCHOR_E) // COL_WIDTH + _ANCHOR_COL
    row_idx = int((northing - _ANCHOR_N) // ROW_HEIGHT) + _ANCHOR_ROW
    if not 0 <= row_idx < len(ROW_LETTERS):
        raise ValueError(f"northing {northing} is outside the Finnish sheet grid")
    name = f"{ROW_LETTERS[row_idx]}{int(col)}"

    east0, north0 = _sheet1_origin(name[0], int(name[1]))
    de, dn = easting - east0, northing - north0

    # Levels 2-4: each halves both axes.
    width, height = COL_WIDTH, ROW_HEIGHT
    for _ in range(3):
        width, height = width // 2, height // 2
        c, r = int(de // width), int(dn // height)
        name += str(c * 2 + r + 1)
        de -= c * width
        dn -= r * height

    # Level 5: the 24 x 12 km sheet splits into 4 columns x 2 rows of 6 x 6 km.
    c, r = int(de // TILE_SIZE), int(dn // TILE_SIZE)
    return name + LEVEL5_LETTERS[c * 2 + r]


def tile_bounds(name: str) -> tuple[int, int, int, int]:
    """(west, south, east, north) of a level-5 sheet, in EPSG:3067 metres."""
    east, north = _sheet1_origin(name[0], int(name[1]))
    width, height = COL_WIDTH, ROW_HEIGHT
    for digit in name[2:5]:
        width, height = width // 2, height // 2
        idx = int(digit) - 1
        east += (idx // 2) * width
        north += (idx % 2) * height
    idx = LEVEL5_LETTERS.index(name[5])
    east += (idx // 2) * TILE_SIZE
    north += (idx % 2) * TILE_SIZE
    return east, north, east + TILE_SIZE, north + TILE_SIZE


def tile_path(name: str) -> str:
    """Mirror-relative path, e.g. 'L5/L52/L5213F.tif'."""
    return f"{name[:2]}/{name[:3]}/{name}.tif"

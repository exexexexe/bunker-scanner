"""Credential loading.

Order of precedence: whatever is already in the process environment wins, then
`BUNKER_SCANNER_ENV_FILE` if set, then a `.env` beside the repo. Nothing here
ever overwrites a variable that is already set, so an explicit export in the
shell always beats a file.
"""

from __future__ import annotations

import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_loaded = False


def parse_env_file(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def load_env(force: bool = False) -> list[pathlib.Path]:
    """Load .env files into os.environ without clobbering existing values."""
    global _loaded
    if _loaded and not force:
        return []
    _loaded = True

    candidates = []
    override = os.environ.get("BUNKER_SCANNER_ENV_FILE")
    if override:
        candidates.append(pathlib.Path(override).expanduser())
    candidates.append(ROOT / ".env")

    used = []
    for path in candidates:
        if not path.is_file():
            continue
        for key, value in parse_env_file(path).items():
            os.environ.setdefault(key, value)
        used.append(path)
    return used

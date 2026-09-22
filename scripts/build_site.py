"""Build the public static site from detection runs.

    scripts/build_site.py --run miehikkala --run salpa-virolahti-c10 ...

Writes site/index.html plus site/runs/<name>.html. Everything is static and
self-contained; the server does nothing but hand out files.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bunker_scanner.review import build

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "bunker_scanner" / "site_template.html"
REPO = "https://github.com/exexexexe/bunker-scanner"

DESCRIPTIONS = {
    "miehikkala": "Salpa Line bunker chain at Miehikkälä — the window the method "
                  "was validated on, with 11 individually named bunkers in frame.",
    "salpa-virolahti-c10": "Salpa Line at Virolahti, 15 km south — a second "
                           "documented stretch, used to check the method travels.",
    "control-forest-keski": "Central Finland forest and mire, far from any known "
                            "fortification — a control for what the detector does "
                            "on ordinary terrain.",
}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="append", required=True)
    parser.add_argument("--out", default=str(ROOT / "site"))
    parser.add_argument("--crop", type=float, default=160.0)
    args = parser.parse_args(argv)

    out_dir = pathlib.Path(args.out)
    runs_dir = out_dir / "runs"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    runs_dir.mkdir(parents=True)

    entries = []
    for name in args.run:
        detection_dir = ROOT / "output" / "detect" / name
        page, context = build(detection_dir, ROOT / "data" / "dem", crop_m=args.crop)
        (runs_dir / f"{name}.html").write_text(page)

        candidates = context["candidates"]
        undocumented = sum(1 for c in candidates
                           if c.get("status") == "undocumented")
        window = context["window"]
        span_km = (window["bbox"][2] - window["bbox"][0]) / 1000
        area = span_km * (window["bbox"][3] - window["bbox"][1]) / 1000
        entries.append({
            "name": name, "candidates": len(candidates),
            "undocumented": undocumented, "area_km2": area,
            "size_mb": len(page.encode()) / 1e6,
        })
        print(f"  {name}: {len(candidates)} candidates "
              f"({undocumented} undocumented), {len(page.encode())/1e6:.1f} MB")

    rows = "".join(
        f'<li class="run"><a href="runs/{html.escape(e["name"])}.html">'
        f'<span class="name">{html.escape(e["name"])}</span>'
        f'<span class="meta">{e["area_km2"]:.2f} km²</span>'
        f'<span class="meta">{e["candidates"]} candidates</span>'
        f'<span class="meta undoc">{e["undocumented"]} undocumented</span>'
        f'<span class="desc">{html.escape(DESCRIPTIONS.get(e["name"], ""))}</span>'
        f"</a></li>"
        for e in entries)

    index = TEMPLATE.read_text()
    index = index.replace("__RUNS__", rows)
    index = index.replace("__REPO__", REPO)
    index = index.replace("__REPO_LABEL__", REPO.replace("https://", ""))
    index = index.replace("__BUILT__", dt.date.today().isoformat())
    (out_dir / "index.html").write_text(index)

    (out_dir / "runs.json").write_text(json.dumps(entries, indent=2))
    total = sum((out_dir.rglob("*.html").__class__ and f.stat().st_size)
                for f in out_dir.rglob("*"))
    print(f"site -> {out_dir} ({total/1e6:.1f} MB total)")


if __name__ == "__main__":
    main()

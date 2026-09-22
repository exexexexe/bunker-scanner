"""Static file server for the Bunker Scanner site.

Nothing dynamic: `scripts/build_site.py` writes site/ and this hands it out.
Railway sets PORT.
"""

from __future__ import annotations

import os
import pathlib

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

SITE = pathlib.Path(__file__).resolve().parent / "site"


async def healthz(request):
    return PlainTextResponse("ok")


app = Starlette(routes=[
    Route("/healthz", healthz),
    Mount("/", app=StaticFiles(directory=SITE, html=True), name="site"),
])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))

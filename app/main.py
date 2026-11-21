"""Fireline — wildfire insurance risk from public data.

Run: uvicorn app.main:app
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.constants import (
    CHECKLIST,
    DEFAULT_EXAMPLE_ADDRESS,
    DEFAULT_EXAMPLE_LAT,
    DEFAULT_EXAMPLE_LON,
    SECOND_EXAMPLE_LAT,
    SECOND_EXAMPLE_LON,
    DISCLAIMER,
    SECOND_EXAMPLE_ADDRESS,
)
from app.risk import LookupProblem, evaluate

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fireline")

app = FastAPI(title="Fireline", docs_url="/api/docs")

CLEAN_FAILURE = {
    "ok": False,
    "error": "failed",
    "message": "The lookup failed before a score could be computed. No numbers were filled in.",
}


@app.exception_handler(Exception)
async def unhandled(request, exc):  # noqa: ARG001
    logger.exception("unhandled error")
    return JSONResponse(CLEAN_FAILURE, status_code=200)


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "status": "ok",
        "disclaimer": DISCLAIMER,
        "firms_configured": bool((os.environ.get("FIRMS_MAP_KEY") or "").strip()),
        "examples": [
            {
                "id": "default",
                "address": DEFAULT_EXAMPLE_ADDRESS,
                "lat": DEFAULT_EXAMPLE_LAT,
                "lon": DEFAULT_EXAMPLE_LON,
                "note": "Greene County, TN",
            },
            {
                "id": "second",
                "address": SECOND_EXAMPLE_ADDRESS,
                "lat": SECOND_EXAMPLE_LAT,
                "lon": SECOND_EXAMPLE_LON,
                "note": "Berkeley, CA",
            },
        ],
        "checklist": list(CHECKLIST),
    }


@app.get("/api/risk")
def risk(
    address: str | None = Query(default=None, max_length=240),
    lat: float | None = None,
    lon: float | None = None,
    simulate_outage: str | None = Query(default=None, max_length=80),
):
    try:
        return evaluate(address, lat, lon, simulate_outage)
    except LookupProblem as exc:
        return JSONResponse(
            {
                "ok": False,
                "error": exc.error,
                "message": exc.message,
                "candidates": exc.candidates,
            },
            status_code=200,
        )
    except Exception:
        logger.exception("risk lookup failed")
        return JSONResponse(CLEAN_FAILURE, status_code=200)


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

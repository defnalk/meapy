"""FastAPI server exposing meapy on Cloud Run.

Endpoints mirror the Lambda adapter so the two deployment targets stay in
sync. Kept dependency-light: only fastapi + uvicorn beyond meapy itself.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

import meapy
from meapy import heat_transfer

app = FastAPI(title="meapy", version=meapy.__version__)


@app.get("/")
def health() -> dict[str, Any]:
    return {"status": "ok", "version": meapy.__version__}


@app.get("/version")
def version() -> dict[str, str]:
    return {"version": meapy.__version__}


@app.post("/analyse")
def analyse(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return {"result": heat_transfer.analyse_exchanger(**payload)}
    except TypeError as exc:
        raise HTTPException(status_code=400, detail=f"bad payload: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

"""AWS Lambda / Function URL adapter for meapy.

Parses API Gateway v2 (HTTP API) and Lambda Function URL events, dispatches
to a tiny in-process router, and returns Lambda proxy responses.

Routes:
    GET  /         -> health (version + uptime)
    GET  /version  -> package version
    POST /analyse  -> run a meapy analysis from a JSON body

Cold-start optimisation: heavy imports happen at module load (numpy/scipy
are pulled in transitively by meapy itself), so warm invocations only pay
the routing cost.

Modify when:
    - Adding new HTTP routes
    - Changing the analyse payload contract
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import meapy
from meapy import heat_transfer

LOG = logging.getLogger("meapy.lambda")
LOG.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

_BOOT_TS = time.time()
JsonDict = dict[str, Any]


def _response(status: int, body: JsonDict) -> JsonDict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _health(_body: JsonDict) -> JsonDict:
    return _response(
        200,
        {
            "status": "ok",
            "version": meapy.__version__,
            "uptime_seconds": round(time.time() - _BOOT_TS, 3),
        },
    )


def _version(_body: JsonDict) -> JsonDict:
    return _response(200, {"version": meapy.__version__})


def _analyse(body: JsonDict) -> JsonDict:
    """Run a heat-exchanger analysis. Body must match analyse_exchanger kwargs."""
    try:
        result = heat_transfer.analyse_exchanger(**body)
    except TypeError as exc:
        return _response(400, {"error": f"bad payload: {exc}"})
    except ValueError as exc:
        # Physical/domain validation errors (e.g. non-positive flows, LMTD
        # crossover) are caller-fixable inputs, not server faults.
        return _response(400, {"error": f"invalid inputs: {exc}"})
    return _response(200, {"result": result})


_ROUTES = {
    ("GET", "/"): _health,
    ("GET", "/version"): _version,
    ("POST", "/analyse"): _analyse,
}


def handler(event: JsonDict, _context: object = None) -> JsonDict:
    try:
        http = event.get("requestContext", {}).get("http", {})
        method = http.get("method", "GET").upper()
        path = http.get("path", "/")

        raw_body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            import base64

            raw_body = base64.b64decode(raw_body).decode("utf-8")
        body: JsonDict = json.loads(raw_body) if raw_body else {}

        route = _ROUTES.get((method, path))
        if route is None:
            return _response(404, {"error": f"no route for {method} {path}"})
        return route(body)
    except json.JSONDecodeError as exc:
        return _response(400, {"error": f"invalid JSON body: {exc}"})
    except Exception as exc:  # noqa: BLE001 — last-resort guard
        LOG.exception("unhandled error")
        return _response(500, {"error": str(exc)})

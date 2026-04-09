"""Unit tests for the AWS Lambda / Function URL adapter."""

from __future__ import annotations

import base64
import json
from typing import Any

import pytest

from meapy import __version__, lambda_handler


def _event(method: str, path: str, body: Any = None, b64: bool = False) -> dict[str, Any]:
    raw = "" if body is None else json.dumps(body)
    if b64:
        raw = base64.b64encode(raw.encode()).decode()
    return {
        "requestContext": {"http": {"method": method, "path": path}},
        "body": raw,
        "isBase64Encoded": b64,
    }


def _decode(resp: dict[str, Any]) -> dict[str, Any]:
    return json.loads(resp["body"])


class TestRouting:
    def test_health(self) -> None:
        resp = lambda_handler.handler(_event("GET", "/"))
        assert resp["statusCode"] == 200
        body = _decode(resp)
        assert body["status"] == "ok"
        assert body["version"] == __version__
        assert "uptime_seconds" in body

    def test_version(self) -> None:
        resp = lambda_handler.handler(_event("GET", "/version"))
        assert resp["statusCode"] == 200
        assert _decode(resp) == {"version": __version__}

    def test_unknown_route(self) -> None:
        resp = lambda_handler.handler(_event("GET", "/nope"))
        assert resp["statusCode"] == 404
        assert "no route" in _decode(resp)["error"]


class TestAnalyse:
    @pytest.fixture
    def good_payload(self) -> dict[str, Any]:
        return {
            "mea_flow_kg_h": 900,
            "cp_mea_j_kg_k": 3940,
            "t_mea_in_c": 85.0,
            "t_mea_out_c": 42.0,
            "utility_flow_kg_h": 800,
            "cp_utility_j_kg_k": 3940,
            "t_utility_in_c": 30.0,
            "t_utility_out_c": 68.0,
            "area_m2": 0.30,
        }

    def test_analyse_ok(self, good_payload: dict[str, Any]) -> None:
        resp = lambda_handler.handler(_event("POST", "/analyse", good_payload))
        assert resp["statusCode"] == 200
        assert "result" in _decode(resp)

    def test_analyse_bad_payload(self) -> None:
        resp = lambda_handler.handler(_event("POST", "/analyse", {"nonsense": 1}))
        assert resp["statusCode"] == 400
        assert "bad payload" in _decode(resp)["error"]

    def test_analyse_base64_body(self, good_payload: dict[str, Any]) -> None:
        resp = lambda_handler.handler(_event("POST", "/analyse", good_payload, b64=True))
        assert resp["statusCode"] == 200


class TestErrors:
    def test_invalid_json(self) -> None:
        evt = {
            "requestContext": {"http": {"method": "POST", "path": "/analyse"}},
            "body": "{not json",
        }
        resp = lambda_handler.handler(evt)
        assert resp["statusCode"] == 400
        assert "invalid JSON" in _decode(resp)["error"]

    def test_missing_request_context(self) -> None:
        # Defaults to GET /, so should hit the health route.
        resp = lambda_handler.handler({})
        assert resp["statusCode"] == 200

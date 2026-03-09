"""Unit tests for FastAPI application helpers."""

from __future__ import annotations

import asyncio
import json
from copy import deepcopy

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError

import app.main as main_module

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def reset_openapi_schema() -> None:
    """Reset the cached OpenAPI schema between tests."""
    original_schema = main_module.app.openapi_schema
    main_module.app.openapi_schema = None
    yield
    main_module.app.openapi_schema = original_schema


def test_custom_openapi_rewrites_validation_responses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rewrites 422 validation docs without crashing on path metadata."""
    raw_schema = {
        "paths": {
            "/demo": {
                "parameters": [
                    {
                        "name": "demo",
                        "in": "query",
                    }
                ],
                "post": {
                    "responses": {
                        "422": {
                            "description": "Validation Error",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": (
                                            "#/components/schemas/"
                                            "HTTPValidationError"
                                        ),
                                    }
                                }
                            },
                        }
                    }
                },
            }
        },
        "components": {
            "schemas": {
                "ErrorResponse": {
                    "title": "ErrorResponse",
                    "type": "object",
                },
                "HTTPValidationError": {
                    "title": "HTTPValidationError",
                    "type": "object",
                },
                "ValidationError": {
                    "title": "ValidationError",
                    "type": "object",
                },
            }
        },
    }

    def fake_get_openapi(**_: object) -> dict[str, object]:
        return deepcopy(raw_schema)

    monkeypatch.setattr(main_module, "get_openapi", fake_get_openapi)

    schema = main_module.custom_openapi()
    responses = schema["paths"]["/demo"]["post"]["responses"]

    assert "422" not in responses
    assert responses["400"]["content"]["application/json"]["schema"] == {
        "$ref": main_module.ERROR_RESPONSE_SCHEMA_REF,
    }
    assert "HTTPValidationError" not in schema["components"]["schemas"]
    assert "ValidationError" not in schema["components"]["schemas"]


def test_custom_openapi_preserves_app_openapi_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Forwards optional FastAPI OpenAPI metadata to get_openapi()."""
    captured: dict[str, object] = {}

    monkeypatch.setattr(main_module.app, "summary", "API summary")
    monkeypatch.setattr(main_module.app, "openapi_version", "3.1.1")
    monkeypatch.setattr(
        main_module.app,
        "openapi_tags",
        [{"name": "recipes"}],
    )
    monkeypatch.setattr(
        main_module.app,
        "servers",
        [{"url": "https://api.example.com"}],
    )
    monkeypatch.setattr(
        main_module.app,
        "terms_of_service",
        "https://example.com/terms",
    )
    monkeypatch.setattr(
        main_module.app,
        "contact",
        {"name": "Support"},
    )
    monkeypatch.setattr(
        main_module.app,
        "license_info",
        {"name": "MIT"},
    )
    monkeypatch.setattr(
        main_module.app,
        "separate_input_output_schemas",
        False,
    )
    monkeypatch.setattr(
        main_module.app,
        "openapi_external_docs",
        {"description": "Docs", "url": "https://example.com/docs"},
    )
    monkeypatch.setattr(
        main_module.app.webhooks,
        "routes",
        ["webhook-route"],
    )

    def fake_get_openapi(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "paths": {},
            "components": {"schemas": {}},
        }

    monkeypatch.setattr(main_module, "get_openapi", fake_get_openapi)

    main_module.custom_openapi()

    assert captured["summary"] == "API summary"
    assert captured["openapi_version"] == "3.1.1"
    assert captured["tags"] == [{"name": "recipes"}]
    assert captured["servers"] == [{"url": "https://api.example.com"}]
    assert captured["terms_of_service"] == "https://example.com/terms"
    assert captured["contact"] == {"name": "Support"}
    assert captured["license_info"] == {"name": "MIT"}
    assert captured["separate_input_output_schemas"] is False
    assert captured["external_docs"] == {
        "description": "Docs",
        "url": "https://example.com/docs",
    }
    assert captured["webhooks"] == ["webhook-route"]


def test_validation_exception_handler_uses_generic_detail() -> None:
    """Uses request-part agnostic detail text for validation failures."""
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [],
        }
    )
    request.state.correlation_id = "test-correlation-id"
    exc = RequestValidationError(
        [
            {
                "type": "missing",
                "loc": ("query", "limit"),
                "msg": "Field required",
                "input": None,
            }
        ]
    )

    response = asyncio.run(
        main_module.validation_exception_handler(request, exc)
    )
    data = json.loads(response.body)

    assert data["detail"] == "Request contains invalid parameters."
    assert data["errors"] == [
        {
            "field": "query.limit",
            "message": "Field required",
        }
    ]

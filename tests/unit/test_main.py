"""Unit tests for FastAPI application helpers."""

from __future__ import annotations

from copy import deepcopy

import pytest

import app.main as main_module


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

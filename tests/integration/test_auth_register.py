"""Integration tests for the user registration endpoint."""

from __future__ import annotations

from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models.user import User

pytestmark = pytest.mark.integration

REGISTER_URL = "/api/v1/auth/register"
VALID_PAYLOAD = {
    "email": "chef@example.com",
    "username": "chefmario",
    "password": "SecureP@ss123",
    "password_confirm": "SecureP@ss123",
}


def _payload(**overrides: object) -> dict[str, object]:
    """Build a registration payload with optional overrides."""
    payload: dict[str, object] = VALID_PAYLOAD.copy()
    payload.update(overrides)
    return payload


def _register(
    test_client: TestClient,
    payload: dict[str, object],
) -> Response:
    """Post a registration request to the API."""
    return test_client.post(REGISTER_URL, json=payload)


def _create_user(
    db_session: Session,
    *,
    email: str = "existing@example.com",
    username: str = "existinguser",
) -> User:
    """Insert a user directly into the test database."""
    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(VALID_PAYLOAD["password"]),
    )
    db_session.add(user)
    db_session.flush()
    return user


def _assert_error_envelope(response: Response, status_code: int) -> None:
    """Assert the response uses the standardized error envelope."""
    assert response.status_code == status_code
    data = response.json()
    assert "type" in data
    assert "title" in data
    assert "status" in data
    assert "detail" in data
    assert data["status"] == status_code


def _assert_field_error(response: Response, field: str) -> None:
    """Assert a validation response contains a field-specific error."""
    _assert_error_envelope(response, 400)
    errors = response.json()["errors"]
    assert any(error["field"] == field for error in errors)


class TestRegisterSuccess:
    """Successful registration scenarios."""

    def test_returns_201_with_auth_response(
        self,
        test_client: TestClient,
    ) -> None:
        """Returns the token and user payload on success."""
        response = _register(test_client, _payload())

        assert response.status_code == 201
        data = response.json()
        assert set(data.keys()) == {"token", "user"}
        assert "access_token" in data["token"]
        assert data["token"]["token_type"] == "bearer"
        assert "expires_in" in data["token"]
        assert data["user"]["email"] == VALID_PAYLOAD["email"]
        assert data["user"]["username"] == VALID_PAYLOAD["username"]

    def test_returns_valid_decodable_jwt(
        self,
        test_client: TestClient,
    ) -> None:
        """Returns a JWT that can be decoded with the app secret."""
        response = _register(test_client, _payload())

        token = response.json()["token"]["access_token"]
        decoded = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
        )

        assert decoded["token_type"] == "access"
        assert "exp" in decoded
        assert "iat" in decoded
        assert "jti" in decoded

    def test_jwt_sub_matches_user_id(
        self,
        test_client: TestClient,
    ) -> None:
        """Sets the JWT subject claim to the created user ID."""
        response = _register(test_client, _payload())

        data = response.json()
        token = data["token"]["access_token"]
        decoded = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
        )

        assert decoded["sub"] == data["user"]["id"]
        assert UUID(decoded["sub"])

    def test_creates_user_in_database(
        self,
        test_client: TestClient,
        db_session: Session,
    ) -> None:
        """Persists the new user to the database."""
        response = _register(test_client, _payload())

        created_user = db_session.scalar(
            select(User).where(User.email == VALID_PAYLOAD["email"])
        )

        assert response.status_code == 201
        assert created_user is not None
        assert str(created_user.id) == response.json()["user"]["id"]

    def test_stores_argon2id_hash_not_plaintext(
        self,
        test_client: TestClient,
        db_session: Session,
    ) -> None:
        """Stores a hashed password instead of the plaintext password."""
        _register(test_client, _payload())

        created_user = db_session.scalar(
            select(User).where(User.email == VALID_PAYLOAD["email"])
        )

        assert created_user is not None
        assert created_user.hashed_password is not None
        assert created_user.hashed_password != VALID_PAYLOAD["password"]
        assert created_user.hashed_password.startswith("$argon2")
        is_valid, _ = verify_password(
            VALID_PAYLOAD["password"],
            created_user.hashed_password,
        )
        assert is_valid is True

    def test_password_not_in_response_body(
        self,
        test_client: TestClient,
    ) -> None:
        """Does not leak password fields in the response body."""
        response = _register(test_client, _payload())

        assert response.status_code == 201
        assert "password" not in response.text
        assert "hashed_password" not in response.text

    def test_user_is_active_by_default(
        self,
        test_client: TestClient,
    ) -> None:
        """Marks new users as active by default."""
        response = _register(test_client, _payload())

        assert response.status_code == 201
        assert response.json()["user"]["is_active"] is True

    def test_user_email_not_verified(
        self,
        test_client: TestClient,
    ) -> None:
        """Leaves email verification unset for new users."""
        response = _register(test_client, _payload())

        assert response.status_code == 201
        assert response.json()["user"]["email_verified_at"] is None

    def test_expires_in_matches_config(
        self,
        test_client: TestClient,
    ) -> None:
        """Returns the configured access token lifetime in seconds."""
        response = _register(test_client, _payload())

        assert response.status_code == 201
        assert response.json()["token"]["expires_in"] == (
            settings.access_token_expire_minutes * 60
        )


class TestRegisterValidation:
    """Validation failure scenarios."""

    def test_missing_email_returns_400(
        self,
        test_client: TestClient,
    ) -> None:
        """Returns 400 when email is missing."""
        payload = _payload()
        payload.pop("email")

        response = _register(test_client, payload)

        _assert_field_error(response, "email")

    def test_invalid_email_format_returns_400(
        self,
        test_client: TestClient,
    ) -> None:
        """Returns 400 for an invalid email address."""
        response = _register(test_client, _payload(email="invalid-email"))

        _assert_field_error(response, "email")

    def test_missing_username_returns_400(
        self,
        test_client: TestClient,
    ) -> None:
        """Returns 400 when username is missing."""
        payload = _payload()
        payload.pop("username")

        response = _register(test_client, payload)

        _assert_field_error(response, "username")

    def test_username_too_short_returns_400(
        self,
        test_client: TestClient,
    ) -> None:
        """Returns 400 when username is too short."""
        response = _register(test_client, _payload(username="ab"))

        _assert_field_error(response, "username")

    def test_username_invalid_chars_returns_400(
        self,
        test_client: TestClient,
    ) -> None:
        """Returns 400 when username contains invalid characters."""
        response = _register(test_client, _payload(username="Chef Mario!"))

        _assert_field_error(response, "username")

    def test_missing_password_returns_400(
        self,
        test_client: TestClient,
    ) -> None:
        """Returns 400 when password is missing."""
        payload = _payload()
        payload.pop("password")

        response = _register(test_client, payload)

        _assert_field_error(response, "password")

    def test_short_password_returns_400(
        self,
        test_client: TestClient,
    ) -> None:
        """Returns 400 when password is too short."""
        response = _register(test_client, _payload(password="Short1"))

        _assert_field_error(response, "password")

    def test_password_no_uppercase_returns_400(
        self,
        test_client: TestClient,
    ) -> None:
        """Returns 400 when password has no uppercase letter."""
        response = _register(
            test_client,
            _payload(
                password="securep@ss123",
                password_confirm="securep@ss123",
            ),
        )

        _assert_field_error(response, "password")

    def test_password_no_digit_returns_400(
        self,
        test_client: TestClient,
    ) -> None:
        """Returns 400 when password has no digit."""
        response = _register(
            test_client,
            _payload(
                password="SecurePassword",
                password_confirm="SecurePassword",
            ),
        )

        _assert_field_error(response, "password")

    def test_password_mismatch_returns_400(
        self,
        test_client: TestClient,
    ) -> None:
        """Returns 400 when password confirmation does not match."""
        response = _register(
            test_client,
            _payload(password_confirm="DifferentP@ss123"),
        )

        _assert_error_envelope(response, 400)
        errors = response.json()["errors"]
        assert any(error["field"] == "non_field_error" for error in errors)
        assert any(
            "Passwords do not match." in error["message"] for error in errors
        )

    def test_empty_body_returns_400(
        self,
        test_client: TestClient,
    ) -> None:
        """Returns 400 when the request body is empty."""
        response = _register(test_client, {})

        _assert_error_envelope(response, 400)
        errors = response.json()["errors"]
        error_fields = {error["field"] for error in errors}
        assert {"email", "username", "password", "password_confirm"} <= (
            error_fields
        )

    def test_error_response_uses_error_envelope(
        self,
        test_client: TestClient,
    ) -> None:
        """Uses the standardized error envelope for validation errors."""
        response = _register(test_client, _payload(email="not-an-email"))

        _assert_error_envelope(response, 400)


class TestRegisterDuplicate:
    """Duplicate user registration scenarios."""

    def test_duplicate_email_returns_409(
        self,
        test_client: TestClient,
        db_session: Session,
    ) -> None:
        """Returns 409 when email already exists."""
        _create_user(
            db_session,
            email=VALID_PAYLOAD["email"],
            username="otheruser",
        )

        response = _register(
            test_client,
            _payload(username="newusername"),
        )

        _assert_error_envelope(response, 409)
        assert "email" in response.json()["detail"].lower()

    def test_duplicate_email_case_insensitive_returns_409(
        self,
        test_client: TestClient,
        db_session: Session,
    ) -> None:
        """Returns 409 for case-insensitive duplicate emails."""
        _create_user(
            db_session,
            email=VALID_PAYLOAD["email"],
            username="otheruser",
        )

        response = _register(
            test_client,
            _payload(
                email="CHEF@EXAMPLE.COM",
                username="newusername",
            ),
        )

        _assert_error_envelope(response, 409)
        assert "email" in response.json()["detail"].lower()

    def test_duplicate_username_returns_409(
        self,
        test_client: TestClient,
        db_session: Session,
    ) -> None:
        """Returns 409 when username already exists."""
        _create_user(
            db_session,
            email="other@example.com",
            username=VALID_PAYLOAD["username"],
        )

        response = _register(
            test_client,
            _payload(email="fresh@example.com"),
        )

        _assert_error_envelope(response, 409)
        assert "username" in response.json()["detail"].lower()

    def test_duplicate_username_case_insensitive_returns_409(
        self,
        test_client: TestClient,
        db_session: Session,
    ) -> None:
        """Returns 409 for case-insensitive duplicate usernames."""
        _create_user(
            db_session,
            email="other@example.com",
            username=VALID_PAYLOAD["username"],
        )

        response = _register(
            test_client,
            _payload(
                email="fresh@example.com",
                username="ChefMario",
            ),
        )

        _assert_error_envelope(response, 409)
        assert "username" in response.json()["detail"].lower()

    def test_409_response_uses_error_envelope(
        self,
        test_client: TestClient,
        db_session: Session,
    ) -> None:
        """Uses the standardized error envelope for conflicts."""
        _create_user(
            db_session,
            email=VALID_PAYLOAD["email"],
            username="otheruser",
        )

        response = _register(
            test_client,
            _payload(username="newusername"),
        )

        _assert_error_envelope(response, 409)


class TestRegisterEdgeCases:
    """Edge-case registration scenarios."""

    def test_email_plus_addressing_succeeds(
        self,
        test_client: TestClient,
    ) -> None:
        """Accepts valid plus-addressed email aliases."""
        response = _register(
            test_client,
            _payload(
                email="chef+newsletter@example.com",
                username="pluschef",
            ),
        )

        assert response.status_code == 201
        assert response.json()["user"]["email"] == (
            "chef+newsletter@example.com"
        )

    def test_reserved_username_returns_400(
        self,
        test_client: TestClient,
    ) -> None:
        """Rejects reserved usernames like admin."""
        response = _register(test_client, _payload(username="admin"))

        _assert_field_error(response, "username")

    def test_extra_fields_in_body_ignored(
        self,
        test_client: TestClient,
    ) -> None:
        """Ignores extra request fields not defined in the schema."""
        response = _register(
            test_client,
            _payload(favorite_dish="lasagna"),
        )

        assert response.status_code == 201
        assert "favorite_dish" not in response.json()["user"]
        assert "favorite_dish" not in response.json()["token"]

    def test_leading_trailing_whitespace_trimmed(
        self,
        test_client: TestClient,
    ) -> None:
        """Normalizes surrounding whitespace in email and username."""
        response = _register(
            test_client,
            _payload(
                email="  CHEF@EXAMPLE.COM  ",
                username="  ChefMario  ",
            ),
        )

        assert response.status_code == 201
        assert response.json()["user"]["email"] == VALID_PAYLOAD["email"]
        assert response.json()["user"]["username"] == VALID_PAYLOAD["username"]


class TestRegisterOpenAPI:
    """OpenAPI documentation scenarios for registration."""

    def test_openapi_preserves_description_and_register_responses(
        self,
        test_client: TestClient,
    ) -> None:
        """Documents register responses without dropping app metadata."""
        response = test_client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        register_post = data["paths"][REGISTER_URL]["post"]

        assert data["info"]["description"] == (
            "AI-powered cooking assistant and recipe creation platform"
        )
        assert set(register_post["responses"]) == {"201", "400", "409"}
        assert register_post["responses"]["400"]["content"]["application/json"][
            "schema"
        ] == {
            "$ref": "#/components/schemas/ErrorResponse",
        }
        schemas = data["components"]["schemas"]
        assert "HTTPValidationError" not in schemas
        assert "ValidationError" not in schemas

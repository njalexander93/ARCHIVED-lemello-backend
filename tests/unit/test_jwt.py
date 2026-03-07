"""Unit tests for JWT token generation and verification.

Tests cover the nine essential JWT verification scenarios:
1. Round-trip encode/decode
2. Expired token rejection
3. Tampered token rejection
4. Wrong signing key rejection
5. Malformed token rejection
6. Missing required claims rejection
7. Future nbf rejection
8. Wrong token type rejection
9. Token payload schema validation
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest
import time_machine

from app.core.config import settings
from app.core.security import create_access_token, verify_token
from app.schemas.auth import TokenPayload

pytestmark = pytest.mark.unit


@pytest.fixture
def sample_user_id() -> uuid.UUID:
    """Return a stable UUIDv7 value for testing."""
    return uuid.UUID("01936e40-7b9a-7123-8456-789abcdef012")


@pytest.fixture
def token_factory() -> Callable[..., str]:
    """Create JWT tokens with customizable claims.

    Returns:
        Callable that produces encoded JWT strings for test scenarios.
    """

    def _create(
        sub: str = "01936e40-7b9a-7123-8456-789abcdef012",
        token_type: str = "access",
        expires_delta: timedelta | None = None,
        extra_claims: dict[str, object] | None = None,
        secret: str | None = None,
        algorithm: str = "HS256",
        exclude_claims: list[str] | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        payload: dict[str, object] = {
            "sub": sub,
            "token_type": token_type,
            "iat": now,
            "exp": now + (expires_delta or timedelta(minutes=30)),
            "jti": str(uuid.uuid4()),
        }
        if extra_claims:
            payload.update(extra_claims)
        if exclude_claims:
            for claim in exclude_claims:
                payload.pop(claim, None)
        return pyjwt.encode(
            payload,
            secret or settings.secret_key,
            algorithm=algorithm,
        )

    return _create


class TestCreateAccessToken:
    """Tests for create_access_token()."""

    def test_creates_valid_token(self, sample_user_id: uuid.UUID) -> None:
        """Token can be created and verified in a round-trip."""
        token = create_access_token(user_id=sample_user_id)
        payload = verify_token(token)

        assert isinstance(payload, TokenPayload)
        assert payload.sub == str(sample_user_id)
        assert payload.token_type == "access"
        assert payload.jti is not None

    def test_uses_default_expiration(self, sample_user_id: uuid.UUID) -> None:
        """Token expiration matches settings.access_token_expire_minutes."""
        now = datetime.now(timezone.utc)
        token = create_access_token(user_id=sample_user_id)
        payload = verify_token(token)

        expected_exp = now + timedelta(
            minutes=settings.access_token_expire_minutes
        )
        assert abs(payload.exp - int(expected_exp.timestamp())) < 5

    def test_custom_expiration(self, sample_user_id: uuid.UUID) -> None:
        """Custom expires_delta overrides the default."""
        delta = timedelta(minutes=5)
        now = datetime.now(timezone.utc)
        token = create_access_token(user_id=sample_user_id, expires_delta=delta)
        payload = verify_token(token)

        expected_exp = now + delta
        assert abs(payload.exp - int(expected_exp.timestamp())) < 5

    def test_unique_jti_per_token(self, sample_user_id: uuid.UUID) -> None:
        """Each token gets a unique jti."""
        token1 = create_access_token(user_id=sample_user_id)
        token2 = create_access_token(user_id=sample_user_id)

        payload1 = verify_token(token1)
        payload2 = verify_token(token2)

        assert payload1.jti != payload2.jti


class TestExpiredToken:
    """Tests for expired token handling."""

    def test_expired_token_raises(
        self, token_factory: Callable[..., str]
    ) -> None:
        """Token past its exp is rejected with ExpiredSignatureError."""
        token = token_factory(expires_delta=timedelta(minutes=-5))

        with pytest.raises(pyjwt.exceptions.ExpiredSignatureError):
            verify_token(token)

    @time_machine.travel("2026-03-06T12:00:00+00:00", tick=False)
    def test_token_expires_after_lifetime(
        self, sample_user_id: uuid.UUID
    ) -> None:
        """Token created at T is valid at issuance time."""
        token = create_access_token(
            user_id=sample_user_id,
            expires_delta=timedelta(minutes=5),
        )

        payload = verify_token(token)
        assert payload.sub == str(sample_user_id)

    @time_machine.travel("2026-03-06T12:06:00+00:00", tick=False)
    def test_token_expired_after_travel(
        self,
        sample_user_id: uuid.UUID,
    ) -> None:
        """Token created for 12:00 with 5-minute expiry fails at 12:06."""
        token = token_factory_at_fixed_time(sample_user_id)

        with pytest.raises(pyjwt.exceptions.ExpiredSignatureError):
            verify_token(token)


def token_factory_at_fixed_time(user_id: uuid.UUID) -> str:
    """Create a token as if issued at 2026-03-06 12:00:00 UTC.

    Args:
        user_id: User identifier to place in the `sub` claim.

    Returns:
        Encoded JWT string with 5-minute expiration.
    """
    issued_at = datetime(2026, 3, 6, 12, 0, 0, tzinfo=timezone.utc)
    payload: dict[str, object] = {
        "sub": str(user_id),
        "exp": issued_at + timedelta(minutes=5),
        "iat": issued_at,
        "jti": str(uuid.uuid4()),
        "token_type": "access",
    }
    return pyjwt.encode(payload, settings.secret_key, algorithm="HS256")


class TestTamperedToken:
    """Tests for token integrity."""

    def test_modified_payload_rejected(
        self,
        token_factory: Callable[..., str],
    ) -> None:
        """Modifying payload content invalidates the signature."""
        token = token_factory()
        parts = token.split(".")
        payload_chars = list(parts[1])
        payload_index = len(payload_chars) // 2
        payload_chars[payload_index] = (
            "A" if payload_chars[payload_index] != "A" else "B"
        )
        tampered_payload = "".join(payload_chars)
        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"

        with pytest.raises(
            (
                pyjwt.exceptions.InvalidSignatureError,
                pyjwt.exceptions.DecodeError,
            )
        ):
            verify_token(tampered_token)

    def test_modified_signature_rejected(
        self,
        token_factory: Callable[..., str],
    ) -> None:
        """Modifying signature content is rejected."""
        token = token_factory()
        parts = token.split(".")
        signature_chars = list(parts[2])
        signature_index = len(signature_chars) // 2
        signature_chars[signature_index] = (
            "A" if signature_chars[signature_index] != "A" else "B"
        )
        tampered_sig = "".join(signature_chars)
        tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"

        with pytest.raises(
            (
                pyjwt.exceptions.InvalidSignatureError,
                pyjwt.exceptions.DecodeError,
            )
        ):
            verify_token(tampered_token)


class TestWrongKey:
    """Tests for key validation."""

    def test_wrong_key_rejected(
        self, token_factory: Callable[..., str]
    ) -> None:
        """Token signed with a different key is rejected."""
        token = token_factory(
            secret="completely-different-secret-key-that-is-long-enough-for-hs256"
        )

        with pytest.raises(
            (
                pyjwt.exceptions.InvalidSignatureError,
                pyjwt.exceptions.DecodeError,
            )
        ):
            verify_token(token)


class TestMalformedToken:
    """Tests for structurally invalid tokens."""

    @pytest.mark.parametrize(
        "bad_token",
        [
            "",
            "not-a-jwt",
            "only.two.parts.but.extra",
            "a.b.c",
            "eyJhbGciOiJIUzI1NiJ9",
            "definitely not base64 encoded at all!!!",
        ],
        ids=[
            "empty_string",
            "random_string",
            "too_many_parts",
            "three_random_parts",
            "header_only",
            "garbage_input",
        ],
    )
    def test_malformed_tokens_rejected(self, bad_token: str) -> None:
        """Malformed token inputs are rejected."""
        with pytest.raises(
            (pyjwt.exceptions.DecodeError, pyjwt.exceptions.InvalidTokenError)
        ):
            verify_token(bad_token)


class TestMissingClaims:
    """Tests for missing required JWT claims."""

    def test_missing_sub_rejected(
        self, token_factory: Callable[..., str]
    ) -> None:
        """Token without `sub` claim is rejected."""
        token = token_factory(exclude_claims=["sub"])

        with pytest.raises(pyjwt.exceptions.MissingRequiredClaimError):
            verify_token(token)

    def test_missing_exp_rejected(
        self, token_factory: Callable[..., str]
    ) -> None:
        """Token without `exp` claim is rejected."""
        token = token_factory(exclude_claims=["exp"])

        with pytest.raises(pyjwt.exceptions.MissingRequiredClaimError):
            verify_token(token)

    def test_missing_iat_rejected(
        self, token_factory: Callable[..., str]
    ) -> None:
        """Token without `iat` claim is rejected."""
        token = token_factory(exclude_claims=["iat"])

        with pytest.raises(pyjwt.exceptions.MissingRequiredClaimError):
            verify_token(token)


class TestFutureNbf:
    """Tests for not-before claim handling."""

    def test_future_nbf_rejected(
        self, token_factory: Callable[..., str]
    ) -> None:
        """Token with future `nbf` is rejected."""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        token = token_factory(extra_claims={"nbf": future})

        with pytest.raises(pyjwt.exceptions.ImmatureSignatureError):
            verify_token(token)


class TestTokenType:
    """Tests for token_type validation."""

    def test_refresh_token_type_rejected(
        self,
        token_factory: Callable[..., str],
    ) -> None:
        """A token with token_type='refresh' is rejected by verify_token()."""
        token = token_factory(token_type="refresh")

        with pytest.raises(
            pyjwt.exceptions.InvalidTokenError,
            match="Invalid token type",
        ):
            verify_token(token)

    def test_unknown_token_type_rejected(
        self,
        token_factory: Callable[..., str],
    ) -> None:
        """A token with an unrecognized token_type is rejected."""
        token = token_factory(token_type="unknown")

        with pytest.raises(
            pyjwt.exceptions.InvalidTokenError,
            match="Invalid token type",
        ):
            verify_token(token)


class TestTokenPayload:
    """Tests for the TokenPayload Pydantic model."""

    def test_valid_payload(self) -> None:
        """TokenPayload accepts valid data."""
        data = TokenPayload(
            sub="01936e40-7b9a-7123-8456-789abcdef012",
            exp=1709726400,
            iat=1709722800,
            jti="550e8400-e29b-41d4-a716-446655440000",
            token_type="access",
        )

        assert data.sub == "01936e40-7b9a-7123-8456-789abcdef012"

    def test_defaults(self) -> None:
        """TokenPayload uses expected defaults."""
        data = TokenPayload(sub="test", exp=999, iat=999)

        assert data.jti is None
        assert data.token_type == "access"

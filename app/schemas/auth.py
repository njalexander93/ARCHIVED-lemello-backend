"""Authentication schemas for JWT token handling."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TokenPayload(BaseModel):
    """Validated JWT token payload.

    Attributes:
        sub: User ID as UUIDv7 string.
        exp: Expiration timestamp (UNIX epoch).
        iat: Issued-at timestamp (UNIX epoch).
        jti: Unique token identifier (UUID4 string). Optional for backward
            compatibility.
        token_type: Token type discriminator. Defaults to "access".
    """

    model_config = ConfigDict(strict=True)

    sub: str
    exp: int
    iat: int
    jti: str | None = None
    token_type: str = "access"


class TokenResponse(BaseModel):
    """Response schema for login/token endpoints.

    Attributes:
        access_token: The encoded JWT string.
        token_type: Always "bearer" per OAuth2 spec.
    """

    access_token: str
    token_type: str = "bearer"

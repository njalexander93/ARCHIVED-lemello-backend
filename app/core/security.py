"""Password hashing and verification using Argon2id.

Uses pwdlib with Argon2id as the primary hasher (OWASP 2025
recommendation) and bcrypt as a legacy fallback. The
verify_and_update pattern enables transparent algorithm
migration: if a user logs in with a bcrypt hash, it is
automatically re-hashed to Argon2id.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import HasherNotAvailable
from pwdlib.hashers.argon2 import Argon2Hasher
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.auth import TokenPayload

BcryptHasherType: type[Any] | None
try:
    from pwdlib.hashers.bcrypt import BcryptHasher as _BcryptHasher
except HasherNotAvailable:
    BcryptHasherType = None
else:
    BcryptHasherType = _BcryptHasher

# Argon2id via pwdlib defaults (no explicit parameter overrides).
# We intentionally avoid hardcoding Argon2 tuning here so behavior
# tracks the library's recommended defaults and can evolve safely.
hashers: list[Any] = [Argon2Hasher()]
if BcryptHasherType is not None:
    hashers.append(BcryptHasherType())
_password_hash = PasswordHash(tuple(hashers))


def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2id.

    Args:
        password: The plaintext password to hash.

    Returns:
        The Argon2id hash string.
    """
    return _password_hash.hash(password)


def verify_password(password: str, hashed: str) -> tuple[bool, str | None]:
    """Verify a password against a stored hash.

    If the hash uses a legacy algorithm (bcrypt), the password
    is re-hashed with Argon2id and the new hash is returned.
    The caller is responsible for persisting the updated hash.

    Args:
        password: The plaintext password to verify.
        hashed: The stored hash to verify against.

    Returns:
        A tuple of (is_valid, updated_hash). updated_hash is
        None if no rehash is needed, or a new Argon2id hash
        string if the password was verified against a legacy
        algorithm.
    """
    return _password_hash.verify_and_update(password, hashed)


def create_access_token(
    user_id: uuid.UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        user_id: The user's UUIDv7 primary key.
        expires_delta: Optional custom expiration. Defaults to
            settings.access_token_expire_minutes. Values that are
            non-positive or exceed the configured maximum are clamped
            to the configured maximum.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    max_expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    if expires_delta is None or expires_delta <= timedelta(0):
        effective_expires_delta = max_expires_delta
    elif expires_delta > max_expires_delta:
        effective_expires_delta = max_expires_delta
    else:
        effective_expires_delta = expires_delta

    expire = now + effective_expires_delta

    payload: dict[str, str | datetime] = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "token_type": "access",
    }

    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def verify_token(token: str) -> TokenPayload:
    """Decode and validate a JWT access token.

    Args:
        token: The raw JWT string from the Authorization header.

    Returns:
        Validated TokenPayload with extracted claims.

    Raises:
        jwt.exceptions.ExpiredSignatureError: Token has expired.
        jwt.exceptions.DecodeError: Token is malformed or has an invalid
            signature.
        jwt.exceptions.InvalidTokenError: Token fails any other validation.
    """
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=["HS256"],
        options={"require": ["sub", "exp", "iat"]},
        leeway=timedelta(seconds=30),
    )

    try:
        token_data = TokenPayload(**payload)
    except ValidationError as exc:
        raise InvalidTokenError("Invalid token payload") from exc

    if token_data.token_type != "access":
        raise InvalidTokenError("Invalid token type")

    return token_data

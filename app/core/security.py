"""Password hashing and verification using Argon2id.

Uses pwdlib with Argon2id as the primary hasher (OWASP 2025
recommendation) and bcrypt as a legacy fallback. The
verify_and_update pattern enables transparent algorithm
migration: if a user logs in with a bcrypt hash, it is
automatically re-hashed to Argon2id.
"""

from typing import Any

from pwdlib import PasswordHash
from pwdlib.exceptions import HasherNotAvailable
from pwdlib.hashers.argon2 import Argon2Hasher

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

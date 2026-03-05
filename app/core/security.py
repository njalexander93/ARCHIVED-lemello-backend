"""Password hashing and verification using Argon2id.

Uses pwdlib with Argon2id as the primary hasher (OWASP 2025
recommendation) and bcrypt as a legacy fallback. The
verify_and_update pattern enables transparent algorithm
migration: if a user logs in with a bcrypt hash, it is
automatically re-hashed to Argon2id.
"""

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

# Argon2id with RFC 9106 LOW_MEMORY profile:
# 64 MiB memory, 3 iterations, 4 parallelism threads.
# Suitable for 1 GB RAM DigitalOcean App Platform containers.
# Each concurrent hash operation uses ~64 MiB.
_password_hash = PasswordHash(
    (
        Argon2Hasher(),
        BcryptHasher(),
    )
)


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

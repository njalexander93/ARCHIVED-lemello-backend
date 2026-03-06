"""Unit tests for password security helpers."""

import pytest
from pwdlib import PasswordHash
from pwdlib.exceptions import HasherNotAvailable

from app.core.security import hash_password, verify_password

pytestmark = pytest.mark.unit


def test_hash_produces_argon2id_prefix() -> None:
    """Hashes are generated using Argon2id."""
    hashed = hash_password("TestPass1")
    assert hashed.startswith("$argon2id$")


def test_verify_correct_password() -> None:
    """Correct password verification succeeds without rehash."""
    hashed = hash_password("TestPass1")

    is_valid, updated_hash = verify_password("TestPass1", hashed)

    assert is_valid is True
    assert updated_hash is None


def test_verify_wrong_password() -> None:
    """Wrong password verification fails."""
    hashed = hash_password("TestPass1")

    is_valid, updated_hash = verify_password("WrongPass1", hashed)

    assert is_valid is False
    assert updated_hash is None


def test_same_password_produces_different_hashes() -> None:
    """Argon2 salts produce different hashes for identical input."""
    first = hash_password("TestPass1")
    second = hash_password("TestPass1")

    assert first != second


def test_hash_does_not_contain_plaintext() -> None:
    """Hash output does not contain the input plaintext password."""
    password = "TestPass1"
    hashed = hash_password(password)

    assert password not in hashed


def test_verify_rehashes_legacy_bcrypt_hash() -> None:
    """Valid bcrypt hashes are verified and upgraded to Argon2id."""
    try:
        from pwdlib.hashers.bcrypt import BcryptHasher
    except HasherNotAvailable:
        pytest.skip("bcrypt backend not available in this environment")

    legacy_hasher = PasswordHash((BcryptHasher(),))
    legacy_hash = legacy_hasher.hash("LegacyPass1")

    is_valid, updated_hash = verify_password("LegacyPass1", legacy_hash)

    assert is_valid is True
    assert updated_hash is not None
    assert updated_hash.startswith("$argon2id$")

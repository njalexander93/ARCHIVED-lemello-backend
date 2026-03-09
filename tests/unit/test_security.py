"""Unit tests for password security helpers."""

import pytest
from pwdlib import PasswordHash
from pwdlib.exceptions import HasherNotAvailable
from pydantic import ValidationError

from app.core.config import settings
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


class TestArgon2idConfiguration:
    """Unit tests for configurable Argon2id hashing behavior."""

    def test_hash_uses_configured_parameters(self) -> None:
        """New hashes encode the configured Argon2id parameters."""
        hashed = hash_password("TestPass1")

        parts = hashed.split("$")
        assert parts[1] == "argon2id"

        param_str = parts[3]
        params = dict(item.split("=") for item in param_str.split(","))

        assert int(params["m"]) == settings.argon2_memory_cost
        assert int(params["t"]) == settings.argon2_time_cost
        assert int(params["p"]) == settings.argon2_parallelism

    def test_argon2_memory_cost_below_owasp_minimum_rejected(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Settings rejects argon2_memory_cost below OWASP floor."""
        from app.core.config import Settings

        del monkeypatch

        with pytest.raises(ValidationError, match="7168"):
            Settings(
                ARGON2_MEMORY_COST=1024,
                SECRET_KEY="a" * 32 + "b",
            )

    def test_argon2_time_cost_zero_rejected(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Settings rejects argon2_time_cost below 1."""
        from app.core.config import Settings

        del monkeypatch

        with pytest.raises(ValidationError, match="ARGON2_TIME_COST"):
            Settings(
                ARGON2_TIME_COST=0,
                SECRET_KEY="a" * 32 + "b",
            )

    def test_argon2_parallelism_zero_rejected(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Settings rejects argon2_parallelism below 1."""
        from app.core.config import Settings

        del monkeypatch

        with pytest.raises(ValidationError, match="ARGON2_PARALLELISM"):
            Settings(
                ARGON2_PARALLELISM=0,
                SECRET_KEY="a" * 32 + "b",
            )

    def test_verify_rejects_malformed_hash(self) -> None:
        """verify_password raises on completely invalid hash strings."""
        from pwdlib.exceptions import UnknownHashError

        with pytest.raises(UnknownHashError):
            verify_password("TestPass1", "not-a-valid-hash")

    def test_hash_empty_password(self) -> None:
        """Empty string can be hashed (length validation is Pydantic's job)."""
        hashed = hash_password("")
        assert hashed.startswith("$argon2id$")

        is_valid, _ = verify_password("", hashed)
        assert is_valid is True

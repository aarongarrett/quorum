"""Unit tests for security functions."""
import pytest
from app.core.security import (
    generate_vote_token,
    create_token_lookup_key,
    create_access_token,
    verify_admin_password,
)


@pytest.mark.unit
class TestTokenGeneration:
    """Test vote token generation and hashing."""

    def test_generate_vote_token_length(self):
        """Token should be URL-safe and of expected length."""
        token = generate_vote_token()
        assert isinstance(token, str)
        assert len(token) > 40  # 32 bytes base64 encoded

    def test_generate_vote_token_uniqueness(self):
        """Each generated token should be unique."""
        tokens = [generate_vote_token() for _ in range(1000)]
        assert len(set(tokens)) == 1000

    def test_create_token_lookup_key(self):
        """Token lookup key should be deterministic HMAC-SHA256."""
        token = generate_vote_token()
        key1 = create_token_lookup_key(token)
        key2 = create_token_lookup_key(token)

        # Should be deterministic (same token = same key)
        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 64  # SHA256 hex output
        assert token != key1

    def test_create_token_lookup_key_different_tokens(self):
        """Different tokens should produce different lookup keys."""
        token1 = generate_vote_token()
        token2 = generate_vote_token()
        key1 = create_token_lookup_key(token1)
        key2 = create_token_lookup_key(token2)

        assert key1 != key2


@pytest.mark.unit
class TestJWT:
    """Test JWT token creation."""

    def test_create_access_token(self):
        """Should create valid JWT token."""
        token = create_access_token({"sub": "admin"})

        assert isinstance(token, str)
        assert len(token) > 20
        # JWT format: header.payload.signature
        assert token.count(".") == 2


@pytest.mark.unit
class TestAdminAuth:
    """Test admin password verification."""

    def test_verify_admin_password_valid(self, monkeypatch):
        """Valid password should return True."""
        monkeypatch.setenv("ADMIN_PASSWORD", "testpass123")

        # Need to reload config after monkeypatch
        from app.core import config
        config.settings = config.Settings()

        assert verify_admin_password("testpass123") is True

    def test_verify_admin_password_invalid(self, monkeypatch):
        """Invalid password should return False."""
        monkeypatch.setenv("ADMIN_PASSWORD", "testpass123")

        from app.core import config
        config.settings = config.Settings()

        assert verify_admin_password("wrongpassword") is False

    def test_verify_admin_password_hashed_valid(self, monkeypatch):
        """Valid hashed password should return True."""
        # Hash "testpass123" using Argon2
        from app.core.security import get_password_hash
        hashed = get_password_hash("testpass123")

        monkeypatch.setenv("ADMIN_PASSWORD", hashed)

        from app.core import config
        config.settings = config.Settings()

        assert verify_admin_password("testpass123") is True

    def test_verify_admin_password_hashed_invalid(self, monkeypatch):
        """Invalid hashed password should return False."""
        # Hash "testpass123" using Argon2
        from app.core.security import get_password_hash
        hashed = get_password_hash("testpass123")

        monkeypatch.setenv("ADMIN_PASSWORD", hashed)

        from app.core import config
        config.settings = config.Settings()

        assert verify_admin_password("wrongpassword") is False

    def test_verify_admin_password_dual_mode_detection(self, monkeypatch):
        """Test that password verification correctly detects and handles both modes."""
        from app.core.security import get_password_hash

        # Test Mode 1: Plaintext password (no $argon2 prefix)
        monkeypatch.setenv("ADMIN_PASSWORD", "plaintext_password")
        from app.core import config
        config.settings = config.Settings()

        # Should use plaintext comparison
        assert verify_admin_password("plaintext_password") is True
        assert verify_admin_password("wrong") is False

        # Test Mode 2: Hashed password (with $argon2 prefix)
        hashed = get_password_hash("secure_password")
        assert hashed.startswith("$argon2"), "Hashed password should start with $argon2"

        monkeypatch.setenv("ADMIN_PASSWORD", hashed)
        config.settings = config.Settings()

        # Should use Argon2 verification
        assert verify_admin_password("secure_password") is True
        assert verify_admin_password("wrong") is False

    def test_verify_admin_password_plaintext_not_treated_as_hash(self, monkeypatch):
        """Test that plaintext passwords without $argon2 prefix aren't treated as hashes."""
        # Set a password that doesn't start with $argon2
        monkeypatch.setenv("ADMIN_PASSWORD", "simple_pass_123")

        from app.core import config
        config.settings = config.Settings()

        # Should use direct comparison, not Argon2 verification
        # The exact string must match for plaintext
        assert verify_admin_password("simple_pass_123") is True
        assert verify_admin_password("simple_pass_12") is False
        assert verify_admin_password("simple_pass_1234") is False

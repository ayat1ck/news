"""Unit tests for core security functions."""

from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password


def test_password_hashing():
    """Test password hash and verify roundtrip."""
    plain = "my_secure_password"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("wrong_password", hashed)


def test_access_token_creation():
    """Test JWT access token creation and decoding."""
    token = create_access_token({"sub": "42"})
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["type"] == "access"


def test_refresh_token_creation():
    """Test JWT refresh token creation and decoding."""
    token = create_refresh_token({"sub": "42"})
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["type"] == "refresh"


def test_invalid_token():
    """Test that invalid tokens return None."""
    assert decode_token("invalid.jwt.token") is None
    assert decode_token("") is None

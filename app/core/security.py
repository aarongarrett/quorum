"""Security and authentication utilities."""
import secrets
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
import argon2
import jwt
from fastapi import HTTPException, Request

from app.core import config

# Argon2 hasher for vote tokens
ph = argon2.PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=1,
    hash_len=32,
    salt_len=16
)


def generate_vote_token() -> str:
    """Generate a secure random vote token."""
    return secrets.token_urlsafe(32)


def get_password_hash(password: str) -> str:
    """Hash a password using Argon2.

    Can be used for any password (vote tokens, admin passwords, etc.).
    """
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its Argon2 hash.

    Can be used for any password (vote tokens, admin passwords, etc.).
    """
    try:
        ph.verify(password_hash, password)
        return True
    except argon2.exceptions.VerifyMismatchError:
        return False


def create_token_lookup_key(token: str) -> str:
    """Create deterministic lookup key from token using HMAC-SHA256.

    This provides O(1) database lookups for token verification instead of O(n).
    HMAC is appropriate here because tokens are:
    - Randomly generated (not user-chosen)
    - Single-use session identifiers
    - Already cryptographically secure (32+ bytes)

    Returns:
        64-character hex string (SHA256 output)
    """
    return hmac.new(
        config.settings.SECRET_KEY.encode(),
        token.encode(),
        hashlib.sha256
    ).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.settings.SECRET_KEY, algorithm=config.settings.ALGORITHM)
    return encoded_jwt


def verify_admin_token(request: Request) -> dict:
    """Verify JWT token from cookie and return payload."""
    token = request.cookies.get("admin_token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token, config.settings.SECRET_KEY, algorithms=[config.settings.ALGORITHM])
        if not payload.get("is_admin"):
            raise HTTPException(status_code=403, detail="Not authorized")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def verify_admin_password(password: str) -> bool:
    """Verify admin password using Argon2.

    Supports both hashed passwords (starting with $argon2) and plaintext.
    If ADMIN_PASSWORD is hashed (recommended), verifies using Argon2.
    If ADMIN_PASSWORD is plaintext (legacy/dev), does direct comparison.

    To hash a password for production, run:
        python -c "from app.core.security import get_password_hash; print(get_password_hash('your-password'))"
    """
    stored_password = config.settings.ADMIN_PASSWORD

    # Check if stored password is already an Argon2 hash
    if stored_password.startswith("$argon2"):
        # Stored password is hashed, verify against it using Argon2
        return verify_password(password, stored_password)
    else:
        # Stored password is plaintext (legacy/dev mode)
        # Simple comparison - consider using hashed passwords in production
        return password == stored_password

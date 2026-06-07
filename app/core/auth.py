"""Authentication utilities: JWT, password hashing, FastAPI dependency.

Provides:
  - create_access_token / verify_token — JWT sign/verify
  - hash_password / verify_password — passlib bcrypt
  - get_current_user — FastAPI Depends that returns user dict or raises 401/403
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from loguru import logger
from passlib.context import CryptContext

from app.config import config

# ── Password hashing ──

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return _pwd_ctx.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return _pwd_ctx.verify(plain_password, hashed_password)


# ── JWT ──

# Module-level cache for auto-generated secret
_auto_secret: str | None = None


def _get_jwt_secret() -> str:
    """Return configured secret or a cached auto-generated one."""
    global _auto_secret
    if config.auth_jwt_secret:
        return config.auth_jwt_secret
    if _auto_secret is None:
        _auto_secret = secrets.token_urlsafe(32)
        logger.warning("auth_jwt_secret not set — using auto-generated secret (invalid after restart)")
    return _auto_secret


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        data: Claims to embed (must include at least "sub").
        expires_delta: Token lifetime.  Defaults to config value (24h).

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=config.auth_access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    secret = _get_jwt_secret()
    return jwt.encode(to_encode, secret, algorithm=config.auth_jwt_algorithm)


def verify_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token.

    Returns:
        Payload dict on success, None on any failure (expired, bad sig, etc.).
    """
    try:
        secret = _get_jwt_secret()
        payload = jwt.decode(
            token, secret, algorithms=[config.auth_jwt_algorithm]
        )
        return payload
    except JWTError as exc:
        logger.debug(f"JWT verify failed: {exc}")
        return None


# ── FastAPI dependency ──

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    """FastAPI dependency: extract and validate current user from Bearer token.

    Returns:
        User dict from DataStore (must contain id, username, role, is_active).

    Raises:
        401 — missing / invalid / expired token
        403 — user is disabled
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id: str = payload.get("sub", "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    # Fetch user from DataStore
    from app.main import get_datastore  # defer to avoid circular import

    ds = get_datastore()
    if ds is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DataStore not initialized",
        )

    user = await ds.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is disabled",
        )

    return user

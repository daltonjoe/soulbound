# astro_integration/core/auth.py 
from __future__ import annotations 
 
import os 
import threading
import time
from datetime import datetime, timedelta

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import requests
 
_SECRET = os.getenv("JWT_SECRET", "change-me-in-production") 
_ALGORITHM = "HS256" 
_TOKEN_EXPIRE_DAYS = 365  # Mobil uygulama — uzun ömürlü token 
_SUPABASE_ALGORITHM = "ES256"
_JWKS_CACHE_TTL_SECONDS = 600
_JWKS_CACHE: tuple[float, dict[str, dict]] | None = None
_JWKS_LOCK = threading.Lock()
 
security = HTTPBearer() 
 
 
def create_app_token() -> str: 
    """Uygulama başlangıcında Flutter'a verilecek token.""" 
    payload = { 
        "sub": "soulbound-app", 
        "exp": datetime.utcnow() + timedelta(days=_TOKEN_EXPIRE_DAYS), 
    } 
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM) 
 
 
def verify_token( 
    credentials: HTTPAuthorizationCredentials = Security(security), 
) -> None: 
    """Her korumalı endpoint'te çalışır. Geçersiz token → 401.""" 
    try: 
        jwt.decode(credentials.credentials, _SECRET, algorithms=[_ALGORITHM]) 
    except JWTError: 
        raise HTTPException( 
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Geçersiz veya süresi dolmuş token.", 
            headers={"WWW-Authenticate": "Bearer"}, 
        )


def get_user_id(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """Return the authenticated Supabase user's UUID from the JWT subject."""
    try:
        token = credentials.credentials
        header = jwt.get_unverified_header(token)
        if header.get("alg") != _SUPABASE_ALGORITHM or not header.get("kid"):
            raise JWTError("Unsupported JWT header")

        supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        if not supabase_url:
            raise JWTError("SUPABASE_URL is not configured")

        jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
        issuer = f"{supabase_url}/auth/v1"
        keys = _get_jwks(jwks_url)
        key = keys.get(header["kid"])
        if key is None:
            keys = _get_jwks(jwks_url, force_refresh=True)
            key = keys.get(header["kid"])
        if key is None:
            raise JWTError("JWT signing key was not found")

        payload = jwt.decode(
            token,
            key,
            algorithms=[_SUPABASE_ALGORITHM],
            audience="authenticated",
            issuer=issuer,
        )
        user_id = payload.get("sub")
        if not user_id:
            raise JWTError("JWT subject is missing")
        return user_id
    except (JWTError, requests.RequestException, ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _get_jwks(jwks_url: str, force_refresh: bool = False) -> dict[str, dict]:
    global _JWKS_CACHE

    now = time.monotonic()
    if not force_refresh and _JWKS_CACHE is not None:
        expires_at, keys = _JWKS_CACHE
        if now < expires_at:
            return keys

    with _JWKS_LOCK:
        now = time.monotonic()
        if not force_refresh and _JWKS_CACHE is not None:
            expires_at, keys = _JWKS_CACHE
            if now < expires_at:
                return keys

        response = requests.get(jwks_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        raw_keys = data.get("keys")
        if not isinstance(raw_keys, list):
            raise ValueError("Invalid JWKS response")
        keys = {
            key["kid"]: key
            for key in raw_keys
            if isinstance(key, dict) and isinstance(key.get("kid"), str)
        }
        if not keys:
            raise ValueError("JWKS contains no signing keys")

        _JWKS_CACHE = (now + _JWKS_CACHE_TTL_SECONDS, keys)
        return keys

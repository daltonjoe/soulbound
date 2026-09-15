# astro_integration/core/auth.py 
from __future__ import annotations 
 
import os 
from datetime import datetime, timedelta 
 
from fastapi import HTTPException, Security, status 
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials 
from jose import JWTError, jwt 
 
_SECRET = os.getenv("JWT_SECRET", "change-me-in-production") 
_ALGORITHM = "HS256" 
_TOKEN_EXPIRE_DAYS = 365  # Mobil uygulama — uzun ömürlü token 
 
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

"""Authentication service for Web3"""

import jwt
from datetime import datetime, timedelta
from typing import Dict, Any

from ..core.config import settings

def create_access_token(data: Dict[str, Any], expires_delta: timedelta = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

async def verify_siwe_message(message: Any, signature: str) -> bool:
    """Verify Sign-In with Ethereum message"""
    # TODO: Implement SIWE verification
    # This would use eth_account to verify the signature
    return True
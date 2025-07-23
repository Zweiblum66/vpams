"""
Authentication and security utilities for Integration Service
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import base64
import json

from .config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token handling
security = HTTPBearer()

# Encryption for sensitive data
def get_fernet_key() -> bytes:
    """Get or generate Fernet encryption key"""
    key = settings.ENCRYPTION_KEY
    if len(key) != 32:
        # Pad or truncate to 32 chars
        key = key.ljust(32, '0')[:32]
    return base64.urlsafe_b64encode(key.encode())

fernet = Fernet(get_fernet_key())


def encrypt_data(data: Dict[str, Any]) -> str:
    """Encrypt sensitive data"""
    json_str = json.dumps(data)
    encrypted = fernet.encrypt(json_str.encode())
    return encrypted.decode()


def decrypt_data(encrypted_data: str) -> Dict[str, Any]:
    """Decrypt sensitive data"""
    decrypted = fernet.decrypt(encrypted_data.encode())
    return json.loads(decrypted.decode())


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Return user info from token
    return {
        "user_id": user_id,
        "email": payload.get("email"),
        "name": payload.get("name"),
        "roles": payload.get("roles", [])
    }


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)
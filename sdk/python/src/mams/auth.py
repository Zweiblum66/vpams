"""
Authentication providers for MAMS SDK
"""

from typing import Dict, Optional, Any
from abc import ABC, abstractmethod
import time
from urllib.parse import urlencode, urlparse, parse_qs
import httpx


class AuthProvider(ABC):
    """Base authentication provider"""
    
    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        pass
    
    @abstractmethod
    def refresh_token(self) -> bool:
        """Refresh authentication token if needed"""
        pass


class APIKeyAuth(AuthProvider):
    """API Key authentication"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def get_headers(self) -> Dict[str, str]:
        return {"X-API-Key": self.api_key}
    
    def refresh_token(self) -> bool:
        # API keys don't need refreshing
        return True


class JWTAuth(AuthProvider):
    """JWT token authentication"""
    
    def __init__(self, token: str):
        self.token = token
        self._parse_token()
    
    def _parse_token(self):
        """Parse JWT token to get expiration"""
        # Simple JWT parsing (production should use proper JWT library)
        try:
            import base64
            import json
            
            # Split token
            parts = self.token.split(".")
            if len(parts) != 3:
                self.expires_at = None
                return
            
            # Decode payload
            payload = parts[1]
            # Add padding if needed
            payload += "=" * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            data = json.loads(decoded)
            
            self.expires_at = data.get("exp")
        except:
            self.expires_at = None
    
    def get_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}
    
    def refresh_token(self) -> bool:
        # Check if token is expired
        if self.expires_at and time.time() > self.expires_at:
            return False
        return True


class OAuth2Provider(AuthProvider):
    """OAuth2 authentication provider"""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        auth_url: str = "https://auth.mams.io/oauth/authorize",
        token_url: str = "https://auth.mams.io/oauth/token",
        scopes: Optional[list] = None
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.auth_url = auth_url
        self.token_url = token_url
        self.scopes = scopes or ["read", "write"]
        
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Get OAuth2 authorization URL"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
        }
        
        if state:
            params["state"] = state
        
        return f"{self.auth_url}?{urlencode(params)}"
    
    def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        with httpx.Client() as client:
            response = client.post(self.token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data.get("refresh_token")
            
            # Calculate expiration
            expires_in = token_data.get("expires_in", 3600)
            self.expires_at = time.time() + expires_in
            
            return token_data
    
    def get_headers(self) -> Dict[str, str]:
        if not self.access_token:
            raise ValueError("No access token available. Call exchange_code() first.")
        
        return {"Authorization": f"Bearer {self.access_token}"}
    
    def refresh_token(self) -> bool:
        """Refresh the access token"""
        if not self.refresh_token:
            return False
        
        # Check if token needs refreshing
        if self.expires_at and time.time() < (self.expires_at - 300):  # 5 min buffer
            return True
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        try:
            with httpx.Client() as client:
                response = client.post(self.token_url, data=data)
                response.raise_for_status()
                
                token_data = response.json()
                self.access_token = token_data["access_token"]
                
                # Update refresh token if provided
                if "refresh_token" in token_data:
                    self.refresh_token = token_data["refresh_token"]
                
                # Update expiration
                expires_in = token_data.get("expires_in", 3600)
                self.expires_at = time.time() + expires_in
                
                return True
        except:
            return False
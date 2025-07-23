"""
SDK Configuration
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class Config:
    """SDK configuration"""
    
    base_url: str = "https://api.mams.io"
    api_version: str = "v1"
    timeout: float = 30.0
    max_retries: int = 3
    verify_ssl: bool = True
    user_agent_suffix: str = "1.0.0"
    
    # Rate limiting
    rate_limit_retry: bool = True
    rate_limit_max_wait: float = 60.0
    
    # File operations
    chunk_size: int = 8 * 1024 * 1024  # 8MB chunks
    max_upload_size: int = 5 * 1024 * 1024 * 1024  # 5GB
    
    # WebSocket
    ws_reconnect: bool = True
    ws_reconnect_delay: float = 5.0
    ws_max_reconnect_attempts: int = 5
    
    def get_api_url(self, path: str) -> str:
        """Get full API URL for a path"""
        if path.startswith("/"):
            path = path[1:]
        return f"{self.base_url}/api/{self.api_version}/{path}"
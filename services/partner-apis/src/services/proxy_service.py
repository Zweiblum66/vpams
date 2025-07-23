"""Service for proxying requests to other MAMS services"""

import httpx
import logging
from typing import Dict, Any, Optional
from ..core.config import settings

logger = logging.getLogger(__name__)


class ProxyService:
    """Service for proxying API requests to internal MAMS services"""
    
    def __init__(self):
        self.service_urls = {
            "asset-management": settings.asset_management_url,
            "user-management": settings.user_management_url,
            "metadata-service": settings.metadata_service_url,
            "search-engine": settings.search_engine_url,
            "workflow-engine": settings.workflow_engine_url,
        }
        self.timeout = httpx.Timeout(30.0, connect=5.0)
    
    async def proxy_request(
        self,
        service: str,
        path: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Proxy a request to an internal service"""
        
        if service not in self.service_urls:
            raise ValueError(f"Unknown service: {service}")
        
        base_url = self.service_urls[service]
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        
        # Default headers
        request_headers = {
            "Content-Type": "application/json",
            "User-Agent": "MAMS-Partner-API/1.0"
        }
        
        if headers:
            request_headers.update(headers)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=json,
                    headers=request_headers
                )
                
                # Raise for HTTP errors
                response.raise_for_status()
                
                # Return JSON response
                return response.json()
                
        except httpx.TimeoutException:
            logger.error(f"Timeout proxying {method} {url}")
            raise Exception(f"Service {service} timeout")
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error proxying {method} {url}: {e.response.status_code}")
            if e.response.status_code == 404:
                raise Exception("Resource not found")
            elif e.response.status_code == 403:
                raise Exception("Access forbidden")
            elif e.response.status_code >= 500:
                raise Exception(f"Service {service} error")
            else:
                raise Exception(f"HTTP {e.response.status_code}")
        
        except httpx.RequestError as e:
            logger.error(f"Request error proxying {method} {url}: {e}")
            raise Exception(f"Service {service} unavailable")
        
        except Exception as e:
            logger.error(f"Unexpected error proxying {method} {url}: {e}")
            raise Exception("Internal service error")
    
    async def check_service_health(self, service: str) -> bool:
        """Check if a service is healthy"""
        
        if service not in self.service_urls:
            return False
        
        try:
            base_url = self.service_urls[service]
            url = f"{base_url.rstrip('/')}/health"
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(url)
                return response.status_code == 200
                
        except Exception as e:
            logger.warning(f"Health check failed for {service}: {e}")
            return False
    
    async def get_service_info(self, service: str) -> Optional[Dict[str, Any]]:
        """Get service information"""
        
        if service not in self.service_urls:
            return None
        
        try:
            base_url = self.service_urls[service]
            url = f"{base_url.rstrip('/')}/"
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.json()
                return None
                
        except Exception as e:
            logger.warning(f"Failed to get info for {service}: {e}")
            return None
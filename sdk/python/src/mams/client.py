"""
MAMS SDK Client
"""

from typing import Optional, Union, Dict, Any
import httpx
from .config import Config
from .auth import AuthProvider, APIKeyAuth, JWTAuth
from .resources import (
    AssetsResource,
    ProjectsResource,
    WorkflowsResource,
    IntegrationsResource,
    UsersResource,
    MetadataResource,
    SearchResource,
)
from .exceptions import MAMSError


class BaseClient:
    """Base client with common functionality"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        jwt_token: Optional[str] = None,
        auth: Optional[AuthProvider] = None,
        config: Optional[Config] = None,
        http_client: Optional[httpx.Client] = None
    ):
        # Initialize config
        if config:
            self.config = config
        else:
            self.config = Config(base_url=base_url or "https://api.mams.io")
        
        # Setup authentication
        if auth:
            self.auth = auth
        elif api_key:
            self.auth = APIKeyAuth(api_key)
        elif jwt_token:
            self.auth = JWTAuth(jwt_token)
        else:
            raise MAMSError("No authentication method provided")
        
        # HTTP client
        self._http_client = http_client
        self._owns_http_client = http_client is None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers including authentication"""
        headers = {
            "User-Agent": f"MAMS-Python-SDK/{self.config.user_agent_suffix}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        # Add auth headers
        auth_headers = self.auth.get_headers()
        headers.update(auth_headers)
        
        return headers
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle API response"""
        if response.status_code >= 200 and response.status_code < 300:
            return response.json() if response.content else {}
        
        # Handle errors
        from .exceptions import handle_error_response
        handle_error_response(response)


class MAMSClient(BaseClient):
    """Synchronous MAMS API client"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize HTTP client
        if self._owns_http_client:
            self._http_client = httpx.Client(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers=self._get_headers(),
                verify=self.config.verify_ssl,
            )
        
        # Initialize resources
        self.assets = AssetsResource(self)
        self.projects = ProjectsResource(self)
        self.workflows = WorkflowsResource(self)
        self.integrations = IntegrationsResource(self)
        self.users = UsersResource(self)
        self.metadata = MetadataResource(self)
        self.search = SearchResource(self)
    
    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request"""
        response = self._http_client.request(
            method=method,
            url=path,
            params=params,
            json=json,
            files=files,
            **kwargs
        )
        return self._handle_response(response)
    
    def close(self):
        """Close HTTP client"""
        if self._owns_http_client and self._http_client:
            self._http_client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class AsyncMAMSClient(BaseClient):
    """Asynchronous MAMS API client"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize HTTP client
        if self._owns_http_client:
            self._http_client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers=self._get_headers(),
                verify=self.config.verify_ssl,
            )
        
        # Initialize async resources
        from .async_resources import (
            AsyncAssetsResource,
            AsyncProjectsResource,
            AsyncWorkflowsResource,
            AsyncIntegrationsResource,
            AsyncUsersResource,
            AsyncMetadataResource,
            AsyncSearchResource,
        )
        
        self.assets = AsyncAssetsResource(self)
        self.projects = AsyncProjectsResource(self)
        self.workflows = AsyncWorkflowsResource(self)
        self.integrations = AsyncIntegrationsResource(self)
        self.users = AsyncUsersResource(self)
        self.metadata = AsyncMetadataResource(self)
        self.search = AsyncSearchResource(self)
    
    async def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make async HTTP request"""
        response = await self._http_client.request(
            method=method,
            url=path,
            params=params,
            json=json,
            files=files,
            **kwargs
        )
        return self._handle_response(response)
    
    async def close(self):
        """Close HTTP client"""
        if self._owns_http_client and self._http_client:
            await self._http_client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
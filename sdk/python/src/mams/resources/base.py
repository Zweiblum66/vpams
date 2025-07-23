"""
Base resource class
"""

from typing import Dict, Any, Optional, List, Iterator, TypeVar, Generic
from ..models import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseResource(Generic[T]):
    """Base class for API resources"""
    
    def __init__(self, client):
        self.client = client
        self.resource_name = ""
        self.model_class = BaseModel
    
    def _get_path(self, *parts: str) -> str:
        """Build API path"""
        path_parts = [self.resource_name] + list(parts)
        return "/".join(p for p in path_parts if p)
    
    def _make_request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make API request"""
        return self.client.request(method, path, **kwargs)
    
    def _parse_response(self, data: Dict[str, Any]) -> T:
        """Parse response into model"""
        return self.model_class(**data)
    
    def _parse_list_response(self, data: Dict[str, Any]) -> List[T]:
        """Parse list response into models"""
        items = data.get("data", [])
        return [self.model_class(**item) for item in items]
    
    def list(
        self,
        limit: int = 20,
        offset: int = 0,
        **filters
    ) -> List[T]:
        """List resources"""
        params = {
            "limit": limit,
            "offset": offset,
            **filters
        }
        
        response = self._make_request(
            "GET",
            self._get_path(),
            params=params
        )
        
        return self._parse_list_response(response)
    
    def get(self, resource_id: str) -> T:
        """Get a single resource"""
        response = self._make_request(
            "GET",
            self._get_path(resource_id)
        )
        
        return self._parse_response(response)
    
    def create(self, **data) -> T:
        """Create a new resource"""
        response = self._make_request(
            "POST",
            self._get_path(),
            json=data
        )
        
        return self._parse_response(response)
    
    def update(self, resource_id: str, **data) -> T:
        """Update a resource"""
        response = self._make_request(
            "PATCH",
            self._get_path(resource_id),
            json=data
        )
        
        return self._parse_response(response)
    
    def delete(self, resource_id: str) -> bool:
        """Delete a resource"""
        self._make_request(
            "DELETE",
            self._get_path(resource_id)
        )
        return True
    
    def iter_all(self, **filters) -> Iterator[T]:
        """Iterate through all resources"""
        offset = 0
        limit = 100
        
        while True:
            items = self.list(limit=limit, offset=offset, **filters)
            
            if not items:
                break
            
            for item in items:
                yield item
            
            if len(items) < limit:
                break
            
            offset += limit
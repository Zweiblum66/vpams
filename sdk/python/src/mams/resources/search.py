"""
Search resource implementation
"""

from typing import Optional, Dict, Any, List
from ..resources.base import BaseResource


class SearchResource(BaseResource):
    """Search API resource"""
    
    def __init__(self, client):
        super().__init__(client)
        self.resource_name = "search"
    
    def search(
        self,
        query: str,
        index: str = "assets",
        filters: Optional[Dict[str, Any]] = None,
        sort: Optional[List[Dict[str, str]]] = None,
        limit: int = 20,
        offset: int = 0,
        highlight: bool = False
    ) -> Dict[str, Any]:
        """Perform search
        
        Args:
            query: Search query
            index: Search index (assets, projects, users)
            filters: Optional filters
            sort: Optional sorting criteria
            limit: Results limit
            offset: Results offset
            highlight: Whether to include highlights
        
        Returns:
            Search results
        """
        data = {
            "query": query,
            "index": index,
            "limit": limit,
            "offset": offset,
            "highlight": highlight
        }
        
        if filters:
            data["filters"] = filters
        
        if sort:
            data["sort"] = sort
        
        response = self._make_request(
            "POST",
            self._get_path(),
            json=data
        )
        
        return response.get("data", {})
    
    def search_assets(
        self,
        query: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Search assets
        
        Args:
            query: Search query
            **kwargs: Additional search parameters
        
        Returns:
            Asset search results
        """
        return self.search(query, index="assets", **kwargs)
    
    def search_projects(
        self,
        query: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Search projects
        
        Args:
            query: Search query
            **kwargs: Additional search parameters
        
        Returns:
            Project search results
        """
        return self.search(query, index="projects", **kwargs)
    
    def search_users(
        self,
        query: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Search users
        
        Args:
            query: Search query
            **kwargs: Additional search parameters
        
        Returns:
            User search results
        """
        return self.search(query, index="users", **kwargs)
    
    def semantic_search(
        self,
        query: str,
        similarity_threshold: float = 0.7,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Perform semantic search
        
        Args:
            query: Search query
            similarity_threshold: Minimum similarity score
            limit: Results limit
        
        Returns:
            Semantic search results
        """
        data = {
            "query": query,
            "similarity_threshold": similarity_threshold,
            "limit": limit
        }
        
        response = self._make_request(
            "POST",
            self._get_path("semantic"),
            json=data
        )
        
        return response.get("data", {})
    
    def visual_search(
        self,
        image_asset_id: str,
        similarity_threshold: float = 0.8,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Perform visual similarity search
        
        Args:
            image_asset_id: Reference image asset ID
            similarity_threshold: Minimum similarity score
            limit: Results limit
        
        Returns:
            Visual search results
        """
        data = {
            "image_asset_id": image_asset_id,
            "similarity_threshold": similarity_threshold,
            "limit": limit
        }
        
        response = self._make_request(
            "POST",
            self._get_path("visual"),
            json=data
        )
        
        return response.get("data", {})
    
    def search_by_timecode(
        self,
        video_asset_id: str,
        start_time: float,
        end_time: float,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search within video timecode range
        
        Args:
            video_asset_id: Video asset ID
            start_time: Start time in seconds
            end_time: End time in seconds
            query: Optional text query
        
        Returns:
            Timecode search results
        """
        data = {
            "video_asset_id": video_asset_id,
            "start_time": start_time,
            "end_time": end_time
        }
        
        if query:
            data["query"] = query
        
        response = self._make_request(
            "POST",
            self._get_path("timecode"),
            json=data
        )
        
        return response.get("data", {})
    
    def get_suggestions(
        self,
        query: str,
        index: str = "assets",
        limit: int = 10
    ) -> List[str]:
        """Get search suggestions
        
        Args:
            query: Partial query
            index: Search index
            limit: Results limit
        
        Returns:
            List of suggestions
        """
        params = {
            "query": query,
            "index": index,
            "limit": limit
        }
        
        response = self._make_request(
            "GET",
            self._get_path("suggestions"),
            params=params
        )
        
        return response.get("data", [])
    
    def get_facets(
        self,
        query: str,
        index: str = "assets",
        facet_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get search facets
        
        Args:
            query: Search query
            index: Search index
            facet_fields: Optional list of facet fields
        
        Returns:
            Facet data
        """
        data = {
            "query": query,
            "index": index
        }
        
        if facet_fields:
            data["facet_fields"] = facet_fields
        
        response = self._make_request(
            "POST",
            self._get_path("facets"),
            json=data
        )
        
        return response.get("data", {})
    
    def save_search(
        self,
        name: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        public: bool = False
    ) -> Dict[str, Any]:
        """Save search query
        
        Args:
            name: Search name
            query: Search query
            filters: Optional filters
            public: Whether search is public
        
        Returns:
            Saved search
        """
        data = {
            "name": name,
            "query": query,
            "public": public
        }
        
        if filters:
            data["filters"] = filters
        
        response = self._make_request(
            "POST",
            self._get_path("saved"),
            json=data
        )
        
        return response.get("data", {})
    
    def get_saved_searches(self) -> List[Dict[str, Any]]:
        """Get saved searches
        
        Returns:
            List of saved searches
        """
        response = self._make_request(
            "GET",
            self._get_path("saved")
        )
        
        return response.get("data", [])
    
    def delete_saved_search(self, search_id: str) -> bool:
        """Delete saved search
        
        Args:
            search_id: Saved search ID
        
        Returns:
            True if successful
        """
        self._make_request(
            "DELETE",
            self._get_path("saved", search_id)
        )
        return True
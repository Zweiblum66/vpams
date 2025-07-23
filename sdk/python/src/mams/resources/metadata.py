"""
Metadata resource implementation
"""

from typing import Optional, Dict, Any, List
from ..resources.base import BaseResource


class MetadataResource(BaseResource):
    """Metadata API resource"""
    
    def __init__(self, client):
        super().__init__(client)
        self.resource_name = "metadata"
    
    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get metadata schemas
        
        Returns:
            List of metadata schemas
        """
        response = self._make_request(
            "GET",
            self._get_path("schemas")
        )
        
        return response.get("data", [])
    
    def create_schema(
        self,
        name: str,
        fields: List[Dict[str, Any]],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create metadata schema
        
        Args:
            name: Schema name
            fields: Field definitions
            description: Optional description
        
        Returns:
            Created schema
        """
        data = {
            "name": name,
            "fields": fields
        }
        
        if description:
            data["description"] = description
        
        response = self._make_request(
            "POST",
            self._get_path("schemas"),
            json=data
        )
        
        return response.get("data", {})
    
    def get_schema(self, schema_id: str) -> Dict[str, Any]:
        """Get metadata schema
        
        Args:
            schema_id: Schema ID
        
        Returns:
            Schema definition
        """
        response = self._make_request(
            "GET",
            self._get_path("schemas", schema_id)
        )
        
        return response.get("data", {})
    
    def update_schema(
        self,
        schema_id: str,
        **updates
    ) -> Dict[str, Any]:
        """Update metadata schema
        
        Args:
            schema_id: Schema ID
            **updates: Fields to update
        
        Returns:
            Updated schema
        """
        response = self._make_request(
            "PATCH",
            self._get_path("schemas", schema_id),
            json=updates
        )
        
        return response.get("data", {})
    
    def delete_schema(self, schema_id: str) -> bool:
        """Delete metadata schema
        
        Args:
            schema_id: Schema ID
        
        Returns:
            True if successful
        """
        self._make_request(
            "DELETE",
            self._get_path("schemas", schema_id)
        )
        return True
    
    def extract_metadata(
        self,
        asset_id: str,
        extractors: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Extract metadata from asset
        
        Args:
            asset_id: Asset ID
            extractors: Optional list of extractors to use
        
        Returns:
            Extracted metadata
        """
        data = {}
        if extractors:
            data["extractors"] = extractors
        
        response = self._make_request(
            "POST",
            self._get_path("extract"),
            json={"asset_id": asset_id, **data}
        )
        
        return response.get("data", {})
    
    def enrich_metadata(
        self,
        asset_id: str,
        metadata: Dict[str, Any],
        providers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Enrich metadata with external providers
        
        Args:
            asset_id: Asset ID
            metadata: Existing metadata
            providers: Optional list of enrichment providers
        
        Returns:
            Enriched metadata
        """
        data = {
            "asset_id": asset_id,
            "metadata": metadata
        }
        
        if providers:
            data["providers"] = providers
        
        response = self._make_request(
            "POST",
            self._get_path("enrich"),
            json=data
        )
        
        return response.get("data", {})
    
    def validate_metadata(
        self,
        metadata: Dict[str, Any],
        schema_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate metadata against schema
        
        Args:
            metadata: Metadata to validate
            schema_id: Optional schema ID
        
        Returns:
            Validation result
        """
        data = {"metadata": metadata}
        
        if schema_id:
            data["schema_id"] = schema_id
        
        response = self._make_request(
            "POST",
            self._get_path("validate"),
            json=data
        )
        
        return response.get("data", {})
    
    def search_by_metadata(
        self,
        criteria: Dict[str, Any],
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search assets by metadata criteria
        
        Args:
            criteria: Search criteria
            limit: Results limit
            offset: Results offset
        
        Returns:
            List of matching assets
        """
        data = {
            "criteria": criteria,
            "limit": limit,
            "offset": offset
        }
        
        response = self._make_request(
            "POST",
            self._get_path("search"),
            json=data
        )
        
        return response.get("data", [])
    
    def get_field_types(self) -> List[Dict[str, Any]]:
        """Get available metadata field types
        
        Returns:
            List of field types
        """
        response = self._make_request(
            "GET",
            self._get_path("field-types")
        )
        
        return response.get("data", [])
    
    def get_extractors(self) -> List[Dict[str, Any]]:
        """Get available metadata extractors
        
        Returns:
            List of extractors
        """
        response = self._make_request(
            "GET",
            self._get_path("extractors")
        )
        
        return response.get("data", [])
    
    def get_enrichment_providers(self) -> List[Dict[str, Any]]:
        """Get available enrichment providers
        
        Returns:
            List of enrichment providers
        """
        response = self._make_request(
            "GET",
            self._get_path("enrichment-providers")
        )
        
        return response.get("data", [])
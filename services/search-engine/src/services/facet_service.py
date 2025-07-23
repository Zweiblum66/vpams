"""
Facet Service - Handles facet/aggregation operations for search
"""

import structlog
from typing import Dict, Any, List, Optional
from opensearchpy import OpenSearch
from opensearchpy.exceptions import RequestError, OpenSearchException

from ..models.schemas import (
    FacetConfig,
    FacetType,
    FacetResult,
    FacetBucket,
    FilterCondition,
    FilterType
)
from ..core.exceptions import SearchError

logger = structlog.get_logger()


class FacetService:
    """Service for handling search facets and aggregations"""
    
    def __init__(self, opensearch_client: OpenSearch):
        self.client = opensearch_client
    
    def build_aggregations(self, facets: List[FacetConfig]) -> Dict[str, Any]:
        """
        Build OpenSearch aggregations from facet configurations
        
        Args:
            facets: List of facet configurations
            
        Returns:
            Dict containing aggregation definitions
        """
        aggregations = {}
        
        for facet in facets:
            agg_def = self._build_single_aggregation(facet)
            if agg_def:
                # Handle nested aggregations
                if facet.nested_path:
                    aggregations[facet.name] = {
                        "nested": {"path": facet.nested_path},
                        "aggs": {
                            f"{facet.name}_inner": agg_def
                        }
                    }
                else:
                    aggregations[facet.name] = agg_def
        
        return aggregations
    
    def _build_single_aggregation(self, facet: FacetConfig) -> Dict[str, Any]:
        """Build a single aggregation definition"""
        agg_def = {}
        
        if facet.type == FacetType.TERMS:
            agg_def = {
                "terms": {
                    "field": facet.field,
                    "size": facet.size or 10
                }
            }
            if facet.missing_value is not None:
                agg_def["terms"]["missing"] = facet.missing_value
                
        elif facet.type == FacetType.RANGE:
            if not facet.ranges:
                logger.warning("range_facet_missing_ranges", facet_name=facet.name)
                return {}
            agg_def = {
                "range": {
                    "field": facet.field,
                    "ranges": facet.ranges
                }
            }
            
        elif facet.type == FacetType.DATE_HISTOGRAM:
            agg_def = {
                "date_histogram": {
                    "field": facet.field,
                    "calendar_interval": facet.interval or "month",
                    "format": "yyyy-MM-dd"
                }
            }
            if facet.missing_value is not None:
                agg_def["date_histogram"]["missing"] = facet.missing_value
                
        elif facet.type == FacetType.HISTOGRAM:
            agg_def = {
                "histogram": {
                    "field": facet.field,
                    "interval": facet.interval or 10
                }
            }
            
        elif facet.type == FacetType.STATS:
            agg_def = {
                "stats": {
                    "field": facet.field
                }
            }
            
        elif facet.type == FacetType.CARDINALITY:
            agg_def = {
                "cardinality": {
                    "field": facet.field,
                    "precision_threshold": 100
                }
            }
        
        return agg_def
    
    def parse_aggregation_results(
        self, 
        raw_aggregations: Dict[str, Any], 
        facet_configs: List[FacetConfig]
    ) -> List[FacetResult]:
        """
        Parse raw OpenSearch aggregation results into FacetResult objects
        
        Args:
            raw_aggregations: Raw aggregation results from OpenSearch
            facet_configs: Original facet configurations
            
        Returns:
            List of parsed FacetResult objects
        """
        results = []
        config_map = {config.name: config for config in facet_configs}
        
        for agg_name, agg_data in raw_aggregations.items():
            if agg_name not in config_map:
                continue
                
            config = config_map[agg_name]
            
            # Handle nested aggregations
            if config.nested_path and "doc_count" in agg_data:
                # Extract inner aggregation
                inner_name = f"{agg_name}_inner"
                if inner_name in agg_data:
                    agg_data = agg_data[inner_name]
            
            facet_result = self._parse_single_aggregation(agg_name, agg_data, config)
            if facet_result:
                results.append(facet_result)
        
        return results
    
    def _parse_single_aggregation(
        self, 
        name: str, 
        agg_data: Dict[str, Any], 
        config: FacetConfig
    ) -> Optional[FacetResult]:
        """Parse a single aggregation result"""
        try:
            if config.type in [FacetType.TERMS, FacetType.RANGE, FacetType.DATE_HISTOGRAM, FacetType.HISTOGRAM]:
                # Bucket aggregations
                buckets = []
                raw_buckets = agg_data.get("buckets", [])
                
                for bucket in raw_buckets:
                    bucket_obj = FacetBucket(
                        key=bucket.get("key"),
                        doc_count=bucket.get("doc_count", 0)
                    )
                    
                    # Add range boundaries if present
                    if "from" in bucket:
                        bucket_obj.from_ = bucket["from"]
                    if "to" in bucket:
                        bucket_obj.to = bucket["to"]
                    
                    buckets.append(bucket_obj)
                
                return FacetResult(
                    name=name,
                    type=config.type,
                    buckets=buckets
                )
                
            elif config.type == FacetType.STATS:
                # Stats aggregation
                return FacetResult(
                    name=name,
                    type=config.type,
                    count=agg_data.get("count", 0),
                    sum=agg_data.get("sum"),
                    avg=agg_data.get("avg"),
                    min=agg_data.get("min"),
                    max=agg_data.get("max")
                )
                
            elif config.type == FacetType.CARDINALITY:
                # Cardinality aggregation
                return FacetResult(
                    name=name,
                    type=config.type,
                    value=agg_data.get("value", 0)
                )
                
        except Exception as e:
            logger.error("facet_parsing_error", facet_name=name, error=str(e))
            
        return None
    
    def build_filter_query(self, filters: List[FilterCondition]) -> List[Dict[str, Any]]:
        """
        Build OpenSearch filter queries from filter conditions
        
        Args:
            filters: List of filter conditions
            
        Returns:
            List of OpenSearch filter queries
        """
        filter_queries = []
        
        for filter_cond in filters:
            filter_query = self._build_single_filter(filter_cond)
            if filter_query:
                # Handle nested filters
                if filter_cond.nested_path:
                    filter_queries.append({
                        "nested": {
                            "path": filter_cond.nested_path,
                            "query": filter_query
                        }
                    })
                else:
                    filter_queries.append(filter_query)
        
        return filter_queries
    
    def _build_single_filter(self, filter_cond: FilterCondition) -> Optional[Dict[str, Any]]:
        """Build a single filter query"""
        try:
            if filter_cond.type == FilterType.TERM:
                return {"term": {filter_cond.field: filter_cond.value}}
                
            elif filter_cond.type == FilterType.TERMS:
                return {"terms": {filter_cond.field: filter_cond.value}}
                
            elif filter_cond.type == FilterType.RANGE:
                return {"range": {filter_cond.field: filter_cond.value}}
                
            elif filter_cond.type == FilterType.EXISTS:
                return {"exists": {"field": filter_cond.field}}
                
            elif filter_cond.type == FilterType.PREFIX:
                return {"prefix": {filter_cond.field: filter_cond.value}}
                
            elif filter_cond.type == FilterType.WILDCARD:
                return {"wildcard": {filter_cond.field: filter_cond.value}}
                
            elif filter_cond.type == FilterType.REGEXP:
                return {"regexp": {filter_cond.field: filter_cond.value}}
                
        except Exception as e:
            logger.error("filter_building_error", filter=filter_cond.dict(), error=str(e))
            
        return None
    
    def get_default_facets(self) -> List[FacetConfig]:
        """Get default facet configurations for common use cases"""
        return [
            FacetConfig(
                name="asset_types",
                field="asset_type",
                type=FacetType.TERMS,
                size=10
            ),
            FacetConfig(
                name="file_extensions", 
                field="file_extension",
                type=FacetType.TERMS,
                size=20
            ),
            FacetConfig(
                name="file_size_ranges",
                field="file_size",
                type=FacetType.RANGE,
                ranges=[
                    {"to": 1048576, "key": "< 1MB"},
                    {"from": 1048576, "to": 10485760, "key": "1MB - 10MB"},
                    {"from": 10485760, "to": 104857600, "key": "10MB - 100MB"},
                    {"from": 104857600, "to": 1073741824, "key": "100MB - 1GB"},
                    {"from": 1073741824, "key": "> 1GB"}
                ]
            ),
            FacetConfig(
                name="created_dates",
                field="created_at",
                type=FacetType.DATE_HISTOGRAM,
                interval="month"
            ),
            FacetConfig(
                name="mime_types",
                field="mime_type",
                type=FacetType.TERMS,
                size=15
            ),
            FacetConfig(
                name="status",
                field="status",
                type=FacetType.TERMS,
                size=10
            )
        ]
    
    def validate_field_for_aggregation(self, field: str, index: str) -> bool:
        """
        Validate if a field can be used for aggregation
        
        Args:
            field: Field name
            index: Index name
            
        Returns:
            True if field can be aggregated, False otherwise
        """
        try:
            # Get field mapping
            mapping = self.client.indices.get_mapping(index=index)
            
            # Navigate through mapping to find field type
            for idx_name, idx_mapping in mapping.items():
                properties = idx_mapping.get("mappings", {}).get("properties", {})
                field_mapping = self._get_field_mapping(properties, field.split("."))
                
                if field_mapping:
                    field_type = field_mapping.get("type", "")
                    # Check if field type supports aggregation
                    return field_type in ["keyword", "integer", "long", "float", "double", "date", "boolean"]
            
        except Exception as e:
            logger.error("field_validation_error", field=field, error=str(e))
            
        return False
    
    def _get_field_mapping(self, properties: Dict[str, Any], field_path: List[str]) -> Optional[Dict[str, Any]]:
        """Recursively get field mapping for nested fields"""
        if not field_path:
            return None
            
        current_field = field_path[0]
        if current_field not in properties:
            return None
            
        field_def = properties[current_field]
        
        if len(field_path) == 1:
            # Check if it's a text field with keyword subfield
            if field_def.get("type") == "text" and "fields" in field_def:
                if "keyword" in field_def["fields"]:
                    return field_def["fields"]["keyword"]
            return field_def
        else:
            # Navigate to nested properties
            if "properties" in field_def:
                return self._get_field_mapping(field_def["properties"], field_path[1:])
            elif field_def.get("type") == "nested" and "properties" in field_def:
                return self._get_field_mapping(field_def["properties"], field_path[1:])
                
        return None
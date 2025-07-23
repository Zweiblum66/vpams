"""
Tests for FacetService
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from opensearchpy import AsyncOpenSearch
from opensearchpy.exceptions import RequestError

from src.services.facet_service import FacetService
from src.models.schemas import (
    FacetConfig, FacetType, FacetResult, FacetBucket,
    FilterCondition, FilterType
)


@pytest.fixture
def mock_opensearch_client():
    """Create a mock OpenSearch client"""
    client = AsyncMock(spec=AsyncOpenSearch)
    client.indices = Mock()
    client.indices.get_mapping = Mock()
    return client


@pytest.fixture
def facet_service(mock_opensearch_client):
    """Create a FacetService instance"""
    return FacetService(mock_opensearch_client)


class TestFacetService:
    """Test FacetService functionality"""
    
    def test_build_terms_aggregation(self, facet_service):
        """Test building a terms aggregation"""
        facet = FacetConfig(
            name="categories",
            field="category",
            type=FacetType.TERMS,
            size=20
        )
        
        result = facet_service.build_aggregations([facet])
        
        assert "categories" in result
        assert result["categories"]["terms"]["field"] == "category"
        assert result["categories"]["terms"]["size"] == 20
    
    def test_build_range_aggregation(self, facet_service):
        """Test building a range aggregation"""
        facet = FacetConfig(
            name="price_ranges",
            field="price",
            type=FacetType.RANGE,
            ranges=[
                {"to": 100, "key": "cheap"},
                {"from": 100, "to": 1000, "key": "moderate"},
                {"from": 1000, "key": "expensive"}
            ]
        )
        
        result = facet_service.build_aggregations([facet])
        
        assert "price_ranges" in result
        assert result["price_ranges"]["range"]["field"] == "price"
        assert len(result["price_ranges"]["range"]["ranges"]) == 3
    
    def test_build_date_histogram_aggregation(self, facet_service):
        """Test building a date histogram aggregation"""
        facet = FacetConfig(
            name="monthly_counts",
            field="created_at",
            type=FacetType.DATE_HISTOGRAM,
            interval="month"
        )
        
        result = facet_service.build_aggregations([facet])
        
        assert "monthly_counts" in result
        assert result["monthly_counts"]["date_histogram"]["field"] == "created_at"
        assert result["monthly_counts"]["date_histogram"]["calendar_interval"] == "month"
    
    def test_build_histogram_aggregation(self, facet_service):
        """Test building a histogram aggregation"""
        facet = FacetConfig(
            name="size_distribution",
            field="file_size",
            type=FacetType.HISTOGRAM,
            interval=1000000  # 1MB intervals
        )
        
        result = facet_service.build_aggregations([facet])
        
        assert "size_distribution" in result
        assert result["size_distribution"]["histogram"]["field"] == "file_size"
        assert result["size_distribution"]["histogram"]["interval"] == 1000000
    
    def test_build_stats_aggregation(self, facet_service):
        """Test building a stats aggregation"""
        facet = FacetConfig(
            name="duration_stats",
            field="duration",
            type=FacetType.STATS
        )
        
        result = facet_service.build_aggregations([facet])
        
        assert "duration_stats" in result
        assert result["duration_stats"]["stats"]["field"] == "duration"
    
    def test_build_cardinality_aggregation(self, facet_service):
        """Test building a cardinality aggregation"""
        facet = FacetConfig(
            name="unique_users",
            field="user_id",
            type=FacetType.CARDINALITY
        )
        
        result = facet_service.build_aggregations([facet])
        
        assert "unique_users" in result
        assert result["unique_users"]["cardinality"]["field"] == "user_id"
    
    def test_build_nested_aggregation(self, facet_service):
        """Test building a nested aggregation"""
        facet = FacetConfig(
            name="nested_tags",
            field="tags.name",
            type=FacetType.TERMS,
            nested_path="tags",
            size=50
        )
        
        result = facet_service.build_aggregations([facet])
        
        assert "nested_tags" in result
        assert result["nested_tags"]["nested"]["path"] == "tags"
        assert "nested_tags_inner" in result["nested_tags"]["aggs"]
        assert result["nested_tags"]["aggs"]["nested_tags_inner"]["terms"]["field"] == "tags.name"
    
    def test_parse_terms_aggregation_result(self, facet_service):
        """Test parsing terms aggregation results"""
        raw_aggs = {
            "categories": {
                "buckets": [
                    {"key": "video", "doc_count": 150},
                    {"key": "image", "doc_count": 100},
                    {"key": "audio", "doc_count": 50}
                ]
            }
        }
        
        facet_configs = [
            FacetConfig(
                name="categories",
                field="category",
                type=FacetType.TERMS
            )
        ]
        
        results = facet_service.parse_aggregation_results(raw_aggs, facet_configs)
        
        assert len(results) == 1
        assert results[0].name == "categories"
        assert results[0].type == FacetType.TERMS
        assert len(results[0].buckets) == 3
        assert results[0].buckets[0].key == "video"
        assert results[0].buckets[0].doc_count == 150
    
    def test_parse_range_aggregation_result(self, facet_service):
        """Test parsing range aggregation results"""
        raw_aggs = {
            "price_ranges": {
                "buckets": [
                    {"key": "cheap", "from": 0, "to": 100, "doc_count": 200},
                    {"key": "moderate", "from": 100, "to": 1000, "doc_count": 150},
                    {"key": "expensive", "from": 1000, "doc_count": 50}
                ]
            }
        }
        
        facet_configs = [
            FacetConfig(
                name="price_ranges",
                field="price",
                type=FacetType.RANGE
            )
        ]
        
        results = facet_service.parse_aggregation_results(raw_aggs, facet_configs)
        
        assert len(results) == 1
        assert results[0].name == "price_ranges"
        assert results[0].type == FacetType.RANGE
        assert len(results[0].buckets) == 3
        assert results[0].buckets[0].from_ == 0
        assert results[0].buckets[0].to == 100
    
    def test_parse_stats_aggregation_result(self, facet_service):
        """Test parsing stats aggregation results"""
        raw_aggs = {
            "duration_stats": {
                "count": 100,
                "min": 10.5,
                "max": 3600.0,
                "avg": 180.5,
                "sum": 18050.0
            }
        }
        
        facet_configs = [
            FacetConfig(
                name="duration_stats",
                field="duration",
                type=FacetType.STATS
            )
        ]
        
        results = facet_service.parse_aggregation_results(raw_aggs, facet_configs)
        
        assert len(results) == 1
        assert results[0].name == "duration_stats"
        assert results[0].type == FacetType.STATS
        assert results[0].count == 100
        assert results[0].min == 10.5
        assert results[0].max == 3600.0
        assert results[0].avg == 180.5
        assert results[0].sum == 18050.0
    
    def test_parse_cardinality_aggregation_result(self, facet_service):
        """Test parsing cardinality aggregation results"""
        raw_aggs = {
            "unique_users": {
                "value": 42
            }
        }
        
        facet_configs = [
            FacetConfig(
                name="unique_users",
                field="user_id",
                type=FacetType.CARDINALITY
            )
        ]
        
        results = facet_service.parse_aggregation_results(raw_aggs, facet_configs)
        
        assert len(results) == 1
        assert results[0].name == "unique_users"
        assert results[0].type == FacetType.CARDINALITY
        assert results[0].value == 42
    
    def test_build_term_filter(self, facet_service):
        """Test building a term filter"""
        filter_cond = FilterCondition(
            field="status",
            type=FilterType.TERM,
            value="active"
        )
        
        result = facet_service.build_filter_query([filter_cond])
        
        assert len(result) == 1
        assert result[0] == {"term": {"status": "active"}}
    
    def test_build_terms_filter(self, facet_service):
        """Test building a terms filter"""
        filter_cond = FilterCondition(
            field="tags",
            type=FilterType.TERMS,
            value=["video", "marketing", "tutorial"]
        )
        
        result = facet_service.build_filter_query([filter_cond])
        
        assert len(result) == 1
        assert result[0] == {"terms": {"tags": ["video", "marketing", "tutorial"]}}
    
    def test_build_range_filter(self, facet_service):
        """Test building a range filter"""
        filter_cond = FilterCondition(
            field="duration",
            type=FilterType.RANGE,
            value={"gte": 60, "lte": 300}
        )
        
        result = facet_service.build_filter_query([filter_cond])
        
        assert len(result) == 1
        assert result[0] == {"range": {"duration": {"gte": 60, "lte": 300}}}
    
    def test_build_exists_filter(self, facet_service):
        """Test building an exists filter"""
        filter_cond = FilterCondition(
            field="thumbnail",
            type=FilterType.EXISTS,
            value=True  # Value is ignored for exists filters
        )
        
        result = facet_service.build_filter_query([filter_cond])
        
        assert len(result) == 1
        assert result[0] == {"exists": {"field": "thumbnail"}}
    
    def test_build_prefix_filter(self, facet_service):
        """Test building a prefix filter"""
        filter_cond = FilterCondition(
            field="file_name",
            type=FilterType.PREFIX,
            value="IMG_"
        )
        
        result = facet_service.build_filter_query([filter_cond])
        
        assert len(result) == 1
        assert result[0] == {"prefix": {"file_name": "IMG_"}}
    
    def test_build_wildcard_filter(self, facet_service):
        """Test building a wildcard filter"""
        filter_cond = FilterCondition(
            field="file_name",
            type=FilterType.WILDCARD,
            value="*.mp4"
        )
        
        result = facet_service.build_filter_query([filter_cond])
        
        assert len(result) == 1
        assert result[0] == {"wildcard": {"file_name": "*.mp4"}}
    
    def test_build_regexp_filter(self, facet_service):
        """Test building a regexp filter"""
        filter_cond = FilterCondition(
            field="asset_id",
            type=FilterType.REGEXP,
            value="[0-9]{4}-[0-9]{6}"
        )
        
        result = facet_service.build_filter_query([filter_cond])
        
        assert len(result) == 1
        assert result[0] == {"regexp": {"asset_id": "[0-9]{4}-[0-9]{6}"}}
    
    def test_build_nested_filter(self, facet_service):
        """Test building a nested filter"""
        filter_cond = FilterCondition(
            field="tags.name",
            type=FilterType.TERM,
            value="important",
            nested_path="tags"
        )
        
        result = facet_service.build_filter_query([filter_cond])
        
        assert len(result) == 1
        assert "nested" in result[0]
        assert result[0]["nested"]["path"] == "tags"
        assert result[0]["nested"]["query"] == {"term": {"tags.name": "important"}}
    
    def test_build_multiple_filters(self, facet_service):
        """Test building multiple filters"""
        filters = [
            FilterCondition(field="status", type=FilterType.TERM, value="active"),
            FilterCondition(field="asset_type", type=FilterType.TERMS, value=["video", "image"]),
            FilterCondition(field="file_size", type=FilterType.RANGE, value={"gte": 1000000})
        ]
        
        result = facet_service.build_filter_query(filters)
        
        assert len(result) == 3
        assert result[0] == {"term": {"status": "active"}}
        assert result[1] == {"terms": {"asset_type": ["video", "image"]}}
        assert result[2] == {"range": {"file_size": {"gte": 1000000}}}
    
    def test_get_default_facets(self, facet_service):
        """Test getting default facet configurations"""
        facets = facet_service.get_default_facets()
        
        assert len(facets) > 0
        
        # Check for expected default facets
        facet_names = [f.name for f in facets]
        assert "asset_types" in facet_names
        assert "file_extensions" in facet_names
        assert "file_size_ranges" in facet_names
        assert "created_dates" in facet_names
        
        # Check file size ranges facet
        file_size_facet = next(f for f in facets if f.name == "file_size_ranges")
        assert file_size_facet.type == FacetType.RANGE
        assert len(file_size_facet.ranges) > 0
    
    def test_validate_field_for_aggregation_valid(self, facet_service):
        """Test validating a field that can be aggregated"""
        # Mock the mapping response
        facet_service.client.indices.get_mapping.return_value = {
            "test_index": {
                "mappings": {
                    "properties": {
                        "category": {"type": "keyword"},
                        "price": {"type": "long"}
                    }
                }
            }
        }
        
        # Test keyword field
        assert facet_service.validate_field_for_aggregation("category", "test_index") is True
        
        # Test numeric field
        assert facet_service.validate_field_for_aggregation("price", "test_index") is True
    
    def test_validate_field_for_aggregation_text_field(self, facet_service):
        """Test validating a text field with keyword subfield"""
        facet_service.client.indices.get_mapping.return_value = {
            "test_index": {
                "mappings": {
                    "properties": {
                        "title": {
                            "type": "text",
                            "fields": {
                                "keyword": {"type": "keyword"}
                            }
                        }
                    }
                }
            }
        }
        
        # Text field with .keyword should be valid
        assert facet_service.validate_field_for_aggregation("title", "test_index") is True
    
    def test_validate_field_for_aggregation_nested_field(self, facet_service):
        """Test validating a nested field"""
        facet_service.client.indices.get_mapping.return_value = {
            "test_index": {
                "mappings": {
                    "properties": {
                        "tags": {
                            "type": "nested",
                            "properties": {
                                "name": {"type": "keyword"}
                            }
                        }
                    }
                }
            }
        }
        
        # Nested field should be valid
        assert facet_service.validate_field_for_aggregation("tags.name", "test_index") is True
    
    def test_validate_field_for_aggregation_invalid(self, facet_service):
        """Test validating a field that cannot be aggregated"""
        facet_service.client.indices.get_mapping.return_value = {
            "test_index": {
                "mappings": {
                    "properties": {
                        "description": {"type": "text"}  # Text without keyword
                    }
                }
            }
        }
        
        # Pure text field cannot be aggregated
        assert facet_service.validate_field_for_aggregation("description", "test_index") is False
    
    def test_validate_field_for_aggregation_missing_field(self, facet_service):
        """Test validating a non-existent field"""
        facet_service.client.indices.get_mapping.return_value = {
            "test_index": {
                "mappings": {
                    "properties": {}
                }
            }
        }
        
        # Non-existent field
        assert facet_service.validate_field_for_aggregation("nonexistent", "test_index") is False
    
    def test_validate_field_for_aggregation_error_handling(self, facet_service):
        """Test error handling in field validation"""
        # Simulate an error
        facet_service.client.indices.get_mapping.side_effect = Exception("Connection error")
        
        # Should return False on error
        assert facet_service.validate_field_for_aggregation("any_field", "test_index") is False
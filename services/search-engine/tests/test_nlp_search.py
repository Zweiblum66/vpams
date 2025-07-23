"""
Tests for Natural Language Search functionality
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from src.services.nlp_search_service import (
    NLPSearchService, QueryIntent, ParsedQuery, get_nlp_search_service
)
from src.models.schemas import SearchType, FilteredSearchQuery


@pytest.fixture
def nlp_service():
    """Create NLP search service instance"""
    return NLPSearchService()


@pytest.mark.asyncio
class TestNLPSearchService:
    """Test natural language search service"""
    
    async def test_parse_simple_query(self, nlp_service):
        """Test parsing simple queries"""
        query = "interview videos"
        parsed = await nlp_service.parse_natural_language_query(query)
        
        assert parsed.original_query == query
        assert parsed.intent == QueryIntent.FIND_BY_NAME
        assert "interview" in parsed.keywords
        assert "videos" in parsed.keywords or parsed.entities.get("type") == "video"
    
    async def test_parse_temporal_query(self, nlp_service):
        """Test parsing temporal queries"""
        query = "videos from last week"
        parsed = await nlp_service.parse_natural_language_query(query)
        
        assert parsed.intent == QueryIntent.FIND_BY_DATE
        assert "created_at" in parsed.temporal_filters
        assert parsed.entities.get("type") == "video"
    
    async def test_parse_person_query(self, nlp_service):
        """Test parsing person-based queries"""
        query = "photos by John Smith"
        parsed = await nlp_service.parse_natural_language_query(query)
        
        assert parsed.intent == QueryIntent.FIND_BY_PERSON
        assert parsed.entities.get("person") == "John Smith"
        assert parsed.entities.get("type") == "image"
    
    async def test_parse_project_query(self, nlp_service):
        """Test parsing project-based queries"""
        query = 'documents in project "Summer Campaign"'
        parsed = await nlp_service.parse_natural_language_query(query)
        
        assert parsed.intent == QueryIntent.FIND_BY_PROJECT
        assert parsed.entities.get("project") == "Summer Campaign"
        assert parsed.entities.get("type") == "document"
    
    async def test_parse_technical_query(self, nlp_service):
        """Test parsing technical specification queries"""
        query = "4K videos longer than 5 minutes"
        parsed = await nlp_service.parse_natural_language_query(query)
        
        assert parsed.intent == QueryIntent.FIND_BY_TECHNICAL
        assert parsed.entities.get("type") == "video"
        assert "resolution_height" in parsed.technical_filters
        assert parsed.technical_filters["resolution_height"] == 2160
        assert "duration" in parsed.technical_filters
        assert parsed.technical_filters["duration"]["gt"] == 300  # 5 minutes in seconds
    
    async def test_parse_complex_query(self, nlp_service):
        """Test parsing complex queries with multiple conditions"""
        query = "recent videos tagged as nature and longer than 2 minutes"
        parsed = await nlp_service.parse_natural_language_query(query)
        
        assert parsed.entities.get("type") == "video"
        assert "nature" in parsed.filters.get("tags", [])
        assert "duration" in parsed.technical_filters
        assert "recent" in parsed.modifiers
    
    async def test_extract_temporal_filters_today(self, nlp_service):
        """Test extracting 'today' temporal filter"""
        query = "files uploaded today"
        parsed = await nlp_service.parse_natural_language_query(query)
        
        assert "created_at" in parsed.temporal_filters
        temporal_filter = parsed.temporal_filters["created_at"]
        
        # Check that the date range covers today
        start_date = datetime.fromisoformat(temporal_filter["gte"])
        end_date = datetime.fromisoformat(temporal_filter["lte"])
        
        now = datetime.utcnow()
        assert start_date.date() == now.date()
        assert end_date.date() == now.date()
    
    async def test_extract_temporal_filters_last_n_days(self, nlp_service):
        """Test extracting 'last N days' temporal filter"""
        query = "videos from last 7 days"
        parsed = await nlp_service.parse_natural_language_query(query)
        
        assert "created_at" in parsed.temporal_filters
        temporal_filter = parsed.temporal_filters["created_at"]
        
        # Check that the date range covers last 7 days
        start_date = datetime.fromisoformat(temporal_filter["gte"])
        end_date = datetime.fromisoformat(temporal_filter["lte"])
        
        now = datetime.utcnow()
        expected_start = now - timedelta(days=7)
        
        assert abs((start_date - expected_start).total_seconds()) < 60  # Within 1 minute
        assert abs((end_date - now).total_seconds()) < 60
    
    async def test_extract_resolution_filters(self, nlp_service):
        """Test extracting resolution filters"""
        test_cases = [
            ("1080p videos", 1080),
            ("4k footage", 2160),
            ("HD clips", 720),
            ("UHD content", 2160),
            ("1920x1080 videos", 1080)
        ]
        
        for query, expected_height in test_cases:
            parsed = await nlp_service.parse_natural_language_query(query)
            assert "resolution_height" in parsed.technical_filters
            assert parsed.technical_filters["resolution_height"] == expected_height
    
    async def test_extract_fps_filters(self, nlp_service):
        """Test extracting frame rate filters"""
        test_cases = [
            ("60fps videos", 60),
            ("30 fps footage", 30),
            ("24 frames per second", 24)
        ]
        
        for query, expected_fps in test_cases:
            parsed = await nlp_service.parse_natural_language_query(query)
            assert "frame_rate" in parsed.technical_filters
            assert parsed.technical_filters["frame_rate"] == expected_fps
    
    async def test_extract_file_size_filters(self, nlp_service):
        """Test extracting file size filters"""
        query = "files larger than 100 MB"
        parsed = await nlp_service.parse_natural_language_query(query)
        
        assert "file_size" in parsed.technical_filters
        assert "gt" in parsed.technical_filters["file_size"]
        assert parsed.technical_filters["file_size"]["gt"] == 100 * 1024 * 1024
    
    async def test_extract_duration_filters(self, nlp_service):
        """Test extracting duration filters"""
        test_cases = [
            ("videos longer than 10 minutes", "gt", 600),
            ("clips shorter than 30 seconds", "lt", 30),
            ("5 minute long videos", "eq", 300)
        ]
        
        for query, expected_op, expected_duration in test_cases:
            parsed = await nlp_service.parse_natural_language_query(query)
            assert "duration" in parsed.technical_filters
            
            if expected_op == "eq":
                # For exact match, we use a range
                assert "gte" in parsed.technical_filters["duration"]
                assert "lte" in parsed.technical_filters["duration"]
                assert parsed.technical_filters["duration"]["gte"] == expected_duration - 30
                assert parsed.technical_filters["duration"]["lte"] == expected_duration + 30
            else:
                assert expected_op in parsed.technical_filters["duration"]
                assert parsed.technical_filters["duration"][expected_op] == expected_duration
    
    async def test_extract_modifiers(self, nlp_service):
        """Test extracting query modifiers"""
        test_cases = [
            ("recent videos", ["recent"]),
            ("latest images", ["latest"]),
            ("oldest documents", ["oldest"]),
            ("most popular clips", ["popular"]),
            ("high quality footage", ["high_quality"])
        ]
        
        for query, expected_modifiers in test_cases:
            parsed = await nlp_service.parse_natural_language_query(query)
            for modifier in expected_modifiers:
                assert modifier in parsed.modifiers
    
    async def test_convert_to_search_query(self, nlp_service):
        """Test converting parsed query to search query"""
        query = "recent 4K videos tagged as nature from project Wildlife"
        parsed = await nlp_service.parse_natural_language_query(query)
        
        search_query = await nlp_service.convert_to_search_query(parsed)
        
        assert isinstance(search_query, FilteredSearchQuery)
        assert search_query.search_type == SearchType.BASIC
        assert search_query.sort_by == "created_at"
        assert search_query.sort_order == "desc"
        
        # Check filters
        filters = search_query.filters
        assert any(f["field"] == "asset_type" and f["value"] == "video" for f in filters)
        assert any(f["field"] == "resolution_height" and f["value"] == 2160 for f in filters)
        assert any(f["field"] == "tags" and "nature" in f["value"] for f in filters)
        assert any(f["field"] == "project_name" and "Wildlife" in f["value"] for f in filters)
    
    async def test_confidence_calculation(self, nlp_service):
        """Test confidence score calculation"""
        # High confidence query with clear intent and entities
        query1 = "videos by John Smith from last week"
        parsed1 = await nlp_service.parse_natural_language_query(query1)
        assert parsed1.confidence > 0.7
        
        # Lower confidence query with vague terms
        query2 = "stuff things whatever"
        parsed2 = await nlp_service.parse_natural_language_query(query2)
        assert parsed2.confidence < 0.5
    
    async def test_quoted_search_terms(self, nlp_service):
        """Test handling of quoted search terms"""
        query = '"exact phrase search" in documents'
        parsed = await nlp_service.parse_natural_language_query(query)
        
        search_query = await nlp_service.convert_to_search_query(parsed)
        assert search_query.search_type == SearchType.PHRASE
    
    async def test_wildcard_search(self, nlp_service):
        """Test handling of wildcard searches"""
        query = "files matching test*"
        parsed = await nlp_service.parse_natural_language_query(query)
        
        search_query = await nlp_service.convert_to_search_query(parsed)
        assert search_query.search_type == SearchType.WILDCARD
    
    async def test_complex_filter_combinations(self, nlp_service):
        """Test complex queries with multiple filter types"""
        query = "HD videos from John Smith in project Marketing uploaded yesterday longer than 2 minutes"
        parsed = await nlp_service.parse_natural_language_query(query)
        
        # Check all components were extracted
        assert parsed.entities.get("type") == "video"
        assert parsed.entities.get("person") == "John Smith"
        assert parsed.entities.get("project") == "Marketing"
        assert "created_at" in parsed.temporal_filters
        assert "resolution_height" in parsed.technical_filters
        assert "duration" in parsed.technical_filters
        
        # Convert to search query
        search_query = await nlp_service.convert_to_search_query(parsed)
        
        # Verify all filters are present
        filter_fields = [f["field"] for f in search_query.filters]
        assert "asset_type" in filter_fields
        assert "creator" in filter_fields
        assert "project_name" in filter_fields
        assert "created_at" in filter_fields
        assert "resolution_height" in filter_fields
        assert "duration" in filter_fields
    
    async def test_tag_extraction(self, nlp_service):
        """Test tag extraction from natural language"""
        query = "images tagged as nature, landscape"
        parsed = await nlp_service.parse_natural_language_query(query)
        
        assert "tags" in parsed.filters
        assert "nature" in parsed.filters["tags"]
        assert "landscape" in parsed.filters["tags"]
    
    async def test_format_extraction(self, nlp_service):
        """Test file format extraction"""
        test_cases = [
            ("MP4 videos", "mp4", "video_format"),
            ("JPG images", "jpg", "image_format"),
            ("PDF documents", "pdf", "document_format"),
            ("MP3 audio files", "mp3", "audio_format")
        ]
        
        for query, expected_format, expected_field in test_cases:
            parsed = await nlp_service.parse_natural_language_query(query)
            assert expected_field in parsed.filters
            assert parsed.filters[expected_field] == expected_format
    
    async def test_intent_based_facets(self, nlp_service):
        """Test that appropriate facets are generated based on intent"""
        test_cases = [
            (QueryIntent.FIND_BY_TYPE, ["file_extension", "mime_type"]),
            (QueryIntent.FIND_BY_PERSON, ["creator", "owner"]),
            (QueryIntent.FIND_BY_DATE, ["created_at"]),
            (QueryIntent.FIND_BY_TECHNICAL, ["resolution_height", "frame_rate", "codec"])
        ]
        
        for intent, expected_facet_fields in test_cases:
            parsed = ParsedQuery(
                original_query="test",
                intent=intent,
                keywords=["test"],
                entities={},
                filters={},
                temporal_filters={},
                technical_filters={},
                modifiers=[],
                confidence=0.8
            )
            
            search_query = await nlp_service.convert_to_search_query(parsed)
            facet_fields = [f["field"] for f in search_query.facets]
            
            for expected_field in expected_facet_fields:
                assert expected_field in facet_fields


@pytest.mark.asyncio
async def test_nlp_service_singleton():
    """Test that NLP service is a singleton"""
    service1 = await get_nlp_search_service()
    service2 = await get_nlp_search_service()
    
    assert service1 is service2


@pytest.mark.asyncio
async def test_edge_cases():
    """Test edge cases and error handling"""
    nlp_service = NLPSearchService()
    
    # Empty query
    parsed = await nlp_service.parse_natural_language_query("")
    assert parsed.confidence < 0.3
    assert len(parsed.keywords) == 0
    
    # Very long query
    long_query = " ".join(["word"] * 100)
    parsed = await nlp_service.parse_natural_language_query(long_query)
    assert parsed.original_query == long_query
    
    # Special characters
    special_query = "test @#$% query"
    parsed = await nlp_service.parse_natural_language_query(special_query)
    assert "test" in parsed.keywords
    assert "query" in parsed.keywords
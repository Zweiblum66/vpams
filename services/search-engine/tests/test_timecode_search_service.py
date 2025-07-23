"""
Tests for Timecode Search Service
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from src.services.timecode_search_service import TimecodeSearchService
from src.models.schemas import (
    TimecodeSearchQuery, TimecodeSearchResponse, TimecodeSearchResult,
    TimecodeSearchStats, TimecodeValidationResult, TimecodeConversionRequest,
    TimecodeConversionResponse, Timecode, TimecodeRange, TimecodeFormat,
    TimecodeRangeType, TimecodeSearchType, IndexType, SortOrder
)
from src.core.exceptions import SearchError, ValidationError


class TestTimecodeSearchService:
    """Test cases for TimecodeSearchService"""
    
    @pytest.fixture
    def mock_opensearch_client(self):
        """Mock OpenSearch client"""
        return AsyncMock()
    
    @pytest.fixture
    def timecode_search_service(self, mock_opensearch_client):
        """Create TimecodeSearchService instance"""
        return TimecodeSearchService(mock_opensearch_client)
    
    @pytest.fixture
    def sample_timecode(self):
        """Sample timecode object"""
        return Timecode(
            hours=1,
            minutes=23,
            seconds=45,
            frames=12,
            format=TimecodeFormat.NON_DROP_FRAME
        )
    
    @pytest.fixture
    def sample_timecode_range(self, sample_timecode):
        """Sample timecode range"""
        end_timecode = Timecode(
            hours=1,
            minutes=25,
            seconds=30,
            frames=24,
            format=TimecodeFormat.NON_DROP_FRAME
        )
        return TimecodeRange(
            start=sample_timecode,
            end=end_timecode,
            type=TimecodeRangeType.RANGE
        )
    
    @pytest.fixture
    def sample_search_query(self, sample_timecode):
        """Sample timecode search query"""
        return TimecodeSearchQuery(
            search_type=TimecodeSearchType.SIMPLE,
            timecode=sample_timecode,
            tolerance_seconds=1.0,
            asset_types=["video"],
            frame_rates=[24.0, 29.97, 30.0],
            page=1,
            limit=20
        )
    
    @pytest.fixture
    def sample_opensearch_response(self):
        """Sample OpenSearch response"""
        return {
            "took": 45,
            "hits": {
                "total": {"value": 150},
                "hits": [
                    {
                        "_id": "asset-123",
                        "_score": 1.5,
                        "_source": {
                            "id": "asset-123",
                            "name": "Test Video",
                            "asset_type": "video",
                            "duration": 1800.0,
                            "frame_rate": 29.97,
                            "timecode_format": "non_drop_frame",
                            "timecode_start": 5025.4,
                            "timecode_end": 6825.4,
                            "resolution": "1920x1080",
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z",
                            "metadata": {
                                "codec": "H.264",
                                "bitrate": 5000000
                            }
                        }
                    },
                    {
                        "_id": "asset-456",
                        "_score": 1.2,
                        "_source": {
                            "id": "asset-456",
                            "name": "Another Video",
                            "asset_type": "video",
                            "duration": 3600.0,
                            "frame_rate": 24.0,
                            "timecode_format": "film",
                            "timecode_start": 0.0,
                            "timecode_end": 3600.0,
                            "resolution": "3840x2160",
                            "created_at": "2024-01-15T11:30:00Z",
                            "updated_at": "2024-01-15T11:30:00Z",
                            "metadata": {
                                "codec": "H.265",
                                "bitrate": 10000000
                            }
                        }
                    }
                ]
            },
            "aggregations": {
                "duration_stats": {
                    "min": 60.0,
                    "max": 7200.0,
                    "avg": 1800.0,
                    "count": 150
                },
                "frame_rate_distribution": {
                    "buckets": [
                        {"key": 29.97, "doc_count": 75},
                        {"key": 24.0, "doc_count": 45},
                        {"key": 30.0, "doc_count": 30}
                    ]
                },
                "format_distribution": {
                    "buckets": [
                        {"key": "non_drop_frame", "doc_count": 100},
                        {"key": "film", "doc_count": 50}
                    ]
                }
            }
        }
    
    @pytest.mark.asyncio
    async def test_search_by_timecode_simple(self, timecode_search_service, sample_search_query, sample_opensearch_response, mock_opensearch_client):
        """Test simple timecode search"""
        # Mock OpenSearch response
        mock_opensearch_client.search.return_value = sample_opensearch_response
        
        # Execute search
        result = await timecode_search_service.search_by_timecode(sample_search_query)
        
        # Verify result
        assert isinstance(result, TimecodeSearchResponse)
        assert result.total == 150
        assert len(result.results) == 2
        assert result.took == 45
        assert result.page == 1
        assert result.limit == 20
        assert result.pages == 8  # (150 + 20 - 1) // 20
        
        # Verify first result
        first_result = result.results[0]
        assert first_result.asset_id == "asset-123"
        assert first_result.asset_name == "Test Video"
        assert first_result.asset_type == "video"
        assert first_result.duration == 1800.0
        assert first_result.frame_rate == 29.97
        assert first_result.timecode_format == TimecodeFormat.NON_DROP_FRAME
        assert first_result.match_score == 1.5
        
        # Verify OpenSearch was called correctly
        mock_opensearch_client.search.assert_called_once()
        call_args = mock_opensearch_client.search.call_args
        assert "assets" in call_args[1]["index"]
        assert call_args[1]["body"]["size"] == 20
        assert call_args[1]["body"]["from"] == 0
    
    @pytest.mark.asyncio
    async def test_search_by_timecode_range(self, timecode_search_service, sample_timecode_range, mock_opensearch_client):
        """Test timecode range search"""
        # Create range search query
        query = TimecodeSearchQuery(
            search_type=TimecodeSearchType.ADVANCED,
            timecode_range=sample_timecode_range,
            tolerance_seconds=0.5,
            asset_types=["video", "audio"],
            page=2,
            limit=10
        )
        
        # Mock OpenSearch response
        mock_response = {
            "took": 30,
            "hits": {
                "total": {"value": 50},
                "hits": []
            },
            "aggregations": {}
        }
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await timecode_search_service.search_by_timecode(query)
        
        # Verify result
        assert result.total == 50
        assert result.page == 2
        assert result.limit == 10
        assert result.pages == 5
        
        # Verify OpenSearch query structure
        call_args = mock_opensearch_client.search.call_args[1]["body"]
        assert call_args["from"] == 10  # (page - 1) * limit
        assert call_args["size"] == 10
        
        # Verify range filter was applied
        bool_query = call_args["query"]["bool"]
        assert "filter" in bool_query
        assert len(bool_query["filter"]) > 0
    
    @pytest.mark.asyncio
    async def test_search_by_duration(self, timecode_search_service, mock_opensearch_client):
        """Test duration-based search"""
        # Create duration search query
        query = TimecodeSearchQuery(
            search_type=TimecodeSearchType.SIMPLE,
            min_duration=60.0,
            max_duration=3600.0,
            asset_types=["video"],
            sort_by="duration",
            sort_order=SortOrder.ASC
        )
        
        # Mock OpenSearch response
        mock_response = {
            "took": 25,
            "hits": {
                "total": {"value": 25},
                "hits": []
            },
            "aggregations": {}
        }
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await timecode_search_service.search_by_timecode(query)
        
        # Verify result
        assert result.total == 25
        
        # Verify duration filters were applied
        call_args = mock_opensearch_client.search.call_args[1]["body"]
        filters = call_args["query"]["bool"]["filter"]
        
        # Check for duration filters
        duration_filters = [f for f in filters if "duration" in f.get("range", {})]
        assert len(duration_filters) == 2  # min and max duration
        
        # Verify sorting
        sort_clause = call_args["sort"]
        assert {"duration": {"order": "asc"}} in sort_clause
    
    @pytest.mark.asyncio
    async def test_search_segment_type(self, timecode_search_service, mock_opensearch_client):
        """Test segment search type"""
        # Create segment search query
        query = TimecodeSearchQuery(
            search_type=TimecodeSearchType.SEGMENT,
            segment_markers=["intro", "outro"],
            chapter_titles=["Chapter 1", "Conclusion"],
            asset_types=["video"]
        )
        
        # Mock OpenSearch response
        mock_response = {
            "took": 35,
            "hits": {
                "total": {"value": 10},
                "hits": []
            },
            "aggregations": {}
        }
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await timecode_search_service.search_by_timecode(query)
        
        # Verify result
        assert result.total == 10
        
        # Verify nested queries for segments
        call_args = mock_opensearch_client.search.call_args[1]["body"]
        should_queries = call_args["query"]["bool"]["should"]
        
        # Check for nested marker queries
        marker_queries = [q for q in should_queries if "nested" in q and "markers" in q["nested"]["path"]]
        assert len(marker_queries) > 0
    
    @pytest.mark.asyncio
    async def test_search_subtitle_type(self, timecode_search_service, mock_opensearch_client):
        """Test subtitle search type"""
        # Create subtitle search query
        query = TimecodeSearchQuery(
            search_type=TimecodeSearchType.SUBTITLE,
            subtitle_text="important dialogue",
            subtitle_language="en",
            asset_types=["video"]
        )
        
        # Mock OpenSearch response
        mock_response = {
            "took": 40,
            "hits": {
                "total": {"value": 5},
                "hits": []
            },
            "aggregations": {}
        }
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await timecode_search_service.search_by_timecode(query)
        
        # Verify result
        assert result.total == 5
        
        # Verify nested queries for subtitles
        call_args = mock_opensearch_client.search.call_args[1]["body"]
        should_queries = call_args["query"]["bool"]["should"]
        
        # Check for nested subtitle queries
        subtitle_queries = [q for q in should_queries if "nested" in q and "subtitles" in q["nested"]["path"]]
        assert len(subtitle_queries) > 0
    
    @pytest.mark.asyncio
    async def test_validate_timecode_valid(self, timecode_search_service):
        """Test timecode validation with valid timecode"""
        result = await timecode_search_service.validate_timecode("01:23:45:12", TimecodeFormat.NON_DROP_FRAME)
        
        assert result.is_valid == True
        assert len(result.errors) == 0
        assert result.normalized_timecode == "01:23:45:12"
        assert result.total_seconds is not None
        assert result.total_frames is not None
        assert result.detected_format == TimecodeFormat.NON_DROP_FRAME
    
    @pytest.mark.asyncio
    async def test_validate_timecode_invalid_format(self, timecode_search_service):
        """Test timecode validation with invalid format"""
        result = await timecode_search_service.validate_timecode("1:23:45:12", TimecodeFormat.NON_DROP_FRAME)
        
        assert result.is_valid == False
        assert len(result.errors) > 0
        assert "HH:MM:SS:FF" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_validate_timecode_drop_frame_detection(self, timecode_search_service):
        """Test drop frame timecode detection"""
        result = await timecode_search_service.validate_timecode("01:23:45;12", TimecodeFormat.NON_DROP_FRAME)
        
        assert result.is_valid == True
        assert len(result.warnings) > 0
        assert "drop frame" in result.warnings[0]
        assert result.detected_format == TimecodeFormat.DROP_FRAME
    
    @pytest.mark.asyncio
    async def test_validate_timecode_frame_validation(self, timecode_search_service):
        """Test frame validation for different formats"""
        # Test invalid frame for film format
        result = await timecode_search_service.validate_timecode("01:23:45:25", TimecodeFormat.FILM)
        
        assert result.is_valid == False
        assert len(result.errors) > 0
        assert "invalid for film format" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_convert_timecode_same_format(self, timecode_search_service):
        """Test timecode conversion between same formats"""
        request = TimecodeConversionRequest(
            source_timecode="01:23:45:12",
            source_format=TimecodeFormat.NON_DROP_FRAME,
            target_format=TimecodeFormat.NON_DROP_FRAME
        )
        
        result = await timecode_search_service.convert_timecode(request)
        
        assert result.source_timecode == "01:23:45:12"
        assert result.target_timecode == "01:23:45:12"
        assert result.source_format == TimecodeFormat.NON_DROP_FRAME
        assert result.target_format == TimecodeFormat.NON_DROP_FRAME
        assert result.precision_loss == False
    
    @pytest.mark.asyncio
    async def test_convert_timecode_different_formats(self, timecode_search_service):
        """Test timecode conversion between different formats"""
        request = TimecodeConversionRequest(
            source_timecode="01:00:00:00",
            source_format=TimecodeFormat.FILM,
            target_format=TimecodeFormat.PAL
        )
        
        result = await timecode_search_service.convert_timecode(request)
        
        assert result.source_timecode == "01:00:00:00"
        assert result.target_timecode != "01:00:00:00"  # Should be different due to frame rate
        assert result.source_format == TimecodeFormat.FILM
        assert result.target_format == TimecodeFormat.PAL
        assert result.precision_loss == True
        assert len(result.warnings) > 0
    
    @pytest.mark.asyncio
    async def test_convert_timecode_invalid_source(self, timecode_search_service):
        """Test timecode conversion with invalid source"""
        request = TimecodeConversionRequest(
            source_timecode="invalid",
            source_format=TimecodeFormat.NON_DROP_FRAME,
            target_format=TimecodeFormat.PAL
        )
        
        with pytest.raises(ValidationError):
            await timecode_search_service.convert_timecode(request)
    
    @pytest.mark.asyncio
    async def test_get_timecode_stats(self, timecode_search_service, mock_opensearch_client):
        """Test getting timecode statistics"""
        # Mock OpenSearch response
        mock_response = {
            "hits": {
                "total": {"value": 1000}
            },
            "aggregations": {
                "duration_stats": {
                    "min": 30.0,
                    "max": 7200.0,
                    "avg": 1800.0,
                    "count": 1000
                },
                "frame_rate_distribution": {
                    "buckets": [
                        {"key": 29.97, "doc_count": 500},
                        {"key": 24.0, "doc_count": 300},
                        {"key": 30.0, "doc_count": 200}
                    ]
                },
                "format_distribution": {
                    "buckets": [
                        {"key": "non_drop_frame", "doc_count": 600},
                        {"key": "film", "doc_count": 300},
                        {"key": "pal", "doc_count": 100}
                    ]
                }
            }
        }
        mock_opensearch_client.search.return_value = mock_response
        
        # Get stats
        result = await timecode_search_service.get_timecode_stats()
        
        # Verify result
        assert isinstance(result, TimecodeSearchStats)
        assert result.total_assets_with_timecode == 1000
        assert result.avg_duration == 1800.0
        assert result.min_duration == 30.0
        assert result.max_duration == 7200.0
        assert result.most_common_frame_rate == 29.97
        assert result.most_common_format == TimecodeFormat.NON_DROP_FRAME
        assert "29.97" in result.frame_rate_distribution
        assert "non_drop_frame" in result.format_distribution
    
    @pytest.mark.asyncio
    async def test_search_error_handling(self, timecode_search_service, sample_search_query, mock_opensearch_client):
        """Test error handling in search"""
        # Mock OpenSearch to raise an exception
        mock_opensearch_client.search.side_effect = Exception("Connection failed")
        
        # Execute search and expect SearchError
        with pytest.raises(SearchError):
            await timecode_search_service.search_by_timecode(sample_search_query)
    
    @pytest.mark.asyncio
    async def test_build_query_with_all_filters(self, timecode_search_service, sample_timecode_range):
        """Test building query with all possible filters"""
        # Create comprehensive query
        query = TimecodeSearchQuery(
            search_type=TimecodeSearchType.ADVANCED,
            timecode_range=sample_timecode_range,
            min_duration=60.0,
            max_duration=3600.0,
            tolerance_seconds=0.5,
            asset_types=["video", "audio"],
            video_formats=["mp4", "mov"],
            audio_formats=["wav", "mp3"],
            frame_rates=[24.0, 29.97],
            resolutions=["1920x1080", "3840x2160"],
            sort_by="duration",
            sort_order=SortOrder.DESC
        )
        
        # Build query
        search_body = await timecode_search_service._build_timecode_query(query)
        
        # Verify query structure
        assert "query" in search_body
        assert "bool" in search_body["query"]
        assert "filter" in search_body["query"]["bool"]
        assert "sort" in search_body
        assert "aggs" in search_body
        
        # Verify filters were applied
        filters = search_body["query"]["bool"]["filter"]
        assert len(filters) > 0
        
        # Verify sorting
        sort_clause = search_body["sort"]
        assert {"duration": {"order": "desc"}} in sort_clause
        
        # Verify aggregations
        aggs = search_body["aggs"]
        assert "duration_stats" in aggs
        assert "frame_rate_distribution" in aggs
        assert "format_distribution" in aggs
    
    @pytest.mark.asyncio
    async def test_process_search_results_with_segments(self, timecode_search_service):
        """Test processing search results with segment information"""
        # Mock OpenSearch response with segment data
        response = {
            "hits": {
                "hits": [
                    {
                        "_id": "asset-123",
                        "_score": 1.5,
                        "_source": {
                            "id": "asset-123",
                            "name": "Test Video",
                            "asset_type": "video",
                            "duration": 1800.0,
                            "frame_rate": 29.97,
                            "timecode_format": "non_drop_frame",
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z",
                            "markers": [
                                {"name": "intro", "timecode": "00:00:10:00"},
                                {"name": "outro", "timecode": "00:28:50:00"}
                            ],
                            "chapters": [
                                {"title": "Introduction", "description": "Opening segment"}
                            ]
                        }
                    }
                ]
            }
        }
        
        # Create segment search query
        query = TimecodeSearchQuery(
            search_type=TimecodeSearchType.SEGMENT,
            segment_markers=["intro"],
            chapter_titles=["Introduction"]
        )
        
        # Process results
        results = await timecode_search_service._process_search_results(response, query)
        
        # Verify segment information was extracted
        assert len(results) == 1
        result = results[0]
        assert result.segment_title == "Introduction"
        assert result.segment_description == "Opening segment"
        assert result.markers is not None
        assert len(result.markers) == 2
    
    @pytest.mark.asyncio
    async def test_process_search_results_with_subtitles(self, timecode_search_service):
        """Test processing search results with subtitle information"""
        # Mock OpenSearch response with subtitle data
        response = {
            "hits": {
                "hits": [
                    {
                        "_id": "asset-456",
                        "_score": 1.2,
                        "_source": {
                            "id": "asset-456",
                            "name": "Test Video",
                            "asset_type": "video",
                            "duration": 1800.0,
                            "frame_rate": 29.97,
                            "timecode_format": "non_drop_frame",
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z",
                            "subtitles": [
                                {
                                    "text": "This is important dialogue",
                                    "start_time": "00:01:30:00",
                                    "end_time": "00:01:33:00",
                                    "language": "en"
                                },
                                {
                                    "text": "Another subtitle",
                                    "start_time": "00:02:00:00",
                                    "end_time": "00:02:03:00",
                                    "language": "en"
                                }
                            ]
                        }
                    }
                ]
            }
        }
        
        # Create subtitle search query
        query = TimecodeSearchQuery(
            search_type=TimecodeSearchType.SUBTITLE,
            subtitle_text="important dialogue",
            subtitle_language="en"
        )
        
        # Process results
        results = await timecode_search_service._process_search_results(response, query)
        
        # Verify subtitle information was extracted
        assert len(results) == 1
        result = results[0]
        assert result.subtitle_matches is not None
        assert len(result.subtitle_matches) == 1
        assert result.subtitle_matches[0]["text"] == "This is important dialogue"
        assert result.subtitle_matches[0]["language"] == "en"


class TestTimecodeModel:
    """Test cases for Timecode model"""
    
    def test_timecode_creation(self):
        """Test creating a timecode object"""
        timecode = Timecode(
            hours=1,
            minutes=23,
            seconds=45,
            frames=12,
            format=TimecodeFormat.NON_DROP_FRAME
        )
        
        assert timecode.hours == 1
        assert timecode.minutes == 23
        assert timecode.seconds == 45
        assert timecode.frames == 12
        assert timecode.format == TimecodeFormat.NON_DROP_FRAME
    
    def test_timecode_to_seconds(self):
        """Test converting timecode to seconds"""
        timecode = Timecode(
            hours=1,
            minutes=0,
            seconds=0,
            frames=0,
            format=TimecodeFormat.NON_DROP_FRAME
        )
        
        assert timecode.to_seconds() == 3600.0
    
    def test_timecode_to_frames(self):
        """Test converting timecode to frames"""
        timecode = Timecode(
            hours=0,
            minutes=0,
            seconds=1,
            frames=0,
            format=TimecodeFormat.NON_DROP_FRAME
        )
        
        assert timecode.to_frames() == 30  # 1 second * 30fps
    
    def test_timecode_string_representation(self):
        """Test timecode string representation"""
        timecode = Timecode(
            hours=1,
            minutes=23,
            seconds=45,
            frames=12,
            format=TimecodeFormat.NON_DROP_FRAME
        )
        
        assert str(timecode) == "01:23:45:12"
    
    def test_timecode_drop_frame_string(self):
        """Test drop frame timecode string representation"""
        timecode = Timecode(
            hours=1,
            minutes=23,
            seconds=45,
            frames=12,
            format=TimecodeFormat.DROP_FRAME
        )
        
        assert str(timecode) == "01:23:45;12"
    
    def test_timecode_from_string(self):
        """Test creating timecode from string"""
        timecode = Timecode.from_string("01:23:45:12", TimecodeFormat.NON_DROP_FRAME)
        
        assert timecode.hours == 1
        assert timecode.minutes == 23
        assert timecode.seconds == 45
        assert timecode.frames == 12
        assert timecode.format == TimecodeFormat.NON_DROP_FRAME
    
    def test_timecode_from_string_drop_frame(self):
        """Test creating drop frame timecode from string"""
        timecode = Timecode.from_string("01:23:45;12")
        
        assert timecode.hours == 1
        assert timecode.minutes == 23
        assert timecode.seconds == 45
        assert timecode.frames == 12
        assert timecode.format == TimecodeFormat.DROP_FRAME
    
    def test_timecode_from_seconds(self):
        """Test creating timecode from seconds"""
        timecode = Timecode.from_seconds(3661.5, TimecodeFormat.NON_DROP_FRAME)
        
        assert timecode.hours == 1
        assert timecode.minutes == 1
        assert timecode.seconds == 1
        assert timecode.frames == 15  # 0.5 seconds * 30fps
    
    def test_timecode_validation_invalid_format(self):
        """Test timecode validation with invalid format"""
        with pytest.raises(ValueError):
            Timecode.from_string("1:23:45:12")  # Missing leading zero
    
    def test_timecode_validation_invalid_frames(self):
        """Test timecode validation with invalid frames"""
        with pytest.raises(ValueError):
            Timecode(
                hours=1,
                minutes=23,
                seconds=45,
                frames=25,  # Invalid for film format
                format=TimecodeFormat.FILM
            )


class TestTimecodeRange:
    """Test cases for TimecodeRange model"""
    
    def test_timecode_range_creation(self):
        """Test creating a timecode range"""
        start = Timecode(hours=1, minutes=0, seconds=0, frames=0)
        end = Timecode(hours=1, minutes=30, seconds=0, frames=0)
        
        range_obj = TimecodeRange(start=start, end=end)
        
        assert range_obj.start == start
        assert range_obj.end == end
        assert range_obj.type == TimecodeRangeType.RANGE
    
    def test_timecode_range_duration(self):
        """Test calculating timecode range duration"""
        start = Timecode(hours=1, minutes=0, seconds=0, frames=0)
        end = Timecode(hours=1, minutes=30, seconds=0, frames=0)
        
        range_obj = TimecodeRange(start=start, end=end)
        
        assert range_obj.duration() == 1800.0  # 30 minutes
    
    def test_timecode_range_contains(self):
        """Test checking if range contains a timecode"""
        start = Timecode(hours=1, minutes=0, seconds=0, frames=0)
        end = Timecode(hours=1, minutes=30, seconds=0, frames=0)
        test_timecode = Timecode(hours=1, minutes=15, seconds=0, frames=0)
        
        range_obj = TimecodeRange(start=start, end=end)
        
        assert range_obj.contains_timecode(test_timecode) == True
    
    def test_timecode_range_overlaps(self):
        """Test checking if ranges overlap"""
        range1 = TimecodeRange(
            start=Timecode(hours=1, minutes=0, seconds=0, frames=0),
            end=Timecode(hours=1, minutes=30, seconds=0, frames=0)
        )
        range2 = TimecodeRange(
            start=Timecode(hours=1, minutes=15, seconds=0, frames=0),
            end=Timecode(hours=1, minutes=45, seconds=0, frames=0)
        )
        
        assert range1.overlaps_with(range2) == True
    
    def test_timecode_range_validation(self):
        """Test timecode range validation"""
        start = Timecode(hours=1, minutes=30, seconds=0, frames=0)
        end = Timecode(hours=1, minutes=0, seconds=0, frames=0)  # End before start
        
        with pytest.raises(ValueError):
            TimecodeRange(start=start, end=end)
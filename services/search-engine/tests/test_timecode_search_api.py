"""
Tests for Timecode Search API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json
from datetime import datetime

from src.main import app
from src.models.schemas import (
    TimecodeSearchResponse, TimecodeSearchResult, TimecodeSearchStats,
    TimecodeValidationResult, TimecodeConversionResponse, TimecodeFormat
)


class TestTimecodeSearchAPI:
    """Test cases for Timecode Search API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_timecode_search_data(self):
        """Sample timecode search request data"""
        return {
            "search_type": "simple",
            "timecode": {
                "hours": 1,
                "minutes": 23,
                "seconds": 45,
                "frames": 12,
                "format": "non_drop_frame"
            },
            "tolerance_seconds": 1.0,
            "asset_types": ["video"],
            "frame_rates": [24.0, 29.97, 30.0],
            "page": 1,
            "limit": 20
        }
    
    @pytest.fixture
    def sample_timecode_range_data(self):
        """Sample timecode range search request data"""
        return {
            "search_type": "advanced",
            "timecode_range": {
                "start": {
                    "hours": 1,
                    "minutes": 0,
                    "seconds": 0,
                    "frames": 0,
                    "format": "non_drop_frame"
                },
                "end": {
                    "hours": 1,
                    "minutes": 30,
                    "seconds": 0,
                    "frames": 0,
                    "format": "non_drop_frame"
                },
                "type": "range"
            },
            "asset_types": ["video"],
            "tolerance_seconds": 0.5
        }
    
    @pytest.fixture
    def sample_duration_search_data(self):
        """Sample duration search request data"""
        return {
            "search_type": "simple",
            "min_duration": 60.0,
            "max_duration": 3600.0,
            "asset_types": ["video"],
            "sort_by": "duration",
            "sort_order": "asc",
            "page": 1,
            "limit": 10
        }
    
    @pytest.fixture
    def sample_search_response(self):
        """Sample timecode search response"""
        return TimecodeSearchResponse(
            results=[
                TimecodeSearchResult(
                    asset_id="asset-123",
                    asset_name="Test Video",
                    asset_type="video",
                    duration=1800.0,
                    duration_timecode="00:30:00:00",
                    frame_rate=29.97,
                    timecode_format=TimecodeFormat.NON_DROP_FRAME,
                    matched_timecode="01:23:45:12",
                    matched_range=None,
                    match_score=1.5,
                    match_type="exact_timecode",
                    segment_title=None,
                    segment_description=None,
                    markers=None,
                    subtitle_matches=None,
                    metadata={"codec": "H.264"},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            ],
            total=1,
            took=45,
            page=1,
            limit=20,
            pages=1,
            aggregations={},
            search_metadata={"search_type": "simple"}
        )
    
    @patch('src.services.timecode_search_service.get_timecode_search_service')
    def test_search_by_timecode_simple(self, mock_get_service, client, sample_timecode_search_data, sample_search_response):
        """Test simple timecode search"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_timecode.return_value = sample_search_response
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/timecode", json=sample_timecode_search_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["asset_id"] == "asset-123"
        assert data["results"][0]["asset_name"] == "Test Video"
        assert data["results"][0]["matched_timecode"] == "01:23:45:12"
        assert data["results"][0]["match_type"] == "exact_timecode"
        assert data["took"] == 45
        
        # Verify service was called
        mock_service.search_by_timecode.assert_called_once()
    
    @patch('src.services.timecode_search_service.get_timecode_search_service')
    def test_search_by_timecode_range(self, mock_get_service, client, sample_timecode_range_data):
        """Test timecode range search"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_timecode.return_value = TimecodeSearchResponse(
            results=[],
            total=0,
            took=30,
            page=1,
            limit=20,
            pages=0,
            aggregations={},
            search_metadata={"search_type": "advanced"}
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/timecode", json=sample_timecode_range_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["results"]) == 0
        assert data["search_metadata"]["search_type"] == "advanced"
        
        # Verify service was called with correct parameters
        mock_service.search_by_timecode.assert_called_once()
        call_args = mock_service.search_by_timecode.call_args[0][0]
        assert call_args.search_type.value == "advanced"
        assert call_args.timecode_range is not None
        assert call_args.tolerance_seconds == 0.5
    
    @patch('src.services.timecode_search_service.get_timecode_search_service')
    def test_search_by_duration(self, mock_get_service, client, sample_duration_search_data):
        """Test duration-based search"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_timecode.return_value = TimecodeSearchResponse(
            results=[],
            total=25,
            took=25,
            page=1,
            limit=10,
            pages=3,
            aggregations={},
            search_metadata={"search_type": "simple"}
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/timecode", json=sample_duration_search_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 25
        assert data["limit"] == 10
        assert data["pages"] == 3
        
        # Verify service was called with duration filters
        mock_service.search_by_timecode.assert_called_once()
        call_args = mock_service.search_by_timecode.call_args[0][0]
        assert call_args.min_duration == 60.0
        assert call_args.max_duration == 3600.0
        assert call_args.sort_by == "duration"
        assert call_args.sort_order.value == "asc"
    
    @patch('src.services.timecode_search_service.get_timecode_search_service')
    def test_search_segment_type(self, mock_get_service, client):
        """Test segment search type"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_timecode.return_value = TimecodeSearchResponse(
            results=[
                TimecodeSearchResult(
                    asset_id="asset-456",
                    asset_name="Segmented Video",
                    asset_type="video",
                    duration=3600.0,
                    duration_timecode="01:00:00:00",
                    frame_rate=24.0,
                    timecode_format=TimecodeFormat.FILM,
                    matched_timecode=None,
                    matched_range=None,
                    match_score=1.2,
                    match_type="segment",
                    segment_title="Introduction",
                    segment_description="Opening segment",
                    markers=[{"name": "intro", "timecode": "00:00:10:00"}],
                    subtitle_matches=None,
                    metadata={},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            ],
            total=1,
            took=35,
            page=1,
            limit=20,
            pages=1,
            aggregations={},
            search_metadata={"search_type": "segment"}
        )
        mock_get_service.return_value = mock_service
        
        # Create segment search request
        segment_data = {
            "search_type": "segment",
            "segment_markers": ["intro", "outro"],
            "chapter_titles": ["Introduction", "Conclusion"],
            "asset_types": ["video"]
        }
        
        # Make request
        response = client.post("/search/timecode", json=segment_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["results"][0]["segment_title"] == "Introduction"
        assert data["results"][0]["segment_description"] == "Opening segment"
        assert data["results"][0]["markers"] is not None
        assert len(data["results"][0]["markers"]) == 1
        
        # Verify service was called with segment parameters
        mock_service.search_by_timecode.assert_called_once()
        call_args = mock_service.search_by_timecode.call_args[0][0]
        assert call_args.search_type.value == "segment"
        assert call_args.segment_markers == ["intro", "outro"]
        assert call_args.chapter_titles == ["Introduction", "Conclusion"]
    
    @patch('src.services.timecode_search_service.get_timecode_search_service')
    def test_search_subtitle_type(self, mock_get_service, client):
        """Test subtitle search type"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_timecode.return_value = TimecodeSearchResponse(
            results=[
                TimecodeSearchResult(
                    asset_id="asset-789",
                    asset_name="Subtitled Video",
                    asset_type="video",
                    duration=1800.0,
                    duration_timecode="00:30:00:00",
                    frame_rate=29.97,
                    timecode_format=TimecodeFormat.NON_DROP_FRAME,
                    matched_timecode=None,
                    matched_range=None,
                    match_score=1.8,
                    match_type="subtitle",
                    segment_title=None,
                    segment_description=None,
                    markers=None,
                    subtitle_matches=[
                        {
                            "text": "This is important dialogue",
                            "start_time": "00:01:30:00",
                            "end_time": "00:01:33:00",
                            "language": "en"
                        }
                    ],
                    metadata={},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            ],
            total=1,
            took=40,
            page=1,
            limit=20,
            pages=1,
            aggregations={},
            search_metadata={"search_type": "subtitle"}
        )
        mock_get_service.return_value = mock_service
        
        # Create subtitle search request
        subtitle_data = {
            "search_type": "subtitle",
            "subtitle_text": "important dialogue",
            "subtitle_language": "en",
            "asset_types": ["video"]
        }
        
        # Make request
        response = client.post("/search/timecode", json=subtitle_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["results"][0]["subtitle_matches"] is not None
        assert len(data["results"][0]["subtitle_matches"]) == 1
        assert data["results"][0]["subtitle_matches"][0]["text"] == "This is important dialogue"
        assert data["results"][0]["subtitle_matches"][0]["language"] == "en"
        
        # Verify service was called with subtitle parameters
        mock_service.search_by_timecode.assert_called_once()
        call_args = mock_service.search_by_timecode.call_args[0][0]
        assert call_args.search_type.value == "subtitle"
        assert call_args.subtitle_text == "important dialogue"
        assert call_args.subtitle_language == "en"
    
    @patch('src.services.timecode_search_service.get_timecode_search_service')
    def test_search_invalid_data(self, mock_get_service, client):
        """Test search with invalid data"""
        # Mock service
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        
        # Make request with invalid data
        invalid_data = {
            "search_type": "invalid_type",
            "timecode": {
                "hours": 25,  # Invalid hours
                "minutes": 0,
                "seconds": 0,
                "frames": 0
            }
        }
        
        response = client.post("/search/timecode", json=invalid_data)
        
        # Verify response
        assert response.status_code == 422  # Validation error
    
    @patch('src.services.timecode_search_service.get_timecode_search_service')
    def test_validate_timecode_valid(self, mock_get_service, client):
        """Test timecode validation with valid timecode"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.validate_timecode.return_value = TimecodeValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            normalized_timecode="01:23:45:12",
            total_seconds=5025.4,
            total_frames=150762,
            detected_format=TimecodeFormat.NON_DROP_FRAME,
            suggested_format=TimecodeFormat.NON_DROP_FRAME
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/timecode/validate", params={
            "timecode": "01:23:45:12",
            "format": "non_drop_frame"
        })
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] == True
        assert len(data["errors"]) == 0
        assert data["normalized_timecode"] == "01:23:45:12"
        assert data["total_seconds"] == 5025.4
        assert data["total_frames"] == 150762
        assert data["detected_format"] == "non_drop_frame"
        
        # Verify service was called
        mock_service.validate_timecode.assert_called_once_with("01:23:45:12", TimecodeFormat.NON_DROP_FRAME)
    
    @patch('src.services.timecode_search_service.get_timecode_search_service')
    def test_validate_timecode_invalid(self, mock_get_service, client):
        """Test timecode validation with invalid timecode"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.validate_timecode.return_value = TimecodeValidationResult(
            is_valid=False,
            errors=["Timecode must be in HH:MM:SS:FF format"],
            warnings=[],
            normalized_timecode=None,
            total_seconds=None,
            total_frames=None,
            detected_format=None,
            suggested_format=TimecodeFormat.NON_DROP_FRAME
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/timecode/validate", params={
            "timecode": "1:23:45:12",  # Invalid format
            "format": "non_drop_frame"
        })
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] == False
        assert len(data["errors"]) == 1
        assert "HH:MM:SS:FF format" in data["errors"][0]
        assert data["normalized_timecode"] is None
        
        # Verify service was called
        mock_service.validate_timecode.assert_called_once_with("1:23:45:12", TimecodeFormat.NON_DROP_FRAME)
    
    @patch('src.services.timecode_search_service.get_timecode_search_service')
    def test_validate_timecode_with_warnings(self, mock_get_service, client):
        """Test timecode validation with warnings"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.validate_timecode.return_value = TimecodeValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Semicolon separator detected but format is not drop frame"],
            normalized_timecode="01:23:45:12",
            total_seconds=5025.4,
            total_frames=150762,
            detected_format=TimecodeFormat.DROP_FRAME,
            suggested_format=TimecodeFormat.NON_DROP_FRAME
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/timecode/validate", params={
            "timecode": "01:23:45;12",  # Drop frame format
            "format": "non_drop_frame"
        })
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] == True
        assert len(data["warnings"]) == 1
        assert "drop frame" in data["warnings"][0]
        assert data["detected_format"] == "drop_frame"
        
        # Verify service was called
        mock_service.validate_timecode.assert_called_once_with("01:23:45;12", TimecodeFormat.NON_DROP_FRAME)
    
    @patch('src.services.timecode_search_service.get_timecode_search_service')
    def test_convert_timecode_success(self, mock_get_service, client):
        """Test successful timecode conversion"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.convert_timecode.return_value = TimecodeConversionResponse(
            source_timecode="01:00:00:00",
            target_timecode="01:00:00:00",
            source_format=TimecodeFormat.FILM,
            target_format=TimecodeFormat.PAL,
            source_seconds=3600.0,
            target_seconds=3456.0,
            source_frames=86400,
            target_frames=86400,
            conversion_method="frame_rate_conversion",
            precision_loss=True,
            warnings=["Precision loss possible when converting from 24.0fps to 25.0fps"]
        )
        mock_get_service.return_value = mock_service
        
        # Create conversion request
        conversion_data = {
            "source_timecode": "01:00:00:00",
            "source_format": "film",
            "target_format": "pal"
        }
        
        # Make request
        response = client.post("/search/timecode/convert", json=conversion_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["source_timecode"] == "01:00:00:00"
        assert data["target_timecode"] == "01:00:00:00"
        assert data["source_format"] == "film"
        assert data["target_format"] == "pal"
        assert data["precision_loss"] == True
        assert len(data["warnings"]) == 1
        assert "Precision loss possible" in data["warnings"][0]
        
        # Verify service was called
        mock_service.convert_timecode.assert_called_once()
    
    @patch('src.services.timecode_search_service.get_timecode_search_service')
    def test_convert_timecode_invalid_source(self, mock_get_service, client):
        """Test timecode conversion with invalid source"""
        # Mock service to raise validation error
        mock_service = AsyncMock()
        mock_service.convert_timecode.side_effect = Exception("Invalid timecode format")
        mock_get_service.return_value = mock_service
        
        # Create conversion request with invalid source
        conversion_data = {
            "source_timecode": "invalid",
            "source_format": "non_drop_frame",
            "target_format": "pal"
        }
        
        # Make request
        response = client.post("/search/timecode/convert", json=conversion_data)
        
        # Verify response
        assert response.status_code == 500
        data = response.json()
        assert "Timecode conversion failed" in data["detail"]
    
    @patch('src.services.timecode_search_service.get_timecode_search_service')
    def test_get_timecode_stats(self, mock_get_service, client):
        """Test getting timecode statistics"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.get_timecode_stats.return_value = TimecodeSearchStats(
            total_searches=1000,
            total_assets_with_timecode=2500,
            avg_duration=1800.0,
            min_duration=30.0,
            max_duration=7200.0,
            frame_rate_distribution={
                "29.97": 1000,
                "24.0": 800,
                "30.0": 700
            },
            most_common_frame_rate=29.97,
            format_distribution={
                "non_drop_frame": 1500,
                "film": 800,
                "pal": 200
            },
            most_common_format=TimecodeFormat.NON_DROP_FRAME,
            avg_search_time_ms=45.0,
            cache_hit_rate=0.85
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.get("/search/timecode/stats")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_searches"] == 1000
        assert data["total_assets_with_timecode"] == 2500
        assert data["avg_duration"] == 1800.0
        assert data["min_duration"] == 30.0
        assert data["max_duration"] == 7200.0
        assert data["most_common_frame_rate"] == 29.97
        assert data["most_common_format"] == "non_drop_frame"
        assert data["avg_search_time_ms"] == 45.0
        assert data["cache_hit_rate"] == 0.85
        
        # Verify frame rate distribution
        assert "29.97" in data["frame_rate_distribution"]
        assert data["frame_rate_distribution"]["29.97"] == 1000
        
        # Verify format distribution
        assert "non_drop_frame" in data["format_distribution"]
        assert data["format_distribution"]["non_drop_frame"] == 1500
        
        # Verify service was called
        mock_service.get_timecode_stats.assert_called_once()
    
    @patch('src.services.timecode_search_service.get_timecode_search_service')
    def test_get_timecode_stats_error(self, mock_get_service, client):
        """Test getting timecode statistics with error"""
        # Mock service to raise error
        mock_service = AsyncMock()
        mock_service.get_timecode_stats.side_effect = Exception("Database connection failed")
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.get("/search/timecode/stats")
        
        # Verify response
        assert response.status_code == 500
        data = response.json()
        assert "Failed to get timecode statistics" in data["detail"]
    
    def test_search_endpoints_exist(self, client):
        """Test that all timecode search endpoints exist"""
        # Test main search endpoint
        response = client.post("/search/timecode", json={
            "search_type": "simple",
            "min_duration": 60.0
        })
        assert response.status_code != 404
        
        # Test validation endpoint
        response = client.post("/search/timecode/validate", params={
            "timecode": "01:23:45:12"
        })
        assert response.status_code != 404
        
        # Test conversion endpoint
        response = client.post("/search/timecode/convert", json={
            "source_timecode": "01:00:00:00",
            "source_format": "film",
            "target_format": "pal"
        })
        assert response.status_code != 404
        
        # Test stats endpoint
        response = client.get("/search/timecode/stats")
        assert response.status_code != 404
    
    def test_search_request_validation(self, client):
        """Test request validation for search endpoint"""
        # Test with completely invalid data
        response = client.post("/search/timecode", json={})
        assert response.status_code == 422
        
        # Test with invalid search type
        response = client.post("/search/timecode", json={
            "search_type": "invalid_type"
        })
        assert response.status_code == 422
        
        # Test with invalid timecode format
        response = client.post("/search/timecode", json={
            "search_type": "simple",
            "timecode": {
                "hours": 25,  # Invalid
                "minutes": 0,
                "seconds": 0,
                "frames": 0
            }
        })
        assert response.status_code == 422
    
    def test_validation_request_parameters(self, client):
        """Test validation endpoint parameter validation"""
        # Test without required timecode parameter
        response = client.post("/search/timecode/validate")
        assert response.status_code == 422
        
        # Test with invalid format parameter
        response = client.post("/search/timecode/validate", params={
            "timecode": "01:23:45:12",
            "format": "invalid_format"
        })
        assert response.status_code == 422
    
    def test_conversion_request_validation(self, client):
        """Test conversion endpoint request validation"""
        # Test with missing required fields
        response = client.post("/search/timecode/convert", json={})
        assert response.status_code == 422
        
        # Test with invalid format
        response = client.post("/search/timecode/convert", json={
            "source_timecode": "01:00:00:00",
            "source_format": "invalid_format",
            "target_format": "pal"
        })
        assert response.status_code == 422
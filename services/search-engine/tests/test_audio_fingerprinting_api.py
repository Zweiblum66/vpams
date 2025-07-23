"""
Tests for Audio Fingerprinting API endpoints
"""

import pytest
from httpx import AsyncClient
from datetime import datetime
import base64
import json

from src.models.schemas import (
    AudioFingerprintingAlgorithm, AudioSearchType, AudioMatchType,
    AudioFeatureType, AudioQualityLevel
)


@pytest.fixture
def sample_fingerprint_query():
    """Sample audio fingerprint query for testing"""
    return {
        "reference_asset_id": "test_audio_001",
        "search_type": AudioSearchType.DUPLICATE_DETECTION.value,
        "fingerprint_algorithm": AudioFingerprintingAlgorithm.CHROMAPRINT.value,
        "min_match_score": 0.8,
        "max_results": 10,
        "include_partial_matches": True
    }


@pytest.fixture
def sample_analysis_request():
    """Sample audio analysis request for testing"""
    return {
        "asset_id": "test_audio_001",
        "extract_fingerprints": True,
        "extract_features": True,
        "analyze_segments": True,
        "assess_quality": True,
        "fingerprint_algorithms": [
            AudioFingerprintingAlgorithm.CHROMAPRINT.value,
            AudioFingerprintingAlgorithm.ECHOPRINT.value
        ],
        "feature_types": [
            AudioFeatureType.MFCC.value,
            AudioFeatureType.CHROMAGRAM.value,
            AudioFeatureType.TEMPO.value
        ]
    }


class TestAudioFingerprintingAPI:
    """Test cases for Audio Fingerprinting API endpoints"""

    @pytest.mark.asyncio
    async def test_search_audio_fingerprint_success(
        self,
        client: AsyncClient,
        sample_fingerprint_query: dict
    ):
        """Test successful audio fingerprint search"""
        response = await client.post(
            "/api/v1/search/audio-fingerprint",
            json=sample_fingerprint_query
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "search_id" in data
        assert data["search_type"] == AudioSearchType.DUPLICATE_DETECTION.value
        assert data["algorithm_used"] == AudioFingerprintingAlgorithm.CHROMAPRINT.value
        assert "matches" in data
        assert isinstance(data["matches"], list)
        assert "total_matches" in data
        assert "processing_time_ms" in data
        assert "search_metadata" in data

    @pytest.mark.asyncio
    async def test_search_audio_fingerprint_with_url(
        self,
        client: AsyncClient
    ):
        """Test audio fingerprint search with URL reference"""
        query = {
            "reference_audio_url": "https://example.com/audio/sample.mp3",
            "search_type": AudioSearchType.MUSIC_IDENTIFICATION.value,
            "fingerprint_algorithm": AudioFingerprintingAlgorithm.SHAZAM.value
        }
        
        response = await client.post(
            "/api/v1/search/audio-fingerprint",
            json=query
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["search_type"] == AudioSearchType.MUSIC_IDENTIFICATION.value
        assert data["algorithm_used"] == AudioFingerprintingAlgorithm.SHAZAM.value
        
        # Music identification might include metadata
        if data["total_matches"] > 0:
            assert "music_metadata" in data

    @pytest.mark.asyncio
    async def test_search_audio_fingerprint_with_base64_data(
        self,
        client: AsyncClient
    ):
        """Test audio fingerprint search with base64 audio data"""
        # Create mock base64 audio data
        mock_audio_data = base64.b64encode(b"mock audio data").decode()
        
        query = {
            "audio_data_base64": mock_audio_data,
            "search_type": AudioSearchType.SAMPLE_DETECTION.value,
            "min_match_duration_ms": 1000
        }
        
        response = await client.post(
            "/api/v1/search/audio-fingerprint",
            json=query
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["search_type"] == AudioSearchType.SAMPLE_DETECTION.value

    @pytest.mark.asyncio
    async def test_search_audio_fingerprint_different_types(
        self,
        client: AsyncClient
    ):
        """Test different audio search types"""
        search_types = [
            AudioSearchType.DUPLICATE_DETECTION,
            AudioSearchType.COPYRIGHT_MONITORING,
            AudioSearchType.BROADCAST_MONITORING,
            AudioSearchType.COVER_DETECTION,
            AudioSearchType.PODCAST_TRACKING
        ]
        
        for search_type in search_types:
            query = {
                "reference_asset_id": "test_audio_001",
                "search_type": search_type.value
            }
            
            response = await client.post(
                "/api/v1/search/audio-fingerprint",
                json=query
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["search_type"] == search_type.value

    @pytest.mark.asyncio
    async def test_search_audio_fingerprint_with_filters(
        self,
        client: AsyncClient
    ):
        """Test audio fingerprint search with various filters"""
        query = {
            "reference_asset_id": "test_audio_001",
            "search_type": AudioSearchType.DUPLICATE_DETECTION.value,
            "asset_types": ["audio/mp3", "audio/wav"],
            "date_range": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            },
            "duration_range_ms": {
                "min": 30000,
                "max": 300000
            },
            "min_match_duration_ms": 5000
        }
        
        response = await client.post(
            "/api/v1/search/audio-fingerprint",
            json=query
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "applied_filters" in data
        assert "asset_types" in data["applied_filters"]
        assert "date_range" in data["applied_filters"]

    @pytest.mark.asyncio
    async def test_analyze_audio_comprehensive(
        self,
        client: AsyncClient,
        sample_analysis_request: dict
    ):
        """Test comprehensive audio analysis"""
        response = await client.post(
            "/api/v1/search/audio-fingerprint/analyze",
            json=sample_analysis_request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "analysis_id" in data
        assert data["asset_id"] == "test_audio_001"
        assert data["analysis_success"] is True
        assert "analysis" in data
        
        analysis = data["analysis"]
        assert "fingerprints" in analysis
        assert "features" in analysis
        assert "segments" in analysis
        assert "quality_metrics" in analysis
        assert "processing_time_ms" in analysis

    @pytest.mark.asyncio
    async def test_analyze_audio_fingerprints_only(
        self,
        client: AsyncClient
    ):
        """Test audio analysis with only fingerprint extraction"""
        request = {
            "asset_id": "test_audio_001",
            "extract_fingerprints": True,
            "extract_features": False,
            "analyze_segments": False,
            "assess_quality": False,
            "fingerprint_algorithms": [
                AudioFingerprintingAlgorithm.CHROMAPRINT.value
            ]
        }
        
        response = await client.post(
            "/api/v1/search/audio-fingerprint/analyze",
            json=request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        analysis = data["analysis"]
        assert len(analysis["fingerprints"]) > 0
        assert len(analysis["features"]) == 0
        assert len(analysis["segments"]) == 0
        assert analysis["quality_metrics"] is None

    @pytest.mark.asyncio
    async def test_analyze_audio_quality_assessment(
        self,
        client: AsyncClient
    ):
        """Test audio quality assessment"""
        request = {
            "asset_id": "test_audio_001",
            "extract_fingerprints": False,
            "extract_features": False,
            "analyze_segments": False,
            "assess_quality": True
        }
        
        response = await client.post(
            "/api/v1/search/audio-fingerprint/analyze",
            json=request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        quality = data["analysis"]["quality_metrics"]
        assert quality is not None
        assert "overall_quality_score" in quality
        assert 0 <= quality["overall_quality_score"] <= 100
        assert "quality_level" in quality
        assert quality["quality_level"] in [level.value for level in AudioQualityLevel]

    @pytest.mark.asyncio
    async def test_analyze_audio_feature_extraction(
        self,
        client: AsyncClient
    ):
        """Test specific audio feature extraction"""
        request = {
            "asset_id": "test_audio_001",
            "extract_features": True,
            "feature_types": [
                AudioFeatureType.MFCC.value,
                AudioFeatureType.CHROMAGRAM.value,
                AudioFeatureType.SPECTRAL_CENTROID.value,
                AudioFeatureType.TEMPO.value
            ],
            "extract_fingerprints": False
        }
        
        response = await client.post(
            "/api/v1/search/audio-fingerprint/analyze",
            json=request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        features = data["analysis"]["features"]
        assert len(features) > 0
        
        # Check requested feature types are present
        feature_types = [f["feature_type"] for f in features]
        assert AudioFeatureType.MFCC.value in feature_types
        assert AudioFeatureType.CHROMAGRAM.value in feature_types

    @pytest.mark.asyncio
    async def test_get_audio_fingerprint_stats(
        self,
        client: AsyncClient
    ):
        """Test getting audio fingerprint statistics"""
        response = await client.get("/api/v1/search/audio-fingerprint/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check main statistics
        assert "total_searches" in data
        assert "total_matches" in data
        assert "total_audio_analyzed" in data
        assert "avg_search_time_ms" in data
        assert "avg_analysis_time_ms" in data
        
        # Check performance metrics
        assert "algorithm_performance" in data
        assert isinstance(data["algorithm_performance"], dict)
        
        # Check distributions
        assert "search_type_distribution" in data
        assert "match_type_distribution" in data
        assert "audio_format_distribution" in data
        assert "quality_distribution" in data

    @pytest.mark.asyncio
    async def test_search_audio_fingerprint_validation_error(
        self,
        client: AsyncClient
    ):
        """Test validation error handling"""
        # Invalid query with conflicting parameters
        query = {
            "search_type": "invalid_search_type",
            "min_match_score": 1.5  # Invalid score > 1.0
        }
        
        response = await client.post(
            "/api/v1/search/audio-fingerprint",
            json=query
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_analyze_audio_missing_asset_id(
        self,
        client: AsyncClient
    ):
        """Test analysis with missing asset ID"""
        request = {
            "extract_fingerprints": True
            # Missing asset_id
        }
        
        response = await client.post(
            "/api/v1/search/audio-fingerprint/analyze",
            json=request
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_concurrent_audio_searches(
        self,
        client: AsyncClient
    ):
        """Test concurrent audio fingerprint searches"""
        import asyncio
        
        queries = [
            {
                "reference_asset_id": f"test_audio_{i:03d}",
                "search_type": AudioSearchType.DUPLICATE_DETECTION.value
            }
            for i in range(5)
        ]
        
        # Send concurrent requests
        tasks = [
            client.post("/api/v1/search/audio-fingerprint", json=query)
            for query in queries
        ]
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "search_id" in data

    @pytest.mark.asyncio
    async def test_search_with_music_identification(
        self,
        client: AsyncClient
    ):
        """Test music identification search type"""
        query = {
            "reference_asset_id": "test_music_001",
            "search_type": AudioSearchType.MUSIC_IDENTIFICATION.value,
            "fingerprint_algorithm": AudioFingerprintingAlgorithm.MUSICBRAINZ.value
        }
        
        response = await client.post(
            "/api/v1/search/audio-fingerprint",
            json=query
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Music identification might return music metadata
        if data["total_matches"] > 0 and data.get("music_metadata"):
            metadata = data["music_metadata"]
            # Should have at least some music information
            assert any([
                metadata.get("title"),
                metadata.get("artist"),
                metadata.get("album")
            ])

    @pytest.mark.asyncio
    async def test_analyze_audio_segment_analysis(
        self,
        client: AsyncClient
    ):
        """Test audio segment analysis"""
        request = {
            "asset_id": "test_audio_001",
            "analyze_segments": True,
            "segment_duration_ms": 5000,
            "extract_fingerprints": False,
            "extract_features": False
        }
        
        response = await client.post(
            "/api/v1/search/audio-fingerprint/analyze",
            json=request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        segments = data["analysis"]["segments"]
        assert len(segments) > 0
        
        for segment in segments:
            assert "start_time_ms" in segment
            assert "end_time_ms" in segment
            assert "segment_type" in segment
            assert segment["segment_type"] in ["speech", "music", "silence", "mixed"]

    @pytest.mark.asyncio
    async def test_search_with_match_filtering(
        self,
        client: AsyncClient
    ):
        """Test search with match score filtering"""
        query = {
            "reference_asset_id": "test_audio_001",
            "search_type": AudioSearchType.DUPLICATE_DETECTION.value,
            "min_match_score": 0.9,  # High threshold
            "max_results": 5
        }
        
        response = await client.post(
            "/api/v1/search/audio-fingerprint",
            json=query
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all matches meet the threshold
        for match in data["matches"]:
            assert match["match_score"] >= 0.9
        
        # Should not exceed max results
        assert len(data["matches"]) <= 5
"""
Tests for Audio Fingerprinting Service
"""

import pytest
import asyncio
from datetime import datetime
from typing import List

from src.services.audio_fingerprinting_service import AudioFingerprintingService
from src.models.schemas import (
    AudioFingerprintQuery, AudioFingerprintResponse, AudioFingerprintStats,
    AudioAnalysisRequest, AudioAnalysisResponse, AudioMatch,
    AudioAnalysis, AudioFingerprint, AudioFeatures, AudioSegment,
    MusicMetadata, AudioQualityMetrics, AudioFingerprintingAlgorithm,
    AudioFingerprintType, AudioMatchType, AudioSearchType,
    AudioFeatureType, AudioQualityLevel
)


@pytest.fixture
def audio_fingerprinting_service():
    """Create AudioFingerprintingService instance for testing"""
    return AudioFingerprintingService()


@pytest.fixture
def sample_fingerprint_query():
    """Create a sample audio fingerprint query"""
    return AudioFingerprintQuery(
        reference_asset_id="test_audio_001",
        search_type=AudioSearchType.DUPLICATE_DETECTION,
        fingerprint_algorithm=AudioFingerprintingAlgorithm.CHROMAPRINT,
        min_match_score=0.8,
        max_results=10
    )


@pytest.fixture
def sample_analysis_request():
    """Create a sample audio analysis request"""
    return AudioAnalysisRequest(
        asset_id="test_audio_001",
        extract_fingerprints=True,
        extract_features=True,
        analyze_segments=True,
        assess_quality=True,
        fingerprint_algorithms=[
            AudioFingerprintingAlgorithm.CHROMAPRINT,
            AudioFingerprintingAlgorithm.ECHOPRINT
        ]
    )


class TestAudioFingerprintingService:
    """Test cases for AudioFingerprintingService"""

    @pytest.mark.asyncio
    async def test_search_audio_fingerprint_with_asset_id(
        self,
        audio_fingerprinting_service: AudioFingerprintingService,
        sample_fingerprint_query: AudioFingerprintQuery
    ):
        """Test audio fingerprint search with reference asset ID"""
        response = await audio_fingerprinting_service.search_audio_fingerprint(sample_fingerprint_query)
        
        assert isinstance(response, AudioFingerprintResponse)
        assert response.search_id
        assert response.search_type == AudioSearchType.DUPLICATE_DETECTION
        assert response.algorithm_used == AudioFingerprintingAlgorithm.CHROMAPRINT
        assert isinstance(response.matches, list)
        assert response.total_matches >= 0
        assert response.query_audio_duration_ms > 0
        assert response.search_metadata is not None

    @pytest.mark.asyncio
    async def test_search_audio_fingerprint_with_url(
        self,
        audio_fingerprinting_service: AudioFingerprintingService
    ):
        """Test audio fingerprint search with reference URL"""
        query = AudioFingerprintQuery(
            reference_audio_url="https://example.com/audio/test.mp3",
            search_type=AudioSearchType.MUSIC_IDENTIFICATION,
            fingerprint_algorithm=AudioFingerprintingAlgorithm.SHAZAM
        )
        
        response = await audio_fingerprinting_service.search_audio_fingerprint(query)
        
        assert isinstance(response, AudioFingerprintResponse)
        assert response.algorithm_used == AudioFingerprintingAlgorithm.SHAZAM
        assert response.search_type == AudioSearchType.MUSIC_IDENTIFICATION
        
        # Should have music metadata for music identification
        if response.total_matches > 0:
            assert response.music_metadata is not None

    @pytest.mark.asyncio
    async def test_search_audio_fingerprint_with_audio_data(
        self,
        audio_fingerprinting_service: AudioFingerprintingService
    ):
        """Test audio fingerprint search with base64 audio data"""
        query = AudioFingerprintQuery(
            audio_data_base64="SGVsbG8gV29ybGQh",  # Mock base64 data
            search_type=AudioSearchType.SAMPLE_DETECTION,
            include_partial_matches=True,
            min_match_duration_ms=1000
        )
        
        response = await audio_fingerprinting_service.search_audio_fingerprint(query)
        
        assert isinstance(response, AudioFingerprintResponse)
        assert response.search_type == AudioSearchType.SAMPLE_DETECTION
        assert "include_partial_matches" in response.applied_filters

    @pytest.mark.asyncio
    async def test_search_audio_fingerprint_different_search_types(
        self,
        audio_fingerprinting_service: AudioFingerprintingService
    ):
        """Test different audio search types"""
        search_types = [
            AudioSearchType.DUPLICATE_DETECTION,
            AudioSearchType.MUSIC_IDENTIFICATION,
            AudioSearchType.COPYRIGHT_MONITORING,
            AudioSearchType.BROADCAST_MONITORING,
            AudioSearchType.COVER_DETECTION
        ]
        
        for search_type in search_types:
            query = AudioFingerprintQuery(
                reference_asset_id="test_audio_001",
                search_type=search_type
            )
            
            response = await audio_fingerprinting_service.search_audio_fingerprint(query)
            
            assert response.search_type == search_type
            assert isinstance(response.matches, list)

    @pytest.mark.asyncio
    async def test_analyze_audio_comprehensive(
        self,
        audio_fingerprinting_service: AudioFingerprintingService,
        sample_analysis_request: AudioAnalysisRequest
    ):
        """Test comprehensive audio analysis"""
        response = await audio_fingerprinting_service.analyze_audio(sample_analysis_request)
        
        assert isinstance(response, AudioAnalysisResponse)
        assert response.analysis_id
        assert response.asset_id == "test_audio_001"
        assert response.analysis_success is True
        
        # Check analysis results
        analysis = response.analysis
        assert isinstance(analysis, AudioAnalysis)
        assert analysis.duration_ms > 0
        assert len(analysis.fingerprints) > 0
        assert len(analysis.features) > 0
        assert len(analysis.segments) > 0
        assert analysis.quality_metrics is not None

    @pytest.mark.asyncio
    async def test_analyze_audio_fingerprints_only(
        self,
        audio_fingerprinting_service: AudioFingerprintingService
    ):
        """Test audio analysis with fingerprints only"""
        request = AudioAnalysisRequest(
            asset_id="test_audio_001",
            extract_fingerprints=True,
            extract_features=False,
            analyze_segments=False,
            assess_quality=False
        )
        
        response = await audio_fingerprinting_service.analyze_audio(request)
        
        assert response.analysis_success is True
        assert len(response.analysis.fingerprints) > 0
        assert len(response.analysis.features) == 0
        assert len(response.analysis.segments) == 0
        assert response.analysis.quality_metrics is None

    @pytest.mark.asyncio
    async def test_analyze_audio_multiple_algorithms(
        self,
        audio_fingerprinting_service: AudioFingerprintingService
    ):
        """Test audio analysis with multiple fingerprinting algorithms"""
        algorithms = [
            AudioFingerprintingAlgorithm.CHROMAPRINT,
            AudioFingerprintingAlgorithm.ECHOPRINT,
            AudioFingerprintingAlgorithm.DEJAVU
        ]
        
        request = AudioAnalysisRequest(
            asset_id="test_audio_001",
            extract_fingerprints=True,
            fingerprint_algorithms=algorithms
        )
        
        response = await audio_fingerprinting_service.analyze_audio(request)
        
        # Should have fingerprints for each requested algorithm
        fingerprint_algorithms = {fp.algorithm for fp in response.analysis.fingerprints}
        for algo in algorithms:
            assert algo in fingerprint_algorithms

    @pytest.mark.asyncio
    async def test_get_fingerprint_stats(
        self,
        audio_fingerprinting_service: AudioFingerprintingService
    ):
        """Test getting audio fingerprint statistics"""
        stats = await audio_fingerprinting_service.get_fingerprint_stats()
        
        assert isinstance(stats, AudioFingerprintStats)
        assert stats.total_searches >= 0
        assert stats.total_matches >= 0
        assert stats.total_audio_analyzed >= 0
        assert stats.avg_search_time_ms >= 0
        assert stats.avg_analysis_time_ms >= 0
        assert isinstance(stats.algorithm_performance, dict)
        assert isinstance(stats.search_type_distribution, dict)
        assert isinstance(stats.match_type_distribution, dict)

    @pytest.mark.asyncio
    async def test_concurrent_searches(
        self,
        audio_fingerprinting_service: AudioFingerprintingService
    ):
        """Test concurrent audio fingerprint searches"""
        queries = [
            AudioFingerprintQuery(
                reference_asset_id=f"test_audio_{i:03d}",
                search_type=AudioSearchType.DUPLICATE_DETECTION
            )
            for i in range(5)
        ]
        
        # Run searches concurrently
        tasks = [
            audio_fingerprinting_service.search_audio_fingerprint(query)
            for query in queries
        ]
        responses = await asyncio.gather(*tasks)
        
        assert len(responses) == 5
        for response in responses:
            assert isinstance(response, AudioFingerprintResponse)
            assert response.search_id

    @pytest.mark.asyncio
    async def test_match_confidence_scoring(
        self,
        audio_fingerprinting_service: AudioFingerprintingService
    ):
        """Test match confidence scoring"""
        query = AudioFingerprintQuery(
            reference_asset_id="test_audio_001",
            search_type=AudioSearchType.DUPLICATE_DETECTION,
            min_match_score=0.7
        )
        
        response = await audio_fingerprinting_service.search_audio_fingerprint(query)
        
        # All matches should meet minimum score
        for match in response.matches:
            assert match.match_score >= 0.7
            assert 0.0 <= match.match_score <= 1.0

    @pytest.mark.asyncio
    async def test_audio_quality_assessment(
        self,
        audio_fingerprinting_service: AudioFingerprintingService
    ):
        """Test audio quality assessment"""
        request = AudioAnalysisRequest(
            asset_id="test_audio_001",
            assess_quality=True,
            extract_fingerprints=False,
            extract_features=False
        )
        
        response = await audio_fingerprinting_service.analyze_audio(request)
        
        quality = response.analysis.quality_metrics
        assert quality is not None
        assert isinstance(quality, AudioQualityMetrics)
        assert 0 <= quality.overall_quality_score <= 100
        assert quality.quality_level in AudioQualityLevel.__members__.values()
        assert quality.sample_rate > 0
        assert quality.bitrate_kbps > 0

    @pytest.mark.asyncio
    async def test_feature_extraction(
        self,
        audio_fingerprinting_service: AudioFingerprintingService
    ):
        """Test audio feature extraction"""
        request = AudioAnalysisRequest(
            asset_id="test_audio_001",
            extract_features=True,
            feature_types=[
                AudioFeatureType.CHROMAGRAM,
                AudioFeatureType.MFCC,
                AudioFeatureType.SPECTRAL_CENTROID,
                AudioFeatureType.TEMPO
            ]
        )
        
        response = await audio_fingerprinting_service.analyze_audio(request)
        
        features = response.analysis.features
        assert len(features) > 0
        
        # Check requested feature types are present
        feature_types = {f.feature_type for f in features}
        assert AudioFeatureType.CHROMAGRAM in feature_types
        assert AudioFeatureType.MFCC in feature_types

    @pytest.mark.asyncio
    async def test_segment_analysis(
        self,
        audio_fingerprinting_service: AudioFingerprintingService
    ):
        """Test audio segment analysis"""
        request = AudioAnalysisRequest(
            asset_id="test_audio_001",
            analyze_segments=True,
            segment_duration_ms=5000  # 5 second segments
        )
        
        response = await audio_fingerprinting_service.analyze_audio(request)
        
        segments = response.analysis.segments
        assert len(segments) > 0
        
        for segment in segments:
            assert isinstance(segment, AudioSegment)
            assert segment.start_time_ms >= 0
            assert segment.end_time_ms > segment.start_time_ms
            assert segment.segment_type in ["speech", "music", "silence", "mixed"]

    @pytest.mark.asyncio
    async def test_music_metadata_extraction(
        self,
        audio_fingerprinting_service: AudioFingerprintingService
    ):
        """Test music metadata extraction"""
        query = AudioFingerprintQuery(
            reference_asset_id="test_music_001",
            search_type=AudioSearchType.MUSIC_IDENTIFICATION
        )
        
        response = await audio_fingerprinting_service.search_audio_fingerprint(query)
        
        if response.music_metadata:
            metadata = response.music_metadata
            assert isinstance(metadata, MusicMetadata)
            # At least one of these should be present
            assert any([
                metadata.title,
                metadata.artist,
                metadata.album,
                metadata.genre
            ])

    @pytest.mark.asyncio
    async def test_error_handling_invalid_input(
        self,
        audio_fingerprinting_service: AudioFingerprintingService
    ):
        """Test error handling for invalid input"""
        # Query with no reference data
        query = AudioFingerprintQuery(
            search_type=AudioSearchType.DUPLICATE_DETECTION
        )
        
        # Should still return a response (mock implementation)
        response = await audio_fingerprinting_service.search_audio_fingerprint(query)
        assert isinstance(response, AudioFingerprintResponse)
        assert response.total_matches == 0

    @pytest.mark.asyncio
    async def test_cache_performance(
        self,
        audio_fingerprinting_service: AudioFingerprintingService
    ):
        """Test fingerprint cache performance"""
        query = AudioFingerprintQuery(
            reference_asset_id="test_audio_001",
            search_type=AudioSearchType.DUPLICATE_DETECTION
        )
        
        # First search
        response1 = await audio_fingerprinting_service.search_audio_fingerprint(query)
        time1 = response1.search_metadata["search_time"]
        
        # Second search (should be cached)
        response2 = await audio_fingerprinting_service.search_audio_fingerprint(query)
        time2 = response2.search_metadata["search_time"]
        
        # Cached search might be faster (in real implementation)
        assert response2.search_id != response1.search_id

    @pytest.mark.asyncio
    async def test_filter_application(
        self,
        audio_fingerprinting_service: AudioFingerprintingService
    ):
        """Test filter application in search"""
        query = AudioFingerprintQuery(
            reference_asset_id="test_audio_001",
            search_type=AudioSearchType.DUPLICATE_DETECTION,
            asset_types=["audio/mp3", "audio/wav"],
            date_range={
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            },
            duration_range_ms={"min": 30000, "max": 300000}
        )
        
        response = await audio_fingerprinting_service.search_audio_fingerprint(query)
        
        assert "asset_types" in response.applied_filters
        assert "date_range" in response.applied_filters
        assert "duration_range" in response.applied_filters

    @pytest.mark.asyncio
    async def test_performance_metrics(
        self,
        audio_fingerprinting_service: AudioFingerprintingService
    ):
        """Test performance metrics tracking"""
        # Perform several operations
        for i in range(3):
            query = AudioFingerprintQuery(
                reference_asset_id=f"test_audio_{i:03d}",
                search_type=AudioSearchType.DUPLICATE_DETECTION
            )
            await audio_fingerprinting_service.search_audio_fingerprint(query)
        
        # Check stats reflect operations
        stats = await audio_fingerprinting_service.get_fingerprint_stats()
        assert stats.total_searches >= 3
        assert stats.avg_search_time_ms > 0
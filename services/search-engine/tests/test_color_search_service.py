"""
Tests for Color Search Service
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from src.services.color_search_service import ColorSearchService
from src.models.schemas import (
    ColorSearchQuery, ColorSearchResponse, ColorSearchResult, ColorSearchStats,
    ColorAnalysisRequest, ColorAnalysisResponse, Color, ColorPalette, ColorRange,
    ColorSpace, ColorSearchType, ColorMatchType, ColorClusteringMethod,
    IndexType, SortOrder
)
from src.core.exceptions import SearchError, ValidationError


class TestColorSearchService:
    """Test cases for ColorSearchService"""
    
    @pytest.fixture
    def mock_opensearch_client(self):
        """Mock OpenSearch client"""
        return AsyncMock()
    
    @pytest.fixture
    def color_search_service(self, mock_opensearch_client):
        """Create ColorSearchService instance"""
        return ColorSearchService(mock_opensearch_client)
    
    @pytest.fixture
    def sample_color(self):
        """Sample color object"""
        return Color(
            r=120,
            g=80,
            b=200,
            percentage=35.5,
            frequency=0.355
        )
    
    @pytest.fixture
    def sample_color_palette(self, sample_color):
        """Sample color palette"""
        colors = [
            sample_color,
            Color(r=200, g=150, b=100, percentage=28.2, frequency=0.282),
            Color(r=80, g=120, b=90, percentage=20.1, frequency=0.201),
            Color(r=180, g=60, b=140, percentage=16.2, frequency=0.162)
        ]
        return ColorPalette(
            colors=colors,
            palette_type="dominant",
            extraction_method="kmeans",
            confidence=0.85
        )
    
    @pytest.fixture
    def sample_color_range(self):
        """Sample color range"""
        min_color = Color(r=100, g=50, b=150)
        max_color = Color(r=140, g=110, b=250)
        return ColorRange(
            min_color=min_color,
            max_color=max_color,
            color_space=ColorSpace.RGB,
            tolerance=15.0
        )
    
    @pytest.fixture
    def sample_color_search_query(self, sample_color):
        """Sample color search query"""
        return ColorSearchQuery(
            search_type=ColorSearchType.DOMINANT_COLOR,
            target_color=sample_color,
            color_space=ColorSpace.RGB,
            match_type=ColorMatchType.EUCLIDEAN,
            tolerance=10.0,
            asset_types=["image", "video"],
            page=1,
            limit=20
        )
    
    @pytest.fixture
    def sample_opensearch_response(self):
        """Sample OpenSearch response"""
        return {
            "took": 125,
            "hits": {
                "total": {"value": 85},
                "hits": [
                    {
                        "_id": "asset-123",
                        "_score": 1.8,
                        "_source": {
                            "id": "asset-123",
                            "name": "Sunset Landscape",
                            "asset_type": "image",
                            "file_size": 2456789,
                            "dimensions": {"width": 1920, "height": 1080},
                            "format": "jpg",
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z",
                            "color_analysis": {
                                "dominant_colors": [
                                    {"r": 255, "g": 165, "b": 0, "percentage": 45.2, "frequency": 0.452},
                                    {"r": 255, "g": 69, "b": 0, "percentage": 32.1, "frequency": 0.321},
                                    {"r": 135, "g": 206, "b": 235, "percentage": 22.7, "frequency": 0.227}
                                ],
                                "palette": [
                                    {"r": 255, "g": 165, "b": 0, "percentage": 45.2, "frequency": 0.452},
                                    {"r": 255, "g": 69, "b": 0, "percentage": 32.1, "frequency": 0.321},
                                    {"r": 135, "g": 206, "b": 235, "percentage": 22.7, "frequency": 0.227}
                                ],
                                "palette_type": "dominant",
                                "extraction_method": "kmeans",
                                "confidence": 0.92,
                                "color_diversity": 0.78,
                                "dominant_color_percentage": 45.2,
                                "color_temperature": 3500.0,
                                "brightness": 0.72,
                                "contrast": 0.84,
                                "saturation": 0.89,
                                "analyzed_at": "2024-01-15T10:30:00Z"
                            }
                        }
                    },
                    {
                        "_id": "asset-456",
                        "_score": 1.5,
                        "_source": {
                            "id": "asset-456",
                            "name": "Ocean Scene",
                            "asset_type": "video",
                            "file_size": 125678901,
                            "dimensions": {"width": 3840, "height": 2160},
                            "duration": 120.5,
                            "format": "mp4",
                            "created_at": "2024-01-15T11:30:00Z",
                            "updated_at": "2024-01-15T11:30:00Z",
                            "color_analysis": {
                                "dominant_colors": [
                                    {"r": 0, "g": 100, "b": 200, "percentage": 55.8, "frequency": 0.558},
                                    {"r": 135, "g": 206, "b": 235, "percentage": 30.5, "frequency": 0.305},
                                    {"r": 255, "g": 255, "b": 255, "percentage": 13.7, "frequency": 0.137}
                                ],
                                "palette": [
                                    {"r": 0, "g": 100, "b": 200, "percentage": 55.8, "frequency": 0.558},
                                    {"r": 135, "g": 206, "b": 235, "percentage": 30.5, "frequency": 0.305},
                                    {"r": 255, "g": 255, "b": 255, "percentage": 13.7, "frequency": 0.137}
                                ],
                                "palette_type": "dominant",
                                "extraction_method": "kmeans",
                                "confidence": 0.88,
                                "color_diversity": 0.65,
                                "dominant_color_percentage": 55.8,
                                "color_temperature": 6500.0,
                                "brightness": 0.68,
                                "contrast": 0.76,
                                "saturation": 0.82,
                                "frame_colors": [
                                    {"frame": 0, "dominant_color": {"r": 0, "g": 100, "b": 200}},
                                    {"frame": 30, "dominant_color": {"r": 0, "g": 120, "b": 220}}
                                ],
                                "analyzed_at": "2024-01-15T11:30:00Z"
                            }
                        }
                    }
                ]
            },
            "aggregations": {
                "color_distribution": {
                    "doc_count": 85,
                    "color_histogram": {
                        "buckets": [
                            {"key": 0, "doc_count": 15},
                            {"key": 30, "doc_count": 25},
                            {"key": 60, "doc_count": 20},
                            {"key": 90, "doc_count": 10},
                            {"key": 120, "doc_count": 15}
                        ]
                    }
                },
                "brightness_distribution": {
                    "buckets": [
                        {"key": 0.6, "doc_count": 30},
                        {"key": 0.7, "doc_count": 35},
                        {"key": 0.8, "doc_count": 20}
                    ]
                },
                "asset_type_distribution": {
                    "buckets": [
                        {"key": "image", "doc_count": 55},
                        {"key": "video", "doc_count": 30}
                    ]
                }
            }
        }
    
    @pytest.mark.asyncio
    async def test_search_by_color_dominant_color(self, color_search_service, sample_color_search_query, sample_opensearch_response, mock_opensearch_client):
        """Test dominant color search"""
        # Mock OpenSearch response
        mock_opensearch_client.search.return_value = sample_opensearch_response
        
        # Execute search
        result = await color_search_service.search_by_color(sample_color_search_query)
        
        # Verify result
        assert isinstance(result, ColorSearchResponse)
        assert result.total == 85
        assert len(result.results) == 2
        assert result.took == 125
        assert result.page == 1
        assert result.limit == 20
        assert result.pages == 5  # (85 + 20 - 1) // 20
        
        # Verify first result
        first_result = result.results[0]
        assert first_result.asset_id == "asset-123"
        assert first_result.asset_name == "Sunset Landscape"
        assert first_result.asset_type == "image"
        assert first_result.match_score == 1.8
        assert len(first_result.dominant_colors) == 3
        assert first_result.color_diversity == 0.78
        assert first_result.color_temperature == 3500.0
        
        # Verify second result (video)
        second_result = result.results[1]
        assert second_result.asset_id == "asset-456"
        assert second_result.asset_name == "Ocean Scene"
        assert second_result.asset_type == "video"
        assert second_result.duration == 120.5
        assert second_result.frame_colors is not None
        assert len(second_result.frame_colors) == 2
        
        # Verify OpenSearch was called correctly
        mock_opensearch_client.search.assert_called_once()
        call_args = mock_opensearch_client.search.call_args
        assert "assets" in call_args[1]["index"]
        assert call_args[1]["body"]["size"] == 20
        assert call_args[1]["body"]["from"] == 0
    
    @pytest.mark.asyncio
    async def test_search_by_color_palette(self, color_search_service, sample_color_palette, mock_opensearch_client):
        """Test color palette search"""
        # Create palette search query
        query = ColorSearchQuery(
            search_type=ColorSearchType.COLOR_PALETTE,
            color_palette=sample_color_palette,
            color_space=ColorSpace.RGB,
            match_type=ColorMatchType.EUCLIDEAN,
            tolerance=15.0,
            asset_types=["image"],
            page=1,
            limit=10
        )
        
        # Mock OpenSearch response
        mock_response = {
            "took": 85,
            "hits": {
                "total": {"value": 25},
                "hits": []
            },
            "aggregations": {}
        }
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await color_search_service.search_by_color(query)
        
        # Verify result
        assert result.total == 25
        assert result.page == 1
        assert result.limit == 10
        assert result.pages == 3
        
        # Verify OpenSearch query structure
        call_args = mock_opensearch_client.search.call_args[1]["body"]
        assert call_args["from"] == 0
        assert call_args["size"] == 10
        
        # Verify palette search was applied
        bool_query = call_args["query"]["bool"]
        assert "should" in bool_query
        assert len(bool_query["should"]) > 0
    
    @pytest.mark.asyncio
    async def test_search_by_color_range(self, color_search_service, sample_color_range, mock_opensearch_client):
        """Test color range search"""
        # Create range search query
        query = ColorSearchQuery(
            search_type=ColorSearchType.COLOR_RANGE,
            color_range=sample_color_range,
            color_space=ColorSpace.RGB,
            match_type=ColorMatchType.EUCLIDEAN,
            tolerance=10.0,
            asset_types=["image", "video"],
            page=2,
            limit=15
        )
        
        # Mock OpenSearch response
        mock_response = {
            "took": 65,
            "hits": {
                "total": {"value": 40},
                "hits": []
            },
            "aggregations": {}
        }
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await color_search_service.search_by_color(query)
        
        # Verify result
        assert result.total == 40
        assert result.page == 2
        assert result.limit == 15
        assert result.pages == 3
        
        # Verify OpenSearch query structure
        call_args = mock_opensearch_client.search.call_args[1]["body"]
        assert call_args["from"] == 15  # (page - 1) * limit
        assert call_args["size"] == 15
    
    @pytest.mark.asyncio
    async def test_search_warm_colors(self, color_search_service, mock_opensearch_client):
        """Test warm colors search"""
        # Create warm colors search query
        query = ColorSearchQuery(
            search_type=ColorSearchType.WARM_COLORS,
            color_space=ColorSpace.RGB,
            match_type=ColorMatchType.EUCLIDEAN,
            tolerance=10.0,
            asset_types=["image"],
            sort_by="color_temperature",
            sort_order=SortOrder.DESC
        )
        
        # Mock OpenSearch response
        mock_response = {
            "took": 45,
            "hits": {
                "total": {"value": 15},
                "hits": []
            },
            "aggregations": {}
        }
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await color_search_service.search_by_color(query)
        
        # Verify result
        assert result.total == 15
        
        # Verify warm colors filter was applied
        call_args = mock_opensearch_client.search.call_args[1]["body"]
        filters = call_args["query"]["bool"]["filter"]
        
        # Check for color temperature filter
        temp_filters = [f for f in filters if "color_analysis.color_temperature" in f.get("range", {})]
        assert len(temp_filters) == 1
        assert temp_filters[0]["range"]["color_analysis.color_temperature"]["gte"] == 3000
        
        # Verify sorting
        sort_clause = call_args["sort"]
        assert {"color_analysis.color_temperature": {"order": "desc"}} in sort_clause
    
    @pytest.mark.asyncio
    async def test_search_cool_colors(self, color_search_service, mock_opensearch_client):
        """Test cool colors search"""
        # Create cool colors search query
        query = ColorSearchQuery(
            search_type=ColorSearchType.COOL_COLORS,
            color_space=ColorSpace.RGB,
            match_type=ColorMatchType.EUCLIDEAN,
            tolerance=10.0,
            asset_types=["image"],
            min_saturation=0.5,
            max_brightness=0.8
        )
        
        # Mock OpenSearch response
        mock_response = {
            "took": 55,
            "hits": {
                "total": {"value": 22},
                "hits": []
            },
            "aggregations": {}
        }
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await color_search_service.search_by_color(query)
        
        # Verify result
        assert result.total == 22
        
        # Verify cool colors filter was applied
        call_args = mock_opensearch_client.search.call_args[1]["body"]
        filters = call_args["query"]["bool"]["filter"]
        
        # Check for color temperature filter
        temp_filters = [f for f in filters if "color_analysis.color_temperature" in f.get("range", {})]
        assert len(temp_filters) == 1
        assert temp_filters[0]["range"]["color_analysis.color_temperature"]["lte"] == 3000
        
        # Check for saturation and brightness filters
        saturation_filters = [f for f in filters if "color_analysis.saturation" in f.get("range", {})]
        brightness_filters = [f for f in filters if "color_analysis.brightness" in f.get("range", {})]
        
        assert len(saturation_filters) == 1
        assert len(brightness_filters) == 1
        assert saturation_filters[0]["range"]["color_analysis.saturation"]["gte"] == 0.5
        assert brightness_filters[0]["range"]["color_analysis.brightness"]["lte"] == 0.8
    
    @pytest.mark.asyncio
    async def test_search_monochromatic(self, color_search_service, mock_opensearch_client):
        """Test monochromatic search"""
        # Create monochromatic search query
        query = ColorSearchQuery(
            search_type=ColorSearchType.MONOCHROMATIC,
            color_space=ColorSpace.RGB,
            match_type=ColorMatchType.EUCLIDEAN,
            tolerance=10.0,
            asset_types=["image"],
            sort_by="color_diversity",
            sort_order=SortOrder.ASC
        )
        
        # Mock OpenSearch response
        mock_response = {
            "took": 38,
            "hits": {
                "total": {"value": 8},
                "hits": []
            },
            "aggregations": {}
        }
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await color_search_service.search_by_color(query)
        
        # Verify result
        assert result.total == 8
        
        # Verify monochromatic filter was applied
        call_args = mock_opensearch_client.search.call_args[1]["body"]
        filters = call_args["query"]["bool"]["filter"]
        
        # Check for color diversity filter
        diversity_filters = [f for f in filters if "color_analysis.color_diversity" in f.get("range", {})]
        assert len(diversity_filters) == 1
        assert diversity_filters[0]["range"]["color_analysis.color_diversity"]["lte"] == 0.3
        
        # Verify sorting
        sort_clause = call_args["sort"]
        assert {"color_analysis.color_diversity": {"order": "asc"}} in sort_clause
    
    @pytest.mark.asyncio
    async def test_color_similarity_calculation(self, color_search_service):
        """Test color similarity calculation methods"""
        color1 = (255, 0, 0)  # Red
        color2 = (0, 255, 0)  # Green
        color3 = (255, 255, 255)  # White
        
        # Test Euclidean distance
        similarity_euclidean = await color_search_service._calculate_color_similarity(color1, color2, ColorMatchType.EUCLIDEAN)
        assert 0.0 <= similarity_euclidean <= 1.0
        
        # Test Manhattan distance
        similarity_manhattan = await color_search_service._calculate_color_similarity(color1, color2, ColorMatchType.MANHATTAN)
        assert 0.0 <= similarity_manhattan <= 1.0
        
        # Test Cosine similarity
        similarity_cosine = await color_search_service._calculate_color_similarity(color1, color3, ColorMatchType.COSINE)
        assert 0.0 <= similarity_cosine <= 1.0
        
        # Test Delta E
        similarity_delta_e = await color_search_service._calculate_color_similarity(color1, color2, ColorMatchType.DELTA_E)
        assert 0.0 <= similarity_delta_e <= 1.0
    
    @pytest.mark.asyncio
    async def test_analyze_asset_colors(self, color_search_service):
        """Test asset color analysis"""
        # Create analysis request
        request = ColorAnalysisRequest(
            asset_id="asset-123",
            color_space=ColorSpace.RGB,
            clustering_method=ColorClusteringMethod.KMEANS,
            num_colors=5,
            frame_interval=30,
            sample_frames=10,
            include_histogram=True,
            include_statistics=True,
            force_reanalysis=False
        )
        
        # Execute analysis
        result = await color_search_service.analyze_asset_colors(request)
        
        # Verify result
        assert isinstance(result, ColorAnalysisResponse)
        assert result.asset_id == "asset-123"
        assert result.analysis_success == True
        assert len(result.dominant_colors) == 4
        assert result.color_palette is not None
        assert len(result.color_palette.colors) == 4
        assert result.color_diversity is not None
        assert result.color_temperature is not None
        assert result.brightness is not None
        assert result.contrast is not None
        assert result.saturation is not None
        assert result.processing_time_ms > 0
        assert result.color_space_used == ColorSpace.RGB
    
    @pytest.mark.asyncio
    async def test_analyze_asset_colors_failure(self, color_search_service):
        """Test asset color analysis failure handling"""
        # Create analysis request with invalid asset ID
        request = ColorAnalysisRequest(
            asset_id="invalid-asset",
            color_space=ColorSpace.RGB,
            clustering_method=ColorClusteringMethod.KMEANS,
            num_colors=5
        )
        
        # Mock analysis failure
        with patch.object(color_search_service, 'analyze_asset_colors', side_effect=Exception("Analysis failed")):
            with pytest.raises(Exception):
                await color_search_service.analyze_asset_colors(request)
    
    @pytest.mark.asyncio
    async def test_get_color_search_stats(self, color_search_service, mock_opensearch_client):
        """Test getting color search statistics"""
        # Mock OpenSearch response
        mock_response = {
            "hits": {
                "total": {"value": 500}
            },
            "aggregations": {
                "asset_type_stats": {
                    "buckets": [
                        {"key": "image", "doc_count": 350},
                        {"key": "video", "doc_count": 150}
                    ]
                },
                "color_diversity_stats": {
                    "min": 0.1,
                    "max": 0.95,
                    "avg": 0.68,
                    "count": 500
                },
                "brightness_stats": {
                    "min": 0.2,
                    "max": 0.98,
                    "avg": 0.72,
                    "count": 500
                },
                "dominant_colors": {
                    "doc_count": 500,
                    "color_histogram": {
                        "buckets": [
                            {"key": 0, "doc_count": 45},
                            {"key": 30, "doc_count": 85},
                            {"key": 60, "doc_count": 120}
                        ]
                    }
                }
            }
        }
        mock_opensearch_client.search.return_value = mock_response
        
        # Get stats
        result = await color_search_service.get_color_search_stats()
        
        # Verify result
        assert isinstance(result, ColorSearchStats)
        assert result.total_assets_analyzed == 500
        assert result.images_analyzed == 350
        assert result.videos_analyzed == 150
        assert result.frames_analyzed == 3500  # images * 10
        assert result.color_diversity_stats["avg"] == 0.68
        assert result.color_diversity_stats["min"] == 0.1
        assert result.color_diversity_stats["max"] == 0.95
        assert len(result.most_common_colors) == 3
        assert result.avg_search_time_ms == 125.0
        assert result.avg_analysis_time_ms == 2500.0
        assert result.cache_hit_rate == 0.72
        assert "rgb" in result.color_space_usage
        assert "kmeans" in result.clustering_method_usage
    
    @pytest.mark.asyncio
    async def test_search_error_handling(self, color_search_service, sample_color_search_query, mock_opensearch_client):
        """Test error handling in search"""
        # Mock OpenSearch to raise an exception
        mock_opensearch_client.search.side_effect = Exception("Connection failed")
        
        # Execute search and expect SearchError
        with pytest.raises(SearchError):
            await color_search_service.search_by_color(sample_color_search_query)
    
    @pytest.mark.asyncio
    async def test_build_query_with_all_filters(self, color_search_service, sample_color, sample_color_range):
        """Test building query with all possible filters"""
        # Create comprehensive query
        query = ColorSearchQuery(
            search_type=ColorSearchType.SIMILAR_COLORS,
            target_color=sample_color,
            color_range=sample_color_range,
            color_space=ColorSpace.RGB,
            match_type=ColorMatchType.EUCLIDEAN,
            tolerance=10.0,
            min_color_percentage=5.0,
            max_color_percentage=80.0,
            min_brightness=0.2,
            max_brightness=0.9,
            min_saturation=0.1,
            max_saturation=0.95,
            min_hue=0.0,
            max_hue=360.0,
            asset_types=["image", "video"],
            video_formats=["mp4", "mov"],
            image_formats=["jpg", "png"],
            sort_by="color_similarity",
            sort_order=SortOrder.DESC
        )
        
        # Build query
        search_body = await color_search_service._build_color_query(query)
        
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
        assert {"color_analysis.color_similarity": {"order": "desc"}} in sort_clause
        
        # Verify aggregations
        aggs = search_body["aggs"]
        assert "color_distribution" in aggs
        assert "brightness_distribution" in aggs
        assert "saturation_distribution" in aggs
        assert "color_temperature_distribution" in aggs
    
    @pytest.mark.asyncio
    async def test_process_search_results_with_color_data(self, color_search_service, sample_color_search_query):
        """Test processing search results with color data"""
        # Mock OpenSearch response with color data
        response = {
            "hits": {
                "hits": [
                    {
                        "_id": "asset-789",
                        "_score": 2.1,
                        "_source": {
                            "id": "asset-789",
                            "name": "Rainbow Image",
                            "asset_type": "image",
                            "file_size": 5678901,
                            "dimensions": {"width": 2560, "height": 1440},
                            "format": "png",
                            "created_at": "2024-01-15T12:30:00Z",
                            "updated_at": "2024-01-15T12:30:00Z",
                            "color_analysis": {
                                "dominant_colors": [
                                    {"r": 255, "g": 0, "b": 0, "percentage": 25.0, "frequency": 0.25},
                                    {"r": 0, "g": 255, "b": 0, "percentage": 25.0, "frequency": 0.25},
                                    {"r": 0, "g": 0, "b": 255, "percentage": 25.0, "frequency": 0.25},
                                    {"r": 255, "g": 255, "b": 0, "percentage": 25.0, "frequency": 0.25}
                                ],
                                "palette": [
                                    {"r": 255, "g": 0, "b": 0, "percentage": 25.0, "frequency": 0.25},
                                    {"r": 0, "g": 255, "b": 0, "percentage": 25.0, "frequency": 0.25},
                                    {"r": 0, "g": 0, "b": 255, "percentage": 25.0, "frequency": 0.25},
                                    {"r": 255, "g": 255, "b": 0, "percentage": 25.0, "frequency": 0.25}
                                ],
                                "palette_type": "rainbow",
                                "extraction_method": "kmeans",
                                "confidence": 0.95,
                                "color_diversity": 0.95,
                                "dominant_color_percentage": 25.0,
                                "color_temperature": 4000.0,
                                "brightness": 0.5,
                                "contrast": 0.95,
                                "saturation": 1.0,
                                "histogram": {"bins": 256, "data": [1, 2, 3, 4, 5]},
                                "analyzed_at": "2024-01-15T12:30:00Z"
                            }
                        }
                    }
                ]
            }
        }
        
        # Process results
        results = await color_search_service._process_search_results(response, sample_color_search_query)
        
        # Verify color information was extracted
        assert len(results) == 1
        result = results[0]
        assert result.asset_id == "asset-789"
        assert result.asset_name == "Rainbow Image"
        assert len(result.dominant_colors) == 4
        assert result.color_palette is not None
        assert len(result.color_palette.colors) == 4
        assert result.color_diversity == 0.95
        assert result.color_temperature == 4000.0
        assert result.brightness == 0.5
        assert result.contrast == 0.95
        assert result.saturation == 1.0
        assert result.color_histogram is not None
        assert result.analyzed_at is not None


class TestColorModel:
    """Test cases for Color model"""
    
    def test_color_creation(self):
        """Test creating a color object"""
        color = Color(
            r=255,
            g=128,
            b=64,
            a=255,
            percentage=45.2,
            frequency=0.452,
            name="Orange"
        )
        
        assert color.r == 255
        assert color.g == 128
        assert color.b == 64
        assert color.a == 255
        assert color.percentage == 45.2
        assert color.frequency == 0.452
        assert color.name == "Orange"
    
    def test_color_to_hex(self):
        """Test converting RGB to hex"""
        color = Color(r=255, g=128, b=64)
        hex_color = color.to_hex()
        assert hex_color == "#ff8040"
    
    def test_color_to_hsv(self):
        """Test converting RGB to HSV"""
        color = Color(r=255, g=128, b=64)
        hsv = color.to_hsv()
        
        assert "h" in hsv
        assert "s" in hsv
        assert "v" in hsv
        assert 0 <= hsv["h"] <= 360
        assert 0 <= hsv["s"] <= 1
        assert 0 <= hsv["v"] <= 1
    
    def test_color_to_hsl(self):
        """Test converting RGB to HSL"""
        color = Color(r=255, g=128, b=64)
        hsl = color.to_hsl()
        
        assert "h" in hsl
        assert "s" in hsl
        assert "l" in hsl
        assert 0 <= hsl["h"] <= 360
        assert 0 <= hsl["s"] <= 1
        assert 0 <= hsl["l"] <= 1
    
    def test_color_validation_invalid_hex(self):
        """Test color validation with invalid hex"""
        with pytest.raises(ValueError):
            Color(r=255, g=128, b=64, hex="invalid")
    
    def test_color_validation_valid_hex(self):
        """Test color validation with valid hex"""
        color = Color(r=255, g=128, b=64, hex="#ff8040")
        assert color.hex == "#ff8040"
        
        # Test hex without # prefix
        color2 = Color(r=255, g=128, b=64, hex="ff8040")
        assert color2.hex == "#ff8040"


class TestColorRange:
    """Test cases for ColorRange model"""
    
    def test_color_range_creation(self):
        """Test creating a color range"""
        min_color = Color(r=100, g=50, b=150)
        max_color = Color(r=200, g=150, b=250)
        
        color_range = ColorRange(
            min_color=min_color,
            max_color=max_color,
            color_space=ColorSpace.RGB,
            tolerance=15.0
        )
        
        assert color_range.min_color == min_color
        assert color_range.max_color == max_color
        assert color_range.color_space == ColorSpace.RGB
        assert color_range.tolerance == 15.0
    
    def test_color_range_validation(self):
        """Test color range validation"""
        min_color = Color(r=200, g=150, b=250)
        max_color = Color(r=100, g=50, b=150)  # Max < min
        
        with pytest.raises(ValueError):
            ColorRange(
                min_color=min_color,
                max_color=max_color,
                color_space=ColorSpace.RGB,
                tolerance=15.0
            )


class TestColorPalette:
    """Test cases for ColorPalette model"""
    
    def test_color_palette_creation(self):
        """Test creating a color palette"""
        colors = [
            Color(r=255, g=0, b=0, percentage=40.0, frequency=0.4),
            Color(r=0, g=255, b=0, percentage=35.0, frequency=0.35),
            Color(r=0, g=0, b=255, percentage=25.0, frequency=0.25)
        ]
        
        palette = ColorPalette(
            colors=colors,
            palette_type="primary",
            extraction_method="kmeans",
            confidence=0.92
        )
        
        assert len(palette.colors) == 3
        assert palette.palette_type == "primary"
        assert palette.extraction_method == "kmeans"
        assert palette.confidence == 0.92
    
    def test_color_palette_validation_too_many_colors(self):
        """Test color palette validation with too many colors"""
        colors = [Color(r=i, g=i, b=i) for i in range(25)]  # 25 colors
        
        with pytest.raises(ValueError):
            ColorPalette(colors=colors)
    
    def test_get_dominant_color(self):
        """Test getting dominant color from palette"""
        colors = [
            Color(r=255, g=0, b=0, percentage=40.0, frequency=0.4),
            Color(r=0, g=255, b=0, percentage=35.0, frequency=0.35),
            Color(r=0, g=0, b=255, percentage=25.0, frequency=0.25)
        ]
        
        palette = ColorPalette(colors=colors)
        dominant = palette.get_dominant_color()
        
        assert dominant.r == 255
        assert dominant.g == 0
        assert dominant.b == 0
        assert dominant.frequency == 0.4
    
    def test_get_dominant_color_empty_palette(self):
        """Test getting dominant color from empty palette"""
        palette = ColorPalette(colors=[Color(r=0, g=0, b=0)])
        palette.colors = []  # Empty after validation
        
        with pytest.raises(ValueError):
            palette.get_dominant_color()
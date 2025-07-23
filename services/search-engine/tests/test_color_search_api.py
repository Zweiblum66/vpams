"""
Tests for Color Search API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json
from datetime import datetime

from src.main import app
from src.models.schemas import (
    ColorSearchResponse, ColorSearchResult, ColorSearchStats, ColorAnalysisResponse,
    ColorSpace, ColorSearchType, ColorMatchType, ColorClusteringMethod, Color, ColorPalette
)


class TestColorSearchAPI:
    """Test cases for Color Search API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_color_search_data(self):
        """Sample color search request data"""
        return {
            "search_type": "dominant_color",
            "target_color": {
                "r": 120,
                "g": 80,
                "b": 200
            },
            "color_space": "rgb",
            "match_type": "euclidean",
            "tolerance": 15.0,
            "min_color_percentage": 10.0,
            "asset_types": ["image", "video"],
            "page": 1,
            "limit": 20
        }
    
    @pytest.fixture
    def sample_color_palette_search_data(self):
        """Sample color palette search request data"""
        return {
            "search_type": "color_palette",
            "color_palette": {
                "colors": [
                    {"r": 255, "g": 0, "b": 0, "percentage": 40.0, "frequency": 0.4},
                    {"r": 0, "g": 255, "b": 0, "percentage": 35.0, "frequency": 0.35},
                    {"r": 0, "g": 0, "b": 255, "percentage": 25.0, "frequency": 0.25}
                ],
                "palette_type": "primary",
                "extraction_method": "kmeans",
                "confidence": 0.92
            },
            "color_space": "rgb",
            "match_type": "euclidean",
            "tolerance": 20.0,
            "asset_types": ["image"],
            "page": 1,
            "limit": 15
        }
    
    @pytest.fixture
    def sample_color_range_search_data(self):
        """Sample color range search request data"""
        return {
            "search_type": "color_range",
            "color_range": {
                "min_color": {"r": 100, "g": 50, "b": 150},
                "max_color": {"r": 200, "g": 150, "b": 250},
                "color_space": "rgb",
                "tolerance": 15.0
            },
            "color_space": "rgb",
            "match_type": "euclidean",
            "tolerance": 10.0,
            "asset_types": ["image", "video"],
            "page": 1,
            "limit": 10
        }
    
    @pytest.fixture
    def sample_warm_colors_search_data(self):
        """Sample warm colors search request data"""
        return {
            "search_type": "warm_colors",
            "color_space": "rgb",
            "match_type": "euclidean",
            "tolerance": 10.0,
            "min_color_percentage": 20.0,
            "asset_types": ["image"],
            "sort_by": "color_temperature",
            "sort_order": "desc",
            "page": 1,
            "limit": 12
        }
    
    @pytest.fixture
    def sample_search_response(self):
        """Sample color search response"""
        return ColorSearchResponse(
            results=[
                ColorSearchResult(
                    asset_id="asset-123",
                    asset_name="Sunset Landscape",
                    asset_type="image",
                    dominant_colors=[
                        Color(r=255, g=165, b=0, percentage=45.2, frequency=0.452),
                        Color(r=255, g=69, b=0, percentage=32.1, frequency=0.321),
                        Color(r=135, g=206, b=235, percentage=22.7, frequency=0.227)
                    ],
                    color_palette=ColorPalette(
                        colors=[
                            Color(r=255, g=165, b=0, percentage=45.2, frequency=0.452),
                            Color(r=255, g=69, b=0, percentage=32.1, frequency=0.321),
                            Color(r=135, g=206, b=235, percentage=22.7, frequency=0.227)
                        ],
                        palette_type="dominant",
                        extraction_method="kmeans",
                        confidence=0.92
                    ),
                    matched_colors=[
                        Color(r=255, g=165, b=0, percentage=45.2, frequency=0.452)
                    ],
                    match_score=1.8,
                    match_type="color_similarity",
                    color_similarity=0.92,
                    color_diversity=0.78,
                    dominant_color_percentage=45.2,
                    color_temperature=3500.0,
                    brightness=0.72,
                    contrast=0.84,
                    saturation=0.89,
                    file_size=2456789,
                    dimensions={"width": 1920, "height": 1080},
                    format="jpg",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    analyzed_at=datetime.utcnow()
                )
            ],
            total=1,
            took=125,
            page=1,
            limit=20,
            pages=1,
            aggregations={},
            search_metadata={"search_type": "dominant_color"}
        )
    
    @pytest.fixture
    def sample_analysis_request_data(self):
        """Sample color analysis request data"""
        return {
            "asset_id": "asset-123",
            "color_space": "rgb",
            "clustering_method": "kmeans",
            "num_colors": 5,
            "frame_interval": 30,
            "sample_frames": 10,
            "include_histogram": True,
            "include_statistics": True,
            "force_reanalysis": False
        }
    
    @patch('src.services.color_search_service.get_color_search_service')
    def test_search_by_color_dominant_color(self, mock_get_service, client, sample_color_search_data, sample_search_response):
        """Test dominant color search"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_color.return_value = sample_search_response
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/color", json=sample_color_search_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["asset_id"] == "asset-123"
        assert data["results"][0]["asset_name"] == "Sunset Landscape"
        assert data["results"][0]["asset_type"] == "image"
        assert data["results"][0]["match_score"] == 1.8
        assert data["results"][0]["match_type"] == "color_similarity"
        assert data["results"][0]["color_similarity"] == 0.92
        assert data["results"][0]["color_diversity"] == 0.78
        assert data["results"][0]["color_temperature"] == 3500.0
        assert len(data["results"][0]["dominant_colors"]) == 3
        assert len(data["results"][0]["matched_colors"]) == 1
        assert data["took"] == 125
        
        # Verify service was called
        mock_service.search_by_color.assert_called_once()
    
    @patch('src.services.color_search_service.get_color_search_service')
    def test_search_by_color_palette(self, mock_get_service, client, sample_color_palette_search_data):
        """Test color palette search"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_color.return_value = ColorSearchResponse(
            results=[],
            total=0,
            took=85,
            page=1,
            limit=15,
            pages=0,
            aggregations={},
            search_metadata={"search_type": "color_palette"}
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/color", json=sample_color_palette_search_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["results"]) == 0
        assert data["search_metadata"]["search_type"] == "color_palette"
        assert data["took"] == 85
        assert data["limit"] == 15
        
        # Verify service was called with correct parameters
        mock_service.search_by_color.assert_called_once()
        call_args = mock_service.search_by_color.call_args[0][0]
        assert call_args.search_type.value == "color_palette"
        assert call_args.color_palette is not None
        assert len(call_args.color_palette.colors) == 3
        assert call_args.tolerance == 20.0
    
    @patch('src.services.color_search_service.get_color_search_service')
    def test_search_by_color_range(self, mock_get_service, client, sample_color_range_search_data):
        """Test color range search"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_color.return_value = ColorSearchResponse(
            results=[],
            total=25,
            took=65,
            page=1,
            limit=10,
            pages=3,
            aggregations={},
            search_metadata={"search_type": "color_range"}
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/color", json=sample_color_range_search_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 25
        assert data["pages"] == 3
        assert data["search_metadata"]["search_type"] == "color_range"
        
        # Verify service was called with correct parameters
        mock_service.search_by_color.assert_called_once()
        call_args = mock_service.search_by_color.call_args[0][0]
        assert call_args.search_type.value == "color_range"
        assert call_args.color_range is not None
        assert call_args.color_range.min_color.r == 100
        assert call_args.color_range.max_color.r == 200
    
    @patch('src.services.color_search_service.get_color_search_service')
    def test_search_warm_colors(self, mock_get_service, client, sample_warm_colors_search_data):
        """Test warm colors search"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_color.return_value = ColorSearchResponse(
            results=[
                ColorSearchResult(
                    asset_id="asset-456",
                    asset_name="Autumn Leaves",
                    asset_type="image",
                    dominant_colors=[
                        Color(r=255, g=140, b=0, percentage=60.5, frequency=0.605),
                        Color(r=255, g=69, b=0, percentage=25.2, frequency=0.252),
                        Color(r=139, g=69, b=19, percentage=14.3, frequency=0.143)
                    ],
                    color_palette=ColorPalette(
                        colors=[
                            Color(r=255, g=140, b=0, percentage=60.5, frequency=0.605),
                            Color(r=255, g=69, b=0, percentage=25.2, frequency=0.252),
                            Color(r=139, g=69, b=19, percentage=14.3, frequency=0.143)
                        ],
                        palette_type="warm",
                        extraction_method="kmeans",
                        confidence=0.88
                    ),
                    matched_colors=[],
                    match_score=2.2,
                    match_type="color_temperature",
                    color_similarity=0.9,
                    color_diversity=0.65,
                    dominant_color_percentage=60.5,
                    color_temperature=2800.0,
                    brightness=0.68,
                    contrast=0.78,
                    saturation=0.95,
                    file_size=3456789,
                    dimensions={"width": 2048, "height": 1536},
                    format="jpg",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    analyzed_at=datetime.utcnow()
                )
            ],
            total=18,
            took=55,
            page=1,
            limit=12,
            pages=2,
            aggregations={},
            search_metadata={"search_type": "warm_colors"}
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/color", json=sample_warm_colors_search_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 18
        assert len(data["results"]) == 1
        assert data["results"][0]["asset_name"] == "Autumn Leaves"
        assert data["results"][0]["color_temperature"] == 2800.0
        assert data["results"][0]["match_type"] == "color_temperature"
        assert data["results"][0]["saturation"] == 0.95
        assert data["search_metadata"]["search_type"] == "warm_colors"
        
        # Verify service was called with correct parameters
        mock_service.search_by_color.assert_called_once()
        call_args = mock_service.search_by_color.call_args[0][0]
        assert call_args.search_type.value == "warm_colors"
        assert call_args.min_color_percentage == 20.0
        assert call_args.sort_by == "color_temperature"
        assert call_args.sort_order.value == "desc"
    
    @patch('src.services.color_search_service.get_color_search_service')
    def test_search_cool_colors(self, mock_get_service, client):
        """Test cool colors search"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_color.return_value = ColorSearchResponse(
            results=[
                ColorSearchResult(
                    asset_id="asset-789",
                    asset_name="Ocean Waves",
                    asset_type="image",
                    dominant_colors=[
                        Color(r=0, g=100, b=200, percentage=55.8, frequency=0.558),
                        Color(r=70, g=130, b=180, percentage=30.5, frequency=0.305),
                        Color(r=176, g=196, b=222, percentage=13.7, frequency=0.137)
                    ],
                    color_palette=ColorPalette(
                        colors=[
                            Color(r=0, g=100, b=200, percentage=55.8, frequency=0.558),
                            Color(r=70, g=130, b=180, percentage=30.5, frequency=0.305),
                            Color(r=176, g=196, b=222, percentage=13.7, frequency=0.137)
                        ],
                        palette_type="cool",
                        extraction_method="kmeans",
                        confidence=0.91
                    ),
                    matched_colors=[],
                    match_score=2.0,
                    match_type="color_temperature",
                    color_similarity=0.88,
                    color_diversity=0.72,
                    dominant_color_percentage=55.8,
                    color_temperature=6500.0,
                    brightness=0.58,
                    contrast=0.82,
                    saturation=0.75,
                    file_size=4567890,
                    dimensions={"width": 1920, "height": 1080},
                    format="png",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    analyzed_at=datetime.utcnow()
                )
            ],
            total=22,
            took=48,
            page=1,
            limit=20,
            pages=2,
            aggregations={},
            search_metadata={"search_type": "cool_colors"}
        )
        mock_get_service.return_value = mock_service
        
        # Create cool colors search request
        cool_colors_data = {
            "search_type": "cool_colors",
            "color_space": "rgb",
            "match_type": "euclidean",
            "tolerance": 12.0,
            "min_saturation": 0.5,
            "max_brightness": 0.8,
            "asset_types": ["image"],
            "page": 1,
            "limit": 20
        }
        
        # Make request
        response = client.post("/search/color", json=cool_colors_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 22
        assert len(data["results"]) == 1
        assert data["results"][0]["asset_name"] == "Ocean Waves"
        assert data["results"][0]["color_temperature"] == 6500.0
        assert data["results"][0]["match_type"] == "color_temperature"
        assert data["results"][0]["saturation"] == 0.75
        assert data["search_metadata"]["search_type"] == "cool_colors"
        
        # Verify service was called with correct parameters
        mock_service.search_by_color.assert_called_once()
        call_args = mock_service.search_by_color.call_args[0][0]
        assert call_args.search_type.value == "cool_colors"
        assert call_args.min_saturation == 0.5
        assert call_args.max_brightness == 0.8
    
    @patch('src.services.color_search_service.get_color_search_service')
    def test_search_monochromatic(self, mock_get_service, client):
        """Test monochromatic search"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_color.return_value = ColorSearchResponse(
            results=[
                ColorSearchResult(
                    asset_id="asset-101",
                    asset_name="Black and White Portrait",
                    asset_type="image",
                    dominant_colors=[
                        Color(r=64, g=64, b=64, percentage=75.0, frequency=0.75),
                        Color(r=192, g=192, b=192, percentage=25.0, frequency=0.25)
                    ],
                    color_palette=ColorPalette(
                        colors=[
                            Color(r=64, g=64, b=64, percentage=75.0, frequency=0.75),
                            Color(r=192, g=192, b=192, percentage=25.0, frequency=0.25)
                        ],
                        palette_type="monochromatic",
                        extraction_method="kmeans",
                        confidence=0.96
                    ),
                    matched_colors=[],
                    match_score=2.5,
                    match_type="general",
                    color_similarity=0.95,
                    color_diversity=0.25,
                    dominant_color_percentage=75.0,
                    color_temperature=5000.0,
                    brightness=0.45,
                    contrast=0.85,
                    saturation=0.05,
                    file_size=1234567,
                    dimensions={"width": 1024, "height": 768},
                    format="jpg",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    analyzed_at=datetime.utcnow()
                )
            ],
            total=8,
            took=38,
            page=1,
            limit=20,
            pages=1,
            aggregations={},
            search_metadata={"search_type": "monochromatic"}
        )
        mock_get_service.return_value = mock_service
        
        # Create monochromatic search request
        mono_data = {
            "search_type": "monochromatic",
            "color_space": "rgb",
            "match_type": "euclidean",
            "tolerance": 10.0,
            "asset_types": ["image"],
            "sort_by": "color_diversity",
            "sort_order": "asc",
            "page": 1,
            "limit": 20
        }
        
        # Make request
        response = client.post("/search/color", json=mono_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 8
        assert len(data["results"]) == 1
        assert data["results"][0]["asset_name"] == "Black and White Portrait"
        assert data["results"][0]["color_diversity"] == 0.25
        assert data["results"][0]["saturation"] == 0.05
        assert data["search_metadata"]["search_type"] == "monochromatic"
        
        # Verify service was called with correct parameters
        mock_service.search_by_color.assert_called_once()
        call_args = mock_service.search_by_color.call_args[0][0]
        assert call_args.search_type.value == "monochromatic"
        assert call_args.sort_by == "color_diversity"
        assert call_args.sort_order.value == "asc"
    
    @patch('src.services.color_search_service.get_color_search_service')
    def test_search_invalid_data(self, mock_get_service, client):
        """Test search with invalid data"""
        # Mock service
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        
        # Make request with invalid data
        invalid_data = {
            "search_type": "invalid_type",
            "target_color": {
                "r": 300,  # Invalid RGB value
                "g": 0,
                "b": 0
            }
        }
        
        response = client.post("/search/color", json=invalid_data)
        
        # Verify response
        assert response.status_code == 422  # Validation error
    
    @patch('src.services.color_search_service.get_color_search_service')
    def test_analyze_asset_colors_success(self, mock_get_service, client, sample_analysis_request_data):
        """Test successful asset color analysis"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.analyze_asset_colors.return_value = ColorAnalysisResponse(
            asset_id="asset-123",
            analysis_success=True,
            dominant_colors=[
                Color(r=120, g=80, b=200, percentage=35.5, frequency=0.355),
                Color(r=200, g=150, b=100, percentage=28.2, frequency=0.282),
                Color(r=80, g=120, b=90, percentage=20.1, frequency=0.201),
                Color(r=180, g=60, b=140, percentage=16.2, frequency=0.162)
            ],
            color_palette=ColorPalette(
                colors=[
                    Color(r=120, g=80, b=200, percentage=35.5, frequency=0.355),
                    Color(r=200, g=150, b=100, percentage=28.2, frequency=0.282),
                    Color(r=80, g=120, b=90, percentage=20.1, frequency=0.201),
                    Color(r=180, g=60, b=140, percentage=16.2, frequency=0.162)
                ],
                palette_type="dominant",
                extraction_method="kmeans",
                confidence=0.85
            ),
            color_histogram={"bins": 256, "data": []},
            color_diversity=0.75,
            color_temperature=3200.0,
            brightness=0.65,
            contrast=0.82,
            saturation=0.71,
            processing_time_ms=2500,
            analysis_method="K-means clustering (kmeans)",
            color_space_used=ColorSpace.RGB,
            errors=[],
            warnings=[]
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/color/analyze", json=sample_analysis_request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["asset_id"] == "asset-123"
        assert data["analysis_success"] == True
        assert len(data["dominant_colors"]) == 4
        assert data["color_palette"] is not None
        assert len(data["color_palette"]["colors"]) == 4
        assert data["color_diversity"] == 0.75
        assert data["color_temperature"] == 3200.0
        assert data["brightness"] == 0.65
        assert data["contrast"] == 0.82
        assert data["saturation"] == 0.71
        assert data["processing_time_ms"] == 2500
        assert data["analysis_method"] == "K-means clustering (kmeans)"
        assert data["color_space_used"] == "rgb"
        assert len(data["errors"]) == 0
        assert len(data["warnings"]) == 0
        
        # Verify service was called
        mock_service.analyze_asset_colors.assert_called_once()
    
    @patch('src.services.color_search_service.get_color_search_service')
    def test_analyze_asset_colors_failure(self, mock_get_service, client):
        """Test asset color analysis failure"""
        # Mock service to raise an error
        mock_service = AsyncMock()
        mock_service.analyze_asset_colors.side_effect = Exception("Analysis failed")
        mock_get_service.return_value = mock_service
        
        # Create analysis request
        analysis_data = {
            "asset_id": "invalid-asset",
            "color_space": "rgb",
            "clustering_method": "kmeans",
            "num_colors": 5
        }
        
        # Make request
        response = client.post("/search/color/analyze", json=analysis_data)
        
        # Verify response
        assert response.status_code == 500
        data = response.json()
        assert "Color analysis failed" in data["detail"]
    
    @patch('src.services.color_search_service.get_color_search_service')
    def test_get_color_search_stats(self, mock_get_service, client):
        """Test getting color search statistics"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.get_color_search_stats.return_value = ColorSearchStats(
            total_searches=1500,
            total_assets_analyzed=3500,
            most_common_colors=[
                {"color": "#FF8C00", "count": 1250},
                {"color": "#0064C8", "count": 980},
                {"color": "#50C878", "count": 875}
            ],
            color_diversity_stats={
                "min": 0.1,
                "max": 0.95,
                "avg": 0.68
            },
            dominant_color_distribution={
                "warm": 1800,
                "cool": 1200,
                "neutral": 500
            },
            avg_search_time_ms=125.0,
            avg_analysis_time_ms=2500.0,
            cache_hit_rate=0.72,
            images_analyzed=2800,
            videos_analyzed=700,
            frames_analyzed=28000,
            color_space_usage={
                "rgb": 2800,
                "hsv": 450,
                "lab": 250
            },
            clustering_method_usage={
                "kmeans": 2200,
                "dbscan": 800,
                "hierarchical": 500
            }
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.get("/search/color/stats")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_searches"] == 1500
        assert data["total_assets_analyzed"] == 3500
        assert len(data["most_common_colors"]) == 3
        assert data["most_common_colors"][0]["color"] == "#FF8C00"
        assert data["most_common_colors"][0]["count"] == 1250
        assert data["color_diversity_stats"]["avg"] == 0.68
        assert data["color_diversity_stats"]["min"] == 0.1
        assert data["color_diversity_stats"]["max"] == 0.95
        assert data["dominant_color_distribution"]["warm"] == 1800
        assert data["dominant_color_distribution"]["cool"] == 1200
        assert data["dominant_color_distribution"]["neutral"] == 500
        assert data["avg_search_time_ms"] == 125.0
        assert data["avg_analysis_time_ms"] == 2500.0
        assert data["cache_hit_rate"] == 0.72
        assert data["images_analyzed"] == 2800
        assert data["videos_analyzed"] == 700
        assert data["frames_analyzed"] == 28000
        assert data["color_space_usage"]["rgb"] == 2800
        assert data["clustering_method_usage"]["kmeans"] == 2200
        
        # Verify service was called
        mock_service.get_color_search_stats.assert_called_once()
    
    @patch('src.services.color_search_service.get_color_search_service')
    def test_get_color_search_stats_error(self, mock_get_service, client):
        """Test getting color search statistics with error"""
        # Mock service to raise error
        mock_service = AsyncMock()
        mock_service.get_color_search_stats.side_effect = Exception("Database connection failed")
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.get("/search/color/stats")
        
        # Verify response
        assert response.status_code == 500
        data = response.json()
        assert "Failed to get color search statistics" in data["detail"]
    
    def test_color_search_endpoints_exist(self, client):
        """Test that all color search endpoints exist"""
        # Test main search endpoint
        response = client.post("/search/color", json={
            "search_type": "dominant_color",
            "target_color": {"r": 120, "g": 80, "b": 200}
        })
        assert response.status_code != 404
        
        # Test analysis endpoint
        response = client.post("/search/color/analyze", json={
            "asset_id": "asset-123",
            "color_space": "rgb",
            "clustering_method": "kmeans",
            "num_colors": 5
        })
        assert response.status_code != 404
        
        # Test stats endpoint
        response = client.get("/search/color/stats")
        assert response.status_code != 404
    
    def test_color_search_request_validation(self, client):
        """Test request validation for color search endpoint"""
        # Test with completely invalid data
        response = client.post("/search/color", json={})
        assert response.status_code == 422
        
        # Test with invalid search type
        response = client.post("/search/color", json={
            "search_type": "invalid_type"
        })
        assert response.status_code == 422
        
        # Test with invalid color values
        response = client.post("/search/color", json={
            "search_type": "dominant_color",
            "target_color": {
                "r": 300,  # Invalid RGB value
                "g": 0,
                "b": 0
            }
        })
        assert response.status_code == 422
        
        # Test with invalid color space
        response = client.post("/search/color", json={
            "search_type": "dominant_color",
            "target_color": {"r": 120, "g": 80, "b": 200},
            "color_space": "invalid_space"
        })
        assert response.status_code == 422
        
        # Test with invalid match type
        response = client.post("/search/color", json={
            "search_type": "dominant_color",
            "target_color": {"r": 120, "g": 80, "b": 200},
            "match_type": "invalid_match"
        })
        assert response.status_code == 422
    
    def test_color_analysis_request_validation(self, client):
        """Test request validation for color analysis endpoint"""
        # Test without required asset_id
        response = client.post("/search/color/analyze", json={})
        assert response.status_code == 422
        
        # Test with invalid color space
        response = client.post("/search/color/analyze", json={
            "asset_id": "asset-123",
            "color_space": "invalid_space"
        })
        assert response.status_code == 422
        
        # Test with invalid clustering method
        response = client.post("/search/color/analyze", json={
            "asset_id": "asset-123",
            "clustering_method": "invalid_method"
        })
        assert response.status_code == 422
        
        # Test with invalid num_colors
        response = client.post("/search/color/analyze", json={
            "asset_id": "asset-123",
            "num_colors": 0  # Should be >= 1
        })
        assert response.status_code == 422
        
        response = client.post("/search/color/analyze", json={
            "asset_id": "asset-123",
            "num_colors": 25  # Should be <= 20
        })
        assert response.status_code == 422
    
    def test_color_range_validation(self, client):
        """Test color range validation"""
        # Test with invalid range (max < min)
        response = client.post("/search/color", json={
            "search_type": "color_range",
            "color_range": {
                "min_color": {"r": 200, "g": 150, "b": 250},
                "max_color": {"r": 100, "g": 50, "b": 150},  # Max < min
                "color_space": "rgb",
                "tolerance": 15.0
            }
        })
        assert response.status_code == 422
    
    def test_color_percentage_validation(self, client):
        """Test color percentage validation"""
        # Test with invalid percentage range
        response = client.post("/search/color", json={
            "search_type": "dominant_color",
            "target_color": {"r": 120, "g": 80, "b": 200},
            "min_color_percentage": 80.0,
            "max_color_percentage": 60.0  # Max < min
        })
        assert response.status_code == 422
    
    def test_brightness_saturation_validation(self, client):
        """Test brightness and saturation validation"""
        # Test with invalid brightness range
        response = client.post("/search/color", json={
            "search_type": "dominant_color",
            "target_color": {"r": 120, "g": 80, "b": 200},
            "min_brightness": 0.8,
            "max_brightness": 0.5  # Max < min
        })
        assert response.status_code == 422
        
        # Test with invalid saturation range
        response = client.post("/search/color", json={
            "search_type": "dominant_color",
            "target_color": {"r": 120, "g": 80, "b": 200},
            "min_saturation": 0.9,
            "max_saturation": 0.7  # Max < min
        })
        assert response.status_code == 422
    
    def test_hue_validation(self, client):
        """Test hue validation"""
        # Test with invalid hue range
        response = client.post("/search/color", json={
            "search_type": "dominant_color",
            "target_color": {"r": 120, "g": 80, "b": 200},
            "min_hue": 300.0,
            "max_hue": 120.0  # Max < min
        })
        assert response.status_code == 422
        
        # Test with hue values outside valid range
        response = client.post("/search/color", json={
            "search_type": "dominant_color",
            "target_color": {"r": 120, "g": 80, "b": 200},
            "min_hue": -10.0  # Invalid negative hue
        })
        assert response.status_code == 422
        
        response = client.post("/search/color", json={
            "search_type": "dominant_color",
            "target_color": {"r": 120, "g": 80, "b": 200},
            "max_hue": 370.0  # Invalid hue > 360
        })
        assert response.status_code == 422
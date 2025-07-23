"""
Tests for Image Similarity Search API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json
from datetime import datetime

from src.main import app
from src.models.schemas import (
    ImageSimilarityResponse, ImageSimilarityStats, ImageAnalysisResponse,
    ImageSimilarityType, ImageFeatureModel, SimilarityMetric, ImageHashType,
    ImageProcessingType, SimilarityMatch, ImageAnalysis, ImageFeatureVector,
    ImageHash, ImageColorProfile, ImageQuality
)


class TestImageSimilarityAPI:
    """Test cases for Image Similarity Search API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_similarity_search_data(self):
        """Sample image similarity search request data"""
        return {
            "reference_asset_id": "asset_123",
            "similarity_type": "visual_similarity",
            "feature_model": "resnet50",
            "similarity_metric": "cosine_similarity",
            "similarity_threshold": 0.8,
            "asset_types": ["image"],
            "include_thumbnails": True,
            "page": 1,
            "limit": 20
        }
    
    @pytest.fixture
    def sample_feature_search_data(self):
        """Sample feature-based similarity search data"""
        return {
            "reference_features": [0.1] * 2048,  # ResNet50 dimensions
            "similarity_type": "content_similarity",
            "feature_model": "resnet50",
            "similarity_metric": "cosine_similarity",
            "similarity_threshold": 0.75,
            "include_features": True,
            "include_analysis": False,
            "page": 1,
            "limit": 15
        }
    
    @pytest.fixture
    def sample_hash_search_data(self):
        """Sample hash-based similarity search data"""
        return {
            "reference_hash": "a1b2c3d4e5f67890",
            "similarity_type": "perceptual_hash",
            "similarity_metric": "hamming_distance",
            "similarity_threshold": 0.9,
            "include_duplicates": False,
            "page": 1,
            "limit": 10
        }
    
    @pytest.fixture
    def sample_url_search_data(self):
        """Sample URL-based similarity search data"""
        return {
            "reference_image_url": "https://example.com/reference.jpg",
            "similarity_type": "style_similarity",
            "feature_model": "vgg19",
            "similarity_metric": "cosine_similarity",
            "similarity_threshold": 0.7,
            "file_formats": ["jpg", "png"],
            "min_quality_score": 0.6,
            "page": 1,
            "limit": 25
        }
    
    @pytest.fixture
    def sample_duplicate_search_data(self):
        """Sample duplicate detection search data"""
        return {
            "reference_asset_id": "asset_456",
            "similarity_type": "duplicate_detection",
            "feature_model": "mobilenet",
            "similarity_metric": "euclidean_distance",
            "similarity_threshold": 0.95,
            "include_duplicates": True,
            "exclude_low_quality": True,
            "page": 1,
            "limit": 30
        }
    
    @pytest.fixture
    def sample_semantic_search_data(self):
        """Sample semantic similarity search data"""
        return {
            "reference_asset_id": "asset_789",
            "similarity_type": "semantic_similarity",
            "feature_model": "clip",
            "similarity_metric": "cosine_similarity",
            "similarity_threshold": 0.6,
            "asset_types": ["image", "video"],
            "include_analysis": True,
            "region_based": False,
            "multi_scale": False,
            "page": 1,
            "limit": 20
        }
    
    @pytest.fixture
    def sample_analysis_request_data(self):
        """Sample image analysis request data"""
        return {
            "asset_id": "asset_123",
            "feature_models": ["resnet50", "efficientnet"],
            "extract_hashes": True,
            "hash_types": ["perceptual_hash", "average_hash"],
            "analyze_color": True,
            "analyze_texture": True,
            "analyze_shape": False,
            "assess_quality": True,
            "detect_objects": True,
            "parallel_processing": True,
            "gpu_acceleration": False
        }
    
    @pytest.fixture
    def sample_comprehensive_analysis_data(self):
        """Sample comprehensive analysis request data"""
        return {
            "asset_id": "asset_comprehensive",
            "feature_models": ["resnet50", "vgg16", "clip", "vision_transformer"],
            "extract_hashes": True,
            "hash_types": ["perceptual_hash", "average_hash", "difference_hash", "wavelet_hash"],
            "analyze_color": True,
            "analyze_texture": True,
            "analyze_shape": True,
            "assess_quality": True,
            "detect_objects": True,
            "preprocessing": ["resize", "normalize"],
            "resize_for_analysis": True,
            "target_size": {"width": 512, "height": 512},
            "parallel_processing": True,
            "gpu_acceleration": True,
            "force_reanalysis": True
        }
    
    @pytest.fixture
    def mock_get_service(self):
        """Mock image similarity service"""
        service_mock = AsyncMock()
        
        with patch('src.api.routes.get_image_similarity_service', return_value=service_mock):
            yield service_mock
    
    def test_search_similar_images_by_asset_id(self, mock_get_service, client, sample_similarity_search_data):
        """Test image similarity search by asset ID"""
        # Mock service response
        mock_response = ImageSimilarityResponse(
            query_id="query_123",
            reference_asset_id="asset_123",
            similarity_type=ImageSimilarityType.VISUAL_SIMILARITY,
            matches=[
                SimilarityMatch(
                    asset_id="asset_456",
                    similarity_score=0.85,
                    match_type="visual_similarity",
                    asset_name="Similar Image 1",
                    asset_type="image",
                    thumbnail_url="/thumbs/asset_456.jpg"
                )
            ],
            total=1,
            page=1,
            limit=20,
            pages=1,
            took=150,
            search_metadata={"similarity_type": "visual_similarity"}
        )
        mock_get_service.search_similar_images.return_value = mock_response
        
        response = client.post("/search/image-similarity", json=sample_similarity_search_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["query_id"] == "query_123"
        assert data["reference_asset_id"] == "asset_123"
        assert data["similarity_type"] == "visual_similarity"
        assert data["total"] == 1
        assert len(data["matches"]) == 1
        assert data["matches"][0]["asset_id"] == "asset_456"
        assert data["matches"][0]["similarity_score"] == 0.85
        assert data["took"] >= 0
    
    def test_search_similar_images_by_features(self, mock_get_service, client, sample_feature_search_data):
        """Test image similarity search by feature vectors"""
        mock_response = ImageSimilarityResponse(
            query_id="query_456",
            reference_asset_id=None,
            similarity_type=ImageSimilarityType.CONTENT_SIMILARITY,
            matches=[
                SimilarityMatch(
                    asset_id="asset_789",
                    similarity_score=0.78,
                    match_type="content_similarity",
                    asset_name="Content Match",
                    asset_type="image",
                    feature_similarities={"global_features": 0.78, "color_features": 0.82}
                )
            ],
            total=1,
            page=1,
            limit=15,
            pages=1,
            took=120,
            search_metadata={"similarity_type": "content_similarity"}
        )
        mock_get_service.search_similar_images.return_value = mock_response
        
        response = client.post("/search/image-similarity", json=sample_feature_search_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["similarity_type"] == "content_similarity"
        assert data["matches"][0]["feature_similarities"] is not None
        assert "global_features" in data["matches"][0]["feature_similarities"]
    
    def test_search_similar_images_by_hash(self, mock_get_service, client, sample_hash_search_data):
        """Test image similarity search by perceptual hash"""
        mock_response = ImageSimilarityResponse(
            query_id="query_hash",
            reference_asset_id=None,
            similarity_type=ImageSimilarityType.PERCEPTUAL_HASH,
            matches=[
                SimilarityMatch(
                    asset_id="asset_hash_match",
                    similarity_score=0.92,
                    match_type="perceptual_hash",
                    distance=0.08,
                    asset_name="Hash Match",
                    asset_type="image"
                )
            ],
            total=1,
            page=1,
            limit=10,
            pages=1,
            took=50,
            search_metadata={"similarity_type": "perceptual_hash"}
        )
        mock_get_service.search_similar_images.return_value = mock_response
        
        response = client.post("/search/image-similarity", json=sample_hash_search_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["similarity_type"] == "perceptual_hash"
        assert data["matches"][0]["distance"] == 0.08
        assert data["took"] == 50
    
    def test_search_similar_images_by_url(self, mock_get_service, client, sample_url_search_data):
        """Test image similarity search by image URL"""
        mock_response = ImageSimilarityResponse(
            query_id="query_url",
            reference_asset_id=None,
            similarity_type=ImageSimilarityType.STYLE_SIMILARITY,
            matches=[
                SimilarityMatch(
                    asset_id="asset_style_match",
                    similarity_score=0.74,
                    match_type="style_similarity",
                    asset_name="Style Match",
                    asset_type="image",
                    quality_score=0.8
                )
            ],
            total=1,
            page=1,
            limit=25,
            pages=1,
            took=200,
            search_metadata={"similarity_type": "style_similarity"}
        )
        mock_get_service.search_similar_images.return_value = mock_response
        
        response = client.post("/search/image-similarity", json=sample_url_search_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["similarity_type"] == "style_similarity"
        assert data["matches"][0]["quality_score"] == 0.8
    
    def test_search_duplicate_detection(self, mock_get_service, client, sample_duplicate_search_data):
        """Test duplicate detection search"""
        mock_response = ImageSimilarityResponse(
            query_id="query_duplicate",
            reference_asset_id="asset_456",
            similarity_type=ImageSimilarityType.DUPLICATE_DETECTION,
            matches=[
                SimilarityMatch(
                    asset_id="asset_duplicate",
                    similarity_score=0.98,
                    match_type="duplicate_detection",
                    asset_name="Near Duplicate",
                    asset_type="image",
                    match_confidence=0.95
                )
            ],
            total=1,
            page=1,
            limit=30,
            pages=1,
            took=75,
            max_similarity=0.98,
            avg_similarity=0.98,
            min_similarity=0.98,
            search_metadata={"similarity_type": "duplicate_detection"}
        )
        mock_get_service.search_similar_images.return_value = mock_response
        
        response = client.post("/search/image-similarity", json=sample_duplicate_search_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["similarity_type"] == "duplicate_detection"
        assert data["max_similarity"] == 0.98
        assert data["matches"][0]["match_confidence"] == 0.95
    
    def test_search_semantic_similarity(self, mock_get_service, client, sample_semantic_search_data):
        """Test semantic similarity search"""
        mock_response = ImageSimilarityResponse(
            query_id="query_semantic",
            reference_asset_id="asset_789",
            similarity_type=ImageSimilarityType.SEMANTIC_SIMILARITY,
            matches=[
                SimilarityMatch(
                    asset_id="asset_semantic_match",
                    similarity_score=0.65,
                    match_type="semantic_similarity",
                    asset_name="Semantic Match",
                    asset_type="image"
                )
            ],
            total=1,
            page=1,
            limit=20,
            pages=1,
            took=180,
            search_metadata={"similarity_type": "semantic_similarity"}
        )
        mock_get_service.search_similar_images.return_value = mock_response
        
        response = client.post("/search/image-similarity", json=sample_semantic_search_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["similarity_type"] == "semantic_similarity"
        assert data["matches"][0]["match_type"] == "semantic_similarity"
    
    def test_search_request_validation_missing_reference(self, client):
        """Test request validation with missing reference input"""
        invalid_data = {
            "similarity_type": "visual_similarity",
            "feature_model": "resnet50",
            "similarity_metric": "cosine_similarity"
        }
        
        response = client.post("/search/image-similarity", json=invalid_data)
        
        assert response.status_code == 422
        assert "validation error" in response.text.lower()
    
    def test_search_request_validation_invalid_threshold(self, client):
        """Test request validation with invalid similarity threshold"""
        invalid_data = {
            "reference_asset_id": "asset_123",
            "similarity_type": "visual_similarity",
            "feature_model": "resnet50",
            "similarity_metric": "cosine_similarity",
            "similarity_threshold": 1.5  # Invalid: > 1.0
        }
        
        response = client.post("/search/image-similarity", json=invalid_data)
        
        assert response.status_code == 422
    
    def test_search_request_validation_invalid_pagination(self, client):
        """Test request validation with invalid pagination"""
        invalid_data = {
            "reference_asset_id": "asset_123",
            "similarity_type": "visual_similarity",
            "feature_model": "resnet50",
            "similarity_metric": "cosine_similarity",
            "page": 0,  # Invalid: < 1
            "limit": 150  # Invalid: > 100
        }
        
        response = client.post("/search/image-similarity", json=invalid_data)
        
        assert response.status_code == 422
    
    def test_search_service_error(self, mock_get_service, client, sample_similarity_search_data):
        """Test service error handling"""
        mock_get_service.search_similar_images.side_effect = Exception("Service error")
        
        response = client.post("/search/image-similarity", json=sample_similarity_search_data)
        
        assert response.status_code == 500
        assert "similarity search failed" in response.text.lower()
    
    def test_analyze_image_basic(self, mock_get_service, client, sample_analysis_request_data):
        """Test basic image analysis"""
        mock_response = ImageAnalysisResponse(
            asset_id="asset_123",
            analysis=ImageAnalysis(
                asset_id="asset_123",
                image_path="/storage/asset_123.jpg",
                dimensions={"width": 1920, "height": 1080},
                file_size=2456789,
                format="jpg",
                feature_vectors=[
                    ImageFeatureVector(
                        model=ImageFeatureModel.RESNET50,
                        features=[0.1] * 2048,
                        dimension=2048,
                        confidence=0.95
                    )
                ],
                perceptual_hashes=[
                    ImageHash(
                        hash_type=ImageHashType.PERCEPTUAL_HASH,
                        hash_value="abcd1234efgh5678",
                        bit_length=64
                    )
                ],
                color_profile=ImageColorProfile(
                    dominant_colors=["#FF0000", "#00FF00"],
                    color_palette=[{"color": "#FF0000", "percentage": 30}],
                    average_color="#808080",
                    brightness=0.7,
                    contrast=0.8,
                    saturation=0.6
                ),
                quality=ImageQuality(
                    overall_score=0.85,
                    sharpness=0.9,
                    blur_score=0.1
                ),
                processing_time_ms=250.0
            ),
            analysis_success=True,
            processing_time_ms=250.0,
            models_used=["resnet50", "efficientnet"],
            errors=[],
            warnings=[]
        )
        mock_get_service.analyze_image.return_value = mock_response
        
        response = client.post("/search/image-similarity/analyze", json=sample_analysis_request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["asset_id"] == "asset_123"
        assert data["analysis_success"] == True
        assert data["processing_time_ms"] == 250.0
        assert len(data["models_used"]) == 2
        assert len(data["errors"]) == 0
        
        # Check analysis structure
        analysis = data["analysis"]
        assert analysis["asset_id"] == "asset_123"
        assert len(analysis["feature_vectors"]) >= 1
        assert len(analysis["perceptual_hashes"]) >= 1
        assert analysis["color_profile"] is not None
        assert analysis["quality"] is not None
    
    def test_analyze_image_comprehensive(self, mock_get_service, client, sample_comprehensive_analysis_data):
        """Test comprehensive image analysis"""
        mock_response = ImageAnalysisResponse(
            asset_id="asset_comprehensive",
            analysis=ImageAnalysis(
                asset_id="asset_comprehensive",
                image_path="/storage/asset_comprehensive.jpg",
                dimensions={"width": 2048, "height": 1536},
                file_size=5234567,
                format="png",
                feature_vectors=[
                    ImageFeatureVector(
                        model=ImageFeatureModel.RESNET50,
                        features=[0.1] * 2048,
                        dimension=2048,
                        confidence=0.92
                    ),
                    ImageFeatureVector(
                        model=ImageFeatureModel.VGG16,
                        features=[0.2] * 4096,
                        dimension=4096,
                        confidence=0.88
                    )
                ],
                perceptual_hashes=[
                    ImageHash(
                        hash_type=ImageHashType.PERCEPTUAL_HASH,
                        hash_value="abcd1234efgh5678",
                        bit_length=64
                    ),
                    ImageHash(
                        hash_type=ImageHashType.AVERAGE_HASH,
                        hash_value="1234abcd5678efgh",
                        bit_length=64
                    )
                ],
                processing_time_ms=450.0,
                detected_objects=[{"class": "person", "confidence": 0.9}],
                object_count=1
            ),
            analysis_success=True,
            processing_time_ms=450.0,
            models_used=["resnet50", "vgg16", "clip", "vision_transformer"],
            preprocessing_applied=["resize", "normalize"],
            errors=[],
            warnings=[]
        )
        mock_get_service.analyze_image.return_value = mock_response
        
        response = client.post("/search/image-similarity/analyze", json=sample_comprehensive_analysis_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["asset_id"] == "asset_comprehensive"
        assert len(data["models_used"]) == 4
        assert len(data["preprocessing_applied"]) == 2
        assert data["analysis"]["object_count"] == 1
    
    def test_analyze_image_validation_error(self, client):
        """Test image analysis validation error"""
        invalid_data = {
            "asset_id": "",  # Invalid: empty string
            "feature_models": [],  # Invalid: empty list
            "extract_hashes": True,
            "hash_types": []  # Invalid: extract_hashes=True but no hash_types
        }
        
        response = client.post("/search/image-similarity/analyze", json=invalid_data)
        
        assert response.status_code == 422
    
    def test_analyze_image_service_error(self, mock_get_service, client, sample_analysis_request_data):
        """Test image analysis service error"""
        mock_get_service.analyze_image.side_effect = Exception("Analysis service error")
        
        response = client.post("/search/image-similarity/analyze", json=sample_analysis_request_data)
        
        assert response.status_code == 500
        assert "analysis failed" in response.text.lower()
    
    def test_analyze_image_analysis_failure(self, mock_get_service, client, sample_analysis_request_data):
        """Test image analysis with analysis failure"""
        mock_response = ImageAnalysisResponse(
            asset_id="asset_123",
            analysis=ImageAnalysis(
                asset_id="asset_123",
                image_path="/storage/asset_123.jpg",
                dimensions={"width": 0, "height": 0},
                file_size=0,
                format="unknown",
                processing_time_ms=50.0
            ),
            analysis_success=False,
            processing_time_ms=50.0,
            models_used=[],
            errors=["Failed to load image"],
            warnings=["Low quality image detected"]
        )
        mock_get_service.analyze_image.return_value = mock_response
        
        response = client.post("/search/image-similarity/analyze", json=sample_analysis_request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["analysis_success"] == False
        assert len(data["errors"]) == 1
        assert len(data["warnings"]) == 1
        assert "Failed to load image" in data["errors"]
    
    def test_get_image_similarity_stats_success(self, mock_get_service, client):
        """Test getting image similarity statistics"""
        mock_stats = ImageSimilarityStats(
            total_searches=150,
            total_comparisons=150000,
            total_matches_found=3750,
            unique_assets_searched=75,
            avg_search_time_ms=125.5,
            avg_feature_extraction_time_ms=180.2,
            cache_hit_rate=0.65,
            images_analyzed=450,
            total_features_extracted=1500,
            total_hashes_computed=750,
            feature_model_usage={
                "resnet50": 75,
                "vgg16": 30,
                "clip": 25,
                "efficientnet": 20
            },
            similarity_metric_usage={
                "cosine_similarity": 100,
                "euclidean_distance": 30,
                "manhattan_distance": 20
            },
            hash_type_usage={
                "perceptual_hash": 60,
                "average_hash": 40,
                "difference_hash": 25
            },
            search_type_distribution={
                "visual_similarity": 80,
                "duplicate_detection": 35,
                "content_similarity": 25,
                "style_similarity": 10
            },
            similarity_score_distribution={
                "0.9-1.0": 15,
                "0.8-0.9": 45,
                "0.7-0.8": 60,
                "0.6-0.7": 30
            },
            avg_image_quality=0.78,
            quality_distribution={
                "excellent": 25,
                "good": 85,
                "fair": 35,
                "poor": 5
            },
            feature_extraction_failures=3,
            search_failures=1,
            low_quality_images=8
        )
        mock_get_service.get_similarity_stats.return_value = mock_stats
        
        response = client.get("/search/image-similarity/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check basic statistics
        assert data["total_searches"] == 150
        assert data["total_comparisons"] == 150000
        assert data["total_matches_found"] == 3750
        assert data["unique_assets_searched"] == 75
        
        # Check performance metrics
        assert data["avg_search_time_ms"] == 125.5
        assert data["avg_feature_extraction_time_ms"] == 180.2
        assert data["cache_hit_rate"] == 0.65
        
        # Check distributions
        assert "resnet50" in data["feature_model_usage"]
        assert "cosine_similarity" in data["similarity_metric_usage"]
        assert "perceptual_hash" in data["hash_type_usage"]
        assert "visual_similarity" in data["search_type_distribution"]
        
        # Check quality metrics
        assert data["avg_image_quality"] == 0.78
        assert "excellent" in data["quality_distribution"]
        
        # Check error statistics
        assert data["feature_extraction_failures"] == 3
        assert data["search_failures"] == 1
        assert data["low_quality_images"] == 8
    
    def test_get_image_similarity_stats_service_error(self, mock_get_service, client):
        """Test image similarity statistics service error"""
        mock_get_service.get_similarity_stats.side_effect = Exception("Stats service error")
        
        response = client.get("/search/image-similarity/stats")
        
        assert response.status_code == 500
        assert "failed to get" in response.text.lower()
    
    def test_search_with_complex_filters(self, mock_get_service, client):
        """Test search with complex filtering options"""
        complex_search_data = {
            "reference_asset_id": "asset_complex",
            "similarity_type": "visual_similarity",
            "feature_model": "resnet50",
            "similarity_metric": "cosine_similarity",
            "similarity_threshold": 0.75,
            "asset_types": ["image"],
            "file_formats": ["jpg", "png", "tiff"],
            "size_range": {"min": 100000, "max": 10000000},
            "dimension_range": {
                "width": {"min": 800, "max": 4000},
                "height": {"min": 600, "max": 3000}
            },
            "date_range": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            },
            "min_quality_score": 0.6,
            "exclude_low_quality": True,
            "include_duplicates": False,
            "include_near_duplicates": True,
            "region_based": True,
            "multi_scale": True,
            "include_features": True,
            "include_analysis": True,
            "include_thumbnails": True,
            "page": 1,
            "limit": 50,
            "sort_by": "similarity_score",
            "sort_order": "desc"
        }
        
        mock_response = ImageSimilarityResponse(
            query_id="query_complex",
            reference_asset_id="asset_complex",
            similarity_type=ImageSimilarityType.VISUAL_SIMILARITY,
            matches=[],
            total=0,
            page=1,
            limit=50,
            pages=0,
            took=300,
            search_metadata={
                "filters_applied": [
                    "asset_types", "file_formats", "size_range", 
                    "dimension_range", "date_range", "min_quality_score",
                    "exclude_low_quality"
                ]
            }
        )
        mock_get_service.search_similar_images.return_value = mock_response
        
        response = client.post("/search/image-similarity", json=complex_search_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["query_id"] == "query_complex"
        assert len(data["search_metadata"]["filters_applied"]) > 0
        assert data["limit"] == 50
    
    def test_endpoint_authentication_integration(self, client, sample_similarity_search_data):
        """Test endpoint integration with authentication (when implemented)"""
        # This tests the structure for future authentication integration
        response = client.post("/search/image-similarity", json=sample_similarity_search_data)
        
        # Currently returns 200 as authentication is mocked
        # In production, this would test actual auth headers and tokens
        assert response.status_code in [200, 401, 403]
    
    def test_response_performance_metadata(self, mock_get_service, client, sample_similarity_search_data):
        """Test response includes performance metadata"""
        mock_response = ImageSimilarityResponse(
            query_id="query_perf",
            reference_asset_id="asset_123",
            similarity_type=ImageSimilarityType.VISUAL_SIMILARITY,
            matches=[],
            total=0,
            page=1,
            limit=20,
            pages=0,
            took=95,
            feature_extraction_time=40,
            search_time=55,
            search_metadata={
                "execution_time": 0.095,
                "cache_hit": False,
                "similarity_type": "visual_similarity"
            }
        )
        mock_get_service.search_similar_images.return_value = mock_response
        
        response = client.post("/search/image-similarity", json=sample_similarity_search_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["took"] == 95
        assert data["feature_extraction_time"] == 40
        assert data["search_time"] == 55
        assert "execution_time" in data["search_metadata"]
        assert "cache_hit" in data["search_metadata"]
    
    def test_pagination_and_sorting(self, mock_get_service, client):
        """Test pagination and sorting functionality"""
        paginated_search_data = {
            "reference_asset_id": "asset_pagination",
            "similarity_type": "visual_similarity",
            "feature_model": "resnet50",
            "similarity_metric": "cosine_similarity",
            "page": 2,
            "limit": 10,
            "sort_by": "similarity_score",
            "sort_order": "asc"
        }
        
        mock_response = ImageSimilarityResponse(
            query_id="query_pagination",
            reference_asset_id="asset_pagination",
            similarity_type=ImageSimilarityType.VISUAL_SIMILARITY,
            matches=[
                SimilarityMatch(
                    asset_id=f"asset_{i}",
                    similarity_score=0.7 + (i * 0.01),
                    match_type="visual_similarity"
                ) for i in range(10)
            ],
            total=25,
            page=2,
            limit=10,
            pages=3,
            took=120,
            search_metadata={"sort_by": "similarity_score", "sort_order": "asc"}
        )
        mock_get_service.search_similar_images.return_value = mock_response
        
        response = client.post("/search/image-similarity", json=paginated_search_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 2
        assert data["limit"] == 10
        assert data["total"] == 25
        assert data["pages"] == 3
        assert len(data["matches"]) == 10
        assert "sort_by" in data["search_metadata"]
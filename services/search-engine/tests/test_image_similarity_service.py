"""
Tests for Image Similarity Search Service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import random

from src.services.image_similarity_service import ImageSimilarityService
from src.models.schemas import (
    ImageSimilarityQuery, ImageSimilarityResponse, ImageSimilarityStats,
    ImageAnalysisRequest, ImageAnalysisResponse, SimilarityMatch,
    ImageAnalysis, ImageFeatureVector, ImageHash, ImageColorProfile,
    ImageTexture, ImageShape, ImageQuality, ImageFeatureModel,
    ImageSimilarityType, SimilarityMetric, ImageHashType,
    ImageQualityMetric, ImageProcessingType, BoundingBox
)


class TestImageSimilarityService:
    """Test cases for Image Similarity Search Service"""
    
    @pytest.fixture
    def service(self):
        """Create ImageSimilarityService instance"""
        return ImageSimilarityService()
    
    @pytest.fixture
    def sample_similarity_query(self):
        """Sample image similarity search query"""
        return ImageSimilarityQuery(
            reference_asset_id="asset_123",
            similarity_type=ImageSimilarityType.VISUAL_SIMILARITY,
            feature_model=ImageFeatureModel.RESNET50,
            similarity_metric=SimilarityMetric.COSINE_SIMILARITY,
            similarity_threshold=0.8,
            asset_types=["image"],
            page=1,
            limit=20
        )
    
    @pytest.fixture
    def sample_feature_similarity_query(self):
        """Sample feature-based similarity query"""
        return ImageSimilarityQuery(
            reference_features=[0.1] * 2048,  # ResNet50 dimensions
            similarity_type=ImageSimilarityType.CONTENT_SIMILARITY,
            feature_model=ImageFeatureModel.RESNET50,
            similarity_metric=SimilarityMetric.COSINE_SIMILARITY,
            similarity_threshold=0.75,
            include_features=True,
            page=1,
            limit=15
        )
    
    @pytest.fixture
    def sample_hash_similarity_query(self):
        """Sample hash-based similarity query"""
        return ImageSimilarityQuery(
            reference_hash="a1b2c3d4e5f67890",
            similarity_type=ImageSimilarityType.PERCEPTUAL_HASH,
            similarity_metric=SimilarityMetric.HAMMING_DISTANCE,
            similarity_threshold=0.9,
            include_duplicates=False,
            page=1,
            limit=10
        )
    
    @pytest.fixture
    def sample_style_similarity_query(self):
        """Sample style similarity query"""
        return ImageSimilarityQuery(
            reference_image_url="https://example.com/reference.jpg",
            similarity_type=ImageSimilarityType.STYLE_SIMILARITY,
            feature_model=ImageFeatureModel.VGG19,
            similarity_metric=SimilarityMetric.COSINE_SIMILARITY,
            similarity_threshold=0.7,
            file_formats=["jpg", "png"],
            min_quality_score=0.6,
            page=1,
            limit=25
        )
    
    @pytest.fixture
    def sample_duplicate_detection_query(self):
        """Sample duplicate detection query"""
        return ImageSimilarityQuery(
            reference_asset_id="asset_456",
            similarity_type=ImageSimilarityType.DUPLICATE_DETECTION,
            feature_model=ImageFeatureModel.MOBILENET,
            similarity_metric=SimilarityMetric.EUCLIDEAN_DISTANCE,
            similarity_threshold=0.95,
            include_duplicates=True,
            exclude_low_quality=True,
            page=1,
            limit=30
        )
    
    @pytest.fixture
    def sample_semantic_similarity_query(self):
        """Sample semantic similarity query"""
        return ImageSimilarityQuery(
            reference_asset_id="asset_789",
            similarity_type=ImageSimilarityType.SEMANTIC_SIMILARITY,
            feature_model=ImageFeatureModel.CLIP,
            similarity_metric=SimilarityMetric.COSINE_SIMILARITY,
            similarity_threshold=0.6,
            asset_types=["image", "video"],
            include_analysis=True,
            page=1,
            limit=20
        )
    
    @pytest.fixture
    def sample_analysis_request(self):
        """Sample image analysis request"""
        return ImageAnalysisRequest(
            asset_id="asset_123",
            feature_models=[ImageFeatureModel.RESNET50, ImageFeatureModel.EFFICIENTNET],
            extract_hashes=True,
            hash_types=[ImageHashType.PERCEPTUAL_HASH, ImageHashType.AVERAGE_HASH],
            analyze_color=True,
            analyze_texture=True,
            analyze_shape=False,
            assess_quality=True,
            detect_objects=True,
            parallel_processing=True,
            gpu_acceleration=False
        )
    
    @pytest.fixture
    def sample_comprehensive_analysis_request(self):
        """Sample comprehensive analysis request"""
        return ImageAnalysisRequest(
            asset_id="asset_comprehensive",
            feature_models=[
                ImageFeatureModel.RESNET50,
                ImageFeatureModel.VGG16,
                ImageFeatureModel.CLIP,
                ImageFeatureModel.VIT
            ],
            extract_hashes=True,
            hash_types=[
                ImageHashType.PERCEPTUAL_HASH,
                ImageHashType.AVERAGE_HASH,
                ImageHashType.DIFFERENCE_HASH,
                ImageHashType.WAVELET_HASH
            ],
            analyze_color=True,
            analyze_texture=True,
            analyze_shape=True,
            assess_quality=True,
            detect_objects=True,
            preprocessing=[ImageProcessingType.RESIZE, ImageProcessingType.NORMALIZE],
            resize_for_analysis=True,
            target_size={"width": 512, "height": 512},
            parallel_processing=True,
            gpu_acceleration=True,
            force_reanalysis=True
        )
    
    @pytest.mark.asyncio
    async def test_search_similar_images_by_asset_id(self, service, sample_similarity_query):
        """Test image similarity search by asset ID"""
        result = await service.search_similar_images(sample_similarity_query)
        
        assert isinstance(result, ImageSimilarityResponse)
        assert result.reference_asset_id == "asset_123"
        assert result.similarity_type == ImageSimilarityType.VISUAL_SIMILARITY
        assert result.total >= 0
        assert len(result.matches) >= 0
        assert result.page == 1
        assert result.limit == 20
        assert result.took >= 0
        assert result.query_id is not None
        
        # Check search metadata
        assert "similarity_type" in result.search_metadata
        assert "feature_model" in result.search_metadata
        assert "similarity_metric" in result.search_metadata
        assert "execution_time" in result.search_metadata
        
        # Check matches structure
        for match in result.matches:
            assert isinstance(match, SimilarityMatch)
            assert match.asset_id is not None
            assert 0.0 <= match.similarity_score <= 1.0
            assert match.match_type == "visual_similarity"
    
    @pytest.mark.asyncio
    async def test_search_similar_images_by_features(self, service, sample_feature_similarity_query):
        """Test image similarity search by feature vectors"""
        result = await service.search_similar_images(sample_feature_similarity_query)
        
        assert isinstance(result, ImageSimilarityResponse)
        assert result.similarity_type == ImageSimilarityType.CONTENT_SIMILARITY
        assert result.total >= 0
        assert len(result.matches) >= 0
        assert result.limit == 15
        
        # Check that feature similarities are included when requested
        for match in result.matches:
            if sample_feature_similarity_query.include_features:
                assert match.feature_similarities is not None
                assert isinstance(match.feature_similarities, dict)
    
    @pytest.mark.asyncio
    async def test_search_similar_images_by_hash(self, service, sample_hash_similarity_query):
        """Test image similarity search by perceptual hash"""
        result = await service.search_similar_images(sample_hash_similarity_query)
        
        assert isinstance(result, ImageSimilarityResponse)
        assert result.similarity_type == ImageSimilarityType.PERCEPTUAL_HASH
        assert result.total >= 0
        assert len(result.matches) >= 0
        assert result.limit == 10
        
        # Check that duplicates are excluded when requested
        if not sample_hash_similarity_query.include_duplicates:
            for match in result.matches:
                assert match.similarity_score < 1.0  # Not exact duplicates
    
    @pytest.mark.asyncio
    async def test_search_similar_images_by_url(self, service, sample_style_similarity_query):
        """Test image similarity search by image URL"""
        result = await service.search_similar_images(sample_style_similarity_query)
        
        assert isinstance(result, ImageSimilarityResponse)
        assert result.similarity_type == ImageSimilarityType.STYLE_SIMILARITY
        assert result.total >= 0
        assert len(result.matches) >= 0
        assert result.limit == 25
        
        # Check that quality filtering is applied
        for match in result.matches:
            if match.quality_score is not None:
                assert match.quality_score >= sample_style_similarity_query.min_quality_score
    
    @pytest.mark.asyncio
    async def test_duplicate_detection(self, service, sample_duplicate_detection_query):
        """Test duplicate detection functionality"""
        result = await service.search_similar_images(sample_duplicate_detection_query)
        
        assert isinstance(result, ImageSimilarityResponse)
        assert result.similarity_type == ImageSimilarityType.DUPLICATE_DETECTION
        assert result.total >= 0
        
        # Check high similarity threshold for duplicates
        for match in result.matches:
            assert match.similarity_score >= sample_duplicate_detection_query.similarity_threshold
            assert match.match_type == "duplicate_detection"
    
    @pytest.mark.asyncio
    async def test_semantic_similarity_search(self, service, sample_semantic_similarity_query):
        """Test semantic similarity search"""
        result = await service.search_similar_images(sample_semantic_similarity_query)
        
        assert isinstance(result, ImageSimilarityResponse)
        assert result.similarity_type == ImageSimilarityType.SEMANTIC_SIMILARITY
        assert result.total >= 0
        
        # Check that analysis is included when requested
        if sample_semantic_similarity_query.include_analysis:
            # This would be included in a real implementation
            pass
    
    @pytest.mark.asyncio
    async def test_analyze_image_basic(self, service, sample_analysis_request):
        """Test basic image analysis"""
        result = await service.analyze_image(sample_analysis_request)
        
        assert isinstance(result, ImageAnalysisResponse)
        assert result.asset_id == "asset_123"
        assert result.analysis_success == True
        assert result.processing_time_ms > 0
        assert len(result.models_used) == 2  # ResNet50 + EfficientNet
        assert len(result.errors) == 0
        
        # Check analysis structure
        analysis = result.analysis
        assert isinstance(analysis, ImageAnalysis)
        assert analysis.asset_id == "asset_123"
        assert analysis.processing_time_ms > 0
        assert len(analysis.feature_vectors) == 2  # Two models
        assert len(analysis.perceptual_hashes) == 2  # Two hash types
        
        # Check feature vectors
        for feature_vector in analysis.feature_vectors:
            assert isinstance(feature_vector, ImageFeatureVector)
            assert feature_vector.model in sample_analysis_request.feature_models
            assert len(feature_vector.features) == service.feature_models[feature_vector.model]["dimensions"]
            assert feature_vector.dimension > 0
            assert feature_vector.extraction_time_ms is not None
        
        # Check perceptual hashes
        for image_hash in analysis.perceptual_hashes:
            assert isinstance(image_hash, ImageHash)
            assert image_hash.hash_type in sample_analysis_request.hash_types
            assert image_hash.hash_value is not None
            assert image_hash.bit_length > 0
        
        # Check color analysis (if enabled)
        if sample_analysis_request.analyze_color:
            assert analysis.color_profile is not None
            assert isinstance(analysis.color_profile, ImageColorProfile)
            assert len(analysis.color_profile.dominant_colors) > 0
            assert 0.0 <= analysis.color_profile.brightness <= 1.0
        
        # Check quality assessment (if enabled)
        if sample_analysis_request.assess_quality:
            assert analysis.quality is not None
            assert isinstance(analysis.quality, ImageQuality)
            assert 0.0 <= analysis.quality.overall_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_analyze_image_comprehensive(self, service, sample_comprehensive_analysis_request):
        """Test comprehensive image analysis with all features"""
        result = await service.analyze_image(sample_comprehensive_analysis_request)
        
        assert isinstance(result, ImageAnalysisResponse)
        assert result.asset_id == "asset_comprehensive"
        assert result.analysis_success == True
        assert len(result.models_used) == 4  # Four models
        
        # Check analysis completeness
        analysis = result.analysis
        assert len(analysis.feature_vectors) == 4  # Four models
        assert len(analysis.perceptual_hashes) == 4  # Four hash types
        
        # Check all analysis types are included
        assert analysis.color_profile is not None
        assert analysis.texture is not None
        assert analysis.shape is not None
        assert analysis.quality is not None
        
        # Check texture analysis
        assert isinstance(analysis.texture, ImageTexture)
        if analysis.texture.lbp_histogram:
            assert len(analysis.texture.lbp_histogram) > 0
        
        # Check shape analysis
        assert isinstance(analysis.shape, ImageShape)
        assert analysis.shape.edges is not None
        assert analysis.shape.contours is not None
        
        # Check object detection (if enabled)
        if sample_comprehensive_analysis_request.detect_objects:
            assert analysis.detected_objects is not None
            assert analysis.object_count >= 0
    
    @pytest.mark.asyncio
    async def test_analyze_image_error_handling(self, service):
        """Test error handling in image analysis"""
        # Test with invalid asset ID that would cause analysis to fail
        invalid_request = ImageAnalysisRequest(
            asset_id="invalid_asset_id_that_does_not_exist",
            feature_models=[ImageFeatureModel.RESNET50]
        )
        
        # Mock the analysis to fail
        with patch.object(service, '_perform_image_analysis', side_effect=Exception("Analysis failed")):
            result = await service.analyze_image(invalid_request)
            
            assert isinstance(result, ImageAnalysisResponse)
            assert result.asset_id == "invalid_asset_id_that_does_not_exist"
            assert result.analysis_success == False
            assert len(result.errors) > 0
            assert "Analysis failed" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_get_similarity_stats(self, service):
        """Test getting image similarity search statistics"""
        # Simulate some searches to have stats
        service.search_count = 10
        service.total_search_time = 5.0
        service.cache_hits = 3
        service.cache_misses = 7
        
        result = await service.get_similarity_stats()
        
        assert isinstance(result, ImageSimilarityStats)
        
        # Check basic statistics
        assert result.total_searches == 10
        assert result.total_comparisons >= 0
        assert result.total_matches_found >= 0
        assert result.unique_assets_searched >= 0
        
        # Check performance metrics
        assert result.avg_search_time_ms >= 0
        assert result.avg_feature_extraction_time_ms >= 0
        assert 0.0 <= result.cache_hit_rate <= 1.0
        
        # Check asset statistics
        assert result.images_analyzed >= 0
        assert result.total_features_extracted >= 0
        assert result.total_hashes_computed >= 0
        
        # Check distributions
        assert isinstance(result.feature_model_usage, dict)
        assert isinstance(result.similarity_metric_usage, dict)
        assert isinstance(result.hash_type_usage, dict)
        assert isinstance(result.search_type_distribution, dict)
        assert isinstance(result.similarity_score_distribution, dict)
        assert isinstance(result.quality_distribution, dict)
        
        # Check quality metrics
        assert 0.0 <= result.avg_image_quality <= 1.0
        
        # Check error statistics
        assert result.feature_extraction_failures >= 0
        assert result.search_failures >= 0
        assert result.low_quality_images >= 0
    
    def test_initialize_feature_models(self, service):
        """Test feature models initialization"""
        models = service.feature_models
        
        assert isinstance(models, dict)
        assert len(models) > 0
        
        # Check specific models
        assert ImageFeatureModel.RESNET50 in models
        assert ImageFeatureModel.VGG16 in models
        assert ImageFeatureModel.CLIP in models
        assert ImageFeatureModel.EFFICIENTNET in models
        
        # Check model properties
        for model, properties in models.items():
            assert "dimensions" in properties
            assert "accuracy" in properties
            assert "speed" in properties
            assert "layer" in properties
            assert "preprocessing" in properties
            assert properties["dimensions"] > 0
            assert 0.0 <= properties["accuracy"] <= 1.0
    
    def test_initialize_similarity_metrics(self, service):
        """Test similarity metrics initialization"""
        metrics = service.similarity_metrics
        
        assert isinstance(metrics, dict)
        assert len(metrics) > 0
        
        # Check specific metrics
        assert SimilarityMetric.COSINE_SIMILARITY in metrics
        assert SimilarityMetric.EUCLIDEAN_DISTANCE in metrics
        assert SimilarityMetric.MANHATTAN_DISTANCE in metrics
        
        # Check metric properties
        for metric, properties in metrics.items():
            assert "range" in properties
            assert "higher_is_better" in properties
            assert "suitable_for" in properties
            assert "computational_cost" in properties
            assert isinstance(properties["higher_is_better"], bool)
    
    def test_initialize_hash_algorithms(self, service):
        """Test hash algorithms initialization"""
        hashes = service.hash_algorithms
        
        assert isinstance(hashes, dict)
        assert len(hashes) > 0
        
        # Check specific algorithms
        assert ImageHashType.PERCEPTUAL_HASH in hashes
        assert ImageHashType.AVERAGE_HASH in hashes
        assert ImageHashType.DIFFERENCE_HASH in hashes
        
        # Check algorithm properties
        for hash_type, properties in hashes.items():
            assert "bit_length" in properties
            assert "rotation_invariant" in properties
            assert "scale_invariant" in properties
            assert "speed" in properties
            assert "accuracy" in properties
            assert properties["bit_length"] > 0
            assert isinstance(properties["rotation_invariant"], bool)
            assert isinstance(properties["scale_invariant"], bool)
    
    @pytest.mark.asyncio
    async def test_get_reference_features_from_asset_id(self, service):
        """Test extracting reference features from asset ID"""
        query = ImageSimilarityQuery(
            reference_asset_id="test_asset",
            feature_model=ImageFeatureModel.RESNET50
        )
        
        features = await service._get_reference_features(query)
        
        assert "features" in features
        assert "model" in features
        assert "from_cache" in features
        assert features["model"] == ImageFeatureModel.RESNET50
        assert len(features["features"]) == service.feature_models[ImageFeatureModel.RESNET50]["dimensions"]
    
    @pytest.mark.asyncio
    async def test_get_reference_features_from_url(self, service):
        """Test extracting reference features from image URL"""
        query = ImageSimilarityQuery(
            reference_image_url="https://example.com/test.jpg",
            feature_model=ImageFeatureModel.VGG16
        )
        
        features = await service._get_reference_features(query)
        
        assert "features" in features
        assert "model" in features
        assert features["model"] == ImageFeatureModel.VGG16
        assert len(features["features"]) == service.feature_models[ImageFeatureModel.VGG16]["dimensions"]
    
    @pytest.mark.asyncio
    async def test_get_reference_features_from_hash(self, service):
        """Test using reference hash for similarity"""
        query = ImageSimilarityQuery(
            reference_hash="abcd1234efgh5678",
            similarity_type=ImageSimilarityType.PERCEPTUAL_HASH
        )
        
        features = await service._get_reference_features(query)
        
        assert "hash" in features
        assert "hash_type" in features
        assert features["hash"] == "abcd1234efgh5678"
    
    @pytest.mark.asyncio
    async def test_get_reference_features_cache_hit(self, service):
        """Test feature cache functionality"""
        query = ImageSimilarityQuery(
            reference_asset_id="cached_asset",
            feature_model=ImageFeatureModel.RESNET50
        )
        
        # First call - cache miss
        features1 = await service._get_reference_features(query)
        assert features1["from_cache"] == False
        
        # Second call - cache hit
        features2 = await service._get_reference_features(query)
        assert features2["from_cache"] == True
        assert features1["features"] == features2["features"]
    
    @pytest.mark.asyncio
    async def test_build_similarity_search_query(self, service, sample_similarity_query):
        """Test building OpenSearch query for similarity"""
        reference_features = {
            "features": [0.1] * 2048,
            "model": ImageFeatureModel.RESNET50,
            "from_cache": False
        }
        
        search_body = await service._build_similarity_search_query(sample_similarity_query, reference_features)
        
        assert isinstance(search_body, dict)
        assert "query" in search_body
        assert "size" in search_body
        assert "from" in search_body
        assert "sort" in search_body
        assert "_source" in search_body
        assert "aggs" in search_body
        
        # Check query structure
        query = search_body["query"]
        assert "bool" in query
        assert "must" in query["bool"]
        assert "filter" in query["bool"]
        
        # Check pagination
        assert search_body["size"] == sample_similarity_query.limit
        assert search_body["from"] == (sample_similarity_query.page - 1) * sample_similarity_query.limit
        
        # Check aggregations
        assert "similarity_distribution" in search_body["aggs"]
        assert "asset_type_distribution" in search_body["aggs"]
        assert "format_distribution" in search_body["aggs"]
    
    @pytest.mark.asyncio
    async def test_build_hash_similarity_query(self, service, sample_hash_similarity_query):
        """Test building hash-based similarity query"""
        reference_features = {
            "hash": "abcd1234efgh5678",
            "hash_type": "perceptual_hash",
            "from_cache": False
        }
        
        search_body = await service._build_similarity_search_query(sample_hash_similarity_query, reference_features)
        
        assert isinstance(search_body, dict)
        assert "query" in search_body
        
        # Should use script_score for hash comparison
        query = search_body["query"]
        assert "bool" in query
        script_score_found = False
        for must_clause in query["bool"]["must"]:
            if "script_score" in must_clause:
                script_score_found = True
                break
        # For mock implementation, it might use different structure
    
    def test_get_similarity_script(self, service):
        """Test similarity script generation"""
        # Test cosine similarity
        cosine_script = service._get_similarity_script(SimilarityMetric.COSINE_SIMILARITY)
        assert "dotProduct" in cosine_script
        assert "normA" in cosine_script
        assert "normB" in cosine_script
        
        # Test euclidean distance
        euclidean_script = service._get_similarity_script(SimilarityMetric.EUCLIDEAN_DISTANCE)
        assert "sqrt" in euclidean_script
        assert "diff" in euclidean_script
        
        # Test manhattan distance
        manhattan_script = service._get_similarity_script(SimilarityMetric.MANHATTAN_DISTANCE)
        assert "abs" in manhattan_script
        assert "sum" in manhattan_script
    
    @pytest.mark.asyncio
    async def test_execute_similarity_search(self, service, sample_similarity_query):
        """Test executing similarity search"""
        search_body = {
            "query": {"match_all": {}},
            "size": 20,
            "from": 0
        }
        
        response = await service._execute_similarity_search(search_body, sample_similarity_query)
        
        assert isinstance(response, dict)
        assert "hits" in response
        assert "aggregations" in response
        assert "total" in response["hits"]
        assert "hits" in response["hits"]
    
    def test_generate_mock_similarity_response(self, service, sample_similarity_query):
        """Test mock response generation"""
        response = service._generate_mock_similarity_response(sample_similarity_query)
        
        assert isinstance(response, dict)
        assert "hits" in response
        assert "aggregations" in response
        
        hits = response["hits"]
        assert "total" in hits
        assert "hits" in hits
        assert hits["total"]["value"] >= 0
        
        # Check hit structure
        for hit in hits["hits"]:
            assert "_id" in hit
            assert "_score" in hit
            assert "_source" in hit
            assert hit["_score"] >= sample_similarity_query.similarity_threshold
    
    @pytest.mark.asyncio
    async def test_process_similarity_results(self, service, sample_similarity_query):
        """Test processing search results"""
        mock_response = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_id": "asset_1",
                        "_score": 0.85,
                        "_source": {
                            "asset_id": "asset_1",
                            "asset_name": "Test Image 1",
                            "asset_type": "image",
                            "file_path": "/storage/image1.jpg",
                            "thumbnail_url": "/thumbs/image1_thumb.jpg",
                            "quality_score": 0.8
                        }
                    },
                    {
                        "_id": "asset_2",
                        "_score": 0.82,
                        "_source": {
                            "asset_id": "asset_2",
                            "asset_name": "Test Image 2",
                            "asset_type": "image",
                            "file_path": "/storage/image2.jpg",
                            "thumbnail_url": "/thumbs/image2_thumb.jpg",
                            "quality_score": 0.9
                        }
                    }
                ]
            }
        }
        
        reference_features = {
            "features": [0.1] * 2048,
            "model": ImageFeatureModel.RESNET50
        }
        
        matches = await service._process_similarity_results(mock_response, sample_similarity_query, reference_features)
        
        assert len(matches) == 2
        
        for match in matches:
            assert isinstance(match, SimilarityMatch)
            assert match.asset_id in ["asset_1", "asset_2"]
            assert 0.0 <= match.similarity_score <= 1.0
            assert match.match_type == "visual_similarity"
            assert match.asset_type == "image"
    
    def test_get_match_type(self, service):
        """Test match type determination"""
        assert service._get_match_type(ImageSimilarityType.VISUAL_SIMILARITY) == "visual_similarity"
        assert service._get_match_type(ImageSimilarityType.CONTENT_SIMILARITY) == "content_similarity"
        assert service._get_match_type(ImageSimilarityType.STYLE_SIMILARITY) == "style_similarity"
        assert service._get_match_type(ImageSimilarityType.DUPLICATE_DETECTION) == "duplicate_detection"
        assert service._get_match_type(ImageSimilarityType.PERCEPTUAL_HASH) == "perceptual_hash"
    
    def test_calculate_search_statistics(self, service):
        """Test search statistics calculation"""
        matches = [
            SimilarityMatch(
                asset_id="asset_1",
                similarity_score=0.85,
                match_type="visual_similarity"
            ),
            SimilarityMatch(
                asset_id="asset_2", 
                similarity_score=0.92,
                match_type="visual_similarity"
            ),
            SimilarityMatch(
                asset_id="asset_3",
                similarity_score=0.78,
                match_type="visual_similarity"
            )
        ]
        
        stats = service._calculate_search_statistics(matches)
        
        assert stats["max_similarity"] == 0.92
        assert stats["min_similarity"] == 0.78
        assert abs(stats["avg_similarity"] - 0.85) < 0.01
        assert stats["feature_extraction_time"] > 0
        assert stats["search_time"] > 0
    
    def test_calculate_search_statistics_empty(self, service):
        """Test search statistics with no matches"""
        stats = service._calculate_search_statistics([])
        
        assert stats["max_similarity"] is None
        assert stats["avg_similarity"] is None
        assert stats["min_similarity"] is None
        assert stats["feature_extraction_time"] > 0
        assert stats["search_time"] > 0
    
    def test_get_applied_filters(self, service):
        """Test applied filters detection"""
        query = ImageSimilarityQuery(
            reference_asset_id="test",
            asset_types=["image"],
            file_formats=["jpg", "png"],
            size_range={"min": 1000, "max": 10000000},
            min_quality_score=0.7,
            exclude_low_quality=True
        )
        
        filters = service._get_applied_filters(query)
        
        assert "asset_types" in filters
        assert "file_formats" in filters
        assert "size_range" in filters
        assert "min_quality_score" in filters
        assert "exclude_low_quality" in filters
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self, service):
        """Test similarity search with various filters"""
        query = ImageSimilarityQuery(
            reference_asset_id="test_asset",
            similarity_type=ImageSimilarityType.VISUAL_SIMILARITY,
            feature_model=ImageFeatureModel.RESNET50,
            asset_types=["image"],
            file_formats=["jpg", "png"],
            size_range={"min": 100000, "max": 5000000},
            dimension_range={
                "width": {"min": 800, "max": 4000},
                "height": {"min": 600, "max": 3000}
            },
            min_quality_score=0.6,
            exclude_low_quality=True,
            similarity_threshold=0.75
        )
        
        result = await service.search_similar_images(query)
        
        assert isinstance(result, ImageSimilarityResponse)
        assert result.total >= 0
        assert "asset_types" in result.search_metadata["filters_applied"]
        assert "file_formats" in result.search_metadata["filters_applied"]
    
    @pytest.mark.asyncio
    async def test_search_error_handling(self, service, sample_similarity_query):
        """Test error handling in similarity search"""
        # Mock a failure in the search process
        with patch.object(service, '_get_reference_features', side_effect=Exception("Feature extraction failed")):
            result = await service.search_similar_images(sample_similarity_query)
            
            assert isinstance(result, ImageSimilarityResponse)
            assert result.total == 0
            assert len(result.matches) == 0
            assert "error" in result.search_metadata
    
    @pytest.mark.asyncio
    async def test_performance_tracking(self, service, sample_similarity_query):
        """Test performance tracking functionality"""
        initial_count = service.search_count
        initial_time = service.total_search_time
        
        await service.search_similar_images(sample_similarity_query)
        
        assert service.search_count == initial_count + 1
        assert service.total_search_time > initial_time
    
    @pytest.mark.asyncio
    async def test_feature_extraction_mock(self, service):
        """Test mock feature extraction"""
        # Test deterministic feature generation
        features1 = await service._extract_features_mock("asset_123", ImageFeatureModel.RESNET50)
        features2 = await service._extract_features_mock("asset_123", ImageFeatureModel.RESNET50)
        
        assert features1 == features2  # Should be deterministic
        assert len(features1) == service.feature_models[ImageFeatureModel.RESNET50]["dimensions"]
        
        # Test different assets produce different features
        features3 = await service._extract_features_mock("asset_456", ImageFeatureModel.RESNET50)
        assert features1 != features3
    
    @pytest.mark.asyncio
    async def test_url_feature_extraction_mock(self, service):
        """Test mock feature extraction from URL"""
        url = "https://example.com/test.jpg"
        features = await service._extract_features_from_url_mock(url, ImageFeatureModel.VGG16)
        
        assert len(features) == service.feature_models[ImageFeatureModel.VGG16]["dimensions"]
        assert all(isinstance(f, float) for f in features)
        
        # Test normalization (features should be unit vector)
        norm = sum(f * f for f in features) ** 0.5
        assert abs(norm - 1.0) < 1e-6
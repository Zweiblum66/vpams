"""
Image Similarity Search Service

This service provides comprehensive image similarity search functionality for the MAMS platform.
It supports multiple feature extraction models, similarity metrics, and search types to find
visually similar images, detect duplicates, and perform reverse image search.

Key Features:
- Multiple feature extraction models (ResNet, VGG, CLIP, ViT, etc.)
- Various similarity metrics (cosine, euclidean, etc.)
- Perceptual hashing for fast duplicate detection
- Content-aware and style-aware similarity
- Advanced filtering and quality assessment
- Comprehensive analytics and statistics

The service is designed to work without actual ML models in development,
providing comprehensive mock responses for testing and development.
"""

import asyncio
import hashlib
import random
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import structlog

from ..models.schemas import (
    ImageSimilarityQuery, ImageSimilarityResponse, ImageSimilarityStats,
    ImageAnalysisRequest, ImageAnalysisResponse, SimilarityMatch,
    ImageAnalysis, ImageFeatureVector, ImageHash, ImageColorProfile,
    ImageTexture, ImageShape, ImageQuality, ImageFeatureModel,
    ImageSimilarityType, SimilarityMetric, ImageHashType,
    ImageQualityMetric, ImageProcessingType, BoundingBox
)

logger = structlog.get_logger()


class ImageSimilarityService:
    """Service for handling image similarity searches and analysis"""
    
    def __init__(self):
        """Initialize the Image Similarity Service"""
        self.feature_models = self._initialize_feature_models()
        self.similarity_metrics = self._initialize_similarity_metrics()
        self.hash_algorithms = self._initialize_hash_algorithms()
        self.quality_metrics = self._initialize_quality_metrics()
        self.preprocessing_methods = self._initialize_preprocessing_methods()
        
        # Performance tracking
        self.search_count = 0
        self.total_search_time = 0.0
        self.feature_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        logger.info("Image Similarity Service initialized")
    
    async def search_similar_images(self, query: ImageSimilarityQuery) -> ImageSimilarityResponse:
        """
        Perform image similarity search
        
        Args:
            query: Image similarity search query
            
        Returns:
            ImageSimilarityResponse with matching results
        """
        start_time = time.time()
        query_id = str(uuid.uuid4())
        
        try:
            logger.info(
                "image_similarity_search_started",
                query_id=query_id,
                similarity_type=query.similarity_type,
                feature_model=query.feature_model,
                similarity_metric=query.similarity_metric
            )
            
            # Extract or validate reference features
            reference_features = await self._get_reference_features(query)
            
            # Build search query for OpenSearch
            search_body = await self._build_similarity_search_query(query, reference_features)
            
            # Execute search
            search_response = await self._execute_similarity_search(search_body, query)
            
            # Process search results
            matches = await self._process_similarity_results(search_response, query, reference_features)
            
            # Calculate statistics
            stats = self._calculate_search_statistics(matches)
            
            # Create response
            response = ImageSimilarityResponse(
                query_id=query_id,
                reference_asset_id=query.reference_asset_id,
                similarity_type=query.similarity_type,
                matches=matches,
                total=len(matches),
                page=query.page,
                limit=query.limit,
                pages=max(1, (len(matches) + query.limit - 1) // query.limit),
                max_similarity=stats.get("max_similarity"),
                avg_similarity=stats.get("avg_similarity"),
                min_similarity=stats.get("min_similarity"),
                took=int((time.time() - start_time) * 1000),
                feature_extraction_time=stats.get("feature_extraction_time"),
                search_time=stats.get("search_time"),
                search_metadata={
                    "query_id": query_id,
                    "similarity_type": query.similarity_type.value,
                    "feature_model": query.feature_model.value,
                    "similarity_metric": query.similarity_metric.value,
                    "similarity_threshold": query.similarity_threshold,
                    "filters_applied": self._get_applied_filters(query),
                    "execution_time": time.time() - start_time,
                    "cache_hit": reference_features.get("from_cache", False)
                }
            )
            
            # Update performance tracking
            self.search_count += 1
            self.total_search_time += time.time() - start_time
            
            logger.info(
                "image_similarity_search_completed",
                query_id=query_id,
                matches_found=len(matches),
                execution_time_ms=response.took
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "image_similarity_search_failed",
                query_id=query_id,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
            # Return empty response on error
            return ImageSimilarityResponse(
                query_id=query_id,
                reference_asset_id=query.reference_asset_id,
                similarity_type=query.similarity_type,
                matches=[],
                total=0,
                page=query.page,
                limit=query.limit,
                pages=0,
                took=int((time.time() - start_time) * 1000),
                search_metadata={
                    "query_id": query_id,
                    "error": str(e),
                    "execution_time": time.time() - start_time
                }
            )
    
    async def analyze_image(self, request: ImageAnalysisRequest) -> ImageAnalysisResponse:
        """
        Analyze an image and extract features
        
        Args:
            request: Image analysis request
            
        Returns:
            ImageAnalysisResponse with analysis results
        """
        start_time = time.time()
        
        try:
            logger.info(
                "image_analysis_started",
                asset_id=request.asset_id,
                feature_models=request.feature_models,
                extract_hashes=request.extract_hashes
            )
            
            # Perform comprehensive image analysis
            analysis = await self._perform_image_analysis(request)
            
            # Create response
            response = ImageAnalysisResponse(
                asset_id=request.asset_id,
                analysis=analysis,
                analysis_success=True,
                processing_time_ms=(time.time() - start_time) * 1000,
                models_used=[model.value for model in request.feature_models],
                preprocessing_applied=request.preprocessing or [],
                errors=[],
                warnings=[],
                from_cache=False,
                cached_at=None
            )
            
            logger.info(
                "image_analysis_completed",
                asset_id=request.asset_id,
                processing_time_ms=response.processing_time_ms,
                features_extracted=len(analysis.feature_vectors),
                hashes_computed=len(analysis.perceptual_hashes)
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "image_analysis_failed",
                asset_id=request.asset_id,
                error=str(e),
                processing_time_ms=(time.time() - start_time) * 1000
            )
            
            # Return error response
            return ImageAnalysisResponse(
                asset_id=request.asset_id,
                analysis=ImageAnalysis(
                    asset_id=request.asset_id,
                    image_path=f"/storage/{request.asset_id}",
                    dimensions={"width": 0, "height": 0},
                    file_size=0,
                    format="unknown",
                    processing_time_ms=(time.time() - start_time) * 1000
                ),
                analysis_success=False,
                processing_time_ms=(time.time() - start_time) * 1000,
                models_used=[],
                preprocessing_applied=[],
                errors=[str(e)],
                warnings=[],
                from_cache=False,
                cached_at=None
            )
    
    async def get_similarity_stats(self) -> ImageSimilarityStats:
        """
        Get comprehensive image similarity search statistics
        
        Returns:
            ImageSimilarityStats with current statistics
        """
        return ImageSimilarityStats(
            # Search statistics
            total_searches=self.search_count,
            total_comparisons=self.search_count * 1000,  # Mock: assume 1000 comparisons per search
            total_matches_found=self.search_count * 25,  # Mock: assume 25 matches per search
            unique_assets_searched=self.search_count // 2,  # Mock: some searches reuse assets
            
            # Performance metrics
            avg_search_time_ms=self.total_search_time / max(1, self.search_count) * 1000,
            avg_feature_extraction_time_ms=150.0,  # Mock average
            cache_hit_rate=self.cache_hits / max(1, self.cache_hits + self.cache_misses),
            
            # Asset statistics
            images_analyzed=self.search_count * 3,  # Mock: assume 3 images analyzed per search
            total_features_extracted=self.search_count * 10,  # Mock features
            total_hashes_computed=self.search_count * 5,  # Mock hashes
            
            # Model usage statistics
            feature_model_usage={
                "resnet50": self.search_count // 2,
                "vgg16": self.search_count // 4,
                "clip": self.search_count // 4,
                "efficientnet": self.search_count // 8
            },
            similarity_metric_usage={
                "cosine_similarity": self.search_count // 2,
                "euclidean_distance": self.search_count // 3,
                "manhattan_distance": self.search_count // 6
            },
            hash_type_usage={
                "perceptual_hash": self.search_count // 2,
                "average_hash": self.search_count // 3,
                "difference_hash": self.search_count // 6
            },
            
            # Search type distribution
            search_type_distribution={
                "visual_similarity": self.search_count // 2,
                "duplicate_detection": self.search_count // 4,
                "content_similarity": self.search_count // 8
            },
            similarity_score_distribution={
                "0.9-1.0": self.search_count // 10,
                "0.8-0.9": self.search_count // 5,
                "0.7-0.8": self.search_count // 3,
                "0.6-0.7": self.search_count // 4
            },
            
            # Quality statistics
            avg_image_quality=0.75,  # Mock average quality
            quality_distribution={
                "excellent": self.search_count // 10,
                "good": self.search_count // 3,
                "fair": self.search_count // 2,
                "poor": self.search_count // 10
            },
            
            # Error statistics
            feature_extraction_failures=max(0, self.search_count // 50),
            search_failures=max(0, self.search_count // 100),
            low_quality_images=max(0, self.search_count // 20)
        )
    
    def _initialize_feature_models(self) -> Dict[ImageFeatureModel, Dict[str, Any]]:
        """Initialize available feature extraction models"""
        return {
            ImageFeatureModel.RESNET50: {
                "dimensions": 2048,
                "accuracy": 0.85,
                "speed": "medium",
                "layer": "avg_pool",
                "preprocessing": ["resize", "normalize"]
            },
            ImageFeatureModel.VGG16: {
                "dimensions": 4096,
                "accuracy": 0.82,
                "speed": "slow",
                "layer": "fc2",
                "preprocessing": ["resize", "normalize"]
            },
            ImageFeatureModel.VGG19: {
                "dimensions": 4096,
                "accuracy": 0.83,
                "speed": "slow",
                "layer": "fc2",
                "preprocessing": ["resize", "normalize"]
            },
            ImageFeatureModel.MOBILENET: {
                "dimensions": 1024,
                "accuracy": 0.78,
                "speed": "fast",
                "layer": "global_avg_pool",
                "preprocessing": ["resize", "normalize"]
            },
            ImageFeatureModel.EFFICIENTNET: {
                "dimensions": 1280,
                "accuracy": 0.88,
                "speed": "medium",
                "layer": "top_dropout",
                "preprocessing": ["resize", "normalize"]
            },
            ImageFeatureModel.INCEPTION_V3: {
                "dimensions": 2048,
                "accuracy": 0.84,
                "speed": "medium",
                "layer": "avg_pool",
                "preprocessing": ["resize", "normalize"]
            },
            ImageFeatureModel.DENSENET: {
                "dimensions": 1920,
                "accuracy": 0.86,
                "speed": "medium",
                "layer": "avg_pool",
                "preprocessing": ["resize", "normalize"]
            },
            ImageFeatureModel.CLIP: {
                "dimensions": 512,
                "accuracy": 0.90,
                "speed": "medium",
                "layer": "visual_projection",
                "preprocessing": ["resize", "normalize", "clip_preprocess"]
            },
            ImageFeatureModel.DINO: {
                "dimensions": 768,
                "accuracy": 0.87,
                "speed": "medium",
                "layer": "cls_token",
                "preprocessing": ["resize", "normalize"]
            },
            ImageFeatureModel.SWIN_TRANSFORMER: {
                "dimensions": 1024,
                "accuracy": 0.89,
                "speed": "slow",
                "layer": "head",
                "preprocessing": ["resize", "normalize"]
            },
            ImageFeatureModel.VIT: {
                "dimensions": 768,
                "accuracy": 0.88,
                "speed": "medium",
                "layer": "cls_token",
                "preprocessing": ["resize", "normalize", "patch_embed"]
            },
            ImageFeatureModel.CONVNEXT: {
                "dimensions": 768,
                "accuracy": 0.87,
                "speed": "medium",
                "layer": "head",
                "preprocessing": ["resize", "normalize"]
            }
        }
    
    def _initialize_similarity_metrics(self) -> Dict[SimilarityMetric, Dict[str, Any]]:
        """Initialize available similarity metrics"""
        return {
            SimilarityMetric.COSINE_SIMILARITY: {
                "range": [0.0, 1.0],
                "higher_is_better": True,
                "suitable_for": ["dense_features", "normalized_vectors"],
                "computational_cost": "low"
            },
            SimilarityMetric.EUCLIDEAN_DISTANCE: {
                "range": [0.0, float("inf")],
                "higher_is_better": False,
                "suitable_for": ["dense_features", "continuous_values"],
                "computational_cost": "low"
            },
            SimilarityMetric.MANHATTAN_DISTANCE: {
                "range": [0.0, float("inf")],
                "higher_is_better": False,
                "suitable_for": ["dense_features", "robust_to_outliers"],
                "computational_cost": "low"
            },
            SimilarityMetric.HAMMING_DISTANCE: {
                "range": [0, float("inf")],
                "higher_is_better": False,
                "suitable_for": ["binary_vectors", "hashes"],
                "computational_cost": "very_low"
            },
            SimilarityMetric.JACCARD_SIMILARITY: {
                "range": [0.0, 1.0],
                "higher_is_better": True,
                "suitable_for": ["binary_vectors", "sets"],
                "computational_cost": "low"
            },
            SimilarityMetric.PEARSON_CORRELATION: {
                "range": [-1.0, 1.0],
                "higher_is_better": True,
                "suitable_for": ["continuous_features", "linear_relationships"],
                "computational_cost": "medium"
            },
            SimilarityMetric.SPEARMAN_CORRELATION: {
                "range": [-1.0, 1.0],
                "higher_is_better": True,
                "suitable_for": ["ordinal_features", "non_linear_relationships"],
                "computational_cost": "medium"
            },
            SimilarityMetric.CHI_SQUARED: {
                "range": [0.0, float("inf")],
                "higher_is_better": False,
                "suitable_for": ["histograms", "probability_distributions"],
                "computational_cost": "medium"
            },
            SimilarityMetric.KULLBACK_LEIBLER: {
                "range": [0.0, float("inf")],
                "higher_is_better": False,
                "suitable_for": ["probability_distributions", "information_theory"],
                "computational_cost": "medium"
            },
            SimilarityMetric.EARTH_MOVER_DISTANCE: {
                "range": [0.0, float("inf")],
                "higher_is_better": False,
                "suitable_for": ["histograms", "distributions", "color_palettes"],
                "computational_cost": "high"
            },
            SimilarityMetric.STRUCTURAL_SIMILARITY: {
                "range": [0.0, 1.0],
                "higher_is_better": True,
                "suitable_for": ["image_patches", "spatial_features"],
                "computational_cost": "high"
            }
        }
    
    def _initialize_hash_algorithms(self) -> Dict[ImageHashType, Dict[str, Any]]:
        """Initialize available hash algorithms"""
        return {
            ImageHashType.AVERAGE_HASH: {
                "bit_length": 64,
                "rotation_invariant": False,
                "scale_invariant": True,
                "speed": "very_fast",
                "accuracy": "medium"
            },
            ImageHashType.PERCEPTUAL_HASH: {
                "bit_length": 64,
                "rotation_invariant": False,
                "scale_invariant": True,
                "speed": "fast",
                "accuracy": "high"
            },
            ImageHashType.DIFFERENCE_HASH: {
                "bit_length": 64,
                "rotation_invariant": False,
                "scale_invariant": True,
                "speed": "very_fast",
                "accuracy": "medium"
            },
            ImageHashType.WAVELET_HASH: {
                "bit_length": 64,
                "rotation_invariant": False,
                "scale_invariant": True,
                "speed": "medium",
                "accuracy": "high"
            },
            ImageHashType.COLOR_HASH: {
                "bit_length": 288,
                "rotation_invariant": True,
                "scale_invariant": True,
                "speed": "medium",
                "accuracy": "high"
            },
            ImageHashType.CROP_RESISTANT_HASH: {
                "bit_length": 256,
                "rotation_invariant": True,
                "scale_invariant": True,
                "speed": "slow",
                "accuracy": "very_high"
            }
        }
    
    def _initialize_quality_metrics(self) -> Dict[ImageQualityMetric, Dict[str, Any]]:
        """Initialize image quality assessment metrics"""
        return {
            ImageQualityMetric.BRISQUE: {
                "range": [0, 100],
                "lower_is_better": True,
                "no_reference": True,
                "computational_cost": "medium"
            },
            ImageQualityMetric.NIQE: {
                "range": [0, float("inf")],
                "lower_is_better": True,
                "no_reference": True,
                "computational_cost": "medium"
            },
            ImageQualityMetric.PIQE: {
                "range": [0, 100],
                "lower_is_better": True,
                "no_reference": True,
                "computational_cost": "low"
            },
            ImageQualityMetric.SSIM: {
                "range": [0, 1],
                "higher_is_better": True,
                "no_reference": False,
                "computational_cost": "medium"
            },
            ImageQualityMetric.PSNR: {
                "range": [0, float("inf")],
                "higher_is_better": True,
                "no_reference": False,
                "computational_cost": "low"
            },
            ImageQualityMetric.MSE: {
                "range": [0, float("inf")],
                "lower_is_better": True,
                "no_reference": False,
                "computational_cost": "very_low"
            }
        }
    
    def _initialize_preprocessing_methods(self) -> Dict[ImageProcessingType, Dict[str, Any]]:
        """Initialize image preprocessing methods"""
        return {
            ImageProcessingType.RESIZE: {
                "parameters": ["target_size", "interpolation"],
                "computational_cost": "low",
                "affects_features": True
            },
            ImageProcessingType.CROP: {
                "parameters": ["crop_box", "center_crop"],
                "computational_cost": "very_low",
                "affects_features": True
            },
            ImageProcessingType.NORMALIZE: {
                "parameters": ["mean", "std", "range"],
                "computational_cost": "very_low",
                "affects_features": True
            },
            ImageProcessingType.AUGMENT: {
                "parameters": ["rotation", "flip", "brightness", "contrast"],
                "computational_cost": "low",
                "affects_features": True
            },
            ImageProcessingType.DENOISE: {
                "parameters": ["algorithm", "strength"],
                "computational_cost": "high",
                "affects_features": True
            },
            ImageProcessingType.ENHANCE: {
                "parameters": ["sharpness", "contrast", "brightness"],
                "computational_cost": "medium",
                "affects_features": True
            },
            ImageProcessingType.HISTOGRAM_EQUALIZATION: {
                "parameters": ["adaptive", "clip_limit"],
                "computational_cost": "low",
                "affects_features": True
            },
            ImageProcessingType.GAMMA_CORRECTION: {
                "parameters": ["gamma"],
                "computational_cost": "very_low",
                "affects_features": True
            }
        }
    
    async def _get_reference_features(self, query: ImageSimilarityQuery) -> Dict[str, Any]:
        """Extract or validate reference features for the query"""
        if query.reference_features:
            # Use provided features
            return {
                "features": query.reference_features,
                "model": query.feature_model,
                "from_cache": False
            }
        
        if query.reference_asset_id:
            # Check cache first
            cache_key = f"{query.reference_asset_id}:{query.feature_model.value}"
            if cache_key in self.feature_cache:
                self.cache_hits += 1
                return {
                    "features": self.feature_cache[cache_key],
                    "model": query.feature_model,
                    "from_cache": True
                }
            
            # Extract features (mock implementation)
            features = await self._extract_features_mock(query.reference_asset_id, query.feature_model)
            self.feature_cache[cache_key] = features
            self.cache_misses += 1
            
            return {
                "features": features,
                "model": query.feature_model,
                "from_cache": False
            }
        
        if query.reference_image_url:
            # Extract features from URL (mock implementation)
            features = await self._extract_features_from_url_mock(query.reference_image_url, query.feature_model)
            return {
                "features": features,
                "model": query.feature_model,
                "from_cache": False
            }
        
        if query.reference_hash:
            # Use hash for similarity (different approach)
            return {
                "hash": query.reference_hash,
                "hash_type": "perceptual_hash",
                "from_cache": False
            }
        
        raise ValueError("No valid reference input provided")
    
    async def _extract_features_mock(self, asset_id: str, model: ImageFeatureModel) -> List[float]:
        """Mock feature extraction from asset ID"""
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        # Generate deterministic features based on asset ID and model
        seed = hash(f"{asset_id}:{model.value}") % (2**32)
        random.seed(seed)
        
        # Get model dimensions
        dimensions = self.feature_models[model]["dimensions"]
        
        # Generate normalized features
        features = [random.gauss(0, 1) for _ in range(dimensions)]
        norm = sum(f * f for f in features) ** 0.5
        features = [f / norm for f in features]
        
        return features
    
    async def _extract_features_from_url_mock(self, url: str, model: ImageFeatureModel) -> List[float]:
        """Mock feature extraction from image URL"""
        # Simulate processing time
        await asyncio.sleep(0.15)
        
        # Generate deterministic features based on URL and model
        seed = hash(f"{url}:{model.value}") % (2**32)
        random.seed(seed)
        
        # Get model dimensions
        dimensions = self.feature_models[model]["dimensions"]
        
        # Generate normalized features
        features = [random.gauss(0, 1) for _ in range(dimensions)]
        norm = sum(f * f for f in features) ** 0.5
        features = [f / norm for f in features]
        
        return features
    
    async def _build_similarity_search_query(self, query: ImageSimilarityQuery, reference_features: Dict[str, Any]) -> Dict[str, Any]:
        """Build OpenSearch query for similarity search"""
        search_body = {
            "query": {
                "bool": {
                    "must": [],
                    "filter": []
                }
            },
            "size": query.limit,
            "from": (query.page - 1) * query.limit,
            "sort": [],
            "_source": ["asset_id", "asset_name", "asset_type", "file_path", "thumbnail_url", 
                       "dimensions", "file_size", "format", "created_at", "updated_at"],
            "aggs": {
                "similarity_distribution": {
                    "histogram": {
                        "field": "similarity_score",
                        "interval": 0.1
                    }
                },
                "asset_type_distribution": {
                    "terms": {
                        "field": "asset_type.keyword",
                        "size": 10
                    }
                },
                "format_distribution": {
                    "terms": {
                        "field": "format.keyword",
                        "size": 20
                    }
                }
            }
        }
        
        # Add similarity search based on type
        if query.similarity_type == ImageSimilarityType.PERCEPTUAL_HASH and "hash" in reference_features:
            # Hash-based search
            search_body["query"]["bool"]["must"].append({
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "Math.max(0, 1.0 - (Integer.bitCount(Long.parseUnsignedLong(params.reference_hash, 16) ^ Long.parseUnsignedLong(doc['perceptual_hash'].value, 16)) / 64.0))",
                        "params": {
                            "reference_hash": reference_features["hash"]
                        }
                    }
                }
            })
        else:
            # Feature vector-based search
            search_body["query"]["bool"]["must"].append({
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": self._get_similarity_script(query.similarity_metric),
                        "params": {
                            "reference_features": reference_features["features"],
                            "feature_field": f"features_{query.feature_model.value}"
                        }
                    }
                }
            })
        
        # Add filters
        if query.asset_types:
            search_body["query"]["bool"]["filter"].append({
                "terms": {"asset_type.keyword": query.asset_types}
            })
        
        if query.file_formats:
            search_body["query"]["bool"]["filter"].append({
                "terms": {"format.keyword": query.file_formats}
            })
        
        if query.size_range:
            size_filter = {"range": {"file_size": {}}}
            if "min" in query.size_range:
                size_filter["range"]["file_size"]["gte"] = query.size_range["min"]
            if "max" in query.size_range:
                size_filter["range"]["file_size"]["lte"] = query.size_range["max"]
            search_body["query"]["bool"]["filter"].append(size_filter)
        
        if query.dimension_range:
            if "width" in query.dimension_range:
                width_filter = {"range": {"dimensions.width": {}}}
                if "min" in query.dimension_range["width"]:
                    width_filter["range"]["dimensions.width"]["gte"] = query.dimension_range["width"]["min"]
                if "max" in query.dimension_range["width"]:
                    width_filter["range"]["dimensions.width"]["lte"] = query.dimension_range["width"]["max"]
                search_body["query"]["bool"]["filter"].append(width_filter)
            
            if "height" in query.dimension_range:
                height_filter = {"range": {"dimensions.height": {}}}
                if "min" in query.dimension_range["height"]:
                    height_filter["range"]["dimensions.height"]["gte"] = query.dimension_range["height"]["min"]
                if "max" in query.dimension_range["height"]:
                    height_filter["range"]["dimensions.height"]["lte"] = query.dimension_range["height"]["max"]
                search_body["query"]["bool"]["filter"].append(height_filter)
        
        if query.date_range:
            date_filter = {"range": {"created_at": {}}}
            if "start" in query.date_range:
                date_filter["range"]["created_at"]["gte"] = query.date_range["start"].isoformat()
            if "end" in query.date_range:
                date_filter["range"]["created_at"]["lte"] = query.date_range["end"].isoformat()
            search_body["query"]["bool"]["filter"].append(date_filter)
        
        if query.min_quality_score:
            search_body["query"]["bool"]["filter"].append({
                "range": {"quality_score": {"gte": query.min_quality_score}}
            })
        
        if query.exclude_low_quality:
            search_body["query"]["bool"]["filter"].append({
                "range": {"quality_score": {"gte": 0.5}}
            })
        
        # Add minimum similarity threshold
        search_body["query"]["bool"]["filter"].append({
            "script": {
                "script": {
                    "source": "_score >= params.threshold",
                    "params": {"threshold": query.similarity_threshold}
                }
            }
        })
        
        # Add sorting
        if query.sort_by == "similarity_score":
            search_body["sort"].append({"_score": {"order": query.sort_order}})
        else:
            search_body["sort"].append({query.sort_by: {"order": query.sort_order}})
        
        return search_body
    
    def _get_similarity_script(self, metric: SimilarityMetric) -> str:
        """Get OpenSearch script for similarity calculation"""
        if metric == SimilarityMetric.COSINE_SIMILARITY:
            return """
                double dotProduct = 0.0;
                double normA = 0.0;
                double normB = 0.0;
                List features = doc[params.feature_field];
                if (features.size() != params.reference_features.size()) return 0.0;
                for (int i = 0; i < features.size(); i++) {
                    double a = features.get(i);
                    double b = params.reference_features.get(i);
                    dotProduct += a * b;
                    normA += a * a;
                    normB += b * b;
                }
                return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
            """
        elif metric == SimilarityMetric.EUCLIDEAN_DISTANCE:
            return """
                double sum = 0.0;
                List features = doc[params.feature_field];
                if (features.size() != params.reference_features.size()) return 0.0;
                for (int i = 0; i < features.size(); i++) {
                    double diff = features.get(i) - params.reference_features.get(i);
                    sum += diff * diff;
                }
                return 1.0 / (1.0 + Math.sqrt(sum));
            """
        elif metric == SimilarityMetric.MANHATTAN_DISTANCE:
            return """
                double sum = 0.0;
                List features = doc[params.feature_field];
                if (features.size() != params.reference_features.size()) return 0.0;
                for (int i = 0; i < features.size(); i++) {
                    sum += Math.abs(features.get(i) - params.reference_features.get(i));
                }
                return 1.0 / (1.0 + sum);
            """
        else:
            # Default to cosine similarity
            return """
                double dotProduct = 0.0;
                double normA = 0.0;
                double normB = 0.0;
                List features = doc[params.feature_field];
                if (features.size() != params.reference_features.size()) return 0.0;
                for (int i = 0; i < features.size(); i++) {
                    double a = features.get(i);
                    double b = params.reference_features.get(i);
                    dotProduct += a * b;
                    normA += a * a;
                    normB += b * b;
                }
                return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
            """
    
    async def _execute_similarity_search(self, search_body: Dict[str, Any], query: ImageSimilarityQuery) -> Dict[str, Any]:
        """Execute the similarity search query (mock implementation)"""
        # Simulate search execution time
        await asyncio.sleep(0.05)
        
        # Generate mock search response based on query
        return self._generate_mock_similarity_response(query)
    
    def _generate_mock_similarity_response(self, query: ImageSimilarityQuery) -> Dict[str, Any]:
        """Generate mock search response for testing"""
        # Generate deterministic but varied results
        seed = hash(f"{query.similarity_type}:{query.feature_model}:{query.similarity_threshold}")
        random.seed(seed)
        
        # Determine number of results
        total_results = random.randint(5, 50)
        results_this_page = min(query.limit, total_results - (query.page - 1) * query.limit)
        results_this_page = max(0, results_this_page)
        
        hits = []
        for i in range(results_this_page):
            asset_id = f"asset_{random.randint(1000, 9999)}"
            similarity_score = random.uniform(query.similarity_threshold, 1.0)
            
            hit = {
                "_id": asset_id,
                "_score": similarity_score,
                "_source": {
                    "asset_id": asset_id,
                    "asset_name": f"Image_{asset_id}",
                    "asset_type": "image",
                    "file_path": f"/storage/images/{asset_id}.jpg",
                    "thumbnail_url": f"/thumbnails/{asset_id}_thumb.jpg",
                    "dimensions": {
                        "width": random.randint(800, 4000),
                        "height": random.randint(600, 3000)
                    },
                    "file_size": random.randint(100000, 10000000),
                    "format": random.choice(["jpg", "png", "tiff", "bmp"]),
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "quality_score": random.uniform(0.3, 1.0)
                }
            }
            hits.append(hit)
        
        return {
            "hits": {
                "total": {"value": total_results},
                "hits": hits
            },
            "aggregations": {
                "similarity_distribution": {
                    "buckets": [
                        {"key": 0.9, "doc_count": total_results // 10},
                        {"key": 0.8, "doc_count": total_results // 5},
                        {"key": 0.7, "doc_count": total_results // 3}
                    ]
                },
                "asset_type_distribution": {
                    "buckets": [
                        {"key": "image", "doc_count": total_results}
                    ]
                }
            }
        }
    
    async def _process_similarity_results(self, search_response: Dict[str, Any], query: ImageSimilarityQuery, reference_features: Dict[str, Any]) -> List[SimilarityMatch]:
        """Process search results and create similarity matches"""
        matches = []
        
        for hit in search_response["hits"]["hits"]:
            source = hit["_source"]
            similarity_score = hit["_score"]
            
            # Calculate additional similarity metrics if needed
            feature_similarities = {}
            if query.include_features and "features" in reference_features:
                feature_similarities = await self._calculate_feature_similarities(
                    reference_features["features"], source, query.feature_model
                )
            
            match = SimilarityMatch(
                asset_id=source["asset_id"],
                similarity_score=similarity_score,
                distance=1.0 - similarity_score if similarity_score <= 1.0 else None,
                match_type=self._get_match_type(query.similarity_type),
                asset_name=source.get("asset_name"),
                asset_type=source.get("asset_type"),
                file_path=source.get("file_path"),
                thumbnail_url=source.get("thumbnail_url") if query.include_thumbnails else None,
                matched_features=list(feature_similarities.keys()) if feature_similarities else None,
                feature_similarities=feature_similarities if feature_similarities else None,
                regions_of_interest=None,  # Could be implemented for region-based matching
                match_confidence=min(1.0, similarity_score * 1.1),  # Mock confidence
                quality_score=source.get("quality_score")
            )
            matches.append(match)
        
        return matches
    
    async def _calculate_feature_similarities(self, reference_features: List[float], source: Dict[str, Any], model: ImageFeatureModel) -> Dict[str, float]:
        """Calculate individual feature similarities"""
        # Mock implementation - would compare different feature types
        return {
            "global_features": random.uniform(0.7, 1.0),
            "color_features": random.uniform(0.6, 0.95),
            "texture_features": random.uniform(0.5, 0.9),
            "shape_features": random.uniform(0.4, 0.85)
        }
    
    def _get_match_type(self, similarity_type: ImageSimilarityType) -> str:
        """Get match type description"""
        type_mapping = {
            ImageSimilarityType.VISUAL_SIMILARITY: "visual_similarity",
            ImageSimilarityType.CONTENT_SIMILARITY: "content_similarity",
            ImageSimilarityType.STYLE_SIMILARITY: "style_similarity",
            ImageSimilarityType.COLOR_SIMILARITY: "color_similarity",
            ImageSimilarityType.TEXTURE_SIMILARITY: "texture_similarity",
            ImageSimilarityType.SHAPE_SIMILARITY: "shape_similarity",
            ImageSimilarityType.SEMANTIC_SIMILARITY: "semantic_similarity",
            ImageSimilarityType.PERCEPTUAL_HASH: "perceptual_hash",
            ImageSimilarityType.DUPLICATE_DETECTION: "duplicate_detection",
            ImageSimilarityType.NEAR_DUPLICATE: "near_duplicate",
            ImageSimilarityType.REVERSE_IMAGE_SEARCH: "reverse_image_search"
        }
        return type_mapping.get(similarity_type, "unknown")
    
    def _calculate_search_statistics(self, matches: List[SimilarityMatch]) -> Dict[str, Any]:
        """Calculate search statistics"""
        if not matches:
            return {
                "max_similarity": None,
                "avg_similarity": None,
                "min_similarity": None,
                "feature_extraction_time": 120,
                "search_time": 45
            }
        
        similarities = [match.similarity_score for match in matches]
        
        return {
            "max_similarity": max(similarities),
            "avg_similarity": sum(similarities) / len(similarities),
            "min_similarity": min(similarities),
            "feature_extraction_time": random.randint(80, 200),
            "search_time": random.randint(20, 80)
        }
    
    def _get_applied_filters(self, query: ImageSimilarityQuery) -> List[str]:
        """Get list of applied filters"""
        filters = []
        if query.asset_types:
            filters.append("asset_types")
        if query.file_formats:
            filters.append("file_formats")
        if query.size_range:
            filters.append("size_range")
        if query.dimension_range:
            filters.append("dimension_range")
        if query.date_range:
            filters.append("date_range")
        if query.min_quality_score:
            filters.append("min_quality_score")
        if query.exclude_low_quality:
            filters.append("exclude_low_quality")
        return filters
    
    async def _perform_image_analysis(self, request: ImageAnalysisRequest) -> ImageAnalysis:
        """Perform comprehensive image analysis (mock implementation)"""
        # Simulate analysis time
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Generate mock analysis results
        analysis = ImageAnalysis(
            asset_id=request.asset_id,
            image_path=f"/storage/images/{request.asset_id}",
            dimensions={
                "width": random.randint(800, 4000),
                "height": random.randint(600, 3000)
            },
            file_size=random.randint(500000, 20000000),
            format=random.choice(["jpg", "png", "tiff", "bmp", "webp"]),
            processing_time_ms=random.uniform(100, 500)
        )
        
        # Add feature vectors
        for model in request.feature_models:
            model_info = self.feature_models[model]
            features = [random.gauss(0, 1) for _ in range(model_info["dimensions"])]
            
            # Normalize features
            norm = sum(f * f for f in features) ** 0.5
            features = [f / norm for f in features]
            
            feature_vector = ImageFeatureVector(
                model=model,
                features=features,
                dimension=model_info["dimensions"],
                layer=model_info["layer"],
                preprocessing=model_info["preprocessing"],
                extraction_time_ms=random.uniform(50, 200),
                confidence=random.uniform(0.8, 1.0)
            )
            analysis.feature_vectors.append(feature_vector)
        
        # Add perceptual hashes
        if request.extract_hashes:
            for hash_type in request.hash_types:
                hash_info = self.hash_algorithms[hash_type]
                
                # Generate mock hash
                hash_value = format(random.getrandbits(hash_info["bit_length"]), 
                                  f'0{hash_info["bit_length"]//4}x')
                
                image_hash = ImageHash(
                    hash_type=hash_type,
                    hash_value=hash_value,
                    bit_length=hash_info["bit_length"],
                    normalized=True,
                    rotation_invariant=hash_info["rotation_invariant"],
                    scale_invariant=hash_info["scale_invariant"]
                )
                analysis.perceptual_hashes.append(image_hash)
        
        # Add color analysis
        if request.analyze_color:
            analysis.color_profile = ImageColorProfile(
                dominant_colors=[
                    f"#{random.randint(0, 255):02x}{random.randint(0, 255):02x}{random.randint(0, 255):02x}"
                    for _ in range(5)
                ],
                color_palette=[
                    {
                        "color": f"#{random.randint(0, 255):02x}{random.randint(0, 255):02x}{random.randint(0, 255):02x}",
                        "percentage": random.uniform(5, 30)
                    }
                    for _ in range(8)
                ],
                average_color=f"#{random.randint(0, 255):02x}{random.randint(0, 255):02x}{random.randint(0, 255):02x}",
                brightness=random.uniform(0.2, 0.9),
                contrast=random.uniform(0.3, 1.5),
                saturation=random.uniform(0.1, 0.9),
                color_space="RGB",
                histogram={
                    "red": [random.randint(0, 1000) for _ in range(256)],
                    "green": [random.randint(0, 1000) for _ in range(256)],
                    "blue": [random.randint(0, 1000) for _ in range(256)]
                }
            )
        
        # Add texture analysis
        if request.analyze_texture:
            analysis.texture = ImageTexture(
                lbp_histogram=[random.uniform(0, 1) for _ in range(256)],
                glcm_features={
                    "contrast": random.uniform(0, 100),
                    "dissimilarity": random.uniform(0, 50),
                    "homogeneity": random.uniform(0, 1),
                    "energy": random.uniform(0, 1),
                    "correlation": random.uniform(-1, 1)
                },
                entropy=random.uniform(0, 8),
                energy=random.uniform(0, 1),
                homogeneity=random.uniform(0, 1),
                contrast=random.uniform(0, 100)
            )
        
        # Add shape analysis
        if request.analyze_shape:
            analysis.shape = ImageShape(
                edges=random.randint(100, 5000),
                contours=random.randint(10, 200),
                corners=random.randint(20, 500),
                symmetry_score=random.uniform(0.1, 0.9),
                complexity_score=random.uniform(0.2, 2.0),
                roundness=random.uniform(0.1, 0.8)
            )
        
        # Add quality assessment
        if request.assess_quality:
            analysis.quality = ImageQuality(
                overall_score=random.uniform(0.3, 1.0),
                sharpness=random.uniform(0.2, 1.0),
                blur_score=random.uniform(0.0, 0.8),
                noise_level=random.uniform(0.0, 0.6),
                brightness=random.uniform(0.2, 0.9),
                contrast=random.uniform(0.3, 1.2),
                exposure=random.choice(["underexposed", "normal", "overexposed"]),
                artifacts=random.sample(["compression", "noise", "blur", "distortion"], 
                                      random.randint(0, 2))
            )
        
        # Add object detection
        if request.detect_objects:
            num_objects = random.randint(0, 8)
            analysis.detected_objects = [
                {
                    "class": random.choice(["person", "car", "building", "tree", "animal", "object"]),
                    "confidence": random.uniform(0.5, 1.0),
                    "bounding_box": {
                        "x": random.randint(0, analysis.dimensions["width"] // 2),
                        "y": random.randint(0, analysis.dimensions["height"] // 2),
                        "width": random.randint(50, analysis.dimensions["width"] // 4),
                        "height": random.randint(50, analysis.dimensions["height"] // 4)
                    }
                }
                for _ in range(num_objects)
            ]
            analysis.object_count = num_objects
        
        return analysis


def get_image_similarity_service() -> ImageSimilarityService:
    """Get Image Similarity Service instance"""
    return ImageSimilarityService()
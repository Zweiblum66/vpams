"""
Tests for Content Clustering Service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import numpy as np
import json
from datetime import datetime
from typing import List, Dict, Any

from src.services.content_clusterer import ContentClusterer, FeatureVector
from src.models.schemas import (
    ContentCluster, ContentSimilarity, ClusteringRequest, ClusteringResult,
    ClusterStatistics, ClusteringMethod
)


@pytest.fixture
def mock_db():
    """Mock database session"""
    return AsyncMock()


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    return AsyncMock()


@pytest.fixture
def content_clusterer(mock_db, mock_redis):
    """Create ContentClusterer instance with mocked dependencies"""
    return ContentClusterer(db=mock_db, redis=mock_redis)


@pytest.fixture
def sample_feature_vector():
    """Sample feature vector for testing"""
    return FeatureVector(
        asset_id="asset123",
        feature_type="visual",
        vector=np.random.rand(128).astype(np.float32),
        metadata={"width": 640, "height": 480},
        extracted_at=datetime.utcnow()
    )


class TestContentClusterer:
    """Test cases for ContentClusterer service"""

    @pytest.mark.asyncio
    async def test_initialize(self, content_clusterer):
        """Test clusterer initialization"""
        with patch.object(content_clusterer, '_load_models', new_callable=AsyncMock):
            await content_clusterer.initialize()
            assert content_clusterer._load_models.called

    @pytest.mark.asyncio
    async def test_extract_visual_features(self, content_clusterer):
        """Test visual feature extraction"""
        asset_info = {
            'file_path': '/path/to/image.jpg',
            'type': 'image/jpeg'
        }
        
        # Mock image loading and processing
        mock_image = np.ones((100, 100, 3), dtype=np.uint8) * 128
        
        with patch('cv2.imread', return_value=mock_image), \
             patch.object(content_clusterer.image_processor, 'resize_for_analysis', return_value=mock_image), \
             patch.object(content_clusterer.image_processor, 'calculate_histogram') as mock_hist, \
             patch.object(content_clusterer.image_processor, 'calculate_complexity', return_value=0.5):
            
            mock_hist.return_value = {
                'red': np.array([128] * 256),
                'green': np.array([128] * 256),
                'blue': np.array([128] * 256)
            }
            
            feature_vector = await content_clusterer._extract_visual_features('asset123', asset_info)
            
            assert feature_vector is not None
            assert feature_vector.asset_id == 'asset123'
            assert feature_vector.feature_type == 'visual'
            assert isinstance(feature_vector.vector, np.ndarray)
            assert len(feature_vector.vector) > 0

    @pytest.mark.asyncio
    async def test_extract_audio_features(self, content_clusterer):
        """Test audio feature extraction"""
        asset_info = {
            'file_path': '/path/to/audio.mp3',
            'type': 'audio/mp3'
        }
        
        # Mock audio feature extraction
        mock_features = {
            'spectral_centroid_mean': 1000.0,
            'spectral_centroid_std': 100.0,
            'spectral_rolloff_mean': 2000.0,
            'spectral_rolloff_std': 200.0,
            'spectral_bandwidth_mean': 500.0,
            'spectral_bandwidth_std': 50.0,
            'zero_crossing_rate_mean': 0.1,
            'zero_crossing_rate_std': 0.01,
            'rms_mean': 0.1,
            'rms_std': 0.01,
            'tempo': 120.0,
            'harmonic_ratio': 0.7,
            'percussive_ratio': 0.3,
            'pitch_mean': 440.0,
            'pitch_std': 50.0,
            'duration': 180.0,
            'sample_rate': 22050
        }
        
        # Add MFCC features
        for i in range(13):
            mock_features[f'mfcc_{i}_mean'] = np.random.rand()
            mock_features[f'mfcc_{i}_std'] = np.random.rand()
        
        with patch.object(content_clusterer.audio_processor, 'extract_audio_features', return_value=mock_features):
            feature_vector = await content_clusterer._extract_audio_features('asset123', asset_info)
            
            assert feature_vector is not None
            assert feature_vector.asset_id == 'asset123'
            assert feature_vector.feature_type == 'audio'
            assert isinstance(feature_vector.vector, np.ndarray)
            assert len(feature_vector.vector) > 0

    @pytest.mark.asyncio
    async def test_extract_text_features(self, content_clusterer):
        """Test text feature extraction"""
        asset_info = {
            'asset_id': 'asset123',
            'type': 'document/pdf'
        }
        
        # Mock text embedding model
        mock_embedding = np.random.rand(384).astype(np.float32)
        content_clusterer.text_embedding_model = Mock()
        content_clusterer.text_embedding_model.encode.return_value = mock_embedding
        
        # Mock text content extraction
        with patch.object(content_clusterer, '_get_asset_text_content', return_value="This is sample text content for testing"):
            feature_vector = await content_clusterer._extract_text_features('asset123', asset_info)
            
            assert feature_vector is not None
            assert feature_vector.asset_id == 'asset123'
            assert feature_vector.feature_type == 'text'
            assert isinstance(feature_vector.vector, np.ndarray)
            assert len(feature_vector.vector) == len(mock_embedding)

    @pytest.mark.asyncio
    async def test_extract_metadata_features(self, content_clusterer):
        """Test metadata feature extraction"""
        asset_info = {
            'file_size': 1024000,
            'created_at': datetime.utcnow(),
            'type': 'image/jpeg',
            'duration': 0
        }
        
        feature_vector = await content_clusterer._extract_metadata_features('asset123', asset_info)
        
        assert feature_vector is not None
        assert feature_vector.asset_id == 'asset123'
        assert feature_vector.feature_type == 'metadata'
        assert isinstance(feature_vector.vector, np.ndarray)
        assert len(feature_vector.vector) > 0

    @pytest.mark.asyncio
    async def test_combine_features(self, content_clusterer):
        """Test feature combination"""
        # Create sample features
        features = {
            'asset1': {
                'visual': FeatureVector(
                    asset_id='asset1',
                    feature_type='visual',
                    vector=np.random.rand(10).astype(np.float32),
                    metadata={},
                    extracted_at=datetime.utcnow()
                ),
                'audio': FeatureVector(
                    asset_id='asset1',
                    feature_type='audio',
                    vector=np.random.rand(15).astype(np.float32),
                    metadata={},
                    extracted_at=datetime.utcnow()
                )
            },
            'asset2': {
                'visual': FeatureVector(
                    asset_id='asset2',
                    feature_type='visual',
                    vector=np.random.rand(10).astype(np.float32),
                    metadata={},
                    extracted_at=datetime.utcnow()
                ),
                'audio': FeatureVector(
                    asset_id='asset2',
                    feature_type='audio',
                    vector=np.random.rand(15).astype(np.float32),
                    metadata={},
                    extracted_at=datetime.utcnow()
                )
            }
        }
        
        feature_types = ['visual', 'audio']
        combined_matrix = await content_clusterer._combine_features(features, feature_types)
        
        assert isinstance(combined_matrix, np.ndarray)
        assert combined_matrix.shape[0] == 2  # Two assets
        assert combined_matrix.shape[1] == 25  # 10 + 15 features

    @pytest.mark.asyncio
    async def test_cluster_dbscan(self, content_clusterer):
        """Test DBSCAN clustering"""
        # Create sample feature matrix
        feature_matrix = np.random.rand(10, 5)
        options = {'eps': 0.5, 'min_samples': 2}
        
        labels = await content_clusterer._cluster_dbscan(feature_matrix, options)
        
        assert isinstance(labels, np.ndarray)
        assert len(labels) == 10

    @pytest.mark.asyncio
    async def test_cluster_kmeans(self, content_clusterer):
        """Test K-means clustering"""
        # Create sample feature matrix
        feature_matrix = np.random.rand(10, 5)
        options = {'n_clusters': 3}
        
        labels = await content_clusterer._cluster_kmeans(feature_matrix, options)
        
        assert isinstance(labels, np.ndarray)
        assert len(labels) == 10
        assert len(set(labels)) <= 3  # Should have at most 3 clusters

    @pytest.mark.asyncio
    async def test_cluster_hierarchical(self, content_clusterer):
        """Test hierarchical clustering"""
        # Create sample feature matrix
        feature_matrix = np.random.rand(10, 5)
        options = {'n_clusters': 3}
        
        labels = await content_clusterer._cluster_hierarchical(feature_matrix, options)
        
        assert isinstance(labels, np.ndarray)
        assert len(labels) == 10
        assert len(set(labels)) <= 3  # Should have at most 3 clusters

    @pytest.mark.asyncio
    async def test_find_similar_content_with_cache(self, content_clusterer, mock_redis):
        """Test similarity search with cached results"""
        # Mock cached result
        cached_similarities = [
            {
                'asset_id': 'similar_asset1',
                'similarity_score': 0.85,
                'matching_features': ['visual', 'audio'],
                'cluster_id': 'cluster123'
            }
        ]
        mock_redis.get.return_value = json.dumps(cached_similarities)
        
        result = await content_clusterer.find_similar_content('asset123')
        
        assert len(result) == 1
        assert result[0].asset_id == 'similar_asset1'
        assert result[0].similarity_score == 0.85

    @pytest.mark.asyncio
    async def test_find_similar_content_no_cache(self, content_clusterer, mock_redis):
        """Test similarity search without cached results"""
        # Mock no cached result
        mock_redis.get.return_value = None
        mock_redis.setex = AsyncMock()
        
        # Mock feature extraction
        target_features = {
            'visual': FeatureVector(
                asset_id='asset123',
                feature_type='visual',
                vector=np.array([1.0, 0.0, 0.0]),
                metadata={},
                extracted_at=datetime.utcnow()
            )
        }
        
        other_features = {
            'similar_asset1': {
                'visual': FeatureVector(
                    asset_id='similar_asset1',
                    feature_type='visual',
                    vector=np.array([0.9, 0.1, 0.0]),  # Similar vector
                    metadata={},
                    extracted_at=datetime.utcnow()
                )
            }
        }
        
        with patch.object(content_clusterer, '_extract_features_single', return_value=target_features), \
             patch.object(content_clusterer, '_get_all_features', return_value=other_features), \
             patch.object(content_clusterer, '_get_asset_cluster', return_value='cluster123'), \
             patch.object(content_clusterer, '_store_similarity_relationships', new_callable=AsyncMock):
            
            result = await content_clusterer.find_similar_content('asset123', similarity_threshold=0.8)
            
            assert len(result) == 1
            assert result[0].asset_id == 'similar_asset1'
            assert result[0].similarity_score > 0.8

    @pytest.mark.asyncio
    async def test_cluster_content_full_workflow(self, content_clusterer):
        """Test complete clustering workflow"""
        asset_ids = ['asset1', 'asset2', 'asset3']
        
        # Mock feature extraction
        features = {}
        for asset_id in asset_ids:
            features[asset_id] = {
                'visual': FeatureVector(
                    asset_id=asset_id,
                    feature_type='visual',
                    vector=np.random.rand(10).astype(np.float32),
                    metadata={},
                    extracted_at=datetime.utcnow()
                )
            }
        
        with patch.object(content_clusterer, '_extract_features_bulk', return_value=features), \
             patch.object(content_clusterer, '_create_clusters', return_value=[]), \
             patch.object(content_clusterer, '_calculate_cluster_statistics') as mock_stats, \
             patch.object(content_clusterer, '_store_clustering_results', new_callable=AsyncMock), \
             patch.object(content_clusterer, '_cache_clustering_results', new_callable=AsyncMock):
            
            mock_stats.return_value = ClusterStatistics(
                total_assets=3,
                total_clusters=2,
                largest_cluster_size=2,
                smallest_cluster_size=1,
                average_cluster_size=1.5,
                silhouette_score=0.6
            )
            
            result = await content_clusterer.cluster_content(
                asset_ids=asset_ids,
                clustering_method=ClusteringMethod.KMEANS
            )
            
            assert isinstance(result, ClusteringResult)
            assert result.statistics.total_assets == 3
            assert result.method == ClusteringMethod.KMEANS

    @pytest.mark.asyncio
    async def test_error_handling(self, content_clusterer):
        """Test error handling in clusterer"""
        # Test with invalid file path
        asset_info = {
            'file_path': '/invalid/path',
            'type': 'image/jpeg'
        }
        
        with patch('cv2.imread', return_value=None):
            feature_vector = await content_clusterer._extract_visual_features('asset123', asset_info)
            assert feature_vector is None

        # Test with exception in feature extraction
        with patch('cv2.imread', side_effect=Exception("File error")):
            feature_vector = await content_clusterer._extract_visual_features('asset123', asset_info)
            assert feature_vector is None

    def test_combine_feature_vectors(self, content_clusterer):
        """Test combining feature vectors for similarity calculation"""
        features = {
            'visual': FeatureVector(
                asset_id='asset123',
                feature_type='visual',
                vector=np.array([1.0, 2.0, 3.0]),
                metadata={},
                extracted_at=datetime.utcnow()
            ),
            'audio': FeatureVector(
                asset_id='asset123',
                feature_type='audio',
                vector=np.array([4.0, 5.0]),
                metadata={},
                extracted_at=datetime.utcnow()
            )
        }
        
        combined = content_clusterer._combine_feature_vectors(features, ['visual', 'audio'])
        
        expected = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        np.testing.assert_array_equal(combined, expected)

    @pytest.mark.asyncio
    async def test_get_cluster_recommendations_no_history(self, content_clusterer):
        """Test cluster recommendations with no user history"""
        with patch.object(content_clusterer, '_get_user_cluster_preferences', return_value={}), \
             patch.object(content_clusterer, '_get_popular_cluster_content', return_value=['asset1', 'asset2']):
            
            recommendations = await content_clusterer.get_cluster_recommendations('user123')
            
            assert len(recommendations) == 2
            assert 'asset1' in recommendations
            assert 'asset2' in recommendations

    @pytest.mark.asyncio
    async def test_get_cluster_recommendations_with_history(self, content_clusterer):
        """Test cluster recommendations with user history"""
        user_clusters = {
            'cluster1': 0.7,
            'cluster2': 0.3
        }
        
        with patch.object(content_clusterer, '_get_user_cluster_preferences', return_value=user_clusters), \
             patch.object(content_clusterer, '_get_cluster_content', side_effect=[
                 ['asset1', 'asset2'],  # cluster1 content
                 ['asset3']             # cluster2 content
             ]):
            
            recommendations = await content_clusterer.get_cluster_recommendations('user123', max_recommendations=10)
            
            assert len(recommendations) == 3
            assert 'asset1' in recommendations
            assert 'asset2' in recommendations
            assert 'asset3' in recommendations

    @pytest.mark.asyncio
    async def test_update_clusters_incremental(self, content_clusterer):
        """Test incremental cluster updates"""
        new_asset_ids = ['new_asset1', 'new_asset2']
        
        # Mock feature extraction for new assets
        new_features = {
            'new_asset1': {
                'visual': FeatureVector(
                    asset_id='new_asset1',
                    feature_type='visual',
                    vector=np.random.rand(10).astype(np.float32),
                    metadata={},
                    extracted_at=datetime.utcnow()
                )
            }
        }
        
        with patch.object(content_clusterer, '_extract_features_bulk', return_value=new_features), \
             patch.object(content_clusterer, '_get_existing_clusters', return_value=[]), \
             patch.object(content_clusterer, '_find_best_cluster', return_value=None), \
             patch.object(content_clusterer, '_create_single_asset_cluster', new_callable=AsyncMock), \
             patch.object(content_clusterer, '_update_cluster_statistics', new_callable=AsyncMock):
            
            await content_clusterer.update_clusters_incremental(new_asset_ids)
            
            # Verify that methods were called
            content_clusterer._extract_features_bulk.assert_called_once()
            content_clusterer._update_cluster_statistics.assert_called_once()


class TestFeatureVector:
    """Test FeatureVector dataclass"""
    
    def test_feature_vector_creation(self):
        """Test creating a FeatureVector"""
        vector = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        metadata = {'width': 640, 'height': 480}
        created_at = datetime.utcnow()
        
        feature_vector = FeatureVector(
            asset_id='asset123',
            feature_type='visual',
            vector=vector,
            metadata=metadata,
            extracted_at=created_at
        )
        
        assert feature_vector.asset_id == 'asset123'
        assert feature_vector.feature_type == 'visual'
        np.testing.assert_array_equal(feature_vector.vector, vector)
        assert feature_vector.metadata == metadata
        assert feature_vector.extracted_at == created_at


class TestContentClustererIntegration:
    """Integration tests for content clustering"""
    
    @pytest.mark.asyncio
    async def test_similarity_calculation_accuracy(self):
        """Test that similarity calculation works correctly"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        clusterer = ContentClusterer(db=mock_db, redis=mock_redis)
        
        # Create identical vectors (should have high similarity)
        vector1 = np.array([1.0, 0.0, 0.0])
        vector2 = np.array([1.0, 0.0, 0.0])
        
        features1 = {
            'visual': FeatureVector(
                asset_id='asset1',
                feature_type='visual',
                vector=vector1,
                metadata={},
                extracted_at=datetime.utcnow()
            )
        }
        
        features2 = {
            'visual': FeatureVector(
                asset_id='asset2',
                feature_type='visual',
                vector=vector2,
                metadata={},
                extracted_at=datetime.utcnow()
            )
        }
        
        combined1 = clusterer._combine_feature_vectors(features1, ['visual'])
        combined2 = clusterer._combine_feature_vectors(features2, ['visual'])
        
        # Calculate cosine similarity manually
        from sklearn.metrics.pairwise import cosine_similarity
        similarity = cosine_similarity(
            combined1.reshape(1, -1),
            combined2.reshape(1, -1)
        )[0][0]
        
        # Identical vectors should have similarity of 1.0
        assert abs(similarity - 1.0) < 0.001
        
        # Test with orthogonal vectors (should have low similarity)
        vector3 = np.array([0.0, 1.0, 0.0])
        features3 = {
            'visual': FeatureVector(
                asset_id='asset3',
                feature_type='visual',
                vector=vector3,
                metadata={},
                extracted_at=datetime.utcnow()
            )
        }
        
        combined3 = clusterer._combine_feature_vectors(features3, ['visual'])
        similarity_low = cosine_similarity(
            combined1.reshape(1, -1),
            combined3.reshape(1, -1)
        )[0][0]
        
        # Orthogonal vectors should have similarity of 0.0
        assert abs(similarity_low) < 0.001

    @pytest.mark.asyncio
    async def test_clustering_consistency(self):
        """Test that clustering produces consistent results"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        clusterer = ContentClusterer(db=mock_db, redis=mock_redis)
        
        # Create deterministic feature matrix
        np.random.seed(42)
        feature_matrix = np.random.rand(20, 10)
        
        # Run clustering multiple times with same parameters
        options = {'n_clusters': 3}
        
        labels1 = await clusterer._cluster_kmeans(feature_matrix, options)
        labels2 = await clusterer._cluster_kmeans(feature_matrix, options)
        
        # While exact labels might differ, cluster assignments should be consistent
        # Check that the same points are grouped together
        for i in range(len(labels1)):
            for j in range(i + 1, len(labels1)):
                same_cluster_1 = labels1[i] == labels1[j]
                same_cluster_2 = labels2[i] == labels2[j]
                assert same_cluster_1 == same_cluster_2
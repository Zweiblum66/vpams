"""
Test Knowledge Base Service

Tests for the persistent knowledge base and entity management functionality.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pickle
import numpy as np

from src.services.knowledge_base_service import KnowledgeBaseService
from src.core.exceptions import InferenceError, ValidationError
from src.db.knowledge_base_models import (
    KnowledgeEntity, EntityFeature, EntityDetection, AnalysisIndex,
    RetroactiveAnalysisJob
)


class TestKnowledgeBaseService:
    """Test cases for KnowledgeBaseService."""
    
    @pytest.fixture
    def model_manager(self):
        """Create mock model manager."""
        manager = Mock()
        return manager
    
    @pytest.fixture
    def service(self, model_manager):
        """Create knowledge base service instance."""
        return KnowledgeBaseService(model_manager)
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.add = Mock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session
    
    @pytest.fixture
    def sample_entity_data(self):
        """Sample entity data for testing."""
        return {
            "entity_type": "person",
            "entity_id": "john_doe",
            "entity_name": "John Doe",
            "description": "Test person entity",
            "tags": ["employee", "engineering"],
            "categories": ["staff", "technical"],
            "confidence_threshold": 0.8
        }
    
    @pytest.fixture
    def sample_features(self):
        """Sample feature data for testing."""
        return {
            "face_embedding": {
                "vector": np.random.rand(128).tolist(),
                "version": "1.0",
                "quality_score": 0.95,
                "confidence": 0.98,
                "source_asset_id": str(uuid.uuid4()),
                "source_bbox": {"x": 100, "y": 100, "width": 200, "height": 200}
            }
        }
    
    async def test_add_entity_success(self, service, mock_db_session, sample_entity_data):
        """Test successfully adding a new entity."""
        with patch('src.services.knowledge_base_service.get_db_session') as mock_get_db:
            # Setup mock
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            
            # Test
            result = await service.add_entity(
                **sample_entity_data,
                trigger_retroactive_analysis=False
            )
            
            # Assertions
            assert result["entity_type"] == "person"
            assert result["entity_id"] == "john_doe"
            assert result["entity_name"] == "John Doe"
            assert result["feature_count"] == 0
            assert result["retroactive_analysis_triggered"] is False
            
            # Verify database calls
            assert mock_db_session.add.called
            assert mock_db_session.commit.called
    
    async def test_add_entity_with_features(self, service, mock_db_session, sample_entity_data, sample_features):
        """Test adding entity with initial features."""
        with patch('src.services.knowledge_base_service.get_db_session') as mock_get_db:
            # Setup mock
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            
            # Test
            result = await service.add_entity(
                **sample_entity_data,
                features=sample_features,
                trigger_retroactive_analysis=False
            )
            
            # Assertions
            assert result["feature_count"] == 1
            
            # Verify feature was added
            add_calls = mock_db_session.add.call_args_list
            assert len(add_calls) >= 2  # Entity + feature
    
    async def test_add_entity_already_exists(self, service, mock_db_session, sample_entity_data):
        """Test adding entity that already exists."""
        with patch('src.services.knowledge_base_service.get_db_session') as mock_get_db:
            # Setup mock - entity already exists
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            mock_entity = Mock()
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_entity
            
            # Test
            with pytest.raises(ValidationError, match="already exists"):
                await service.add_entity(**sample_entity_data)
    
    async def test_add_entity_from_detection(self, service, mock_db_session):
        """Test adding entity from a detection in an asset."""
        asset_id = str(uuid.uuid4())
        detection_data = {
            "confidence": 0.95,
            "bbox": {"x": 100, "y": 100, "width": 200, "height": 200},
            "face_embedding": np.random.rand(128).tolist(),
            "asset_type": "image"
        }
        
        with patch('src.services.knowledge_base_service.get_db_session') as mock_get_db:
            # Setup mock
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            
            # Mock the add_entity method
            with patch.object(service, 'add_entity', return_value={"id": str(uuid.uuid4())}) as mock_add:
                result = await service.add_entity_from_detection(
                    asset_id=asset_id,
                    detection_data=detection_data,
                    entity_type="person",
                    entity_id="detected_person_1",
                    entity_name="Detected Person 1",
                    trigger_retroactive_analysis=False
                )
                
                # Verify add_entity was called with features
                mock_add.assert_called_once()
                call_args = mock_add.call_args[1]
                assert "features" in call_args
                assert "face_embedding" in call_args["features"]
    
    async def test_find_matches(self, service, mock_db_session):
        """Test finding matching entities based on features."""
        # Create mock entities
        mock_entity = Mock()
        mock_entity.id = uuid.uuid4()
        mock_entity.entity_type = "person"
        mock_entity.entity_id = "person_1"
        mock_entity.entity_name = "Person 1"
        mock_entity.confidence_threshold = 0.7
        mock_entity.description = "Test person"
        mock_entity.tags = ["test"]
        mock_entity.categories = ["people"]
        
        # Create mock feature
        mock_feature = Mock()
        mock_feature.feature_type = "face_embedding"
        feature_vector = np.random.rand(128)
        mock_feature.feature_vector = pickle.dumps(feature_vector)
        
        with patch('src.services.knowledge_base_service.get_db_session') as mock_get_db:
            # Setup mock
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            
            # Mock entity query
            mock_entities_result = Mock()
            mock_entities_result.scalars.return_value.all.return_value = [mock_entity]
            
            # Mock features query
            mock_features_result = Mock()
            mock_features_result.scalars.return_value.all.return_value = [mock_feature]
            
            mock_db_session.execute.side_effect = [mock_entities_result, mock_features_result]
            
            # Test
            query_features = {"face_embedding": feature_vector + np.random.rand(128) * 0.1}
            matches = await service.find_matches(
                features=query_features,
                entity_type="person",
                confidence_threshold=0.5
            )
            
            # Assertions
            assert len(matches) == 1
            assert matches[0]["entity_identifier"] == "person_1"
            assert matches[0]["entity_name"] == "Person 1"
            assert matches[0]["feature_type"] == "face_embedding"
            assert 0 <= matches[0]["similarity"] <= 1
    
    async def test_find_matches_no_results(self, service, mock_db_session):
        """Test finding matches with no results."""
        with patch('src.services.knowledge_base_service.get_db_session') as mock_get_db:
            # Setup mock - no entities
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            mock_entities_result = Mock()
            mock_entities_result.scalars.return_value.all.return_value = []
            mock_db_session.execute.return_value = mock_entities_result
            
            # Test
            matches = await service.find_matches(
                features={"face_embedding": np.random.rand(128)},
                entity_type="person"
            )
            
            # Should return empty list
            assert matches == []
    
    async def test_record_detection(self, service, mock_db_session):
        """Test recording entity detections in an asset."""
        asset_id = str(uuid.uuid4())
        entity_matches = [
            {
                "entity_id": str(uuid.uuid4()),
                "confidence": 0.95,
                "bbox": {"x": 100, "y": 100, "width": 200, "height": 200},
                "start_time": 10.5,
                "end_time": 15.2
            },
            {
                "entity_id": str(uuid.uuid4()),
                "confidence": 0.87,
                "bbox": {"x": 300, "y": 200, "width": 150, "height": 150}
            }
        ]
        
        with patch('src.services.knowledge_base_service.get_db_session') as mock_get_db:
            # Setup mock
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            
            # Test
            count = await service.record_detection(
                asset_id=asset_id,
                entity_matches=entity_matches,
                detection_type="face",
                asset_type="video"
            )
            
            # Assertions
            assert count == 2
            assert mock_db_session.add.call_count == 2
            assert mock_db_session.commit.called
    
    async def test_get_asset_entities(self, service, mock_db_session):
        """Test getting all entities detected in an asset."""
        asset_id = str(uuid.uuid4())
        
        # Create mock detection and entity
        mock_detection = Mock()
        mock_detection.id = uuid.uuid4()
        mock_detection.confidence = 0.95
        mock_detection.bbox_x = 100
        mock_detection.bbox_y = 100
        mock_detection.bbox_width = 200
        mock_detection.bbox_height = 200
        mock_detection.start_time = 10.5
        mock_detection.end_time = 15.2
        mock_detection.is_verified = True
        mock_detection.detection_metadata = {"additional": "data"}
        
        mock_entity = Mock()
        mock_entity.entity_type = "person"
        mock_entity.entity_id = "person_1"
        mock_entity.entity_name = "Person 1"
        mock_entity.description = "Test person"
        mock_entity.tags = ["test"]
        mock_entity.categories = ["people"]
        
        with patch('src.services.knowledge_base_service.get_db_session') as mock_get_db:
            # Setup mock
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            mock_result = Mock()
            mock_result.all.return_value = [(mock_detection, mock_entity)]
            mock_db_session.execute.return_value = mock_result
            
            # Test
            result = await service.get_asset_entities(
                asset_id=asset_id,
                include_metadata=True
            )
            
            # Assertions
            assert result["asset_id"] == asset_id
            assert result["total_detections"] == 1
            assert "person" in result["entities"]
            assert len(result["entities"]["person"]) == 1
            
            person_data = result["entities"]["person"][0]
            assert person_data["entity_id"] == "person_1"
            assert person_data["entity_name"] == "Person 1"
            assert person_data["confidence"] == 0.95
            assert person_data["is_verified"] is True
            assert "bbox" in person_data
            assert "timespan" in person_data
            assert person_data["description"] == "Test person"
    
    async def test_update_analysis_index_new_asset(self, service, mock_db_session):
        """Test updating analysis index for a new asset."""
        asset_id = str(uuid.uuid4())
        
        with patch('src.services.knowledge_base_service.get_db_session') as mock_get_db:
            # Setup mock - no existing index
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            
            # Test
            await service.update_analysis_index(
                asset_id=asset_id,
                asset_type="video",
                analysis_type="faces",
                features={"face_features": [1, 2, 3]},
                asset_metadata={"path": "/path/to/video.mp4", "size": 1000000, "duration": 120.5}
            )
            
            # Verify new index was created
            add_calls = [call for call in mock_db_session.add.call_args_list]
            assert len(add_calls) == 1
            
            # Check the added object
            added_obj = add_calls[0][0][0]
            assert hasattr(added_obj, 'asset_id')
            assert hasattr(added_obj, 'faces_analyzed')
    
    async def test_update_analysis_index_existing_asset(self, service, mock_db_session):
        """Test updating analysis index for existing asset."""
        asset_id = str(uuid.uuid4())
        
        # Create mock existing index
        mock_index = Mock()
        mock_index.faces_analyzed = False
        
        with patch('src.services.knowledge_base_service.get_db_session') as mock_get_db:
            # Setup mock
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_index
            
            # Test
            await service.update_analysis_index(
                asset_id=asset_id,
                asset_type="video",
                analysis_type="faces"
            )
            
            # Verify index was updated
            assert mock_index.faces_analyzed is True
            assert mock_index.faces_analyzed_at is not None
            assert mock_db_session.commit.called
    
    async def test_calculate_similarity_cosine(self, service):
        """Test cosine similarity calculation for embeddings."""
        # Create two similar vectors
        vector1 = np.array([1, 0, 0, 1])
        vector2 = np.array([1, 0, 0, 0.8])
        
        similarity = await service._calculate_similarity(
            vector1, vector2, "face_embedding"
        )
        
        # Should be high similarity
        assert 0.9 < similarity <= 1.0
        
        # Test orthogonal vectors
        vector3 = np.array([0, 1, 0, 0])
        similarity2 = await service._calculate_similarity(
            vector1, vector3, "face_embedding"
        )
        
        # Should be low similarity
        assert similarity2 < 0.5
    
    async def test_calculate_similarity_euclidean(self, service):
        """Test Euclidean distance-based similarity."""
        vector1 = np.array([1, 2, 3])
        vector2 = np.array([1, 2, 3])
        
        # Same vectors should have similarity 1
        similarity = await service._calculate_similarity(
            vector1, vector2, "other_feature"
        )
        assert similarity == 1.0
        
        # Different vectors
        vector3 = np.array([4, 5, 6])
        similarity2 = await service._calculate_similarity(
            vector1, vector3, "other_feature"
        )
        assert 0 < similarity2 < 1
    
    async def test_trigger_retroactive_analysis(self, service, mock_db_session):
        """Test triggering retroactive analysis for a new entity."""
        entity_id = uuid.uuid4()
        
        with patch('src.services.knowledge_base_service.get_db_session') as mock_get_db:
            # Setup mock
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            
            # Test private method
            await service._trigger_retroactive_analysis(entity_id, "person")
            
            # Verify job was created
            assert mock_db_session.add.called
            added_obj = mock_db_session.add.call_args[0][0]
            assert hasattr(added_obj, 'entity_id')
            assert hasattr(added_obj, 'job_type')
            assert added_obj.job_type == "person_match"
            assert added_obj.status == "pending"
    
    async def test_get_knowledge_base_stats(self, service, mock_db_session):
        """Test getting knowledge base statistics."""
        with patch('src.services.knowledge_base_service.get_db_session') as mock_get_db:
            # Setup mock
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            
            # Mock query results
            mock_db_session.execute.side_effect = [
                # Entities by type
                Mock(all=lambda: [("person", 10), ("logo", 5), ("object", 15)]),
                # Total detections
                Mock(scalar=lambda: 150),
                # Analyzed assets
                Mock(scalar=lambda: 50),
                # Recent entities
                Mock(scalar=lambda: 3)
            ]
            
            # Test
            stats = await service.get_knowledge_base_stats()
            
            # Assertions
            assert stats["entities_by_type"] == {"person": 10, "logo": 5, "object": 15}
            assert stats["total_entities"] == 30
            assert stats["total_detections"] == 150
            assert stats["analyzed_assets"] == 50
            assert stats["recent_entities"] == 3
    
    async def test_search_entities(self, service, mock_db_session):
        """Test searching entities in the knowledge base."""
        # Create mock entities
        mock_entity1 = Mock()
        mock_entity1.id = uuid.uuid4()
        mock_entity1.entity_type = "person"
        mock_entity1.entity_id = "john_doe"
        mock_entity1.entity_name = "John Doe"
        mock_entity1.description = "Software engineer"
        mock_entity1.tags = ["employee", "engineering"]
        mock_entity1.categories = ["staff"]
        mock_entity1.created_at = datetime.utcnow()
        mock_entity1.last_matched = datetime.utcnow()
        
        with patch('src.services.knowledge_base_service.get_db_session') as mock_get_db:
            # Setup mock
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = [mock_entity1]
            mock_db_session.execute.return_value = mock_result
            
            # Test
            results = await service.search_entities(
                query="john",
                entity_types=["person"],
                tags=["employee"]
            )
            
            # Assertions
            assert len(results) == 1
            assert results[0]["entity_id"] == "john_doe"
            assert results[0]["entity_name"] == "John Doe"
            assert "created_at" in results[0]
            assert "last_matched" in results[0]
    
    async def test_search_entities_empty_query(self, service, mock_db_session):
        """Test searching with empty results."""
        with patch('src.services.knowledge_base_service.get_db_session') as mock_get_db:
            # Setup mock - no results
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = []
            mock_db_session.execute.return_value = mock_result
            
            # Test
            results = await service.search_entities(query="nonexistent")
            
            # Should return empty list
            assert results == []
    
    async def test_error_handling(self, service):
        """Test error handling in various methods."""
        # Test add_entity error
        with patch('src.services.knowledge_base_service.get_db_session') as mock_get_db:
            mock_get_db.side_effect = Exception("Database error")
            
            with pytest.raises(InferenceError, match="Failed to add entity"):
                await service.add_entity(
                    entity_type="person",
                    entity_id="test",
                    entity_name="Test"
                )
        
        # Test find_matches error
        with patch('src.services.knowledge_base_service.get_db_session') as mock_get_db:
            mock_get_db.side_effect = Exception("Search error")
            
            with pytest.raises(InferenceError, match="Failed to find matches"):
                await service.find_matches(
                    features={"test": [1, 2, 3]},
                    entity_type="person"
                )
    
    async def test_concurrent_operations(self, service, mock_db_session):
        """Test concurrent operations on the knowledge base."""
        with patch('src.services.knowledge_base_service.get_db_session') as mock_get_db:
            # Setup mock
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            
            # Run multiple concurrent operations
            tasks = []
            for i in range(5):
                tasks.append(service.add_entity(
                    entity_type="person",
                    entity_id=f"person_{i}",
                    entity_name=f"Person {i}",
                    trigger_retroactive_analysis=False
                ))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed
            assert len(results) == 5
            for result in results:
                assert isinstance(result, dict)
                assert "entity_id" in result
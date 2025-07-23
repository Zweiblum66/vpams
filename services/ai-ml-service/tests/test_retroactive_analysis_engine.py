"""
Test Retroactive Analysis Engine

Tests for retroactive analysis of archived content when new entities are added.
"""

import pytest
import asyncio
import uuid
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
import numpy as np

from src.services.retroactive_analysis_engine import RetroactiveAnalysisEngine
from src.services.knowledge_base_service import KnowledgeBaseService
from src.core.exceptions import InferenceError, ValidationError
from src.db.knowledge_base_models import (
    KnowledgeEntity, EntityFeature, EntityDetection, AnalysisIndex,
    RetroactiveAnalysisJob
)


class MockEntity:
    """Mock entity for testing."""
    def __init__(self, entity_id="test_entity", entity_type="person"):
        self.id = uuid.uuid4()
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.entity_name = "Test Entity"
        self.description = "Test description"
        self.tags = ["test"]
        self.categories = ["test_category"]
        self.confidence_threshold = 0.7
        self.is_active = True


class MockJob:
    """Mock retroactive analysis job."""
    def __init__(self, job_id=None, status="pending"):
        self.id = job_id or uuid.uuid4()
        self.entity_id = uuid.uuid4()
        self.job_type = "person_match"
        self.analysis_scope = "all"
        self.status = status
        self.total_assets = 0
        self.processed_assets = 0
        self.matches_found = 0
        self.processing_errors = 0
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None
        self.error_details = None
        self.filters = {}


class TestRetroactiveAnalysisEngine:
    """Test cases for RetroactiveAnalysisEngine."""
    
    @pytest.fixture
    def model_manager(self):
        """Create mock model manager."""
        manager = Mock()
        manager.get_model = AsyncMock()
        return manager
    
    @pytest.fixture
    def knowledge_base_service(self):
        """Create mock knowledge base service."""
        service = Mock(spec=KnowledgeBaseService)
        service.find_matches = AsyncMock()
        service.record_detection = AsyncMock()
        return service
    
    @pytest.fixture
    def engine(self, model_manager, knowledge_base_service):
        """Create retroactive analysis engine instance."""
        return RetroactiveAnalysisEngine(model_manager, knowledge_base_service)
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()
        session.rollback = AsyncMock()
        return session
    
    async def test_process_retroactive_analysis_job_success(self, engine, mock_db_session):
        """Test successful processing of retroactive analysis job."""
        job_id = str(uuid.uuid4())
        mock_job = MockJob(uuid.UUID(job_id))
        mock_entity = MockEntity()
        
        # Setup database mocks
        with patch('src.services.retroactive_analysis_engine.get_db_session') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            
            # Mock job retrieval
            mock_result = Mock()
            mock_result.first.return_value = (mock_job, mock_entity)
            mock_db_session.execute.return_value = mock_result
            
            # Mock job update
            mock_update_result = Mock()
            mock_update_result.scalar_one.return_value = mock_job
            mock_db_session.execute.side_effect = [mock_result, mock_update_result]
            
            # Mock execute retroactive analysis
            with patch.object(engine, '_execute_retroactive_analysis', new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = {
                    "matches_found": 5,
                    "processed_assets": 10,
                    "processing_errors": 0
                }
                
                result = await engine.process_retroactive_analysis_job(job_id)
                
                # Assertions
                assert result["matches_found"] == 5
                assert result["processed_assets"] == 10
                assert result["processing_errors"] == 0
                assert mock_job.status == "completed"
                assert mock_job.started_at is not None
                assert mock_job.completed_at is not None
    
    async def test_process_retroactive_analysis_job_not_found(self, engine, mock_db_session):
        """Test processing non-existent job."""
        job_id = str(uuid.uuid4())
        
        with patch('src.services.retroactive_analysis_engine.get_db_session') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            
            # Mock job not found
            mock_result = Mock()
            mock_result.first.return_value = None
            mock_db_session.execute.return_value = mock_result
            
            with pytest.raises(ValidationError, match="Job .* not found"):
                await engine.process_retroactive_analysis_job(job_id)
    
    async def test_process_retroactive_analysis_job_not_pending(self, engine, mock_db_session):
        """Test processing job that's not pending."""
        job_id = str(uuid.uuid4())
        mock_job = MockJob(uuid.UUID(job_id), status="running")
        mock_entity = MockEntity()
        
        with patch('src.services.retroactive_analysis_engine.get_db_session') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            
            # Mock job retrieval
            mock_result = Mock()
            mock_result.first.return_value = (mock_job, mock_entity)
            mock_db_session.execute.return_value = mock_result
            
            with pytest.raises(ValidationError, match="Job .* is not pending"):
                await engine.process_retroactive_analysis_job(job_id)
    
    async def test_process_retroactive_analysis_job_failure(self, engine, mock_db_session):
        """Test job processing failure."""
        job_id = str(uuid.uuid4())
        mock_job = MockJob(uuid.UUID(job_id))
        mock_entity = MockEntity()
        
        with patch('src.services.retroactive_analysis_engine.get_db_session') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            
            # Mock job retrieval
            mock_result = Mock()
            mock_result.first.return_value = (mock_job, mock_entity)
            mock_db_session.execute.return_value = mock_result
            
            # Mock execute failure
            with patch.object(engine, '_execute_retroactive_analysis', new_callable=AsyncMock) as mock_execute:
                mock_execute.side_effect = Exception("Processing failed")
                
                # Mock job update for failure
                mock_update_result = Mock()
                mock_update_result.scalar_one_or_none.return_value = mock_job
                mock_db_session.execute.side_effect = [mock_result, mock_update_result]
                
                with pytest.raises(InferenceError, match="Retroactive analysis job failed"):
                    await engine.process_retroactive_analysis_job(job_id)
                
                # Job should be marked as failed
                assert mock_job.status == "failed"
                assert mock_job.error_details is not None
    
    async def test_execute_retroactive_analysis(self, engine, mock_db_session):
        """Test executing retroactive analysis."""
        mock_job = MockJob()
        mock_entity = MockEntity()
        
        # Mock entity features
        mock_features = {
            "face_embedding": np.random.rand(128)
        }
        
        # Mock assets to analyze
        mock_assets = [
            {"asset_id": str(uuid.uuid4()), "asset_type": "image"},
            {"asset_id": str(uuid.uuid4()), "asset_type": "video"}
        ]
        
        with patch.object(engine, '_get_entity_features', new_callable=AsyncMock) as mock_get_features:
            with patch.object(engine, '_get_assets_to_analyze', new_callable=AsyncMock) as mock_get_assets:
                with patch.object(engine, '_process_asset_batch', new_callable=AsyncMock) as mock_process_batch:
                    mock_get_features.return_value = mock_features
                    mock_get_assets.return_value = mock_assets
                    mock_process_batch.return_value = {
                        "matches_found": 2,
                        "processed_assets": 2,
                        "processing_errors": 0
                    }
                    
                    with patch('src.services.retroactive_analysis_engine.get_db_session') as mock_get_db:
                        mock_get_db.return_value.__aenter__.return_value = mock_db_session
                        
                        # Mock job update
                        mock_update_result = Mock()
                        mock_update_result.scalar_one.return_value = mock_job
                        mock_db_session.execute.return_value = mock_update_result
                        
                        result = await engine._execute_retroactive_analysis(
                            mock_job, mock_entity, batch_size=10
                        )
                        
                        assert result["matches_found"] == 2
                        assert result["processed_assets"] == 2
                        assert result["processing_errors"] == 0
                        assert mock_job.total_assets == 2
    
    async def test_execute_retroactive_analysis_no_features(self, engine):
        """Test executing analysis with no entity features."""
        mock_job = MockJob()
        mock_entity = MockEntity()
        
        with patch.object(engine, '_get_entity_features', new_callable=AsyncMock) as mock_get_features:
            mock_get_features.return_value = {}
            
            with pytest.raises(ValidationError, match="No features found"):
                await engine._execute_retroactive_analysis(mock_job, mock_entity, batch_size=10)
    
    async def test_get_entity_features(self, engine, mock_db_session):
        """Test getting entity features."""
        entity_id = uuid.uuid4()
        
        # Create mock features
        mock_feature1 = Mock()
        mock_feature1.feature_type = "face_embedding"
        mock_feature1.feature_vector = b"serialized_vector"
        
        mock_feature2 = Mock()
        mock_feature2.feature_type = "voice_print"
        mock_feature2.feature_vector = b"serialized_voice"
        
        with patch('src.services.retroactive_analysis_engine.get_db_session') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = [mock_feature1, mock_feature2]
            mock_db_session.execute.return_value = mock_result
            
            # Mock pickle deserialization
            with patch('pickle.loads') as mock_pickle:
                mock_pickle.side_effect = [np.array([1, 2, 3]), np.array([4, 5, 6])]
                
                features = await engine._get_entity_features(entity_id)
                
                assert "face_embedding" in features
                assert "voice_print" in features
                assert len(features) == 2
    
    async def test_get_assets_to_analyze_all_scope(self, engine, mock_db_session):
        """Test getting all assets to analyze."""
        mock_job = MockJob()
        mock_job.analysis_scope = "all"
        mock_entity = MockEntity(entity_type="person")
        
        # Create mock analysis indices
        mock_indices = []
        for i in range(5):
            mock_index = Mock()
            mock_index.asset_id = uuid.uuid4()
            mock_index.asset_type = "video" if i % 2 == 0 else "image"
            mock_index.faces_analyzed = True
            mock_indices.append(mock_index)
        
        with patch('src.services.retroactive_analysis_engine.get_db_session') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = mock_indices
            mock_db_session.execute.return_value = mock_result
            
            assets = await engine._get_assets_to_analyze(mock_job, mock_entity)
            
            assert len(assets) == 5
            assert all("asset_id" in asset for asset in assets)
            assert all("asset_type" in asset for asset in assets)
    
    async def test_get_assets_to_analyze_recent_scope(self, engine, mock_db_session):
        """Test getting recent assets to analyze."""
        mock_job = MockJob()
        mock_job.analysis_scope = "recent"
        mock_entity = MockEntity(entity_type="object")
        
        # Create mock analysis indices
        mock_indices = []
        for i in range(3):
            mock_index = Mock()
            mock_index.asset_id = uuid.uuid4()
            mock_index.asset_type = "image"
            mock_index.objects_analyzed = True
            mock_indices.append(mock_index)
        
        with patch('src.services.retroactive_analysis_engine.get_db_session') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = mock_indices
            mock_db_session.execute.return_value = mock_result
            
            assets = await engine._get_assets_to_analyze(mock_job, mock_entity)
            
            assert len(assets) == 3
    
    async def test_process_asset_batch(self, engine, knowledge_base_service):
        """Test processing a batch of assets."""
        mock_entity = MockEntity()
        entity_features = {"face_embedding": np.random.rand(128)}
        
        assets = [
            {"asset_id": str(uuid.uuid4()), "asset_type": "image"},
            {"asset_id": str(uuid.uuid4()), "asset_type": "video"}
        ]
        
        # Mock matches
        knowledge_base_service.find_matches.side_effect = [
            [{"entity_id": mock_entity.id, "confidence": 0.9}],  # Match for first asset
            []  # No match for second asset
        ]
        
        knowledge_base_service.record_detection.return_value = 1
        
        result = await engine._process_asset_batch(
            assets, mock_entity, entity_features, "person_match"
        )
        
        assert result["processed_assets"] == 2
        assert result["matches_found"] == 1
        assert result["processing_errors"] == 0
        
        # Verify knowledge base methods were called
        assert knowledge_base_service.find_matches.call_count == 2
        assert knowledge_base_service.record_detection.call_count == 1
    
    async def test_process_asset_batch_with_errors(self, engine, knowledge_base_service):
        """Test processing batch with errors."""
        mock_entity = MockEntity()
        entity_features = {"face_embedding": np.random.rand(128)}
        
        assets = [
            {"asset_id": str(uuid.uuid4()), "asset_type": "image"},
            {"asset_id": str(uuid.uuid4()), "asset_type": "video"}
        ]
        
        # Mock error for first asset
        knowledge_base_service.find_matches.side_effect = [
            Exception("Processing error"),
            [{"entity_id": mock_entity.id, "confidence": 0.9}]
        ]
        
        knowledge_base_service.record_detection.return_value = 1
        
        result = await engine._process_asset_batch(
            assets, mock_entity, entity_features, "person_match"
        )
        
        assert result["processed_assets"] == 2
        assert result["matches_found"] == 1
        assert result["processing_errors"] == 1
    
    async def test_get_job_status(self, engine, mock_db_session):
        """Test getting job status."""
        job_id = str(uuid.uuid4())
        mock_job = MockJob(uuid.UUID(job_id), status="running")
        mock_job.total_assets = 100
        mock_job.processed_assets = 50
        mock_job.matches_found = 10
        
        with patch('src.services.retroactive_analysis_engine.get_db_session') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = mock_job
            mock_db_session.execute.return_value = mock_result
            
            status = await engine.get_job_status(job_id)
            
            assert status["status"] == "running"
            assert status["total_assets"] == 100
            assert status["processed_assets"] == 50
            assert status["matches_found"] == 10
            assert status["progress_percentage"] == 50.0
    
    async def test_get_job_status_not_found(self, engine, mock_db_session):
        """Test getting status for non-existent job."""
        job_id = str(uuid.uuid4())
        
        with patch('src.services.retroactive_analysis_engine.get_db_session') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db_session.execute.return_value = mock_result
            
            status = await engine.get_job_status(job_id)
            
            assert status is None
    
    async def test_cancel_job(self, engine, mock_db_session):
        """Test canceling a running job."""
        job_id = str(uuid.uuid4())
        mock_job = MockJob(uuid.UUID(job_id), status="running")
        
        # Add to running jobs
        engine._running_jobs[job_id] = {
            "job": mock_job,
            "entity": MockEntity(),
            "start_time": time.time()
        }
        
        with patch('src.services.retroactive_analysis_engine.get_db_session') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = mock_job
            mock_db_session.execute.return_value = mock_result
            
            result = await engine.cancel_job(job_id)
            
            assert result is True
            assert mock_job.status == "cancelled"
            assert job_id not in engine._running_jobs
    
    async def test_list_jobs(self, engine, mock_db_session):
        """Test listing retroactive analysis jobs."""
        # Create mock jobs
        mock_jobs = []
        for i in range(3):
            job = MockJob()
            job.status = ["pending", "running", "completed"][i]
            mock_jobs.append(job)
        
        with patch('src.services.retroactive_analysis_engine.get_db_session') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = mock_jobs
            mock_db_session.execute.return_value = mock_result
            
            jobs = await engine.list_jobs(status="all")
            
            assert len(jobs) == 3
            assert jobs[0]["status"] == "pending"
            assert jobs[1]["status"] == "running"
            assert jobs[2]["status"] == "completed"
    
    async def test_concurrent_job_processing(self, engine):
        """Test handling concurrent job processing."""
        job_ids = [str(uuid.uuid4()) for _ in range(3)]
        
        # Track which jobs were processed
        processed_jobs = []
        
        async def mock_execute(job, entity, batch_size, progress_callback):
            processed_jobs.append(str(job.id))
            await asyncio.sleep(0.1)  # Simulate processing
            return {
                "matches_found": 1,
                "processed_assets": 1,
                "processing_errors": 0
            }
        
        with patch.object(engine, '_execute_retroactive_analysis', side_effect=mock_execute):
            # Process jobs concurrently
            tasks = []
            for job_id in job_ids:
                mock_job = MockJob(uuid.UUID(job_id))
                mock_entity = MockEntity()
                
                # Add to running jobs
                engine._running_jobs[job_id] = {
                    "job": mock_job,
                    "entity": mock_entity,
                    "start_time": time.time()
                }
                
                # Create task
                task = mock_execute(mock_job, mock_entity, 100, None)
                tasks.append(task)
            
            # Wait for all to complete
            await asyncio.gather(*tasks)
            
            # All jobs should be processed
            assert len(processed_jobs) == 3
            assert all(job_id in processed_jobs for job_id in job_ids)
"""
Tests for Storage Optimizer Service
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.services.storage_optimizer import StorageOptimizer
from src.models.schemas import (
    StorageMetrics, StorageRecommendation, StorageOptimizationPlan,
    StorageTier
)
from src.db.models import StorageRecommendationModel


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = Mock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    return redis


@pytest.fixture
def storage_optimizer(mock_db, mock_redis):
    """Create storage optimizer instance"""
    return StorageOptimizer(db=mock_db, redis=mock_redis)


@pytest.fixture
def sample_storage_metrics():
    """Sample storage metrics"""
    return [
        StorageMetrics(
            asset_id="asset1",
            size_bytes=1024 * 1024 * 1024,  # 1GB
            current_tier=StorageTier.HOT,
            access_frequency_weekly=10,
            last_accessed=datetime.utcnow() - timedelta(days=1),
            created_at=datetime.utcnow() - timedelta(days=30),
            age_days=30,
            cost_per_month=10.0
        ),
        StorageMetrics(
            asset_id="asset2",
            size_bytes=5 * 1024 * 1024 * 1024,  # 5GB
            current_tier=StorageTier.HOT,
            access_frequency_weekly=0.1,
            last_accessed=datetime.utcnow() - timedelta(days=90),
            created_at=datetime.utcnow() - timedelta(days=180),
            age_days=180,
            cost_per_month=50.0
        ),
        StorageMetrics(
            asset_id="asset3",
            size_bytes=10 * 1024 * 1024 * 1024,  # 10GB
            current_tier=StorageTier.WARM,
            access_frequency_weekly=0,
            last_accessed=datetime.utcnow() - timedelta(days=365),
            created_at=datetime.utcnow() - timedelta(days=400),
            age_days=400,
            cost_per_month=30.0
        )
    ]


class TestStorageOptimizer:
    """Test storage optimization functionality"""
    
    @pytest.mark.asyncio
    async def test_initialize(self, storage_optimizer):
        """Test optimizer initialization"""
        await storage_optimizer.initialize()
        
        assert storage_optimizer.tier_costs is not None
        assert storage_optimizer.tier_thresholds is not None
    
    @pytest.mark.asyncio
    async def test_analyze_storage(self, storage_optimizer, sample_storage_metrics):
        """Test storage analysis and optimization plan generation"""
        # Mock asset metrics retrieval
        storage_optimizer._get_asset_storage_metrics = AsyncMock(
            return_value=sample_storage_metrics
        )
        
        plan = await storage_optimizer.analyze_storage(min_savings_percent=10)
        
        assert isinstance(plan, StorageOptimizationPlan)
        assert plan.total_assets == 3
        assert len(plan.recommendations) > 0
        assert plan.total_cost_savings_monthly > 0
        assert plan.total_storage_to_move_gb > 0
        assert len(plan.implementation_priority) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_asset_hot_to_cold(self, storage_optimizer):
        """Test analysis recommending move from hot to cold tier"""
        metrics = StorageMetrics(
            asset_id="asset1",
            size_bytes=10 * 1024 * 1024 * 1024,  # 10GB
            current_tier=StorageTier.HOT,
            access_frequency_weekly=0,
            last_accessed=datetime.utcnow() - timedelta(days=180),
            created_at=datetime.utcnow() - timedelta(days=200),
            age_days=200,
            cost_per_month=100.0
        )
        
        recommendation = await storage_optimizer._analyze_asset(metrics)
        
        assert recommendation is not None
        assert recommendation.recommended_tier == StorageTier.COLD
        assert recommendation.estimated_cost_savings_monthly > 0
        assert recommendation.confidence_score > 0.5
        assert len(recommendation.reasoning) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_asset_no_change_needed(self, storage_optimizer):
        """Test analysis where no tier change is needed"""
        metrics = StorageMetrics(
            asset_id="asset1",
            size_bytes=1024 * 1024 * 1024,  # 1GB
            current_tier=StorageTier.HOT,
            access_frequency_weekly=50,
            last_accessed=datetime.utcnow(),
            created_at=datetime.utcnow() - timedelta(days=7),
            age_days=7,
            cost_per_month=10.0
        )
        
        recommendation = await storage_optimizer._analyze_asset(metrics)
        
        assert recommendation is None
    
    def test_determine_optimal_tier_hot(self, storage_optimizer):
        """Test optimal tier determination for frequently accessed assets"""
        metrics = StorageMetrics(
            asset_id="asset1",
            size_bytes=1024 * 1024 * 1024,
            current_tier=StorageTier.WARM,
            access_frequency_weekly=100,
            last_accessed=datetime.utcnow(),
            created_at=datetime.utcnow() - timedelta(days=1),
            age_days=1,
            cost_per_month=5.0
        )
        
        tier = storage_optimizer._determine_optimal_tier(metrics)
        assert tier == StorageTier.HOT
    
    def test_determine_optimal_tier_archive(self, storage_optimizer):
        """Test optimal tier determination for old, rarely accessed assets"""
        metrics = StorageMetrics(
            asset_id="asset1",
            size_bytes=1024 * 1024 * 1024,
            current_tier=StorageTier.HOT,
            access_frequency_weekly=0,
            last_accessed=datetime.utcnow() - timedelta(days=400),
            created_at=datetime.utcnow() - timedelta(days=500),
            age_days=500,
            cost_per_month=10.0
        )
        
        tier = storage_optimizer._determine_optimal_tier(metrics)
        assert tier == StorageTier.ARCHIVE
    
    def test_estimate_access_time_change(self, storage_optimizer):
        """Test access time change estimation"""
        # Hot to Archive
        change = storage_optimizer._estimate_access_time_change(
            StorageTier.HOT,
            StorageTier.ARCHIVE
        )
        assert change > 0  # Access time increases
        
        # Archive to Hot
        change = storage_optimizer._estimate_access_time_change(
            StorageTier.ARCHIVE,
            StorageTier.HOT
        )
        assert change < 0  # Access time decreases
        
        # Same tier
        change = storage_optimizer._estimate_access_time_change(
            StorageTier.WARM,
            StorageTier.WARM
        )
        assert change == 0
    
    def test_generate_reasoning(self, storage_optimizer):
        """Test reasoning generation for recommendations"""
        metrics = StorageMetrics(
            asset_id="asset1",
            size_bytes=1024 * 1024 * 1024,
            current_tier=StorageTier.HOT,
            access_frequency_weekly=0.5,
            last_accessed=datetime.utcnow() - timedelta(days=100),
            created_at=datetime.utcnow() - timedelta(days=150),
            age_days=150,
            cost_per_month=10.0
        )
        
        reasoning = storage_optimizer._generate_reasoning(metrics, StorageTier.COLD)
        
        assert isinstance(reasoning, str)
        assert "Low access frequency" in reasoning
        assert "150 days old" in reasoning
        assert "cold" in reasoning.lower()
    
    @pytest.mark.asyncio
    async def test_store_recommendation(self, storage_optimizer, mock_db):
        """Test storing recommendation in database"""
        recommendation = StorageRecommendation(
            asset_id="asset1",
            current_tier=StorageTier.HOT,
            recommended_tier=StorageTier.COLD,
            confidence_score=0.85,
            estimated_cost_savings_monthly=50.0,
            estimated_access_time_change_ms=5000,
            reasoning="Test reasoning",
            transition_date=datetime.utcnow().date()
        )
        
        await storage_optimizer._store_recommendation(recommendation)
        
        assert mock_db.add.called
        assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_minimum_savings_filter(self, storage_optimizer, sample_storage_metrics):
        """Test filtering recommendations by minimum savings percentage"""
        storage_optimizer._get_asset_storage_metrics = AsyncMock(
            return_value=sample_storage_metrics
        )
        
        # High threshold - should get fewer recommendations
        plan_high = await storage_optimizer.analyze_storage(min_savings_percent=50)
        
        # Low threshold - should get more recommendations
        plan_low = await storage_optimizer.analyze_storage(min_savings_percent=5)
        
        assert len(plan_low.recommendations) >= len(plan_high.recommendations)
    
    @pytest.mark.asyncio
    async def test_implementation_priority(self, storage_optimizer, sample_storage_metrics):
        """Test implementation priority ordering"""
        storage_optimizer._get_asset_storage_metrics = AsyncMock(
            return_value=sample_storage_metrics
        )
        
        plan = await storage_optimizer.analyze_storage()
        
        # Priority should be ordered by savings (highest first)
        if len(plan.recommendations) > 1:
            for i in range(1, len(plan.recommendations)):
                assert (plan.recommendations[i-1].estimated_cost_savings_monthly >= 
                       plan.recommendations[i].estimated_cost_savings_monthly)
    
    @pytest.mark.asyncio
    async def test_metrics_update(self, storage_optimizer, sample_storage_metrics):
        """Test metrics are updated after optimization"""
        storage_optimizer._get_asset_storage_metrics = AsyncMock(
            return_value=sample_storage_metrics
        )
        
        with patch('src.utils.metrics.ai_metrics') as mock_metrics:
            await storage_optimizer.analyze_storage()
            
            mock_metrics.storage_optimizations.inc.assert_called()
            mock_metrics.storage_savings_gb.set.assert_called()
            mock_metrics.cost_savings_usd.labels.assert_called()
    
    @pytest.mark.asyncio
    async def test_empty_assets(self, storage_optimizer):
        """Test handling when no assets to optimize"""
        storage_optimizer._get_asset_storage_metrics = AsyncMock(return_value=[])
        
        plan = await storage_optimizer.analyze_storage()
        
        assert plan.total_assets == 0
        assert len(plan.recommendations) == 0
        assert plan.total_cost_savings_monthly == 0
        assert plan.total_storage_to_move_gb == 0
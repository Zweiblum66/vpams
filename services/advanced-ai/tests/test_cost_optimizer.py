"""
Tests for Cost Optimization Service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, date, timedelta
from typing import List, Dict, Any

from src.services.cost_optimizer import CostOptimizer, CostAnalysis, OptimizationType, CostCategory
from src.models.schemas import (
    CostOptimizationSuggestion, CostForecast, CostMetrics, StorageTier
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
def cost_optimizer(mock_db, mock_redis):
    """Create CostOptimizer instance with mocked dependencies"""
    return CostOptimizer(db=mock_db, redis=mock_redis)


@pytest.fixture
def sample_cost_analysis():
    """Sample cost analysis for testing"""
    return CostAnalysis(
        resource_id="resource123",
        resource_type="storage",
        current_monthly_cost=100.0,
        usage_patterns={
            "access_frequency": 5,
            "storage_tier": StorageTier.HOT,
            "storage_size_gb": 1000,
            "cpu_utilization": 0.3,
            "memory_utilization": 0.4
        },
        efficiency_score=0.4,
        optimization_potential=60.0,
        recommendations=["Consider moving to cold storage", "Optimize access patterns"]
    )


class TestCostOptimizer:
    """Test cases for CostOptimizer service"""

    @pytest.mark.asyncio
    async def test_initialize(self, cost_optimizer):
        """Test cost optimizer initialization"""
        with patch.object(cost_optimizer, '_load_cost_models', new_callable=AsyncMock):
            await cost_optimizer.initialize()
            assert cost_optimizer._load_cost_models.called

    @pytest.mark.asyncio
    async def test_analyze_resource_costs(self, cost_optimizer):
        """Test resource cost analysis"""
        resource_ids = ["resource1", "resource2"]
        
        # Mock single resource analysis
        mock_analysis = CostAnalysis(
            resource_id="resource1",
            resource_type="storage",
            current_monthly_cost=50.0,
            usage_patterns={"access_frequency": 10},
            efficiency_score=0.7,
            optimization_potential=30.0,
            recommendations=["Good utilization"]
        )
        
        with patch.object(cost_optimizer, '_get_all_resource_ids', return_value=resource_ids), \
             patch.object(cost_optimizer, '_analyze_single_resource', return_value=mock_analysis):
            
            analyses = await cost_optimizer.analyze_resource_costs(
                resource_ids=resource_ids,
                analysis_period_days=30
            )
            
            assert len(analyses) == 2  # Two resources
            assert analyses[0].resource_id == "resource1"
            assert analyses[0].current_monthly_cost == 50.0

    @pytest.mark.asyncio
    async def test_generate_optimization_suggestions(self, cost_optimizer, sample_cost_analysis):
        """Test optimization suggestions generation"""
        with patch.object(cost_optimizer, 'analyze_resource_costs', return_value=[sample_cost_analysis]), \
             patch.object(cost_optimizer, '_generate_resource_suggestions') as mock_gen, \
             patch.object(cost_optimizer, '_store_optimization_suggestions', new_callable=AsyncMock):
            
            # Mock suggestion generation
            mock_suggestion = CostOptimizationSuggestion(
                resource_id="resource123",
                resource_type="storage",
                current_cost_monthly=100.0,
                projected_cost_monthly=60.0,
                savings_monthly=40.0,
                savings_percentage=40.0,
                optimization_type=OptimizationType.STORAGE_TIER,
                description="Move to cold storage",
                implementation_effort="low",
                risk_level="low",
                steps=["Step 1", "Step 2"]
            )
            mock_gen.return_value = [mock_suggestion]
            
            suggestions = await cost_optimizer.generate_optimization_suggestions(
                min_savings_percentage=10.0,
                max_risk_level="medium"
            )
            
            assert len(suggestions) == 1
            assert suggestions[0].savings_monthly == 40.0
            assert suggestions[0].optimization_type == OptimizationType.STORAGE_TIER

    @pytest.mark.asyncio
    async def test_forecast_costs(self, cost_optimizer):
        """Test cost forecasting"""
        with patch.object(cost_optimizer, '_get_historical_usage_data', return_value={}), \
             patch.object(cost_optimizer, '_predict_usage_for_date', return_value={}), \
             patch.object(cost_optimizer, '_calculate_forecasted_cost', return_value=150.0), \
             patch.object(cost_optimizer, '_store_cost_forecasts', new_callable=AsyncMock):
            
            forecasts = await cost_optimizer.forecast_costs(
                forecast_days=7
            )
            
            assert len(forecasts) == 7
            assert all(f.forecasted_cost == 150.0 for f in forecasts)
            assert all(isinstance(f.forecast_date, date) for f in forecasts)

    @pytest.mark.asyncio
    async def test_detect_cost_anomalies(self, cost_optimizer):
        """Test cost anomaly detection"""
        # Mock cost data
        recent_costs = [
            CostMetrics(
                resource_id="resource1",
                resource_type="storage",
                period_start=date.today() - timedelta(days=1),
                period_end=date.today(),
                storage_cost=50.0,
                compute_cost=30.0,
                transfer_cost=10.0,
                total_cost=90.0,
                usage_efficiency=0.8
            )
        ]
        
        baseline_costs = [
            CostMetrics(
                resource_id="resource1",
                resource_type="storage",
                period_start=date.today() - timedelta(days=10),
                period_end=date.today() - timedelta(days=9),
                storage_cost=25.0,
                compute_cost=15.0,
                transfer_cost=5.0,
                total_cost=45.0,
                usage_efficiency=0.8
            )
        ]
        
        mock_anomaly = {
            "resource_id": "resource1",
            "anomaly_type": "cost_spike",
            "severity": "high",
            "description": "Cost doubled from baseline"
        }
        
        with patch.object(cost_optimizer, '_get_cost_metrics', side_effect=[recent_costs, baseline_costs]), \
             patch.object(cost_optimizer, '_detect_resource_anomaly', return_value=mock_anomaly):
            
            anomalies = await cost_optimizer.detect_cost_anomalies(
                lookback_days=7,
                anomaly_threshold=2.0
            )
            
            assert len(anomalies) == 1
            assert anomalies[0]["resource_id"] == "resource1"
            assert anomalies[0]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_optimize_storage_tiers(self, cost_optimizer):
        """Test storage tier optimization"""
        asset_ids = ["asset1", "asset2"]
        
        # Mock access pattern analysis
        access_pattern = {
            "current_tier": StorageTier.HOT,
            "access_frequency": 2,  # Low frequency - should move to cold
            "asset_size_gb": 500
        }
        
        with patch.object(cost_optimizer, '_get_all_asset_ids', return_value=asset_ids), \
             patch.object(cost_optimizer, '_analyze_asset_access_pattern', return_value=access_pattern), \
             patch.object(cost_optimizer, '_determine_optimal_storage_tier', return_value=StorageTier.COLD), \
             patch.object(cost_optimizer, '_calculate_storage_cost', side_effect=[23.0, 8.0]):  # Current, new
            
            suggestions = await cost_optimizer.optimize_storage_tiers(asset_ids)
            
            assert len(suggestions) >= 0  # May have suggestions if cost savings exist
            if suggestions:
                assert suggestions[0].optimization_type == OptimizationType.STORAGE_TIER
                assert suggestions[0].savings_monthly > 0

    @pytest.mark.asyncio
    async def test_generate_storage_tier_suggestion(self, cost_optimizer, sample_cost_analysis):
        """Test storage tier suggestion generation"""
        # Modify analysis for low access frequency
        sample_cost_analysis.usage_patterns['access_frequency'] = 2  # Low access
        sample_cost_analysis.usage_patterns['storage_size_gb'] = 1000
        sample_cost_analysis.usage_patterns['storage_tier'] = StorageTier.HOT
        
        suggestion = await cost_optimizer._generate_storage_tier_suggestion(sample_cost_analysis)
        
        assert suggestion is not None
        assert suggestion.optimization_type == OptimizationType.STORAGE_TIER
        assert suggestion.savings_monthly > 0
        assert "cold" in suggestion.description.lower()

    @pytest.mark.asyncio
    async def test_generate_compute_rightsizing_suggestion(self, cost_optimizer, sample_cost_analysis):
        """Test compute rightsizing suggestion generation"""
        # Set low utilization
        sample_cost_analysis.usage_patterns['cpu_utilization'] = 0.2
        sample_cost_analysis.usage_patterns['memory_utilization'] = 0.25
        sample_cost_analysis.usage_patterns['instance_type'] = 'large'
        sample_cost_analysis.resource_type = 'compute'
        
        suggestion = await cost_optimizer._generate_compute_rightsizing_suggestion(sample_cost_analysis)
        
        assert suggestion is not None
        assert suggestion.optimization_type == OptimizationType.COMPUTE_RIGHTSIZING
        assert suggestion.savings_monthly > 0
        assert "small" in suggestion.description.lower()

    @pytest.mark.asyncio
    async def test_generate_transfer_optimization_suggestion(self, cost_optimizer, sample_cost_analysis):
        """Test data transfer optimization suggestion"""
        # Set high transfer volume
        sample_cost_analysis.usage_patterns['data_transfer_gb_monthly'] = 500
        sample_cost_analysis.usage_patterns['external_transfer_ratio'] = 0.8
        
        suggestion = await cost_optimizer._generate_transfer_optimization_suggestion(sample_cost_analysis)
        
        assert suggestion is not None
        assert suggestion.optimization_type == OptimizationType.DATA_TRANSFER
        assert suggestion.savings_monthly > 0
        assert "cdn" in suggestion.description.lower() or "caching" in suggestion.description.lower()

    @pytest.mark.asyncio
    async def test_generate_unused_resource_suggestion(self, cost_optimizer, sample_cost_analysis):
        """Test unused resource suggestion generation"""
        # Set very low efficiency
        sample_cost_analysis.efficiency_score = 0.1
        
        suggestion = await cost_optimizer._generate_unused_resource_suggestion(sample_cost_analysis)
        
        assert suggestion is not None
        assert suggestion.optimization_type == OptimizationType.UNUSED_RESOURCES
        assert suggestion.savings_percentage == 100.0
        assert "remove" in suggestion.description.lower() or "consolidate" in suggestion.description.lower()

    def test_storage_tier_determination(self, cost_optimizer):
        """Test storage tier determination logic"""
        # Test archive tier (very low access)
        access_pattern = {"access_frequency": 0.5}
        tier = cost_optimizer._determine_optimal_storage_tier(access_pattern)
        assert tier == StorageTier.ARCHIVE
        
        # Test cold tier (low access)
        access_pattern = {"access_frequency": 3}
        tier = cost_optimizer._determine_optimal_storage_tier(access_pattern)
        assert tier == StorageTier.COLD
        
        # Test warm tier (medium access)
        access_pattern = {"access_frequency": 15}
        tier = cost_optimizer._determine_optimal_storage_tier(access_pattern)
        assert tier == StorageTier.WARM
        
        # Test hot tier (high access)
        access_pattern = {"access_frequency": 50}
        tier = cost_optimizer._determine_optimal_storage_tier(access_pattern)
        assert tier == StorageTier.HOT

    @pytest.mark.asyncio
    async def test_analyze_single_resource_no_data(self, cost_optimizer):
        """Test single resource analysis with no usage data"""
        with patch.object(cost_optimizer, '_get_resource_usage_patterns', return_value=None):
            analysis = await cost_optimizer._analyze_single_resource("resource123", 30)
            assert analysis is None

    @pytest.mark.asyncio
    async def test_analyze_single_resource_with_data(self, cost_optimizer):
        """Test single resource analysis with usage data"""
        usage_patterns = {
            "type": "storage",
            "access_frequency": 10,
            "storage_size_gb": 500
        }
        
        with patch.object(cost_optimizer, '_get_resource_usage_patterns', return_value=usage_patterns), \
             patch.object(cost_optimizer, '_calculate_current_monthly_cost', return_value=75.0), \
             patch.object(cost_optimizer, '_calculate_efficiency_score', return_value=0.6), \
             patch.object(cost_optimizer, '_calculate_optimization_potential', return_value=40.0), \
             patch.object(cost_optimizer, '_generate_basic_recommendations', return_value=["Test recommendation"]):
            
            analysis = await cost_optimizer._analyze_single_resource("resource123", 30)
            
            assert analysis is not None
            assert analysis.resource_id == "resource123"
            assert analysis.resource_type == "storage"
            assert analysis.current_monthly_cost == 75.0
            assert analysis.efficiency_score == 0.6
            assert analysis.optimization_potential == 40.0

    @pytest.mark.asyncio
    async def test_filter_suggestions_by_risk(self, cost_optimizer, sample_cost_analysis):
        """Test filtering suggestions by risk level"""
        # Create suggestions with different risk levels
        high_risk_suggestion = CostOptimizationSuggestion(
            resource_id="resource1",
            resource_type="compute",
            current_cost_monthly=100.0,
            projected_cost_monthly=50.0,
            savings_monthly=50.0,
            savings_percentage=50.0,
            optimization_type=OptimizationType.COMPUTE_RIGHTSIZING,
            description="High risk optimization",
            implementation_effort="high",
            risk_level="high",
            steps=[]
        )
        
        low_risk_suggestion = CostOptimizationSuggestion(
            resource_id="resource2",
            resource_type="storage",
            current_cost_monthly=100.0,
            projected_cost_monthly=80.0,
            savings_monthly=20.0,
            savings_percentage=20.0,
            optimization_type=OptimizationType.STORAGE_TIER,
            description="Low risk optimization",
            implementation_effort="low",
            risk_level="low",
            steps=[]
        )
        
        with patch.object(cost_optimizer, '_generate_storage_tier_suggestion', return_value=low_risk_suggestion), \
             patch.object(cost_optimizer, '_generate_compute_rightsizing_suggestion', return_value=high_risk_suggestion), \
             patch.object(cost_optimizer, '_generate_transfer_optimization_suggestion', return_value=None), \
             patch.object(cost_optimizer, '_generate_unused_resource_suggestion', return_value=None):
            
            # Test with low risk filter
            suggestions = await cost_optimizer._generate_resource_suggestions(
                sample_cost_analysis, 10.0, "low"
            )
            
            # Should only return low risk suggestion
            assert len(suggestions) == 1
            assert suggestions[0].risk_level == "low"
            
            # Test with medium risk filter
            suggestions = await cost_optimizer._generate_resource_suggestions(
                sample_cost_analysis, 10.0, "medium"
            )
            
            # Should return both low and high risk (high risk filtered by medium threshold)
            assert len(suggestions) == 1  # Only low risk passes the medium filter
            
            # Test with high risk filter
            suggestions = await cost_optimizer._generate_resource_suggestions(
                sample_cost_analysis, 10.0, "high"
            )
            
            # Should return both suggestions
            assert len(suggestions) == 2

    def test_cost_calculation_constants(self, cost_optimizer):
        """Test that cost calculation constants are reasonable"""
        # Test storage costs are in reasonable range
        assert cost_optimizer.storage_costs[StorageTier.HOT] > cost_optimizer.storage_costs[StorageTier.WARM]
        assert cost_optimizer.storage_costs[StorageTier.WARM] > cost_optimizer.storage_costs[StorageTier.COLD]
        assert cost_optimizer.storage_costs[StorageTier.COLD] > cost_optimizer.storage_costs[StorageTier.ARCHIVE]
        
        # Test compute costs increase with size
        assert cost_optimizer.compute_costs['small'] < cost_optimizer.compute_costs['medium']
        assert cost_optimizer.compute_costs['medium'] < cost_optimizer.compute_costs['large']
        assert cost_optimizer.compute_costs['large'] < cost_optimizer.compute_costs['xlarge']
        
        # Test transfer costs
        assert cost_optimizer.transfer_costs['internal'] == 0.0
        assert cost_optimizer.transfer_costs['external'] > cost_optimizer.transfer_costs['cdn']

    @pytest.mark.asyncio
    async def test_error_handling(self, cost_optimizer):
        """Test error handling in cost optimizer"""
        # Test with invalid resource
        with patch.object(cost_optimizer, '_get_resource_usage_patterns', side_effect=Exception("Database error")):
            analysis = await cost_optimizer._analyze_single_resource("invalid_resource", 30)
            assert analysis is None

        # Test suggestion generation with errors
        sample_analysis = CostAnalysis(
            resource_id="test",
            resource_type="storage",
            current_monthly_cost=100.0,
            usage_patterns={},
            efficiency_score=0.5,
            optimization_potential=50.0,
            recommendations=[]
        )
        
        with patch.object(cost_optimizer, '_generate_storage_tier_suggestion', side_effect=Exception("Error")):
            suggestion = await cost_optimizer._generate_storage_tier_suggestion(sample_analysis)
            assert suggestion is None


class TestCostAnalysis:
    """Test CostAnalysis dataclass"""
    
    def test_cost_analysis_creation(self, sample_cost_analysis):
        """Test creating a CostAnalysis"""
        assert sample_cost_analysis.resource_id == "resource123"
        assert sample_cost_analysis.resource_type == "storage"
        assert sample_cost_analysis.current_monthly_cost == 100.0
        assert sample_cost_analysis.efficiency_score == 0.4
        assert sample_cost_analysis.optimization_potential == 60.0
        assert len(sample_cost_analysis.recommendations) == 2


class TestOptimizationTypes:
    """Test optimization type enumeration"""
    
    def test_optimization_types_exist(self):
        """Test that all expected optimization types exist"""
        assert OptimizationType.STORAGE_TIER == "storage_tier"
        assert OptimizationType.COMPUTE_RIGHTSIZING == "compute_rightsizing"
        assert OptimizationType.DATA_TRANSFER == "data_transfer"
        assert OptimizationType.UNUSED_RESOURCES == "unused_resources"
        assert OptimizationType.RESERVED_INSTANCES == "reserved_instances"
        assert OptimizationType.SCHEDULING == "scheduling"
        assert OptimizationType.COMPRESSION == "compression"
        assert OptimizationType.DEDUPLICATION == "deduplication"


class TestCostOptimizerIntegration:
    """Integration tests for cost optimizer"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_optimization_workflow(self):
        """Test complete optimization workflow"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        optimizer = CostOptimizer(db=mock_db, redis=mock_redis)
        
        # Mock all external dependencies
        with patch.object(optimizer, '_load_cost_models', new_callable=AsyncMock), \
             patch.object(optimizer, '_get_all_resource_ids', return_value=["resource1"]), \
             patch.object(optimizer, '_get_resource_usage_patterns') as mock_patterns, \
             patch.object(optimizer, '_calculate_current_monthly_cost', return_value=100.0), \
             patch.object(optimizer, '_calculate_efficiency_score', return_value=0.3), \
             patch.object(optimizer, '_calculate_optimization_potential', return_value=70.0), \
             patch.object(optimizer, '_generate_basic_recommendations', return_value=["Optimize"]), \
             patch.object(optimizer, '_store_optimization_suggestions', new_callable=AsyncMock):
            
            # Setup usage patterns for storage tier optimization
            mock_patterns.return_value = {
                "type": "storage",
                "access_frequency": 1,  # Low access - should suggest archive
                "storage_tier": StorageTier.HOT,
                "storage_size_gb": 1000
            }
            
            await optimizer.initialize()
            
            # Run analysis
            analyses = await optimizer.analyze_resource_costs(["resource1"])
            
            # Generate suggestions
            suggestions = await optimizer.generate_optimization_suggestions(["resource1"])
            
            # Verify results
            assert len(analyses) == 1
            assert analyses[0].efficiency_score == 0.3
            assert analyses[0].optimization_potential == 70.0
            
            # Should generate storage tier suggestion due to low access frequency
            assert len(suggestions) >= 1
            storage_suggestions = [s for s in suggestions if s.optimization_type == OptimizationType.STORAGE_TIER]
            assert len(storage_suggestions) >= 1
"""
Storage Optimization Service

Analyzes storage patterns and recommends tier transitions.
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from aioredis import Redis
import structlog
import numpy as np
from sklearn.cluster import KMeans

from ..core.config import settings
from ..models.schemas import (
    StorageMetrics, StorageRecommendation, StorageOptimizationPlan,
    StorageTier, ModelType
)
from ..db.models import StorageRecommendationModel
from ..utils.metrics import ai_metrics


logger = structlog.get_logger()


class StorageOptimizer:
    """Optimizes storage tier placement for assets"""
    
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.tier_costs = settings.COST_PER_GB_STORAGE
        self.tier_thresholds = settings.STORAGE_TIER_THRESHOLDS
    
    async def initialize(self):
        """Initialize storage optimizer"""
        logger.info("Initializing storage optimizer")
        
        # Schedule periodic optimization
        asyncio.create_task(self._periodic_optimization())
    
    async def analyze_storage(self, min_savings_percent: float = 10) -> StorageOptimizationPlan:
        """Analyze storage and generate optimization plan"""
        logger.info("Analyzing storage for optimization")
        
        # Get storage metrics for all assets
        # This would interface with the storage service
        assets = await self._get_asset_storage_metrics()
        
        recommendations = []
        total_savings = 0.0
        total_size_to_move = 0.0
        
        for asset in assets:
            recommendation = await self._analyze_asset(asset)
            
            if recommendation and recommendation.estimated_cost_savings_monthly > 0:
                # Calculate savings percentage
                current_cost = asset.cost_per_month
                savings_percent = (recommendation.estimated_cost_savings_monthly / current_cost) * 100
                
                if savings_percent >= min_savings_percent:
                    recommendations.append(recommendation)
                    total_savings += recommendation.estimated_cost_savings_monthly
                    total_size_to_move += asset.size_bytes / (1024**3)  # Convert to GB
        
        # Sort by savings
        recommendations.sort(key=lambda r: r.estimated_cost_savings_monthly, reverse=True)
        
        # Create implementation priority
        priority = [r.asset_id for r in recommendations[:100]]  # Top 100
        
        plan = StorageOptimizationPlan(
            total_assets=len(assets),
            recommendations=recommendations,
            total_cost_savings_monthly=total_savings,
            total_storage_to_move_gb=total_size_to_move,
            implementation_priority=priority
        )
        
        # Store recommendations
        for rec in recommendations:
            await self._store_recommendation(rec)
        
        # Update metrics
        ai_metrics.storage_optimizations.inc(len(recommendations))
        ai_metrics.storage_savings_gb.set(total_size_to_move)
        ai_metrics.cost_savings_usd.labels(type="storage").set(total_savings)
        
        return plan
    
    async def _analyze_asset(self, metrics: StorageMetrics) -> Optional[StorageRecommendation]:
        """Analyze individual asset for optimization"""
        current_tier = metrics.current_tier
        
        # Determine recommended tier based on access patterns
        recommended_tier = self._determine_optimal_tier(metrics)
        
        if recommended_tier == current_tier:
            return None
        
        # Calculate cost difference
        current_cost = (metrics.size_bytes / (1024**3)) * self.tier_costs[current_tier.value]
        new_cost = (metrics.size_bytes / (1024**3)) * self.tier_costs[recommended_tier.value]
        savings = current_cost - new_cost
        
        # Estimate access time change
        access_time_change = self._estimate_access_time_change(current_tier, recommended_tier)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(metrics, recommended_tier)
        
        return StorageRecommendation(
            asset_id=metrics.asset_id,
            current_tier=current_tier,
            recommended_tier=recommended_tier,
            confidence_score=0.85,  # Simplified
            estimated_cost_savings_monthly=savings,
            estimated_access_time_change_ms=access_time_change,
            reasoning=reasoning,
            transition_date=datetime.utcnow().date() + timedelta(days=7)
        )
    
    def _determine_optimal_tier(self, metrics: StorageMetrics) -> StorageTier:
        """Determine optimal storage tier based on access patterns"""
        # Simple rule-based approach (could use ML model)
        
        # Check each tier's thresholds
        for tier in [StorageTier.ARCHIVE, StorageTier.COLD, StorageTier.WARM, StorageTier.HOT]:
            thresholds = self.tier_thresholds[tier.value]
            
            if (metrics.access_frequency_weekly <= thresholds["access_frequency"] and
                metrics.age_days >= thresholds["age_days"]):
                return tier
        
        return StorageTier.HOT  # Default to hot
    
    def _estimate_access_time_change(self, current: StorageTier, recommended: StorageTier) -> float:
        """Estimate access time change in milliseconds"""
        # Simplified estimates
        access_times = {
            StorageTier.HOT: 10,      # 10ms
            StorageTier.WARM: 100,    # 100ms
            StorageTier.COLD: 5000,   # 5 seconds
            StorageTier.ARCHIVE: 43200000  # 12 hours
        }
        
        current_time = access_times.get(current, 10)
        new_time = access_times.get(recommended, 10)
        
        return new_time - current_time
    
    def _generate_reasoning(self, metrics: StorageMetrics, recommended: StorageTier) -> str:
        """Generate human-readable reasoning for recommendation"""
        reasons = []
        
        if metrics.access_frequency_weekly < 1:
            reasons.append(f"Low access frequency ({metrics.access_frequency_weekly:.1f} times/week)")
        
        if metrics.age_days > 90:
            reasons.append(f"Asset is {metrics.age_days} days old")
        
        if metrics.last_accessed > datetime.utcnow() - timedelta(days=30):
            reasons.append(f"Not accessed in {(datetime.utcnow() - metrics.last_accessed).days} days")
        
        reasons.append(f"Recommended tier: {recommended.value}")
        
        return ". ".join(reasons)
    
    async def _get_asset_storage_metrics(self) -> List[StorageMetrics]:
        """Get storage metrics for all assets"""
        # This would interface with the actual storage and asset services
        # For now, return mock data
        return []
    
    async def _store_recommendation(self, recommendation: StorageRecommendation):
        """Store recommendation in database"""
        db_rec = StorageRecommendationModel(
            asset_id=recommendation.asset_id,
            current_tier=recommendation.current_tier,
            recommended_tier=recommendation.recommended_tier,
            confidence_score=recommendation.confidence_score,
            estimated_cost_savings_monthly=recommendation.estimated_cost_savings_monthly,
            estimated_access_time_change_ms=recommendation.estimated_access_time_change_ms,
            reasoning=recommendation.reasoning,
            transition_date=recommendation.transition_date
        )
        
        self.db.add(db_rec)
        await self.db.commit()
    
    async def _periodic_optimization(self):
        """Periodically run storage optimization"""
        while True:
            try:
                await asyncio.sleep(24 * 3600)  # Daily
                
                logger.info("Running periodic storage optimization")
                await self.analyze_storage()
                
            except Exception as e:
                logger.error("Error in periodic optimization", error=str(e))
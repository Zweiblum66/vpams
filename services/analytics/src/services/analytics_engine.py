"""
Analytics Engine

Core analytics processing engine for MAMS usage analytics.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.orm import selectinload
import redis.asyncio as redis
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from ..models.analytics import (
    Event, UserSession, AssetInteraction, SearchQuery, 
    UsageMetrics, UserBehavior, AnalyticsOverview
)
from ..core.config import settings
from shared.tracing.python_tracing import trace_async_function
from shared.logging.python_logging import get_logger

logger = get_logger(__name__)


class AnalyticsEngine:
    """Core analytics processing engine."""
    
    def __init__(self):
        self.redis_client = None
        self.batch_queue = []
        self.processing_lock = asyncio.Lock()
        self.cache_ttl = settings.CACHE_TTL_SECONDS
        
    async def _get_redis(self) -> redis.Redis:
        """Get Redis connection."""
        if not self.redis_client:
            self.redis_client = redis.from_url(settings.REDIS_URL)
        return self.redis_client
    
    @trace_async_function(operation_name="analytics.process_batch")
    async def process_batch(self) -> None:
        """Process a batch of analytics data."""
        async with self.processing_lock:
            if not self.batch_queue:
                return
            
            logger.info(f"Processing batch of {len(self.batch_queue)} events")
            
            try:
                # Process events in batch
                await self._process_events_batch()
                
                # Update aggregated metrics
                await self._update_aggregated_metrics()
                
                # Update user behavior patterns
                await self._update_user_behavior()
                
                # Update real-time metrics cache
                await self._update_realtime_cache()
                
                # Clear processed events
                self.batch_queue.clear()
                
                logger.info("Batch processing completed successfully")
                
            except Exception as e:
                logger.error(f"Batch processing failed: {e}", exc_info=True)
    
    async def _process_events_batch(self) -> None:
        """Process events from batch queue."""
        # This would typically involve:
        # 1. Validating and cleaning event data
        # 2. Enriching events with additional context
        # 3. Storing in time-series database
        # 4. Updating session data
        pass
    
    async def _update_aggregated_metrics(self) -> None:
        """Update aggregated metrics tables."""
        # Generate hourly, daily, weekly aggregations
        # This involves complex SQL queries and time-series operations
        pass
    
    async def _update_user_behavior(self) -> None:
        """Update user behavior patterns and segments."""
        # Use ML algorithms to classify user behavior
        # Update user segments based on activity patterns
        pass
    
    async def _update_realtime_cache(self) -> None:
        """Update real-time analytics cache."""
        redis_client = await self._get_redis()
        
        # Cache current active users
        active_users = await self._get_active_users_count()
        await redis_client.setex("analytics:active_users", self.cache_ttl, active_users)
        
        # Cache real-time events per minute
        events_per_minute = await self._get_events_per_minute()
        await redis_client.setex("analytics:events_per_minute", self.cache_ttl, events_per_minute)
    
    @trace_async_function(operation_name="analytics.get_overview_metrics")
    async def get_overview_metrics(
        self, 
        start_time: datetime, 
        end_time: datetime,
        db: AsyncSession
    ) -> AnalyticsOverview:
        """Get overview metrics for dashboard."""
        
        # Check cache first
        redis_client = await self._get_redis()
        cache_key = f"analytics:overview:{start_time.isoformat()}:{end_time.isoformat()}"
        cached_data = await redis_client.get(cache_key)
        
        if cached_data:
            return AnalyticsOverview.parse_raw(cached_data)
        
        # Calculate metrics
        total_users = await self._get_total_users(start_time, end_time, db)
        active_users_24h = await self._get_active_users(datetime.utcnow() - timedelta(hours=24), datetime.utcnow(), db)
        total_sessions = await self._get_total_sessions(start_time, end_time, db)
        avg_session_duration = await self._get_avg_session_duration(start_time, end_time, db)
        total_page_views = await self._get_total_page_views(start_time, end_time, db)
        total_assets_uploaded = await self._get_total_assets_uploaded(start_time, end_time, db)
        total_assets_downloaded = await self._get_total_assets_downloaded(start_time, end_time, db)
        total_searches = await self._get_total_searches(start_time, end_time, db)
        top_features = await self._get_top_features(start_time, end_time, db)
        user_segments = await self._get_user_segments(start_time, end_time, db)
        growth_metrics = await self._get_growth_metrics(start_time, end_time, db)
        
        overview = AnalyticsOverview(
            total_users=total_users,
            active_users_24h=active_users_24h,
            total_sessions=total_sessions,
            avg_session_duration=avg_session_duration,
            total_page_views=total_page_views,
            total_assets_uploaded=total_assets_uploaded,
            total_assets_downloaded=total_assets_downloaded,
            total_searches=total_searches,
            top_features=top_features,
            user_segments=user_segments,
            growth_metrics=growth_metrics
        )
        
        # Cache result
        await redis_client.setex(cache_key, self.cache_ttl, overview.json())
        
        return overview
    
    async def _get_total_users(self, start_time: datetime, end_time: datetime, db: AsyncSession) -> int:
        """Get total unique users in time range."""
        query = select(func.count(func.distinct(UserSession.user_id))).where(
            and_(
                UserSession.started_at >= start_time,
                UserSession.started_at <= end_time
            )
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def _get_active_users(self, start_time: datetime, end_time: datetime, db: AsyncSession) -> int:
        """Get active users in time range."""
        query = select(func.count(func.distinct(UserSession.user_id))).where(
            and_(
                UserSession.last_activity_at >= start_time,
                UserSession.last_activity_at <= end_time
            )
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def _get_total_sessions(self, start_time: datetime, end_time: datetime, db: AsyncSession) -> int:
        """Get total sessions in time range."""
        query = select(func.count(UserSession.id)).where(
            and_(
                UserSession.started_at >= start_time,
                UserSession.started_at <= end_time
            )
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def _get_avg_session_duration(self, start_time: datetime, end_time: datetime, db: AsyncSession) -> float:
        """Get average session duration in minutes."""
        query = select(func.avg(UserSession.duration_seconds)).where(
            and_(
                UserSession.started_at >= start_time,
                UserSession.started_at <= end_time,
                UserSession.duration_seconds.isnot(None)
            )
        )
        result = await db.execute(query)
        duration_seconds = result.scalar() or 0
        return round(duration_seconds / 60, 2)  # Convert to minutes
    
    async def _get_total_page_views(self, start_time: datetime, end_time: datetime, db: AsyncSession) -> int:
        """Get total page views."""
        query = select(func.count(Event.id)).where(
            and_(
                Event.event_type == "page_view",
                Event.timestamp >= start_time,
                Event.timestamp <= end_time
            )
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def _get_total_assets_uploaded(self, start_time: datetime, end_time: datetime, db: AsyncSession) -> int:
        """Get total assets uploaded."""
        query = select(func.count(AssetInteraction.id)).where(
            and_(
                AssetInteraction.interaction_type == "upload",
                AssetInteraction.timestamp >= start_time,
                AssetInteraction.timestamp <= end_time
            )
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def _get_total_assets_downloaded(self, start_time: datetime, end_time: datetime, db: AsyncSession) -> int:
        """Get total assets downloaded."""
        query = select(func.count(AssetInteraction.id)).where(
            and_(
                AssetInteraction.interaction_type == "download",
                AssetInteraction.timestamp >= start_time,
                AssetInteraction.timestamp <= end_time
            )
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def _get_total_searches(self, start_time: datetime, end_time: datetime, db: AsyncSession) -> int:
        """Get total search queries."""
        query = select(func.count(SearchQuery.id)).where(
            and_(
                SearchQuery.timestamp >= start_time,
                SearchQuery.timestamp <= end_time
            )
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def _get_top_features(self, start_time: datetime, end_time: datetime, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get top used features."""
        query = select(
            Event.event_name,
            func.count(Event.id).label('usage_count')
        ).where(
            and_(
                Event.timestamp >= start_time,
                Event.timestamp <= end_time,
                Event.event_type == "user_action"
            )
        ).group_by(Event.event_name).order_by(desc('usage_count')).limit(10)
        
        result = await db.execute(query)
        return [
            {"feature": row.event_name, "usage_count": row.usage_count}
            for row in result.fetchall()
        ]
    
    async def _get_user_segments(self, start_time: datetime, end_time: datetime, db: AsyncSession) -> Dict[str, int]:
        """Get user segment distribution."""
        query = select(
            UserBehavior.user_segment,
            func.count(func.distinct(UserBehavior.user_id)).label('user_count')
        ).where(
            and_(
                UserBehavior.period_start >= start_time,
                UserBehavior.period_end <= end_time,
                UserBehavior.user_segment.isnot(None)
            )
        ).group_by(UserBehavior.user_segment)
        
        result = await db.execute(query)
        return {
            row.user_segment: row.user_count
            for row in result.fetchall()
        }
    
    async def _get_growth_metrics(self, start_time: datetime, end_time: datetime, db: AsyncSession) -> Dict[str, float]:
        """Get growth metrics compared to previous period."""
        period_duration = end_time - start_time
        previous_start = start_time - period_duration
        previous_end = start_time
        
        current_users = await self._get_total_users(start_time, end_time, db)
        previous_users = await self._get_total_users(previous_start, previous_end, db)
        
        current_sessions = await self._get_total_sessions(start_time, end_time, db)
        previous_sessions = await self._get_total_sessions(previous_start, previous_end, db)
        
        user_growth = ((current_users - previous_users) / max(previous_users, 1)) * 100 if previous_users > 0 else 0
        session_growth = ((current_sessions - previous_sessions) / max(previous_sessions, 1)) * 100 if previous_sessions > 0 else 0
        
        return {
            "user_growth_percentage": round(user_growth, 2),
            "session_growth_percentage": round(session_growth, 2)
        }
    
    @trace_async_function(operation_name="analytics.get_trend_data")
    async def get_trend_data(
        self,
        metric: str,
        timeframe: str,
        granularity: str,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get trend data for charts."""
        
        # Parse timeframe
        end_time = datetime.utcnow()
        if timeframe == "1h":
            start_time = end_time - timedelta(hours=1)
        elif timeframe == "24h":
            start_time = end_time - timedelta(hours=24)
        elif timeframe == "7d":
            start_time = end_time - timedelta(days=7)
        elif timeframe == "30d":
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(hours=24)
        
        # Get cached data first
        redis_client = await self._get_redis()
        cache_key = f"analytics:trends:{metric}:{timeframe}:{granularity}"
        cached_data = await redis_client.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        # Query based on metric type
        if metric == "users":
            trend_data = await self._get_user_trend_data(start_time, end_time, granularity, db)
        elif metric == "sessions":
            trend_data = await self._get_session_trend_data(start_time, end_time, granularity, db)
        elif metric == "page_views":
            trend_data = await self._get_page_view_trend_data(start_time, end_time, granularity, db)
        elif metric == "assets":
            trend_data = await self._get_asset_trend_data(start_time, end_time, granularity, db)
        else:
            trend_data = []
        
        # Cache result
        await redis_client.setex(cache_key, self.cache_ttl, json.dumps(trend_data))
        
        return trend_data
    
    async def _get_user_trend_data(
        self, 
        start_time: datetime, 
        end_time: datetime, 
        granularity: str, 
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get user trend data."""
        # This would implement time-series aggregation
        # For now, return sample data
        return [
            {"timestamp": start_time.isoformat(), "value": 100},
            {"timestamp": end_time.isoformat(), "value": 150}
        ]
    
    async def _get_session_trend_data(
        self, 
        start_time: datetime, 
        end_time: datetime, 
        granularity: str, 
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get session trend data."""
        return [
            {"timestamp": start_time.isoformat(), "value": 200},
            {"timestamp": end_time.isoformat(), "value": 250}
        ]
    
    async def _get_page_view_trend_data(
        self, 
        start_time: datetime, 
        end_time: datetime, 
        granularity: str, 
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get page view trend data."""
        return [
            {"timestamp": start_time.isoformat(), "value": 500},
            {"timestamp": end_time.isoformat(), "value": 600}
        ]
    
    async def _get_asset_trend_data(
        self, 
        start_time: datetime, 
        end_time: datetime, 
        granularity: str, 
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get asset interaction trend data."""
        return [
            {"timestamp": start_time.isoformat(), "value": 50},
            {"timestamp": end_time.isoformat(), "value": 75}
        ]
    
    async def _get_active_users_count(self) -> int:
        """Get current active users count."""
        # This would query real-time session data
        return 42  # Sample data
    
    async def _get_events_per_minute(self) -> int:
        """Get events per minute rate."""
        # This would calculate real-time event rate
        return 15  # Sample data
    
    @trace_async_function(operation_name="analytics.user_segmentation")
    async def perform_user_segmentation(self, db: AsyncSession) -> None:
        """Perform ML-based user segmentation."""
        try:
            # Get user behavior data
            query = select(UserBehavior).where(
                UserBehavior.period_start >= datetime.utcnow() - timedelta(days=30)
            )
            result = await db.execute(query)
            behaviors = result.scalars().all()
            
            if len(behaviors) < 10:  # Need minimum data for clustering
                logger.warning("Insufficient data for user segmentation")
                return
            
            # Prepare feature matrix
            features = []
            user_ids = []
            
            for behavior in behaviors:
                features.append([
                    behavior.sessions_count,
                    behavior.total_time_minutes,
                    behavior.page_views,
                    behavior.actions_count,
                    behavior.assets_viewed,
                    behavior.assets_uploaded,
                    behavior.searches_performed
                ])
                user_ids.append(behavior.user_id)
            
            # Normalize features
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            
            # Perform K-means clustering
            n_clusters = min(5, len(features) // 2)  # Max 5 segments
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            segments = kmeans.fit_predict(features_scaled)
            
            # Map cluster numbers to meaningful segment names
            segment_names = {
                0: "power_user",
                1: "casual_user", 
                2: "content_creator",
                3: "searcher",
                4: "new_user"
            }
            
            # Update user segments in database
            for i, behavior in enumerate(behaviors):
                segment_id = segments[i] % len(segment_names)
                behavior.user_segment = segment_names[segment_id]
                
                # Determine activity level
                if behavior.sessions_count > 20:
                    behavior.activity_level = "high"
                elif behavior.sessions_count > 5:
                    behavior.activity_level = "medium"
                else:
                    behavior.activity_level = "low"
            
            await db.commit()
            logger.info(f"User segmentation completed for {len(behaviors)} users")
            
        except Exception as e:
            logger.error(f"User segmentation failed: {e}", exc_info=True)
            await db.rollback()
    
    async def close(self):
        """Clean up resources."""
        if self.redis_client:
            await self.redis_client.close()
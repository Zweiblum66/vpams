"""
User Behavior Tracking Service

This service tracks and analyzes user behavior patterns to provide insights
into user engagement, feature usage, and system optimization opportunities.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
import asyncio
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
import redis.asyncio as redis
import numpy as np
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

from ..models.analytics import (
    UserSession, Event, AssetInteraction, SearchQuery, UserBehavior,
    EventType
)
from ..core.config import settings
from shared.tracing.python_tracing import trace_async_function
from shared.logging.python_logging import get_logger

logger = get_logger(__name__)


class UserSegment(str, Enum):
    """User segment types."""
    POWER_USER = "power_user"
    CASUAL_USER = "casual_user"
    CONTENT_CREATOR = "content_creator"
    SEARCHER = "searcher"
    NEW_USER = "new_user"
    INACTIVE_USER = "inactive_user"
    EXPLORER = "explorer"
    WORKFLOW_USER = "workflow_user"


class ActivityLevel(str, Enum):
    """User activity levels."""
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


@dataclass
class BehaviorPattern:
    """Represents a user behavior pattern."""
    pattern_id: str
    pattern_name: str
    description: str
    metrics: Dict[str, float]
    users_count: int
    confidence: float


@dataclass
class UserJourney:
    """Represents a user's journey through the system."""
    user_id: str
    session_id: str
    journey_steps: List[Dict[str, Any]]
    duration_minutes: float
    conversion_events: List[str]
    drop_off_point: Optional[str]


class BehaviorTracker:
    """Tracks and analyzes user behavior patterns."""
    
    def __init__(self):
        self.redis_client = None
        self.behavior_cache = {}
        self.journey_buffer = defaultdict(list)
        
    async def _get_redis(self) -> redis.Redis:
        """Get Redis connection."""
        if not self.redis_client:
            self.redis_client = redis.from_url(settings.REDIS_URL)
        return self.redis_client
    
    @trace_async_function(operation_name="behavior.track_user_action")
    async def track_user_action(
        self,
        user_id: str,
        session_id: str,
        action: str,
        context: Dict[str, Any],
        db: AsyncSession
    ) -> None:
        """Track a user action for behavior analysis."""
        try:
            # Create event record
            event = Event(
                event_type=EventType.USER_ACTION,
                event_name=action,
                category="behavior",
                user_id=user_id,
                session_id=session_id,
                properties=context,
                metadata={
                    "tracked_at": datetime.utcnow().isoformat(),
                    "source": "behavior_tracker"
                }
            )
            
            db.add(event)
            await db.commit()
            
            # Update real-time behavior cache
            await self._update_realtime_behavior(user_id, action, context)
            
            # Add to journey buffer for journey analysis
            self.journey_buffer[f"{user_id}:{session_id}"].append({
                "action": action,
                "timestamp": datetime.utcnow(),
                "context": context
            })
            
            # Process journey if buffer is large enough
            if len(self.journey_buffer[f"{user_id}:{session_id}"]) >= 10:
                await self._process_user_journey(user_id, session_id, db)
            
            logger.debug(f"Tracked user action: {action} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to track user action: {e}", exc_info=True)
    
    async def _update_realtime_behavior(
        self,
        user_id: str,
        action: str,
        context: Dict[str, Any]
    ) -> None:
        """Update real-time behavior metrics in cache."""
        redis_client = await self._get_redis()
        
        # Update action count
        await redis_client.hincrby(f"user_behavior:{user_id}", "total_actions", 1)
        await redis_client.hincrby(f"user_behavior:{user_id}", f"action:{action}", 1)
        
        # Update last activity
        await redis_client.hset(
            f"user_behavior:{user_id}",
            "last_activity",
            datetime.utcnow().isoformat()
        )
        
        # Track feature usage
        if "feature" in context:
            await redis_client.hincrby(
                f"user_behavior:{user_id}",
                f"feature:{context['feature']}",
                1
            )
        
        # Set expiration for cache cleanup
        await redis_client.expire(f"user_behavior:{user_id}", 86400 * 7)  # 7 days
    
    @trace_async_function(operation_name="behavior.analyze_user_patterns")
    async def analyze_user_patterns(self, db: AsyncSession) -> List[BehaviorPattern]:
        """Analyze user behavior patterns using machine learning."""
        try:
            # Get user behavior data for analysis
            query = select(UserBehavior).where(
                UserBehavior.period_start >= datetime.utcnow() - timedelta(days=30)
            )
            result = await db.execute(query)
            behaviors = result.scalars().all()
            
            if len(behaviors) < 20:  # Need minimum data for pattern analysis
                logger.warning("Insufficient data for pattern analysis")
                return []
            
            # Prepare feature matrix
            features = []
            user_ids = []
            
            for behavior in behaviors:
                feature_vector = [
                    behavior.sessions_count,
                    behavior.total_time_minutes,
                    behavior.page_views,
                    behavior.actions_count,
                    behavior.assets_viewed,
                    behavior.assets_uploaded,
                    behavior.assets_downloaded,
                    behavior.searches_performed,
                    behavior.workflows_created,
                    behavior.workflows_executed,
                    behavior.bounce_rate or 0,
                    behavior.avg_session_duration or 0
                ]
                features.append(feature_vector)
                user_ids.append(behavior.user_id)
            
            # Normalize features
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            
            # Apply DBSCAN clustering for pattern discovery
            dbscan = DBSCAN(eps=0.5, min_samples=5)
            cluster_labels = dbscan.fit_predict(features_scaled)
            
            # Analyze patterns
            patterns = []
            unique_labels = set(cluster_labels)
            
            for label in unique_labels:
                if label == -1:  # Noise points
                    continue
                
                # Get users in this cluster
                cluster_mask = cluster_labels == label
                cluster_features = np.array(features)[cluster_mask]
                cluster_users = np.array(user_ids)[cluster_mask]
                
                # Calculate pattern metrics
                pattern_metrics = {
                    "avg_sessions": float(np.mean(cluster_features[:, 0])),
                    "avg_time_minutes": float(np.mean(cluster_features[:, 1])),
                    "avg_page_views": float(np.mean(cluster_features[:, 2])),
                    "avg_actions": float(np.mean(cluster_features[:, 3])),
                    "avg_assets_viewed": float(np.mean(cluster_features[:, 4])),
                    "avg_uploads": float(np.mean(cluster_features[:, 5])),
                    "avg_downloads": float(np.mean(cluster_features[:, 6])),
                    "avg_searches": float(np.mean(cluster_features[:, 7]))
                }
                
                # Determine pattern characteristics
                pattern_name, description = self._classify_behavior_pattern(pattern_metrics)
                
                pattern = BehaviorPattern(
                    pattern_id=f"pattern_{label}",
                    pattern_name=pattern_name,
                    description=description,
                    metrics=pattern_metrics,
                    users_count=len(cluster_users),
                    confidence=min(len(cluster_users) / 10.0, 1.0)  # Confidence based on cluster size
                )
                
                patterns.append(pattern)
            
            logger.info(f"Discovered {len(patterns)} behavior patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}", exc_info=True)
            return []
    
    def _classify_behavior_pattern(self, metrics: Dict[str, float]) -> Tuple[str, str]:
        """Classify a behavior pattern based on metrics."""
        
        # High activity across all metrics
        if (metrics["avg_sessions"] > 20 and 
            metrics["avg_time_minutes"] > 300 and 
            metrics["avg_actions"] > 100):
            return "power_user", "Highly engaged users with frequent and long sessions"
        
        # High upload activity
        if metrics["avg_uploads"] > 10:
            return "content_creator", "Users who frequently upload and create content"
        
        # High search activity
        if metrics["avg_searches"] > 50:
            return "searcher", "Users who primarily use search functionality"
        
        # High view, low interaction
        if (metrics["avg_assets_viewed"] > 20 and 
            metrics["avg_uploads"] < 2 and 
            metrics["avg_actions"] < 20):
            return "browser", "Users who browse content but rarely interact"
        
        # Low activity overall
        if (metrics["avg_sessions"] < 5 and 
            metrics["avg_time_minutes"] < 60):
            return "casual_user", "Infrequent users with short sessions"
        
        # Balanced activity
        return "balanced_user", "Users with moderate engagement across features"
    
    @trace_async_function(operation_name="behavior.segment_users")
    async def segment_users(self, db: AsyncSession) -> Dict[UserSegment, List[str]]:
        """Segment users based on their behavior patterns."""
        try:
            # Get recent user behavior data
            query = select(UserBehavior).where(
                UserBehavior.period_start >= datetime.utcnow() - timedelta(days=30)
            )
            result = await db.execute(query)
            behaviors = result.scalars().all()
            
            segments = defaultdict(list)
            
            for behavior in behaviors:
                segment = self._determine_user_segment(behavior)
                segments[segment].append(str(behavior.user_id))
            
            logger.info(f"Segmented {len(behaviors)} users into {len(segments)} segments")
            return dict(segments)
            
        except Exception as e:
            logger.error(f"User segmentation failed: {e}", exc_info=True)
            return {}
    
    def _determine_user_segment(self, behavior: UserBehavior) -> UserSegment:
        """Determine the segment for a user based on their behavior."""
        
        # Check for power users
        if (behavior.sessions_count > 30 and 
            behavior.total_time_minutes > 600 and 
            behavior.actions_count > 200):
            return UserSegment.POWER_USER
        
        # Check for content creators
        if behavior.assets_uploaded > 20:
            return UserSegment.CONTENT_CREATOR
        
        # Check for workflow users
        if behavior.workflows_executed > 10:
            return UserSegment.WORKFLOW_USER
        
        # Check for searchers
        if behavior.searches_performed > 50:
            return UserSegment.SEARCHER
        
        # Check for explorers (high variety, moderate usage)
        if (behavior.page_views > 100 and 
            len(behavior.features_used or []) > 5):
            return UserSegment.EXPLORER
        
        # Check for new users
        if behavior.sessions_count < 5:
            return UserSegment.NEW_USER
        
        # Check for inactive users
        if (behavior.sessions_count < 2 or 
            behavior.total_time_minutes < 30):
            return UserSegment.INACTIVE_USER
        
        # Default to casual user
        return UserSegment.CASUAL_USER
    
    @trace_async_function(operation_name="behavior.analyze_user_journey")
    async def _process_user_journey(
        self,
        user_id: str,
        session_id: str,
        db: AsyncSession
    ) -> Optional[UserJourney]:
        """Process and analyze a user's journey."""
        try:
            journey_key = f"{user_id}:{session_id}"
            journey_steps = self.journey_buffer.get(journey_key, [])
            
            if len(journey_steps) < 3:  # Need minimum steps for analysis
                return None
            
            # Sort steps by timestamp
            journey_steps.sort(key=lambda x: x["timestamp"])
            
            # Calculate journey duration
            start_time = journey_steps[0]["timestamp"]
            end_time = journey_steps[-1]["timestamp"]
            duration_minutes = (end_time - start_time).total_seconds() / 60
            
            # Identify conversion events
            conversion_events = []
            for step in journey_steps:
                if step["action"] in ["asset_upload", "workflow_complete", "project_create"]:
                    conversion_events.append(step["action"])
            
            # Identify drop-off point
            drop_off_point = None
            if len(journey_steps) > 5:
                # Look for patterns indicating user confusion or frustration
                recent_actions = [step["action"] for step in journey_steps[-5:]]
                if recent_actions.count("search") > 3:
                    drop_off_point = "search_loop"
                elif recent_actions.count("page_view") > 4:
                    drop_off_point = "browsing_fatigue"
            
            journey = UserJourney(
                user_id=user_id,
                session_id=session_id,
                journey_steps=journey_steps,
                duration_minutes=duration_minutes,
                conversion_events=conversion_events,
                drop_off_point=drop_off_point
            )
            
            # Store journey analysis
            await self._store_journey_analysis(journey, db)
            
            # Clear processed steps from buffer
            self.journey_buffer[journey_key] = []
            
            return journey
            
        except Exception as e:
            logger.error(f"Journey processing failed: {e}", exc_info=True)
            return None
    
    async def _store_journey_analysis(self, journey: UserJourney, db: AsyncSession) -> None:
        """Store journey analysis results."""
        try:
            # Create event for journey completion
            event = Event(
                event_type=EventType.SYSTEM_EVENT,
                event_name="journey_analyzed",
                category="analytics",
                user_id=journey.user_id,
                session_id=journey.session_id,
                properties={
                    "duration_minutes": journey.duration_minutes,
                    "steps_count": len(journey.journey_steps),
                    "conversion_events": journey.conversion_events,
                    "drop_off_point": journey.drop_off_point
                },
                metadata={
                    "analysis_timestamp": datetime.utcnow().isoformat()
                }
            )
            
            db.add(event)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to store journey analysis: {e}", exc_info=True)
    
    @trace_async_function(operation_name="behavior.get_user_insights")
    async def get_user_insights(
        self,
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get detailed insights for a specific user."""
        try:
            # Get user behavior data
            query = select(UserBehavior).where(
                and_(
                    UserBehavior.user_id == user_id,
                    UserBehavior.period_start >= datetime.utcnow() - timedelta(days=90)
                )
            ).order_by(desc(UserBehavior.period_start))
            
            result = await db.execute(query)
            behaviors = result.scalars().all()
            
            if not behaviors:
                return {"error": "No behavior data found for user"}
            
            latest_behavior = behaviors[0]
            
            # Calculate trends
            trends = {}
            if len(behaviors) >= 2:
                previous_behavior = behaviors[1]
                trends = {
                    "sessions_trend": latest_behavior.sessions_count - previous_behavior.sessions_count,
                    "time_trend": latest_behavior.total_time_minutes - previous_behavior.total_time_minutes,
                    "activity_trend": latest_behavior.actions_count - previous_behavior.actions_count
                }
            
            # Get feature usage patterns
            feature_usage = await self._get_user_feature_usage(user_id, db)
            
            # Get recent activity
            recent_activity = await self._get_recent_user_activity(user_id, db)
            
            insights = {
                "user_id": user_id,
                "segment": latest_behavior.user_segment,
                "activity_level": latest_behavior.activity_level,
                "current_metrics": {
                    "sessions_count": latest_behavior.sessions_count,
                    "total_time_minutes": latest_behavior.total_time_minutes,
                    "actions_count": latest_behavior.actions_count,
                    "assets_viewed": latest_behavior.assets_viewed,
                    "assets_uploaded": latest_behavior.assets_uploaded,
                    "searches_performed": latest_behavior.searches_performed
                },
                "trends": trends,
                "feature_usage": feature_usage,
                "recent_activity": recent_activity,
                "recommendations": self._generate_user_recommendations(latest_behavior)
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get user insights: {e}", exc_info=True)
            return {"error": "Failed to generate insights"}
    
    async def _get_user_feature_usage(
        self,
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, int]:
        """Get feature usage statistics for a user."""
        try:
            # Query events for feature usage
            query = select(
                Event.event_name,
                func.count(Event.id).label('usage_count')
            ).where(
                and_(
                    Event.user_id == user_id,
                    Event.event_type == EventType.USER_ACTION,
                    Event.timestamp >= datetime.utcnow() - timedelta(days=30)
                )
            ).group_by(Event.event_name)
            
            result = await db.execute(query)
            feature_usage = {row.event_name: row.usage_count for row in result.fetchall()}
            
            return feature_usage
            
        except Exception as e:
            logger.error(f"Failed to get feature usage: {e}", exc_info=True)
            return {}
    
    async def _get_recent_user_activity(
        self,
        user_id: str,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get recent activity for a user."""
        try:
            query = select(Event).where(
                and_(
                    Event.user_id == user_id,
                    Event.timestamp >= datetime.utcnow() - timedelta(days=7)
                )
            ).order_by(desc(Event.timestamp)).limit(20)
            
            result = await db.execute(query)
            events = result.scalars().all()
            
            activity = []
            for event in events:
                activity.append({
                    "timestamp": event.timestamp.isoformat(),
                    "action": event.event_name,
                    "category": event.category,
                    "properties": event.properties
                })
            
            return activity
            
        except Exception as e:
            logger.error(f"Failed to get recent activity: {e}", exc_info=True)
            return []
    
    def _generate_user_recommendations(self, behavior: UserBehavior) -> List[str]:
        """Generate personalized recommendations for a user."""
        recommendations = []
        
        # Recommend based on usage patterns
        if behavior.assets_uploaded > 0 and behavior.workflows_executed == 0:
            recommendations.append("Try creating automated workflows for your uploads")
        
        if behavior.searches_performed > 20 and behavior.assets_viewed < 50:
            recommendations.append("Explore search results more thoroughly to discover relevant content")
        
        if behavior.sessions_count > 10 and behavior.avg_session_duration < 15:
            recommendations.append("Consider using keyboard shortcuts to work more efficiently")
        
        if behavior.assets_viewed > 100 and behavior.assets_uploaded < 5:
            recommendations.append("Start uploading your own content to build your library")
        
        # Recommend features based on segment
        if behavior.user_segment == UserSegment.SEARCHER:
            recommendations.append("Try using advanced search filters for more precise results")
        elif behavior.user_segment == UserSegment.CONTENT_CREATOR:
            recommendations.append("Explore batch upload tools for efficiency")
        elif behavior.user_segment == UserSegment.CASUAL_USER:
            recommendations.append("Check out our quick start guide for tips")
        
        return recommendations[:3]  # Return top 3 recommendations
    
    @trace_async_function(operation_name="behavior.get_engagement_metrics")
    async def get_engagement_metrics(self, db: AsyncSession) -> Dict[str, Any]:
        """Get overall user engagement metrics."""
        try:
            # Get current period data
            current_start = datetime.utcnow() - timedelta(days=30)
            
            # Total active users
            query = select(func.count(func.distinct(UserBehavior.user_id))).where(
                UserBehavior.period_start >= current_start
            )
            result = await db.execute(query)
            total_active_users = result.scalar() or 0
            
            # Average session duration
            query = select(func.avg(UserBehavior.avg_session_duration)).where(
                UserBehavior.period_start >= current_start
            )
            result = await db.execute(query)
            avg_session_duration = result.scalar() or 0
            
            # User segments distribution
            query = select(
                UserBehavior.user_segment,
                func.count(func.distinct(UserBehavior.user_id)).label('count')
            ).where(
                UserBehavior.period_start >= current_start
            ).group_by(UserBehavior.user_segment)
            
            result = await db.execute(query)
            segments_distribution = {
                row.user_segment: row.count 
                for row in result.fetchall() 
                if row.user_segment
            }
            
            # Feature adoption rates
            feature_adoption = await self._calculate_feature_adoption(db)
            
            # User retention metrics
            retention_metrics = await self._calculate_retention_metrics(db)
            
            metrics = {
                "total_active_users": total_active_users,
                "avg_session_duration_minutes": round(avg_session_duration, 2),
                "segments_distribution": segments_distribution,
                "feature_adoption_rates": feature_adoption,
                "retention_metrics": retention_metrics,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get engagement metrics: {e}", exc_info=True)
            return {}
    
    async def _calculate_feature_adoption(self, db: AsyncSession) -> Dict[str, float]:
        """Calculate feature adoption rates."""
        try:
            # Get total active users
            total_users_query = select(func.count(func.distinct(UserBehavior.user_id))).where(
                UserBehavior.period_start >= datetime.utcnow() - timedelta(days=30)
            )
            result = await db.execute(total_users_query)
            total_users = result.scalar() or 1
            
            # Get feature usage by users
            features = [
                "asset_upload", "asset_download", "search_query", 
                "workflow_create", "project_create", "share_asset"
            ]
            
            adoption_rates = {}
            for feature in features:
                query = select(func.count(func.distinct(Event.user_id))).where(
                    and_(
                        Event.event_name == feature,
                        Event.timestamp >= datetime.utcnow() - timedelta(days=30)
                    )
                )
                result = await db.execute(query)
                feature_users = result.scalar() or 0
                adoption_rates[feature] = round((feature_users / total_users) * 100, 2)
            
            return adoption_rates
            
        except Exception as e:
            logger.error(f"Failed to calculate feature adoption: {e}", exc_info=True)
            return {}
    
    async def _calculate_retention_metrics(self, db: AsyncSession) -> Dict[str, float]:
        """Calculate user retention metrics."""
        try:
            # 7-day retention
            week_ago = datetime.utcnow() - timedelta(days=7)
            two_weeks_ago = datetime.utcnow() - timedelta(days=14)
            
            # Users active in week 1
            week1_query = select(func.count(func.distinct(UserSession.user_id))).where(
                and_(
                    UserSession.started_at >= two_weeks_ago,
                    UserSession.started_at < week_ago
                )
            )
            result = await db.execute(week1_query)
            week1_users = result.scalar() or 1
            
            # Users from week 1 who returned in week 2
            retained_query = select(func.count(func.distinct(UserSession.user_id))).where(
                and_(
                    UserSession.started_at >= week_ago,
                    UserSession.user_id.in_(
                        select(UserSession.user_id).where(
                            and_(
                                UserSession.started_at >= two_weeks_ago,
                                UserSession.started_at < week_ago
                            )
                        )
                    )
                )
            )
            result = await db.execute(retained_query)
            retained_users = result.scalar() or 0
            
            week_retention = round((retained_users / week1_users) * 100, 2)
            
            # Similar calculation for 30-day retention
            month_ago = datetime.utcnow() - timedelta(days=30)
            two_months_ago = datetime.utcnow() - timedelta(days=60)
            
            month1_query = select(func.count(func.distinct(UserSession.user_id))).where(
                and_(
                    UserSession.started_at >= two_months_ago,
                    UserSession.started_at < month_ago
                )
            )
            result = await db.execute(month1_query)
            month1_users = result.scalar() or 1
            
            month_retained_query = select(func.count(func.distinct(UserSession.user_id))).where(
                and_(
                    UserSession.started_at >= month_ago,
                    UserSession.user_id.in_(
                        select(UserSession.user_id).where(
                            and_(
                                UserSession.started_at >= two_months_ago,
                                UserSession.started_at < month_ago
                            )
                        )
                    )
                )
            )
            result = await db.execute(month_retained_query)
            month_retained_users = result.scalar() or 0
            
            month_retention = round((month_retained_users / month1_users) * 100, 2)
            
            return {
                "week_7_retention_percent": week_retention,
                "month_30_retention_percent": month_retention
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate retention metrics: {e}", exc_info=True)
            return {"week_7_retention_percent": 0, "month_30_retention_percent": 0}
    
    async def close(self):
        """Clean up resources."""
        if self.redis_client:
            await self.redis_client.close()
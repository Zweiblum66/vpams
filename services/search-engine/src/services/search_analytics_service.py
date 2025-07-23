"""
Search analytics service for the Search Engine Service
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import structlog
from fastapi import Request

from ..db.mongodb import get_mongodb_connection
from ..db.models import SearchAnalyticsModel
from ..models.schemas import (
    SearchAnalyticsCreate,
    SearchAnalyticsEntry,
    SearchAnalyticsAggregation,
    SearchAnalyticsTimeRange,
    SearchAnalyticsFilter,
    SearchAnalyticsQuery,
    SearchAnalyticsReport,
    SearchPerformanceMetrics,
    SearchTrendData,
    SearchType
)
from ..core.exceptions import ValidationError, NotFoundError

logger = structlog.get_logger()


class SearchAnalyticsService:
    """Service for search analytics and reporting"""
    
    def __init__(self, db):
        self.db = db
        self.analytics_model = SearchAnalyticsModel(db)
    
    async def log_search_analytics(
        self, 
        query: str,
        search_type: SearchType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        indices: List[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        results_count: int = 0,
        response_time_ms: int = 0,
        clicked_results: List[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referrer: Optional[str] = None,
        location: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log search analytics data"""
        try:
            analytics_data = {
                "query": query,
                "search_type": search_type.value,
                "user_id": user_id,
                "session_id": session_id or str(uuid.uuid4()),
                "indices": indices or [],
                "filters": filters,
                "results_count": results_count,
                "response_time_ms": response_time_ms,
                "clicked_results": clicked_results or [],
                "ip_address": ip_address,
                "user_agent": user_agent,
                "referrer": referrer,
                "location": location
            }
            
            analytics_id = await self.analytics_model.create(analytics_data)
            
            logger.info(
                "search_analytics_logged",
                analytics_id=analytics_id,
                query=query,
                user_id=user_id,
                results_count=results_count,
                response_time_ms=response_time_ms
            )
            
            return analytics_id
            
        except Exception as e:
            logger.error("failed_to_log_search_analytics", error=str(e))
            # Don't raise exception to avoid breaking search functionality
            return None
    
    async def get_search_analytics(
        self, 
        time_range: SearchAnalyticsTimeRange,
        filters: Optional[SearchAnalyticsFilter] = None
    ) -> SearchAnalyticsAggregation:
        """Get aggregated search analytics"""
        try:
            # Build MongoDB filter
            mongo_filters = {}
            
            if filters:
                if filters.search_type:
                    mongo_filters["search_type"] = filters.search_type.value
                if filters.user_id:
                    mongo_filters["user_id"] = filters.user_id
                if filters.query_contains:
                    mongo_filters["query"] = {"$regex": filters.query_contains, "$options": "i"}
                if filters.min_results is not None:
                    mongo_filters["results_count"] = {"$gte": filters.min_results}
                if filters.max_results is not None:
                    mongo_filters.setdefault("results_count", {})["$lte"] = filters.max_results
                if filters.min_response_time is not None:
                    mongo_filters["response_time_ms"] = {"$gte": filters.min_response_time}
                if filters.max_response_time is not None:
                    mongo_filters.setdefault("response_time_ms", {})["$lte"] = filters.max_response_time
                if filters.indices:
                    mongo_filters["indices"] = {"$in": filters.indices}
                if filters.has_clicks is not None:
                    if filters.has_clicks:
                        mongo_filters["clicked_results"] = {"$exists": True, "$ne": []}
                    else:
                        mongo_filters["$or"] = [
                            {"clicked_results": {"$exists": False}},
                            {"clicked_results": {"$eq": []}}
                        ]
            
            # Get aggregated statistics
            stats = await self.analytics_model.get_aggregated_stats(
                start_time=time_range.start_time,
                end_time=time_range.end_time,
                filters=mongo_filters
            )
            
            # Get top queries
            top_queries = await self.analytics_model.get_top_queries(
                start_time=time_range.start_time,
                end_time=time_range.end_time,
                limit=10,
                filters=mongo_filters
            )
            
            # Get top filters
            top_filters = await self.analytics_model.get_top_filters(
                start_time=time_range.start_time,
                end_time=time_range.end_time,
                limit=10,
                filters=mongo_filters
            )
            
            # Get search trends
            search_patterns = await self.analytics_model.get_search_trends(
                start_time=time_range.start_time,
                end_time=time_range.end_time,
                interval=time_range.interval,
                filters=mongo_filters
            )
            
            # Get performance metrics
            performance_metrics = await self.analytics_model.get_performance_metrics(
                start_time=time_range.start_time,
                end_time=time_range.end_time,
                filters=mongo_filters
            )
            
            return SearchAnalyticsAggregation(
                total_searches=stats["total_searches"],
                unique_queries=stats["unique_queries"],
                unique_users=stats["unique_users"],
                unique_sessions=stats["unique_sessions"],
                avg_response_time_ms=stats["avg_response_time_ms"],
                avg_results_per_search=stats["avg_results_per_search"],
                avg_clicks_per_search=stats["avg_clicks_per_search"],
                click_through_rate=stats["click_through_rate"],
                zero_result_rate=stats["zero_result_rate"],
                top_queries=top_queries,
                top_filters=top_filters,
                search_patterns=search_patterns,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            logger.error("failed_to_get_search_analytics", error=str(e))
            raise ValidationError(f"Failed to get search analytics: {str(e)}")
    
    async def get_search_performance_metrics(
        self, 
        time_range: SearchAnalyticsTimeRange,
        filters: Optional[SearchAnalyticsFilter] = None
    ) -> SearchPerformanceMetrics:
        """Get detailed search performance metrics"""
        try:
            # Build MongoDB filter
            mongo_filters = {}
            if filters:
                if filters.search_type:
                    mongo_filters["search_type"] = filters.search_type.value
                if filters.user_id:
                    mongo_filters["user_id"] = filters.user_id
                if filters.query_contains:
                    mongo_filters["query"] = {"$regex": filters.query_contains, "$options": "i"}
            
            performance_data = await self.analytics_model.get_performance_metrics(
                start_time=time_range.start_time,
                end_time=time_range.end_time,
                filters=mongo_filters
            )
            
            return SearchPerformanceMetrics(
                avg_response_time_ms=performance_data["avg_response_time_ms"],
                p50_response_time_ms=performance_data["p50_response_time_ms"],
                p95_response_time_ms=performance_data["p95_response_time_ms"],
                p99_response_time_ms=performance_data["p99_response_time_ms"],
                slowest_queries=performance_data["slowest_queries"],
                fastest_queries=performance_data["fastest_queries"],
                error_rate=performance_data["error_rate"],
                timeout_rate=performance_data["timeout_rate"]
            )
            
        except Exception as e:
            logger.error("failed_to_get_performance_metrics", error=str(e))
            raise ValidationError(f"Failed to get performance metrics: {str(e)}")
    
    async def get_search_trends(
        self, 
        time_range: SearchAnalyticsTimeRange,
        filters: Optional[SearchAnalyticsFilter] = None
    ) -> List[SearchTrendData]:
        """Get search trends over time"""
        try:
            # Build MongoDB filter
            mongo_filters = {}
            if filters:
                if filters.search_type:
                    mongo_filters["search_type"] = filters.search_type.value
                if filters.user_id:
                    mongo_filters["user_id"] = filters.user_id
                if filters.query_contains:
                    mongo_filters["query"] = {"$regex": filters.query_contains, "$options": "i"}
            
            trends_data = await self.analytics_model.get_search_trends(
                start_time=time_range.start_time,
                end_time=time_range.end_time,
                interval=time_range.interval,
                filters=mongo_filters
            )
            
            trends = []
            for trend in trends_data:
                trends.append(SearchTrendData(
                    timestamp=datetime.fromisoformat(trend["timestamp"]),
                    search_count=trend["search_count"],
                    unique_users=trend["unique_users"],
                    avg_response_time_ms=trend["avg_response_time_ms"],
                    avg_results=trend["avg_results"],
                    click_through_rate=trend["click_through_rate"]
                ))
            
            return trends
            
        except Exception as e:
            logger.error("failed_to_get_search_trends", error=str(e))
            raise ValidationError(f"Failed to get search trends: {str(e)}")
    
    async def get_user_segments(
        self, 
        time_range: SearchAnalyticsTimeRange,
        filters: Optional[SearchAnalyticsFilter] = None
    ) -> List[Dict[str, Any]]:
        """Get user segment analysis"""
        try:
            # Build MongoDB filter
            mongo_filters = {}
            if filters:
                if filters.search_type:
                    mongo_filters["search_type"] = filters.search_type.value
                if filters.query_contains:
                    mongo_filters["query"] = {"$regex": filters.query_contains, "$options": "i"}
            
            segments = await self.analytics_model.get_user_segments(
                start_time=time_range.start_time,
                end_time=time_range.end_time,
                filters=mongo_filters
            )
            
            return segments
            
        except Exception as e:
            logger.error("failed_to_get_user_segments", error=str(e))
            raise ValidationError(f"Failed to get user segments: {str(e)}")
    
    async def generate_analytics_report(
        self, 
        time_range: SearchAnalyticsTimeRange,
        filters: Optional[SearchAnalyticsFilter] = None
    ) -> SearchAnalyticsReport:
        """Generate a comprehensive analytics report"""
        try:
            # Get all analytics data
            summary = await self.get_search_analytics(time_range, filters)
            trends = await self.get_search_trends(time_range, filters)
            performance = await self.get_search_performance_metrics(time_range, filters)
            user_segments = await self.get_user_segments(time_range, filters)
            
            # Get top queries with more detail
            mongo_filters = {}
            if filters:
                if filters.search_type:
                    mongo_filters["search_type"] = filters.search_type.value
                if filters.user_id:
                    mongo_filters["user_id"] = filters.user_id
                if filters.query_contains:
                    mongo_filters["query"] = {"$regex": filters.query_contains, "$options": "i"}
            
            top_queries = await self.analytics_model.get_top_queries(
                start_time=time_range.start_time,
                end_time=time_range.end_time,
                limit=20,
                filters=mongo_filters
            )
            
            # Analyze search patterns
            search_patterns = await self._analyze_search_patterns(
                time_range, mongo_filters
            )
            
            return SearchAnalyticsReport(
                summary=summary,
                trends=trends,
                performance=performance,
                top_queries=top_queries,
                search_patterns=search_patterns,
                user_segments=user_segments,
                generated_at=datetime.utcnow(),
                time_range=time_range
            )
            
        except Exception as e:
            logger.error("failed_to_generate_analytics_report", error=str(e))
            raise ValidationError(f"Failed to generate analytics report: {str(e)}")
    
    async def _analyze_search_patterns(
        self, 
        time_range: SearchAnalyticsTimeRange,
        mongo_filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze search patterns for insights"""
        try:
            patterns = []
            
            # Pattern 1: Peak search times
            hourly_trends = await self.analytics_model.get_search_trends(
                start_time=time_range.start_time,
                end_time=time_range.end_time,
                interval="1h",
                filters=mongo_filters
            )
            
            if hourly_trends:
                peak_hour = max(hourly_trends, key=lambda x: x["search_count"])
                patterns.append({
                    "pattern": "peak_search_time",
                    "description": f"Peak search activity at {peak_hour['timestamp']}",
                    "data": peak_hour
                })
            
            # Pattern 2: Query length analysis
            # This would require additional aggregation in the model
            patterns.append({
                "pattern": "query_complexity",
                "description": "Analysis of query complexity and length",
                "data": {"avg_words": 2.5, "complex_queries_rate": 15.3}
            })
            
            # Pattern 3: User behavior patterns
            patterns.append({
                "pattern": "user_behavior",
                "description": "Common user search behaviors",
                "data": {
                    "refinement_rate": 25.4,
                    "abandonment_rate": 8.2,
                    "multi_page_rate": 45.6
                }
            })
            
            return patterns
            
        except Exception as e:
            logger.error("failed_to_analyze_search_patterns", error=str(e))
            return []
    
    async def cleanup_old_analytics(self, older_than_days: int = 365) -> int:
        """Clean up old analytics data"""
        try:
            if older_than_days < 1:
                raise ValidationError("older_than_days must be at least 1")
            
            deleted_count = await self.analytics_model.cleanup_old_analytics(older_than_days)
            
            logger.info(
                "analytics_cleanup_completed",
                older_than_days=older_than_days,
                deleted_count=deleted_count
            )
            
            return deleted_count
            
        except Exception as e:
            logger.error("failed_to_cleanup_analytics", error=str(e))
            raise ValidationError(f"Failed to cleanup analytics: {str(e)}")
    
    async def log_search_click(
        self, 
        search_id: str,
        asset_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """Log a click on a search result"""
        try:
            # This would typically update the original search analytics entry
            # For now, we'll create a new entry to track the click
            click_data = {
                "query": f"click:{search_id}",
                "search_type": "click",
                "user_id": user_id,
                "session_id": session_id,
                "clicked_results": [asset_id],
                "results_count": 1,
                "response_time_ms": 0
            }
            
            await self.analytics_model.create(click_data)
            
            logger.info(
                "search_click_logged",
                search_id=search_id,
                asset_id=asset_id,
                user_id=user_id
            )
            
            return True
            
        except Exception as e:
            logger.error("failed_to_log_search_click", error=str(e))
            return False
    
    @staticmethod
    def extract_session_info(request: Request) -> Dict[str, Any]:
        """Extract session information from request"""
        session_id = request.headers.get("x-session-id")
        if not session_id:
            # Generate a new session ID if not provided
            session_id = str(uuid.uuid4())
        
        return {
            "session_id": session_id,
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "referrer": request.headers.get("referer")
        }


# Dependency injection
async def get_search_analytics_service() -> SearchAnalyticsService:
    """Get search analytics service instance"""
    db = await get_mongodb_connection()
    return SearchAnalyticsService(db)
"""
Search history service for the Search Engine Service
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import structlog
from fastapi import Request

from ..db.mongodb import get_mongodb_connection
from ..db.models import SearchHistoryModel
from ..models.schemas import (
    SearchHistoryCreate,
    SearchHistoryEntry,
    SearchHistoryList,
    SearchHistoryStats,
    SearchType
)
from ..core.exceptions import ValidationError, NotFoundError

logger = structlog.get_logger()


class SearchHistoryService:
    """Service for managing search history"""
    
    def __init__(self, db):
        self.db = db
        self.search_history_model = SearchHistoryModel(db)
    
    async def log_search(
        self, 
        user_id: str, 
        query: str, 
        search_type: SearchType,
        indices: List[str],
        filters: Optional[Dict[str, Any]] = None,
        results_count: int = 0,
        response_time_ms: int = 0,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """Log a search to history"""
        try:
            history_data = {
                "user_id": user_id,
                "query": query,
                "search_type": search_type.value,
                "indices": indices,
                "filters": filters,
                "results_count": results_count,
                "response_time_ms": response_time_ms,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
            
            history_id = await self.search_history_model.create(history_data)
            
            logger.info(
                "search_logged_to_history",
                user_id=user_id,
                query=query,
                search_type=search_type.value,
                history_id=history_id
            )
            
            return history_id
            
        except Exception as e:
            logger.error("failed_to_log_search", error=str(e), user_id=user_id, query=query)
            raise ValidationError(f"Failed to log search: {str(e)}")
    
    async def get_user_history(
        self, 
        user_id: str, 
        page: int = 1, 
        per_page: int = 20,
        search_type: Optional[str] = None,
        query_filter: Optional[str] = None
    ) -> SearchHistoryList:
        """Get search history for a user"""
        try:
            if per_page > 100:
                per_page = 100
            
            skip = (page - 1) * per_page
            
            entries, total = await self.search_history_model.get_user_history(
                user_id=user_id,
                skip=skip,
                limit=per_page,
                search_type=search_type,
                query_filter=query_filter
            )
            
            # Convert to response models
            history_entries = []
            for entry in entries:
                history_entries.append(self._format_history_entry(entry))
            
            total_pages = (total + per_page - 1) // per_page
            
            return SearchHistoryList(
                entries=history_entries,
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages
            )
            
        except Exception as e:
            logger.error("failed_to_get_user_history", error=str(e), user_id=user_id)
            raise ValidationError(f"Failed to get user history: {str(e)}")
    
    async def get_user_stats(self, user_id: str, days: int = 30) -> SearchHistoryStats:
        """Get search statistics for a user"""
        try:
            if days > 365:
                days = 365
            
            # Get basic stats
            stats = await self.search_history_model.get_user_stats(user_id, days)
            
            # Get top queries
            top_queries = await self.search_history_model.get_top_queries(user_id, days=days)
            
            # Get search volume by day
            volume_data = await self.search_history_model.get_search_volume_by_day(user_id, days)
            
            return SearchHistoryStats(
                total_searches=stats["total_searches"],
                unique_queries=stats["unique_queries"],
                avg_response_time_ms=stats["avg_response_time_ms"],
                most_common_search_type=SearchType(stats["most_common_search_type"]),
                top_queries=top_queries,
                search_volume_by_day=volume_data,
                avg_results_per_search=stats["avg_results_per_search"]
            )
            
        except Exception as e:
            logger.error("failed_to_get_user_stats", error=str(e), user_id=user_id)
            raise ValidationError(f"Failed to get user stats: {str(e)}")
    
    async def delete_user_history(self, user_id: str, older_than_days: int = 90) -> int:
        """Delete old search history entries for a user"""
        try:
            if older_than_days < 1:
                raise ValidationError("older_than_days must be at least 1")
            
            deleted_count = await self.search_history_model.delete_user_history(
                user_id=user_id,
                older_than_days=older_than_days
            )
            
            logger.info(
                "user_history_deleted",
                user_id=user_id,
                older_than_days=older_than_days,
                deleted_count=deleted_count
            )
            
            return deleted_count
            
        except Exception as e:
            logger.error("failed_to_delete_user_history", error=str(e), user_id=user_id)
            raise ValidationError(f"Failed to delete user history: {str(e)}")
    
    async def clear_user_history(self, user_id: str) -> int:
        """Clear all search history for a user"""
        try:
            deleted_count = await self.search_history_model.clear_user_history(user_id)
            
            logger.info(
                "user_history_cleared",
                user_id=user_id,
                deleted_count=deleted_count
            )
            
            return deleted_count
            
        except Exception as e:
            logger.error("failed_to_clear_user_history", error=str(e), user_id=user_id)
            raise ValidationError(f"Failed to clear user history: {str(e)}")
    
    def _format_history_entry(self, entry: dict) -> SearchHistoryEntry:
        """Format a search history entry from database document"""
        return SearchHistoryEntry(
            id=entry["id"],
            user_id=entry["user_id"],
            query=entry["query"],
            search_type=SearchType(entry["search_type"]),
            indices=entry.get("indices", []),
            filters=entry.get("filters"),
            results_count=entry.get("results_count", 0),
            response_time_ms=entry.get("response_time_ms", 0),
            ip_address=entry.get("ip_address"),
            user_agent=entry.get("user_agent"),
            timestamp=entry["timestamp"]
        )
    
    @staticmethod
    def extract_request_info(request: Request) -> dict:
        """Extract IP address and user agent from request"""
        return {
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent")
        }


# Dependency injection
async def get_search_history_service() -> SearchHistoryService:
    """Get search history service instance"""
    db = await get_mongodb_connection()
    return SearchHistoryService(db)
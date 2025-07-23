"""Service for API usage analytics and logging"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timedelta
import logging

from ..core.database import get_db
from ..db.models import APIUsageLog, APIAnalytics, HTTPMethodEnum, APIVersionEnum

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for managing API analytics and usage tracking"""
    
    async def log_api_usage(
        self,
        api_key_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: Optional[int] = None,
        response_size_bytes: Optional[int] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        api_version: str = "v1"
    ):
        """Log API usage for analytics"""
        
        try:
            # This would normally get a database session
            # For this example, we'll create the log entry
            
            usage_log = APIUsageLog(
                api_key_id=UUID(api_key_id),
                endpoint=endpoint,
                method=HTTPMethodEnum(method.upper()),
                api_version=APIVersionEnum(api_version),
                status_code=status_code,
                response_time_ms=response_time_ms or 0,
                response_size_bytes=response_size_bytes,
                user_agent=user_agent,
                ip_address=ip_address,
                request_id=request_id,
                request_data=request_data,
                error_message=error_message
            )
            
            # In a real implementation, we would save this to the database
            logger.info(f"API usage logged: {api_key_id} {method} {endpoint} -> {status_code}")
            
        except Exception as e:
            logger.error(f"Failed to log API usage: {e}")
    
    async def get_usage_stats(
        self,
        db: AsyncSession,
        api_key_id: Optional[UUID] = None,
        partner_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get usage statistics for API key or partner"""
        
        try:
            # Build query filters
            filters = []
            
            if api_key_id:
                filters.append(APIUsageLog.api_key_id == api_key_id)
            
            if start_date:
                filters.append(APIUsageLog.timestamp >= start_date)
            
            if end_date:
                filters.append(APIUsageLog.timestamp <= end_date)
            
            # Get basic stats
            stmt = select(
                func.count(APIUsageLog.id).label("total_requests"),
                func.count().filter(APIUsageLog.status_code < 400).label("successful_requests"),
                func.count().filter(APIUsageLog.status_code >= 400).label("failed_requests"),
                func.avg(APIUsageLog.response_time_ms).label("avg_response_time"),
                func.sum(APIUsageLog.response_size_bytes).label("total_bytes"),
                func.count(func.distinct(APIUsageLog.endpoint)).label("unique_endpoints")
            )
            
            if filters:
                stmt = stmt.where(and_(*filters))
            
            result = await db.execute(stmt)
            stats = result.first()
            
            return {
                "total_requests": stats.total_requests or 0,
                "successful_requests": stats.successful_requests or 0,
                "failed_requests": stats.failed_requests or 0,
                "success_rate": (stats.successful_requests / stats.total_requests * 100) if stats.total_requests > 0 else 0,
                "avg_response_time_ms": float(stats.avg_response_time or 0),
                "total_response_size_bytes": stats.total_bytes or 0,
                "unique_endpoints": stats.unique_endpoints or 0,
                "period_start": start_date,
                "period_end": end_date
            }
            
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "success_rate": 0,
                "avg_response_time_ms": 0,
                "total_response_size_bytes": 0,
                "unique_endpoints": 0,
                "period_start": start_date,
                "period_end": end_date
            }
    
    async def get_usage_by_endpoint(
        self,
        db: AsyncSession,
        api_key_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get usage statistics by endpoint"""
        
        try:
            filters = []
            
            if api_key_id:
                filters.append(APIUsageLog.api_key_id == api_key_id)
            
            if start_date:
                filters.append(APIUsageLog.timestamp >= start_date)
            
            if end_date:
                filters.append(APIUsageLog.timestamp <= end_date)
            
            stmt = select(
                APIUsageLog.endpoint,
                APIUsageLog.method,
                func.count(APIUsageLog.id).label("request_count"),
                func.avg(APIUsageLog.response_time_ms).label("avg_response_time"),
                (func.count().filter(APIUsageLog.status_code < 400) * 100.0 / func.count()).label("success_rate"),
                func.max(APIUsageLog.timestamp).label("last_called")
            ).group_by(
                APIUsageLog.endpoint,
                APIUsageLog.method
            ).order_by(
                func.count(APIUsageLog.id).desc()
            ).limit(limit)
            
            if filters:
                stmt = stmt.where(and_(*filters))
            
            result = await db.execute(stmt)
            rows = result.all()
            
            return [
                {
                    "endpoint": row.endpoint,
                    "method": row.method,
                    "request_count": row.request_count,
                    "avg_response_time_ms": float(row.avg_response_time or 0),
                    "success_rate": float(row.success_rate or 0),
                    "last_called": row.last_called
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Error getting usage by endpoint: {e}")
            return []
    
    async def get_daily_usage(
        self,
        db: AsyncSession,
        api_key_id: Optional[UUID] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get daily usage statistics"""
        
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            filters = [
                APIUsageLog.timestamp >= start_date,
                APIUsageLog.timestamp <= end_date
            ]
            
            if api_key_id:
                filters.append(APIUsageLog.api_key_id == api_key_id)
            
            stmt = select(
                func.date(APIUsageLog.timestamp).label("date"),
                func.count(APIUsageLog.id).label("request_count"),
                func.count().filter(APIUsageLog.status_code >= 400).label("error_count"),
                func.avg(APIUsageLog.response_time_ms).label("avg_response_time")
            ).where(
                and_(*filters)
            ).group_by(
                func.date(APIUsageLog.timestamp)
            ).order_by(
                func.date(APIUsageLog.timestamp)
            )
            
            result = await db.execute(stmt)
            rows = result.all()
            
            return [
                {
                    "date": row.date,
                    "request_count": row.request_count,
                    "error_count": row.error_count,
                    "avg_response_time_ms": float(row.avg_response_time or 0)
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Error getting daily usage: {e}")
            return []
    
    async def get_error_analysis(
        self,
        db: AsyncSession,
        api_key_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get error analysis for API usage"""
        
        try:
            filters = [APIUsageLog.status_code >= 400]
            
            if api_key_id:
                filters.append(APIUsageLog.api_key_id == api_key_id)
            
            if start_date:
                filters.append(APIUsageLog.timestamp >= start_date)
            
            if end_date:
                filters.append(APIUsageLog.timestamp <= end_date)
            
            # Get error breakdown by status code
            status_stmt = select(
                APIUsageLog.status_code,
                func.count(APIUsageLog.id).label("count")
            ).where(
                and_(*filters)
            ).group_by(
                APIUsageLog.status_code
            ).order_by(
                func.count(APIUsageLog.id).desc()
            )
            
            status_result = await db.execute(status_stmt)
            status_breakdown = {
                str(row.status_code): row.count
                for row in status_result.all()
            }
            
            # Get error breakdown by endpoint
            endpoint_stmt = select(
                APIUsageLog.endpoint,
                func.count(APIUsageLog.id).label("count")
            ).where(
                and_(*filters)
            ).group_by(
                APIUsageLog.endpoint
            ).order_by(
                func.count(APIUsageLog.id).desc()
            ).limit(10)
            
            endpoint_result = await db.execute(endpoint_stmt)
            endpoint_breakdown = {
                row.endpoint: row.count
                for row in endpoint_result.all()
            }
            
            # Get total error count
            total_stmt = select(func.count(APIUsageLog.id)).where(and_(*filters))
            total_result = await db.execute(total_stmt)
            total_errors = total_result.scalar() or 0
            
            return {
                "total_errors": total_errors,
                "by_status_code": status_breakdown,
                "by_endpoint": endpoint_breakdown
            }
            
        except Exception as e:
            logger.error(f"Error getting error analysis: {e}")
            return {
                "total_errors": 0,
                "by_status_code": {},
                "by_endpoint": {}
            }
    
    async def cleanup_old_logs(
        self,
        db: AsyncSession,
        retention_days: int = 90
    ) -> int:
        """Clean up old usage logs"""
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            stmt = select(func.count(APIUsageLog.id)).where(
                APIUsageLog.timestamp < cutoff_date
            )
            result = await db.execute(stmt)
            count_to_delete = result.scalar() or 0
            
            # Delete old records
            delete_stmt = APIUsageLog.__table__.delete().where(
                APIUsageLog.timestamp < cutoff_date
            )
            await db.execute(delete_stmt)
            await db.commit()
            
            logger.info(f"Cleaned up {count_to_delete} old usage log records")
            return count_to_delete
            
        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")
            await db.rollback()
            return 0
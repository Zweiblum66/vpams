"""
Storage Analytics and Reporting Service

This module provides comprehensive analytics and reporting capabilities for storage
usage, performance metrics, and system health monitoring.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from collections import defaultdict
import statistics

from ..core.interfaces import StorageObject, StorageOperationError
from ..core.config import get_settings


logger = logging.getLogger(__name__)


class ReportType(Enum):
    """Types of analytics reports"""
    STORAGE_USAGE = "storage_usage"
    PERFORMANCE = "performance"
    TIER_DISTRIBUTION = "tier_distribution"
    ACCESS_PATTERNS = "access_patterns"
    QUOTA_USAGE = "quota_usage"
    DRIVER_HEALTH = "driver_health"
    COST_ANALYSIS = "cost_analysis"


class TimeRange(Enum):
    """Time ranges for analytics"""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


@dataclass
class StorageMetric:
    """Individual storage metric"""
    timestamp: datetime
    driver_name: str
    metric_type: str
    value: float
    unit: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "driver_name": self.driver_name,
            "metric_type": self.metric_type,
            "value": self.value,
            "unit": self.unit,
            "metadata": self.metadata
        }


@dataclass
class AnalyticsReport:
    """Analytics report container"""
    report_id: str
    report_type: ReportType
    time_range: TimeRange
    start_time: datetime
    end_time: datetime
    generated_at: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "report_id": self.report_id,
            "report_type": self.report_type.value,
            "time_range": self.time_range.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "data": self.data,
            "summary": self.summary,
            "metadata": self.metadata
        }


@dataclass
class UsageStats:
    """Storage usage statistics"""
    total_objects: int = 0
    total_bytes: int = 0
    total_files: int = 0
    avg_file_size: float = 0.0
    median_file_size: float = 0.0
    largest_file_size: int = 0
    smallest_file_size: int = 0
    by_driver: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_tier: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_file_type: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    growth_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_objects": self.total_objects,
            "total_bytes": self.total_bytes,
            "total_files": self.total_files,
            "avg_file_size": self.avg_file_size,
            "median_file_size": self.median_file_size,
            "largest_file_size": self.largest_file_size,
            "smallest_file_size": self.smallest_file_size,
            "by_driver": self.by_driver,
            "by_tier": self.by_tier,
            "by_file_type": self.by_file_type,
            "growth_rate": self.growth_rate
        }


@dataclass
class PerformanceStats:
    """Storage performance statistics"""
    avg_upload_speed: float = 0.0
    avg_download_speed: float = 0.0
    avg_response_time: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    success_rate: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    by_operation: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_driver: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "avg_upload_speed": self.avg_upload_speed,
            "avg_download_speed": self.avg_download_speed,
            "avg_response_time": self.avg_response_time,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.success_rate,
            "p95_response_time": self.p95_response_time,
            "p99_response_time": self.p99_response_time,
            "by_operation": self.by_operation,
            "by_driver": self.by_driver
        }


class AnalyticsService:
    """Service for storage analytics and reporting"""
    
    def __init__(self, storage_service):
        self.storage_service = storage_service
        self.settings = get_settings()
        
        # Metrics storage
        self._metrics: List[StorageMetric] = []
        self._reports: Dict[str, AnalyticsReport] = {}
        self._metric_retention_days = 90
        
        # Performance tracking
        self._operation_times: Dict[str, List[float]] = defaultdict(list)
        self._request_counts: Dict[str, int] = defaultdict(int)
        self._error_counts: Dict[str, int] = defaultdict(int)
        
        # Data persistence
        self._data_dir = Path(self.settings.temp_directory) / "analytics"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        
        # Background tasks
        self._collection_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
    
    async def initialize(self) -> None:
        """Initialize the analytics service"""
        logger.info("Initializing analytics service")
        
        # Load persisted data
        await self._load_data()
        
        # Start background tasks
        if self.settings.enable_metrics:
            self._collection_task = asyncio.create_task(self._metrics_collection_worker())
            self._cleanup_task = asyncio.create_task(self._cleanup_worker())
    
    async def shutdown(self) -> None:
        """Shutdown the analytics service"""
        logger.info("Shutting down analytics service")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel background tasks
        for task in [self._collection_task, self._cleanup_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Save data
        await self._save_data()
    
    def record_metric(
        self,
        driver_name: str,
        metric_type: str,
        value: float,
        unit: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a storage metric"""
        metric = StorageMetric(
            timestamp=datetime.utcnow(),
            driver_name=driver_name,
            metric_type=metric_type,
            value=value,
            unit=unit,
            metadata=metadata or {}
        )
        
        self._metrics.append(metric)
        
        # Keep metrics limited
        if len(self._metrics) > 100000:  # 100k metrics max
            self._metrics = self._metrics[-50000:]  # Keep last 50k
    
    def record_operation_time(
        self,
        operation: str,
        duration: float,
        driver_name: str,
        success: bool = True
    ) -> None:
        """Record operation timing"""
        key = f"{driver_name}:{operation}"
        self._operation_times[key].append(duration)
        
        if success:
            self._request_counts[key] += 1
        else:
            self._error_counts[key] += 1
        
        # Keep operation times limited
        if len(self._operation_times[key]) > 1000:
            self._operation_times[key] = self._operation_times[key][-500:]
    
    async def get_usage_stats(
        self,
        driver_name: Optional[str] = None,
        time_range: Optional[TimeRange] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> UsageStats:
        """Get storage usage statistics"""
        stats = UsageStats()
        
        # Get time range
        if time_range:
            start_time, end_time = self._get_time_range_bounds(time_range)
        elif not start_time or not end_time:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=30)
        
        # Collect data from all or specific drivers
        drivers_to_check = [driver_name] if driver_name else list(self.storage_service._drivers.keys())
        
        all_objects = []
        for driver in drivers_to_check:
            try:
                driver_instance = self.storage_service.get_driver(driver)
                objects, _ = await driver_instance.list_objects(max_keys=10000)
                
                # Filter by time range if specified
                filtered_objects = [
                    obj for obj in objects
                    if start_time <= obj.last_modified <= end_time
                ]
                
                all_objects.extend(filtered_objects)
                
                # Driver-specific stats
                driver_stats = self._calculate_driver_stats(filtered_objects)
                stats.by_driver[driver] = driver_stats
                
            except Exception as e:
                logger.error(f"Failed to get stats for driver {driver}: {e}")
        
        # Calculate overall stats
        if all_objects:
            file_sizes = [obj.size for obj in all_objects]
            
            stats.total_objects = len(all_objects)
            stats.total_bytes = sum(file_sizes)
            stats.total_files = len(all_objects)
            stats.avg_file_size = statistics.mean(file_sizes)
            stats.median_file_size = statistics.median(file_sizes)
            stats.largest_file_size = max(file_sizes)
            stats.smallest_file_size = min(file_sizes)
            
            # Group by tier
            stats.by_tier = self._group_by_tier(all_objects)
            
            # Group by file type
            stats.by_file_type = self._group_by_file_type(all_objects)
            
            # Calculate growth rate
            stats.growth_rate = await self._calculate_growth_rate(time_range or TimeRange.MONTH)
        
        return stats
    
    async def get_performance_stats(
        self,
        driver_name: Optional[str] = None,
        time_range: Optional[TimeRange] = None
    ) -> PerformanceStats:
        """Get storage performance statistics"""
        stats = PerformanceStats()
        
        # Get time range
        if time_range:
            start_time, end_time = self._get_time_range_bounds(time_range)
        else:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
        
        # Filter metrics by time range and driver
        filtered_metrics = [
            metric for metric in self._metrics
            if start_time <= metric.timestamp <= end_time
            and (not driver_name or metric.driver_name == driver_name)
        ]
        
        # Calculate performance metrics from operation times
        for key, times in self._operation_times.items():
            if not times:
                continue
            
            key_driver, operation = key.split(":", 1)
            if driver_name and key_driver != driver_name:
                continue
            
            op_stats = {
                "avg_time": statistics.mean(times),
                "median_time": statistics.median(times),
                "min_time": min(times),
                "max_time": max(times),
                "total_requests": self._request_counts[key],
                "failed_requests": self._error_counts[key]
            }
            
            if len(times) > 1:
                sorted_times = sorted(times)
                op_stats["p95_time"] = sorted_times[int(len(sorted_times) * 0.95)]
                op_stats["p99_time"] = sorted_times[int(len(sorted_times) * 0.99)]
            
            stats.by_operation[operation] = op_stats
            stats.by_driver[key_driver] = stats.by_driver.get(key_driver, {})
            stats.by_driver[key_driver][operation] = op_stats
        
        # Calculate overall stats
        all_times = []
        total_requests = 0
        total_errors = 0
        
        for times in self._operation_times.values():
            all_times.extend(times)
        
        for count in self._request_counts.values():
            total_requests += count
        
        for count in self._error_counts.values():
            total_errors += count
        
        if all_times:
            stats.avg_response_time = statistics.mean(all_times)
            sorted_times = sorted(all_times)
            stats.p95_response_time = sorted_times[int(len(sorted_times) * 0.95)]
            stats.p99_response_time = sorted_times[int(len(sorted_times) * 0.99)]
        
        stats.total_requests = total_requests
        stats.failed_requests = total_errors
        stats.successful_requests = total_requests - total_errors
        
        if total_requests > 0:
            stats.success_rate = (stats.successful_requests / total_requests) * 100
        
        return stats
    
    async def generate_report(
        self,
        report_type: ReportType,
        time_range: TimeRange,
        filters: Optional[Dict[str, Any]] = None
    ) -> AnalyticsReport:
        """Generate an analytics report"""
        import uuid
        
        start_time, end_time = self._get_time_range_bounds(time_range)
        
        report_id = str(uuid.uuid4())
        report = AnalyticsReport(
            report_id=report_id,
            report_type=report_type,
            time_range=time_range,
            start_time=start_time,
            end_time=end_time
        )
        
        try:
            if report_type == ReportType.STORAGE_USAGE:
                await self._generate_usage_report(report, filters)
            elif report_type == ReportType.PERFORMANCE:
                await self._generate_performance_report(report, filters)
            elif report_type == ReportType.TIER_DISTRIBUTION:
                await self._generate_tier_report(report, filters)
            elif report_type == ReportType.ACCESS_PATTERNS:
                await self._generate_access_report(report, filters)
            elif report_type == ReportType.QUOTA_USAGE:
                await self._generate_quota_report(report, filters)
            elif report_type == ReportType.DRIVER_HEALTH:
                await self._generate_health_report(report, filters)
            elif report_type == ReportType.COST_ANALYSIS:
                await self._generate_cost_report(report, filters)
            else:
                raise ValueError(f"Unknown report type: {report_type}")
            
            self._reports[report_id] = report
            
        except Exception as e:
            logger.error(f"Failed to generate report {report_type}: {e}")
            report.summary["error"] = str(e)
        
        return report
    
    def get_report(self, report_id: str) -> Optional[AnalyticsReport]:
        """Get a generated report"""
        return self._reports.get(report_id)
    
    def list_reports(
        self,
        report_type: Optional[ReportType] = None,
        limit: int = 50
    ) -> List[AnalyticsReport]:
        """List generated reports"""
        reports = list(self._reports.values())
        
        if report_type:
            reports = [r for r in reports if r.report_type == report_type]
        
        # Sort by generation time (newest first)
        reports.sort(key=lambda r: r.generated_at, reverse=True)
        
        return reports[:limit]
    
    def delete_report(self, report_id: str) -> bool:
        """Delete a report"""
        if report_id in self._reports:
            del self._reports[report_id]
            return True
        return False
    
    def _calculate_driver_stats(self, objects: List[StorageObject]) -> Dict[str, Any]:
        """Calculate statistics for a specific driver"""
        if not objects:
            return {
                "object_count": 0,
                "total_bytes": 0,
                "avg_size": 0,
                "file_types": {}
            }
        
        file_sizes = [obj.size for obj in objects]
        file_types = defaultdict(int)
        
        for obj in objects:
            ext = Path(obj.key).suffix.lower()
            file_types[ext or "no_extension"] += 1
        
        return {
            "object_count": len(objects),
            "total_bytes": sum(file_sizes),
            "avg_size": statistics.mean(file_sizes),
            "median_size": statistics.median(file_sizes),
            "largest_size": max(file_sizes),
            "smallest_size": min(file_sizes),
            "file_types": dict(file_types)
        }
    
    def _group_by_tier(self, objects: List[StorageObject]) -> Dict[str, Dict[str, Any]]:
        """Group objects by storage tier"""
        tiers = defaultdict(list)
        
        for obj in objects:
            tier = self._get_tier_from_storage_class(obj.storage_class or "hot")
            tiers[tier].append(obj)
        
        result = {}
        for tier, tier_objects in tiers.items():
            result[tier] = self._calculate_driver_stats(tier_objects)
        
        return result
    
    def _group_by_file_type(self, objects: List[StorageObject]) -> Dict[str, Dict[str, Any]]:
        """Group objects by file type"""
        types = defaultdict(list)
        
        for obj in objects:
            ext = Path(obj.key).suffix.lower()
            file_type = self._categorize_file_type(ext)
            types[file_type].append(obj)
        
        result = {}
        for file_type, type_objects in types.items():
            result[file_type] = self._calculate_driver_stats(type_objects)
        
        return result
    
    def _categorize_file_type(self, extension: str) -> str:
        """Categorize file by extension"""
        video_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"}
        audio_exts = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"}
        image_exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".svg", ".webp"}
        document_exts = {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt"}
        
        if extension in video_exts:
            return "video"
        elif extension in audio_exts:
            return "audio"
        elif extension in image_exts:
            return "image"
        elif extension in document_exts:
            return "document"
        else:
            return "other"
    
    def _get_tier_from_storage_class(self, storage_class: str) -> str:
        """Get tier name from storage class"""
        storage_class_lower = storage_class.lower()
        
        if "hot" in storage_class_lower or "standard" in storage_class_lower:
            return "hot"
        elif "warm" in storage_class_lower or "nearline" in storage_class_lower:
            return "warm"
        elif "cold" in storage_class_lower or "coldline" in storage_class_lower:
            return "cold"
        elif "archive" in storage_class_lower or "glacier" in storage_class_lower:
            return "archive"
        else:
            return "unknown"
    
    def _get_time_range_bounds(self, time_range: TimeRange) -> Tuple[datetime, datetime]:
        """Get start and end times for a time range"""
        end_time = datetime.utcnow()
        
        if time_range == TimeRange.HOUR:
            start_time = end_time - timedelta(hours=1)
        elif time_range == TimeRange.DAY:
            start_time = end_time - timedelta(days=1)
        elif time_range == TimeRange.WEEK:
            start_time = end_time - timedelta(weeks=1)
        elif time_range == TimeRange.MONTH:
            start_time = end_time - timedelta(days=30)
        elif time_range == TimeRange.QUARTER:
            start_time = end_time - timedelta(days=90)
        elif time_range == TimeRange.YEAR:
            start_time = end_time - timedelta(days=365)
        else:
            start_time = end_time - timedelta(days=1)
        
        return start_time, end_time
    
    async def _calculate_growth_rate(self, time_range: TimeRange) -> float:
        """Calculate storage growth rate"""
        # Simplified growth rate calculation
        # In a real implementation, this would compare historical data
        try:
            current_stats = await self.get_usage_stats(time_range=time_range)
            
            # Get previous period stats for comparison
            previous_start, previous_end = self._get_time_range_bounds(time_range)
            duration = previous_end - previous_start
            previous_start = previous_start - duration
            previous_end = previous_start + duration
            
            previous_stats = await self.get_usage_stats(
                start_time=previous_start,
                end_time=previous_end
            )
            
            if previous_stats.total_bytes > 0:
                growth = ((current_stats.total_bytes - previous_stats.total_bytes) / 
                         previous_stats.total_bytes) * 100
                return round(growth, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate growth rate: {e}")
        
        return 0.0
    
    async def _generate_usage_report(
        self,
        report: AnalyticsReport,
        filters: Optional[Dict[str, Any]]
    ) -> None:
        """Generate storage usage report"""
        driver_name = filters.get("driver") if filters else None
        stats = await self.get_usage_stats(
            driver_name=driver_name,
            time_range=report.time_range
        )
        
        report.data = stats.to_dict()
        report.summary = {
            "total_objects": stats.total_objects,
            "total_size_gb": round(stats.total_bytes / (1024**3), 2),
            "avg_file_size_mb": round(stats.avg_file_size / (1024**2), 2),
            "growth_rate_percent": stats.growth_rate,
            "top_driver": max(stats.by_driver.items(), 
                            key=lambda x: x[1]["total_bytes"])[0] if stats.by_driver else None
        }
    
    async def _generate_performance_report(
        self,
        report: AnalyticsReport,
        filters: Optional[Dict[str, Any]]
    ) -> None:
        """Generate performance report"""
        driver_name = filters.get("driver") if filters else None
        stats = await self.get_performance_stats(
            driver_name=driver_name,
            time_range=report.time_range
        )
        
        report.data = stats.to_dict()
        report.summary = {
            "avg_response_time_ms": round(stats.avg_response_time * 1000, 2),
            "success_rate_percent": round(stats.success_rate, 2),
            "total_requests": stats.total_requests,
            "p95_response_time_ms": round(stats.p95_response_time * 1000, 2)
        }
    
    async def _generate_tier_report(
        self,
        report: AnalyticsReport,
        filters: Optional[Dict[str, Any]]
    ) -> None:
        """Generate tier distribution report"""
        stats = await self.get_usage_stats(time_range=report.time_range)
        
        report.data = {
            "tier_distribution": stats.by_tier,
            "total_objects": stats.total_objects,
            "total_bytes": stats.total_bytes
        }
        
        # Calculate tier percentages
        tier_percentages = {}
        if stats.total_bytes > 0:
            for tier, tier_stats in stats.by_tier.items():
                percentage = (tier_stats["total_bytes"] / stats.total_bytes) * 100
                tier_percentages[tier] = round(percentage, 2)
        
        report.summary = {
            "tier_percentages": tier_percentages,
            "dominant_tier": max(tier_percentages.items(), 
                               key=lambda x: x[1])[0] if tier_percentages else None
        }
    
    async def _generate_access_report(
        self,
        report: AnalyticsReport,
        filters: Optional[Dict[str, Any]]
    ) -> None:
        """Generate access patterns report"""
        # Simplified access patterns based on operation metrics
        access_metrics = [
            metric for metric in self._metrics
            if metric.metric_type in ["download", "access", "read"]
            and report.start_time <= metric.timestamp <= report.end_time
        ]
        
        access_by_hour = defaultdict(int)
        access_by_driver = defaultdict(int)
        
        for metric in access_metrics:
            hour = metric.timestamp.hour
            access_by_hour[hour] += 1
            access_by_driver[metric.driver_name] += 1
        
        report.data = {
            "access_by_hour": dict(access_by_hour),
            "access_by_driver": dict(access_by_driver),
            "total_accesses": len(access_metrics)
        }
        
        peak_hour = max(access_by_hour.items(), key=lambda x: x[1])[0] if access_by_hour else 0
        most_accessed_driver = max(access_by_driver.items(), 
                                 key=lambda x: x[1])[0] if access_by_driver else None
        
        report.summary = {
            "total_accesses": len(access_metrics),
            "peak_access_hour": peak_hour,
            "most_accessed_driver": most_accessed_driver
        }
    
    async def _generate_quota_report(
        self,
        report: AnalyticsReport,
        filters: Optional[Dict[str, Any]]
    ) -> None:
        """Generate quota usage report"""
        # This would integrate with the quota service
        # For now, provide a placeholder implementation
        report.data = {
            "quota_violations": [],
            "usage_warnings": [],
            "top_consumers": []
        }
        
        report.summary = {
            "total_violations": 0,
            "total_warnings": 0,
            "overall_usage_percent": 0
        }
    
    async def _generate_health_report(
        self,
        report: AnalyticsReport,
        filters: Optional[Dict[str, Any]]
    ) -> None:
        """Generate driver health report"""
        health_status = {}
        
        for driver_name in self.storage_service._drivers:
            try:
                driver = self.storage_service.get_driver(driver_name)
                # Simple health check - try to list objects
                await driver.list_objects(max_keys=1)
                health_status[driver_name] = {
                    "status": "healthy",
                    "last_checked": datetime.utcnow().isoformat(),
                    "error_rate": self._error_counts.get(driver_name, 0) / 
                                max(self._request_counts.get(driver_name, 1), 1) * 100
                }
            except Exception as e:
                health_status[driver_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "last_checked": datetime.utcnow().isoformat()
                }
        
        report.data = {"driver_health": health_status}
        
        healthy_drivers = sum(1 for status in health_status.values() 
                            if status["status"] == "healthy")
        total_drivers = len(health_status)
        
        report.summary = {
            "healthy_drivers": healthy_drivers,
            "total_drivers": total_drivers,
            "health_percentage": (healthy_drivers / total_drivers) * 100 if total_drivers > 0 else 0
        }
    
    async def _generate_cost_report(
        self,
        report: AnalyticsReport,
        filters: Optional[Dict[str, Any]]
    ) -> None:
        """Generate cost analysis report"""
        # Simplified cost calculation based on storage usage
        # In reality, this would integrate with cloud provider billing APIs
        
        stats = await self.get_usage_stats(time_range=report.time_range)
        
        # Estimate costs (simplified)
        cost_per_gb = {
            "hot": 0.023,     # $0.023 per GB
            "warm": 0.0125,   # $0.0125 per GB
            "cold": 0.004,    # $0.004 per GB
            "archive": 0.00099 # $0.00099 per GB
        }
        
        estimated_costs = {}
        total_cost = 0
        
        for tier, tier_stats in stats.by_tier.items():
            gb_used = tier_stats["total_bytes"] / (1024**3)
            tier_cost = gb_used * cost_per_gb.get(tier, 0.023)
            estimated_costs[tier] = round(tier_cost, 2)
            total_cost += tier_cost
        
        report.data = {
            "estimated_costs_by_tier": estimated_costs,
            "storage_breakdown": stats.by_tier
        }
        
        report.summary = {
            "total_estimated_cost": round(total_cost, 2),
            "most_expensive_tier": max(estimated_costs.items(), 
                                     key=lambda x: x[1])[0] if estimated_costs else None,
            "cost_per_gb_avg": round(total_cost / (stats.total_bytes / (1024**3)), 4) 
                              if stats.total_bytes > 0 else 0
        }
    
    async def _metrics_collection_worker(self) -> None:
        """Background worker for collecting metrics"""
        logger.info("Starting metrics collection worker")
        
        while not self._shutdown_event.is_set():
            try:
                # Collect metrics every 5 minutes
                await asyncio.sleep(300)
                
                # Collect driver metrics
                for driver_name in self.storage_service._drivers:
                    try:
                        await self._collect_driver_metrics(driver_name)
                    except Exception as e:
                        logger.error(f"Failed to collect metrics for {driver_name}: {e}")
                
                # Save metrics periodically
                await self._save_data()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics collection worker error: {e}")
                await asyncio.sleep(60)
        
        logger.info("Metrics collection worker stopped")
    
    async def _collect_driver_metrics(self, driver_name: str) -> None:
        """Collect metrics for a specific driver"""
        try:
            driver = self.storage_service.get_driver(driver_name)
            
            # Get basic object count and size
            objects, _ = await driver.list_objects(max_keys=1000)
            
            total_objects = len(objects)
            total_bytes = sum(obj.size for obj in objects)
            
            # Record metrics
            self.record_metric(driver_name, "object_count", total_objects, "count")
            self.record_metric(driver_name, "total_bytes", total_bytes, "bytes")
            
            if total_objects > 0:
                avg_size = total_bytes / total_objects
                self.record_metric(driver_name, "avg_object_size", avg_size, "bytes")
            
        except Exception as e:
            logger.error(f"Failed to collect driver metrics for {driver_name}: {e}")
    
    async def _cleanup_worker(self) -> None:
        """Background worker for cleaning up old data"""
        logger.info("Starting analytics cleanup worker")
        
        while not self._shutdown_event.is_set():
            try:
                # Cleanup every day
                await asyncio.sleep(86400)
                
                # Remove old metrics
                cutoff_time = datetime.utcnow() - timedelta(days=self._metric_retention_days)
                self._metrics = [
                    metric for metric in self._metrics
                    if metric.timestamp > cutoff_time
                ]
                
                # Remove old reports (keep last 100)
                if len(self._reports) > 100:
                    sorted_reports = sorted(
                        self._reports.items(),
                        key=lambda x: x[1].generated_at,
                        reverse=True
                    )
                    self._reports = dict(sorted_reports[:100])
                
                logger.info(f"Cleaned up old analytics data. "
                          f"Metrics: {len(self._metrics)}, Reports: {len(self._reports)}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Analytics cleanup worker error: {e}")
                await asyncio.sleep(3600)
        
        logger.info("Analytics cleanup worker stopped")
    
    async def _save_data(self) -> None:
        """Save analytics data to disk"""
        try:
            # Save metrics (last 10k only)
            metrics_data = [
                metric.to_dict() 
                for metric in self._metrics[-10000:]
            ]
            
            metrics_file = self._data_dir / "metrics.json"
            with open(metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)
            
            # Save reports metadata
            reports_data = {
                report_id: report.to_dict()
                for report_id, report in self._reports.items()
            }
            
            reports_file = self._data_dir / "reports.json"
            with open(reports_file, 'w') as f:
                json.dump(reports_data, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save analytics data: {e}")
    
    async def _load_data(self) -> None:
        """Load analytics data from disk"""
        try:
            # Load metrics
            metrics_file = self._data_dir / "metrics.json"
            if metrics_file.exists():
                with open(metrics_file, 'r') as f:
                    metrics_data = json.load(f)
                
                self._metrics = []
                for metric_dict in metrics_data:
                    metric = StorageMetric(
                        timestamp=datetime.fromisoformat(metric_dict["timestamp"]),
                        driver_name=metric_dict["driver_name"],
                        metric_type=metric_dict["metric_type"],
                        value=metric_dict["value"],
                        unit=metric_dict["unit"],
                        metadata=metric_dict.get("metadata", {})
                    )
                    self._metrics.append(metric)
            
            # Load reports
            reports_file = self._data_dir / "reports.json"
            if reports_file.exists():
                with open(reports_file, 'r') as f:
                    reports_data = json.load(f)
                
                for report_id, report_dict in reports_data.items():
                    report = AnalyticsReport(
                        report_id=report_dict["report_id"],
                        report_type=ReportType(report_dict["report_type"]),
                        time_range=TimeRange(report_dict["time_range"]),
                        start_time=datetime.fromisoformat(report_dict["start_time"]),
                        end_time=datetime.fromisoformat(report_dict["end_time"]),
                        generated_at=datetime.fromisoformat(report_dict["generated_at"]),
                        data=report_dict.get("data", {}),
                        summary=report_dict.get("summary", {}),
                        metadata=report_dict.get("metadata", {})
                    )
                    self._reports[report_id] = report
            
        except Exception as e:
            logger.error(f"Failed to load analytics data: {e}")


# Global instance
_analytics_service: Optional[AnalyticsService] = None


async def get_analytics_service(storage_service) -> AnalyticsService:
    """Get or create analytics service instance"""
    global _analytics_service
    
    if _analytics_service is None:
        _analytics_service = AnalyticsService(storage_service)
        await _analytics_service.initialize()
    
    return _analytics_service


async def close_analytics_service() -> None:
    """Close analytics service"""
    global _analytics_service
    
    if _analytics_service is not None:
        await _analytics_service.shutdown()
        _analytics_service = None
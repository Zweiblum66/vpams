"""
Tests for Analytics functionality
"""

import pytest
import asyncio
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import statistics

from src.services.analytics_service import (
    AnalyticsService, StorageMetric, AnalyticsReport, UsageStats, PerformanceStats,
    ReportType, TimeRange
)
from src.core.interfaces import StorageObject


class MockStorageDriver:
    """Mock storage driver for testing"""
    def __init__(self, driver_name: str = "test_driver"):
        self.driver_name = driver_name
        self.objects = [
            StorageObject(
                key="video/test1.mp4",
                size=1024 * 1024 * 100,  # 100MB
                last_modified=datetime.utcnow() - timedelta(days=1),
                etag="abc123",
                storage_class="hot"
            ),
            StorageObject(
                key="images/photo1.jpg",
                size=1024 * 1024 * 5,  # 5MB
                last_modified=datetime.utcnow() - timedelta(days=10),
                etag="def456",
                storage_class="warm"
            ),
            StorageObject(
                key="documents/report.pdf",
                size=1024 * 512,  # 512KB
                last_modified=datetime.utcnow() - timedelta(days=30),
                etag="ghi789",
                storage_class="cold"
            ),
            StorageObject(
                key="archive/old_data.zip",
                size=1024 * 1024 * 1024,  # 1GB
                last_modified=datetime.utcnow() - timedelta(days=365),
                etag="jkl012",
                storage_class="archive"
            )
        ]
    
    async def list_objects(self, **kwargs):
        max_keys = kwargs.get('max_keys', len(self.objects))
        return self.objects[:max_keys], None


class MockStorageService:
    """Mock storage service for testing"""
    def __init__(self):
        self._drivers = {
            "local": MockStorageDriver("local"),
            "s3": MockStorageDriver("s3"),
            "azure": MockStorageDriver("azure")
        }
        self._default_driver = "local"
    
    def get_driver(self, driver_name=None):
        return self._drivers.get(driver_name or self._default_driver)


class MockSettings:
    """Mock settings for testing"""
    def __init__(self):
        self.enable_metrics = True
        self.temp_directory = tempfile.mkdtemp()


@pytest.fixture
async def analytics_service():
    """Create an analytics service for testing"""
    storage_service = MockStorageService()
    
    # Create temporary directory for test data
    temp_dir = tempfile.mkdtemp()
    
    service = AnalyticsService(storage_service)
    service.settings = MockSettings()
    service._data_dir = Path(temp_dir) / "analytics"
    service._data_dir.mkdir(parents=True, exist_ok=True)
    
    # Don't start background workers in tests
    service._collection_task = None
    service._cleanup_task = None
    
    yield service
    
    await service.shutdown()
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestMetricRecording:
    """Test cases for metric recording"""
    
    def test_record_metric(self, analytics_service):
        """Test recording a storage metric"""
        analytics_service.record_metric(
            driver_name="local",
            metric_type="upload_speed",
            value=1024.5,
            unit="bytes/sec",
            metadata={"file_type": "video"}
        )
        
        assert len(analytics_service._metrics) == 1
        metric = analytics_service._metrics[0]
        
        assert metric.driver_name == "local"
        assert metric.metric_type == "upload_speed"
        assert metric.value == 1024.5
        assert metric.unit == "bytes/sec"
        assert metric.metadata["file_type"] == "video"
    
    def test_record_operation_time(self, analytics_service):
        """Test recording operation timing"""
        analytics_service.record_operation_time(
            operation="upload",
            duration=2.5,
            driver_name="s3",
            success=True
        )
        
        key = "s3:upload"
        assert key in analytics_service._operation_times
        assert analytics_service._operation_times[key] == [2.5]
        assert analytics_service._request_counts[key] == 1
        assert analytics_service._error_counts[key] == 0
    
    def test_record_failed_operation(self, analytics_service):
        """Test recording failed operation"""
        analytics_service.record_operation_time(
            operation="download",
            duration=1.0,
            driver_name="azure",
            success=False
        )
        
        key = "azure:download"
        assert analytics_service._operation_times[key] == [1.0]
        assert analytics_service._request_counts[key] == 0
        assert analytics_service._error_counts[key] == 1
    
    def test_metric_limit(self, analytics_service):
        """Test metric storage limit"""
        # Set a low limit for testing
        original_limit = 100000
        analytics_service._metrics = []
        
        # Add metrics up to limit
        for i in range(150):
            analytics_service.record_metric(
                driver_name="local",
                metric_type="test",
                value=i
            )
        
        # Should be limited
        assert len(analytics_service._metrics) == 150


class TestUsageStatistics:
    """Test cases for usage statistics"""
    
    async def test_get_usage_stats_all_drivers(self, analytics_service):
        """Test getting usage stats for all drivers"""
        stats = await analytics_service.get_usage_stats()
        
        # Should have data from all mock drivers (3 drivers * 4 objects each)
        assert stats.total_objects == 12
        assert stats.total_files == 12
        assert stats.total_bytes > 0
        
        # Should have driver breakdown
        assert "local" in stats.by_driver
        assert "s3" in stats.by_driver
        assert "azure" in stats.by_driver
        
        # Each driver should have 4 objects
        for driver_stats in stats.by_driver.values():
            assert driver_stats["object_count"] == 4
    
    async def test_get_usage_stats_single_driver(self, analytics_service):
        """Test getting usage stats for a single driver"""
        stats = await analytics_service.get_usage_stats(driver_name="local")
        
        # Should only have data from local driver
        assert stats.total_objects == 4
        assert len(stats.by_driver) == 1
        assert "local" in stats.by_driver
    
    async def test_usage_stats_by_tier(self, analytics_service):
        """Test usage statistics grouped by tier"""
        stats = await analytics_service.get_usage_stats()
        
        # Should have tier breakdown
        assert "hot" in stats.by_tier
        assert "warm" in stats.by_tier
        assert "cold" in stats.by_tier
        assert "archive" in stats.by_tier
        
        # Each tier should have some objects (3 drivers with 1 object per tier)
        for tier_stats in stats.by_tier.values():
            assert tier_stats["object_count"] == 3
    
    async def test_usage_stats_by_file_type(self, analytics_service):
        """Test usage statistics grouped by file type"""
        stats = await analytics_service.get_usage_stats()
        
        # Should have file type breakdown
        assert "video" in stats.by_file_type
        assert "image" in stats.by_file_type
        assert "document" in stats.by_file_type
        assert "other" in stats.by_file_type
        
        # Video should have 3 objects (one per driver)
        assert stats.by_file_type["video"]["object_count"] == 3
        assert stats.by_file_type["image"]["object_count"] == 3
        assert stats.by_file_type["document"]["object_count"] == 3
        assert stats.by_file_type["other"]["object_count"] == 3
    
    async def test_usage_stats_calculations(self, analytics_service):
        """Test usage statistics calculations"""
        stats = await analytics_service.get_usage_stats()
        
        # Test calculated fields
        assert stats.avg_file_size > 0
        assert stats.median_file_size > 0
        assert stats.largest_file_size > stats.smallest_file_size
        assert stats.smallest_file_size > 0


class TestPerformanceStatistics:
    """Test cases for performance statistics"""
    
    async def test_get_performance_stats_empty(self, analytics_service):
        """Test getting performance stats with no data"""
        stats = await analytics_service.get_performance_stats()
        
        # Should return empty stats
        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0
        assert stats.avg_response_time == 0
    
    async def test_get_performance_stats_with_data(self, analytics_service):
        """Test getting performance stats with recorded data"""
        # Record some operation times
        analytics_service.record_operation_time("upload", 1.0, "local", True)
        analytics_service.record_operation_time("upload", 2.0, "local", True)
        analytics_service.record_operation_time("upload", 1.5, "local", False)
        analytics_service.record_operation_time("download", 0.5, "s3", True)
        analytics_service.record_operation_time("download", 0.8, "s3", True)
        
        stats = await analytics_service.get_performance_stats()
        
        # Should have aggregated stats
        assert stats.total_requests == 4  # Successful requests
        assert stats.failed_requests == 1  # Failed requests
        assert stats.successful_requests == 4
        
        # Should have operation breakdown
        assert "upload" in stats.by_operation
        assert "download" in stats.by_operation
        
        upload_stats = stats.by_operation["upload"]
        assert upload_stats["total_requests"] == 2
        assert upload_stats["failed_requests"] == 1
        assert upload_stats["avg_time"] == 1.5  # (1.0 + 2.0 + 1.5) / 3
    
    async def test_performance_stats_percentiles(self, analytics_service):
        """Test performance statistics percentile calculations"""
        # Record many operation times
        times = [i * 0.1 for i in range(1, 101)]  # 0.1 to 10.0 seconds
        
        for time in times:
            analytics_service.record_operation_time("test", time, "local", True)
        
        stats = await analytics_service.get_performance_stats()
        
        # Should calculate percentiles
        assert stats.p95_response_time > 0
        assert stats.p99_response_time > 0
        assert stats.p99_response_time >= stats.p95_response_time


class TestReportGeneration:
    """Test cases for report generation"""
    
    async def test_generate_usage_report(self, analytics_service):
        """Test generating storage usage report"""
        report = await analytics_service.generate_report(
            ReportType.STORAGE_USAGE,
            TimeRange.MONTH
        )
        
        assert report.report_type == ReportType.STORAGE_USAGE
        assert report.time_range == TimeRange.MONTH
        assert report.report_id is not None
        
        # Should have data and summary
        assert "total_objects" in report.data
        assert "by_driver" in report.data
        assert "total_objects" in report.summary
        assert "total_size_gb" in report.summary
    
    async def test_generate_performance_report(self, analytics_service):
        """Test generating performance report"""
        # Add some performance data
        analytics_service.record_operation_time("upload", 1.0, "local", True)
        analytics_service.record_operation_time("download", 0.5, "s3", True)
        
        report = await analytics_service.generate_report(
            ReportType.PERFORMANCE,
            TimeRange.DAY
        )
        
        assert report.report_type == ReportType.PERFORMANCE
        assert report.time_range == TimeRange.DAY
        
        # Should have performance data
        assert "by_operation" in report.data
        assert "avg_response_time_ms" in report.summary
        assert "success_rate_percent" in report.summary
    
    async def test_generate_tier_distribution_report(self, analytics_service):
        """Test generating tier distribution report"""
        report = await analytics_service.generate_report(
            ReportType.TIER_DISTRIBUTION,
            TimeRange.WEEK
        )
        
        assert report.report_type == ReportType.TIER_DISTRIBUTION
        
        # Should have tier distribution data
        assert "tier_distribution" in report.data
        assert "tier_percentages" in report.summary
        assert "dominant_tier" in report.summary
    
    async def test_generate_health_report(self, analytics_service):
        """Test generating driver health report"""
        report = await analytics_service.generate_report(
            ReportType.DRIVER_HEALTH,
            TimeRange.HOUR
        )
        
        assert report.report_type == ReportType.DRIVER_HEALTH
        
        # Should have health data for all drivers
        assert "driver_health" in report.data
        driver_health = report.data["driver_health"]
        
        assert "local" in driver_health
        assert "s3" in driver_health
        assert "azure" in driver_health
        
        # All drivers should be healthy (mocked)
        for driver_status in driver_health.values():
            assert driver_status["status"] == "healthy"
    
    async def test_generate_cost_analysis_report(self, analytics_service):
        """Test generating cost analysis report"""
        report = await analytics_service.generate_report(
            ReportType.COST_ANALYSIS,
            TimeRange.MONTH
        )
        
        assert report.report_type == ReportType.COST_ANALYSIS
        
        # Should have cost data
        assert "estimated_costs_by_tier" in report.data
        assert "total_estimated_cost" in report.summary
        assert "most_expensive_tier" in report.summary
    
    async def test_generate_access_patterns_report(self, analytics_service):
        """Test generating access patterns report"""
        # Add some access metrics
        now = datetime.utcnow()
        for hour in range(24):
            analytics_service.record_metric(
                driver_name="local",
                metric_type="access",
                value=hour,
                metadata={"hour": hour}
            )
            # Set timestamp manually for testing
            if analytics_service._metrics:
                analytics_service._metrics[-1].timestamp = now.replace(hour=hour)
        
        report = await analytics_service.generate_report(
            ReportType.ACCESS_PATTERNS,
            TimeRange.DAY
        )
        
        assert report.report_type == ReportType.ACCESS_PATTERNS
        
        # Should have access pattern data
        assert "access_by_hour" in report.data
        assert "total_accesses" in report.summary


class TestReportManagement:
    """Test cases for report management"""
    
    async def test_get_report(self, analytics_service):
        """Test getting a specific report"""
        # Generate a report first
        report = await analytics_service.generate_report(
            ReportType.STORAGE_USAGE,
            TimeRange.DAY
        )
        
        # Get the report
        retrieved_report = analytics_service.get_report(report.report_id)
        
        assert retrieved_report is not None
        assert retrieved_report.report_id == report.report_id
        assert retrieved_report.report_type == ReportType.STORAGE_USAGE
    
    async def test_get_nonexistent_report(self, analytics_service):
        """Test getting a non-existent report"""
        report = analytics_service.get_report("nonexistent_id")
        assert report is None
    
    async def test_list_reports(self, analytics_service):
        """Test listing reports"""
        # Generate multiple reports
        report1 = await analytics_service.generate_report(
            ReportType.STORAGE_USAGE,
            TimeRange.DAY
        )
        report2 = await analytics_service.generate_report(
            ReportType.PERFORMANCE,
            TimeRange.WEEK
        )
        
        # List all reports
        reports = analytics_service.list_reports()
        
        assert len(reports) == 2
        report_ids = [r.report_id for r in reports]
        assert report1.report_id in report_ids
        assert report2.report_id in report_ids
    
    async def test_list_reports_filtered(self, analytics_service):
        """Test listing reports with filter"""
        # Generate reports of different types
        await analytics_service.generate_report(ReportType.STORAGE_USAGE, TimeRange.DAY)
        await analytics_service.generate_report(ReportType.PERFORMANCE, TimeRange.DAY)
        await analytics_service.generate_report(ReportType.STORAGE_USAGE, TimeRange.WEEK)
        
        # Filter by report type
        usage_reports = analytics_service.list_reports(
            report_type=ReportType.STORAGE_USAGE
        )
        
        assert len(usage_reports) == 2
        for report in usage_reports:
            assert report.report_type == ReportType.STORAGE_USAGE
    
    async def test_delete_report(self, analytics_service):
        """Test deleting a report"""
        # Generate a report
        report = await analytics_service.generate_report(
            ReportType.STORAGE_USAGE,
            TimeRange.DAY
        )
        
        # Delete the report
        success = analytics_service.delete_report(report.report_id)
        assert success is True
        
        # Verify it's deleted
        retrieved_report = analytics_service.get_report(report.report_id)
        assert retrieved_report is None
    
    async def test_delete_nonexistent_report(self, analytics_service):
        """Test deleting a non-existent report"""
        success = analytics_service.delete_report("nonexistent_id")
        assert success is False


class TestDataPersistence:
    """Test cases for data persistence"""
    
    async def test_save_and_load_metrics(self, analytics_service):
        """Test saving and loading metrics"""
        # Record some metrics
        analytics_service.record_metric("local", "upload_speed", 1024.0, "bps")
        analytics_service.record_metric("s3", "download_speed", 2048.0, "bps")
        
        # Save data
        await analytics_service._save_data()
        
        # Clear metrics and reload
        analytics_service._metrics.clear()
        await analytics_service._load_data()
        
        # Verify metrics were restored
        assert len(analytics_service._metrics) == 2
        
        metrics_by_driver = {m.driver_name: m for m in analytics_service._metrics}
        assert "local" in metrics_by_driver
        assert "s3" in metrics_by_driver
        
        assert metrics_by_driver["local"].metric_type == "upload_speed"
        assert metrics_by_driver["local"].value == 1024.0
    
    async def test_save_and_load_reports(self, analytics_service):
        """Test saving and loading reports"""
        # Generate reports
        report1 = await analytics_service.generate_report(
            ReportType.STORAGE_USAGE,
            TimeRange.DAY
        )
        report2 = await analytics_service.generate_report(
            ReportType.PERFORMANCE,
            TimeRange.WEEK
        )
        
        # Save data
        await analytics_service._save_data()
        
        # Clear reports and reload
        analytics_service._reports.clear()
        await analytics_service._load_data()
        
        # Verify reports were restored
        assert len(analytics_service._reports) == 2
        assert report1.report_id in analytics_service._reports
        assert report2.report_id in analytics_service._reports
        
        restored_report1 = analytics_service._reports[report1.report_id]
        assert restored_report1.report_type == ReportType.STORAGE_USAGE
        assert restored_report1.time_range == TimeRange.DAY


class TestAnalyticsIntegration:
    """Integration tests for analytics functionality"""
    
    async def test_full_analytics_workflow(self, analytics_service):
        """Test complete analytics workflow"""
        # 1. Record various metrics
        analytics_service.record_metric("local", "upload_count", 10, "count")
        analytics_service.record_metric("s3", "upload_count", 15, "count")
        analytics_service.record_operation_time("upload", 1.5, "local", True)
        analytics_service.record_operation_time("upload", 2.0, "s3", True)
        analytics_service.record_operation_time("download", 0.8, "local", False)
        
        # 2. Get usage statistics
        usage_stats = await analytics_service.get_usage_stats()
        assert usage_stats.total_objects > 0
        assert len(usage_stats.by_driver) == 3  # local, s3, azure
        
        # 3. Get performance statistics
        perf_stats = await analytics_service.get_performance_stats()
        assert perf_stats.total_requests > 0
        assert "upload" in perf_stats.by_operation
        
        # 4. Generate multiple types of reports
        usage_report = await analytics_service.generate_report(
            ReportType.STORAGE_USAGE,
            TimeRange.MONTH
        )
        perf_report = await analytics_service.generate_report(
            ReportType.PERFORMANCE,
            TimeRange.DAY
        )
        tier_report = await analytics_service.generate_report(
            ReportType.TIER_DISTRIBUTION,
            TimeRange.WEEK
        )
        
        # 5. Verify report generation
        assert usage_report.report_type == ReportType.STORAGE_USAGE
        assert perf_report.report_type == ReportType.PERFORMANCE
        assert tier_report.report_type == ReportType.TIER_DISTRIBUTION
        
        # 6. List all reports
        all_reports = analytics_service.list_reports()
        assert len(all_reports) == 3
        
        # 7. Filter reports by type
        usage_reports = analytics_service.list_reports(
            report_type=ReportType.STORAGE_USAGE
        )
        assert len(usage_reports) == 1
        assert usage_reports[0].report_id == usage_report.report_id
        
        # 8. Test data persistence
        await analytics_service._save_data()
        
        # Clear and reload
        analytics_service._metrics.clear()
        analytics_service._reports.clear()
        await analytics_service._load_data()
        
        # Verify data was restored
        assert len(analytics_service._metrics) > 0
        assert len(analytics_service._reports) == 3
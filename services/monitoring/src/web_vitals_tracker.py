"""
Web Core Vitals and user experience tracking for MAMS frontend.

Tracks LCP, FID, CLS, and other performance metrics to monitor
real user experience and optimize frontend performance.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
import aioredis
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

logger = logging.getLogger(__name__)


class VitalMetric(Enum):
    """Core Web Vitals and other performance metrics."""
    LCP = "largest_contentful_paint"      # Loading performance
    FID = "first_input_delay"             # Interactivity
    CLS = "cumulative_layout_shift"       # Visual stability
    FCP = "first_contentful_paint"        # Loading
    TTFB = "time_to_first_byte"          # Server response
    TTI = "time_to_interactive"           # Interactivity
    TBT = "total_blocking_time"           # Main thread blocking
    INP = "interaction_to_next_paint"     # Responsiveness


@dataclass
class WebVitalMeasurement:
    """Individual web vital measurement."""
    metric: VitalMetric
    value: float
    timestamp: datetime
    page_url: str
    user_agent: str
    connection_type: Optional[str] = None
    device_type: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'metric': self.metric.value,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'page_url': self.page_url,
            'user_agent': self.user_agent,
            'connection_type': self.connection_type,
            'device_type': self.device_type,
            'user_id': self.user_id,
            'session_id': self.session_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WebVitalMeasurement':
        return cls(
            metric=VitalMetric(data['metric']),
            value=data['value'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            page_url=data['page_url'],
            user_agent=data['user_agent'],
            connection_type=data.get('connection_type'),
            device_type=data.get('device_type'),
            user_id=data.get('user_id'),
            session_id=data.get('session_id')
        )


@dataclass
class PerformanceSummary:
    """Performance summary for a time period."""
    period_start: datetime
    period_end: datetime
    total_measurements: int
    metrics: Dict[str, Dict[str, float]]  # metric -> {p50, p75, p95, etc.}
    scores: Dict[str, str]  # metric -> good/needs_improvement/poor
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'total_measurements': self.total_measurements,
            'metrics': self.metrics,
            'scores': self.scores
        }


class WebVitalsTracker:
    """Tracks and analyzes Core Web Vitals and user experience metrics."""
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self.thresholds = self._get_web_vitals_thresholds()
        
    def _get_web_vitals_thresholds(self) -> Dict[VitalMetric, Dict[str, float]]:
        """Get Core Web Vitals thresholds from Google."""
        return {
            VitalMetric.LCP: {
                'good': 2500,      # ≤ 2.5s
                'poor': 4000       # > 4.0s
            },
            VitalMetric.FID: {
                'good': 100,       # ≤ 100ms
                'poor': 300        # > 300ms
            },
            VitalMetric.CLS: {
                'good': 0.1,       # ≤ 0.1
                'poor': 0.25       # > 0.25
            },
            VitalMetric.FCP: {
                'good': 1800,      # ≤ 1.8s
                'poor': 3000       # > 3.0s
            },
            VitalMetric.TTFB: {
                'good': 800,       # ≤ 800ms
                'poor': 1800       # > 1.8s
            },
            VitalMetric.TTI: {
                'good': 3800,      # ≤ 3.8s
                'poor': 7300       # > 7.3s
            },
            VitalMetric.TBT: {
                'good': 200,       # ≤ 200ms
                'poor': 600        # > 600ms
            },
            VitalMetric.INP: {
                'good': 200,       # ≤ 200ms
                'poor': 500        # > 500ms
            }
        }
    
    async def record_measurement(self, measurement: WebVitalMeasurement):
        """Record a web vital measurement."""
        # Store individual measurement
        await self.redis.lpush(
            f'web_vitals:{measurement.metric.value}',
            json.dumps(measurement.to_dict())
        )
        
        # Keep only recent measurements (last 7 days worth)
        await self.redis.ltrim(f'web_vitals:{measurement.metric.value}', 0, 9999)
        
        # Store by page for page-specific analysis
        page_key = self._get_page_key(measurement.page_url)
        await self.redis.lpush(
            f'web_vitals:pages:{page_key}:{measurement.metric.value}',
            json.dumps(measurement.to_dict())
        )
        await self.redis.ltrim(
            f'web_vitals:pages:{page_key}:{measurement.metric.value}', 0, 999
        )
        
        # Store by user for user experience tracking
        if measurement.user_id:
            await self.redis.lpush(
                f'web_vitals:users:{measurement.user_id}:{measurement.metric.value}',
                json.dumps(measurement.to_dict())
            )
            await self.redis.ltrim(
                f'web_vitals:users:{measurement.user_id}:{measurement.metric.value}', 0, 99
            )
            
        # Update real-time counters
        await self._update_real_time_stats(measurement)
        
    async def _update_real_time_stats(self, measurement: WebVitalMeasurement):
        """Update real-time statistics."""
        now = datetime.utcnow()
        hour_key = now.strftime('%Y-%m-%d-%H')
        
        # Increment measurement count
        await self.redis.incr(f'web_vitals:counts:{hour_key}:{measurement.metric.value}')
        await self.redis.expire(f'web_vitals:counts:{hour_key}:{measurement.metric.value}', 604800)  # 7 days
        
        # Update running averages (using sorted sets for efficient percentile calculations)
        score = measurement.value
        await self.redis.zadd(
            f'web_vitals:scores:{hour_key}:{measurement.metric.value}',
            {f'{measurement.timestamp.timestamp()}:{measurement.session_id}': score}
        )
        await self.redis.expire(f'web_vitals:scores:{hour_key}:{measurement.metric.value}', 604800)
        
    def _get_page_key(self, url: str) -> str:
        """Extract page key from URL."""
        # Remove query parameters and hash
        if '?' in url:
            url = url.split('?')[0]
        if '#' in url:
            url = url.split('#')[0]
            
        # Extract path
        if url.startswith('http'):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.path.strip('/') or 'home'
        
        return url.strip('/') or 'home'
    
    async def get_performance_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page_filter: Optional[str] = None,
        user_filter: Optional[str] = None
    ) -> PerformanceSummary:
        """Get performance summary for a time period."""
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(hours=24)  # Last 24 hours
            
        measurements_by_metric = {}
        total_measurements = 0
        
        for metric in VitalMetric:
            measurements = await self._get_measurements_for_period(
                metric, start_time, end_time, page_filter, user_filter
            )
            measurements_by_metric[metric] = measurements
            total_measurements += len(measurements)
            
        # Calculate statistics
        metrics_stats = {}
        scores = {}
        
        for metric, measurements in measurements_by_metric.items():
            if not measurements:
                continue
                
            values = [m.value for m in measurements]
            
            # Calculate percentiles
            if len(values) >= 10:  # Need minimum data points
                sorted_values = sorted(values)
                stats = {
                    'count': len(values),
                    'min': min(values),
                    'max': max(values),
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'p75': self._percentile(sorted_values, 75),
                    'p90': self._percentile(sorted_values, 90),
                    'p95': self._percentile(sorted_values, 95),
                    'p99': self._percentile(sorted_values, 99)
                }
                
                metrics_stats[metric.value] = stats
                
                # Calculate score based on p75 (Google's recommendation)
                p75_value = stats['p75']
                score = self._get_metric_score(metric, p75_value)
                scores[metric.value] = score
                
        return PerformanceSummary(
            period_start=start_time,
            period_end=end_time,
            total_measurements=total_measurements,
            metrics=metrics_stats,
            scores=scores
        )
    
    async def _get_measurements_for_period(
        self,
        metric: VitalMetric,
        start_time: datetime,
        end_time: datetime,
        page_filter: Optional[str] = None,
        user_filter: Optional[str] = None
    ) -> List[WebVitalMeasurement]:
        """Get measurements for a specific period and filters."""
        
        if user_filter:
            key = f'web_vitals:users:{user_filter}:{metric.value}'
        elif page_filter:
            page_key = self._get_page_key(page_filter)
            key = f'web_vitals:pages:{page_key}:{metric.value}'
        else:
            key = f'web_vitals:{metric.value}'
            
        # Get all measurements (this could be optimized with time-based indexing)
        raw_measurements = await self.redis.lrange(key, 0, -1)
        
        measurements = []
        for raw in raw_measurements:
            try:
                measurement = WebVitalMeasurement.from_dict(json.loads(raw))
                if start_time <= measurement.timestamp <= end_time:
                    measurements.append(measurement)
            except (json.JSONDecodeError, ValueError, KeyError):
                continue
                
        return measurements
    
    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not sorted_values:
            return 0.0
            
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def _get_metric_score(self, metric: VitalMetric, value: float) -> str:
        """Get performance score for a metric value."""
        thresholds = self.thresholds.get(metric)
        if not thresholds:
            return 'unknown'
            
        if value <= thresholds['good']:
            return 'good'
        elif value <= thresholds['poor']:
            return 'needs_improvement'
        else:
            return 'poor'
    
    async def get_real_time_dashboard(self) -> Dict[str, Any]:
        """Get real-time dashboard data."""
        now = datetime.utcnow()
        current_hour = now.strftime('%Y-%m-%d-%H')
        
        dashboard_data = {
            'timestamp': now.isoformat(),
            'current_hour_stats': {},
            'last_24h_summary': {},
            'top_pages': {},
            'alerts': []
        }
        
        # Current hour statistics
        for metric in VitalMetric:
            count_key = f'web_vitals:counts:{current_hour}:{metric.value}'
            scores_key = f'web_vitals:scores:{current_hour}:{metric.value}'
            
            count = await self.redis.get(count_key)
            count = int(count) if count else 0
            
            # Get percentiles from sorted set
            percentiles = {}
            if count > 0:
                total_scores = await self.redis.zcard(scores_key)
                if total_scores >= 10:
                    # Get percentile values
                    p50_idx = int(total_scores * 0.5)
                    p75_idx = int(total_scores * 0.75)
                    p95_idx = int(total_scores * 0.95)
                    
                    p50_data = await self.redis.zrange(scores_key, p50_idx, p50_idx, withscores=True)
                    p75_data = await self.redis.zrange(scores_key, p75_idx, p75_idx, withscores=True)
                    p95_data = await self.redis.zrange(scores_key, p95_idx, p95_idx, withscores=True)
                    
                    percentiles = {
                        'p50': p50_data[0][1] if p50_data else 0,
                        'p75': p75_data[0][1] if p75_data else 0,
                        'p95': p95_data[0][1] if p95_data else 0
                    }
            
            dashboard_data['current_hour_stats'][metric.value] = {
                'count': count,
                'percentiles': percentiles,
                'score': self._get_metric_score(metric, percentiles.get('p75', 0)) if percentiles else 'unknown'
            }
        
        # Last 24 hours summary
        summary_24h = await self.get_performance_summary(
            start_time=now - timedelta(hours=24),
            end_time=now
        )
        dashboard_data['last_24h_summary'] = summary_24h.to_dict()
        
        # Top performing/problematic pages
        dashboard_data['top_pages'] = await self._get_top_pages_analysis()
        
        # Performance alerts
        dashboard_data['alerts'] = await self._generate_performance_alerts()
        
        return dashboard_data
    
    async def _get_top_pages_analysis(self) -> Dict[str, Any]:
        """Analyze performance by page."""
        # Get all page keys
        page_keys = set()
        for metric in VitalMetric:
            keys = await self.redis.keys(f'web_vitals:pages:*:{metric.value}')
            for key in keys:
                page_key = key.decode().split(':')[2]  # Extract page key
                page_keys.add(page_key)
        
        page_analysis = {}
        for page_key in list(page_keys)[:20]:  # Limit to top 20 pages
            page_summary = await self.get_performance_summary(
                start_time=datetime.utcnow() - timedelta(hours=24),
                end_time=datetime.utcnow(),
                page_filter=f'/{page_key}'
            )
            
            if page_summary.total_measurements > 10:  # Only include pages with sufficient data
                page_analysis[page_key] = page_summary.to_dict()
        
        return page_analysis
    
    async def _generate_performance_alerts(self) -> List[Dict[str, Any]]:
        """Generate performance alerts based on current metrics."""
        alerts = []
        now = datetime.utcnow()
        current_hour = now.strftime('%Y-%m-%d-%H')
        
        for metric in VitalMetric:
            scores_key = f'web_vitals:scores:{current_hour}:{metric.value}'
            total_scores = await self.redis.zcard(scores_key)
            
            if total_scores >= 10:  # Need minimum data
                # Get p75 value
                p75_idx = int(total_scores * 0.75)
                p75_data = await self.redis.zrange(scores_key, p75_idx, p75_idx, withscores=True)
                
                if p75_data:
                    p75_value = p75_data[0][1]
                    score = self._get_metric_score(metric, p75_value)
                    
                    if score == 'poor':
                        alerts.append({
                            'type': 'performance_degradation',
                            'severity': 'high',
                            'metric': metric.value,
                            'current_value': p75_value,
                            'threshold': self.thresholds[metric]['poor'],
                            'message': f'{metric.value} is performing poorly (p75: {p75_value:.1f})',
                            'timestamp': now.isoformat()
                        })
                    elif score == 'needs_improvement':
                        alerts.append({
                            'type': 'performance_warning',
                            'severity': 'medium',
                            'metric': metric.value,
                            'current_value': p75_value,
                            'threshold': self.thresholds[metric]['good'],
                            'message': f'{metric.value} needs improvement (p75: {p75_value:.1f})',
                            'timestamp': now.isoformat()
                        })
        
        return alerts
    
    async def get_user_experience_insights(self, user_id: str) -> Dict[str, Any]:
        """Get user-specific performance insights."""
        user_data = {
            'user_id': user_id,
            'measurements_by_metric': {},
            'overall_score': 'unknown',
            'problem_pages': [],
            'recommendations': []
        }
        
        # Get user measurements
        total_measurements = 0
        good_scores = 0
        
        for metric in VitalMetric:
            measurements = await self._get_measurements_for_period(
                metric,
                datetime.utcnow() - timedelta(days=7),  # Last 7 days
                datetime.utcnow(),
                user_filter=user_id
            )
            
            if measurements:
                values = [m.value for m in measurements]
                p75_value = self._percentile(sorted(values), 75)
                score = self._get_metric_score(metric, p75_value)
                
                user_data['measurements_by_metric'][metric.value] = {
                    'count': len(measurements),
                    'p75': p75_value,
                    'score': score
                }
                
                total_measurements += len(measurements)
                if score == 'good':
                    good_scores += 1
        
        # Calculate overall score
        if total_measurements > 0:
            core_vitals = [VitalMetric.LCP, VitalMetric.FID, VitalMetric.CLS]
            core_vital_scores = [
                user_data['measurements_by_metric'].get(metric.value, {}).get('score', 'poor')
                for metric in core_vitals
                if metric.value in user_data['measurements_by_metric']
            ]
            
            good_core_vitals = sum(1 for score in core_vital_scores if score == 'good')
            
            if good_core_vitals == len(core_vital_scores) and len(core_vital_scores) >= 2:
                user_data['overall_score'] = 'good'
            elif good_core_vitals >= len(core_vital_scores) * 0.5:
                user_data['overall_score'] = 'needs_improvement'
            else:
                user_data['overall_score'] = 'poor'
        
        return user_data


# Integration with FastAPI
class WebVitalsAPI:
    """FastAPI integration for web vitals tracking."""
    
    def __init__(self, tracker: WebVitalsTracker):
        self.tracker = tracker
    
    async def record_vitals(self, vitals_data: Dict[str, Any]) -> Dict[str, str]:
        """API endpoint to record web vitals."""
        try:
            # Parse and validate measurement data
            measurement = WebVitalMeasurement(
                metric=VitalMetric(vitals_data['metric']),
                value=float(vitals_data['value']),
                timestamp=datetime.utcnow(),
                page_url=vitals_data['page_url'],
                user_agent=vitals_data.get('user_agent', ''),
                connection_type=vitals_data.get('connection_type'),
                device_type=vitals_data.get('device_type'),
                user_id=vitals_data.get('user_id'),
                session_id=vitals_data.get('session_id')
            )
            
            await self.tracker.record_measurement(measurement)
            
            return {'status': 'success', 'message': 'Measurement recorded'}
            
        except Exception as e:
            logger.error(f"Failed to record web vital: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def get_dashboard(self) -> Dict[str, Any]:
        """API endpoint for dashboard data."""
        return await self.tracker.get_real_time_dashboard()
    
    async def get_performance_report(
        self,
        hours: int = 24,
        page: Optional[str] = None,
        user: Optional[str] = None
    ) -> Dict[str, Any]:
        """API endpoint for performance reports."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        summary = await self.tracker.get_performance_summary(
            start_time=start_time,
            end_time=end_time,
            page_filter=page,
            user_filter=user
        )
        
        return summary.to_dict()


# Example usage
async def main():
    """Example usage of web vitals tracker."""
    redis = aioredis.from_url("redis://localhost:6379")
    tracker = WebVitalsTracker(redis)
    
    # Simulate some measurements
    test_measurements = [
        WebVitalMeasurement(
            metric=VitalMetric.LCP,
            value=2100.0,  # Good LCP
            timestamp=datetime.utcnow(),
            page_url="/dashboard",
            user_agent="Chrome/91.0",
            session_id="session_123"
        ),
        WebVitalMeasurement(
            metric=VitalMetric.FID,
            value=85.0,  # Good FID
            timestamp=datetime.utcnow(),
            page_url="/dashboard",
            user_agent="Chrome/91.0",
            session_id="session_123"
        ),
        WebVitalMeasurement(
            metric=VitalMetric.CLS,
            value=0.05,  # Good CLS
            timestamp=datetime.utcnow(),
            page_url="/dashboard",
            user_agent="Chrome/91.0",
            session_id="session_123"
        )
    ]
    
    # Record measurements
    for measurement in test_measurements:
        await tracker.record_measurement(measurement)
    
    # Get dashboard data
    dashboard = await tracker.get_real_time_dashboard()
    print("Dashboard data:", json.dumps(dashboard, indent=2, default=str))
    
    await redis.close()


if __name__ == "__main__":
    asyncio.run(main())
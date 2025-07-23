"""
Models module for CDN service
"""

from .database import (
    CDNDistribution,
    CDNMetric,
    CDNPurgeRequest,
    CDNOptimization,
    CDNAlert,
    CDNAccessLog,
    CDNCostTracking,
    CDNProviderConfig,
    User
)

from .schemas import (
    CDNProvider,
    CDNOrigin,
    CacheRule,
    SecurityPolicy,
    GeoRestriction,
    PurgeRequest,
    PrefetchRequest,
    CDNMetrics,
    BandwidthUsage,
    EdgeLocation,
    ContentOptimization,
    ImageOptimizationSettings,
    VideoOptimizationSettings,
    CDNHealthCheck,
    CDNAlert as CDNAlertSchema,
    CacheStatus,
    CDNCostEstimate
)

__all__ = [
    # Database models
    "CDNDistribution",
    "CDNMetric",
    "CDNPurgeRequest",
    "CDNOptimization",
    "CDNAlert",
    "CDNAccessLog",
    "CDNCostTracking",
    "CDNProviderConfig",
    "User",
    # Schemas
    "CDNProvider",
    "CDNOrigin",
    "CacheRule",
    "SecurityPolicy",
    "GeoRestriction",
    "PurgeRequest",
    "PrefetchRequest",
    "CDNMetrics",
    "BandwidthUsage",
    "EdgeLocation",
    "ContentOptimization",
    "ImageOptimizationSettings",
    "VideoOptimizationSettings",
    "CDNHealthCheck",
    "CDNAlertSchema",
    "CacheStatus",
    "CDNCostEstimate"
]
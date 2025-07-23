"""
Pydantic models for CDN service
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, validator, HttpUrl


class CDNProviderType(str, Enum):
    CLOUDFRONT = "cloudfront"
    CLOUDFLARE = "cloudflare"
    AKAMAI = "akamai"
    FASTLY = "fastly"
    AZURE_CDN = "azure_cdn"
    CUSTOM = "custom"


class CacheStrategy(str, Enum):
    CACHE_EVERYTHING = "cache_everything"
    CACHE_STATIC = "cache_static"
    CACHE_DYNAMIC = "cache_dynamic"
    BYPASS_CACHE = "bypass_cache"
    CUSTOM_RULES = "custom_rules"


class OptimizationType(str, Enum):
    IMAGE_OPTIMIZATION = "image_optimization"
    VIDEO_TRANSCODING = "video_transcoding"
    COMPRESSION = "compression"
    MINIFICATION = "minification"
    WEBP_CONVERSION = "webp_conversion"


class HTTPMethod(str, Enum):
    GET = "GET"
    HEAD = "HEAD"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"


class CDNProvider(BaseModel):
    """CDN provider configuration"""
    provider_id: str
    provider_type: CDNProviderType
    name: str
    enabled: bool = True
    configuration: Dict[str, Any] = {}
    api_endpoint: Optional[str] = None
    regions_available: List[str] = []
    features_supported: List[str] = []
    
    class Config:
        use_enum_values = True


class CDNOrigin(BaseModel):
    """Origin server configuration"""
    origin_id: str
    domain_name: str
    origin_path: Optional[str] = ""
    protocol: str = "https"
    port: int = 443
    custom_headers: Dict[str, str] = {}
    connection_timeout: int = Field(default=10, ge=1, le=60)
    connection_attempts: int = Field(default=3, ge=1, le=5)
    origin_shield_enabled: bool = False
    origin_shield_region: Optional[str] = None


class CacheRule(BaseModel):
    """Cache behavior rule"""
    rule_id: Optional[str] = None
    path_pattern: str
    origin_index: int = 0
    cache_enabled: bool = True
    cache_strategy: CacheStrategy = CacheStrategy.CACHE_STATIC
    allowed_methods: List[HTTPMethod] = [HTTPMethod.GET, HTTPMethod.HEAD]
    cached_methods: List[HTTPMethod] = [HTTPMethod.GET, HTTPMethod.HEAD]
    default_ttl: int = Field(default=86400, ge=0)  # 24 hours
    max_ttl: int = Field(default=31536000, ge=0)  # 1 year
    min_ttl: int = Field(default=0, ge=0)
    compress: bool = True
    query_string_behavior: str = "none"  # none, whitelist, all
    query_string_keys: List[str] = []
    headers_behavior: str = "none"  # none, whitelist, all
    headers_whitelist: List[str] = []
    cookies_behavior: str = "none"  # none, whitelist, all
    cookies_whitelist: List[str] = []
    
    @validator("max_ttl")
    def validate_ttl_order(cls, v, values):
        if "min_ttl" in values and v < values["min_ttl"]:
            raise ValueError("max_ttl must be greater than or equal to min_ttl")
        return v


class GeoRestriction(BaseModel):
    """Geographic restriction configuration"""
    restriction_type: str = "whitelist"  # whitelist or blacklist
    locations: List[str] = []  # ISO 3166-1 alpha-2 country codes


class SecurityPolicy(BaseModel):
    """Security policy configuration"""
    minimum_protocol_version: str = "TLSv1.2"
    ssl_protocols: List[str] = ["TLSv1.2", "TLSv1.3"]
    waf_enabled: bool = False
    waf_rule_set: Optional[str] = None
    geo_restriction: Optional[GeoRestriction] = None
    signed_urls_enabled: bool = False
    signed_cookies_enabled: bool = False
    ip_whitelist: List[str] = []
    ip_blacklist: List[str] = []
    custom_error_pages: Dict[int, str] = {}  # status_code -> error_page_url


class CDNDistribution(BaseModel):
    """CDN distribution configuration"""
    distribution_id: str
    provider_id: str
    provider_distribution_id: Optional[str] = None
    name: str
    status: str = "creating"  # creating, deploying, deployed, updating, deleting
    enabled: bool = True
    domain_name: Optional[str] = None
    custom_domain: Optional[str] = None
    cname_records: List[str] = []
    certificate_arn: Optional[str] = None
    origins: List[CDNOrigin]
    cache_rules: List[CacheRule]
    security_policy: SecurityPolicy = Field(default_factory=SecurityPolicy)
    logging_enabled: bool = False
    logging_bucket: Optional[str] = None
    logging_prefix: Optional[str] = None
    realtime_logs_enabled: bool = False
    realtime_logs_config: Optional[str] = None
    price_class: str = "all"  # all, us_eu, us_eu_asia
    http_version: str = "http2and3"
    ipv6_enabled: bool = True
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class EdgeLocation(BaseModel):
    """CDN edge location"""
    location_id: str
    name: str
    region: str
    country: str
    city: Optional[str] = None
    latitude: float
    longitude: float
    status: str = "active"  # active, maintenance, inactive
    capacity_gbps: Optional[float] = None
    pop_code: Optional[str] = None  # Point of Presence code


class PurgeRequest(BaseModel):
    """Cache purge request"""
    request_id: str
    distribution_id: str
    paths: List[str] = []
    tags: List[str] = []
    purge_all: bool = False
    status: str = "pending"  # pending, in_progress, completed, failed
    provider_request_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    @validator("paths")
    def validate_paths(cls, v):
        # Ensure paths start with /
        return [path if path.startswith("/") else f"/{path}" for path in v]


class PrefetchRequest(BaseModel):
    """Content prefetch request"""
    request_id: str
    distribution_id: str
    urls: List[str]
    priority: str = "normal"  # low, normal, high
    status: str = "pending"  # pending, in_progress, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    urls_processed: int = 0
    urls_failed: int = 0
    error_messages: List[str] = []


class CDNMetrics(BaseModel):
    """CDN performance metrics"""
    distribution_id: str
    period_start: datetime
    period_end: datetime
    requests_total: int = 0
    requests_cached: int = 0
    cache_hit_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    bandwidth_bytes: int = 0
    bandwidth_cached_bytes: int = 0
    unique_visitors: int = 0
    error_4xx_count: int = 0
    error_5xx_count: int = 0
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    avg_response_time_ms: float = 0.0
    avg_origin_response_time_ms: float = 0.0
    
    @property
    def cache_bandwidth_ratio(self) -> float:
        if self.bandwidth_bytes == 0:
            return 0.0
        return self.bandwidth_cached_bytes / self.bandwidth_bytes


class BandwidthUsage(BaseModel):
    """Bandwidth usage data"""
    timestamp: datetime
    bytes_in: int = 0
    bytes_out: int = 0
    requests: int = 0
    unique_ips: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    
    @property
    def total_bytes(self) -> int:
        return self.bytes_in + self.bytes_out
    
    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total


class CacheStatus(BaseModel):
    """Cache status information"""
    distribution_id: str
    total_objects: int = 0
    total_size_bytes: int = 0
    hot_objects: int = 0
    warm_objects: int = 0
    cold_objects: int = 0
    eviction_rate: float = 0.0
    fill_rate: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ContentOptimization(BaseModel):
    """Content optimization configuration"""
    optimization_id: str
    distribution_id: str
    optimization_type: OptimizationType
    enabled: bool = True
    settings: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class ImageOptimizationSettings(BaseModel):
    """Image optimization settings"""
    auto_webp: bool = True
    auto_avif: bool = False
    quality: int = Field(default=85, ge=1, le=100)
    progressive: bool = True
    strip_metadata: bool = True
    resize_enabled: bool = True
    max_width: Optional[int] = 4096
    max_height: Optional[int] = 4096
    responsive_sizes: List[int] = [320, 640, 1024, 1920]
    blur_placeholder: bool = True
    lazy_loading: bool = True


class VideoOptimizationSettings(BaseModel):
    """Video optimization settings"""
    adaptive_bitrate: bool = True
    transcoding_enabled: bool = True
    output_formats: List[str] = ["mp4", "webm"]
    quality_levels: List[str] = ["360p", "720p", "1080p"]
    max_bitrate_mbps: float = 10.0
    audio_normalization: bool = True
    thumbnail_generation: bool = True
    thumbnail_interval_seconds: int = 10


class CDNHealthCheck(BaseModel):
    """CDN health check configuration"""
    check_id: str
    distribution_id: str
    check_type: str = "http"  # http, https, tcp
    check_path: str = "/health"
    check_interval_seconds: int = Field(default=30, ge=10, le=300)
    timeout_seconds: int = Field(default=10, ge=1, le=60)
    healthy_threshold: int = Field(default=3, ge=1, le=10)
    unhealthy_threshold: int = Field(default=3, ge=1, le=10)
    expected_status_codes: List[int] = [200]
    enabled: bool = True


class CDNAlert(BaseModel):
    """CDN alert configuration"""
    alert_id: str
    distribution_id: str
    alert_type: str  # error_rate, bandwidth, cache_hit_rate, availability
    threshold_value: float
    comparison_operator: str = "greater_than"  # greater_than, less_than, equal
    evaluation_periods: int = Field(default=3, ge=1, le=10)
    period_seconds: int = Field(default=300, ge=60, le=3600)
    enabled: bool = True
    notification_channels: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CDNAccessLog(BaseModel):
    """CDN access log entry"""
    timestamp: datetime
    client_ip: str
    method: str
    uri: str
    status_code: int
    bytes_sent: int
    referer: Optional[str] = None
    user_agent: Optional[str] = None
    edge_location: str
    cache_status: str  # hit, miss, expired, error
    response_time_ms: float
    ssl_protocol: Optional[str] = None
    ssl_cipher: Optional[str] = None
    edge_result_type: str  # hit, miss, error, redirect


class CDNCostEstimate(BaseModel):
    """CDN cost estimate"""
    distribution_id: str
    period_start: datetime
    period_end: datetime
    data_transfer_gb: float
    data_transfer_cost: float
    requests_millions: float
    requests_cost: float
    invalidation_requests: int
    invalidation_cost: float
    field_level_encryption_requests: int
    field_level_encryption_cost: float
    total_cost: float
    currency: str = "USD"
    
    @property
    def cost_per_gb(self) -> float:
        if self.data_transfer_gb == 0:
            return 0.0
        return self.total_cost / self.data_transfer_gb
"""
Pydantic schemas for WAF Protection Service
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class WAFMode(str, Enum):
    """WAF operation modes"""
    OFF = "off"
    MONITORING = "monitoring"
    BLOCKING = "blocking"


class ThreatLevel(str, Enum):
    """Threat severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RuleAction(str, Enum):
    """Rule action types"""
    ALLOW = "allow"
    BLOCK = "block"
    LOG = "log"
    RATE_LIMIT = "rate_limit"
    CHALLENGE = "challenge"


class RuleTarget(str, Enum):
    """Rule target types"""
    URL = "url"
    HEADER = "header"
    BODY = "body"
    IP = "ip"
    USER_AGENT = "user_agent"
    METHOD = "method"
    QUERY_STRING = "query_string"
    COOKIE = "cookie"


class OperatorType(str, Enum):
    """Rule operator types"""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    LENGTH_GT = "length_gt"
    LENGTH_LT = "length_lt"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    IP_IN_RANGE = "ip_in_range"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"


# Request schemas
class WAFAnalysisRequest(BaseModel):
    """Request for WAF analysis"""
    ip: str = Field(..., description="Client IP address")
    method: str = Field(..., description="HTTP method")
    url: str = Field(..., description="Request URL")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP headers")
    body: Optional[str] = Field(default=None, description="Request body")
    user_agent: Optional[str] = Field(default=None, description="User agent")
    referer: Optional[str] = Field(default=None, description="Referer header")


class RuleConditionCreate(BaseModel):
    """Rule condition creation schema"""
    target: RuleTarget = Field(..., description="Target to evaluate")
    operator: OperatorType = Field(..., description="Comparison operator")
    value: Union[str, int, float, List[str]] = Field(..., description="Expected value")
    header_name: Optional[str] = Field(default=None, description="Header name for header targets")
    case_sensitive: bool = Field(default=False, description="Case sensitive comparison")


class CustomRuleCreate(BaseModel):
    """Custom rule creation schema"""
    id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    enabled: bool = Field(default=True, description="Rule enabled status")
    action: RuleAction = Field(..., description="Action to take when rule matches")
    conditions: List[RuleConditionCreate] = Field(..., description="Rule conditions")
    priority: int = Field(default=100, description="Rule priority (lower = higher priority)")
    threat_level: ThreatLevel = Field(default=ThreatLevel.MEDIUM, description="Threat level")
    score: int = Field(default=50, ge=0, le=100, description="Threat score (0-100)")
    rate_limit_window: Optional[int] = Field(default=None, description="Rate limit window in seconds")
    rate_limit_threshold: Optional[int] = Field(default=None, description="Rate limit threshold")
    tags: List[str] = Field(default_factory=list, description="Rule tags")


class CustomRuleUpdate(BaseModel):
    """Custom rule update schema"""
    name: Optional[str] = Field(default=None, description="Rule name")
    description: Optional[str] = Field(default=None, description="Rule description")
    enabled: Optional[bool] = Field(default=None, description="Rule enabled status")
    action: Optional[RuleAction] = Field(default=None, description="Action to take when rule matches")
    conditions: Optional[List[RuleConditionCreate]] = Field(default=None, description="Rule conditions")
    priority: Optional[int] = Field(default=None, description="Rule priority")
    threat_level: Optional[ThreatLevel] = Field(default=None, description="Threat level")
    score: Optional[int] = Field(default=None, ge=0, le=100, description="Threat score")
    rate_limit_window: Optional[int] = Field(default=None, description="Rate limit window in seconds")
    rate_limit_threshold: Optional[int] = Field(default=None, description="Rate limit threshold")
    tags: Optional[List[str]] = Field(default=None, description="Rule tags")


# Response schemas
class RuleConditionResponse(BaseModel):
    """Rule condition response schema"""
    target: RuleTarget = Field(..., description="Target to evaluate")
    operator: OperatorType = Field(..., description="Comparison operator")
    value: Union[str, int, float, List[str]] = Field(..., description="Expected value")
    header_name: Optional[str] = Field(default=None, description="Header name for header targets")
    case_sensitive: bool = Field(..., description="Case sensitive comparison")


class CustomRuleResponse(BaseModel):
    """Custom rule response schema"""
    id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    enabled: bool = Field(..., description="Rule enabled status")
    action: RuleAction = Field(..., description="Action to take when rule matches")
    conditions: List[RuleConditionResponse] = Field(..., description="Rule conditions")
    priority: int = Field(..., description="Rule priority")
    threat_level: ThreatLevel = Field(..., description="Threat level")
    score: int = Field(..., description="Threat score")
    rate_limit_window: Optional[int] = Field(default=None, description="Rate limit window in seconds")
    rate_limit_threshold: Optional[int] = Field(default=None, description="Rate limit threshold")
    tags: List[str] = Field(..., description="Rule tags")
    created_at: datetime = Field(..., description="Rule creation timestamp")
    updated_at: datetime = Field(..., description="Rule last update timestamp")


class WAFAnalysisResponse(BaseModel):
    """WAF analysis result"""
    allowed: bool = Field(..., description="Whether request is allowed")
    rule_triggered: Optional[str] = Field(default=None, description="Rule that triggered")
    threat_level: ThreatLevel = Field(..., description="Detected threat level")
    block_reason: Optional[str] = Field(default=None, description="Reason for blocking")
    score: int = Field(..., description="Threat score (0-100)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional analysis metadata")
    processing_time_ms: float = Field(..., description="Analysis processing time")


class WAFStatsResponse(BaseModel):
    """WAF statistics response"""
    requests_processed: int = Field(..., description="Total requests processed")
    requests_blocked: int = Field(..., description="Total requests blocked")
    block_rate: float = Field(..., description="Block rate percentage")
    sql_injection_attempts: int = Field(..., description="SQL injection attempts detected")
    xss_attempts: int = Field(..., description="XSS attempts detected")
    bot_requests: int = Field(..., description="Bot requests detected")
    rate_limited: int = Field(..., description="Requests rate limited")
    geo_blocked: int = Field(..., description="Requests geo-blocked")
    top_blocked_ips: List[Dict[str, Any]] = Field(default_factory=list, description="Top blocked IPs")
    top_triggered_rules: List[Dict[str, Any]] = Field(default_factory=list, description="Top triggered rules")


class RuleStatsResponse(BaseModel):
    """Rule statistics response"""
    total_rules: int = Field(..., description="Total number of rules")
    enabled_rules: int = Field(..., description="Number of enabled rules")
    disabled_rules: int = Field(..., description="Number of disabled rules")
    rule_stats: Dict[str, Dict[str, int]] = Field(..., description="Individual rule statistics")


class BlockedRequest(BaseModel):
    """Blocked request information"""
    id: str = Field(..., description="Request identifier")
    ip: str = Field(..., description="Client IP address")
    method: str = Field(..., description="HTTP method")
    url: str = Field(..., description="Request URL")
    user_agent: Optional[str] = Field(default=None, description="User agent")
    rule_triggered: str = Field(..., description="Rule that triggered the block")
    threat_level: ThreatLevel = Field(..., description="Threat level")
    block_reason: str = Field(..., description="Reason for blocking")
    score: int = Field(..., description="Threat score")
    timestamp: datetime = Field(..., description="Block timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class IPWhitelistRequest(BaseModel):
    """IP whitelist management request"""
    ips: List[str] = Field(..., description="List of IP addresses or CIDR blocks")
    description: Optional[str] = Field(default=None, description="Description for the whitelist entry")


class IPBlacklistRequest(BaseModel):
    """IP blacklist management request"""
    ips: List[str] = Field(..., description="List of IP addresses or CIDR blocks")
    description: Optional[str] = Field(default=None, description="Description for the blacklist entry")
    duration: Optional[int] = Field(default=None, description="Duration in seconds (None for permanent)")


class GeoBlockingConfig(BaseModel):
    """Geographic blocking configuration"""
    enabled: bool = Field(..., description="Enable geographic blocking")
    blocked_countries: List[str] = Field(default_factory=list, description="Blocked country codes")
    allowed_countries: List[str] = Field(default_factory=list, description="Allowed country codes")


class RateLimitConfig(BaseModel):
    """Rate limiting configuration"""
    enabled: bool = Field(..., description="Enable rate limiting")
    requests_per_minute: int = Field(default=60, description="Requests per minute limit")
    burst_limit: int = Field(default=10, description="Burst limit")
    block_duration: int = Field(default=300, description="Block duration in seconds")


class WAFConfig(BaseModel):
    """WAF configuration"""
    enabled: bool = Field(..., description="Enable WAF")
    mode: WAFMode = Field(..., description="WAF operation mode")
    sql_injection_protection: bool = Field(default=True, description="Enable SQL injection protection")
    xss_protection: bool = Field(default=True, description="Enable XSS protection")
    bot_protection: bool = Field(default=True, description="Enable bot protection")
    rate_limiting: RateLimitConfig = Field(..., description="Rate limiting configuration")
    geo_blocking: GeoBlockingConfig = Field(..., description="Geographic blocking configuration")
    custom_rules_enabled: bool = Field(default=True, description="Enable custom rules")


class RuleTestRequest(BaseModel):
    """Rule testing request"""
    rule_id: str = Field(..., description="Rule ID to test")
    test_request: WAFAnalysisRequest = Field(..., description="Test request data")


class RuleTestResponse(BaseModel):
    """Rule testing response"""
    rule_id: str = Field(..., description="Rule ID tested")
    matched: bool = Field(..., description="Whether rule matched")
    conditions_results: List[Dict[str, Any]] = Field(..., description="Individual condition results")
    execution_time_ms: float = Field(..., description="Rule execution time")


class BulkRuleOperation(BaseModel):
    """Bulk rule operations"""
    rule_ids: List[str] = Field(..., description="List of rule IDs")
    operation: str = Field(..., description="Operation to perform (enable, disable, delete)")


class AlertConfig(BaseModel):
    """Alert configuration"""
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL for alerts")
    email: Optional[str] = Field(default=None, description="Email for alerts")
    threshold: int = Field(default=10, description="Alert threshold per minute")
    enabled: bool = Field(default=True, description="Enable alerting")


class HealthStatus(BaseModel):
    """Service health status"""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str = Field(..., description="Service version")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    database_connected: bool = Field(..., description="Database connection status")
    redis_connected: bool = Field(..., description="Redis connection status")
    waf_engine_status: str = Field(..., description="WAF engine status")
    rules_loaded: int = Field(..., description="Number of rules loaded")


# List responses with pagination
class RuleListResponse(BaseModel):
    """List of rules with pagination"""
    rules: List[CustomRuleResponse] = Field(..., description="List of rules")
    total: int = Field(..., description="Total number of rules")
    page: int = Field(default=1, description="Current page")
    limit: int = Field(default=20, description="Page size")


class BlockedRequestListResponse(BaseModel):
    """List of blocked requests with pagination"""
    blocked_requests: List[BlockedRequest] = Field(..., description="List of blocked requests")
    total: int = Field(..., description="Total number of blocked requests")
    page: int = Field(default=1, description="Current page")
    limit: int = Field(default=20, description="Page size")


# Import/Export schemas
class RuleExportResponse(BaseModel):
    """Rule export response"""
    rules: List[CustomRuleResponse] = Field(..., description="Exported rules")
    exported_at: datetime = Field(..., description="Export timestamp")
    format: str = Field(..., description="Export format")


class RuleImportRequest(BaseModel):
    """Rule import request"""
    rules: List[CustomRuleCreate] = Field(..., description="Rules to import")
    overwrite_existing: bool = Field(default=False, description="Overwrite existing rules")


class RuleImportResponse(BaseModel):
    """Rule import response"""
    imported_count: int = Field(..., description="Number of rules imported")
    skipped_count: int = Field(..., description="Number of rules skipped")
    errors: List[str] = Field(default_factory=list, description="Import errors")
    imported_at: datetime = Field(..., description="Import timestamp")
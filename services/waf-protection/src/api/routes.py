"""
API routes for WAF Protection Service
"""

import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..core.config import get_settings, Settings
from ..core.waf_engine import WAFEngine, WAFRequest
from ..core.rule_engine import RuleEngine, DEFAULT_RULES
from ..models.schemas import (
    WAFAnalysisRequest, WAFAnalysisResponse, CustomRuleCreate, CustomRuleUpdate,
    CustomRuleResponse, WAFStatsResponse, RuleStatsResponse, BlockedRequest,
    RuleListResponse, BlockedRequestListResponse, WAFConfig, RuleTestRequest,
    RuleTestResponse, BulkRuleOperation, IPWhitelistRequest, IPBlacklistRequest,
    GeoBlockingConfig, RateLimitConfig, AlertConfig, HealthStatus
)
from ..services.database import get_db
from ..services.waf_service import WAFService

logger = structlog.get_logger()

# Initialize routers
waf_router = APIRouter(prefix="/api/v1/waf", tags=["WAF Protection"])
rules_router = APIRouter(prefix="/api/v1/rules", tags=["WAF Rules"])
config_router = APIRouter(prefix="/api/v1/config", tags=["WAF Configuration"])
stats_router = APIRouter(prefix="/api/v1/stats", tags=["WAF Statistics"])
health_router = APIRouter(prefix="/health", tags=["Health"])

# Global WAF engine and rule engine instances
waf_engine: Optional[WAFEngine] = None
rule_engine: Optional[RuleEngine] = None


def get_waf_engine(settings: Settings = Depends(get_settings)) -> WAFEngine:
    """Get WAF engine instance"""
    global waf_engine
    if waf_engine is None:
        # Initialize with Redis if available
        redis_client = None  # Will be initialized with actual Redis connection
        waf_engine = WAFEngine(settings, redis_client)
    return waf_engine


def get_rule_engine(settings: Settings = Depends(get_settings)) -> RuleEngine:
    """Get rule engine instance"""
    global rule_engine
    if rule_engine is None:
        rule_engine = RuleEngine()
        # Load default rules
        rule_engine.load_rules_from_dict(DEFAULT_RULES)
        # Try to load custom rules file
        if settings.custom_rules_enabled:
            rule_engine.load_rules_from_file(settings.custom_rules_file)
    return rule_engine


# WAF Analysis endpoints
@waf_router.post("/analyze", response_model=WAFAnalysisResponse)
async def analyze_request(
    request: WAFAnalysisRequest,
    waf_engine: WAFEngine = Depends(get_waf_engine),
    rule_engine: RuleEngine = Depends(get_rule_engine),
    waf_service: WAFService = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Analyze a request for threats"""
    start_time = time.time()
    
    try:
        # Convert to WAF request
        waf_request = WAFRequest(
            ip=request.ip,
            method=request.method,
            url=request.url,
            headers=request.headers,
            body=request.body,
            user_agent=request.user_agent,
            referer=request.referer
        )
        
        # Run WAF analysis
        result = await waf_engine.analyze_request(waf_request)
        
        # Check custom rules
        matched_rules = rule_engine.evaluate_request(waf_request)
        if matched_rules:
            # Use the highest priority rule
            top_rule = matched_rules[0]
            if top_rule.action.value in ["block", "challenge"]:
                result.allowed = False
                result.rule_triggered = top_rule.id
                result.threat_level = top_rule.threat_level
                result.block_reason = f"Custom rule triggered: {top_rule.name}"
                result.score = max(result.score, top_rule.score)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Log blocked request
        if not result.allowed:
            await waf_service.log_blocked_request(
                db, waf_request, result, processing_time
            )
        
        return WAFAnalysisResponse(
            allowed=result.allowed,
            rule_triggered=result.rule_triggered,
            threat_level=result.threat_level,
            block_reason=result.block_reason,
            score=result.score,
            metadata=result.metadata,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error("WAF analysis failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"WAF analysis failed: {str(e)}"
        )


@waf_router.get("/status", response_model=dict)
async def get_waf_status(
    waf_engine: WAFEngine = Depends(get_waf_engine),
    rule_engine: RuleEngine = Depends(get_rule_engine),
    settings: Settings = Depends(get_settings)
):
    """Get WAF status and configuration"""
    return {
        "enabled": settings.waf_enabled,
        "mode": settings.waf_mode,
        "engine_stats": waf_engine.get_stats(),
        "rule_stats": rule_engine.get_stats(),
        "protection_modules": {
            "sql_injection": settings.sql_injection_protection,
            "xss_protection": settings.xss_protection,
            "bot_protection": settings.bot_protection_enabled,
            "rate_limiting": settings.rate_limit_enabled,
            "geo_blocking": settings.geo_blocking_enabled
        }
    }


# Rules management endpoints
@rules_router.post("/", response_model=CustomRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    rule: CustomRuleCreate,
    rule_engine: RuleEngine = Depends(get_rule_engine),
    waf_service: WAFService = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Create a new custom rule"""
    try:
        # Check if rule ID already exists
        existing_rule = rule_engine.get_rule(rule.id)
        if existing_rule:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Rule with ID '{rule.id}' already exists"
            )
        
        # Save to database and add to engine
        db_rule = await waf_service.create_rule(db, rule)
        
        # Convert to engine rule and add
        from ..core.rule_engine import CustomRule as EngineRule, RuleCondition
        conditions = []
        for cond in rule.conditions:
            condition = RuleCondition(
                target=cond.target,
                operator=cond.operator,
                value=cond.value,
                header_name=cond.header_name,
                case_sensitive=cond.case_sensitive
            )
            conditions.append(condition)
        
        engine_rule = EngineRule(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            enabled=rule.enabled,
            action=rule.action,
            conditions=conditions,
            priority=rule.priority,
            threat_level=rule.threat_level.value,
            score=rule.score,
            rate_limit_window=rule.rate_limit_window,
            rate_limit_threshold=rule.rate_limit_threshold,
            tags=rule.tags
        )
        
        rule_engine.add_rule(engine_rule)
        
        return CustomRuleResponse(
            id=db_rule.id,
            name=db_rule.name,
            description=db_rule.description,
            enabled=db_rule.enabled,
            action=db_rule.action,
            conditions=[],  # Will be populated from conditions JSON
            priority=db_rule.priority,
            threat_level=db_rule.threat_level,
            score=db_rule.score,
            rate_limit_window=db_rule.rate_limit_window,
            rate_limit_threshold=db_rule.rate_limit_threshold,
            tags=db_rule.tags or [],
            created_at=db_rule.created_at,
            updated_at=db_rule.updated_at
        )
        
    except Exception as e:
        logger.error("Failed to create rule", rule_id=rule.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create rule: {str(e)}"
        )


@rules_router.get("/{rule_id}", response_model=CustomRuleResponse)
async def get_rule(
    rule_id: str,
    waf_service: WAFService = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific rule"""
    rule = await waf_service.get_rule(db, rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule '{rule_id}' not found"
        )
    
    # Convert database rule to response
    return CustomRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        enabled=rule.enabled,
        action=rule.action,
        conditions=[],  # Populate from conditions JSON
        priority=rule.priority,
        threat_level=rule.threat_level,
        score=rule.score,
        rate_limit_window=rule.rate_limit_window,
        rate_limit_threshold=rule.rate_limit_threshold,
        tags=rule.tags or [],
        created_at=rule.created_at,
        updated_at=rule.updated_at
    )


@rules_router.put("/{rule_id}", response_model=CustomRuleResponse)
async def update_rule(
    rule_id: str,
    rule_update: CustomRuleUpdate,
    rule_engine: RuleEngine = Depends(get_rule_engine),
    waf_service: WAFService = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing rule"""
    try:
        updated_rule = await waf_service.update_rule(db, rule_id, rule_update)
        if not updated_rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule '{rule_id}' not found"
            )
        
        # Update in rule engine
        # This would require reloading the rule in the engine
        logger.info("Rule updated", rule_id=rule_id)
        
        return CustomRuleResponse(
            id=updated_rule.id,
            name=updated_rule.name,
            description=updated_rule.description,
            enabled=updated_rule.enabled,
            action=updated_rule.action,
            conditions=[],
            priority=updated_rule.priority,
            threat_level=updated_rule.threat_level,
            score=updated_rule.score,
            rate_limit_window=updated_rule.rate_limit_window,
            rate_limit_threshold=updated_rule.rate_limit_threshold,
            tags=updated_rule.tags or [],
            created_at=updated_rule.created_at,
            updated_at=updated_rule.updated_at
        )
        
    except Exception as e:
        logger.error("Failed to update rule", rule_id=rule_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update rule: {str(e)}"
        )


@rules_router.delete("/{rule_id}", response_model=dict)
async def delete_rule(
    rule_id: str,
    rule_engine: RuleEngine = Depends(get_rule_engine),
    waf_service: WAFService = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Delete a rule"""
    try:
        success = await waf_service.delete_rule(db, rule_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule '{rule_id}' not found"
            )
        
        # Remove from rule engine
        rule_engine.remove_rule(rule_id)
        
        return {"message": f"Rule '{rule_id}' deleted successfully"}
        
    except Exception as e:
        logger.error("Failed to delete rule", rule_id=rule_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete rule: {str(e)}"
        )


@rules_router.get("/", response_model=RuleListResponse)
async def list_rules(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    action: Optional[str] = Query(None, description="Filter by action"),
    threat_level: Optional[str] = Query(None, description="Filter by threat level"),
    waf_service: WAFService = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """List rules with pagination and filtering"""
    try:
        rules, total = await waf_service.list_rules(
            db, page=page, limit=limit, enabled=enabled, action=action, threat_level=threat_level
        )
        
        rule_responses = []
        for rule in rules:
            rule_responses.append(CustomRuleResponse(
                id=rule.id,
                name=rule.name,
                description=rule.description,
                enabled=rule.enabled,
                action=rule.action,
                conditions=[],
                priority=rule.priority,
                threat_level=rule.threat_level,
                score=rule.score,
                rate_limit_window=rule.rate_limit_window,
                rate_limit_threshold=rule.rate_limit_threshold,
                tags=rule.tags or [],
                created_at=rule.created_at,
                updated_at=rule.updated_at
            ))
        
        return RuleListResponse(
            rules=rule_responses,
            total=total,
            page=page,
            limit=limit
        )
        
    except Exception as e:
        logger.error("Failed to list rules", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list rules: {str(e)}"
        )


@rules_router.post("/test", response_model=RuleTestResponse)
async def test_rule(
    test_request: RuleTestRequest,
    rule_engine: RuleEngine = Depends(get_rule_engine)
):
    """Test a rule against a sample request"""
    try:
        rule = rule_engine.get_rule(test_request.rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule '{test_request.rule_id}' not found"
            )
        
        # Convert test request to WAF request
        waf_request = WAFRequest(
            ip=test_request.test_request.ip,
            method=test_request.test_request.method,
            url=test_request.test_request.url,
            headers=test_request.test_request.headers,
            body=test_request.test_request.body,
            user_agent=test_request.test_request.user_agent,
            referer=test_request.test_request.referer
        )
        
        start_time = time.time()
        matched = rule.matches(waf_request)
        execution_time = (time.time() - start_time) * 1000
        
        # Test individual conditions
        conditions_results = []
        for i, condition in enumerate(rule.conditions):
            condition_matched = condition.matches(waf_request)
            conditions_results.append({
                "condition_index": i,
                "matched": condition_matched,
                "target": condition.target.value,
                "operator": condition.operator.value,
                "value": condition.value
            })
        
        return RuleTestResponse(
            rule_id=test_request.rule_id,
            matched=matched,
            conditions_results=conditions_results,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error("Rule test failed", rule_id=test_request.rule_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rule test failed: {str(e)}"
        )


# Configuration endpoints
@config_router.get("/", response_model=WAFConfig)
async def get_waf_config(settings: Settings = Depends(get_settings)):
    """Get WAF configuration"""
    return WAFConfig(
        enabled=settings.waf_enabled,
        mode=settings.waf_mode,
        sql_injection_protection=settings.sql_injection_protection,
        xss_protection=settings.xss_protection,
        bot_protection=settings.bot_protection_enabled,
        rate_limiting=RateLimitConfig(
            enabled=settings.rate_limit_enabled,
            requests_per_minute=settings.rate_limit_requests_per_minute,
            burst_limit=settings.rate_limit_burst,
            block_duration=300  # Default
        ),
        geo_blocking=GeoBlockingConfig(
            enabled=settings.geo_blocking_enabled,
            blocked_countries=settings.blocked_countries,
            allowed_countries=settings.allowed_countries
        ),
        custom_rules_enabled=settings.custom_rules_enabled
    )


@config_router.put("/geo-blocking", response_model=dict)
async def update_geo_blocking(
    config: GeoBlockingConfig,
    waf_service: WAFService = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Update geographic blocking configuration"""
    try:
        await waf_service.update_geo_blocking_config(db, config)
        return {"message": "Geographic blocking configuration updated"}
        
    except Exception as e:
        logger.error("Failed to update geo-blocking config", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


# Statistics endpoints
@stats_router.get("/waf", response_model=WAFStatsResponse)
async def get_waf_stats(
    waf_engine: WAFEngine = Depends(get_waf_engine),
    waf_service: WAFService = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Get WAF statistics"""
    try:
        engine_stats = waf_engine.get_stats()
        
        # Get additional stats from database
        top_blocked_ips = await waf_service.get_top_blocked_ips(db, limit=10)
        top_rules = await waf_service.get_top_triggered_rules(db, limit=10)
        
        return WAFStatsResponse(
            requests_processed=engine_stats["requests_processed"],
            requests_blocked=engine_stats["requests_blocked"],
            block_rate=engine_stats.get("block_rate", 0),
            sql_injection_attempts=engine_stats["sql_injection_attempts"],
            xss_attempts=engine_stats["xss_attempts"],
            bot_requests=engine_stats["bot_requests"],
            rate_limited=engine_stats["rate_limited"],
            geo_blocked=engine_stats["geo_blocked"],
            top_blocked_ips=top_blocked_ips,
            top_triggered_rules=top_rules
        )
        
    except Exception as e:
        logger.error("Failed to get WAF stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


@stats_router.get("/blocked-requests", response_model=BlockedRequestListResponse)
async def get_blocked_requests(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    ip: Optional[str] = Query(None, description="Filter by IP address"),
    rule: Optional[str] = Query(None, description="Filter by rule ID"),
    threat_level: Optional[str] = Query(None, description="Filter by threat level"),
    waf_service: WAFService = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Get blocked requests with pagination"""
    try:
        blocked_requests, total = await waf_service.get_blocked_requests(
            db, page=page, limit=limit, ip=ip, rule=rule, threat_level=threat_level
        )
        
        return BlockedRequestListResponse(
            blocked_requests=blocked_requests,
            total=total,
            page=page,
            limit=limit
        )
        
    except Exception as e:
        logger.error("Failed to get blocked requests", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get blocked requests: {str(e)}"
        )


# Health endpoint
@health_router.get("/", response_model=HealthStatus)
async def health_check(
    settings: Settings = Depends(get_settings),
    waf_engine: WAFEngine = Depends(get_waf_engine),
    rule_engine: RuleEngine = Depends(get_rule_engine),
    db: AsyncSession = Depends(get_db)
):
    """Service health check"""
    import time
    from datetime import datetime
    
    try:
        # Check database connection
        await db.execute("SELECT 1")
        database_connected = True
    except Exception:
        database_connected = False
    
    # Check Redis connection (simplified)
    redis_connected = True  # Would check actual Redis connection
    
    # Get WAF engine status
    engine_stats = waf_engine.get_stats()
    waf_status = "healthy" if settings.waf_enabled else "disabled"
    
    # Get loaded rules count
    rules_count = len(rule_engine.list_rules())
    
    return HealthStatus(
        status="healthy" if database_connected and redis_connected else "unhealthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        uptime_seconds=time.time(),  # Simplified uptime
        database_connected=database_connected,
        redis_connected=redis_connected,
        waf_engine_status=waf_status,
        rules_loaded=rules_count
    )
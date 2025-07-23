"""
WAF Service - Business logic for WAF Protection
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
import structlog
import hashlib
import json

from ..models.database import (
    CustomRule as DBCustomRule, BlockedRequest as DBBlockedRequest,
    WAFMetrics, IPWhitelist, IPBlacklist, WAFConfig as DBWAFConfig,
    AlertRule, SuspiciousActivity
)
from ..models.schemas import (
    CustomRuleCreate, CustomRuleUpdate, BlockedRequest,
    GeoBlockingConfig, RateLimitConfig
)
from ..core.waf_engine import WAFRequest, WAFResult

logger = structlog.get_logger()


class WAFService:
    """Service for managing WAF operations"""
    
    async def create_rule(self, db: AsyncSession, rule: CustomRuleCreate) -> DBCustomRule:
        """Create a new custom rule"""
        try:
            # Serialize conditions
            conditions_data = []
            for condition in rule.conditions:
                cond_data = {
                    "target": condition.target.value,
                    "operator": condition.operator.value,
                    "value": condition.value,
                    "header_name": condition.header_name,
                    "case_sensitive": condition.case_sensitive
                }
                conditions_data.append(cond_data)
            
            db_rule = DBCustomRule(
                id=rule.id,
                name=rule.name,
                description=rule.description,
                enabled=rule.enabled,
                action=rule.action.value,
                priority=rule.priority,
                threat_level=rule.threat_level.value,
                score=rule.score,
                conditions=conditions_data,
                rate_limit_window=rule.rate_limit_window,
                rate_limit_threshold=rule.rate_limit_threshold,
                tags=rule.tags
            )
            
            db.add(db_rule)
            await db.commit()
            await db.refresh(db_rule)
            
            logger.info("Custom rule created", rule_id=rule.id, rule_name=rule.name)
            return db_rule
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to create rule", rule_id=rule.id, error=str(e))
            raise
    
    async def get_rule(self, db: AsyncSession, rule_id: str) -> Optional[DBCustomRule]:
        """Get a rule by ID"""
        try:
            stmt = select(DBCustomRule).where(DBCustomRule.id == rule_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error("Failed to get rule", rule_id=rule_id, error=str(e))
            raise
    
    async def update_rule(self, db: AsyncSession, rule_id: str, rule_update: CustomRuleUpdate) -> Optional[DBCustomRule]:
        """Update an existing rule"""
        try:
            stmt = select(DBCustomRule).where(DBCustomRule.id == rule_id)
            result = await db.execute(stmt)
            db_rule = result.scalar_one_or_none()
            
            if not db_rule:
                return None
            
            # Update fields if provided
            if rule_update.name is not None:
                db_rule.name = rule_update.name
            if rule_update.description is not None:
                db_rule.description = rule_update.description
            if rule_update.enabled is not None:
                db_rule.enabled = rule_update.enabled
            if rule_update.action is not None:
                db_rule.action = rule_update.action.value
            if rule_update.priority is not None:
                db_rule.priority = rule_update.priority
            if rule_update.threat_level is not None:
                db_rule.threat_level = rule_update.threat_level.value
            if rule_update.score is not None:
                db_rule.score = rule_update.score
            if rule_update.rate_limit_window is not None:
                db_rule.rate_limit_window = rule_update.rate_limit_window
            if rule_update.rate_limit_threshold is not None:
                db_rule.rate_limit_threshold = rule_update.rate_limit_threshold
            if rule_update.tags is not None:
                db_rule.tags = rule_update.tags
            
            # Update conditions if provided
            if rule_update.conditions is not None:
                conditions_data = []
                for condition in rule_update.conditions:
                    cond_data = {
                        "target": condition.target.value,
                        "operator": condition.operator.value,
                        "value": condition.value,
                        "header_name": condition.header_name,
                        "case_sensitive": condition.case_sensitive
                    }
                    conditions_data.append(cond_data)
                db_rule.conditions = conditions_data
            
            db_rule.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(db_rule)
            
            logger.info("Rule updated", rule_id=rule_id)
            return db_rule
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to update rule", rule_id=rule_id, error=str(e))
            raise
    
    async def delete_rule(self, db: AsyncSession, rule_id: str) -> bool:
        """Delete a rule"""
        try:
            stmt = select(DBCustomRule).where(DBCustomRule.id == rule_id)
            result = await db.execute(stmt)
            db_rule = result.scalar_one_or_none()
            
            if not db_rule:
                return False
            
            await db.delete(db_rule)
            await db.commit()
            
            logger.info("Rule deleted", rule_id=rule_id)
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to delete rule", rule_id=rule_id, error=str(e))
            raise
    
    async def list_rules(
        self,
        db: AsyncSession,
        page: int = 1,
        limit: int = 20,
        enabled: Optional[bool] = None,
        action: Optional[str] = None,
        threat_level: Optional[str] = None
    ) -> Tuple[List[DBCustomRule], int]:
        """List rules with pagination and filtering"""
        try:
            # Build query
            query = select(DBCustomRule)
            
            # Apply filters
            filters = []
            if enabled is not None:
                filters.append(DBCustomRule.enabled == enabled)
            if action:
                filters.append(DBCustomRule.action == action)
            if threat_level:
                filters.append(DBCustomRule.threat_level == threat_level)
            
            if filters:
                query = query.where(and_(*filters))
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await db.execute(count_query)
            total = count_result.scalar()
            
            # Apply pagination and ordering
            query = query.order_by(DBCustomRule.priority, DBCustomRule.created_at)
            query = query.offset((page - 1) * limit).limit(limit)
            
            result = await db.execute(query)
            rules = result.scalars().all()
            
            return list(rules), total
            
        except Exception as e:
            logger.error("Failed to list rules", error=str(e))
            raise
    
    async def log_blocked_request(
        self,
        db: AsyncSession,
        request: WAFRequest,
        result: WAFResult,
        processing_time: float
    ) -> DBBlockedRequest:
        """Log a blocked request"""
        try:
            # Hash body for privacy if it exists
            body_hash = None
            if request.body:
                body_hash = hashlib.sha256(request.body.encode()).hexdigest()
            
            blocked_request = DBBlockedRequest(
                ip=request.ip,
                method=request.method,
                url=request.url,
                user_agent=request.user_agent,
                referer=request.referer,
                headers=request.headers,
                body_hash=body_hash,
                rule_triggered=result.rule_triggered or "unknown",
                threat_level=result.threat_level,
                block_reason=result.block_reason or "Unknown reason",
                score=result.score,
                country_code=result.metadata.get("country_code"),
                country_name=result.metadata.get("country_name"),
                is_bot=result.metadata.get("is_bot", False),
                metadata=result.metadata,
                processing_time_ms=processing_time
            )
            
            db.add(blocked_request)
            await db.commit()
            
            # Update suspicious activity tracking
            await self._track_suspicious_activity(db, request, result)
            
            logger.info("Blocked request logged",
                       ip=request.ip,
                       rule=result.rule_triggered,
                       threat_level=result.threat_level)
            
            return blocked_request
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to log blocked request", error=str(e))
            raise
    
    async def get_blocked_requests(
        self,
        db: AsyncSession,
        page: int = 1,
        limit: int = 20,
        ip: Optional[str] = None,
        rule: Optional[str] = None,
        threat_level: Optional[str] = None,
        hours: int = 24
    ) -> Tuple[List[BlockedRequest], int]:
        """Get blocked requests with pagination"""
        try:
            # Build query
            query = select(DBBlockedRequest)
            
            # Apply time filter
            since = datetime.utcnow() - timedelta(hours=hours)
            filters = [DBBlockedRequest.timestamp >= since]
            
            # Apply additional filters
            if ip:
                filters.append(DBBlockedRequest.ip == ip)
            if rule:
                filters.append(DBBlockedRequest.rule_triggered == rule)
            if threat_level:
                filters.append(DBBlockedRequest.threat_level == threat_level)
            
            query = query.where(and_(*filters))
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await db.execute(count_query)
            total = count_result.scalar()
            
            # Apply pagination and ordering
            query = query.order_by(desc(DBBlockedRequest.timestamp))
            query = query.offset((page - 1) * limit).limit(limit)
            
            result = await db.execute(query)
            db_requests = result.scalars().all()
            
            # Convert to response models
            blocked_requests = []
            for db_req in db_requests:
                blocked_requests.append(BlockedRequest(
                    id=str(db_req.id),
                    ip=db_req.ip,
                    method=db_req.method,
                    url=db_req.url,
                    user_agent=db_req.user_agent,
                    rule_triggered=db_req.rule_triggered,
                    threat_level=db_req.threat_level,
                    block_reason=db_req.block_reason,
                    score=db_req.score,
                    timestamp=db_req.timestamp,
                    metadata=db_req.metadata or {}
                ))
            
            return blocked_requests, total
            
        except Exception as e:
            logger.error("Failed to get blocked requests", error=str(e))
            raise
    
    async def get_top_blocked_ips(self, db: AsyncSession, limit: int = 10, hours: int = 24) -> List[Dict[str, Any]]:
        """Get top blocked IP addresses"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            stmt = select(
                DBBlockedRequest.ip,
                func.count(DBBlockedRequest.id).label("count"),
                func.max(DBBlockedRequest.timestamp).label("last_blocked")
            ).where(
                DBBlockedRequest.timestamp >= since
            ).group_by(
                DBBlockedRequest.ip
            ).order_by(
                desc(func.count(DBBlockedRequest.id))
            ).limit(limit)
            
            result = await db.execute(stmt)
            rows = result.all()
            
            return [
                {
                    "ip": row.ip,
                    "count": row.count,
                    "last_blocked": row.last_blocked.isoformat()
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error("Failed to get top blocked IPs", error=str(e))
            raise
    
    async def get_top_triggered_rules(self, db: AsyncSession, limit: int = 10, hours: int = 24) -> List[Dict[str, Any]]:
        """Get top triggered rules"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            stmt = select(
                DBBlockedRequest.rule_triggered,
                func.count(DBBlockedRequest.id).label("count"),
                func.max(DBBlockedRequest.timestamp).label("last_triggered")
            ).where(
                DBBlockedRequest.timestamp >= since
            ).group_by(
                DBBlockedRequest.rule_triggered
            ).order_by(
                desc(func.count(DBBlockedRequest.id))
            ).limit(limit)
            
            result = await db.execute(stmt)
            rows = result.all()
            
            return [
                {
                    "rule": row.rule_triggered,
                    "count": row.count,
                    "last_triggered": row.last_triggered.isoformat()
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error("Failed to get top triggered rules", error=str(e))
            raise
    
    async def update_geo_blocking_config(self, db: AsyncSession, config: GeoBlockingConfig):
        """Update geographic blocking configuration"""
        try:
            # Store configuration in database
            config_data = {
                "enabled": config.enabled,
                "blocked_countries": config.blocked_countries,
                "allowed_countries": config.allowed_countries
            }
            
            # Upsert configuration
            stmt = select(DBWAFConfig).where(DBWAFConfig.config_key == "geo_blocking")
            result = await db.execute(stmt)
            db_config = result.scalar_one_or_none()
            
            if db_config:
                db_config.config_value = config_data
                db_config.updated_at = datetime.utcnow()
            else:
                db_config = DBWAFConfig(
                    config_key="geo_blocking",
                    config_value=config_data,
                    description="Geographic blocking configuration",
                    config_type="geo_blocking"
                )
                db.add(db_config)
            
            await db.commit()
            logger.info("Geo-blocking configuration updated")
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to update geo-blocking config", error=str(e))
            raise
    
    async def add_ip_to_whitelist(self, db: AsyncSession, ip_range: str, description: str = None):
        """Add IP to whitelist"""
        try:
            whitelist_entry = IPWhitelist(
                ip_range=ip_range,
                description=description,
                enabled=True
            )
            
            db.add(whitelist_entry)
            await db.commit()
            
            logger.info("IP added to whitelist", ip_range=ip_range)
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to add IP to whitelist", ip_range=ip_range, error=str(e))
            raise
    
    async def add_ip_to_blacklist(self, db: AsyncSession, ip_range: str, description: str = None, duration: int = None):
        """Add IP to blacklist"""
        try:
            expires_at = None
            if duration:
                expires_at = datetime.utcnow() + timedelta(seconds=duration)
            
            blacklist_entry = IPBlacklist(
                ip_range=ip_range,
                description=description,
                enabled=True,
                expires_at=expires_at
            )
            
            db.add(blacklist_entry)
            await db.commit()
            
            logger.info("IP added to blacklist", ip_range=ip_range, duration=duration)
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to add IP to blacklist", ip_range=ip_range, error=str(e))
            raise
    
    async def _track_suspicious_activity(self, db: AsyncSession, request: WAFRequest, result: WAFResult):
        """Track suspicious activity patterns"""
        try:
            # Simple pattern detection - repeated blocks from same IP
            since = datetime.utcnow() - timedelta(hours=1)
            
            # Count recent blocks from this IP
            stmt = select(func.count(DBBlockedRequest.id)).where(
                and_(
                    DBBlockedRequest.ip == request.ip,
                    DBBlockedRequest.timestamp >= since
                )
            )
            count_result = await db.execute(stmt)
            recent_blocks = count_result.scalar()
            
            # If multiple blocks, create or update suspicious activity record
            if recent_blocks >= 5:  # Threshold for suspicious activity
                stmt = select(SuspiciousActivity).where(
                    and_(
                        SuspiciousActivity.ip == request.ip,
                        SuspiciousActivity.activity_type == "repeated_blocks",
                        SuspiciousActivity.status == "active"
                    )
                )
                result_activity = await db.execute(stmt)
                activity = result_activity.scalar_one_or_none()
                
                if activity:
                    # Update existing record
                    activity.last_seen = datetime.utcnow()
                    activity.occurrence_count += 1
                    activity.confidence_score = min(1.0, activity.confidence_score + 0.1)
                else:
                    # Create new suspicious activity record
                    activity = SuspiciousActivity(
                        ip=request.ip,
                        activity_type="repeated_blocks",
                        severity="medium",
                        description=f"IP {request.ip} has been blocked {recent_blocks} times in the last hour",
                        pattern_data={
                            "recent_blocks": recent_blocks,
                            "rules_triggered": [result.rule_triggered],
                            "threat_levels": [result.threat_level]
                        },
                        confidence_score=0.7,
                        user_agent=request.user_agent,
                        country_code=result.metadata.get("country_code")
                    )
                    db.add(activity)
                
                await db.commit()
                logger.info("Suspicious activity tracked", ip=request.ip, blocks=recent_blocks)
            
        except Exception as e:
            logger.error("Failed to track suspicious activity", error=str(e))
            # Don't raise - this is non-critical
    
    async def get_waf_analytics(self, db: AsyncSession, hours: int = 24) -> Dict[str, Any]:
        """Get WAF analytics and metrics"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Basic statistics
            total_blocks_stmt = select(func.count(DBBlockedRequest.id)).where(
                DBBlockedRequest.timestamp >= since
            )
            total_blocks_result = await db.execute(total_blocks_stmt)
            total_blocks = total_blocks_result.scalar()
            
            # Threat level distribution
            threat_dist_stmt = select(
                DBBlockedRequest.threat_level,
                func.count(DBBlockedRequest.id).label("count")
            ).where(
                DBBlockedRequest.timestamp >= since
            ).group_by(DBBlockedRequest.threat_level)
            
            threat_dist_result = await db.execute(threat_dist_stmt)
            threat_distribution = {row.threat_level: row.count for row in threat_dist_result}
            
            # Rule effectiveness
            rule_stats_stmt = select(
                DBBlockedRequest.rule_triggered,
                func.count(DBBlockedRequest.id).label("blocks"),
                func.avg(DBBlockedRequest.score).label("avg_score")
            ).where(
                DBBlockedRequest.timestamp >= since
            ).group_by(DBBlockedRequest.rule_triggered)
            
            rule_stats_result = await db.execute(rule_stats_stmt)
            rule_effectiveness = [
                {
                    "rule": row.rule_triggered,
                    "blocks": row.blocks,
                    "avg_score": float(row.avg_score) if row.avg_score else 0
                }
                for row in rule_stats_result
            ]
            
            # Geographic distribution
            geo_dist_stmt = select(
                DBBlockedRequest.country_code,
                DBBlockedRequest.country_name,
                func.count(DBBlockedRequest.id).label("count")
            ).where(
                and_(
                    DBBlockedRequest.timestamp >= since,
                    DBBlockedRequest.country_code.isnot(None)
                )
            ).group_by(
                DBBlockedRequest.country_code,
                DBBlockedRequest.country_name
            ).order_by(desc(func.count(DBBlockedRequest.id))).limit(10)
            
            geo_dist_result = await db.execute(geo_dist_stmt)
            geographic_distribution = [
                {
                    "country_code": row.country_code,
                    "country_name": row.country_name,
                    "count": row.count
                }
                for row in geo_dist_result
            ]
            
            return {
                "period_hours": hours,
                "total_blocks": total_blocks,
                "threat_distribution": threat_distribution,
                "rule_effectiveness": rule_effectiveness,
                "geographic_distribution": geographic_distribution,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get WAF analytics", error=str(e))
            raise
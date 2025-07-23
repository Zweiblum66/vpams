"""
Failover Manager for MAMS
Handles automatic and manual failover between regions
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from enum import Enum
import httpx
import aioredis
import structlog

from ..core.config import settings
from ..models.schemas import (
    RegionHealth,
    ServiceHealth,
    FailoverEvent,
    FailoverPlan,
    FailoverStatus,
    RegionStatus,
    ServiceStatus,
    FailoverState,
    FailoverType,
    LoadBalancerConfig,
    LoadBalancerAlgorithm,
    DataConsistencyCheck,
    RecoveryPointStatus
)
from ..utils.notifications import NotificationManager
from ..utils.metrics import MetricsCollector

logger = structlog.get_logger(__name__)


class FailoverManager:
    """
    Manages region failover for MAMS platform
    """
    
    def __init__(self):
        self.regions = settings.SECONDARY_REGIONS + [settings.PRIMARY_REGION]
        self.primary_region = settings.PRIMARY_REGION
        self.current_active_region = settings.CURRENT_REGION
        
        # Health tracking
        self.region_health: Dict[str, RegionHealth] = {}
        self.service_health: Dict[str, Dict[str, ServiceHealth]] = {}
        
        # Failover state
        self.failover_state = FailoverState.NORMAL
        self.active_failover: Optional[FailoverEvent] = None
        self.failover_history: List[FailoverEvent] = []
        
        # Components
        self.notifications = NotificationManager()
        self.metrics = MetricsCollector()
        self.redis_client: Optional[aioredis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # Tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._consistency_check_task: Optional[asyncio.Task] = None
        self._initialized = False
        
        # Load balancer
        self.load_balancer = LoadBalancerConfig(
            algorithm=LoadBalancerAlgorithm(settings.LOAD_BALANCER_TYPE),
            regions=self.regions,
            weights=settings.REGION_WEIGHTS if settings.LOAD_BALANCER_TYPE == "weighted" else None
        )
    
    async def initialize(self):
        """Initialize failover manager"""
        if self._initialized:
            return
        
        logger.info("Initializing failover manager")
        
        # Initialize Redis for state management
        self.redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        
        # Initialize HTTP client
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.HEALTH_CHECK_TIMEOUT_SECONDS)
        )
        
        # Initialize region health
        for region in self.regions:
            self.region_health[region] = RegionHealth(
                region=region,
                status=RegionStatus.ACTIVE if region == self.current_active_region else RegionStatus.STANDBY
            )
        
        # Load previous state
        await self._load_state()
        
        # Start health monitoring
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        # Start consistency checking
        if settings.ENABLE_DATA_CONSISTENCY_CHECK:
            self._consistency_check_task = asyncio.create_task(self._consistency_check_loop())
        
        self._initialized = True
        logger.info("Failover manager initialized")
    
    async def _health_check_loop(self):
        """Continuous health check loop"""
        while True:
            try:
                await self._check_all_regions()
                await asyncio.sleep(settings.HEALTH_CHECK_INTERVAL_SECONDS)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(10)
    
    async def _check_all_regions(self):
        """Check health of all regions"""
        tasks = []
        for region in self.regions:
            task = self._check_region_health(region)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and determine if failover is needed
        for region, result in zip(self.regions, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to check region {region}: {result}")
                await self._handle_region_failure(region)
            else:
                await self._update_region_health(region, result)
    
    async def _check_region_health(self, region: str) -> RegionHealth:
        """Check health of a specific region"""
        region_health = self.region_health.get(region, RegionHealth(region=region, status=RegionStatus.UNKNOWN))
        
        # Check all services in the region
        service_statuses = {}
        for service_name, endpoint_template in settings.SERVICE_HEALTH_ENDPOINTS.items():
            # Adjust endpoint for region
            endpoint = self._get_region_endpoint(endpoint_template, region)
            status = await self._check_service_health(service_name, endpoint, region)
            service_statuses[service_name] = status.status
            
            # Store service health
            if region not in self.service_health:
                self.service_health[region] = {}
            self.service_health[region][service_name] = status
        
        # Check databases
        database_status = await self._check_database_health(region)
        
        # Calculate overall region status
        healthy_services = sum(1 for s in service_statuses.values() if s == ServiceStatus.HEALTHY)
        total_services = len(service_statuses)
        
        if healthy_services == total_services and all(database_status.values()):
            region_health.status = RegionStatus.ACTIVE if region == self.current_active_region else RegionStatus.STANDBY
            region_health.consecutive_failures = 0
        elif healthy_services >= total_services * 0.7:  # 70% threshold
            region_health.status = RegionStatus.DEGRADED
        else:
            region_health.status = RegionStatus.FAILED
            region_health.consecutive_failures += 1
        
        region_health.services = service_statuses
        region_health.database_status = database_status
        region_health.last_check = datetime.utcnow()
        
        # Update metrics
        self.metrics.gauge(
            "failover.region.health",
            region_health.health_percentage,
            labels={"region": region}
        )
        
        return region_health
    
    async def _check_service_health(self, service_name: str, endpoint: str, region: str) -> ServiceHealth:
        """Check health of a specific service"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            response = await self.http_client.get(endpoint)
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            if response.status_code == 200:
                return ServiceHealth(
                    service_name=service_name,
                    region=region,
                    status=ServiceStatus.HEALTHY,
                    response_time_ms=response_time
                )
            else:
                return ServiceHealth(
                    service_name=service_name,
                    region=region,
                    status=ServiceStatus.UNHEALTHY,
                    response_time_ms=response_time,
                    error_count=1
                )
                
        except Exception as e:
            logger.error(f"Health check failed for {service_name} in {region}: {e}")
            return ServiceHealth(
                service_name=service_name,
                region=region,
                status=ServiceStatus.UNHEALTHY,
                error_count=1
            )
    
    async def _check_database_health(self, region: str) -> Dict[str, bool]:
        """Check database health in a region"""
        database_status = {}
        
        endpoints = settings.DATABASE_ENDPOINTS.get(region, {})
        for db_type, endpoint in endpoints.items():
            try:
                # Simple connectivity check
                # In production, would use actual database clients
                database_status[db_type] = True
            except Exception as e:
                logger.error(f"Database {db_type} unhealthy in {region}: {e}")
                database_status[db_type] = False
        
        return database_status
    
    async def _update_region_health(self, region: str, health: RegionHealth):
        """Update region health and trigger failover if needed"""
        self.region_health[region] = health
        
        # Save state
        await self._save_state()
        
        # Check if we need to failover
        if region == self.current_active_region and health.status == RegionStatus.FAILED:
            if health.consecutive_failures >= settings.FAILOVER_THRESHOLD:
                await self._trigger_automatic_failover(region)
    
    async def _handle_region_failure(self, region: str):
        """Handle region failure"""
        health = self.region_health.get(region)
        if not health:
            return
        
        health.consecutive_failures += 1
        health.status = RegionStatus.FAILED
        health.last_check = datetime.utcnow()
        
        if region == self.current_active_region and health.consecutive_failures >= settings.FAILOVER_THRESHOLD:
            await self._trigger_automatic_failover(region)
    
    async def _trigger_automatic_failover(self, failed_region: str):
        """Trigger automatic failover"""
        if not settings.AUTO_FAILOVER_ENABLED:
            logger.warning(f"Region {failed_region} failed but auto-failover is disabled")
            await self.notifications.send_critical_alert(
                f"Region {failed_region} has failed. Manual intervention required."
            )
            return
        
        # Find best target region
        target_region = await self._select_failover_target(failed_region)
        if not target_region:
            logger.error("No healthy region available for failover")
            await self.notifications.send_critical_alert(
                "All regions are unhealthy. System is in critical state."
            )
            return
        
        # Create failover event
        event = FailoverEvent(
            event_type=FailoverType.AUTOMATIC,
            state=FailoverState.FAILING_OVER,
            from_region=failed_region,
            to_region=target_region,
            reason=f"Region {failed_region} health check failures exceeded threshold",
            triggered_by="system"
        )
        
        await self.execute_failover(event)
    
    async def _select_failover_target(self, exclude_region: str) -> Optional[str]:
        """Select best region for failover"""
        candidates = []
        
        for region, health in self.region_health.items():
            if region == exclude_region:
                continue
            
            if health.is_healthy:
                candidates.append({
                    "region": region,
                    "health": health.health_percentage,
                    "latency": health.latency_ms or float('inf'),
                    "priority": self._get_region_priority(region)
                })
        
        if not candidates:
            return None
        
        # Sort by priority, health, and latency
        candidates.sort(key=lambda x: (-x["priority"], -x["health"], x["latency"]))
        
        return candidates[0]["region"]
    
    def _get_region_priority(self, region: str) -> int:
        """Get region failover priority"""
        # Primary region has highest priority
        if region == self.primary_region:
            return 100
        
        # Use configured weights if available
        if self.load_balancer.weights:
            return int(self.load_balancer.weights.get(region, 0) * 100)
        
        # Default priority based on region order
        try:
            return 90 - self.regions.index(region) * 10
        except ValueError:
            return 0
    
    async def execute_failover(self, event: FailoverEvent):
        """Execute failover plan"""
        logger.info(f"Executing failover from {event.from_region} to {event.to_region}")
        
        # Update state
        self.failover_state = FailoverState.FAILING_OVER
        self.active_failover = event
        event.started_at = datetime.utcnow()
        
        # Notify about failover start
        await self.notifications.send_failover_notification(
            f"Starting failover from {event.from_region} to {event.to_region}",
            event
        )
        
        try:
            # Create failover plan
            plan = await self._create_failover_plan(event)
            
            # Execute pre-checks
            await self._execute_pre_checks(plan)
            
            # Execute failover steps
            for step in plan.steps:
                await self._execute_failover_step(step, event)
            
            # Update active region
            self.current_active_region = event.to_region
            self.region_health[event.to_region].status = RegionStatus.ACTIVE
            self.region_health[event.from_region].status = RegionStatus.FAILED
            
            # Execute post-checks
            await self._execute_post_checks(plan)
            
            # Mark as successful
            event.completed_at = datetime.utcnow()
            event.success = True
            event.state = FailoverState.FAILED_OVER
            self.failover_state = FailoverState.FAILED_OVER
            
            # Save state
            await self._save_state()
            
            # Notify success
            await self.notifications.send_failover_notification(
                f"Failover completed successfully to {event.to_region}",
                event
            )
            
            # Update metrics
            self.metrics.increment(
                "failover.completed",
                labels={"type": event.event_type, "success": "true"}
            )
            
            # Schedule failback if enabled
            if settings.AUTO_FAILBACK_ENABLED and event.from_region == self.primary_region:
                await self._schedule_failback(event)
            
        except Exception as e:
            logger.error(f"Failover failed: {e}")
            event.success = False
            event.completed_at = datetime.utcnow()
            
            # Attempt rollback
            await self._rollback_failover(event)
            
            # Notify failure
            await self.notifications.send_critical_alert(
                f"Failover failed: {str(e)}"
            )
            
            # Update metrics
            self.metrics.increment(
                "failover.completed",
                labels={"type": event.event_type, "success": "false"}
            )
        
        finally:
            # Add to history
            self.failover_history.append(event)
            self.active_failover = None
    
    async def _create_failover_plan(self, event: FailoverEvent) -> FailoverPlan:
        """Create detailed failover plan"""
        plan = FailoverPlan(
            name=f"Failover-{event.event_id}",
            description=f"Failover from {event.from_region} to {event.to_region}",
            source_region=event.from_region,
            target_region=event.to_region,
            services=list(settings.SERVICE_HEALTH_ENDPOINTS.keys()),
            estimated_downtime_minutes=settings.RTO_MINUTES
        )
        
        # Add pre-checks
        plan.pre_checks = [
            "verify_target_region_health",
            "check_replication_lag",
            "verify_network_connectivity"
        ]
        
        # Add failover steps
        plan.steps = [
            {"name": "update_dns", "action": "update_dns_records"},
            {"name": "update_load_balancer", "action": "update_load_balancer_config"},
            {"name": "redirect_traffic", "action": "redirect_traffic_to_target"},
            {"name": "update_service_configs", "action": "update_service_configurations"},
            {"name": "verify_services", "action": "verify_service_health"}
        ]
        
        # Add post-checks
        plan.post_checks = [
            "verify_all_services_healthy",
            "check_data_consistency",
            "verify_user_access"
        ]
        
        # Add rollback steps
        plan.rollback_steps = [
            {"name": "restore_dns", "action": "restore_original_dns"},
            {"name": "restore_load_balancer", "action": "restore_load_balancer_config"},
            {"name": "redirect_traffic_back", "action": "redirect_traffic_to_source"}
        ]
        
        return plan
    
    async def _execute_pre_checks(self, plan: FailoverPlan):
        """Execute pre-failover checks"""
        logger.info("Executing pre-failover checks")
        
        # Verify target region health
        target_health = self.region_health.get(plan.target_region)
        if not target_health or not target_health.is_healthy:
            raise Exception(f"Target region {plan.target_region} is not healthy")
        
        # Check replication lag
        rpo_status = await self.check_rpo_status(plan.source_region, plan.target_region)
        if not rpo_status.is_within_rpo:
            logger.warning(f"RPO exceeded: {rpo_status.current_lag_minutes} minutes")
    
    async def _execute_failover_step(self, step: Dict[str, Any], event: FailoverEvent):
        """Execute a single failover step"""
        logger.info(f"Executing failover step: {step['name']}")
        
        action = step["action"]
        
        if action == "update_dns_records":
            await self._update_dns_records(event.to_region)
        elif action == "update_load_balancer_config":
            await self._update_load_balancer(event.to_region)
        elif action == "redirect_traffic_to_target":
            await self._redirect_traffic(event.from_region, event.to_region)
        elif action == "update_service_configurations":
            await self._update_service_configs(event.to_region)
        elif action == "verify_service_health":
            await self._verify_services_healthy(event.to_region)
    
    async def _execute_post_checks(self, plan: FailoverPlan):
        """Execute post-failover checks"""
        logger.info("Executing post-failover checks")
        
        # Verify all services are healthy
        region_health = await self._check_region_health(plan.target_region)
        if not region_health.is_healthy:
            raise Exception(f"Post-check failed: Region {plan.target_region} is not fully healthy")
        
        # Schedule data consistency check
        if settings.ENABLE_DATA_CONSISTENCY_CHECK:
            asyncio.create_task(self.check_data_consistency([plan.source_region, plan.target_region]))
    
    async def _rollback_failover(self, event: FailoverEvent):
        """Rollback failed failover"""
        logger.info("Rolling back failover")
        
        try:
            # Restore original configuration
            await self._update_dns_records(event.from_region)
            await self._update_load_balancer(event.from_region)
            await self._redirect_traffic(event.to_region, event.from_region)
            
            # Update state
            self.current_active_region = event.from_region
            self.failover_state = FailoverState.NORMAL
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
    
    async def _schedule_failback(self, original_event: FailoverEvent):
        """Schedule automatic failback to primary region"""
        delay_seconds = settings.FAILBACK_DELAY_MINUTES * 60
        
        logger.info(f"Scheduling failback to {original_event.from_region} in {settings.FAILBACK_DELAY_MINUTES} minutes")
        
        await asyncio.sleep(delay_seconds)
        
        # Check if primary is healthy
        primary_health = await self._check_region_health(original_event.from_region)
        if primary_health.is_healthy:
            # Create failback event
            failback_event = FailoverEvent(
                event_type=FailoverType.AUTOMATIC,
                state=FailoverState.FAILING_BACK,
                from_region=original_event.to_region,
                to_region=original_event.from_region,
                reason="Automatic failback to primary region",
                triggered_by="system"
            )
            
            await self.execute_failover(failback_event)
    
    async def _update_dns_records(self, target_region: str):
        """Update DNS records to point to target region"""
        # In production, would use Route53 or similar
        logger.info(f"Updating DNS records to point to {target_region}")
        await asyncio.sleep(1)  # Simulate DNS update
    
    async def _update_load_balancer(self, target_region: str):
        """Update load balancer configuration"""
        # In production, would update actual load balancer
        logger.info(f"Updating load balancer to route traffic to {target_region}")
        
        # Update weights
        if self.load_balancer.algorithm == LoadBalancerAlgorithm.WEIGHTED:
            new_weights = {r: 0.0 for r in self.regions}
            new_weights[target_region] = 1.0
            self.load_balancer.weights = new_weights
    
    async def _redirect_traffic(self, from_region: str, to_region: str):
        """Redirect traffic from one region to another"""
        logger.info(f"Redirecting traffic from {from_region} to {to_region}")
        # In production, would update ingress controllers, API gateways, etc.
        await asyncio.sleep(1)
    
    async def _update_service_configs(self, target_region: str):
        """Update service configurations for new region"""
        logger.info(f"Updating service configurations for {target_region}")
        
        # Update database endpoints
        db_endpoints = settings.DATABASE_ENDPOINTS.get(target_region, {})
        
        # In production, would update service environment variables or configs
        await asyncio.sleep(1)
    
    async def _verify_services_healthy(self, region: str):
        """Verify all services are healthy in region"""
        health = await self._check_region_health(region)
        if not health.is_healthy:
            unhealthy_services = [s for s, status in health.services.items() 
                                 if status != ServiceStatus.HEALTHY]
            raise Exception(f"Services unhealthy in {region}: {unhealthy_services}")
    
    def _get_region_endpoint(self, endpoint_template: str, region: str) -> str:
        """Get region-specific endpoint"""
        # In production, would use region-specific DNS or service discovery
        return endpoint_template.replace("-us-east-1", f"-{region}")
    
    async def manual_failover(self, target_region: str, reason: str, 
                            triggered_by: str, force: bool = False) -> FailoverEvent:
        """Execute manual failover"""
        if self.failover_state != FailoverState.NORMAL and not force:
            raise Exception("Failover already in progress")
        
        # Verify target region health
        if not force:
            target_health = self.region_health.get(target_region)
            if not target_health or not target_health.is_healthy:
                raise Exception(f"Target region {target_region} is not healthy")
        
        # Create manual failover event
        event = FailoverEvent(
            event_type=FailoverType.MANUAL,
            state=FailoverState.FAILING_OVER,
            from_region=self.current_active_region,
            to_region=target_region,
            reason=reason,
            triggered_by=triggered_by
        )
        
        await self.execute_failover(event)
        return event
    
    async def get_failover_status(self) -> FailoverStatus:
        """Get current failover status"""
        return FailoverStatus(
            current_state=self.failover_state,
            primary_region=self.primary_region,
            active_region=self.current_active_region,
            standby_regions=[r for r in self.regions if r != self.current_active_region],
            region_health=self.region_health,
            active_failover=self.active_failover,
            automated_actions_enabled=settings.AUTO_FAILOVER_ENABLED
        )
    
    async def check_rpo_status(self, source_region: str, target_region: str) -> RecoveryPointStatus:
        """Check Recovery Point Objective status"""
        # In production, would check actual replication lag
        current_lag = 3.5  # Simulated lag in minutes
        
        return RecoveryPointStatus(
            region=target_region,
            rpo_target_minutes=settings.RPO_MINUTES,
            current_lag_minutes=current_lag,
            is_within_rpo=current_lag <= settings.RPO_MINUTES,
            last_sync_time=datetime.utcnow() - timedelta(minutes=current_lag)
        )
    
    async def check_data_consistency(self, regions: List[str]) -> DataConsistencyCheck:
        """Check data consistency between regions"""
        check = DataConsistencyCheck(
            regions_compared=regions,
            check_type="sample"
        )
        
        # In production, would perform actual consistency checks
        check.records_checked = 10000
        check.inconsistencies_found = 5
        check.completed_at = datetime.utcnow()
        
        return check
    
    async def _consistency_check_loop(self):
        """Periodic data consistency checking"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                if self.failover_state == FailoverState.NORMAL:
                    regions = [self.current_active_region] + [
                        r for r in self.regions if r != self.current_active_region
                    ][:1]  # Check active and one standby
                    
                    check = await self.check_data_consistency(regions)
                    
                    if check.consistency_percentage < 99.9:
                        await self.notifications.send_warning(
                            f"Data consistency below threshold: {check.consistency_percentage:.2f}%"
                        )
                        
            except Exception as e:
                logger.error(f"Consistency check error: {e}")
    
    async def _save_state(self):
        """Save failover state to Redis"""
        if not self.redis_client:
            return
        
        state = {
            "current_active_region": self.current_active_region,
            "failover_state": self.failover_state,
            "region_health": {
                region: health.dict() for region, health in self.region_health.items()
            },
            "last_updated": datetime.utcnow().isoformat()
        }
        
        await self.redis_client.set("failover:state", json.dumps(state, default=str))
    
    async def _load_state(self):
        """Load failover state from Redis"""
        if not self.redis_client:
            return
        
        state_json = await self.redis_client.get("failover:state")
        if state_json:
            state = json.loads(state_json)
            self.current_active_region = state.get("current_active_region", self.primary_region)
            self.failover_state = FailoverState(state.get("failover_state", FailoverState.NORMAL))
    
    async def shutdown(self):
        """Shutdown failover manager"""
        logger.info("Shutting down failover manager")
        
        if self._health_check_task:
            self._health_check_task.cancel()
        
        if self._consistency_check_task:
            self._consistency_check_task.cancel()
        
        if self.http_client:
            await self.http_client.aclose()
        
        if self.redis_client:
            await self.redis_client.close()
        
        self._initialized = False
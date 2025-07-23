"""
Disaster Recovery Service for MAMS Platform

This service provides comprehensive disaster recovery and business continuity
capabilities including:
- Backup strategies and management
- Failover procedures and automation
- Recovery time objectives (RTO) and recovery point objectives (RPO)
- Business continuity planning
- Disaster recovery testing and drills
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import asyncio
import json
import uuid
from pathlib import Path
import aiohttp
import asyncpg
from redis import asyncio as aioredis
import aioboto3
from opensearchpy import AsyncOpenSearch

from ..core.config import settings
from ..core.logging import get_logger
from ..db.models import (
    DisasterRecoveryPlan, BackupStrategy, FailoverProcedure,
    RecoveryTest, BusinessContinuityPlan, RecoveryMetrics,
    DisasterEvent, RecoveryOperation, BackupJob, FailoverEvent
)

logger = get_logger(__name__)


class DisasterType(str, Enum):
    """Types of disasters that can occur"""
    HARDWARE_FAILURE = "hardware_failure"
    SOFTWARE_FAILURE = "software_failure"
    NETWORK_OUTAGE = "network_outage"
    DATA_CORRUPTION = "data_corruption"
    CYBER_ATTACK = "cyber_attack"
    NATURAL_DISASTER = "natural_disaster"
    POWER_OUTAGE = "power_outage"
    HUMAN_ERROR = "human_error"
    PROVIDER_OUTAGE = "provider_outage"
    COMPLETE_DATACENTER_LOSS = "complete_datacenter_loss"


class BackupType(str, Enum):
    """Types of backup strategies"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"
    CONTINUOUS = "continuous"


class FailoverMode(str, Enum):
    """Failover modes"""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EMERGENCY = "emergency"


class RecoveryTier(str, Enum):
    """Recovery tier priorities"""
    CRITICAL = "critical"  # RTO: < 1 hour, RPO: < 15 minutes
    HIGH = "high"        # RTO: < 4 hours, RPO: < 1 hour
    MEDIUM = "medium"    # RTO: < 24 hours, RPO: < 4 hours
    LOW = "low"         # RTO: < 72 hours, RPO: < 24 hours


class ServiceStatus(str, Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    FAILED = "failed"
    RECOVERING = "recovering"


class DisasterRecoveryService:
    """Main disaster recovery service implementation"""
    
    def __init__(self):
        self.redis_client = None
        self.s3_client = None
        self.monitoring_tasks = []
        self.recovery_in_progress = False
        
    async def initialize(self):
        """Initialize service connections"""
        try:
            # Initialize Redis
            self.redis_client = await aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )
            
            # Initialize S3 for backup storage
            session = aioboto3.Session()
            self.s3_client = await session.client('s3').__aenter__()
            
            logger.info("Disaster Recovery Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Disaster Recovery Service: {e}")
            raise
    
    async def create_disaster_recovery_plan(
        self,
        name: str,
        description: str,
        recovery_tiers: Dict[str, RecoveryTier],
        backup_strategies: List[Dict[str, Any]],
        failover_procedures: List[Dict[str, Any]],
        contact_list: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> DisasterRecoveryPlan:
        """Create a comprehensive disaster recovery plan"""
        try:
            plan_id = str(uuid.uuid4())
            
            # Create the main DR plan
            dr_plan = DisasterRecoveryPlan(
                id=plan_id,
                name=name,
                description=description,
                recovery_tiers=recovery_tiers,
                contact_list=contact_list,
                metadata=metadata or {},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_active=True
            )
            
            # Create backup strategies
            for strategy_data in backup_strategies:
                await self._create_backup_strategy(plan_id, strategy_data)
            
            # Create failover procedures
            for procedure_data in failover_procedures:
                await self._create_failover_procedure(plan_id, procedure_data)
            
            # Create default RTO/RPO objectives based on tiers
            await self._create_recovery_objectives(plan_id, recovery_tiers)
            
            # Initialize monitoring for critical services
            await self._initialize_monitoring(plan_id, recovery_tiers)
            
            logger.info(f"Created disaster recovery plan: {plan_id}")
            return dr_plan
            
        except Exception as e:
            logger.error(f"Failed to create disaster recovery plan: {e}")
            raise
    
    async def _create_backup_strategy(
        self,
        plan_id: str,
        strategy_data: Dict[str, Any]
    ) -> BackupStrategy:
        """Create a backup strategy for the DR plan"""
        strategy = BackupStrategy(
            id=str(uuid.uuid4()),
            plan_id=plan_id,
            service_name=strategy_data['service_name'],
            backup_type=BackupType(strategy_data['backup_type']),
            frequency=strategy_data['frequency'],  # cron expression
            retention_days=strategy_data['retention_days'],
            storage_locations=strategy_data['storage_locations'],
            encryption_enabled=strategy_data.get('encryption_enabled', True),
            compression_enabled=strategy_data.get('compression_enabled', True),
            verification_enabled=strategy_data.get('verification_enabled', True),
            metadata=strategy_data.get('metadata', {}),
            created_at=datetime.utcnow()
        )
        
        # Schedule backup jobs
        await self._schedule_backup_jobs(strategy)
        
        return strategy
    
    async def _create_failover_procedure(
        self,
        plan_id: str,
        procedure_data: Dict[str, Any]
    ) -> FailoverProcedure:
        """Create a failover procedure for the DR plan"""
        procedure = FailoverProcedure(
            id=str(uuid.uuid4()),
            plan_id=plan_id,
            service_name=procedure_data['service_name'],
            failover_mode=FailoverMode(procedure_data['failover_mode']),
            primary_region=procedure_data['primary_region'],
            failover_regions=procedure_data['failover_regions'],
            health_check_url=procedure_data['health_check_url'],
            failover_steps=procedure_data['failover_steps'],
            rollback_steps=procedure_data.get('rollback_steps', []),
            validation_steps=procedure_data.get('validation_steps', []),
            notification_channels=procedure_data.get('notification_channels', []),
            auto_failover_threshold=procedure_data.get('auto_failover_threshold', 3),
            metadata=procedure_data.get('metadata', {}),
            created_at=datetime.utcnow()
        )
        
        return procedure
    
    async def _create_recovery_objectives(
        self,
        plan_id: str,
        recovery_tiers: Dict[str, RecoveryTier]
    ):
        """Create RTO/RPO objectives based on recovery tiers"""
        tier_objectives = {
            RecoveryTier.CRITICAL: {"rto_minutes": 60, "rpo_minutes": 15},
            RecoveryTier.HIGH: {"rto_minutes": 240, "rpo_minutes": 60},
            RecoveryTier.MEDIUM: {"rto_minutes": 1440, "rpo_minutes": 240},
            RecoveryTier.LOW: {"rto_minutes": 4320, "rpo_minutes": 1440}
        }
        
        for service_name, tier in recovery_tiers.items():
            objectives = tier_objectives[tier]
            
            metrics = RecoveryMetrics(
                id=str(uuid.uuid4()),
                plan_id=plan_id,
                service_name=service_name,
                recovery_tier=tier,
                rto_target_minutes=objectives['rto_minutes'],
                rpo_target_minutes=objectives['rpo_minutes'],
                last_backup_time=None,
                last_test_time=None,
                success_rate=0.0,
                created_at=datetime.utcnow()
            )
            
            # Store in cache for quick access
            cache_key = f"dr:metrics:{plan_id}:{service_name}"
            await self.redis_client.set(
                cache_key,
                json.dumps(metrics.dict()),
                ex=3600  # 1 hour cache
            )
    
    async def _initialize_monitoring(
        self,
        plan_id: str,
        recovery_tiers: Dict[str, RecoveryTier]
    ):
        """Initialize health monitoring for critical services"""
        critical_services = [
            service for service, tier in recovery_tiers.items()
            if tier in [RecoveryTier.CRITICAL, RecoveryTier.HIGH]
        ]
        
        for service_name in critical_services:
            # Create monitoring task
            task = asyncio.create_task(
                self._monitor_service_health(plan_id, service_name)
            )
            self.monitoring_tasks.append(task)
    
    async def _monitor_service_health(
        self,
        plan_id: str,
        service_name: str
    ):
        """Continuously monitor service health"""
        while True:
            try:
                # Get failover procedure for this service
                procedure = await self._get_failover_procedure(plan_id, service_name)
                if not procedure:
                    await asyncio.sleep(60)
                    continue
                
                # Check service health
                health_status = await self._check_service_health(
                    procedure.health_check_url
                )
                
                # Update status in cache
                cache_key = f"dr:health:{service_name}"
                await self.redis_client.set(
                    cache_key,
                    health_status.value,
                    ex=300  # 5 minute cache
                )
                
                # Check if automatic failover is needed
                if (health_status == ServiceStatus.FAILED and 
                    procedure.failover_mode == FailoverMode.AUTOMATIC):
                    
                    failure_count = await self._increment_failure_count(service_name)
                    
                    if failure_count >= procedure.auto_failover_threshold:
                        await self.execute_failover(
                            plan_id,
                            service_name,
                            DisasterType.SERVICE_FAILURE,
                            automatic=True
                        )
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring service {service_name}: {e}")
                await asyncio.sleep(60)
    
    async def _check_service_health(self, health_check_url: str) -> ServiceStatus:
        """Check the health status of a service"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    health_check_url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        status = data.get('status', 'healthy').lower()
                        
                        if status == 'healthy':
                            return ServiceStatus.HEALTHY
                        elif status == 'degraded':
                            return ServiceStatus.DEGRADED
                        else:
                            return ServiceStatus.CRITICAL
                    else:
                        return ServiceStatus.FAILED
                        
        except Exception as e:
            logger.error(f"Health check failed for {health_check_url}: {e}")
            return ServiceStatus.FAILED
    
    async def execute_backup(
        self,
        plan_id: str,
        service_name: str,
        backup_type: Optional[BackupType] = None
    ) -> BackupJob:
        """Execute a backup for a specific service"""
        try:
            # Get backup strategy
            strategy = await self._get_backup_strategy(plan_id, service_name)
            if not strategy:
                raise ValueError(f"No backup strategy found for {service_name}")
            
            backup_id = str(uuid.uuid4())
            start_time = datetime.utcnow()
            
            # Create backup job record
            backup_job = BackupJob(
                id=backup_id,
                plan_id=plan_id,
                service_name=service_name,
                backup_type=backup_type or strategy.backup_type,
                status="in_progress",
                start_time=start_time,
                storage_location=None,
                size_bytes=0,
                metadata={}
            )
            
            # Execute backup based on service type
            if service_name == "postgresql":
                result = await self._backup_postgresql(strategy, backup_id)
            elif service_name == "mongodb":
                result = await self._backup_mongodb(strategy, backup_id)
            elif service_name == "opensearch":
                result = await self._backup_opensearch(strategy, backup_id)
            elif service_name == "redis":
                result = await self._backup_redis(strategy, backup_id)
            elif service_name.startswith("storage"):
                result = await self._backup_storage(strategy, backup_id)
            else:
                result = await self._backup_generic_service(strategy, backup_id)
            
            # Update backup job with results
            backup_job.end_time = datetime.utcnow()
            backup_job.status = "completed" if result['success'] else "failed"
            backup_job.storage_location = result.get('storage_location')
            backup_job.size_bytes = result.get('size_bytes', 0)
            backup_job.metadata = result.get('metadata', {})
            
            # Update last backup time in metrics
            await self._update_backup_metrics(plan_id, service_name, backup_job)
            
            logger.info(f"Backup completed for {service_name}: {backup_id}")
            return backup_job
            
        except Exception as e:
            logger.error(f"Backup failed for {service_name}: {e}")
            raise
    
    async def _backup_postgresql(
        self,
        strategy: BackupStrategy,
        backup_id: str
    ) -> Dict[str, Any]:
        """Backup PostgreSQL database"""
        try:
            # Generate backup filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"postgresql_backup_{backup_id}_{timestamp}.sql.gz"
            
            # Execute pg_dump with compression
            dump_command = (
                f"pg_dump {settings.DATABASE_URL} | gzip > /tmp/{filename}"
            )
            
            # In production, use subprocess or dedicated backup tools
            # This is a simplified example
            
            # Upload to S3
            s3_key = f"backups/postgresql/{filename}"
            
            # Mock backup for example
            size_bytes = 1024 * 1024 * 500  # 500MB example
            
            return {
                'success': True,
                'storage_location': f"s3://{settings.BACKUP_BUCKET}/{s3_key}",
                'size_bytes': size_bytes,
                'metadata': {
                    'compression': 'gzip',
                    'encryption': 'AES-256',
                    'checksum': 'sha256:example_checksum'
                }
            }
            
        except Exception as e:
            logger.error(f"PostgreSQL backup failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _backup_mongodb(
        self,
        strategy: BackupStrategy,
        backup_id: str
    ) -> Dict[str, Any]:
        """Backup MongoDB database"""
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"mongodb_backup_{backup_id}_{timestamp}.archive.gz"
            
            # Execute mongodump
            # In production, use proper MongoDB backup tools
            
            s3_key = f"backups/mongodb/{filename}"
            size_bytes = 1024 * 1024 * 300  # 300MB example
            
            return {
                'success': True,
                'storage_location': f"s3://{settings.BACKUP_BUCKET}/{s3_key}",
                'size_bytes': size_bytes,
                'metadata': {
                    'compression': 'gzip',
                    'format': 'archive'
                }
            }
            
        except Exception as e:
            logger.error(f"MongoDB backup failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def execute_failover(
        self,
        plan_id: str,
        service_name: str,
        disaster_type: DisasterType,
        target_region: Optional[str] = None,
        automatic: bool = False
    ) -> FailoverEvent:
        """Execute failover procedure for a service"""
        try:
            if self.recovery_in_progress:
                raise RuntimeError("Another recovery operation is in progress")
            
            self.recovery_in_progress = True
            failover_id = str(uuid.uuid4())
            start_time = datetime.utcnow()
            
            # Get failover procedure
            procedure = await self._get_failover_procedure(plan_id, service_name)
            if not procedure:
                raise ValueError(f"No failover procedure found for {service_name}")
            
            # Create failover event
            failover_event = FailoverEvent(
                id=failover_id,
                plan_id=plan_id,
                service_name=service_name,
                disaster_type=disaster_type,
                failover_mode=FailoverMode.AUTOMATIC if automatic else FailoverMode.MANUAL,
                source_region=procedure.primary_region,
                target_region=target_region or procedure.failover_regions[0],
                status="in_progress",
                start_time=start_time,
                steps_completed=[],
                validation_results={},
                metadata={}
            )
            
            # Send initial notifications
            await self._send_failover_notification(
                failover_event,
                "Failover initiated",
                procedure.notification_channels
            )
            
            # Execute failover steps
            for step in procedure.failover_steps:
                try:
                    await self._execute_failover_step(
                        failover_event,
                        step,
                        procedure
                    )
                    failover_event.steps_completed.append(step['name'])
                except Exception as e:
                    logger.error(f"Failover step failed: {step['name']} - {e}")
                    failover_event.status = "failed"
                    failover_event.metadata['failure_reason'] = str(e)
                    
                    # Attempt rollback
                    await self._execute_rollback(failover_event, procedure)
                    break
            
            # Validate failover if all steps completed
            if len(failover_event.steps_completed) == len(procedure.failover_steps):
                validation_passed = await self._validate_failover(
                    failover_event,
                    procedure
                )
                
                failover_event.status = "completed" if validation_passed else "validation_failed"
            
            failover_event.end_time = datetime.utcnow()
            
            # Send completion notification
            await self._send_failover_notification(
                failover_event,
                f"Failover {failover_event.status}",
                procedure.notification_channels
            )
            
            # Update recovery metrics
            await self._update_recovery_metrics(plan_id, service_name, failover_event)
            
            self.recovery_in_progress = False
            
            logger.info(f"Failover {failover_event.status} for {service_name}: {failover_id}")
            return failover_event
            
        except Exception as e:
            self.recovery_in_progress = False
            logger.error(f"Failover failed for {service_name}: {e}")
            raise
    
    async def _execute_failover_step(
        self,
        failover_event: FailoverEvent,
        step: Dict[str, Any],
        procedure: FailoverProcedure
    ):
        """Execute a single failover step"""
        step_type = step['type']
        
        if step_type == 'update_dns':
            await self._update_dns_records(
                step['domain'],
                failover_event.target_region
            )
        elif step_type == 'update_load_balancer':
            await self._update_load_balancer(
                step['load_balancer_id'],
                failover_event.target_region
            )
        elif step_type == 'scale_resources':
            await self._scale_resources(
                failover_event.service_name,
                failover_event.target_region,
                step['scale_factor']
            )
        elif step_type == 'sync_data':
            await self._sync_data(
                failover_event.service_name,
                failover_event.source_region,
                failover_event.target_region
            )
        elif step_type == 'update_configuration':
            await self._update_service_configuration(
                failover_event.service_name,
                failover_event.target_region,
                step['config_updates']
            )
        elif step_type == 'custom_script':
            await self._execute_custom_script(
                step['script_path'],
                step.get('parameters', {})
            )
    
    async def conduct_recovery_test(
        self,
        plan_id: str,
        test_type: str,
        services: List[str],
        scenario: Dict[str, Any]
    ) -> RecoveryTest:
        """Conduct a disaster recovery test/drill"""
        try:
            test_id = str(uuid.uuid4())
            start_time = datetime.utcnow()
            
            # Create recovery test record
            recovery_test = RecoveryTest(
                id=test_id,
                plan_id=plan_id,
                test_type=test_type,
                services_tested=services,
                scenario=scenario,
                status="in_progress",
                start_time=start_time,
                results={},
                issues_found=[],
                recommendations=[],
                metadata={}
            )
            
            # Execute test based on type
            if test_type == "tabletop":
                results = await self._conduct_tabletop_exercise(
                    plan_id,
                    services,
                    scenario
                )
            elif test_type == "backup_restore":
                results = await self._test_backup_restore(
                    plan_id,
                    services
                )
            elif test_type == "failover":
                results = await self._test_failover(
                    plan_id,
                    services,
                    scenario
                )
            elif test_type == "full_simulation":
                results = await self._conduct_full_simulation(
                    plan_id,
                    services,
                    scenario
                )
            else:
                raise ValueError(f"Unknown test type: {test_type}")
            
            # Update test record with results
            recovery_test.end_time = datetime.utcnow()
            recovery_test.status = "completed"
            recovery_test.results = results['test_results']
            recovery_test.issues_found = results['issues']
            recovery_test.recommendations = results['recommendations']
            recovery_test.success_rate = results['success_rate']
            
            # Update test metrics
            await self._update_test_metrics(plan_id, services, recovery_test)
            
            # Generate test report
            report = await self._generate_test_report(recovery_test)
            recovery_test.metadata['report_url'] = report['url']
            
            logger.info(f"Recovery test completed: {test_id}")
            return recovery_test
            
        except Exception as e:
            logger.error(f"Recovery test failed: {e}")
            raise
    
    async def _test_backup_restore(
        self,
        plan_id: str,
        services: List[str]
    ) -> Dict[str, Any]:
        """Test backup and restore procedures"""
        test_results = {}
        issues = []
        recommendations = []
        successful_tests = 0
        
        for service_name in services:
            try:
                # Create test backup
                backup_job = await self.execute_backup(
                    plan_id,
                    service_name,
                    BackupType.FULL
                )
                
                if backup_job.status != "completed":
                    issues.append({
                        'service': service_name,
                        'issue': 'Backup failed',
                        'severity': 'high'
                    })
                    continue
                
                # Test restore (in isolated environment)
                restore_result = await self._test_restore_backup(
                    backup_job,
                    service_name
                )
                
                test_results[service_name] = {
                    'backup_time': (backup_job.end_time - backup_job.start_time).seconds,
                    'restore_time': restore_result['restore_time'],
                    'data_integrity': restore_result['integrity_check'],
                    'success': restore_result['success']
                }
                
                if restore_result['success']:
                    successful_tests += 1
                else:
                    issues.append({
                        'service': service_name,
                        'issue': restore_result['error'],
                        'severity': 'high'
                    })
                
            except Exception as e:
                issues.append({
                    'service': service_name,
                    'issue': str(e),
                    'severity': 'critical'
                })
        
        # Generate recommendations
        if issues:
            recommendations.append({
                'category': 'backup_procedures',
                'recommendation': 'Review and update backup procedures for failed services',
                'priority': 'high'
            })
        
        success_rate = (successful_tests / len(services)) * 100 if services else 0
        
        return {
            'test_results': test_results,
            'issues': issues,
            'recommendations': recommendations,
            'success_rate': success_rate
        }
    
    async def create_business_continuity_plan(
        self,
        dr_plan_id: str,
        critical_functions: List[Dict[str, Any]],
        communication_plan: Dict[str, Any],
        emergency_procedures: List[Dict[str, Any]],
        resource_requirements: Dict[str, Any]
    ) -> BusinessContinuityPlan:
        """Create a business continuity plan"""
        try:
            bcp_id = str(uuid.uuid4())
            
            # Create BCP
            bcp = BusinessContinuityPlan(
                id=bcp_id,
                dr_plan_id=dr_plan_id,
                critical_functions=critical_functions,
                communication_plan=communication_plan,
                emergency_procedures=emergency_procedures,
                resource_requirements=resource_requirements,
                activation_criteria={
                    'rto_breach': True,
                    'multiple_service_failure': True,
                    'data_loss_threshold': 100,  # GB
                    'user_impact_threshold': 1000  # users
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_active=True
            )
            
            # Create emergency contact database
            await self._create_emergency_contacts(bcp_id, communication_plan)
            
            # Set up automated activation monitoring
            await self._setup_bcp_monitoring(bcp)
            
            logger.info(f"Created business continuity plan: {bcp_id}")
            return bcp
            
        except Exception as e:
            logger.error(f"Failed to create business continuity plan: {e}")
            raise
    
    async def get_recovery_dashboard(
        self,
        plan_id: str
    ) -> Dict[str, Any]:
        """Get comprehensive recovery dashboard data"""
        try:
            # Get plan details
            plan = await self._get_disaster_recovery_plan(plan_id)
            
            # Get current service health
            service_health = {}
            for service_name in plan.recovery_tiers.keys():
                health_key = f"dr:health:{service_name}"
                health_status = await self.redis_client.get(health_key)
                service_health[service_name] = health_status or "unknown"
            
            # Get backup status
            backup_status = await self._get_backup_status(plan_id)
            
            # Get recovery metrics
            recovery_metrics = await self._get_recovery_metrics(plan_id)
            
            # Get recent events
            recent_events = await self._get_recent_events(plan_id, limit=10)
            
            # Calculate overall readiness score
            readiness_score = await self._calculate_readiness_score(
                plan_id,
                service_health,
                backup_status,
                recovery_metrics
            )
            
            return {
                'plan_id': plan_id,
                'plan_name': plan.name,
                'service_health': service_health,
                'backup_status': backup_status,
                'recovery_metrics': recovery_metrics,
                'recent_events': recent_events,
                'readiness_score': readiness_score,
                'last_test_date': recovery_metrics.get('last_test_date'),
                'next_test_date': recovery_metrics.get('next_test_date'),
                'compliance_status': {
                    'rto_compliance': recovery_metrics.get('rto_compliance', 0),
                    'rpo_compliance': recovery_metrics.get('rpo_compliance', 0),
                    'backup_compliance': backup_status.get('compliance_rate', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get recovery dashboard: {e}")
            raise
    
    async def _calculate_readiness_score(
        self,
        plan_id: str,
        service_health: Dict[str, str],
        backup_status: Dict[str, Any],
        recovery_metrics: Dict[str, Any]
    ) -> float:
        """Calculate overall disaster recovery readiness score"""
        scores = []
        
        # Service health score (40% weight)
        healthy_services = sum(
            1 for status in service_health.values()
            if status == ServiceStatus.HEALTHY.value
        )
        health_score = (healthy_services / len(service_health)) * 100 if service_health else 0
        scores.append(health_score * 0.4)
        
        # Backup compliance score (30% weight)
        backup_score = backup_status.get('compliance_rate', 0)
        scores.append(backup_score * 0.3)
        
        # RTO/RPO compliance score (20% weight)
        rto_compliance = recovery_metrics.get('rto_compliance', 0)
        rpo_compliance = recovery_metrics.get('rpo_compliance', 0)
        compliance_score = (rto_compliance + rpo_compliance) / 2
        scores.append(compliance_score * 0.2)
        
        # Testing score (10% weight)
        last_test_date = recovery_metrics.get('last_test_date')
        if last_test_date:
            days_since_test = (datetime.utcnow() - last_test_date).days
            test_score = max(0, 100 - (days_since_test * 2))  # -2 points per day
        else:
            test_score = 0
        scores.append(test_score * 0.1)
        
        return sum(scores)
    
    async def generate_recovery_runbook(
        self,
        plan_id: str,
        disaster_type: DisasterType,
        affected_services: List[str]
    ) -> Dict[str, Any]:
        """Generate a step-by-step recovery runbook"""
        try:
            runbook = {
                'id': str(uuid.uuid4()),
                'plan_id': plan_id,
                'disaster_type': disaster_type.value,
                'affected_services': affected_services,
                'generated_at': datetime.utcnow().isoformat(),
                'steps': []
            }
            
            # Initial assessment steps
            runbook['steps'].extend([
                {
                    'order': 1,
                    'phase': 'assessment',
                    'action': 'Activate incident response team',
                    'responsible': 'Incident Commander',
                    'duration_minutes': 15,
                    'critical': True
                },
                {
                    'order': 2,
                    'phase': 'assessment',
                    'action': 'Assess scope and impact of disaster',
                    'responsible': 'Technical Lead',
                    'duration_minutes': 30,
                    'critical': True
                }
            ])
            
            # Service-specific recovery steps
            step_order = 3
            for service_name in affected_services:
                service_steps = await self._generate_service_recovery_steps(
                    plan_id,
                    service_name,
                    disaster_type,
                    step_order
                )
                runbook['steps'].extend(service_steps)
                step_order += len(service_steps)
            
            # Validation steps
            runbook['steps'].extend([
                {
                    'order': step_order,
                    'phase': 'validation',
                    'action': 'Verify all services are operational',
                    'responsible': 'Operations Team',
                    'duration_minutes': 60,
                    'critical': True
                },
                {
                    'order': step_order + 1,
                    'phase': 'validation',
                    'action': 'Conduct user acceptance testing',
                    'responsible': 'QA Team',
                    'duration_minutes': 120,
                    'critical': False
                }
            ])
            
            # Calculate total recovery time
            total_duration = sum(step['duration_minutes'] for step in runbook['steps'])
            runbook['estimated_recovery_time_hours'] = total_duration / 60
            
            # Generate printable version
            runbook['printable_url'] = await self._generate_printable_runbook(runbook)
            
            return runbook
            
        except Exception as e:
            logger.error(f"Failed to generate recovery runbook: {e}")
            raise
    
    async def _generate_service_recovery_steps(
        self,
        plan_id: str,
        service_name: str,
        disaster_type: DisasterType,
        start_order: int
    ) -> List[Dict[str, Any]]:
        """Generate recovery steps for a specific service"""
        steps = []
        order = start_order
        
        # Get service recovery tier
        plan = await self._get_disaster_recovery_plan(plan_id)
        recovery_tier = plan.recovery_tiers.get(service_name, RecoveryTier.MEDIUM)
        
        # Common steps for all services
        if disaster_type == DisasterType.DATA_CORRUPTION:
            steps.append({
                'order': order,
                'phase': 'recovery',
                'action': f'Stop {service_name} to prevent further corruption',
                'responsible': 'Operations Team',
                'duration_minutes': 5,
                'critical': True,
                'service': service_name
            })
            order += 1
            
            steps.append({
                'order': order,
                'phase': 'recovery',
                'action': f'Restore {service_name} from last known good backup',
                'responsible': 'Database Team',
                'duration_minutes': 60,
                'critical': True,
                'service': service_name
            })
            order += 1
            
        elif disaster_type in [DisasterType.HARDWARE_FAILURE, DisasterType.PROVIDER_OUTAGE]:
            steps.append({
                'order': order,
                'phase': 'recovery',
                'action': f'Initiate failover for {service_name}',
                'responsible': 'Infrastructure Team',
                'duration_minutes': 15,
                'critical': True,
                'service': service_name
            })
            order += 1
            
        # Add service-specific steps
        if service_name == "postgresql":
            steps.extend([
                {
                    'order': order,
                    'phase': 'recovery',
                    'action': 'Verify database consistency',
                    'responsible': 'Database Team',
                    'duration_minutes': 30,
                    'critical': True,
                    'service': service_name
                },
                {
                    'order': order + 1,
                    'phase': 'recovery',
                    'action': 'Rebuild indexes if needed',
                    'responsible': 'Database Team',
                    'duration_minutes': 45,
                    'critical': False,
                    'service': service_name
                }
            ])
            
        return steps


class BackupManager:
    """Manages backup operations and scheduling"""
    
    def __init__(self, dr_service: DisasterRecoveryService):
        self.dr_service = dr_service
        self.scheduled_jobs = {}
    
    async def schedule_backup_jobs(self, strategy: BackupStrategy):
        """Schedule recurring backup jobs based on strategy"""
        # Implementation would use APScheduler or similar
        # This is a simplified example
        job_id = f"backup_{strategy.id}"
        
        self.scheduled_jobs[job_id] = {
            'strategy': strategy,
            'next_run': self._calculate_next_run(strategy.frequency),
            'active': True
        }
    
    def _calculate_next_run(self, cron_expression: str) -> datetime:
        """Calculate next run time from cron expression"""
        # Use croniter or similar library in production
        # Simple example: assume daily at midnight
        tomorrow = datetime.utcnow() + timedelta(days=1)
        return tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
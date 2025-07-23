"""
Scheduler service for managing scheduled ingest operations
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import BackgroundTasks

from ..models.schemas import ScheduledIngestConfig, IngestJobCreate, IngestType
from ..core.config import settings
from ..core.exceptions import SchedulerError, IngestServiceError
from ..core.logging import get_logger, log_ingest_event
from .ingest_service import IngestService

logger = get_logger(__name__)


class SchedulerService:
    """Service for managing scheduled ingest operations"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.ingest_service: Optional[IngestService] = None
        self.scheduled_ingests: Dict[str, ScheduledIngestConfig] = {}
        self._is_running = False
    
    async def initialize(self, ingest_service: IngestService):
        """Initialize the scheduler service"""
        self.ingest_service = ingest_service
        
        # Load existing scheduled ingests
        await self._load_scheduled_ingests()
        
        # Start the scheduler
        self.scheduler.start()
        self._is_running = True
        
        logger.info(
            "scheduler_service_initialized",
            scheduled_ingest_count=len(self.scheduled_ingests)
        )
    
    async def _load_scheduled_ingests(self):
        """Load scheduled ingest configurations from storage"""
        # In a real implementation, this would load from database
        # For now, we'll initialize with empty dict
        pass
    
    async def create_scheduled_ingest(self, config: ScheduledIngestConfig) -> ScheduledIngestConfig:
        """Create a new scheduled ingest configuration"""
        try:
            # Validate cron expression
            try:
                CronTrigger.from_crontab(config.cron_expression)
            except Exception as e:
                raise SchedulerError(f"Invalid cron expression: {str(e)}")
            
            # Store configuration
            self.scheduled_ingests[config.id] = config
            
            # Schedule the job if enabled
            if config.enabled:
                await self._schedule_ingest_job(config)
            
            logger.info(
                "scheduled_ingest_created",
                scheduled_ingest_id=config.id,
                cron_expression=config.cron_expression,
                enabled=config.enabled
            )
            
            return config
            
        except Exception as e:
            logger.error(
                "failed_to_create_scheduled_ingest",
                error=str(e),
                cron_expression=config.cron_expression
            )
            raise SchedulerError(f"Failed to create scheduled ingest: {str(e)}")
    
    async def list_scheduled_ingests(self) -> List[ScheduledIngestConfig]:
        """List all scheduled ingest configurations"""
        return list(self.scheduled_ingests.values())
    
    async def get_scheduled_ingest(self, ingest_id: str) -> Optional[ScheduledIngestConfig]:
        """Get a specific scheduled ingest configuration"""
        return self.scheduled_ingests.get(ingest_id)
    
    async def update_scheduled_ingest(
        self,
        ingest_id: str,
        config: ScheduledIngestConfig
    ) -> Optional[ScheduledIngestConfig]:
        """Update a scheduled ingest configuration"""
        if ingest_id not in self.scheduled_ingests:
            return None
        
        old_config = self.scheduled_ingests[ingest_id]
        
        try:
            # Remove old scheduled job
            if old_config.enabled:
                await self._unschedule_ingest_job(ingest_id)
            
            # Update configuration
            config.id = ingest_id  # Ensure ID consistency
            self.scheduled_ingests[ingest_id] = config
            
            # Schedule new job if enabled
            if config.enabled:
                await self._schedule_ingest_job(config)
            
            logger.info(
                "scheduled_ingest_updated",
                scheduled_ingest_id=ingest_id,
                cron_expression=config.cron_expression,
                enabled=config.enabled
            )
            
            return config
            
        except Exception as e:
            # Restore old configuration on error
            self.scheduled_ingests[ingest_id] = old_config
            if old_config.enabled:
                await self._schedule_ingest_job(old_config)
            
            logger.error(
                "failed_to_update_scheduled_ingest",
                error=str(e),
                ingest_id=ingest_id
            )
            raise SchedulerError(f"Failed to update scheduled ingest: {str(e)}")
    
    async def delete_scheduled_ingest(self, ingest_id: str) -> bool:
        """Delete a scheduled ingest configuration"""
        if ingest_id not in self.scheduled_ingests:
            return False
        
        try:
            # Remove scheduled job
            await self._unschedule_ingest_job(ingest_id)
            
            # Remove configuration
            del self.scheduled_ingests[ingest_id]
            
            logger.info("scheduled_ingest_deleted", scheduled_ingest_id=ingest_id)
            
            return True
            
        except Exception as e:
            logger.error(
                "failed_to_delete_scheduled_ingest",
                error=str(e),
                ingest_id=ingest_id
            )
            raise SchedulerError(f"Failed to delete scheduled ingest: {str(e)}")
    
    async def run_scheduled_ingest(
        self,
        ingest_id: str,
        background_tasks: BackgroundTasks
    ) -> bool:
        """Manually trigger a scheduled ingest"""
        if ingest_id not in self.scheduled_ingests:
            return False
        
        config = self.scheduled_ingests[ingest_id]
        
        try:
            # Execute the scheduled ingest
            background_tasks.add_task(
                self._execute_scheduled_ingest,
                config
            )
            
            logger.info(
                "scheduled_ingest_manually_triggered",
                scheduled_ingest_id=ingest_id
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "failed_to_run_scheduled_ingest",
                error=str(e),
                ingest_id=ingest_id
            )
            return False
    
    async def _schedule_ingest_job(self, config: ScheduledIngestConfig):
        """Schedule an ingest job using APScheduler"""
        try:
            job_id = f"scheduled_ingest_{config.id}"
            
            # Remove existing job if it exists
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # Add new job
            self.scheduler.add_job(
                func=self._execute_scheduled_ingest,
                trigger=CronTrigger.from_crontab(config.cron_expression),
                args=[config],
                id=job_id,
                name=f"Scheduled Ingest: {config.name}",
                max_instances=1,  # Prevent overlapping executions
                coalesce=True,    # Combine missed executions
                misfire_grace_time=300  # 5 minutes grace time
            )
            
            logger.info(
                "scheduled_ingest_job_added",
                scheduled_ingest_id=config.id,
                job_id=job_id,
                cron_expression=config.cron_expression
            )
            
        except Exception as e:
            logger.error(
                "failed_to_schedule_ingest_job",
                error=str(e),
                scheduled_ingest_id=config.id
            )
            raise SchedulerError(f"Failed to schedule ingest job: {str(e)}")
    
    async def _unschedule_ingest_job(self, ingest_id: str):
        """Remove a scheduled ingest job"""
        try:
            job_id = f"scheduled_ingest_{ingest_id}"
            
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                
                logger.info(
                    "scheduled_ingest_job_removed",
                    scheduled_ingest_id=ingest_id,
                    job_id=job_id
                )
            
        except Exception as e:
            logger.error(
                "failed_to_unschedule_ingest_job",
                error=str(e),
                ingest_id=ingest_id
            )
    
    async def _execute_scheduled_ingest(self, config: ScheduledIngestConfig):
        """Execute a scheduled ingest operation"""
        try:
            if not self.ingest_service:
                raise IngestServiceError("Ingest service not initialized")
            
            execution_time = datetime.utcnow()
            
            logger.info(
                "executing_scheduled_ingest",
                scheduled_ingest_id=config.id,
                source_path=config.source_path,
                execution_time=execution_time.isoformat()
            )
            
            # Create ingest job request
            job_request = IngestJobCreate(
                source_path=config.source_path,
                destination_project_id=config.destination_project_id,
                ingest_type=IngestType.SCHEDULED,
                validation_rules=config.validation_rules,
                metadata_override=config.metadata_template or {},
                tags=config.tags or [],
                priority=config.priority,
                auto_generate_proxies=config.auto_generate_proxies,
                preserve_folder_structure=config.preserve_folder_structure
            )
            
            # Create and process job
            job = await self.ingest_service.create_job(job_request)
            
            # Process job
            await self.ingest_service.process_job(job.id)
            
            # Update last execution time
            config.last_execution = execution_time
            
            log_ingest_event(
                logger,
                "scheduled_ingest_executed",
                config.source_path,
                job_id=job.id,
                scheduled_ingest_id=config.id,
                execution_time=execution_time.isoformat()
            )
            
        except Exception as e:
            logger.error(
                "scheduled_ingest_execution_failed",
                error=str(e),
                scheduled_ingest_id=config.id,
                source_path=config.source_path
            )
            
            # Update last execution time even on failure
            config.last_execution = datetime.utcnow()
    
    async def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        jobs = self.scheduler.get_jobs()
        
        stats = {
            "is_running": self._is_running,
            "total_scheduled_ingests": len(self.scheduled_ingests),
            "active_scheduled_ingests": len([c for c in self.scheduled_ingests.values() if c.enabled]),
            "scheduled_jobs": len(jobs),
            "next_run_times": []
        }
        
        # Get next run times
        for job in jobs:
            if job.next_run_time:
                stats["next_run_times"].append({
                    "job_id": job.id,
                    "job_name": job.name,
                    "next_run_time": job.next_run_time.isoformat()
                })
        
        return stats
    
    async def shutdown(self):
        """Shutdown the scheduler service"""
        try:
            if self._is_running:
                self.scheduler.shutdown(wait=True)
                self._is_running = False
                
                logger.info("scheduler_service_shutdown")
            
        except Exception as e:
            logger.error("scheduler_shutdown_failed", error=str(e))


# Dependency injection
_scheduler_service: Optional[SchedulerService] = None


async def get_scheduler_service() -> SchedulerService:
    """Get scheduler service instance"""
    global _scheduler_service
    
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
        # Note: initialization with ingest_service happens in main.py
    
    return _scheduler_service
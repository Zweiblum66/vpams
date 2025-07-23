"""
Workflow Trigger Service

This module handles workflow triggers, including:
- Schedule-based triggers (cron)
- Event-based triggers
- Webhook triggers
- File watch triggers
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import structlog
from croniter import croniter
import aioredis

from ..models.schemas import (
    TriggerConfig, TriggerType, WorkflowDefinition,
    WorkflowPriority
)
from ..db.models import (
    WorkflowDefinition as WorkflowDefinitionDB,
    WorkflowTrigger as WorkflowTriggerDB
)
from .workflow_engine import WorkflowEngine
from ..core.config import settings

logger = structlog.get_logger()


class TriggerService:
    """
    Service for managing workflow triggers
    """
    
    def __init__(self, db_session: AsyncSession, redis_client: aioredis.Redis = None):
        self.db = db_session
        self.redis = redis_client
        self.engine = WorkflowEngine(db_session, redis_client)
        self.active_triggers: Dict[str, asyncio.Task] = {}
        self.webhook_subscriptions: Dict[str, List[str]] = {}
        self.event_subscriptions: Dict[str, List[str]] = {}
        
    async def start(self):
        """
        Start trigger service
        """
        logger.info("Starting trigger service")
        
        # Load all active triggers
        await self._load_active_triggers()
        
        # Start scheduler
        asyncio.create_task(self._schedule_checker())
        
        # Start event listener
        if self.redis:
            asyncio.create_task(self._event_listener())
        
        logger.info("Trigger service started")
    
    async def stop(self):
        """
        Stop trigger service
        """
        logger.info("Stopping trigger service")
        
        # Cancel all active triggers
        for task_id, task in self.active_triggers.items():
            task.cancel()
        
        self.active_triggers.clear()
        
        logger.info("Trigger service stopped")
    
    async def _load_active_triggers(self):
        """
        Load all active workflow triggers
        """
        # Get all enabled workflows with triggers
        result = await self.db.execute(
            select(WorkflowDefinitionDB).where(
                and_(
                    WorkflowDefinitionDB.enabled == True,
                    WorkflowDefinitionDB.deleted == False,
                    WorkflowDefinitionDB.triggers != []
                )
            )
        )
        workflows = result.scalars().all()
        
        for workflow in workflows:
            for trigger_config in workflow.triggers:
                await self._register_trigger(
                    workflow.workflow_id,
                    TriggerConfig(**trigger_config)
                )
        
        logger.info(
            "Loaded active triggers",
            workflow_count=len(workflows),
            trigger_count=len(self.active_triggers)
        )
    
    async def _register_trigger(
        self,
        workflow_id: str,
        trigger: TriggerConfig
    ):
        """
        Register a workflow trigger
        """
        trigger_key = f"{workflow_id}:{trigger.trigger_id}"
        
        if trigger.trigger_type == TriggerType.SCHEDULE:
            # Schedule triggers are handled by the scheduler
            pass
        
        elif trigger.trigger_type == TriggerType.WEBHOOK:
            # Register webhook endpoint
            webhook_path = trigger.webhook_config.get("path", f"/webhooks/{workflow_id}")
            if webhook_path not in self.webhook_subscriptions:
                self.webhook_subscriptions[webhook_path] = []
            self.webhook_subscriptions[webhook_path].append(workflow_id)
        
        elif trigger.trigger_type == TriggerType.EVENT:
            # Register event subscriptions
            for event in trigger.events:
                event_type = event.get("event_type")
                if event_type not in self.event_subscriptions:
                    self.event_subscriptions[event_type] = []
                self.event_subscriptions[event_type].append(workflow_id)
        
        elif trigger.trigger_type == TriggerType.FILE_WATCH:
            # Start file watcher
            task = asyncio.create_task(
                self._file_watcher(workflow_id, trigger)
            )
            self.active_triggers[trigger_key] = task
        
        elif trigger.trigger_type == TriggerType.API:
            # API triggers are handled on-demand
            pass
        
        logger.debug(
            "Registered trigger",
            workflow_id=workflow_id,
            trigger_type=trigger.trigger_type.value
        )
    
    async def _schedule_checker(self):
        """
        Check and execute scheduled workflows
        """
        while True:
            try:
                # Check every minute
                await asyncio.sleep(60)
                
                # Get workflows with schedule triggers
                result = await self.db.execute(
                    select(WorkflowDefinitionDB).where(
                        and_(
                            WorkflowDefinitionDB.enabled == True,
                            WorkflowDefinitionDB.deleted == False
                        )
                    )
                )
                workflows = result.scalars().all()
                
                now = datetime.utcnow()
                
                for workflow in workflows:
                    for trigger_config in workflow.triggers:
                        trigger = TriggerConfig(**trigger_config)
                        
                        if trigger.trigger_type == TriggerType.SCHEDULE:
                            # Check if should execute
                            if await self._should_execute_schedule(
                                workflow.workflow_id,
                                trigger,
                                now
                            ):
                                # Execute workflow
                                await self._trigger_workflow(
                                    workflow.workflow_id,
                                    trigger,
                                    {"scheduled_time": now.isoformat()}
                                )
                
            except Exception as e:
                logger.error("Schedule checker error", error=str(e))
    
    async def _should_execute_schedule(
        self,
        workflow_id: str,
        trigger: TriggerConfig,
        now: datetime
    ) -> bool:
        """
        Check if scheduled workflow should execute
        """
        schedule = trigger.schedule
        
        if schedule.schedule_type == "cron":
            # Parse cron expression
            cron = croniter(schedule.cron_expression, now)
            prev_run = cron.get_prev(datetime)
            
            # Check if we should have run in the last minute
            if now - prev_run < timedelta(minutes=1):
                # Check if already executed
                last_run_key = f"schedule:{workflow_id}:{trigger.trigger_id}:last_run"
                
                if self.redis:
                    last_run = await self.redis.get(last_run_key)
                    if last_run:
                        last_run_time = datetime.fromisoformat(last_run.decode())
                        if last_run_time >= prev_run:
                            return False
                    
                    # Mark as executed
                    await self.redis.setex(
                        last_run_key,
                        86400,  # 24 hours
                        now.isoformat()
                    )
                
                return True
        
        elif schedule.schedule_type == "interval":
            # Check interval
            interval_minutes = schedule.interval_minutes
            
            # Check last execution
            last_run_key = f"schedule:{workflow_id}:{trigger.trigger_id}:last_run"
            
            if self.redis:
                last_run = await self.redis.get(last_run_key)
                if last_run:
                    last_run_time = datetime.fromisoformat(last_run.decode())
                    if now - last_run_time < timedelta(minutes=interval_minutes):
                        return False
                
                # Mark as executed
                await self.redis.setex(
                    last_run_key,
                    86400,  # 24 hours
                    now.isoformat()
                )
            
            return True
        
        elif schedule.schedule_type == "once":
            # Check if scheduled time has passed
            scheduled_at = datetime.fromisoformat(schedule.scheduled_at)
            
            if now >= scheduled_at:
                # Check if already executed
                executed_key = f"schedule:{workflow_id}:{trigger.trigger_id}:executed"
                
                if self.redis:
                    if await self.redis.exists(executed_key):
                        return False
                    
                    # Mark as executed
                    await self.redis.set(executed_key, "1")
                
                return True
        
        return False
    
    async def _event_listener(self):
        """
        Listen for events from Redis pub/sub
        """
        if not self.redis:
            return
        
        # Subscribe to workflow events channel
        pubsub = self.redis.pubsub()
        await pubsub.subscribe("workflow:events")
        
        logger.info("Event listener started")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        # Parse event
                        event_data = json.loads(message["data"])
                        event_type = event_data.get("event_type")
                        
                        # Find subscribed workflows
                        workflow_ids = self.event_subscriptions.get(event_type, [])
                        
                        for workflow_id in workflow_ids:
                            # Get trigger config
                            workflow = await self._get_workflow(workflow_id)
                            if workflow:
                                for trigger_config in workflow.triggers:
                                    trigger = TriggerConfig(**trigger_config)
                                    
                                    if (trigger.trigger_type == TriggerType.EVENT and
                                        any(e.get("event_type") == event_type for e in trigger.events)):
                                        
                                        # Check event filters
                                        if self._match_event_filters(
                                            event_data,
                                            trigger.events
                                        ):
                                            # Trigger workflow
                                            await self._trigger_workflow(
                                                workflow_id,
                                                trigger,
                                                event_data
                                            )
                        
                    except Exception as e:
                        logger.error(
                            "Error processing event",
                            error=str(e),
                            event=message["data"]
                        )
        
        except asyncio.CancelledError:
            await pubsub.unsubscribe("workflow:events")
            raise
    
    async def _file_watcher(
        self,
        workflow_id: str,
        trigger: TriggerConfig
    ):
        """
        Watch for file changes
        """
        file_watch = trigger.file_watch
        path = file_watch.get("path")
        pattern = file_watch.get("pattern", "*")
        events = file_watch.get("events", ["created"])
        
        logger.info(
            "Starting file watcher",
            workflow_id=workflow_id,
            path=path,
            pattern=pattern
        )
        
        # This is a simplified implementation
        # In production, use inotify or similar
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Check for new files (simplified)
                # In real implementation, track file state
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "File watcher error",
                    workflow_id=workflow_id,
                    error=str(e)
                )
    
    async def _trigger_workflow(
        self,
        workflow_id: str,
        trigger: TriggerConfig,
        trigger_data: Dict[str, Any]
    ):
        """
        Trigger workflow execution
        """
        try:
            logger.info(
                "Triggering workflow",
                workflow_id=workflow_id,
                trigger_type=trigger.trigger_type.value
            )
            
            # Create workflow instance
            instance = await self.engine.create_workflow_instance(
                workflow_id=workflow_id,
                input_data=trigger.input_mapping or {},
                triggered_by="trigger",
                trigger_type=trigger.trigger_type.value,
                trigger_data=trigger_data,
                priority=WorkflowPriority.HIGH if trigger.trigger_type == TriggerType.EVENT else None
            )
            
            # Execute workflow
            await self.engine.execute_workflow(
                instance.instance_id,
                background=True
            )
            
        except Exception as e:
            logger.error(
                "Failed to trigger workflow",
                workflow_id=workflow_id,
                trigger_type=trigger.trigger_type.value,
                error=str(e)
            )
    
    async def handle_webhook(
        self,
        path: str,
        method: str,
        headers: Dict[str, str],
        body: Any
    ) -> Dict[str, Any]:
        """
        Handle incoming webhook
        """
        # Find workflows subscribed to this webhook
        workflow_ids = self.webhook_subscriptions.get(path, [])
        
        if not workflow_ids:
            return {"status": "error", "message": "No workflow found for webhook"}
        
        triggered_count = 0
        
        for workflow_id in workflow_ids:
            workflow = await self._get_workflow(workflow_id)
            if workflow:
                for trigger_config in workflow.triggers:
                    trigger = TriggerConfig(**trigger_config)
                    
                    if (trigger.trigger_type == TriggerType.WEBHOOK and
                        trigger.webhook_config.get("path") == path):
                        
                        # Validate webhook if configured
                        if not await self._validate_webhook(
                            trigger.webhook_config,
                            headers,
                            body
                        ):
                            continue
                        
                        # Trigger workflow
                        await self._trigger_workflow(
                            workflow_id,
                            trigger,
                            {
                                "webhook_path": path,
                                "method": method,
                                "headers": headers,
                                "body": body
                            }
                        )
                        triggered_count += 1
        
        return {
            "status": "success",
            "triggered_workflows": triggered_count
        }
    
    async def _validate_webhook(
        self,
        webhook_config: Dict[str, Any],
        headers: Dict[str, str],
        body: Any
    ) -> bool:
        """
        Validate webhook request
        """
        # Check authentication if configured
        auth_type = webhook_config.get("auth_type")
        
        if auth_type == "token":
            expected_token = webhook_config.get("auth_token")
            provided_token = headers.get("Authorization", "").replace("Bearer ", "")
            if provided_token != expected_token:
                return False
        
        elif auth_type == "signature":
            # Validate signature (e.g., HMAC)
            # Implementation depends on signature method
            pass
        
        return True
    
    def _match_event_filters(
        self,
        event_data: Dict[str, Any],
        event_configs: List[Dict[str, Any]]
    ) -> bool:
        """
        Check if event matches filters
        """
        event_type = event_data.get("event_type")
        
        for event_config in event_configs:
            if event_config.get("event_type") == event_type:
                # Check filters
                filters = event_config.get("filters", {})
                
                for key, value in filters.items():
                    if event_data.get(key) != value:
                        return False
                
                return True
        
        return False
    
    async def _get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinitionDB]:
        """
        Get workflow definition
        """
        result = await self.db.execute(
            select(WorkflowDefinitionDB).where(
                and_(
                    WorkflowDefinitionDB.workflow_id == workflow_id,
                    WorkflowDefinitionDB.enabled == True,
                    WorkflowDefinitionDB.deleted == False
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def trigger_api_workflow(
        self,
        workflow_id: str,
        api_key: str,
        input_data: Dict[str, Any]
    ) -> str:
        """
        Trigger workflow via API
        """
        # Validate API key
        workflow = await self._get_workflow(workflow_id)
        if not workflow:
            raise ValueError("Workflow not found")
        
        # Find API trigger
        api_trigger = None
        for trigger_config in workflow.triggers:
            trigger = TriggerConfig(**trigger_config)
            if (trigger.trigger_type == TriggerType.API and
                trigger.api_config.get("api_key") == api_key):
                api_trigger = trigger
                break
        
        if not api_trigger:
            raise ValueError("Invalid API key")
        
        # Check rate limits if configured
        if api_trigger.api_config.get("rate_limit"):
            # Implement rate limiting
            pass
        
        # Create and execute workflow
        instance = await self.engine.create_workflow_instance(
            workflow_id=workflow_id,
            input_data=input_data,
            triggered_by="api",
            trigger_type=TriggerType.API.value
        )
        
        await self.engine.execute_workflow(
            instance.instance_id,
            background=True
        )
        
        return instance.instance_id
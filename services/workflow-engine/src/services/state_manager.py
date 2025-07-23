"""
Workflow State Manager

This module handles workflow state persistence and recovery, including:
- State snapshots
- Checkpoint management
- State recovery after failures
- Distributed locking
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
import aioredis
import structlog

from ..models.schemas import WorkflowInstance, TaskInstance, WorkflowStatus, TaskStatus
from ..core.config import settings

logger = structlog.get_logger()


class WorkflowStateManager:
    """
    Manages workflow state persistence and recovery
    """
    
    def __init__(self, db_session: AsyncSession, redis_client: aioredis.Redis = None):
        self.db = db_session
        self.redis = redis_client
        self.state_prefix = settings.REDIS_STATE_PREFIX
        self.lock_prefix = settings.REDIS_LOCK_PREFIX
        
    async def save_workflow_state(
        self,
        workflow_instance: WorkflowInstance,
        checkpoint: bool = False
    ) -> bool:
        """
        Save workflow state to Redis
        """
        if not self.redis:
            return False
        
        try:
            state_key = f"{self.state_prefix}{workflow_instance.instance_id}"
            
            state_data = {
                "instance_id": workflow_instance.instance_id,
                "workflow_id": workflow_instance.workflow_id,
                "status": workflow_instance.status.value,
                "current_task_id": workflow_instance.current_task_id,
                "execution_path": workflow_instance.execution_path,
                "variables": workflow_instance.variables,
                "output_data": workflow_instance.output_data,
                "retry_count": workflow_instance.retry_count,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Save state with TTL
            ttl = 86400 * 7  # 7 days
            await self.redis.setex(
                state_key,
                ttl,
                json.dumps(state_data)
            )
            
            # Save checkpoint if requested
            if checkpoint:
                await self._save_checkpoint(workflow_instance)
            
            logger.debug(
                "Workflow state saved",
                instance_id=workflow_instance.instance_id,
                checkpoint=checkpoint
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to save workflow state",
                instance_id=workflow_instance.instance_id,
                error=str(e)
            )
            return False
    
    async def load_workflow_state(
        self,
        instance_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load workflow state from Redis
        """
        if not self.redis:
            return None
        
        try:
            state_key = f"{self.state_prefix}{instance_id}"
            state_data = await self.redis.get(state_key)
            
            if state_data:
                return json.loads(state_data)
            
            return None
            
        except Exception as e:
            logger.error(
                "Failed to load workflow state",
                instance_id=instance_id,
                error=str(e)
            )
            return None
    
    async def delete_workflow_state(self, instance_id: str) -> bool:
        """
        Delete workflow state from Redis
        """
        if not self.redis:
            return False
        
        try:
            state_key = f"{self.state_prefix}{instance_id}"
            await self.redis.delete(state_key)
            
            # Also delete checkpoints
            checkpoint_pattern = f"{self.state_prefix}checkpoint:{instance_id}:*"
            checkpoint_keys = await self.redis.keys(checkpoint_pattern)
            if checkpoint_keys:
                await self.redis.delete(*checkpoint_keys)
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to delete workflow state",
                instance_id=instance_id,
                error=str(e)
            )
            return False
    
    async def _save_checkpoint(self, workflow_instance: WorkflowInstance):
        """
        Save workflow checkpoint
        """
        checkpoint_key = (
            f"{self.state_prefix}checkpoint:"
            f"{workflow_instance.instance_id}:"
            f"{datetime.utcnow().timestamp()}"
        )
        
        checkpoint_data = {
            "instance_id": workflow_instance.instance_id,
            "workflow_id": workflow_instance.workflow_id,
            "status": workflow_instance.status.value,
            "current_task_id": workflow_instance.current_task_id,
            "execution_path": workflow_instance.execution_path,
            "variables": workflow_instance.variables,
            "output_data": workflow_instance.output_data,
            "checkpoint_time": datetime.utcnow().isoformat()
        }
        
        # Save checkpoint with TTL
        ttl = 86400 * 30  # 30 days
        await self.redis.setex(
            checkpoint_key,
            ttl,
            json.dumps(checkpoint_data)
        )
    
    async def list_checkpoints(self, instance_id: str) -> List[Dict[str, Any]]:
        """
        List all checkpoints for a workflow instance
        """
        if not self.redis:
            return []
        
        try:
            checkpoint_pattern = f"{self.state_prefix}checkpoint:{instance_id}:*"
            checkpoint_keys = await self.redis.keys(checkpoint_pattern)
            
            checkpoints = []
            for key in checkpoint_keys:
                checkpoint_data = await self.redis.get(key)
                if checkpoint_data:
                    checkpoint = json.loads(checkpoint_data)
                    # Extract timestamp from key
                    timestamp = float(key.split(":")[-1])
                    checkpoint["timestamp"] = timestamp
                    checkpoints.append(checkpoint)
            
            # Sort by timestamp
            checkpoints.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return checkpoints
            
        except Exception as e:
            logger.error(
                "Failed to list checkpoints",
                instance_id=instance_id,
                error=str(e)
            )
            return []
    
    async def restore_from_checkpoint(
        self,
        instance_id: str,
        checkpoint_timestamp: float
    ) -> Optional[Dict[str, Any]]:
        """
        Restore workflow state from a specific checkpoint
        """
        if not self.redis:
            return None
        
        try:
            checkpoint_key = (
                f"{self.state_prefix}checkpoint:"
                f"{instance_id}:"
                f"{checkpoint_timestamp}"
            )
            
            checkpoint_data = await self.redis.get(checkpoint_key)
            if checkpoint_data:
                return json.loads(checkpoint_data)
            
            return None
            
        except Exception as e:
            logger.error(
                "Failed to restore from checkpoint",
                instance_id=instance_id,
                checkpoint_timestamp=checkpoint_timestamp,
                error=str(e)
            )
            return None
    
    async def acquire_workflow_lock(
        self,
        instance_id: str,
        timeout: int = 300
    ) -> bool:
        """
        Acquire distributed lock for workflow instance
        """
        if not self.redis:
            return True  # No Redis, no locking
        
        try:
            lock_key = f"{self.lock_prefix}{instance_id}"
            lock_value = f"{datetime.utcnow().timestamp()}"
            
            # Try to acquire lock with NX (only if not exists)
            acquired = await self.redis.set(
                lock_key,
                lock_value,
                nx=True,
                ex=timeout
            )
            
            if acquired:
                logger.debug(
                    "Workflow lock acquired",
                    instance_id=instance_id,
                    timeout=timeout
                )
            
            return bool(acquired)
            
        except Exception as e:
            logger.error(
                "Failed to acquire workflow lock",
                instance_id=instance_id,
                error=str(e)
            )
            return False
    
    async def release_workflow_lock(self, instance_id: str) -> bool:
        """
        Release distributed lock for workflow instance
        """
        if not self.redis:
            return True
        
        try:
            lock_key = f"{self.lock_prefix}{instance_id}"
            await self.redis.delete(lock_key)
            
            logger.debug(
                "Workflow lock released",
                instance_id=instance_id
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to release workflow lock",
                instance_id=instance_id,
                error=str(e)
            )
            return False
    
    async def extend_workflow_lock(
        self,
        instance_id: str,
        timeout: int = 300
    ) -> bool:
        """
        Extend workflow lock timeout
        """
        if not self.redis:
            return True
        
        try:
            lock_key = f"{self.lock_prefix}{instance_id}"
            
            # Check if lock exists
            if await self.redis.exists(lock_key):
                # Extend TTL
                await self.redis.expire(lock_key, timeout)
                return True
            
            return False
            
        except Exception as e:
            logger.error(
                "Failed to extend workflow lock",
                instance_id=instance_id,
                error=str(e)
            )
            return False
    
    async def get_running_workflows(self) -> List[str]:
        """
        Get list of currently running workflow instances
        """
        if not self.redis:
            return []
        
        try:
            # Find all state keys
            state_pattern = f"{self.state_prefix}*"
            state_keys = await self.redis.keys(state_pattern)
            
            running_instances = []
            
            for key in state_keys:
                # Skip checkpoint keys
                if "checkpoint:" in key:
                    continue
                
                state_data = await self.redis.get(key)
                if state_data:
                    state = json.loads(state_data)
                    if state.get("status") == WorkflowStatus.RUNNING.value:
                        instance_id = key.replace(self.state_prefix, "")
                        running_instances.append(instance_id)
            
            return running_instances
            
        except Exception as e:
            logger.error(
                "Failed to get running workflows",
                error=str(e)
            )
            return []
    
    async def cleanup_old_states(self, days_to_keep: int = 30):
        """
        Clean up old workflow states and checkpoints
        """
        if not self.redis:
            return
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Find all state keys
            state_pattern = f"{self.state_prefix}*"
            state_keys = await self.redis.keys(state_pattern)
            
            deleted_count = 0
            
            for key in state_keys:
                state_data = await self.redis.get(key)
                if state_data:
                    state = json.loads(state_data)
                    updated_at = datetime.fromisoformat(
                        state.get("updated_at", datetime.utcnow().isoformat())
                    )
                    
                    # Delete if older than cutoff and not running
                    if (updated_at < cutoff_time and 
                        state.get("status") != WorkflowStatus.RUNNING.value):
                        await self.redis.delete(key)
                        deleted_count += 1
            
            logger.info(
                "Cleaned up old workflow states",
                deleted_count=deleted_count,
                days_to_keep=days_to_keep
            )
            
        except Exception as e:
            logger.error(
                "Failed to cleanup old states",
                error=str(e)
            )
    
    async def save_task_state(
        self,
        task_instance: TaskInstance
    ) -> bool:
        """
        Save task state
        """
        if not self.redis:
            return False
        
        try:
            task_key = (
                f"{self.state_prefix}task:"
                f"{task_instance.workflow_instance_id}:"
                f"{task_instance.task_id}"
            )
            
            task_data = {
                "task_instance_id": task_instance.task_instance_id,
                "task_id": task_instance.task_id,
                "status": task_instance.status.value,
                "input_data": task_instance.input_data,
                "output_data": task_instance.output_data,
                "error_message": task_instance.error_message,
                "retry_count": task_instance.retry_count,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Save with TTL
            ttl = 86400 * 7  # 7 days
            await self.redis.setex(
                task_key,
                ttl,
                json.dumps(task_data)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to save task state",
                task_instance_id=task_instance.task_instance_id,
                error=str(e)
            )
            return False
    
    async def load_task_state(
        self,
        workflow_instance_id: str,
        task_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load task state
        """
        if not self.redis:
            return None
        
        try:
            task_key = (
                f"{self.state_prefix}task:"
                f"{workflow_instance_id}:"
                f"{task_id}"
            )
            
            task_data = await self.redis.get(task_key)
            if task_data:
                return json.loads(task_data)
            
            return None
            
        except Exception as e:
            logger.error(
                "Failed to load task state",
                workflow_instance_id=workflow_instance_id,
                task_id=task_id,
                error=str(e)
            )
            return None
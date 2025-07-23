"""
Background Task Worker

This worker processes workflow tasks from RabbitMQ queue
"""

import asyncio
import signal
import sys
from typing import Dict, Any
import structlog
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from ..core.config import settings
from ..services.rabbitmq_service import rabbitmq_service
from ..services.workflow_engine import WorkflowEngine
from ..services.task_executor import TaskExecutor
from ..db.base import get_db_session
from ..core.deps import get_redis_client

logger = structlog.get_logger()


class TaskWorker:
    """
    Background worker for processing workflow tasks
    """
    
    def __init__(self):
        self.running = False
        self.workflow_engine = None
        self.task_executor = None
        self.db_session = None
        self.redis_client = None
        
    async def start(self):
        """
        Start the worker
        """
        logger.info("Starting workflow task worker...")
        
        # Initialize database
        engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW
        )
        
        async_session_maker = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        self.db_session = async_session_maker()
        
        # Initialize Redis
        self.redis_client = await get_redis_client()
        
        # Initialize services
        self.workflow_engine = WorkflowEngine(self.db_session, self.redis_client)
        self.task_executor = TaskExecutor(self.db_session, self.redis_client)
        
        # Connect to RabbitMQ
        await rabbitmq_service.connect()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = True
        
        # Start consuming tasks
        await rabbitmq_service.consume_tasks(self._process_task)
        
        # Keep running
        while self.running:
            await asyncio.sleep(1)
        
        # Cleanup
        await self.stop()
    
    async def stop(self):
        """
        Stop the worker
        """
        logger.info("Stopping workflow task worker...")
        
        self.running = False
        
        # Disconnect from services
        await rabbitmq_service.disconnect()
        
        if self.redis_client:
            await self.redis_client.close()
        
        if self.db_session:
            await self.db_session.close()
        
        logger.info("Worker stopped")
    
    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals
        """
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    async def _process_task(self, task_data: Dict[str, Any]):
        """
        Process a task from the queue
        """
        task_id = task_data.get("task_id")
        task_type = task_data.get("task_type")
        data = task_data.get("data", {})
        
        logger.info(
            "Processing task from queue",
            task_id=task_id,
            task_type=task_type
        )
        
        try:
            if task_type == "execute_workflow":
                # Execute workflow
                instance_id = data.get("instance_id")
                await self.workflow_engine.execute_workflow(
                    instance_id,
                    background=False
                )
                
            elif task_type == "execute_task":
                # Execute individual task
                task_instance_id = data.get("task_instance_id")
                task_config = data.get("task_config")
                context = data.get("context")
                
                # Load task instance
                task_instance = await self._load_task_instance(task_instance_id)
                
                # Execute task
                await self.task_executor.execute_task(
                    task_instance,
                    task_config,
                    context
                )
                
            elif task_type == "schedule_workflow":
                # Handle scheduled workflow
                workflow_id = data.get("workflow_id")
                input_data = data.get("input_data", {})
                triggered_by = data.get("triggered_by", "scheduler")
                
                # Create and execute workflow instance
                instance = await self.workflow_engine.create_workflow_instance(
                    workflow_id=workflow_id,
                    input_data=input_data,
                    triggered_by=triggered_by,
                    trigger_type="scheduled"
                )
                
                await self.workflow_engine.execute_workflow(
                    instance.instance_id,
                    background=False
                )
                
            elif task_type == "retry_workflow":
                # Retry failed workflow
                instance_id = data.get("instance_id")
                await self.workflow_engine.execute_workflow(
                    instance_id,
                    background=False
                )
                
            else:
                logger.warning(f"Unknown task type: {task_type}")
                
        except Exception as e:
            logger.error(
                "Task processing failed",
                task_id=task_id,
                task_type=task_type,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def _load_task_instance(self, task_instance_id: str):
        """
        Load task instance from database
        """
        # Implementation would load from database
        # This is a placeholder
        pass


async def main():
    """
    Main entry point for the worker
    """
    worker = TaskWorker()
    
    try:
        await worker.start()
    except Exception as e:
        logger.error("Worker failed", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
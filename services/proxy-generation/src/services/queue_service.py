"""
Queue Service for managing proxy generation jobs
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import aio_pika
from aio_pika import Message, ExchangeType, DeliveryMode

from ..core.config import settings
from ..core.exceptions import QueueError
from ..core.logging import get_logger

logger = get_logger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobPriority(int, Enum):
    """Job priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class ProxyJob:
    """Proxy generation job"""
    
    def __init__(
        self,
        job_id: str,
        asset_id: str,
        input_path: str,
        job_type: str,
        parameters: Dict[str, Any],
        priority: JobPriority = JobPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.job_id = job_id
        self.asset_id = asset_id
        self.input_path = input_path
        self.job_type = job_type
        self.parameters = parameters
        self.priority = priority
        self.metadata = metadata or {}
        self.status = JobStatus.PENDING
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None
        self.error = None
        self.retry_count = 0
        self.result = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary"""
        return {
            "job_id": self.job_id,
            "asset_id": self.asset_id,
            "input_path": self.input_path,
            "job_type": self.job_type,
            "parameters": self.parameters,
            "priority": self.priority,
            "metadata": self.metadata,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "retry_count": self.retry_count,
            "result": self.result
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProxyJob":
        """Create job from dictionary"""
        job = cls(
            job_id=data["job_id"],
            asset_id=data["asset_id"],
            input_path=data["input_path"],
            job_type=data["job_type"],
            parameters=data["parameters"],
            priority=JobPriority(data.get("priority", JobPriority.NORMAL)),
            metadata=data.get("metadata", {})
        )
        job.status = JobStatus(data.get("status", JobStatus.PENDING))
        job.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            job.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            job.completed_at = datetime.fromisoformat(data["completed_at"])
        job.error = data.get("error")
        job.retry_count = data.get("retry_count", 0)
        job.result = data.get("result")
        return job


class QueueService:
    """Service for managing proxy generation queue"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
        self.queue = None
        self.consumer_tag = None
        self.job_handlers: Dict[str, Callable] = {}
        self.active_jobs: Dict[str, ProxyJob] = {}
        self._running = False
    
    async def initialize(self):
        """Initialize RabbitMQ connection and setup queue"""
        try:
            # Create connection
            self.connection = await aio_pika.connect_robust(
                settings.rabbitmq_url,
                loop=asyncio.get_event_loop()
            )
            
            # Create channel
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=settings.max_concurrent_jobs)
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                name="mams.proxy",
                type=ExchangeType.DIRECT,
                durable=True
            )
            
            # Declare queue
            self.queue = await self.channel.declare_queue(
                name=settings.proxy_queue_name,
                durable=True,
                arguments={
                    "x-max-priority": JobPriority.URGENT,
                    "x-message-ttl": 86400000  # 24 hours
                }
            )
            
            # Bind queue to exchange
            await self.queue.bind(self.exchange, routing_key="proxy.generate")
            
            logger.info(
                "queue_initialized",
                queue_name=settings.proxy_queue_name,
                max_concurrent_jobs=settings.max_concurrent_jobs
            )
            
        except Exception as e:
            logger.error("queue_initialization_failed", error=str(e))
            raise QueueError(f"Failed to initialize queue: {str(e)}")
    
    async def close(self):
        """Close queue connections"""
        try:
            if self.consumer_tag:
                await self.queue.cancel(self.consumer_tag)
                self.consumer_tag = None
            
            if self.channel:
                await self.channel.close()
            
            if self.connection:
                await self.connection.close()
            
            logger.info("queue_closed")
            
        except Exception as e:
            logger.error("queue_close_failed", error=str(e))
    
    def register_handler(self, job_type: str, handler: Callable):
        """Register a job handler for specific job type"""
        self.job_handlers[job_type] = handler
        logger.info("handler_registered", job_type=job_type)
    
    async def submit_job(
        self,
        asset_id: str,
        input_path: str,
        job_type: str,
        parameters: Dict[str, Any],
        priority: JobPriority = JobPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Submit a new job to the queue"""
        try:
            # Create job
            job_id = str(uuid.uuid4())
            job = ProxyJob(
                job_id=job_id,
                asset_id=asset_id,
                input_path=input_path,
                job_type=job_type,
                parameters=parameters,
                priority=priority,
                metadata=metadata
            )
            
            # Prepare message
            message_body = json.dumps(job.to_dict())
            message = Message(
                body=message_body.encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                priority=priority,
                headers={
                    "job_id": job_id,
                    "job_type": job_type,
                    "asset_id": asset_id
                }
            )
            
            # Publish to exchange
            await self.exchange.publish(
                message,
                routing_key="proxy.generate"
            )
            
            logger.info(
                "job_submitted",
                job_id=job_id,
                asset_id=asset_id,
                job_type=job_type,
                priority=priority
            )
            
            return job_id
            
        except Exception as e:
            logger.error(
                "job_submission_failed",
                error=str(e),
                asset_id=asset_id,
                job_type=job_type
            )
            raise QueueError(f"Failed to submit job: {str(e)}")
    
    async def start_consumer(self):
        """Start consuming jobs from queue"""
        try:
            self._running = True
            
            # Start consuming
            self.consumer_tag = await self.queue.consume(
                self._process_message,
                no_ack=False
            )
            
            logger.info("consumer_started")
            
            # Keep running until stopped
            while self._running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error("consumer_failed", error=str(e))
            raise QueueError(f"Consumer failed: {str(e)}")
    
    async def stop_consumer(self):
        """Stop consuming jobs"""
        self._running = False
        if self.consumer_tag:
            await self.queue.cancel(self.consumer_tag)
            self.consumer_tag = None
        logger.info("consumer_stopped")
    
    async def _process_message(self, message: aio_pika.IncomingMessage):
        """Process incoming message from queue"""
        job = None
        try:
            async with message.process():
                # Parse job data
                job_data = json.loads(message.body.decode())
                job = ProxyJob.from_dict(job_data)
                
                # Check if handler exists
                handler = self.job_handlers.get(job.job_type)
                if not handler:
                    raise QueueError(f"No handler registered for job type: {job.job_type}")
                
                # Update job status
                job.status = JobStatus.PROCESSING
                job.started_at = datetime.utcnow()
                self.active_jobs[job.job_id] = job
                
                logger.info(
                    "job_processing_started",
                    job_id=job.job_id,
                    job_type=job.job_type,
                    asset_id=job.asset_id
                )
                
                # Execute handler
                result = await handler(job)
                
                # Update job status
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.result = result
                
                logger.info(
                    "job_completed",
                    job_id=job.job_id,
                    processing_time=(job.completed_at - job.started_at).total_seconds()
                )
                
                # Remove from active jobs
                self.active_jobs.pop(job.job_id, None)
                
        except Exception as e:
            logger.error(
                "job_processing_failed",
                error=str(e),
                job_id=job.job_id if job else "unknown",
                job_type=job.job_type if job else "unknown"
            )
            
            if job:
                job.status = JobStatus.FAILED
                job.error = str(e)
                job.completed_at = datetime.utcnow()
                
                # Check retry policy
                if job.retry_count < settings.max_retries:
                    job.retry_count += 1
                    job.status = JobStatus.RETRYING
                    
                    # Requeue with delay
                    await asyncio.sleep(settings.retry_delay)
                    await self._requeue_job(job)
                else:
                    # Max retries reached
                    self.active_jobs.pop(job.job_id, None)
            
            # Reject message if processing failed completely
            await message.reject(requeue=False)
    
    async def _requeue_job(self, job: ProxyJob):
        """Requeue a failed job for retry"""
        try:
            job.status = JobStatus.PENDING
            job.error = None
            
            message_body = json.dumps(job.to_dict())
            message = Message(
                body=message_body.encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                priority=job.priority,
                headers={
                    "job_id": job.job_id,
                    "job_type": job.job_type,
                    "asset_id": job.asset_id,
                    "retry_count": job.retry_count
                }
            )
            
            await self.exchange.publish(
                message,
                routing_key="proxy.generate"
            )
            
            logger.info(
                "job_requeued",
                job_id=job.job_id,
                retry_count=job.retry_count
            )
            
        except Exception as e:
            logger.error(
                "job_requeue_failed",
                error=str(e),
                job_id=job.job_id
            )
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            queue_info = await self.queue.declare(passive=True)
            
            return {
                "queue_name": settings.proxy_queue_name,
                "message_count": queue_info.message_count,
                "consumer_count": queue_info.consumer_count,
                "active_jobs": len(self.active_jobs),
                "max_concurrent_jobs": settings.max_concurrent_jobs
            }
            
        except Exception as e:
            logger.error("get_queue_stats_failed", error=str(e))
            return {
                "error": str(e),
                "active_jobs": len(self.active_jobs)
            }
    
    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get list of active jobs"""
        return [job.to_dict() for job in self.active_jobs.values()]


# Singleton instance
_queue_service: Optional[QueueService] = None


async def get_queue_service() -> QueueService:
    """Get queue service instance"""
    global _queue_service
    
    if _queue_service is None:
        _queue_service = QueueService()
        await _queue_service.initialize()
    
    return _queue_service
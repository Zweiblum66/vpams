"""
RabbitMQ Service for Workflow Engine

This module handles RabbitMQ integration for async task processing:
- Task queue management
- Message publishing and consumption
- Dead letter queue handling
- Connection management
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable
import aio_pika
from aio_pika import Message, ExchangeType, DeliveryMode
import structlog

from ..core.config import settings
from ..core.exceptions import WorkflowExecutionError

logger = structlog.get_logger()


class RabbitMQService:
    """
    RabbitMQ service for async task processing
    """
    
    def __init__(self):
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        self.task_queue: Optional[aio_pika.Queue] = None
        self.dlq: Optional[aio_pika.Queue] = None
        self.consumers = {}
        
    async def connect(self):
        """
        Establish connection to RabbitMQ
        """
        try:
            self.connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URL,
                loop=asyncio.get_event_loop()
            )
            
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                settings.WORKFLOW_EXCHANGE,
                ExchangeType.TOPIC,
                durable=True
            )
            
            # Declare main task queue
            self.task_queue = await self.channel.declare_queue(
                settings.TASK_QUEUE,
                durable=True,
                arguments={
                    "x-message-ttl": 86400000,  # 24 hours
                    "x-dead-letter-exchange": "",
                    "x-dead-letter-routing-key": f"{settings.TASK_QUEUE}.dlq"
                }
            )
            
            # Declare dead letter queue
            self.dlq = await self.channel.declare_queue(
                f"{settings.TASK_QUEUE}.dlq",
                durable=True,
                arguments={
                    "x-message-ttl": 604800000  # 7 days
                }
            )
            
            # Bind queues
            await self.task_queue.bind(self.exchange, routing_key="workflow.task.*")
            await self.dlq.bind(self.exchange, routing_key="workflow.task.failed")
            
            logger.info("Connected to RabbitMQ", url=settings.RABBITMQ_URL)
            
        except Exception as e:
            logger.error("Failed to connect to RabbitMQ", error=str(e))
            raise
    
    async def disconnect(self):
        """
        Close RabbitMQ connection
        """
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("Disconnected from RabbitMQ")
    
    async def publish_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        priority: int = 5,
        delay_seconds: int = 0
    ) -> str:
        """
        Publish a task to the queue
        """
        if not self.exchange:
            await self.connect()
        
        task_id = str(uuid.uuid4())
        
        message_body = {
            "task_id": task_id,
            "task_type": task_type,
            "data": task_data,
            "timestamp": datetime.utcnow().isoformat(),
            "retry_count": 0
        }
        
        message = Message(
            body=json.dumps(message_body).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
            priority=priority,
            correlation_id=task_id,
            headers={
                "task_type": task_type,
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
        if delay_seconds > 0:
            message.headers["x-delay"] = delay_seconds * 1000
        
        routing_key = f"workflow.task.{task_type}"
        
        await self.exchange.publish(
            message,
            routing_key=routing_key
        )
        
        logger.info(
            "Task published",
            task_id=task_id,
            task_type=task_type,
            routing_key=routing_key
        )
        
        return task_id
    
    async def consume_tasks(
        self,
        task_handler: Callable,
        task_types: Optional[list] = None
    ):
        """
        Start consuming tasks from the queue
        """
        if not self.task_queue:
            await self.connect()
        
        async def process_message(message: aio_pika.IncomingMessage):
            """
            Process incoming message
            """
            async with message.process():
                try:
                    # Parse message
                    body = json.loads(message.body.decode())
                    task_type = body.get("task_type")
                    
                    # Check if should process this task type
                    if task_types and task_type not in task_types:
                        await message.nack(requeue=True)
                        return
                    
                    logger.info(
                        "Processing task",
                        task_id=body.get("task_id"),
                        task_type=task_type
                    )
                    
                    # Execute task handler
                    await task_handler(body)
                    
                except json.JSONDecodeError as e:
                    logger.error("Invalid message format", error=str(e))
                    await message.reject(requeue=False)
                    
                except Exception as e:
                    logger.error(
                        "Task processing failed",
                        task_id=body.get("task_id"),
                        error=str(e)
                    )
                    
                    # Increment retry count
                    retry_count = body.get("retry_count", 0) + 1
                    
                    if retry_count <= settings.TASK_MAX_RETRIES:
                        # Requeue with updated retry count
                        body["retry_count"] = retry_count
                        await self.publish_task(
                            body["task_type"],
                            body["data"],
                            priority=message.priority,
                            delay_seconds=settings.TASK_RETRY_DELAY * retry_count
                        )
                    else:
                        # Send to dead letter queue
                        await self._publish_to_dlq(body, str(e))
                    
                    await message.reject(requeue=False)
        
        # Start consuming
        consumer_tag = await self.task_queue.consume(process_message)
        self.consumers[consumer_tag] = True
        
        logger.info("Started consuming tasks", task_types=task_types)
    
    async def _publish_to_dlq(self, task_data: Dict[str, Any], error: str):
        """
        Publish failed task to dead letter queue
        """
        message_body = {
            **task_data,
            "failed_at": datetime.utcnow().isoformat(),
            "error": error
        }
        
        message = Message(
            body=json.dumps(message_body).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
            headers={
                "x-death-reason": "max-retries-exceeded",
                "x-original-task-type": task_data.get("task_type")
            }
        )
        
        await self.exchange.publish(
            message,
            routing_key="workflow.task.failed"
        )
        
        logger.warning(
            "Task sent to DLQ",
            task_id=task_data.get("task_id"),
            task_type=task_data.get("task_type")
        )
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics
        """
        if not self.task_queue:
            await self.connect()
        
        task_queue_info = await self.task_queue.declare(passive=True)
        dlq_info = await self.dlq.declare(passive=True)
        
        return {
            "task_queue": {
                "name": self.task_queue.name,
                "messages": task_queue_info.message_count,
                "consumers": task_queue_info.consumer_count
            },
            "dead_letter_queue": {
                "name": self.dlq.name,
                "messages": dlq_info.message_count
            },
            "active_consumers": len(self.consumers)
        }
    
    async def reprocess_dlq_messages(self, limit: int = 100) -> int:
        """
        Reprocess messages from dead letter queue
        """
        if not self.dlq:
            await self.connect()
        
        reprocessed = 0
        
        async for message in self.dlq:
            if reprocessed >= limit:
                await message.nack(requeue=True)
                break
            
            try:
                async with message.process():
                    body = json.loads(message.body.decode())
                    
                    # Reset retry count
                    body["retry_count"] = 0
                    
                    # Republish to main queue
                    await self.publish_task(
                        body["task_type"],
                        body["data"]
                    )
                    
                    reprocessed += 1
                    
            except Exception as e:
                logger.error(
                    "Failed to reprocess DLQ message",
                    error=str(e)
                )
                await message.reject(requeue=True)
        
        logger.info(f"Reprocessed {reprocessed} messages from DLQ")
        return reprocessed
    
    async def purge_queue(self, queue_name: str):
        """
        Purge all messages from a queue
        """
        if queue_name == settings.TASK_QUEUE:
            await self.task_queue.purge()
        elif queue_name == f"{settings.TASK_QUEUE}.dlq":
            await self.dlq.purge()
        else:
            raise ValueError(f"Unknown queue: {queue_name}")
        
        logger.warning(f"Purged queue: {queue_name}")


# Singleton instance
rabbitmq_service = RabbitMQService()
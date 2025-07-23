"""
Queue service for asynchronous processing using RabbitMQ
"""

import asyncio
import json
import uuid
from typing import Optional, Dict, Any, Callable
import structlog
import aio_pika
from aio_pika import Message, ExchangeType
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractExchange, AbstractQueue

from ..models.schemas import IngestJob, IngestNotification
from ..core.config import settings
from ..core.exceptions import QueueError
from ..core.logging import get_logger

logger = get_logger(__name__)


class QueueService:
    """Service for managing RabbitMQ message queues"""
    
    def __init__(self):
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.exchange: Optional[AbstractExchange] = None
        self.queues: Dict[str, AbstractQueue] = {}
        self.consumers: Dict[str, Any] = {}
        self._is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize RabbitMQ connection and setup queues"""
        if self._is_initialized:
            return
        
        try:
            # Establish connection
            self.connection = await aio_pika.connect_robust(
                settings.rabbitmq_url,
                client_properties={
                    "service": settings.service_name,
                    "version": settings.service_version
                }
            )
            
            # Create channel
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=settings.max_concurrent_ingests)
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                settings.rabbitmq_exchange,
                ExchangeType.TOPIC,
                durable=True
            )
            
            # Setup queues
            await self._setup_queues()
            
            self._is_initialized = True
            
            logger.info(
                "queue_service_initialized",
                exchange=settings.rabbitmq_exchange,
                queues=list(self.queues.keys())
            )
            
        except Exception as e:
            logger.error("failed_to_initialize_queue_service", error=str(e))
            raise QueueError(f"Failed to initialize queue service: {str(e)}")
    
    async def _setup_queues(self) -> None:
        """Setup all required queues"""
        queue_configs = [
            {
                "name": settings.rabbitmq_queues["ingest"],
                "routing_key": "ingest.job.created",
                "durable": True,
                "arguments": {
                    "x-message-ttl": 3600000,  # 1 hour TTL
                    "x-dead-letter-exchange": settings.rabbitmq_exchange,
                    "x-dead-letter-routing-key": f"{settings.rabbitmq_queue_prefix}.dead_letter"
                }
            },
            {
                "name": settings.rabbitmq_queues["validation"],
                "routing_key": "ingest.validation.required",
                "durable": True,
                "arguments": {
                    "x-message-ttl": 1800000,  # 30 minutes TTL
                    "x-dead-letter-exchange": settings.rabbitmq_exchange,
                    "x-dead-letter-routing-key": f"{settings.rabbitmq_queue_prefix}.dead_letter"
                }
            },
            {
                "name": settings.rabbitmq_queues["processing"],
                "routing_key": "ingest.processing.required",
                "durable": True,
                "arguments": {
                    "x-message-ttl": 7200000,  # 2 hours TTL
                    "x-dead-letter-exchange": settings.rabbitmq_exchange,
                    "x-dead-letter-routing-key": f"{settings.rabbitmq_queue_prefix}.dead_letter"
                }
            },
            {
                "name": settings.rabbitmq_queues["metadata"],
                "routing_key": "ingest.metadata.extraction",
                "durable": True,
                "arguments": {
                    "x-message-ttl": 1800000,  # 30 minutes TTL
                    "x-dead-letter-exchange": settings.rabbitmq_exchange,
                    "x-dead-letter-routing-key": f"{settings.rabbitmq_queue_prefix}.dead_letter"
                }
            },
            {
                "name": settings.rabbitmq_queues["notifications"],
                "routing_key": "ingest.notification.*",
                "durable": True,
                "arguments": {
                    "x-message-ttl": 300000,  # 5 minutes TTL
                }
            },
            {
                "name": settings.rabbitmq_queues["retry"],
                "routing_key": "ingest.retry.*",
                "durable": True,
                "arguments": {
                    "x-message-ttl": 3600000,  # 1 hour TTL
                    "x-max-retries": 3
                }
            },
            {
                "name": settings.rabbitmq_queues["dead_letter"],
                "routing_key": f"{settings.rabbitmq_queue_prefix}.dead_letter",
                "durable": True,
                "arguments": {}
            }
        ]
        
        for config in queue_configs:
            queue = await self.channel.declare_queue(
                config["name"],
                durable=config["durable"],
                arguments=config["arguments"]
            )
            
            await queue.bind(
                self.exchange,
                routing_key=config["routing_key"]
            )
            
            self.queues[config["name"]] = queue
            
            logger.debug(
                "queue_declared",
                queue_name=config["name"],
                routing_key=config["routing_key"]
            )
    
    async def publish_ingest_job(self, job: IngestJob) -> None:
        """Publish an ingest job to the processing queue"""
        await self._ensure_initialized()
        
        message_body = {
            "job_id": job.id,
            "source_path": job.source_path,
            "ingest_type": job.ingest_type.value,
            "destination_project_id": job.destination_project_id,
            "priority": job.priority,
            "created_at": job.created_at.isoformat(),
            "metadata": {
                "total_files": job.total_files,
                "total_size": job.total_size,
                "auto_generate_proxies": job.auto_generate_proxies,
                "preserve_folder_structure": job.preserve_folder_structure
            }
        }
        
        await self._publish_message(
            routing_key="ingest.job.created",
            body=message_body,
            priority=job.priority,
            correlation_id=job.id
        )
        
        logger.info(
            "ingest_job_published",
            job_id=job.id,
            source_path=job.source_path,
            priority=job.priority
        )
    
    async def publish_validation_request(
        self,
        file_path: str,
        job_id: str,
        validation_rules: Optional[list] = None
    ) -> None:
        """Publish a file validation request"""
        await self._ensure_initialized()
        
        message_body = {
            "job_id": job_id,
            "file_path": file_path,
            "validation_rules": validation_rules or [],
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await self._publish_message(
            routing_key="ingest.validation.required",
            body=message_body,
            correlation_id=job_id
        )
        
        logger.info(
            "validation_request_published",
            job_id=job_id,
            file_path=file_path
        )
    
    async def publish_metadata_extraction_request(
        self,
        file_path: str,
        job_id: str,
        extract_technical: bool = True,
        extract_embedded: bool = True
    ) -> None:
        """Publish a metadata extraction request"""
        await self._ensure_initialized()
        
        message_body = {
            "job_id": job_id,
            "file_path": file_path,
            "extract_technical": extract_technical,
            "extract_embedded": extract_embedded,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await self._publish_message(
            routing_key="ingest.metadata.extraction",
            body=message_body,
            correlation_id=job_id
        )
        
        logger.info(
            "metadata_extraction_request_published",
            job_id=job_id,
            file_path=file_path
        )
    
    async def publish_proxy_request(
        self,
        asset_id: str,
        job_id: str,
        quality_presets: Optional[list] = None
    ) -> None:
        """Publish a proxy generation request"""
        await self._ensure_initialized()
        
        message_body = {
            "asset_id": asset_id,
            "job_id": job_id,
            "quality_presets": quality_presets or ["low", "medium", "edit"],
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # This would be sent to the proxy generation service
        await self._publish_message(
            routing_key="proxy.generation.requested",
            body=message_body,
            correlation_id=job_id
        )
        
        logger.info(
            "proxy_request_published",
            asset_id=asset_id,
            job_id=job_id
        )
    
    async def publish_notification(self, notification: IngestNotification) -> None:
        """Publish a notification message"""
        await self._ensure_initialized()
        
        message_body = {
            "job_id": notification.job_id,
            "event_type": notification.event_type,
            "message": notification.message,
            "details": notification.details,
            "timestamp": notification.timestamp.isoformat(),
            "user_id": notification.user_id
        }
        
        await self._publish_message(
            routing_key=f"ingest.notification.{notification.event_type}",
            body=message_body,
            correlation_id=notification.job_id
        )
        
        logger.info(
            "notification_published",
            job_id=notification.job_id,
            event_type=notification.event_type
        )
    
    async def publish_retry_message(
        self,
        original_routing_key: str,
        original_body: Dict[str, Any],
        retry_count: int = 0,
        delay_seconds: int = 60
    ) -> None:
        """Publish a message to the retry queue"""
        await self._ensure_initialized()
        
        retry_body = {
            "original_routing_key": original_routing_key,
            "original_body": original_body,
            "retry_count": retry_count,
            "max_retries": 3,
            "delay_seconds": delay_seconds,
            "retry_timestamp": asyncio.get_event_loop().time()
        }
        
        await self._publish_message(
            routing_key=f"ingest.retry.{original_routing_key}",
            body=retry_body,
            delay=delay_seconds * 1000  # Convert to milliseconds
        )
        
        logger.info(
            "retry_message_published",
            original_routing_key=original_routing_key,
            retry_count=retry_count,
            delay_seconds=delay_seconds
        )
    
    async def subscribe_to_queue(
        self,
        queue_name: str,
        callback: Callable,
        auto_ack: bool = False
    ) -> None:
        """Subscribe to a queue with a callback function"""
        await self._ensure_initialized()
        
        if queue_name not in self.queues:
            raise QueueError(f"Queue {queue_name} not found")
        
        queue = self.queues[queue_name]
        
        async def message_processor(message: aio_pika.abc.AbstractIncomingMessage):
            async with message.process(ignore_processed=auto_ack):
                try:
                    # Decode message body
                    body = json.loads(message.body.decode())
                    
                    # Call the callback function
                    await callback(body, message)
                    
                    logger.debug(
                        "message_processed",
                        queue=queue_name,
                        routing_key=message.routing_key,
                        correlation_id=message.correlation_id
                    )
                    
                except json.JSONDecodeError as e:
                    logger.error(
                        "message_decode_failed",
                        queue=queue_name,
                        error=str(e),
                        body=message.body[:100]  # Log first 100 chars
                    )
                    # Reject message - it will go to dead letter queue
                    raise
                    
                except Exception as e:
                    logger.error(
                        "message_processing_failed",
                        queue=queue_name,
                        error=str(e),
                        routing_key=message.routing_key,
                        correlation_id=message.correlation_id
                    )
                    
                    # Determine if message should be retried
                    delivery_count = message.headers.get("x-delivery-count", 0) if message.headers else 0
                    
                    if delivery_count < 3:  # Max 3 retries
                        # Publish to retry queue
                        await self.publish_retry_message(
                            original_routing_key=message.routing_key or "",
                            original_body=json.loads(message.body.decode()),
                            retry_count=delivery_count + 1,
                            delay_seconds=60 * (delivery_count + 1)  # Exponential backoff
                        )
                    
                    # Reject the message (will go to dead letter after retries)
                    raise
        
        # Start consuming messages
        consumer_tag = await queue.consume(message_processor)
        self.consumers[queue_name] = consumer_tag
        
        logger.info(
            "queue_subscription_started",
            queue=queue_name,
            consumer_tag=consumer_tag
        )
    
    async def unsubscribe_from_queue(self, queue_name: str) -> None:
        """Unsubscribe from a queue"""
        if queue_name in self.consumers:
            consumer_tag = self.consumers[queue_name]
            
            if queue_name in self.queues:
                await self.queues[queue_name].cancel(consumer_tag)
            
            del self.consumers[queue_name]
            
            logger.info(
                "queue_subscription_stopped",
                queue=queue_name,
                consumer_tag=consumer_tag
            )
    
    async def get_queue_info(self, queue_name: str) -> Dict[str, Any]:
        """Get information about a queue"""
        await self._ensure_initialized()
        
        if queue_name not in self.queues:
            raise QueueError(f"Queue {queue_name} not found")
        
        queue = self.queues[queue_name]
        
        # Get queue declaration result to access queue info
        declaration_result = await self.channel.declare_queue(
            queue_name,
            passive=True  # Only check if queue exists
        )
        
        return {
            "name": queue_name,
            "message_count": declaration_result.method.message_count,
            "consumer_count": declaration_result.method.consumer_count,
            "is_durable": queue.durable,
            "is_auto_delete": queue.auto_delete,
            "arguments": queue.arguments
        }
    
    async def purge_queue(self, queue_name: str) -> int:
        """Purge all messages from a queue"""
        await self._ensure_initialized()
        
        if queue_name not in self.queues:
            raise QueueError(f"Queue {queue_name} not found")
        
        queue = self.queues[queue_name]
        purge_result = await queue.purge()
        
        logger.warning(
            "queue_purged",
            queue=queue_name,
            messages_purged=purge_result.method.message_count
        )
        
        return purge_result.method.message_count
    
    async def _publish_message(
        self,
        routing_key: str,
        body: Dict[str, Any],
        priority: int = 5,
        correlation_id: Optional[str] = None,
        delay: Optional[int] = None,
        headers: Optional[Dict[str, Any]] = None
    ) -> None:
        """Publish a message to the exchange"""
        await self._ensure_initialized()
        
        message_headers = headers or {}
        if delay:
            message_headers["x-delay"] = delay
        
        message = Message(
            body=json.dumps(body, default=str).encode(),
            priority=priority,
            correlation_id=correlation_id or str(uuid.uuid4()),
            headers=message_headers,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        
        await self.exchange.publish(
            message,
            routing_key=routing_key
        )
        
        logger.debug(
            "message_published",
            routing_key=routing_key,
            correlation_id=message.correlation_id,
            priority=priority
        )
    
    async def _ensure_initialized(self) -> None:
        """Ensure the service is initialized"""
        if not self._is_initialized:
            await self.initialize()
    
    async def close(self) -> None:
        """Close the queue service connection"""
        try:
            # Stop all consumers
            for queue_name in list(self.consumers.keys()):
                await self.unsubscribe_from_queue(queue_name)
            
            # Close channel and connection
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
            
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            
            self._is_initialized = False
            
            logger.info("queue_service_closed")
            
        except Exception as e:
            logger.error("failed_to_close_queue_service", error=str(e))
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the queue service"""
        try:
            await self._ensure_initialized()
            
            # Check connection status
            connection_ok = self.connection and not self.connection.is_closed
            channel_ok = self.channel and not self.channel.is_closed
            
            # Get queue information
            queue_info = {}
            for queue_name in self.queues:
                try:
                    info = await self.get_queue_info(queue_name)
                    queue_info[queue_name] = info
                except Exception as e:
                    queue_info[queue_name] = {"error": str(e)}
            
            return {
                "status": "healthy" if connection_ok and channel_ok else "unhealthy",
                "connection_ok": connection_ok,
                "channel_ok": channel_ok,
                "queues": queue_info,
                "exchange": settings.rabbitmq_exchange,
                "consumers": len(self.consumers)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Dependency injection
_queue_service: Optional[QueueService] = None


async def get_queue_service() -> QueueService:
    """Get queue service instance"""
    global _queue_service
    
    if _queue_service is None:
        _queue_service = QueueService()
        await _queue_service.initialize()
    
    return _queue_service
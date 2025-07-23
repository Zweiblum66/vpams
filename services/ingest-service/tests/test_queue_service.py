"""
Test Queue Service

Tests for RabbitMQ queue service functionality.
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
import aio_pika
from aio_pika import Message, ExchangeType, DeliveryMode
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractExchange, AbstractQueue

from src.services.queue_service import QueueService, get_queue_service
from src.models.schemas import IngestJob, IngestNotification, IngestStatus, IngestType
from src.core.exceptions import QueueError
from src.core.config import settings


class MockIncomingMessage:
    """Mock incoming message from RabbitMQ."""
    def __init__(self, body, routing_key="test.routing.key", correlation_id=None, headers=None):
        self.body = body.encode() if isinstance(body, str) else body
        self.routing_key = routing_key
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.headers = headers or {}
        self._processed = False
    
    def process(self, ignore_processed=False):
        """Context manager for message processing."""
        class MessageProcessor:
            def __init__(self, message):
                self.message = message
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if exc_type is None:
                    self.message._processed = True
                return False
        
        return MessageProcessor(self)


class TestQueueService:
    """Test cases for QueueService."""
    
    @pytest.fixture
    def mock_connection(self):
        """Create mock RabbitMQ connection."""
        connection = AsyncMock(spec=AbstractConnection)
        connection.is_closed = False
        return connection
    
    @pytest.fixture
    def mock_channel(self):
        """Create mock RabbitMQ channel."""
        channel = AsyncMock(spec=AbstractChannel)
        channel.is_closed = False
        channel.set_qos = AsyncMock()
        channel.declare_exchange = AsyncMock()
        channel.declare_queue = AsyncMock()
        channel.close = AsyncMock()
        return channel
    
    @pytest.fixture
    def mock_exchange(self):
        """Create mock RabbitMQ exchange."""
        exchange = AsyncMock(spec=AbstractExchange)
        exchange.publish = AsyncMock()
        return exchange
    
    @pytest.fixture
    def mock_queue(self):
        """Create mock RabbitMQ queue."""
        queue = AsyncMock(spec=AbstractQueue)
        queue.bind = AsyncMock()
        queue.consume = AsyncMock(return_value="consumer_tag_123")
        queue.cancel = AsyncMock()
        queue.purge = AsyncMock()
        queue.durable = True
        queue.auto_delete = False
        queue.arguments = {}
        return queue
    
    @pytest.fixture
    async def service(self, mock_connection, mock_channel, mock_exchange, mock_queue):
        """Create queue service with mocked dependencies."""
        with patch('aio_pika.connect_robust', return_value=mock_connection):
            mock_connection.channel.return_value = mock_channel
            mock_channel.declare_exchange.return_value = mock_exchange
            mock_channel.declare_queue.return_value = mock_queue
            
            service = QueueService()
            await service.initialize()
            
            return service
    
    @pytest.fixture
    def sample_ingest_job(self):
        """Create sample ingest job."""
        return IngestJob(
            id=str(uuid.uuid4()),
            source_path="/test/path/video.mp4",
            destination_project_id="project123",
            ingest_type=IngestType.STANDARD,
            status=IngestStatus.PENDING,
            priority=5,
            total_files=1,
            total_size=1000000,
            auto_generate_proxies=True,
            preserve_folder_structure=False
        )
    
    @pytest.fixture
    def sample_notification(self):
        """Create sample notification."""
        return IngestNotification(
            job_id=str(uuid.uuid4()),
            event_type="job_completed",
            message="Ingest job completed successfully",
            details={"processed_files": 10},
            timestamp=datetime.utcnow(),
            user_id="user123"
        )
    
    async def test_initialize_success(self, mock_connection, mock_channel, mock_exchange, mock_queue):
        """Test successful service initialization."""
        with patch('aio_pika.connect_robust', return_value=mock_connection):
            mock_connection.channel.return_value = mock_channel
            mock_channel.declare_exchange.return_value = mock_exchange
            mock_channel.declare_queue.return_value = mock_queue
            
            service = QueueService()
            await service.initialize()
            
            # Assertions
            assert service._is_initialized is True
            assert service.connection == mock_connection
            assert service.channel == mock_channel
            assert service.exchange == mock_exchange
            assert len(service.queues) > 0
            
            # Verify connection was established
            mock_connection.channel.assert_called_once()
            mock_channel.set_qos.assert_called_once_with(prefetch_count=settings.max_concurrent_ingests)
    
    async def test_initialize_already_initialized(self, service):
        """Test initialization when already initialized."""
        # Clear call counts
        service.connection.channel.reset_mock()
        
        # Initialize again
        await service.initialize()
        
        # Should not reconnect
        service.connection.channel.assert_not_called()
    
    async def test_initialize_connection_failure(self):
        """Test initialization with connection failure."""
        with patch('aio_pika.connect_robust', side_effect=Exception("Connection failed")):
            service = QueueService()
            
            with pytest.raises(QueueError, match="Failed to initialize queue service"):
                await service.initialize()
    
    async def test_setup_queues(self, service, mock_channel, mock_queue):
        """Test queue setup."""
        # Reset to track calls
        mock_channel.declare_queue.reset_mock()
        mock_queue.bind.reset_mock()
        
        # Call setup queues
        await service._setup_queues()
        
        # Should declare all configured queues
        expected_queues = ["ingest", "validation", "processing", "metadata", 
                          "notifications", "retry", "dead_letter"]
        assert mock_channel.declare_queue.call_count == len(expected_queues)
        assert mock_queue.bind.call_count == len(expected_queues)
    
    async def test_publish_ingest_job(self, service, sample_ingest_job, mock_exchange):
        """Test publishing an ingest job."""
        await service.publish_ingest_job(sample_ingest_job)
        
        # Verify message was published
        mock_exchange.publish.assert_called_once()
        
        # Check message content
        call_args = mock_exchange.publish.call_args
        message = call_args[0][0]
        assert isinstance(message, Message)
        assert message.correlation_id == sample_ingest_job.id
        assert message.priority == sample_ingest_job.priority
        
        # Check routing key
        routing_key = call_args[1]["routing_key"]
        assert routing_key == "ingest.job.created"
        
        # Check message body
        body = json.loads(message.body.decode())
        assert body["job_id"] == sample_ingest_job.id
        assert body["source_path"] == sample_ingest_job.source_path
    
    async def test_publish_validation_request(self, service, mock_exchange):
        """Test publishing a validation request."""
        file_path = "/test/file.mp4"
        job_id = str(uuid.uuid4())
        validation_rules = [{"type": "size", "max": 1000000}]
        
        await service.publish_validation_request(file_path, job_id, validation_rules)
        
        # Verify message was published
        mock_exchange.publish.assert_called_once()
        
        # Check routing key
        call_args = mock_exchange.publish.call_args
        routing_key = call_args[1]["routing_key"]
        assert routing_key == "ingest.validation.required"
        
        # Check message body
        message = call_args[0][0]
        body = json.loads(message.body.decode())
        assert body["job_id"] == job_id
        assert body["file_path"] == file_path
        assert body["validation_rules"] == validation_rules
    
    async def test_publish_metadata_extraction_request(self, service, mock_exchange):
        """Test publishing a metadata extraction request."""
        file_path = "/test/file.mp4"
        job_id = str(uuid.uuid4())
        
        await service.publish_metadata_extraction_request(
            file_path, job_id, extract_technical=True, extract_embedded=False
        )
        
        # Verify message was published
        mock_exchange.publish.assert_called_once()
        
        # Check message body
        message = mock_exchange.publish.call_args[0][0]
        body = json.loads(message.body.decode())
        assert body["job_id"] == job_id
        assert body["file_path"] == file_path
        assert body["extract_technical"] is True
        assert body["extract_embedded"] is False
    
    async def test_publish_proxy_request(self, service, mock_exchange):
        """Test publishing a proxy generation request."""
        asset_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        quality_presets = ["low", "high"]
        
        await service.publish_proxy_request(asset_id, job_id, quality_presets)
        
        # Verify message was published
        mock_exchange.publish.assert_called_once()
        
        # Check routing key
        call_args = mock_exchange.publish.call_args
        routing_key = call_args[1]["routing_key"]
        assert routing_key == "proxy.generation.requested"
        
        # Check message body
        message = call_args[0][0]
        body = json.loads(message.body.decode())
        assert body["asset_id"] == asset_id
        assert body["job_id"] == job_id
        assert body["quality_presets"] == quality_presets
    
    async def test_publish_notification(self, service, sample_notification, mock_exchange):
        """Test publishing a notification."""
        await service.publish_notification(sample_notification)
        
        # Verify message was published
        mock_exchange.publish.assert_called_once()
        
        # Check routing key
        call_args = mock_exchange.publish.call_args
        routing_key = call_args[1]["routing_key"]
        assert routing_key == f"ingest.notification.{sample_notification.event_type}"
        
        # Check message body
        message = call_args[0][0]
        body = json.loads(message.body.decode())
        assert body["job_id"] == sample_notification.job_id
        assert body["event_type"] == sample_notification.event_type
        assert body["message"] == sample_notification.message
    
    async def test_publish_retry_message(self, service, mock_exchange):
        """Test publishing a retry message."""
        original_routing_key = "ingest.job.created"
        original_body = {"job_id": "123", "data": "test"}
        retry_count = 2
        delay_seconds = 120
        
        await service.publish_retry_message(
            original_routing_key, original_body, retry_count, delay_seconds
        )
        
        # Verify message was published
        mock_exchange.publish.assert_called_once()
        
        # Check message headers for delay
        message = mock_exchange.publish.call_args[0][0]
        assert message.headers["x-delay"] == delay_seconds * 1000
        
        # Check message body
        body = json.loads(message.body.decode())
        assert body["original_routing_key"] == original_routing_key
        assert body["original_body"] == original_body
        assert body["retry_count"] == retry_count
    
    async def test_subscribe_to_queue(self, service, mock_queue):
        """Test subscribing to a queue."""
        queue_name = settings.rabbitmq_queues["ingest"]
        callback = AsyncMock()
        
        # Add queue to service
        service.queues[queue_name] = mock_queue
        
        await service.subscribe_to_queue(queue_name, callback, auto_ack=False)
        
        # Verify consumer was started
        mock_queue.consume.assert_called_once()
        assert queue_name in service.consumers
        assert service.consumers[queue_name] == "consumer_tag_123"
    
    async def test_subscribe_to_nonexistent_queue(self, service):
        """Test subscribing to non-existent queue."""
        with pytest.raises(QueueError, match="Queue nonexistent not found"):
            await service.subscribe_to_queue("nonexistent", AsyncMock())
    
    async def test_message_processor_success(self, service, mock_queue):
        """Test message processor with successful callback."""
        queue_name = settings.rabbitmq_queues["ingest"]
        callback = AsyncMock()
        
        # Add queue and subscribe
        service.queues[queue_name] = mock_queue
        await service.subscribe_to_queue(queue_name, callback)
        
        # Get the message processor function
        message_processor = mock_queue.consume.call_args[0][0]
        
        # Create mock message
        message_body = {"job_id": "123", "data": "test"}
        mock_message = MockIncomingMessage(json.dumps(message_body))
        
        # Process message
        await message_processor(mock_message)
        
        # Verify callback was called
        callback.assert_called_once_with(message_body, mock_message)
    
    async def test_message_processor_json_decode_error(self, service, mock_queue):
        """Test message processor with invalid JSON."""
        queue_name = settings.rabbitmq_queues["ingest"]
        callback = AsyncMock()
        
        # Add queue and subscribe
        service.queues[queue_name] = mock_queue
        await service.subscribe_to_queue(queue_name, callback)
        
        # Get the message processor
        message_processor = mock_queue.consume.call_args[0][0]
        
        # Create message with invalid JSON
        mock_message = MockIncomingMessage(b"invalid json")
        
        # Process should raise exception
        with pytest.raises(json.JSONDecodeError):
            await message_processor(mock_message)
        
        # Callback should not be called
        callback.assert_not_called()
    
    async def test_message_processor_callback_error_with_retry(self, service, mock_queue, mock_exchange):
        """Test message processor when callback fails and retry is needed."""
        queue_name = settings.rabbitmq_queues["ingest"]
        callback = AsyncMock(side_effect=Exception("Processing failed"))
        
        # Add queue and subscribe
        service.queues[queue_name] = mock_queue
        await service.subscribe_to_queue(queue_name, callback)
        
        # Get the message processor
        message_processor = mock_queue.consume.call_args[0][0]
        
        # Create message
        message_body = {"job_id": "123"}
        mock_message = MockIncomingMessage(
            json.dumps(message_body),
            headers={"x-delivery-count": 1}
        )
        
        # Process should raise exception
        with pytest.raises(Exception, match="Processing failed"):
            await message_processor(mock_message)
        
        # Verify retry was published
        assert mock_exchange.publish.call_count >= 1
    
    async def test_unsubscribe_from_queue(self, service, mock_queue):
        """Test unsubscribing from a queue."""
        queue_name = settings.rabbitmq_queues["ingest"]
        
        # Add queue and consumer
        service.queues[queue_name] = mock_queue
        service.consumers[queue_name] = "consumer_tag_123"
        
        await service.unsubscribe_from_queue(queue_name)
        
        # Verify consumer was cancelled
        mock_queue.cancel.assert_called_once_with("consumer_tag_123")
        assert queue_name not in service.consumers
    
    async def test_get_queue_info(self, service, mock_channel, mock_queue):
        """Test getting queue information."""
        queue_name = settings.rabbitmq_queues["ingest"]
        service.queues[queue_name] = mock_queue
        
        # Mock declaration result
        mock_result = Mock()
        mock_result.method.message_count = 10
        mock_result.method.consumer_count = 2
        mock_channel.declare_queue.return_value = mock_result
        
        info = await service.get_queue_info(queue_name)
        
        # Assertions
        assert info["name"] == queue_name
        assert info["message_count"] == 10
        assert info["consumer_count"] == 2
        assert info["is_durable"] is True
    
    async def test_get_queue_info_nonexistent(self, service):
        """Test getting info for non-existent queue."""
        with pytest.raises(QueueError, match="Queue nonexistent not found"):
            await service.get_queue_info("nonexistent")
    
    async def test_purge_queue(self, service, mock_queue):
        """Test purging a queue."""
        queue_name = settings.rabbitmq_queues["ingest"]
        service.queues[queue_name] = mock_queue
        
        # Mock purge result
        mock_result = Mock()
        mock_result.method.message_count = 25
        mock_queue.purge.return_value = mock_result
        
        count = await service.purge_queue(queue_name)
        
        # Assertions
        assert count == 25
        mock_queue.purge.assert_called_once()
    
    async def test_health_check_healthy(self, service):
        """Test health check when service is healthy."""
        health = await service.health_check()
        
        assert health["status"] == "healthy"
        assert health["connection_ok"] is True
        assert health["channel_ok"] is True
        assert "queues" in health
        assert health["consumers"] == 0
    
    async def test_health_check_unhealthy(self, service):
        """Test health check when service is unhealthy."""
        # Mark connection as closed
        service.connection.is_closed = True
        
        health = await service.health_check()
        
        assert health["status"] == "unhealthy"
        assert health["connection_ok"] is False
    
    async def test_close(self, service, mock_channel, mock_connection):
        """Test closing the service."""
        # Add a consumer
        service.consumers["test_queue"] = "consumer_tag"
        
        await service.close()
        
        # Verify cleanup
        assert len(service.consumers) == 0
        mock_channel.close.assert_called_once()
        mock_connection.close.assert_called_once()
        assert service._is_initialized is False
    
    async def test_close_with_error(self, service, mock_channel):
        """Test closing service when error occurs."""
        mock_channel.close.side_effect = Exception("Close failed")
        
        # Should not raise exception
        await service.close()
        
        assert service._is_initialized is False
    
    async def test_ensure_initialized(self):
        """Test ensure initialized when not initialized."""
        service = QueueService()
        assert service._is_initialized is False
        
        with patch.object(service, 'initialize', new_callable=AsyncMock) as mock_init:
            await service._ensure_initialized()
            mock_init.assert_called_once()
    
    async def test_get_queue_service_singleton(self):
        """Test that get_queue_service returns singleton."""
        with patch('aio_pika.connect_robust', new_callable=AsyncMock):
            service1 = await get_queue_service()
            service2 = await get_queue_service()
            
            assert service1 is service2
    
    async def test_message_persistence(self, service, mock_exchange):
        """Test that messages are published with persistence."""
        await service._publish_message(
            routing_key="test.key",
            body={"test": "data"},
            priority=5
        )
        
        # Check message was published with persistence
        message = mock_exchange.publish.call_args[0][0]
        assert message.delivery_mode == DeliveryMode.PERSISTENT
    
    async def test_correlation_id_generation(self, service, mock_exchange):
        """Test automatic correlation ID generation."""
        await service._publish_message(
            routing_key="test.key",
            body={"test": "data"}
        )
        
        # Check correlation ID was generated
        message = mock_exchange.publish.call_args[0][0]
        assert message.correlation_id is not None
        assert len(message.correlation_id) == 36  # UUID length
    
    async def test_delayed_message_publishing(self, service, mock_exchange):
        """Test publishing delayed messages."""
        delay_ms = 5000
        
        await service._publish_message(
            routing_key="test.key",
            body={"test": "data"},
            delay=delay_ms
        )
        
        # Check delay header was set
        message = mock_exchange.publish.call_args[0][0]
        assert message.headers["x-delay"] == delay_ms
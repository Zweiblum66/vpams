"""
Tests for optimized indexing functionality
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from src.core.optimized_indexer import (
    OptimizedIndexer, BulkDocument, IndexingStats
)
from src.core.config import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    return Settings(
        service_name="search-engine-test",
        opensearch_url="http://localhost:9200",
        redis_url="redis://localhost:6379",
        debug=True
    )


@pytest.fixture
def mock_opensearch_client():
    """Mock OpenSearch client"""
    client = AsyncMock()
    
    # Mock cluster methods
    client.cluster.put_settings = AsyncMock(return_value={"acknowledged": True})
    
    # Mock indices methods
    client.indices.put_template = AsyncMock(return_value={"acknowledged": True})
    client.indices.put_settings = AsyncMock(return_value={"acknowledged": True})
    client.indices.refresh = AsyncMock(return_value={"_shards": {"successful": 1}})
    client.indices.get_settings = AsyncMock(return_value={
        "test_index": {
            "settings": {
                "index": {
                    "refresh_interval": "1s"
                }
            }
        }
    })
    
    return client


@pytest.fixture
async def indexer(mock_settings, mock_opensearch_client):
    """Create an optimized indexer instance"""
    indexer = OptimizedIndexer(
        settings=mock_settings,
        client=mock_opensearch_client,
        batch_size=10,
        max_queue_size=100,
        parallel_bulk_processes=2
    )
    await indexer.initialize()
    yield indexer
    await indexer.shutdown()


class TestBulkDocument:
    """Test BulkDocument class"""
    
    def test_bulk_document_creation(self):
        """Test creating a bulk document"""
        doc = BulkDocument(
            index="test_index",
            id="doc1",
            source={"title": "Test Document", "content": "Test content"},
            routing="shard1"
        )
        
        assert doc.index == "test_index"
        assert doc.id == "doc1"
        assert doc.source["title"] == "Test Document"
        assert doc.routing == "shard1"
        assert doc.action == "index"
    
    def test_bulk_document_to_action(self):
        """Test converting document to bulk action"""
        doc = BulkDocument(
            index="test_index",
            id="doc1",
            source={"title": "Test"},
            routing="shard1",
            version=2
        )
        
        action = doc.to_bulk_action()
        
        assert "index" in action
        assert action["index"]["_index"] == "test_index"
        assert action["index"]["_id"] == "doc1"
        assert action["index"]["routing"] == "shard1"
        assert action["index"]["_version"] == 2
        assert action["index"]["_version_type"] == "external"
    
    def test_bulk_document_size(self):
        """Test calculating document size"""
        doc = BulkDocument(
            index="test_index",
            id="doc1",
            source={"text": "a" * 100}
        )
        
        size = doc.get_size()
        assert size > 100  # Should include JSON overhead


class TestIndexingStats:
    """Test IndexingStats class"""
    
    def test_stats_initialization(self):
        """Test stats initialization"""
        stats = IndexingStats()
        
        assert stats.documents_indexed == 0
        assert stats.documents_failed == 0
        assert stats.bytes_indexed == 0
        assert stats.indexing_time_ms == 0
        assert stats.last_index_time is None
        assert len(stats.errors) == 0
    
    def test_add_success(self):
        """Test adding successful indexing"""
        stats = IndexingStats()
        
        stats.add_success(count=10, bytes_size=1024, time_ms=100)
        
        assert stats.documents_indexed == 10
        assert stats.bytes_indexed == 1024
        assert stats.indexing_time_ms == 100
        assert stats.last_index_time is not None
    
    def test_add_failure(self):
        """Test adding failed indexing"""
        stats = IndexingStats()
        
        stats.add_failure(count=5, error="Connection timeout")
        
        assert stats.documents_failed == 5
        assert len(stats.errors) == 1
        assert stats.errors[0]["error"] == "Connection timeout"
        assert stats.errors[0]["count"] == 5
    
    def test_get_stats(self):
        """Test getting stats summary"""
        stats = IndexingStats()
        
        stats.add_success(count=100, bytes_size=10240, time_ms=1000)
        stats.add_failure(count=5, error="Error")
        
        summary = stats.get_stats()
        
        assert summary["documents_indexed"] == 100
        assert summary["documents_failed"] == 5
        assert summary["bytes_indexed"] == 10240
        assert summary["average_time_per_doc_ms"] == 10  # 1000/100
        assert summary["error_count"] == 1


class TestOptimizedIndexer:
    """Test OptimizedIndexer class"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, indexer, mock_opensearch_client):
        """Test indexer initialization"""
        assert indexer.batch_size == 10
        assert indexer.max_queue_size == 100
        assert indexer.is_processing is True
        
        # Check that cluster settings were optimized
        mock_opensearch_client.cluster.put_settings.assert_called()
        
        # Check that templates were created
        assert mock_opensearch_client.indices.put_template.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_index_single_document(self, indexer):
        """Test indexing a single document"""
        # Index a document
        await indexer.index_document(
            index="test_index",
            doc_id="doc1",
            document={"title": "Test"}
        )
        
        # Document should be in queue
        assert len(indexer.queue) == 1
        assert indexer.queue[0].id == "doc1"
    
    @pytest.mark.asyncio
    async def test_index_multiple_documents(self, indexer):
        """Test indexing multiple documents"""
        docs = [
            ("test_index", f"doc{i}", {"title": f"Test {i}"})
            for i in range(5)
        ]
        
        await indexer.index_documents(docs)
        
        # All documents should be in queue
        assert len(indexer.queue) == 5
    
    @pytest.mark.asyncio
    async def test_immediate_indexing(self, indexer, mock_opensearch_client):
        """Test immediate indexing without queuing"""
        # Mock helpers.async_bulk
        with patch('opensearchpy.helpers.async_bulk') as mock_bulk:
            # Create async generator mock
            async def mock_async_bulk_gen(*args, **kwargs):
                for i in range(3):
                    yield True, {"_id": f"doc{i}"}
            
            mock_bulk.return_value = mock_async_bulk_gen()
            
            # Index documents immediately
            await indexer.index_document(
                index="test_index",
                doc_id="doc1",
                document={"title": "Test"},
                immediate=True
            )
            
            # Queue should be empty
            assert len(indexer.queue) == 0
            
            # Bulk indexing should have been called
            mock_bulk.assert_called()
    
    @pytest.mark.asyncio
    async def test_batch_processing(self, indexer, mock_opensearch_client):
        """Test batch processing when queue reaches batch size"""
        # Mock helpers.async_bulk
        with patch('opensearchpy.helpers.async_bulk') as mock_bulk:
            # Create async generator mock
            async def mock_async_bulk_gen(*args, **kwargs):
                actions = args[1]
                for action in actions:
                    yield True, action
            
            mock_bulk.return_value = mock_async_bulk_gen()
            
            # Add documents up to batch size
            for i in range(10):
                await indexer.index_document(
                    index="test_index",
                    doc_id=f"doc{i}",
                    document={"title": f"Test {i}"}
                )
            
            # Wait for processing
            await asyncio.sleep(0.2)
            
            # Queue should be processed
            assert len(indexer.queue) < 10
            assert indexer.stats.documents_indexed > 0
    
    @pytest.mark.asyncio
    async def test_adaptive_refresh(self, indexer, mock_opensearch_client):
        """Test adaptive refresh interval management"""
        # Test disabling refresh
        await indexer._set_index_refresh("test_index", "-1")
        
        mock_opensearch_client.indices.put_settings.assert_called_with(
            index="test_index",
            body={"index": {"refresh_interval": "-1"}}
        )
        
        # Test restoring refresh
        await indexer._restore_index_refresh("test_index")
        
        # Should restore and force refresh
        assert mock_opensearch_client.indices.refresh.called
    
    @pytest.mark.asyncio
    async def test_parallel_indexing(self, indexer, mock_opensearch_client):
        """Test parallel bulk indexing"""
        with patch('opensearchpy.helpers.async_bulk') as mock_bulk:
            # Track concurrent calls
            concurrent_calls = []
            
            async def mock_async_bulk_gen(*args, **kwargs):
                concurrent_calls.append(time.time())
                await asyncio.sleep(0.1)  # Simulate processing
                for i in range(5):
                    yield True, {"_id": f"doc{i}"}
            
            mock_bulk.return_value = mock_async_bulk_gen()
            
            # Create many documents to trigger parallel processing
            docs = [
                BulkDocument(
                    index="test_index",
                    id=f"doc{i}",
                    source={"title": f"Test {i}"}
                )
                for i in range(100)
            ]
            
            await indexer._index_batch_parallel(docs)
            
            # Should have multiple concurrent calls
            assert len(concurrent_calls) > 1
    
    @pytest.mark.asyncio
    async def test_error_handling(self, indexer, mock_opensearch_client):
        """Test error handling during indexing"""
        with patch('opensearchpy.helpers.async_bulk') as mock_bulk:
            # Simulate error
            mock_bulk.side_effect = Exception("Connection error")
            
            docs = [
                BulkDocument(
                    index="test_index",
                    id="doc1",
                    source={"title": "Test"}
                )
            ]
            
            # Should not raise exception
            await indexer._index_batch_parallel(docs)
            
            # Error should be tracked
            assert indexer.stats.documents_failed > 0
    
    @pytest.mark.asyncio
    async def test_create_optimized_index(self, indexer, mock_opensearch_client):
        """Test creating index with optimal settings"""
        mock_opensearch_client.indices.create = AsyncMock(return_value={"acknowledged": True})
        
        # Test with large document count
        result = await indexer.create_index_with_optimal_settings(
            "large_index",
            doc_count_estimate=50_000_000
        )
        
        assert result is True
        
        # Check that appropriate shard count was calculated
        call_args = mock_opensearch_client.indices.create.call_args
        settings = call_args[1]["body"]["settings"]
        
        # Should have multiple shards for 50M docs
        assert settings["number_of_shards"] > 1
        assert settings["refresh_interval"] == "60s"  # Large index refresh
    
    @pytest.mark.asyncio
    async def test_stats_reporting(self, indexer):
        """Test getting indexer statistics"""
        # Add some stats
        indexer.stats.add_success(100, 1024000, 1000)
        indexer.stats.add_failure(5, "Test error")
        
        # Add some documents to queue
        for i in range(15):
            await indexer.index_document(
                index="test_index",
                doc_id=f"doc{i}",
                document={"title": f"Test {i}"}
            )
        
        stats = indexer.get_stats()
        
        assert stats["documents_indexed"] == 100
        assert stats["documents_failed"] == 5
        assert stats["queue_size"] == 15
        assert stats["is_processing"] is True
    
    @pytest.mark.asyncio
    async def test_shutdown(self, mock_settings, mock_opensearch_client):
        """Test graceful shutdown"""
        indexer = OptimizedIndexer(
            settings=mock_settings,
            client=mock_opensearch_client,
            batch_size=10
        )
        await indexer.initialize()
        
        # Add some documents
        for i in range(5):
            await indexer.index_document(
                index="test_index",
                doc_id=f"doc{i}",
                document={"title": f"Test {i}"}
            )
        
        # Shutdown should process remaining documents
        await indexer.shutdown()
        
        assert indexer.is_processing is False
        # Cluster settings should be restored
        assert mock_opensearch_client.cluster.put_settings.call_count >= 2
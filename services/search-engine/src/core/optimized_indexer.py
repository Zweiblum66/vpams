"""
Optimized search indexing system with performance enhancements
"""

import asyncio
import json
import logging
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, AsyncGenerator
from dataclasses import dataclass, field
import hashlib
from concurrent.futures import ThreadPoolExecutor

from opensearchpy import AsyncOpenSearch, helpers
from opensearchpy.exceptions import OpenSearchException
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import Settings
from .opensearch import get_index_name

logger = logging.getLogger(__name__)


@dataclass
class IndexingStats:
    """Track indexing performance metrics"""
    documents_indexed: int = 0
    documents_failed: int = 0
    bytes_indexed: int = 0
    indexing_time_ms: float = 0
    last_index_time: Optional[datetime] = None
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_success(self, count: int, bytes_size: int, time_ms: float):
        self.documents_indexed += count
        self.bytes_indexed += bytes_size
        self.indexing_time_ms += time_ms
        self.last_index_time = datetime.utcnow()
    
    def add_failure(self, count: int, error: str):
        self.documents_failed += count
        self.errors.append({
            "timestamp": datetime.utcnow().isoformat(),
            "error": error,
            "count": count
        })
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "documents_indexed": self.documents_indexed,
            "documents_failed": self.documents_failed,
            "bytes_indexed": self.bytes_indexed,
            "average_time_per_doc_ms": (
                self.indexing_time_ms / self.documents_indexed 
                if self.documents_indexed > 0 else 0
            ),
            "last_index_time": self.last_index_time.isoformat() if self.last_index_time else None,
            "error_count": len(self.errors),
            "recent_errors": self.errors[-10:]  # Last 10 errors
        }


@dataclass
class BulkDocument:
    """Represents a document for bulk indexing"""
    index: str
    id: str
    source: Dict[str, Any]
    action: str = "index"
    routing: Optional[str] = None
    version: Optional[int] = None
    retry_count: int = 0
    
    def to_bulk_action(self) -> Dict[str, Any]:
        """Convert to OpenSearch bulk action format"""
        action_data = {
            "_index": self.index,
            "_id": self.id,
            "_source": self.source
        }
        
        if self.routing:
            action_data["routing"] = self.routing
            
        if self.version:
            action_data["_version"] = self.version
            action_data["_version_type"] = "external"
            
        return {self.action: action_data}
    
    def get_size(self) -> int:
        """Get approximate size in bytes"""
        return len(json.dumps(self.source).encode('utf-8'))


class OptimizedIndexer:
    """High-performance indexer with batching, parallel processing, and adaptive refresh"""
    
    def __init__(
        self,
        settings: Settings,
        client: AsyncOpenSearch,
        batch_size: int = 500,
        max_queue_size: int = 10000,
        parallel_bulk_processes: int = 4,
        adaptive_refresh: bool = True
    ):
        self.settings = settings
        self.client = client
        self.batch_size = batch_size
        self.max_queue_size = max_queue_size
        self.parallel_bulk_processes = parallel_bulk_processes
        self.adaptive_refresh = adaptive_refresh
        
        # Indexing queue and processing
        self.queue: deque[BulkDocument] = deque(maxlen=max_queue_size)
        self.processing_lock = asyncio.Lock()
        self.is_processing = False
        
        # Performance tracking
        self.stats = IndexingStats()
        self.index_refresh_intervals: Dict[str, int] = {}
        
        # Thread pool for CPU-intensive operations
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # Index settings cache
        self._index_settings_cache: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self):
        """Initialize the indexer and optimize index settings"""
        logger.info("Initializing optimized indexer")
        
        # Optimize cluster settings for bulk indexing
        await self._optimize_cluster_settings()
        
        # Create index templates for common patterns
        await self._create_index_templates()
        
        # Start background processing
        self.is_processing = True
        asyncio.create_task(self._process_queue())
        
    async def shutdown(self):
        """Gracefully shutdown the indexer"""
        logger.info("Shutting down optimized indexer")
        self.is_processing = False
        
        # Process remaining documents
        await self._flush_queue()
        
        # Restore normal settings
        await self._restore_cluster_settings()
        
        self.thread_pool.shutdown(wait=True)
        
    async def _optimize_cluster_settings(self):
        """Optimize cluster settings for bulk indexing"""
        try:
            # Increase thread pool sizes for bulk operations
            await self.client.cluster.put_settings(
                body={
                    "transient": {
                        "thread_pool.write.size": 10,
                        "thread_pool.write.queue_size": 1000,
                        "indices.memory.index_buffer_size": "30%",
                        "cluster.routing.allocation.node_concurrent_recoveries": 4
                    }
                }
            )
            logger.info("Optimized cluster settings for bulk indexing")
        except Exception as e:
            logger.warning(f"Failed to optimize cluster settings: {e}")
    
    async def _restore_cluster_settings(self):
        """Restore normal cluster settings"""
        try:
            await self.client.cluster.put_settings(
                body={
                    "transient": {
                        "thread_pool.write.size": None,
                        "thread_pool.write.queue_size": None,
                        "indices.memory.index_buffer_size": None,
                        "cluster.routing.allocation.node_concurrent_recoveries": None
                    }
                }
            )
        except Exception as e:
            logger.warning(f"Failed to restore cluster settings: {e}")
    
    async def _create_index_templates(self):
        """Create optimized index templates"""
        templates = {
            "mams_assets": {
                "index_patterns": ["assets*"],
                "settings": {
                    "number_of_shards": 3,
                    "number_of_replicas": 1,
                    "refresh_interval": "30s",
                    "index": {
                        "codec": "best_compression",
                        "merge": {
                            "scheduler": {
                                "max_thread_count": 2
                            }
                        }
                    }
                },
                "mappings": {
                    "dynamic_templates": [
                        {
                            "strings_as_keywords": {
                                "match_mapping_type": "string",
                                "match": "*_id",
                                "mapping": {
                                    "type": "keyword"
                                }
                            }
                        }
                    ]
                }
            },
            "mams_metadata": {
                "index_patterns": ["metadata*"],
                "settings": {
                    "number_of_shards": 2,
                    "number_of_replicas": 1,
                    "refresh_interval": "30s"
                }
            }
        }
        
        for name, template in templates.items():
            try:
                await self.client.indices.put_template(
                    name=name,
                    body=template
                )
                logger.info(f"Created index template: {name}")
            except Exception as e:
                logger.warning(f"Failed to create template {name}: {e}")
    
    async def index_document(
        self,
        index: str,
        doc_id: str,
        document: Dict[str, Any],
        routing: Optional[str] = None,
        immediate: bool = False
    ):
        """Index a single document"""
        bulk_doc = BulkDocument(
            index=index,
            id=doc_id,
            source=document,
            routing=routing
        )
        
        if immediate:
            await self._index_immediate([bulk_doc])
        else:
            await self._add_to_queue(bulk_doc)
    
    async def index_documents(
        self,
        documents: List[Tuple[str, str, Dict[str, Any]]],
        routing: Optional[str] = None,
        immediate: bool = False
    ):
        """Index multiple documents"""
        bulk_docs = [
            BulkDocument(
                index=index,
                id=doc_id,
                source=doc,
                routing=routing
            )
            for index, doc_id, doc in documents
        ]
        
        if immediate:
            await self._index_immediate(bulk_docs)
        else:
            for doc in bulk_docs:
                await self._add_to_queue(doc)
    
    async def _add_to_queue(self, document: BulkDocument):
        """Add document to indexing queue"""
        if len(self.queue) >= self.max_queue_size:
            # Queue is full, process immediately
            await self._flush_queue()
        
        self.queue.append(document)
    
    async def _process_queue(self):
        """Background task to process the indexing queue"""
        while self.is_processing:
            try:
                if len(self.queue) >= self.batch_size:
                    await self._flush_batch()
                elif len(self.queue) > 0:
                    # Wait a bit for more documents or timeout
                    await asyncio.sleep(1)
                    if len(self.queue) > 0:
                        await self._flush_batch()
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in queue processing: {e}")
                await asyncio.sleep(1)
    
    async def _flush_queue(self):
        """Flush all documents in the queue"""
        async with self.processing_lock:
            while self.queue:
                await self._flush_batch()
    
    async def _flush_batch(self):
        """Flush a batch of documents from the queue"""
        batch = []
        batch_size = min(self.batch_size, len(self.queue))
        
        for _ in range(batch_size):
            if self.queue:
                batch.append(self.queue.popleft())
        
        if batch:
            await self._index_batch_parallel(batch)
    
    async def _index_immediate(self, documents: List[BulkDocument]):
        """Index documents immediately without queuing"""
        await self._index_batch_parallel(documents)
    
    async def _index_batch_parallel(self, documents: List[BulkDocument]):
        """Index a batch of documents with parallel processing"""
        if not documents:
            return
        
        start_time = time.time()
        
        # Group documents by index for optimized processing
        docs_by_index: Dict[str, List[BulkDocument]] = {}
        for doc in documents:
            if doc.index not in docs_by_index:
                docs_by_index[doc.index] = []
            docs_by_index[doc.index].append(doc)
        
        # Process each index group in parallel
        tasks = []
        for index, index_docs in docs_by_index.items():
            # Split into smaller chunks for parallel processing
            chunk_size = max(50, len(index_docs) // self.parallel_bulk_processes)
            chunks = [
                index_docs[i:i + chunk_size]
                for i in range(0, len(index_docs), chunk_size)
            ]
            
            for chunk in chunks:
                task = self._index_chunk(index, chunk)
                tasks.append(task)
        
        # Wait for all parallel tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        total_indexed = 0
        total_failed = 0
        total_bytes = 0
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Chunk indexing failed: {result}")
                total_failed += len(documents) // len(results)  # Approximate
            else:
                indexed, failed, bytes_size = result
                total_indexed += indexed
                total_failed += failed
                total_bytes += bytes_size
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Update stats
        if total_indexed > 0:
            self.stats.add_success(total_indexed, total_bytes, elapsed_ms)
        if total_failed > 0:
            self.stats.add_failure(total_failed, "Bulk indexing failures")
        
        logger.info(
            f"Indexed {total_indexed} documents in {elapsed_ms:.2f}ms "
            f"({total_bytes / 1024 / 1024:.2f} MB)"
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _index_chunk(
        self,
        index: str,
        documents: List[BulkDocument]
    ) -> Tuple[int, int, int]:
        """Index a chunk of documents for a specific index"""
        if not documents:
            return 0, 0, 0
        
        # Prepare bulk actions
        actions = []
        total_bytes = 0
        
        for doc in documents:
            action = {
                "_op_type": doc.action,
                "_index": doc.index,
                "_id": doc.id,
                "_source": doc.source
            }
            
            if doc.routing:
                action["routing"] = doc.routing
                
            actions.append(action)
            total_bytes += doc.get_size()
        
        # Perform bulk indexing
        try:
            # Temporarily disable refresh for bulk operation
            if self.adaptive_refresh:
                await self._set_index_refresh(index, "-1")
            
            # Use helpers.async_bulk for better performance
            success_count = 0
            failed_count = 0
            
            async for ok, result in helpers.async_bulk(
                self.client,
                actions,
                chunk_size=100,
                max_retries=2,
                initial_backoff=2,
                max_backoff=600,
                yield_ok=True
            ):
                if ok:
                    success_count += 1
                else:
                    failed_count += 1
                    logger.warning(f"Failed to index document: {result}")
            
            # Restore refresh interval
            if self.adaptive_refresh:
                await self._restore_index_refresh(index)
            
            return success_count, failed_count, total_bytes
            
        except Exception as e:
            logger.error(f"Bulk indexing error: {e}")
            # On error, restore refresh interval
            if self.adaptive_refresh:
                await self._restore_index_refresh(index)
            raise
    
    async def _set_index_refresh(self, index: str, interval: str):
        """Set index refresh interval"""
        try:
            # Store original interval
            if index not in self.index_refresh_intervals:
                settings = await self.client.indices.get_settings(index=index)
                index_settings = settings.get(index, {}).get("settings", {}).get("index", {})
                self.index_refresh_intervals[index] = index_settings.get("refresh_interval", "1s")
            
            # Set new interval
            await self.client.indices.put_settings(
                index=index,
                body={"index": {"refresh_interval": interval}}
            )
        except Exception as e:
            logger.warning(f"Failed to set refresh interval for {index}: {e}")
    
    async def _restore_index_refresh(self, index: str):
        """Restore original index refresh interval"""
        try:
            original = self.index_refresh_intervals.get(index, "1s")
            await self.client.indices.put_settings(
                index=index,
                body={"index": {"refresh_interval": original}}
            )
            
            # Force refresh after bulk operation
            await self.client.indices.refresh(index=index)
        except Exception as e:
            logger.warning(f"Failed to restore refresh interval for {index}: {e}")
    
    async def optimize_indices(self, indices: Optional[List[str]] = None):
        """Optimize indices for better search performance"""
        if indices is None:
            indices = ["assets*", "metadata*", "content*"]
        
        for index_pattern in indices:
            try:
                # Force merge to reduce segments
                await self.client.indices.forcemerge(
                    index=index_pattern,
                    max_num_segments=1,
                    flush=True
                )
                logger.info(f"Optimized index: {index_pattern}")
                
                # Clear cache
                await self.client.indices.clear_cache(index=index_pattern)
                
            except Exception as e:
                logger.warning(f"Failed to optimize {index_pattern}: {e}")
    
    async def reindex_with_new_settings(
        self,
        source_index: str,
        target_index: str,
        new_settings: Dict[str, Any],
        new_mappings: Optional[Dict[str, Any]] = None
    ):
        """Reindex with optimized settings using aliases for zero downtime"""
        try:
            # Create target index with new settings
            body = {"settings": new_settings}
            if new_mappings:
                body["mappings"] = new_mappings
            
            await self.client.indices.create(index=target_index, body=body)
            
            # Reindex data
            await self.client.reindex(
                body={
                    "source": {"index": source_index},
                    "dest": {"index": target_index}
                },
                wait_for_completion=False
            )
            
            # Monitor reindex progress
            task_id = (await self.client.tasks.list(
                detailed=True,
                actions="*reindex"
            ))["tasks"]
            
            logger.info(f"Started reindex from {source_index} to {target_index}")
            
            # Switch aliases atomically
            await self.client.indices.update_aliases(
                body={
                    "actions": [
                        {"remove": {"index": source_index, "alias": f"{source_index}_alias"}},
                        {"add": {"index": target_index, "alias": f"{source_index}_alias"}}
                    ]
                }
            )
            
        except Exception as e:
            logger.error(f"Reindex failed: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        return {
            **self.stats.get_stats(),
            "queue_size": len(self.queue),
            "max_queue_size": self.max_queue_size,
            "batch_size": self.batch_size,
            "is_processing": self.is_processing
        }
    
    async def create_index_with_optimal_settings(
        self,
        index_name: str,
        doc_count_estimate: int = 1000000
    ) -> bool:
        """Create index with settings optimized for document count"""
        # Calculate optimal shard count
        shard_count = max(1, min(20, doc_count_estimate // 1000000))
        
        # Calculate optimal refresh interval based on indexing rate
        if doc_count_estimate > 10000000:
            refresh_interval = "60s"
        elif doc_count_estimate > 1000000:
            refresh_interval = "30s"
        else:
            refresh_interval = "5s"
        
        settings = {
            "number_of_shards": shard_count,
            "number_of_replicas": 1,
            "refresh_interval": refresh_interval,
            "index": {
                "codec": "best_compression",
                "merge": {
                    "policy": {
                        "max_merge_at_once": 5,
                        "segments_per_tier": 5
                    }
                },
                "translog": {
                    "durability": "async",
                    "sync_interval": "30s"
                }
            },
            "analysis": {
                "analyzer": {
                    "default": {
                        "type": "standard",
                        "stopwords": "_english_"
                    },
                    "autocomplete": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "autocomplete_filter"]
                    }
                },
                "filter": {
                    "autocomplete_filter": {
                        "type": "edge_ngram",
                        "min_gram": 2,
                        "max_gram": 20
                    }
                }
            }
        }
        
        try:
            await self.client.indices.create(
                index=index_name,
                body={"settings": settings}
            )
            logger.info(f"Created optimized index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            return False
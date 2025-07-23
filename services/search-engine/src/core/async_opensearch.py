"""
Async OpenSearch client with connection pooling and optimizations
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from opensearchpy import AsyncOpenSearch, AsyncHttpConnection
from opensearchpy.exceptions import ConnectionError, TransportError
from opensearchpy.helpers import bulk as sync_bulk
from opensearchpy.helpers import async_bulk

from .config import Settings

logger = logging.getLogger(__name__)


class OptimizedAsyncOpenSearch:
    """Optimized async OpenSearch client with connection pooling and retries"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: Optional[AsyncOpenSearch] = None
        self._connection_pool_size = 25
        self._max_retries = 3
        
    async def initialize(self):
        """Initialize the async OpenSearch client"""
        # Parse OpenSearch URL
        parsed_url = urlparse(self.settings.opensearch_url)
        
        # Configure connection settings
        client_config = {
            "hosts": [{
                "host": parsed_url.hostname,
                "port": parsed_url.port or 9200,
                "scheme": parsed_url.scheme or "http"
            }],
            "http_compress": True,  # Enable compression
            "verify_certs": False,  # For development
            "ssl_show_warn": False,
            "max_retries": self._max_retries,
            "retry_on_timeout": True,
            "timeout": 30,
            # Connection pooling
            "connections_per_node": self._connection_pool_size,
            # Use async connection class
            "connection_class": AsyncHttpConnection,
            # HTTP settings
            "http_auth": (parsed_url.username, parsed_url.password) if parsed_url.username else None,
        }
        
        # Create async client
        self._client = AsyncOpenSearch(**client_config)
        
        # Test connection
        try:
            info = await self._client.info()
            logger.info(f"Connected to OpenSearch cluster: {info['cluster_name']}")
        except Exception as e:
            logger.error(f"Failed to connect to OpenSearch: {e}")
            raise
    
    async def close(self):
        """Close the client connection"""
        if self._client:
            await self._client.close()
    
    @property
    def client(self) -> AsyncOpenSearch:
        """Get the OpenSearch client"""
        if not self._client:
            raise RuntimeError("OpenSearch client not initialized")
        return self._client
    
    async def wait_for_cluster_health(
        self,
        health: str = "yellow",
        timeout: str = "30s"
    ) -> bool:
        """Wait for cluster to reach specified health status"""
        try:
            response = await self._client.cluster.health(
                wait_for_status=health,
                timeout=timeout
            )
            return response["status"] in ["green", "yellow"]
        except Exception as e:
            logger.error(f"Error checking cluster health: {e}")
            return False
    
    async def optimize_for_indexing(self):
        """Optimize cluster settings for bulk indexing"""
        try:
            # Increase refresh interval for all indices during bulk indexing
            await self._client.indices.put_settings(
                index="_all",
                body={
                    "index": {
                        "refresh_interval": "30s",
                        "number_of_replicas": 0  # Temporarily disable replicas
                    }
                }
            )
            
            # Increase indexing buffer
            await self._client.cluster.put_settings(
                body={
                    "transient": {
                        "indices.memory.index_buffer_size": "30%",
                        "indices.memory.min_index_buffer_size": "96mb",
                        "indices.memory.max_index_buffer_size": "512mb"
                    }
                }
            )
            
            logger.info("Optimized cluster for bulk indexing")
        except Exception as e:
            logger.warning(f"Failed to optimize for indexing: {e}")
    
    async def restore_normal_settings(self):
        """Restore normal cluster settings after bulk indexing"""
        try:
            # Restore refresh interval
            await self._client.indices.put_settings(
                index="_all",
                body={
                    "index": {
                        "refresh_interval": "1s",
                        "number_of_replicas": 1
                    }
                }
            )
            
            # Reset indexing buffer
            await self._client.cluster.put_settings(
                body={
                    "transient": {
                        "indices.memory.index_buffer_size": None,
                        "indices.memory.min_index_buffer_size": None,
                        "indices.memory.max_index_buffer_size": None
                    }
                }
            )
            
            logger.info("Restored normal cluster settings")
        except Exception as e:
            logger.warning(f"Failed to restore settings: {e}")
    
    async def parallel_bulk_index(
        self,
        actions: List[Dict[str, Any]],
        chunk_size: int = 500,
        max_concurrent_chunks: int = 4
    ) -> Dict[str, Any]:
        """Perform parallel bulk indexing for maximum throughput"""
        if not actions:
            return {"indexed": 0, "errors": []}
        
        # Split actions into chunks
        chunks = [
            actions[i:i + chunk_size]
            for i in range(0, len(actions), chunk_size)
        ]
        
        # Process chunks in parallel with concurrency limit
        semaphore = asyncio.Semaphore(max_concurrent_chunks)
        
        async def process_chunk(chunk):
            async with semaphore:
                return await self._bulk_index_chunk(chunk)
        
        # Execute all chunks
        results = await asyncio.gather(
            *[process_chunk(chunk) for chunk in chunks],
            return_exceptions=True
        )
        
        # Aggregate results
        total_indexed = 0
        total_errors = []
        
        for result in results:
            if isinstance(result, Exception):
                total_errors.append(str(result))
            else:
                total_indexed += result["indexed"]
                total_errors.extend(result["errors"])
        
        return {
            "indexed": total_indexed,
            "errors": total_errors,
            "chunks_processed": len(chunks)
        }
    
    async def _bulk_index_chunk(
        self,
        actions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Index a single chunk of documents"""
        indexed = 0
        errors = []
        
        try:
            async for ok, result in async_bulk(
                self._client,
                actions,
                chunk_size=100,
                yield_ok=True,
                raise_on_error=False
            ):
                if ok:
                    indexed += 1
                else:
                    errors.append(result)
        except Exception as e:
            logger.error(f"Bulk indexing error: {e}")
            errors.append(str(e))
        
        return {"indexed": indexed, "errors": errors}
    
    async def create_index_with_sharding(
        self,
        index_name: str,
        estimated_size_gb: float,
        estimated_doc_count: int
    ) -> bool:
        """Create index with optimal sharding based on size estimates"""
        # Calculate optimal shard count
        # Rule of thumb: 20-40GB per shard, max 50M docs per shard
        shard_by_size = max(1, int(estimated_size_gb / 30))
        shard_by_docs = max(1, int(estimated_doc_count / 30_000_000))
        optimal_shards = max(shard_by_size, shard_by_docs)
        
        # Limit shard count
        optimal_shards = min(optimal_shards, 20)
        
        settings = {
            "number_of_shards": optimal_shards,
            "number_of_replicas": 1,
            "refresh_interval": "5s",
            "codec": "best_compression",
            "merge": {
                "scheduler": {
                    "max_thread_count": 2
                }
            },
            "translog": {
                "durability": "async",
                "sync_interval": "30s"
            }
        }
        
        try:
            await self._client.indices.create(
                index=index_name,
                body={"settings": settings}
            )
            logger.info(
                f"Created index {index_name} with {optimal_shards} shards "
                f"(estimated size: {estimated_size_gb}GB, docs: {estimated_doc_count})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            return False
    
    async def get_indexing_stats(self) -> Dict[str, Any]:
        """Get cluster indexing statistics"""
        try:
            stats = await self._client.indices.stats(metric="indexing,store")
            
            total_indexed = 0
            total_size_bytes = 0
            index_stats = {}
            
            for index, data in stats["indices"].items():
                indexing = data.get("primaries", {}).get("indexing", {})
                store = data.get("primaries", {}).get("store", {})
                
                indexed = indexing.get("index_total", 0)
                size = store.get("size_in_bytes", 0)
                
                total_indexed += indexed
                total_size_bytes += size
                
                index_stats[index] = {
                    "documents": indexed,
                    "size_gb": size / (1024 ** 3),
                    "indexing_time_ms": indexing.get("index_time_in_millis", 0),
                    "average_doc_size_kb": (size / indexed / 1024) if indexed > 0 else 0
                }
            
            return {
                "total_documents": total_indexed,
                "total_size_gb": total_size_bytes / (1024 ** 3),
                "indices": index_stats
            }
        except Exception as e:
            logger.error(f"Failed to get indexing stats: {e}")
            return {}


# Global client instance
_opensearch_client: Optional[OptimizedAsyncOpenSearch] = None


async def get_opensearch_client(settings: Settings) -> OptimizedAsyncOpenSearch:
    """Get or create the global OpenSearch client"""
    global _opensearch_client
    
    if _opensearch_client is None:
        _opensearch_client = OptimizedAsyncOpenSearch(settings)
        await _opensearch_client.initialize()
    
    return _opensearch_client


async def close_opensearch_client():
    """Close the global OpenSearch client"""
    global _opensearch_client
    
    if _opensearch_client:
        await _opensearch_client.close()
        _opensearch_client = None
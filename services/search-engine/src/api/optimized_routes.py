"""
Optimized API routes for search indexing and monitoring
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field

from ..core.config import get_settings, Settings
from ..core.async_opensearch import get_opensearch_client, OptimizedAsyncOpenSearch
from ..core.optimized_indexer import OptimizedIndexer, IndexingStats
from ..core.query_optimizer import QueryOptimizer
from ..core.index_monitor import IndexMonitor
from ..models.search import SearchRequest, SearchResponse
import redis.asyncio as redis

router = APIRouter(prefix="/api/v1/optimize", tags=["optimization"])

# Global instances
_indexer: Optional[OptimizedIndexer] = None
_query_optimizer: Optional[QueryOptimizer] = None
_index_monitor: Optional[IndexMonitor] = None
_redis_client: Optional[redis.Redis] = None


async def get_indexer() -> OptimizedIndexer:
    """Get or create the optimized indexer"""
    global _indexer
    if _indexer is None:
        settings = get_settings()
        client = await get_opensearch_client(settings)
        _indexer = OptimizedIndexer(
            settings=settings,
            client=client.client,
            batch_size=500,
            max_queue_size=10000,
            parallel_bulk_processes=4
        )
        await _indexer.initialize()
    return _indexer


async def get_query_optimizer() -> QueryOptimizer:
    """Get or create the query optimizer"""
    global _query_optimizer, _redis_client
    
    if _query_optimizer is None:
        settings = get_settings()
        client = await get_opensearch_client(settings)
        
        # Initialize Redis for caching
        if settings.redis_url and _redis_client is None:
            _redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        
        _query_optimizer = QueryOptimizer(
            client=client.client,
            redis_client=_redis_client,
            cache_ttl=3600
        )
    
    return _query_optimizer


async def get_index_monitor() -> IndexMonitor:
    """Get or create the index monitor"""
    global _index_monitor
    
    if _index_monitor is None:
        settings = get_settings()
        client = await get_opensearch_client(settings)
        _index_monitor = IndexMonitor(client.client)
        await _index_monitor.start_monitoring()
    
    return _index_monitor


# Request/Response Models
class BulkIndexRequest(BaseModel):
    """Bulk indexing request"""
    documents: List[Dict[str, Any]] = Field(..., description="List of documents to index")
    index: str = Field(..., description="Target index name")
    immediate: bool = Field(False, description="Index immediately without queuing")


class BulkIndexResponse(BaseModel):
    """Bulk indexing response"""
    queued: int = Field(..., description="Number of documents queued")
    indexed: int = Field(..., description="Number of documents indexed immediately")
    queue_size: int = Field(..., description="Current queue size")


class OptimizeSettingsRequest(BaseModel):
    """Settings optimization request"""
    index_pattern: str = Field("*", description="Index pattern to optimize")
    mode: str = Field("balanced", description="Optimization mode: indexing, searching, balanced")


class ReindexRequest(BaseModel):
    """Reindex request with new settings"""
    source_index: str = Field(..., description="Source index name")
    target_index: str = Field(..., description="Target index name")
    settings: Dict[str, Any] = Field(..., description="New index settings")
    mappings: Optional[Dict[str, Any]] = Field(None, description="New index mappings")


class QueryAnalysisRequest(BaseModel):
    """Query analysis request"""
    index: str = Field(..., description="Index to search")
    query: Dict[str, Any] = Field(..., description="Search query to analyze")


# Indexing Endpoints
@router.post("/bulk", response_model=BulkIndexResponse)
async def bulk_index_optimized(
    request: BulkIndexRequest,
    background_tasks: BackgroundTasks,
    indexer: OptimizedIndexer = Depends(get_indexer)
):
    """Bulk index documents with optimization"""
    try:
        # Prepare documents for indexing
        docs = [
            (request.index, doc.get("id", str(i)), doc)
            for i, doc in enumerate(request.documents)
        ]
        
        if request.immediate:
            # Index immediately
            await indexer.index_documents(docs, immediate=True)
            return BulkIndexResponse(
                queued=0,
                indexed=len(docs),
                queue_size=len(indexer.queue)
            )
        else:
            # Queue for background processing
            await indexer.index_documents(docs, immediate=False)
            return BulkIndexResponse(
                queued=len(docs),
                indexed=0,
                queue_size=len(indexer.queue)
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indexing/stats")
async def get_indexing_stats(indexer: OptimizedIndexer = Depends(get_indexer)):
    """Get current indexing statistics"""
    return indexer.get_stats()


@router.post("/indexing/flush")
async def flush_indexing_queue(indexer: OptimizedIndexer = Depends(get_indexer)):
    """Flush the indexing queue immediately"""
    try:
        await indexer._flush_queue()
        return {"status": "flushed", "message": "Indexing queue flushed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Query Optimization Endpoints
@router.post("/query/optimize")
async def optimize_query(
    request: QueryAnalysisRequest,
    optimizer: QueryOptimizer = Depends(get_query_optimizer)
):
    """Optimize a search query"""
    try:
        # Optimize the query
        optimized = await optimizer.optimize_query(request.query)
        
        # Create profile
        profile = await optimizer.create_query_profile(request.index, request.query)
        
        return {
            "original_query": request.query,
            "optimized_query": optimized,
            "profile": profile
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/execute")
async def execute_optimized_query(
    request: QueryAnalysisRequest,
    use_cache: bool = Query(True, description="Use query cache"),
    optimizer: QueryOptimizer = Depends(get_query_optimizer)
):
    """Execute an optimized query with caching"""
    try:
        # Optimize query
        optimized = await optimizer.optimize_query(request.query)
        
        # Execute with timing
        start_time = time.time()
        
        if use_cache:
            result = await optimizer.execute_with_cache(request.index, optimized)
        else:
            client = await get_opensearch_client(get_settings())
            result = await client.client.search(index=request.index, body=optimized)
        
        execution_time = (time.time() - start_time) * 1000
        
        return {
            "took_ms": execution_time,
            "hits": result.get("hits", {}),
            "aggregations": result.get("aggregations", {}),
            "optimized": True,
            "cached": use_cache
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query/slow")
async def get_slow_queries(
    threshold_ms: float = Query(1000, description="Slow query threshold in milliseconds"),
    optimizer: QueryOptimizer = Depends(get_query_optimizer)
):
    """Get analysis of slow queries"""
    try:
        slow_queries = await optimizer.analyze_slow_queries(threshold_ms)
        return {
            "threshold_ms": threshold_ms,
            "slow_queries": slow_queries,
            "count": len(slow_queries)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Index Monitoring Endpoints
@router.get("/indices/health")
async def get_indices_health(
    monitor: IndexMonitor = Depends(get_index_monitor)
):
    """Get health status of all indices"""
    try:
        indices_health = await monitor.check_all_indices()
        
        # Convert to serializable format
        health_data = {}
        for index_name, health in indices_health.items():
            health_data[index_name] = {
                "status": health.status,
                "document_count": health.document_count,
                "size_gb": health.size_gb,
                "shard_count": health.shard_count,
                "issues": health.issues,
                "recommendations": health.recommendations,
                "metrics": {
                    "deleted_docs_ratio": health.deleted_docs_ratio,
                    "segment_count": health.segment_count,
                    "indexing_rate": health.indexing_rate,
                    "search_rate": health.search_rate
                }
            }
        
        return health_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indices/{index_name}/health")
async def get_index_health(
    index_name: str,
    monitor: IndexMonitor = Depends(get_index_monitor)
):
    """Get detailed health analysis for a specific index"""
    try:
        health = await monitor.analyze_index_health(index_name)
        
        return {
            "index": health.index_name,
            "status": health.status,
            "document_count": health.document_count,
            "size_gb": health.size_gb,
            "shards": {
                "count": health.shard_count,
                "replicas": health.replica_count,
                "average_size_gb": health.size_gb / health.shard_count if health.shard_count > 0 else 0
            },
            "performance": {
                "indexing_rate": health.indexing_rate,
                "search_rate": health.search_rate,
                "refresh_time_ms": health.refresh_time_ms
            },
            "segments": {
                "count": health.segment_count,
                "deleted_docs_ratio": health.deleted_docs_ratio
            },
            "issues": health.issues,
            "recommendations": health.recommendations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/indices/{index_name}/optimize")
async def optimize_index(
    index_name: str,
    background_tasks: BackgroundTasks,
    monitor: IndexMonitor = Depends(get_index_monitor)
):
    """Manually trigger index optimization"""
    try:
        # Get current health
        health = await monitor.analyze_index_health(index_name)
        
        # Schedule optimization in background
        background_tasks.add_task(
            monitor.auto_optimize_index,
            index_name,
            health
        )
        
        return {
            "status": "optimization_scheduled",
            "index": index_name,
            "current_issues": health.issues,
            "optimizations": health.recommendations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/indices/{index_name}/force-merge")
async def force_merge_index(
    index_name: str,
    max_segments: int = Query(1, description="Maximum number of segments"),
    only_expunge_deletes: bool = Query(False, description="Only expunge deleted documents"),
    background_tasks: BackgroundTasks,
    monitor: IndexMonitor = Depends(get_index_monitor)
):
    """Force merge an index to optimize segments"""
    try:
        # Schedule force merge in background
        background_tasks.add_task(
            monitor.force_merge_index,
            index_name,
            max_segments,
            only_expunge_deletes
        )
        
        return {
            "status": "force_merge_scheduled",
            "index": index_name,
            "max_segments": max_segments,
            "only_expunge_deletes": only_expunge_deletes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cluster/health")
async def get_cluster_health(monitor: IndexMonitor = Depends(get_index_monitor)):
    """Get overall cluster health summary"""
    try:
        return await monitor.get_cluster_health_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Settings Optimization Endpoints
@router.post("/settings/optimize")
async def optimize_settings(
    request: OptimizeSettingsRequest,
    client: OptimizedAsyncOpenSearch = Depends(get_opensearch_client)
):
    """Optimize cluster settings for specific workload"""
    try:
        if request.mode == "indexing":
            await client.optimize_for_indexing()
            message = "Optimized for high-volume indexing"
        elif request.mode == "searching":
            await client.restore_normal_settings()
            message = "Optimized for search performance"
        else:  # balanced
            await client.restore_normal_settings()
            message = "Using balanced settings"
        
        return {
            "status": "success",
            "mode": request.mode,
            "message": message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/indices/create-optimized")
async def create_optimized_index(
    index_name: str,
    estimated_size_gb: float = Query(..., description="Estimated index size in GB"),
    estimated_doc_count: int = Query(..., description="Estimated document count"),
    client: OptimizedAsyncOpenSearch = Depends(get_opensearch_client)
):
    """Create an index with optimized settings based on size estimates"""
    try:
        success = await client.create_index_with_sharding(
            index_name,
            estimated_size_gb,
            estimated_doc_count
        )
        
        if success:
            return {
                "status": "created",
                "index": index_name,
                "message": f"Index created with optimal sharding for {estimated_size_gb}GB and {estimated_doc_count} documents"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create index")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reindex")
async def reindex_with_optimization(
    request: ReindexRequest,
    background_tasks: BackgroundTasks,
    indexer: OptimizedIndexer = Depends(get_indexer)
):
    """Reindex with optimized settings"""
    try:
        # Schedule reindex in background
        background_tasks.add_task(
            indexer.reindex_with_new_settings,
            request.source_index,
            request.target_index,
            request.settings,
            request.mappings
        )
        
        return {
            "status": "reindex_scheduled",
            "source": request.source_index,
            "target": request.target_index,
            "message": "Reindexing started in background"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Cleanup on shutdown
async def cleanup():
    """Cleanup resources on shutdown"""
    global _indexer, _query_optimizer, _index_monitor, _redis_client
    
    if _indexer:
        await _indexer.shutdown()
        _indexer = None
    
    if _index_monitor:
        await _index_monitor.stop_monitoring()
        _index_monitor = None
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
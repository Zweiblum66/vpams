"""
Index monitoring and maintenance for optimal search performance
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

from opensearchpy import AsyncOpenSearch

logger = logging.getLogger(__name__)


@dataclass
class IndexHealth:
    """Index health metrics"""
    index_name: str
    status: str  # green, yellow, red
    document_count: int
    size_gb: float
    shard_count: int
    replica_count: int
    segment_count: int
    deleted_docs_ratio: float
    refresh_time_ms: float
    indexing_rate: float  # docs per second
    search_rate: float  # queries per second
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class IndexMonitor:
    """Monitor and optimize index health and performance"""
    
    def __init__(self, client: AsyncOpenSearch):
        self.client = client
        self._monitoring = False
        self._check_interval = 300  # 5 minutes
        
    async def start_monitoring(self):
        """Start background monitoring"""
        self._monitoring = True
        asyncio.create_task(self._monitor_loop())
        logger.info("Started index monitoring")
        
    async def stop_monitoring(self):
        """Stop background monitoring"""
        self._monitoring = False
        logger.info("Stopped index monitoring")
        
    async def _monitor_loop(self):
        """Background monitoring loop"""
        while self._monitoring:
            try:
                await self.check_all_indices()
                await asyncio.sleep(self._check_interval)
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(60)  # Wait before retry
    
    async def check_all_indices(self) -> Dict[str, IndexHealth]:
        """Check health of all indices"""
        indices_health = {}
        
        try:
            # Get all indices
            indices = await self.client.cat.indices(format="json")
            
            for index_info in indices:
                index_name = index_info["index"]
                if index_name.startswith("."):  # Skip system indices
                    continue
                
                health = await self.analyze_index_health(index_name)
                indices_health[index_name] = health
                
                # Log any issues
                if health.issues:
                    logger.warning(f"Index {index_name} has issues: {health.issues}")
                
                # Perform automatic optimizations
                if health.status == "red" or len(health.issues) > 3:
                    await self.auto_optimize_index(index_name, health)
        
        except Exception as e:
            logger.error(f"Failed to check indices: {e}")
        
        return indices_health
    
    async def analyze_index_health(self, index_name: str) -> IndexHealth:
        """Analyze health of a specific index"""
        try:
            # Get index stats
            stats = await self.client.indices.stats(index=index_name)
            index_stats = stats["indices"][index_name]
            
            # Get index settings
            settings = await self.client.indices.get_settings(index=index_name)
            index_settings = settings[index_name]["settings"]["index"]
            
            # Get cluster health for this index
            health = await self.client.cluster.health(index=index_name)
            
            # Calculate metrics
            primaries = index_stats["primaries"]
            total = index_stats["total"]
            
            doc_count = primaries["docs"]["count"]
            deleted_count = primaries["docs"]["deleted"]
            size_bytes = primaries["store"]["size_in_bytes"]
            
            # Get segment info
            segments = await self.client.indices.segments(index=index_name)
            segment_count = sum(
                len(shard["segments"])
                for shard in segments["indices"][index_name]["shards"].values()
                for shard_info in shard
            )
            
            # Calculate rates
            indexing_total = primaries["indexing"]["index_total"]
            indexing_time = primaries["indexing"]["index_time_in_millis"] / 1000.0
            indexing_rate = indexing_total / indexing_time if indexing_time > 0 else 0
            
            search_total = total["search"]["query_total"]
            search_time = total["search"]["query_time_in_millis"] / 1000.0
            search_rate = search_total / search_time if search_time > 0 else 0
            
            # Create health object
            health_obj = IndexHealth(
                index_name=index_name,
                status=health["status"],
                document_count=doc_count,
                size_gb=size_bytes / (1024**3),
                shard_count=int(index_settings.get("number_of_shards", 1)),
                replica_count=int(index_settings.get("number_of_replicas", 0)),
                segment_count=segment_count,
                deleted_docs_ratio=deleted_count / (doc_count + deleted_count) if (doc_count + deleted_count) > 0 else 0,
                refresh_time_ms=primaries["refresh"]["total_time_in_millis"] / primaries["refresh"]["total"] if primaries["refresh"]["total"] > 0 else 0,
                indexing_rate=indexing_rate,
                search_rate=search_rate
            )
            
            # Analyze issues
            self._analyze_issues(health_obj)
            
            # Generate recommendations
            self._generate_recommendations(health_obj)
            
            return health_obj
            
        except Exception as e:
            logger.error(f"Failed to analyze index {index_name}: {e}")
            return IndexHealth(
                index_name=index_name,
                status="unknown",
                document_count=0,
                size_gb=0,
                shard_count=0,
                replica_count=0,
                segment_count=0,
                deleted_docs_ratio=0,
                refresh_time_ms=0,
                indexing_rate=0,
                search_rate=0,
                issues=[f"Failed to analyze: {str(e)}"]
            )
    
    def _analyze_issues(self, health: IndexHealth):
        """Identify issues with index health"""
        # Check index status
        if health.status == "red":
            health.issues.append("Index is in RED status - some shards are not allocated")
        elif health.status == "yellow":
            health.issues.append("Index is in YELLOW status - replicas are not allocated")
        
        # Check shard size
        if health.document_count > 0:
            avg_shard_size = health.size_gb / health.shard_count
            if avg_shard_size > 50:
                health.issues.append(f"Shards too large ({avg_shard_size:.1f}GB average)")
            elif avg_shard_size < 1 and health.shard_count > 1:
                health.issues.append(f"Shards too small ({avg_shard_size:.1f}GB average)")
        
        # Check deleted documents ratio
        if health.deleted_docs_ratio > 0.3:
            health.issues.append(f"High ratio of deleted documents ({health.deleted_docs_ratio:.1%})")
        
        # Check segment count
        segments_per_shard = health.segment_count / health.shard_count
        if segments_per_shard > 50:
            health.issues.append(f"Too many segments ({segments_per_shard:.0f} per shard)")
        
        # Check refresh time
        if health.refresh_time_ms > 1000:
            health.issues.append(f"Slow refresh time ({health.refresh_time_ms:.0f}ms)")
        
        # Check replica count
        if health.replica_count == 0 and health.status == "green":
            health.issues.append("No replicas configured - no redundancy")
    
    def _generate_recommendations(self, health: IndexHealth):
        """Generate optimization recommendations"""
        # Shard recommendations
        if health.document_count > 0:
            ideal_shard_count = max(1, int(health.size_gb / 30))
            if abs(ideal_shard_count - health.shard_count) > 2:
                health.recommendations.append(
                    f"Consider reindexing with {ideal_shard_count} shards "
                    f"(currently {health.shard_count})"
                )
        
        # Deleted documents
        if health.deleted_docs_ratio > 0.3:
            health.recommendations.append(
                "Force merge to reclaim space from deleted documents"
            )
        
        # Segment count
        if health.segment_count > health.shard_count * 50:
            health.recommendations.append(
                "Force merge to reduce segment count"
            )
        
        # Replica recommendations
        if health.replica_count == 0:
            health.recommendations.append(
                "Add at least 1 replica for redundancy"
            )
        elif health.search_rate > 100 and health.replica_count < 2:
            health.recommendations.append(
                "Add more replicas to handle search load"
            )
        
        # Performance recommendations
        if health.indexing_rate > 1000:
            health.recommendations.append(
                "High indexing rate - consider increasing refresh interval"
            )
        
        if health.refresh_time_ms > 1000:
            health.recommendations.append(
                "Slow refresh - consider increasing refresh interval or adding resources"
            )
    
    async def auto_optimize_index(self, index_name: str, health: IndexHealth):
        """Automatically optimize index based on health analysis"""
        logger.info(f"Auto-optimizing index {index_name}")
        
        try:
            # Force merge if too many deleted docs
            if health.deleted_docs_ratio > 0.3:
                await self.force_merge_index(
                    index_name,
                    max_num_segments=max(1, health.shard_count),
                    only_expunge_deletes=True
                )
            
            # Adjust refresh interval based on indexing rate
            if health.indexing_rate > 1000:
                await self.client.indices.put_settings(
                    index=index_name,
                    body={"index": {"refresh_interval": "30s"}}
                )
            elif health.indexing_rate < 10:
                await self.client.indices.put_settings(
                    index=index_name,
                    body={"index": {"refresh_interval": "1s"}}
                )
            
            # Add replicas if missing
            if health.replica_count == 0 and health.status == "green":
                await self.client.indices.put_settings(
                    index=index_name,
                    body={"index": {"number_of_replicas": 1}}
                )
                
        except Exception as e:
            logger.error(f"Failed to auto-optimize {index_name}: {e}")
    
    async def force_merge_index(
        self,
        index_name: str,
        max_num_segments: int = 1,
        only_expunge_deletes: bool = False
    ):
        """Force merge index to optimize segments"""
        try:
            logger.info(f"Force merging index {index_name}")
            
            # Disable refresh during merge
            await self.client.indices.put_settings(
                index=index_name,
                body={"index": {"refresh_interval": "-1"}}
            )
            
            # Perform force merge
            await self.client.indices.forcemerge(
                index=index_name,
                max_num_segments=max_num_segments,
                only_expunge_deletes=only_expunge_deletes,
                flush=True
            )
            
            # Re-enable refresh
            await self.client.indices.put_settings(
                index=index_name,
                body={"index": {"refresh_interval": "1s"}}
            )
            
            logger.info(f"Completed force merge for {index_name}")
            
        except Exception as e:
            logger.error(f"Force merge failed for {index_name}: {e}")
            # Try to re-enable refresh even if merge failed
            try:
                await self.client.indices.put_settings(
                    index=index_name,
                    body={"index": {"refresh_interval": "1s"}}
                )
            except:
                pass
    
    async def optimize_old_indices(self, days_old: int = 30):
        """Optimize indices older than specified days"""
        try:
            indices = await self.client.cat.indices(format="json")
            current_time = datetime.utcnow()
            
            for index_info in indices:
                index_name = index_info["index"]
                if index_name.startswith("."):
                    continue
                
                # Parse creation date from index name if it contains date
                # Assumes format like "logs-2024-01-15"
                try:
                    date_parts = index_name.split("-")[-3:]
                    if len(date_parts) == 3 and all(p.isdigit() for p in date_parts):
                        index_date = datetime(
                            int(date_parts[0]),
                            int(date_parts[1]),
                            int(date_parts[2])
                        )
                        
                        if (current_time - index_date).days > days_old:
                            # Optimize old index
                            await self._optimize_old_index(index_name)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Failed to optimize old indices: {e}")
    
    async def _optimize_old_index(self, index_name: str):
        """Optimize a single old index"""
        try:
            logger.info(f"Optimizing old index: {index_name}")
            
            # Set to read-only
            await self.client.indices.put_settings(
                index=index_name,
                body={"index": {"blocks": {"write": True}}}
            )
            
            # Force merge to single segment
            await self.force_merge_index(index_name, max_num_segments=1)
            
            # Shrink shards if overshareded
            stats = await self.client.indices.stats(index=index_name)
            shard_count = len(stats["indices"][index_name]["shards"])
            size_gb = stats["indices"][index_name]["primaries"]["store"]["size_in_bytes"] / (1024**3)
            
            if shard_count > 1 and size_gb / shard_count < 20:
                # Shrink to fewer shards
                new_shard_count = max(1, int(size_gb / 40))
                await self._shrink_index(index_name, new_shard_count)
            
        except Exception as e:
            logger.error(f"Failed to optimize old index {index_name}: {e}")
    
    async def _shrink_index(self, index_name: str, target_shards: int):
        """Shrink index to fewer shards"""
        try:
            shrunk_name = f"{index_name}-shrunk"
            
            # Ensure all shards are on same node
            await self.client.indices.put_settings(
                index=index_name,
                body={
                    "index": {
                        "routing": {
                            "allocation": {
                                "require": {"_name": "*"}
                            }
                        }
                    }
                }
            )
            
            # Wait for relocation
            await self.client.cluster.health(
                index=index_name,
                wait_for_no_relocating_shards=True
            )
            
            # Shrink index
            await self.client.indices.shrink(
                index=index_name,
                target=shrunk_name,
                body={
                    "settings": {
                        "index": {
                            "number_of_shards": target_shards,
                            "number_of_replicas": 0
                        }
                    }
                }
            )
            
            # Wait for shrink to complete
            await self.client.cluster.health(
                index=shrunk_name,
                wait_for_status="green"
            )
            
            # Swap aliases
            await self.client.indices.update_aliases(
                body={
                    "actions": [
                        {"remove": {"index": index_name, "alias": "*"}},
                        {"add": {"index": shrunk_name, "alias": index_name}},
                        {"remove_index": {"index": index_name}}
                    ]
                }
            )
            
            logger.info(f"Successfully shrunk {index_name} to {target_shards} shards")
            
        except Exception as e:
            logger.error(f"Failed to shrink index {index_name}: {e}")
    
    async def get_cluster_health_summary(self) -> Dict[str, Any]:
        """Get overall cluster health summary"""
        try:
            # Get cluster health
            health = await self.client.cluster.health()
            
            # Get cluster stats
            stats = await self.client.cluster.stats()
            
            # Get nodes info
            nodes = await self.client.nodes.info()
            
            return {
                "status": health["status"],
                "node_count": health["number_of_nodes"],
                "data_node_count": health["number_of_data_nodes"],
                "active_shards": health["active_shards"],
                "relocating_shards": health["relocating_shards"],
                "initializing_shards": health["initializing_shards"],
                "unassigned_shards": health["unassigned_shards"],
                "indices": {
                    "count": stats["indices"]["count"],
                    "total_size_gb": stats["indices"]["store"]["size_in_bytes"] / (1024**3),
                    "total_docs": stats["indices"]["docs"]["count"]
                },
                "nodes": {
                    "jvm_heap_used_percent": stats["nodes"]["jvm"]["mem"]["heap_used_percent"],
                    "total_memory_gb": sum(
                        node["os"]["mem"]["total_in_bytes"] / (1024**3)
                        for node in nodes["nodes"].values()
                    ),
                    "cpu_count": sum(
                        node["os"]["cpu"]["count"]
                        for node in nodes["nodes"].values()
                    )
                }
            }
        except Exception as e:
            logger.error(f"Failed to get cluster health: {e}")
            return {"error": str(e)}
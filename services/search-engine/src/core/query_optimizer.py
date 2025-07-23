"""
Query optimization utilities for improved search performance
"""

import hashlib
import json
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio

from opensearchpy import AsyncOpenSearch
import redis.asyncio as redis

from .config import Settings

logger = logging.getLogger(__name__)


@dataclass
class QueryStats:
    """Statistics for query performance tracking"""
    query_hash: str
    execution_count: int = 0
    total_time_ms: float = 0
    average_time_ms: float = 0
    hit_count: int = 0
    last_execution: Optional[datetime] = None
    
    def add_execution(self, time_ms: float, hits: int):
        self.execution_count += 1
        self.total_time_ms += time_ms
        self.average_time_ms = self.total_time_ms / self.execution_count
        self.hit_count = hits
        self.last_execution = datetime.utcnow()


class QueryOptimizer:
    """Optimize search queries for better performance"""
    
    def __init__(
        self,
        client: AsyncOpenSearch,
        redis_client: Optional[redis.Redis] = None,
        cache_ttl: int = 3600
    ):
        self.client = client
        self.redis_client = redis_client
        self.cache_ttl = cache_ttl
        self.query_stats: Dict[str, QueryStats] = {}
        
        # Query rewriting rules
        self.rewrite_rules = {
            "wildcard_optimization": self._optimize_wildcard_queries,
            "range_optimization": self._optimize_range_queries,
            "bool_optimization": self._optimize_bool_queries,
            "aggregation_optimization": self._optimize_aggregations
        }
        
    def _hash_query(self, query: Dict[str, Any]) -> str:
        """Generate a hash for query caching"""
        query_str = json.dumps(query, sort_keys=True)
        return hashlib.md5(query_str.encode()).hexdigest()
    
    async def optimize_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Apply query optimizations"""
        optimized = query.copy()
        
        # Apply rewrite rules
        for rule_name, rule_func in self.rewrite_rules.items():
            try:
                optimized = rule_func(optimized)
            except Exception as e:
                logger.warning(f"Failed to apply {rule_name}: {e}")
        
        # Add query hints
        optimized = self._add_query_hints(optimized)
        
        return optimized
    
    def _optimize_wildcard_queries(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize wildcard queries to use more efficient alternatives"""
        if "query" not in query:
            return query
        
        def optimize_wildcard(q: Dict[str, Any]) -> Dict[str, Any]:
            if isinstance(q, dict):
                if "wildcard" in q:
                    for field, pattern in q["wildcard"].items():
                        # Convert leading wildcard to prefix query if possible
                        if isinstance(pattern, str) and pattern.startswith("*") and not "*" in pattern[1:]:
                            # *abc -> reverse field search
                            return {
                                "prefix": {
                                    f"{field}.reverse": pattern[1:][::-1]
                                }
                            }
                        # Convert to match_phrase_prefix for better performance
                        elif isinstance(pattern, str) and pattern.endswith("*") and not "*" in pattern[:-1]:
                            return {
                                "match_phrase_prefix": {
                                    field: pattern[:-1]
                                }
                            }
                
                # Recursively optimize nested queries
                for key, value in q.items():
                    if isinstance(value, dict):
                        q[key] = optimize_wildcard(value)
                    elif isinstance(value, list):
                        q[key] = [optimize_wildcard(v) if isinstance(v, dict) else v for v in value]
            
            return q
        
        query["query"] = optimize_wildcard(query["query"])
        return query
    
    def _optimize_range_queries(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize range queries with better bounds"""
        if "query" not in query:
            return query
        
        def optimize_range(q: Dict[str, Any]) -> Dict[str, Any]:
            if isinstance(q, dict):
                if "range" in q:
                    for field, conditions in q["range"].items():
                        # Add format hints for date fields
                        if any(date_term in field.lower() for date_term in ["date", "time", "created", "updated"]):
                            if "format" not in conditions:
                                conditions["format"] = "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis"
                        
                        # Use filter context for better caching
                        return {
                            "bool": {
                                "filter": [{
                                    "range": {field: conditions}
                                }]
                            }
                        }
                
                # Recursively optimize
                for key, value in q.items():
                    if isinstance(value, dict):
                        q[key] = optimize_range(value)
                    elif isinstance(value, list):
                        q[key] = [optimize_range(v) if isinstance(v, dict) else v for v in value]
            
            return q
        
        query["query"] = optimize_range(query["query"])
        return query
    
    def _optimize_bool_queries(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize boolean queries for better performance"""
        if "query" not in query:
            return query
        
        def optimize_bool(q: Dict[str, Any]) -> Dict[str, Any]:
            if isinstance(q, dict) and "bool" in q:
                bool_query = q["bool"]
                
                # Move queries from must to filter when scoring not needed
                if "must" in bool_query:
                    non_scoring = []
                    scoring = []
                    
                    for clause in bool_query["must"]:
                        # Term queries don't need scoring
                        if any(k in clause for k in ["term", "terms", "range", "exists"]):
                            non_scoring.append(clause)
                        else:
                            scoring.append(clause)
                    
                    if non_scoring:
                        bool_query["must"] = scoring
                        if "filter" not in bool_query:
                            bool_query["filter"] = []
                        bool_query["filter"].extend(non_scoring)
                    
                    # Remove empty must
                    if not bool_query["must"]:
                        del bool_query["must"]
                
                # Optimize multiple term queries on same field
                if "filter" in bool_query:
                    term_queries = {}
                    other_queries = []
                    
                    for clause in bool_query["filter"]:
                        if "term" in clause:
                            field = list(clause["term"].keys())[0]
                            value = clause["term"][field]
                            if field not in term_queries:
                                term_queries[field] = []
                            term_queries[field].append(value)
                        else:
                            other_queries.append(clause)
                    
                    # Convert multiple terms to terms query
                    new_filter = other_queries
                    for field, values in term_queries.items():
                        if len(values) > 1:
                            new_filter.append({"terms": {field: values}})
                        else:
                            new_filter.append({"term": {field: values[0]}})
                    
                    bool_query["filter"] = new_filter
            
            # Recursively optimize
            if isinstance(q, dict):
                for key, value in q.items():
                    if isinstance(value, dict):
                        q[key] = optimize_bool(value)
                    elif isinstance(value, list):
                        q[key] = [optimize_bool(v) if isinstance(v, dict) else v for v in value]
            
            return q
        
        query["query"] = optimize_bool(query["query"])
        return query
    
    def _optimize_aggregations(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize aggregations for better performance"""
        if "aggs" not in query and "aggregations" not in query:
            return query
        
        aggs_key = "aggs" if "aggs" in query else "aggregations"
        aggs = query[aggs_key]
        
        def optimize_agg(agg: Dict[str, Any]) -> Dict[str, Any]:
            for agg_name, agg_def in agg.items():
                if isinstance(agg_def, dict):
                    # Add execution hints for terms aggregations
                    if "terms" in agg_def:
                        terms_agg = agg_def["terms"]
                        
                        # Use execution hint for better performance
                        if "execution_hint" not in terms_agg:
                            if terms_agg.get("size", 10) > 100:
                                terms_agg["execution_hint"] = "map"
                            else:
                                terms_agg["execution_hint"] = "global_ordinals"
                        
                        # Add shard_size for better accuracy
                        if "shard_size" not in terms_agg and "size" in terms_agg:
                            terms_agg["shard_size"] = terms_agg["size"] * 2
                    
                    # Optimize date histogram
                    elif "date_histogram" in agg_def:
                        date_hist = agg_def["date_histogram"]
                        
                        # Add min_doc_count to reduce bucket overhead
                        if "min_doc_count" not in date_hist:
                            date_hist["min_doc_count"] = 1
                        
                        # Use fixed_interval instead of calendar_interval when possible
                        if "calendar_interval" in date_hist:
                            interval = date_hist["calendar_interval"]
                            if interval in ["1m", "5m", "10m", "30m", "1h", "3h", "12h"]:
                                date_hist["fixed_interval"] = interval
                                del date_hist["calendar_interval"]
                    
                    # Recursively optimize sub-aggregations
                    if "aggs" in agg_def or "aggregations" in agg_def:
                        sub_aggs_key = "aggs" if "aggs" in agg_def else "aggregations"
                        agg_def[sub_aggs_key] = optimize_agg(agg_def[sub_aggs_key])
            
            return agg
        
        query[aggs_key] = optimize_agg(aggs)
        return query
    
    def _add_query_hints(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Add performance hints to query"""
        # Add preference for consistent results across searches
        if "_source" not in query:
            query["_source"] = True
        
        # Limit source fields if possible
        if isinstance(query.get("_source"), bool) and query["_source"]:
            # Don't fetch large fields by default
            query["_source"] = {
                "excludes": ["*.raw", "*.keyword", "*_vector", "content_binary"]
            }
        
        # Add search timeout
        if "timeout" not in query:
            query["timeout"] = "30s"
        
        # Enable request cache for aggregations
        if ("aggs" in query or "aggregations" in query) and "request_cache" not in query:
            query["request_cache"] = True
        
        return query
    
    async def execute_with_cache(
        self,
        index: str,
        query: Dict[str, Any],
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute query with caching"""
        if not cache_key:
            cache_key = f"search:{index}:{self._hash_query(query)}"
        
        # Check cache
        if self.redis_client:
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit for query: {cache_key}")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        
        # Execute query
        start_time = datetime.utcnow()
        result = await self.client.search(index=index, body=query)
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Update stats
        query_hash = self._hash_query(query)
        if query_hash not in self.query_stats:
            self.query_stats[query_hash] = QueryStats(query_hash)
        
        self.query_stats[query_hash].add_execution(
            execution_time,
            result.get("hits", {}).get("total", {}).get("value", 0)
        )
        
        # Cache result
        if self.redis_client and result.get("hits", {}).get("total", {}).get("value", 0) > 0:
            try:
                await self.redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(result)
                )
            except Exception as e:
                logger.warning(f"Cache write error: {e}")
        
        return result
    
    async def analyze_slow_queries(self, threshold_ms: float = 1000) -> List[Dict[str, Any]]:
        """Analyze slow queries for optimization opportunities"""
        slow_queries = []
        
        for query_hash, stats in self.query_stats.items():
            if stats.average_time_ms > threshold_ms:
                slow_queries.append({
                    "query_hash": query_hash,
                    "average_time_ms": stats.average_time_ms,
                    "execution_count": stats.execution_count,
                    "last_execution": stats.last_execution.isoformat() if stats.last_execution else None,
                    "recommendations": self._get_optimization_recommendations(stats)
                })
        
        return sorted(slow_queries, key=lambda x: x["average_time_ms"], reverse=True)
    
    def _get_optimization_recommendations(self, stats: QueryStats) -> List[str]:
        """Get optimization recommendations for slow queries"""
        recommendations = []
        
        if stats.average_time_ms > 5000:
            recommendations.append("Consider adding more specific filters to reduce search scope")
            recommendations.append("Check if the index needs more shards for parallelization")
        
        if stats.hit_count > 10000:
            recommendations.append("Large result set - consider pagination or aggregations")
            recommendations.append("Add filters to reduce the number of matching documents")
        
        if stats.execution_count > 100:
            recommendations.append("Frequently executed query - consider caching results")
            recommendations.append("Create a materialized view or summary index")
        
        return recommendations
    
    async def create_query_profile(
        self,
        index: str,
        query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a detailed query profile for analysis"""
        profile_query = query.copy()
        profile_query["profile"] = True
        
        result = await self.client.search(index=index, body=profile_query)
        
        profile = result.get("profile", {})
        shards = profile.get("shards", [])
        
        total_time = 0
        phase_times = {
            "query": 0,
            "fetch": 0,
            "highlight": 0,
            "aggregations": 0
        }
        
        for shard in shards:
            for search in shard.get("searches", []):
                query_time = search.get("query", [{}])[0].get("time_in_nanos", 0) / 1_000_000
                phase_times["query"] += query_time
                total_time += query_time
                
                fetch_time = search.get("fetch", {}).get("time_in_nanos", 0) / 1_000_000
                phase_times["fetch"] += fetch_time
                total_time += fetch_time
        
        return {
            "total_time_ms": total_time,
            "phase_breakdown": phase_times,
            "shard_count": len(shards),
            "query_complexity": self._calculate_query_complexity(query),
            "recommendations": self._get_profile_recommendations(phase_times, total_time)
        }
    
    def _calculate_query_complexity(self, query: Dict[str, Any]) -> int:
        """Calculate query complexity score"""
        complexity = 0
        
        def count_clauses(q: Any) -> int:
            if isinstance(q, dict):
                count = len(q)
                for value in q.values():
                    count += count_clauses(value)
                return count
            elif isinstance(q, list):
                return sum(count_clauses(item) for item in q)
            return 0
        
        complexity = count_clauses(query.get("query", {}))
        complexity += count_clauses(query.get("aggs", {})) * 2  # Aggregations are more expensive
        
        return complexity
    
    def _get_profile_recommendations(
        self,
        phase_times: Dict[str, float],
        total_time: float
    ) -> List[str]:
        """Get recommendations based on query profile"""
        recommendations = []
        
        # Check which phase is slowest
        slowest_phase = max(phase_times, key=phase_times.get)
        slowest_time = phase_times[slowest_phase]
        
        if slowest_phase == "query" and slowest_time > 0.7 * total_time:
            recommendations.append("Query phase is slowest - consider optimizing query structure")
            recommendations.append("Add more selective filters early in the query")
        
        elif slowest_phase == "fetch" and slowest_time > 0.5 * total_time:
            recommendations.append("Fetch phase is slowest - reduce _source fields")
            recommendations.append("Consider using stored fields for frequently accessed data")
        
        elif slowest_phase == "aggregations":
            recommendations.append("Aggregations are expensive - consider pre-computing common aggregations")
            recommendations.append("Use composite aggregations for large cardinality fields")
        
        if total_time > 1000:
            recommendations.append("Query is very slow - consider splitting into multiple simpler queries")
            recommendations.append("Review index mapping and add appropriate data types")
        
        return recommendations
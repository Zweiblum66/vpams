"""
MongoDB models for the Search Engine Service
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING, IndexModel
import structlog

logger = structlog.get_logger()


class SavedSearchModel:
    """MongoDB model for saved searches"""
    
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create indexes for the saved searches collection"""
        indexes = [
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("is_public", ASCENDING)]),
            IndexModel([("tags", ASCENDING)]),
            IndexModel([("name", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("usage_count", DESCENDING)]),
            IndexModel([("last_used_at", DESCENDING)]),
            IndexModel([
                ("user_id", ASCENDING),
                ("name", ASCENDING)
            ], unique=True)  # Unique constraint on user_id + name
        ]
        
        try:
            self.collection.create_indexes(indexes)
            logger.info("saved_search_indexes_created")
        except Exception as e:
            logger.error("failed_to_create_indexes", error=str(e))
    
    async def create(self, saved_search: Dict[str, Any]) -> str:
        """Create a new saved search"""
        try:
            saved_search["created_at"] = datetime.utcnow()
            saved_search["updated_at"] = datetime.utcnow()
            saved_search["usage_count"] = 0
            saved_search["last_used_at"] = None
            
            result = await self.collection.insert_one(saved_search)
            return str(result.inserted_id)
        except Exception as e:
            logger.error("failed_to_create_saved_search", error=str(e))
            raise
    
    async def get_by_id(self, search_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a saved search by ID"""
        try:
            from bson import ObjectId
            
            query = {"_id": ObjectId(search_id)}
            if user_id:
                # User can access their own searches or public searches
                query = {
                    "_id": ObjectId(search_id),
                    "$or": [
                        {"user_id": user_id},
                        {"is_public": True}
                    ]
                }
            
            search = await self.collection.find_one(query)
            if search:
                search["id"] = str(search.pop("_id"))
            return search
        except Exception as e:
            logger.error("failed_to_get_saved_search", error=str(e), search_id=search_id)
            return None
    
    async def get_user_searches(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        include_public: bool = True
    ) -> tuple[List[Dict[str, Any]], int]:
        """Get saved searches for a user"""
        try:
            # Build query
            if include_public:
                query = {
                    "$or": [
                        {"user_id": user_id},
                        {"is_public": True}
                    ]
                }
            else:
                query = {"user_id": user_id}
            
            # Get total count
            total = await self.collection.count_documents(query)
            
            # Get paginated results
            cursor = self.collection.find(query).sort("created_at", DESCENDING).skip(skip).limit(limit)
            searches = []
            async for search in cursor:
                search["id"] = str(search.pop("_id"))
                searches.append(search)
            
            return searches, total
        except Exception as e:
            logger.error("failed_to_get_user_searches", error=str(e), user_id=user_id)
            return [], 0
    
    async def search_by_tags(self, tags: List[str], skip: int = 0, limit: int = 20) -> tuple[List[Dict[str, Any]], int]:
        """Search saved searches by tags"""
        try:
            query = {
                "is_public": True,
                "tags": {"$in": tags}
            }
            
            # Get total count
            total = await self.collection.count_documents(query)
            
            # Get paginated results
            cursor = self.collection.find(query).sort("usage_count", DESCENDING).skip(skip).limit(limit)
            searches = []
            async for search in cursor:
                search["id"] = str(search.pop("_id"))
                searches.append(search)
            
            return searches, total
        except Exception as e:
            logger.error("failed_to_search_by_tags", error=str(e), tags=tags)
            return [], 0
    
    async def get_popular_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular public searches"""
        try:
            cursor = self.collection.find(
                {"is_public": True}
            ).sort("usage_count", DESCENDING).limit(limit)
            
            searches = []
            async for search in cursor:
                search["id"] = str(search.pop("_id"))
                searches.append(search)
            
            return searches
        except Exception as e:
            logger.error("failed_to_get_popular_searches", error=str(e))
            return []
    
    async def update(self, search_id: str, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a saved search"""
        try:
            from bson import ObjectId
            
            update_data["updated_at"] = datetime.utcnow()
            
            result = await self.collection.update_one(
                {
                    "_id": ObjectId(search_id),
                    "user_id": user_id  # Only owner can update
                },
                {"$set": update_data}
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error("failed_to_update_saved_search", error=str(e), search_id=search_id)
            return False
    
    async def increment_usage(self, search_id: str) -> bool:
        """Increment usage count and update last used timestamp"""
        try:
            from bson import ObjectId
            
            result = await self.collection.update_one(
                {"_id": ObjectId(search_id)},
                {
                    "$inc": {"usage_count": 1},
                    "$set": {"last_used_at": datetime.utcnow()}
                }
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error("failed_to_increment_usage", error=str(e), search_id=search_id)
            return False
    
    async def delete(self, search_id: str, user_id: str) -> bool:
        """Delete a saved search"""
        try:
            from bson import ObjectId
            
            result = await self.collection.delete_one({
                "_id": ObjectId(search_id),
                "user_id": user_id  # Only owner can delete
            })
            
            return result.deleted_count > 0
        except Exception as e:
            logger.error("failed_to_delete_saved_search", error=str(e), search_id=search_id)
            return False
    
    async def check_name_exists(self, user_id: str, name: str, exclude_id: Optional[str] = None) -> bool:
        """Check if a search name already exists for a user"""
        try:
            from bson import ObjectId
            
            query = {
                "user_id": user_id,
                "name": name
            }
            
            if exclude_id:
                query["_id"] = {"$ne": ObjectId(exclude_id)}
            
            count = await self.collection.count_documents(query)
            return count > 0
        except Exception as e:
            logger.error("failed_to_check_name_exists", error=str(e))
            return False


class SearchHistoryModel:
    """MongoDB model for search history"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db.search_history
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create necessary indexes for search history collection"""
        # Index for user queries
        self.collection.create_index([("user_id", 1), ("timestamp", -1)])
        
        # Index for query text searches
        self.collection.create_index([("query", "text")])
        
        # Index for search type filtering
        self.collection.create_index([("search_type", 1)])
        
        # Index for timestamp-based queries
        self.collection.create_index([("timestamp", -1)])
        
        # Compound index for user stats
        self.collection.create_index([("user_id", 1), ("search_type", 1), ("timestamp", -1)])
    
    async def create(self, history_data: dict) -> str:
        """Create a new search history entry"""
        history_data["timestamp"] = datetime.utcnow()
        
        result = await self.collection.insert_one(history_data)
        return str(result.inserted_id)
    
    async def get_user_history(
        self, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 20,
        search_type: Optional[str] = None,
        query_filter: Optional[str] = None
    ) -> Tuple[List[dict], int]:
        """Get search history for a user"""
        filter_query = {"user_id": user_id}
        
        if search_type:
            filter_query["search_type"] = search_type
        
        if query_filter:
            filter_query["query"] = {"$regex": query_filter, "$options": "i"}
        
        # Get total count
        total = await self.collection.count_documents(filter_query)
        
        # Get paginated results
        cursor = self.collection.find(filter_query).sort("timestamp", -1).skip(skip).limit(limit)
        entries = []
        
        async for doc in cursor:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
            entries.append(doc)
        
        return entries, total
    
    async def get_user_stats(self, user_id: str, days: int = 30) -> dict:
        """Get search statistics for a user"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "timestamp": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_searches": {"$sum": 1},
                    "unique_queries": {"$addToSet": "$query"},
                    "avg_response_time": {"$avg": "$response_time_ms"},
                    "avg_results": {"$avg": "$results_count"},
                    "search_types": {"$push": "$search_type"}
                }
            }
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        if not result:
            return {
                "total_searches": 0,
                "unique_queries": 0,
                "avg_response_time_ms": 0,
                "avg_results_per_search": 0,
                "most_common_search_type": "basic"
            }
        
        stats = result[0]
        unique_queries_count = len(stats["unique_queries"])
        
        # Find most common search type
        search_types = stats["search_types"]
        most_common_type = max(set(search_types), key=search_types.count) if search_types else "basic"
        
        return {
            "total_searches": stats["total_searches"],
            "unique_queries": unique_queries_count,
            "avg_response_time_ms": stats["avg_response_time"] or 0,
            "avg_results_per_search": stats["avg_results"] or 0,
            "most_common_search_type": most_common_type
        }
    
    async def get_top_queries(self, user_id: str, limit: int = 10, days: int = 30) -> List[dict]:
        """Get top queries for a user"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "timestamp": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": "$query",
                    "count": {"$sum": 1},
                    "avg_results": {"$avg": "$results_count"},
                    "avg_response_time": {"$avg": "$response_time_ms"},
                    "last_used": {"$max": "$timestamp"}
                }
            },
            {
                "$sort": {"count": -1}
            },
            {
                "$limit": limit
            }
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(length=limit)
        
        top_queries = []
        for item in result:
            top_queries.append({
                "query": item["_id"],
                "count": item["count"],
                "avg_results": item["avg_results"],
                "avg_response_time_ms": item["avg_response_time"],
                "last_used": item["last_used"]
            })
        
        return top_queries
    
    async def get_search_volume_by_day(self, user_id: str, days: int = 30) -> List[dict]:
        """Get search volume by day for a user"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "timestamp": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$timestamp"},
                        "month": {"$month": "$timestamp"},
                        "day": {"$dayOfMonth": "$timestamp"}
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(length=days)
        
        volume_data = []
        for item in result:
            date_obj = datetime(
                item["_id"]["year"],
                item["_id"]["month"],
                item["_id"]["day"]
            )
            volume_data.append({
                "date": date_obj.strftime("%Y-%m-%d"),
                "count": item["count"]
            })
        
        return volume_data
    
    async def delete_user_history(self, user_id: str, older_than_days: int = 90) -> int:
        """Delete old search history entries for a user"""
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        result = await self.collection.delete_many({
            "user_id": user_id,
            "timestamp": {"$lt": cutoff_date}
        })
        
        return result.deleted_count
    
    async def clear_user_history(self, user_id: str) -> int:
        """Clear all search history for a user"""
        result = await self.collection.delete_many({"user_id": user_id})
        return result.deleted_count


class SearchAnalyticsModel:
    """MongoDB model for search analytics"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db.search_analytics
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create necessary indexes for search analytics collection"""
        # Index for timestamp-based queries
        self.collection.create_index([("timestamp", -1)])
        
        # Index for query analysis
        self.collection.create_index([("query", "text")])
        
        # Index for user-based analytics
        self.collection.create_index([("user_id", 1), ("timestamp", -1)])
        
        # Index for session-based analytics
        self.collection.create_index([("session_id", 1), ("timestamp", -1)])
        
        # Index for search type filtering
        self.collection.create_index([("search_type", 1)])
        
        # Index for performance analysis
        self.collection.create_index([("response_time_ms", 1)])
        
        # Index for result count analysis
        self.collection.create_index([("results_count", 1)])
        
        # Compound index for complex queries
        self.collection.create_index([
            ("timestamp", -1),
            ("search_type", 1),
            ("user_id", 1)
        ])
    
    async def create(self, analytics_data: dict) -> str:
        """Create a new search analytics entry"""
        analytics_data["timestamp"] = datetime.utcnow()
        
        result = await self.collection.insert_one(analytics_data)
        return str(result.inserted_id)
    
    async def get_aggregated_stats(
        self, 
        start_time: datetime, 
        end_time: datetime,
        filters: Optional[dict] = None
    ) -> dict:
        """Get aggregated statistics for a time range"""
        base_match = {
            "timestamp": {"$gte": start_time, "$lte": end_time}
        }
        
        if filters:
            base_match.update(filters)
        
        pipeline = [
            {"$match": base_match},
            {
                "$group": {
                    "_id": None,
                    "total_searches": {"$sum": 1},
                    "unique_queries": {"$addToSet": "$query"},
                    "unique_users": {"$addToSet": "$user_id"},
                    "unique_sessions": {"$addToSet": "$session_id"},
                    "avg_response_time": {"$avg": "$response_time_ms"},
                    "avg_results": {"$avg": "$results_count"},
                    "total_clicks": {"$sum": {"$size": {"$ifNull": ["$clicked_results", []]}}},
                    "zero_result_searches": {
                        "$sum": {"$cond": [{"$eq": ["$results_count", 0]}, 1, 0]}
                    },
                    "searches_with_clicks": {
                        "$sum": {
                            "$cond": [
                                {"$gt": [{"$size": {"$ifNull": ["$clicked_results", []]}}, 0]},
                                1,
                                0
                            ]
                        }
                    }
                }
            },
            {
                "$project": {
                    "total_searches": 1,
                    "unique_queries": {"$size": "$unique_queries"},
                    "unique_users": {"$size": "$unique_users"},
                    "unique_sessions": {"$size": "$unique_sessions"},
                    "avg_response_time_ms": {"$round": ["$avg_response_time", 2]},
                    "avg_results_per_search": {"$round": ["$avg_results", 2]},
                    "avg_clicks_per_search": {
                        "$round": [
                            {"$divide": ["$total_clicks", "$total_searches"]},
                            2
                        ]
                    },
                    "click_through_rate": {
                        "$round": [
                            {"$multiply": [
                                {"$divide": ["$searches_with_clicks", "$total_searches"]},
                                100
                            ]},
                            2
                        ]
                    },
                    "zero_result_rate": {
                        "$round": [
                            {"$multiply": [
                                {"$divide": ["$zero_result_searches", "$total_searches"]},
                                100
                            ]},
                            2
                        ]
                    }
                }
            }
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        
        if not result:
            return {
                "total_searches": 0,
                "unique_queries": 0,
                "unique_users": 0,
                "unique_sessions": 0,
                "avg_response_time_ms": 0,
                "avg_results_per_search": 0,
                "avg_clicks_per_search": 0,
                "click_through_rate": 0,
                "zero_result_rate": 0
            }
        
        return result[0]
    
    async def get_top_queries(
        self, 
        start_time: datetime, 
        end_time: datetime,
        limit: int = 10,
        filters: Optional[dict] = None
    ) -> List[dict]:
        """Get top queries for a time range"""
        base_match = {
            "timestamp": {"$gte": start_time, "$lte": end_time}
        }
        
        if filters:
            base_match.update(filters)
        
        pipeline = [
            {"$match": base_match},
            {
                "$group": {
                    "_id": "$query",
                    "count": {"$sum": 1},
                    "avg_response_time": {"$avg": "$response_time_ms"},
                    "avg_results": {"$avg": "$results_count"},
                    "total_clicks": {"$sum": {"$size": {"$ifNull": ["$clicked_results", []]}}},
                    "unique_users": {"$addToSet": "$user_id"},
                    "last_searched": {"$max": "$timestamp"}
                }
            },
            {
                "$project": {
                    "query": "$_id",
                    "count": 1,
                    "avg_response_time_ms": {"$round": ["$avg_response_time", 2]},
                    "avg_results": {"$round": ["$avg_results", 2]},
                    "total_clicks": 1,
                    "unique_users": {"$size": "$unique_users"},
                    "click_through_rate": {
                        "$round": [
                            {"$multiply": [
                                {"$divide": ["$total_clicks", "$count"]},
                                100
                            ]},
                            2
                        ]
                    },
                    "last_searched": 1
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        
        return await self.collection.aggregate(pipeline).to_list(length=limit)
    
    async def get_top_filters(
        self, 
        start_time: datetime, 
        end_time: datetime,
        limit: int = 10,
        filters: Optional[dict] = None
    ) -> List[dict]:
        """Get most used filters for a time range"""
        base_match = {
            "timestamp": {"$gte": start_time, "$lte": end_time},
            "filters": {"$exists": True, "$ne": None}
        }
        
        if filters:
            base_match.update(filters)
        
        pipeline = [
            {"$match": base_match},
            {"$unwind": {"path": "$filters", "preserveNullAndEmptyArrays": False}},
            {
                "$group": {
                    "_id": "$filters",
                    "count": {"$sum": 1},
                    "unique_queries": {"$addToSet": "$query"},
                    "unique_users": {"$addToSet": "$user_id"}
                }
            },
            {
                "$project": {
                    "filter": "$_id",
                    "count": 1,
                    "unique_queries": {"$size": "$unique_queries"},
                    "unique_users": {"$size": "$unique_users"}
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        
        return await self.collection.aggregate(pipeline).to_list(length=limit)
    
    async def get_search_trends(
        self, 
        start_time: datetime, 
        end_time: datetime,
        interval: str = "1h",
        filters: Optional[dict] = None
    ) -> List[dict]:
        """Get search trends over time"""
        base_match = {
            "timestamp": {"$gte": start_time, "$lte": end_time}
        }
        
        if filters:
            base_match.update(filters)
        
        # Convert interval to MongoDB date format
        interval_map = {
            "1h": {"$hour": "$timestamp"},
            "1d": {"$dayOfYear": "$timestamp"},
            "1w": {"$week": "$timestamp"},
            "1M": {"$month": "$timestamp"}
        }
        
        date_group = interval_map.get(interval, {"$hour": "$timestamp"})
        
        pipeline = [
            {"$match": base_match},
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$timestamp"},
                        "period": date_group,
                        "date": {"$dateToString": {
                            "format": "%Y-%m-%d %H:00:00",
                            "date": "$timestamp"
                        }}
                    },
                    "search_count": {"$sum": 1},
                    "unique_users": {"$addToSet": "$user_id"},
                    "avg_response_time": {"$avg": "$response_time_ms"},
                    "avg_results": {"$avg": "$results_count"},
                    "total_clicks": {"$sum": {"$size": {"$ifNull": ["$clicked_results", []]}}},
                    "searches_with_clicks": {
                        "$sum": {
                            "$cond": [
                                {"$gt": [{"$size": {"$ifNull": ["$clicked_results", []]}}, 0]},
                                1,
                                0
                            ]
                        }
                    }
                }
            },
            {
                "$project": {
                    "timestamp": "$_id.date",
                    "search_count": 1,
                    "unique_users": {"$size": "$unique_users"},
                    "avg_response_time_ms": {"$round": ["$avg_response_time", 2]},
                    "avg_results": {"$round": ["$avg_results", 2]},
                    "click_through_rate": {
                        "$round": [
                            {"$multiply": [
                                {"$divide": ["$searches_with_clicks", "$search_count"]},
                                100
                            ]},
                            2
                        ]
                    }
                }
            },
            {"$sort": {"_id.year": 1, "_id.period": 1}}
        ]
        
        return await self.collection.aggregate(pipeline).to_list(length=None)
    
    async def get_performance_metrics(
        self, 
        start_time: datetime, 
        end_time: datetime,
        filters: Optional[dict] = None
    ) -> dict:
        """Get performance metrics for a time range"""
        base_match = {
            "timestamp": {"$gte": start_time, "$lte": end_time}
        }
        
        if filters:
            base_match.update(filters)
        
        pipeline = [
            {"$match": base_match},
            {
                "$group": {
                    "_id": None,
                    "response_times": {"$push": "$response_time_ms"},
                    "queries": {"$push": {
                        "query": "$query",
                        "response_time_ms": "$response_time_ms"
                    }},
                    "avg_response_time": {"$avg": "$response_time_ms"},
                    "error_count": {
                        "$sum": {"$cond": [{"$eq": ["$results_count", -1]}, 1, 0]}
                    },
                    "timeout_count": {
                        "$sum": {"$cond": [{"$gte": ["$response_time_ms", 30000]}, 1, 0]}
                    },
                    "total_searches": {"$sum": 1}
                }
            },
            {
                "$project": {
                    "avg_response_time_ms": {"$round": ["$avg_response_time", 2]},
                    "response_times": 1,
                    "queries": 1,
                    "error_rate": {
                        "$round": [
                            {"$multiply": [
                                {"$divide": ["$error_count", "$total_searches"]},
                                100
                            ]},
                            2
                        ]
                    },
                    "timeout_rate": {
                        "$round": [
                            {"$multiply": [
                                {"$divide": ["$timeout_count", "$total_searches"]},
                                100
                            ]},
                            2
                        ]
                    }
                }
            }
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        
        if not result:
            return {
                "avg_response_time_ms": 0,
                "p50_response_time_ms": 0,
                "p95_response_time_ms": 0,
                "p99_response_time_ms": 0,
                "slowest_queries": [],
                "fastest_queries": [],
                "error_rate": 0,
                "timeout_rate": 0
            }
        
        stats = result[0]
        response_times = sorted(stats["response_times"])
        
        # Calculate percentiles
        def percentile(data, p):
            if not data:
                return 0
            index = int(len(data) * p / 100)
            return data[min(index, len(data) - 1)]
        
        # Get slowest and fastest queries
        queries = sorted(stats["queries"], key=lambda x: x["response_time_ms"])
        
        return {
            "avg_response_time_ms": stats["avg_response_time_ms"],
            "p50_response_time_ms": percentile(response_times, 50),
            "p95_response_time_ms": percentile(response_times, 95),
            "p99_response_time_ms": percentile(response_times, 99),
            "slowest_queries": queries[-10:],  # Top 10 slowest
            "fastest_queries": queries[:10],   # Top 10 fastest
            "error_rate": stats["error_rate"],
            "timeout_rate": stats["timeout_rate"]
        }
    
    async def get_user_segments(
        self, 
        start_time: datetime, 
        end_time: datetime,
        filters: Optional[dict] = None
    ) -> List[dict]:
        """Get user segment analysis"""
        base_match = {
            "timestamp": {"$gte": start_time, "$lte": end_time},
            "user_id": {"$exists": True, "$ne": None}
        }
        
        if filters:
            base_match.update(filters)
        
        pipeline = [
            {"$match": base_match},
            {
                "$group": {
                    "_id": "$user_id",
                    "search_count": {"$sum": 1},
                    "avg_response_time": {"$avg": "$response_time_ms"},
                    "avg_results": {"$avg": "$results_count"},
                    "total_clicks": {"$sum": {"$size": {"$ifNull": ["$clicked_results", []]}}},
                    "unique_queries": {"$addToSet": "$query"},
                    "search_types": {"$addToSet": "$search_type"},
                    "last_search": {"$max": "$timestamp"}
                }
            },
            {
                "$project": {
                    "user_id": "$_id",
                    "search_count": 1,
                    "avg_response_time_ms": {"$round": ["$avg_response_time", 2]},
                    "avg_results": {"$round": ["$avg_results", 2]},
                    "total_clicks": 1,
                    "unique_queries": {"$size": "$unique_queries"},
                    "search_types": {"$size": "$search_types"},
                    "last_search": 1,
                    "segment": {
                        "$switch": {
                            "branches": [
                                {"case": {"$gte": ["$search_count", 50]}, "then": "power_user"},
                                {"case": {"$gte": ["$search_count", 10]}, "then": "regular_user"},
                                {"case": {"$gte": ["$search_count", 1]}, "then": "casual_user"}
                            ],
                            "default": "new_user"
                        }
                    }
                }
            },
            {"$sort": {"search_count": -1}}
        ]
        
        return await self.collection.aggregate(pipeline).to_list(length=None)
    
    async def cleanup_old_analytics(self, older_than_days: int = 365) -> int:
        """Clean up old analytics data"""
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        result = await self.collection.delete_many({
            "timestamp": {"$lt": cutoff_date}
        })
        
        return result.deleted_count
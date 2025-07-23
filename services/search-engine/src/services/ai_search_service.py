"""AI-powered search service for intelligent content discovery"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import numpy as np
from sentence_transformers import SentenceTransformer
import torch
import openai
from sklearn.metrics.pairwise import cosine_similarity
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from opensearchpy import AsyncOpenSearch
import redis.asyncio as redis

from ..core.config import settings
from ..models.schemas import (
    SearchRequest,
    SearchResponse,
    SearchHit,
    SearchFilter,
)

logger = logging.getLogger(__name__)


class AISearchService:
    """Service for AI-powered search capabilities"""
    
    def __init__(self):
        """Initialize AI search service"""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Initialize semantic search model
        self.semantic_model = None
        if settings.enable_semantic_search:
            self._initialize_semantic_model()
            
        # Initialize OpenAI client for query understanding
        self.openai_client = None
        if settings.openai_api_key:
            openai.api_key = settings.openai_api_key
            self.openai_client = openai
            
        # Initialize OpenSearch client
        self.opensearch = AsyncOpenSearch(
            hosts=[settings.opensearch_url],
            http_auth=(settings.opensearch_user, settings.opensearch_password),
            use_ssl=True,
            verify_certs=False,
            ssl_show_warn=False,
        )
        
        # Initialize Redis for caching
        self.redis = None
        self.embedding_cache = {}
        
    async def initialize(self):
        """Initialize async components"""
        self.redis = await redis.from_url(settings.redis_url)
        logger.info("AI Search Service initialized")
        
    async def shutdown(self):
        """Cleanup resources"""
        if self.redis:
            await self.redis.close()
        await self.opensearch.close()
        
    def _initialize_semantic_model(self):
        """Initialize semantic search model"""
        try:
            model_name = settings.semantic_model_name or "all-MiniLM-L6-v2"
            logger.info(f"Loading semantic model: {model_name}")
            self.semantic_model = SentenceTransformer(model_name)
            self.semantic_model.to(self.device)
            logger.info("Semantic model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load semantic model: {e}")
            
    async def search(
        self,
        request: SearchRequest,
        user_id: str
    ) -> SearchResponse:
        """Perform AI-powered search"""
        try:
            # Enhance query with AI
            enhanced_query = await self._enhance_query(request.query)
            
            # Extract entities and intent
            query_analysis = await self._analyze_query(enhanced_query)
            
            # Generate search strategies
            strategies = await self._generate_search_strategies(
                enhanced_query,
                query_analysis,
                request
            )
            
            # Execute parallel search strategies
            results = await self._execute_search_strategies(strategies, request)
            
            # Rank and merge results
            final_results = await self._rank_and_merge_results(
                results,
                enhanced_query,
                query_analysis
            )
            
            # Generate facets
            facets = await self._generate_intelligent_facets(
                final_results,
                query_analysis
            )
            
            # Create response with enhanced attributes
            response = SearchResponse(
                query=request.query,
                total_hits=len(final_results),
                max_score=final_results[0].score if final_results else 0.0,
                hits=final_results[:request.limit],
                took=100,  # Would calculate actual time
                timed_out=False,
                page=request.offset // request.limit + 1,
                per_page=request.limit
            )
            
            # Add enhanced attributes for AI search
            response.enhanced_query = enhanced_query
            response.suggestions = query_analysis.get("suggestions", [])
            response.query_analysis = query_analysis
            
            return response
            
        except Exception as e:
            logger.error(f"AI search error: {e}")
            # Fallback to basic search
            return await self._fallback_search(request)
            
    async def _enhance_query(self, query: str) -> str:
        """Enhance query using AI"""
        if not self.openai_client or len(query) < 3:
            return query
            
        try:
            # Check cache
            cache_key = f"enhanced_query:{query}"
            cached = await self.redis.get(cache_key) if self.redis else None
            if cached:
                return cached.decode()
                
            # Use AI to enhance query
            response = await asyncio.to_thread(
                self.openai_client.ChatCompletion.create,
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": """You are a search query enhancer. Expand the user's query with:
                    1. Synonyms and related terms
                    2. Common variations and abbreviations
                    3. Related concepts
                    Keep the enhanced query concise and relevant."""
                }, {
                    "role": "user",
                    "content": f"Enhance this search query: {query}"
                }],
                max_tokens=100,
                temperature=0.3
            )
            
            enhanced = response.choices[0].message.content.strip()
            
            # Cache result
            if self.redis:
                await self.redis.setex(cache_key, 3600, enhanced)
                
            return enhanced
            
        except Exception as e:
            logger.warning(f"Query enhancement failed: {e}")
            return query
            
    async def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query for intent and entities"""
        analysis = {
            "intent": "search",
            "entities": [],
            "filters": {},
            "temporal": None,
            "suggestions": []
        }
        
        if not self.openai_client:
            return analysis
            
        try:
            # Use AI to analyze query
            response = await asyncio.to_thread(
                self.openai_client.ChatCompletion.create,
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": """Analyze the search query and extract:
                    1. Intent (search, filter, browse, discover)
                    2. Entities (people, places, objects, concepts)
                    3. Implicit filters (time, location, type, quality)
                    4. Temporal references
                    Return as JSON."""
                }, {
                    "role": "user",
                    "content": f"Analyze: {query}"
                }],
                max_tokens=200,
                temperature=0.2
            )
            
            # Parse response
            try:
                result = json.loads(response.choices[0].message.content)
                analysis.update(result)
            except:
                pass
                
            # Generate suggestions based on analysis
            analysis["suggestions"] = await self._generate_suggestions(query, analysis)
            
        except Exception as e:
            logger.warning(f"Query analysis failed: {e}")
            
        return analysis
        
    async def _generate_search_strategies(
        self,
        query: str,
        analysis: Dict[str, Any],
        request: SearchRequest
    ) -> List[Dict[str, Any]]:
        """Generate multiple search strategies"""
        strategies = []
        
        # 1. Semantic search strategy
        if self.semantic_model:
            strategies.append({
                "type": "semantic",
                "weight": 0.4,
                "params": {
                    "query": query,
                    "threshold": 0.7
                }
            })
            
        # 2. Full-text search strategy
        strategies.append({
            "type": "fulltext",
            "weight": 0.3,
            "params": {
                "query": query,
                "fields": ["title^3", "description^2", "content", "tags"],
                "fuzziness": "AUTO"
            }
        })
        
        # 3. Entity-based search
        if analysis.get("entities"):
            strategies.append({
                "type": "entity",
                "weight": 0.2,
                "params": {
                    "entities": analysis["entities"],
                    "boost": 2.0
                }
            })
            
        # 4. Temporal search
        if analysis.get("temporal"):
            strategies.append({
                "type": "temporal",
                "weight": 0.1,
                "params": {
                    "temporal": analysis["temporal"],
                    "range": "flexible"
                }
            })
            
        return strategies
        
    async def _execute_search_strategies(
        self,
        strategies: List[Dict[str, Any]],
        request: SearchRequest
    ) -> List[Tuple[str, List[Dict[str, Any]]]]:
        """Execute multiple search strategies in parallel"""
        tasks = []
        
        for strategy in strategies:
            if strategy["type"] == "semantic":
                task = self._semantic_search(
                    strategy["params"]["query"],
                    strategy["params"]["threshold"],
                    request.limit * 2  # Get more for ranking
                )
            elif strategy["type"] == "fulltext":
                task = self._fulltext_search(
                    strategy["params"]["query"],
                    strategy["params"]["fields"],
                    strategy["params"]["fuzziness"],
                    request.filters,
                    request.limit * 2
                )
            elif strategy["type"] == "entity":
                task = self._entity_search(
                    strategy["params"]["entities"],
                    strategy["params"]["boost"],
                    request.limit * 2
                )
            elif strategy["type"] == "temporal":
                task = self._temporal_search(
                    strategy["params"]["temporal"],
                    request.limit * 2
                )
            else:
                continue
                
            tasks.append((strategy["type"], strategy["weight"], task))
            
        # Execute all strategies in parallel
        results = []
        for strategy_type, weight, task in tasks:
            try:
                strategy_results = await task
                results.append((strategy_type, weight, strategy_results))
            except Exception as e:
                logger.error(f"Strategy {strategy_type} failed: {e}")
                
        return results
        
    async def _semantic_search(
        self,
        query: str,
        threshold: float,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search"""
        if not self.semantic_model:
            return []
            
        try:
            # Generate query embedding
            query_embedding = await self._get_embedding(query)
            
            # Search in OpenSearch using cosine similarity
            body = {
                "size": limit,
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                            "params": {"query_vector": query_embedding.tolist()}
                        }
                    }
                },
                "_source": ["id", "title", "description", "type", "created_at", "score"]
            }
            
            response = await self.opensearch.search(
                index=settings.opensearch_index,
                body=body
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                if hit["_score"] > threshold:
                    result = hit["_source"]
                    result["score"] = hit["_score"]
                    result["match_type"] = "semantic"
                    results.append(result)
                    
            return results
            
        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []
            
    async def _fulltext_search(
        self,
        query: str,
        fields: List[str],
        fuzziness: str,
        filters: Optional[List[SearchFilter]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Perform full-text search"""
        try:
            # Build query
            must_clauses = [{
                "multi_match": {
                    "query": query,
                    "fields": fields,
                    "type": "best_fields",
                    "fuzziness": fuzziness,
                    "operator": "and"
                }
            }]
            
            # Add filters
            if filters:
                for filter_item in filters:
                    if filter_item.field and filter_item.value:
                        must_clauses.append({
                            "term": {filter_item.field: filter_item.value}
                        })
                        
            body = {
                "size": limit,
                "query": {
                    "bool": {
                        "must": must_clauses
                    }
                },
                "_source": ["id", "title", "description", "type", "created_at"],
                "highlight": {
                    "fields": {
                        "title": {},
                        "description": {},
                        "content": {}
                    }
                }
            }
            
            response = await self.opensearch.search(
                index=settings.opensearch_index,
                body=body
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                result = hit["_source"]
                result["score"] = hit["_score"]
                result["match_type"] = "fulltext"
                if "highlight" in hit:
                    result["highlights"] = hit["highlight"]
                results.append(result)
                
            return results
            
        except Exception as e:
            logger.error(f"Full-text search error: {e}")
            return []
            
    async def _entity_search(
        self,
        entities: List[Dict[str, str]],
        boost: float,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search based on extracted entities"""
        if not entities:
            return []
            
        try:
            should_clauses = []
            
            for entity in entities:
                entity_type = entity.get("type", "general")
                entity_value = entity.get("value", "")
                
                if entity_type == "person":
                    should_clauses.extend([
                        {"match": {"people": {"query": entity_value, "boost": boost}}},
                        {"match": {"credits": {"query": entity_value, "boost": boost}}}
                    ])
                elif entity_type == "location":
                    should_clauses.extend([
                        {"match": {"location": {"query": entity_value, "boost": boost}}},
                        {"match": {"shooting_location": {"query": entity_value, "boost": boost}}}
                    ])
                elif entity_type == "organization":
                    should_clauses.append(
                        {"match": {"organization": {"query": entity_value, "boost": boost}}}
                    )
                else:
                    should_clauses.append(
                        {"match": {"tags": {"query": entity_value, "boost": boost}}}
                    )
                    
            body = {
                "size": limit,
                "query": {
                    "bool": {
                        "should": should_clauses,
                        "minimum_should_match": 1
                    }
                },
                "_source": ["id", "title", "description", "type", "created_at"]
            }
            
            response = await self.opensearch.search(
                index=settings.opensearch_index,
                body=body
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                result = hit["_source"]
                result["score"] = hit["_score"]
                result["match_type"] = "entity"
                result["matched_entities"] = entities
                results.append(result)
                
            return results
            
        except Exception as e:
            logger.error(f"Entity search error: {e}")
            return []
            
    async def _temporal_search(
        self,
        temporal: Dict[str, Any],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search based on temporal references"""
        try:
            # Parse temporal information
            time_range = temporal.get("range", {})
            time_type = temporal.get("type", "absolute")
            
            # Build date range query
            range_query = {}
            if time_type == "relative":
                # Handle relative dates like "last week", "yesterday"
                range_query = self._parse_relative_time(temporal.get("value", ""))
            else:
                # Handle absolute dates
                if "start" in time_range:
                    range_query["gte"] = time_range["start"]
                if "end" in time_range:
                    range_query["lte"] = time_range["end"]
                    
            body = {
                "size": limit,
                "query": {
                    "range": {
                        "created_at": range_query
                    }
                },
                "_source": ["id", "title", "description", "type", "created_at"],
                "sort": [{"created_at": {"order": "desc"}}]
            }
            
            response = await self.opensearch.search(
                index=settings.opensearch_index,
                body=body
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                result = hit["_source"]
                result["score"] = hit["_score"]
                result["match_type"] = "temporal"
                results.append(result)
                
            return results
            
        except Exception as e:
            logger.error(f"Temporal search error: {e}")
            return []
            
    async def _rank_and_merge_results(
        self,
        strategy_results: List[Tuple[str, float, List[Dict[str, Any]]]],
        query: str,
        analysis: Dict[str, Any]
    ) -> List[SearchHit]:
        """Rank and merge results from different strategies"""
        # Collect all unique results
        result_map = {}
        
        for strategy_type, weight, results in strategy_results:
            for result in results:
                result_id = result.get("id")
                if result_id not in result_map:
                    result_map[result_id] = {
                        "data": result,
                        "scores": {},
                        "match_types": set()
                    }
                    
                # Record score and match type
                result_map[result_id]["scores"][strategy_type] = result.get("score", 0) * weight
                result_map[result_id]["match_types"].add(result.get("match_type", strategy_type))
                
        # Calculate final scores
        final_results = []
        for result_id, result_data in result_map.items():
            # Combine scores
            final_score = sum(result_data["scores"].values())
            
            # Apply boosting based on analysis
            if analysis.get("intent") == "discover":
                # Boost diverse results
                final_score *= (1 + 0.1 * len(result_data["match_types"]))
                
            # Create search hit
            search_hit = SearchHit(
                id=result_id,
                index=settings.opensearch_index,
                score=final_score,
                source=result_data["data"],
                highlight=result_data["data"].get("highlights", {}),
                ranking_explanation={
                    "match_types": list(result_data["match_types"]),
                    "strategy_scores": result_data["scores"],
                    "final_score": final_score
                }
            )
            final_results.append(search_hit)
            
        # Sort by final score
        final_results.sort(key=lambda x: x.score, reverse=True)
        
        # Apply personalization if available
        if settings.enable_personalization:
            final_results = await self._personalize_results(final_results, query)
            
        return final_results
        
    async def _generate_intelligent_facets(
        self,
        results: List[SearchHit],
        analysis: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Generate intelligent facets based on results and query analysis"""
        facets = {}
        
        # Standard facets
        standard_facets = ["type", "format", "status", "tags"]
        
        # Dynamic facets based on query analysis
        if "location" in str(analysis.get("entities", [])):
            standard_facets.append("location")
            
        if analysis.get("temporal"):
            standard_facets.append("date_range")
            
        # Collect facet values from results
        for facet_field in standard_facets:
            facet_values = {}
            
            for result in results:
                value = result.source.get(facet_field)
                if value:
                    if isinstance(value, list):
                        for v in value:
                            facet_values[v] = facet_values.get(v, 0) + 1
                    else:
                        facet_values[value] = facet_values.get(value, 0) + 1
                        
            # Convert to facet buckets
            if facet_values:
                facets[facet_field] = [
                    {"key": k, "doc_count": v}
                    for k, v in sorted(
                        facet_values.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:10]  # Top 10 values
                ]
                
        return facets
        
    async def _generate_suggestions(
        self,
        query: str,
        analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate search suggestions"""
        suggestions = []
        
        # Query completions
        if len(query) > 2:
            # Get popular searches starting with query
            completions = await self._get_query_completions(query)
            suggestions.extend(completions[:3])
            
        # Related searches based on entities
        for entity in analysis.get("entities", []):
            related = await self._get_related_searches(entity.get("value", ""))
            suggestions.extend(related[:2])
            
        # Dedup and limit
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s not in seen and s != query:
                seen.add(s)
                unique_suggestions.append(s)
                
        return unique_suggestions[:5]
        
    async def _get_embedding(self, text: str) -> np.ndarray:
        """Get text embedding with caching"""
        # Check cache
        if text in self.embedding_cache:
            return self.embedding_cache[text]
            
        # Generate embedding
        embedding = self.semantic_model.encode(text, convert_to_numpy=True)
        
        # Cache (limit size)
        if len(self.embedding_cache) < 1000:
            self.embedding_cache[text] = embedding
            
        return embedding
        
    async def _get_query_completions(self, prefix: str) -> List[str]:
        """Get query completions from search history"""
        # This would query a search history index
        # For now, return empty
        return []
        
    async def _get_related_searches(self, term: str) -> List[str]:
        """Get related search terms"""
        # This would use a knowledge graph or related terms index
        # For now, return empty
        return []
        
    async def _personalize_results(
        self,
        results: List[SearchHit],
        query: str
    ) -> List[SearchHit]:
        """Personalize results based on user preferences"""
        # This would use user history and preferences
        # For now, return as-is
        return results
        
    def _parse_relative_time(self, time_str: str) -> Dict[str, str]:
        """Parse relative time strings"""
        now = datetime.utcnow()
        
        time_mappings = {
            "today": {"gte": now.date().isoformat()},
            "yesterday": {
                "gte": (now.date() - timedelta(days=1)).isoformat(),
                "lt": now.date().isoformat()
            },
            "last week": {"gte": (now - timedelta(days=7)).isoformat()},
            "last month": {"gte": (now - timedelta(days=30)).isoformat()},
            "last year": {"gte": (now - timedelta(days=365)).isoformat()},
        }
        
        return time_mappings.get(time_str.lower(), {})
        
    async def _fallback_search(self, request: SearchRequest) -> SearchResponse:
        """Fallback to basic search if AI features fail"""
        try:
            # Basic OpenSearch query
            body = {
                "size": request.limit,
                "from": request.offset,
                "query": {
                    "multi_match": {
                        "query": request.query,
                        "fields": ["title^3", "description^2", "content", "tags"]
                    }
                }
            }
            
            response = await self.opensearch.search(
                index=settings.opensearch_index,
                body=body
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                result = SearchHit(
                    id=hit["_source"].get("id"),
                    index=settings.opensearch_index,
                    score=hit["_score"],
                    source=hit["_source"]
                )
                results.append(result)
                
            return SearchResponse(
                query=request.query,
                total_hits=response["hits"]["total"]["value"],
                max_score=response["hits"]["max_score"],
                hits=results,
                took=response.get("took", 0),
                timed_out=response.get("timed_out", False),
                page=request.offset // request.limit + 1,
                per_page=request.limit
            )
            
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return SearchResponse(
                query=request.query,
                total_hits=0,
                max_score=0.0,
                hits=[],
                took=0,
                timed_out=False,
                page=1,
                per_page=request.limit
            )
            
    async def index_with_ai(
        self,
        document: Dict[str, Any],
        generate_embeddings: bool = True
    ) -> Dict[str, Any]:
        """Index document with AI enhancements"""
        try:
            # Generate embeddings for semantic search
            if generate_embeddings and self.semantic_model:
                text_content = f"{document.get('title', '')} {document.get('description', '')} {document.get('content', '')}"
                embedding = await self._get_embedding(text_content[:1000])  # Limit length
                document["embedding"] = embedding.tolist()
                
            # Extract entities using AI
            if self.openai_client:
                entities = await self._extract_entities(document)
                document["ai_entities"] = entities
                
            # Generate AI tags
            if self.openai_client:
                ai_tags = await self._generate_ai_tags(document)
                existing_tags = document.get("tags", [])
                document["tags"] = list(set(existing_tags + ai_tags))
                
            # Generate summary if missing
            if not document.get("description") and document.get("content"):
                summary = await self._generate_summary(document["content"])
                document["ai_summary"] = summary
                
            return document
            
        except Exception as e:
            logger.error(f"AI indexing enhancement failed: {e}")
            return document
            
    async def _extract_entities(self, document: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract entities from document using AI"""
        try:
            text = f"{document.get('title', '')} {document.get('description', '')}"
            
            response = await asyncio.to_thread(
                self.openai_client.ChatCompletion.create,
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "Extract named entities (people, places, organizations, dates) from the text. Return as JSON array."
                }, {
                    "role": "user",
                    "content": text[:500]
                }],
                max_tokens=200,
                temperature=0.1
            )
            
            entities = json.loads(response.choices[0].message.content)
            return entities
            
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")
            return []
            
    async def _generate_ai_tags(self, document: Dict[str, Any]) -> List[str]:
        """Generate AI tags for document"""
        try:
            text = f"{document.get('title', '')} {document.get('description', '')}"
            
            response = await asyncio.to_thread(
                self.openai_client.ChatCompletion.create,
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "Generate 5-10 relevant tags for this content. Return as comma-separated list."
                }, {
                    "role": "user",
                    "content": text[:500]
                }],
                max_tokens=100,
                temperature=0.5
            )
            
            tags = [tag.strip() for tag in response.choices[0].message.content.split(",")]
            return tags[:10]
            
        except Exception as e:
            logger.warning(f"AI tag generation failed: {e}")
            return []
            
    async def _generate_summary(self, content: str) -> str:
        """Generate summary for content"""
        try:
            response = await asyncio.to_thread(
                self.openai_client.ChatCompletion.create,
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "Create a concise 2-3 sentence summary of this content."
                }, {
                    "role": "user",
                    "content": content[:1000]
                }],
                max_tokens=150,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            return ""


# Global service instance
ai_search_service = AISearchService()
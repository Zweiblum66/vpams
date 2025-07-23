"""
Search Service - Core search functionality
"""

import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import structlog
from opensearchpy import AsyncOpenSearch
from opensearchpy.exceptions import RequestError, ConnectionError as OpenSearchConnectionError

from ..models.schemas import (
    SearchQuery, AdvancedSearchQuery, MetadataFieldSearchQuery, SearchResponse, SearchHit, 
    SearchAggregation, IndexType, SearchType, RankingConfig,
    FilteredSearchQuery, FilteredSearchResponse, FilterCondition, FacetConfig, FacetResult,
    FuzzySearchQuery, FuzzySearchResponse, FuzzyMatchType, FuzzinessType, FuzzySearchConfig,
    PhoneticSearchQuery, PhoneticSearchResponse, PhoneticSuggestionQuery, PhoneticSuggestionResponse,
    SynonymSearchQuery, SynonymSearchResponse, SynonymSuggestionQuery, SynonymSuggestionResponse
)
from ..db.opensearch import get_opensearch_client
from ..core.config import get_settings
from ..core.exceptions import SearchError, SearchTimeoutError, InvalidQueryError
from .ranking_service import RankingService, get_ranking_service
from .facet_service import FacetService
from .fuzzy_service import FuzzySearchService
from .phonetic_service import PhoneticSearchService
from .synonym_service import SynonymService

logger = structlog.get_logger()


class SearchService:
    """Service for handling search operations"""
    
    def __init__(self, opensearch_client: AsyncOpenSearch, ranking_service: Optional[RankingService] = None):
        self.client = opensearch_client
        self.settings = get_settings()
        self.ranking_service = ranking_service
        self.facet_service = FacetService(opensearch_client)
        self.fuzzy_service = FuzzySearchService(opensearch_client)
        self.phonetic_service = PhoneticSearchService(opensearch_client)
        self.synonym_service = SynonymService(opensearch_client)
        self.index_mappings = {
            IndexType.ASSETS: self.settings.assets_index_name,
            IndexType.METADATA: self.settings.metadata_index_name,
            IndexType.CONTENT: self.settings.content_index_name,
            IndexType.ALL: f"{self.settings.assets_index_name},{self.settings.metadata_index_name},{self.settings.content_index_name}"
        }
    
    async def search(self, query: SearchQuery) -> SearchResponse:
        """
        Perform a basic search across specified indices
        
        Args:
            query: Search query parameters
            
        Returns:
            SearchResponse with results and metadata
        """
        try:
            start_time = time.time()
            
            # Build the search request
            search_body = self._build_search_body(query)
            
            # Determine indices to search
            indices = self._get_search_indices(query.indices)
            
            logger.info(
                "executing_search",
                query=query.query,
                indices=indices,
                size=query.size,
                from_=query.from_
            )
            
            # Execute search
            response = await self.client.search(
                index=indices,
                body=search_body,
                timeout=f"{query.timeout or self.settings.search_timeout}s"
            )
            
            # Process response
            search_response = await self._process_search_response(
                response, 
                query, 
                int((time.time() - start_time) * 1000)
            )
            
            logger.info(
                "search_completed",
                query=query.query,
                total_hits=search_response.total_hits,
                took_ms=search_response.took
            )
            
            return search_response
            
        except OpenSearchConnectionError as e:
            logger.error("search_connection_error", error=str(e))
            raise SearchError("Failed to connect to search service", query=query.query)
        except RequestError as e:
            logger.error("search_request_error", error=str(e), query=query.query)
            raise InvalidQueryError(f"Invalid search query: {str(e)}", query=query.query)
        except Exception as e:
            logger.error("search_failed", error=str(e), query=query.query)
            raise SearchError(f"Search operation failed: {str(e)}", query=query.query)
    
    async def advanced_search(self, query: AdvancedSearchQuery) -> SearchResponse:
        """
        Perform an advanced search with complex query conditions
        
        Args:
            query: Advanced search query parameters
            
        Returns:
            SearchResponse with results and metadata
        """
        try:
            start_time = time.time()
            
            # Build advanced search request
            search_body = self._build_advanced_search_body(query)
            
            # Always search all indices for advanced search
            indices = self.index_mappings[IndexType.ALL]
            
            logger.info(
                "executing_advanced_search",
                must_conditions=len(query.must or []),
                should_conditions=len(query.should or []),
                must_not_conditions=len(query.must_not or [])
            )
            
            # Execute search
            response = await self.client.search(
                index=indices,
                body=search_body,
                timeout=f"{self.settings.search_timeout}s"
            )
            
            # Process response
            search_response = await self._process_search_response(
                response,
                SearchQuery(  # Convert to basic query for response processing
                    query="Advanced search",
                    size=query.size,
                    from_=query.from_,
                    sort_by=query.sort_by,
                    sort_order=query.sort_order,
                    highlight=query.highlight,
                    include_aggregations=query.include_aggregations
                ),
                int((time.time() - start_time) * 1000)
            )
            
            logger.info(
                "advanced_search_completed",
                total_hits=search_response.total_hits,
                took_ms=search_response.took
            )
            
            return search_response
            
        except Exception as e:
            logger.error("advanced_search_failed", error=str(e))
            raise SearchError(f"Advanced search operation failed: {str(e)}")
    
    async def metadata_field_search(self, query: MetadataFieldSearchQuery) -> SearchResponse:
        """
        Perform a search on specific metadata fields
        
        Args:
            query: Metadata field search query parameters
            
        Returns:
            SearchResponse with results and metadata
        """
        try:
            start_time = time.time()
            
            # Build metadata field search request
            search_body = self._build_metadata_field_search_body(query)
            
            # Determine indices to search
            indices = self._get_search_indices(query.indices)
            
            logger.info(
                "executing_metadata_field_search",
                field_count=len(query.field_queries),
                operator=query.operator,
                indices=indices,
                fuzzy=query.fuzzy
            )
            
            # Execute search
            response = await self.client.search(
                index=indices,
                body=search_body,
                timeout=f"{self.settings.search_timeout}s"
            )
            
            # Process response
            search_response = await self._process_search_response(
                response,
                SearchQuery(  # Convert to basic query for response processing
                    query=f"Metadata field search: {query.operator} operator",
                    size=query.size,
                    from_=query.from_,
                    sort_by=query.sort_by,
                    sort_order=query.sort_order,
                    highlight=query.highlight,
                    include_aggregations=query.include_aggregations
                ),
                int((time.time() - start_time) * 1000)
            )
            
            logger.info(
                "metadata_field_search_completed",
                total_hits=search_response.total_hits,
                took_ms=search_response.took
            )
            
            return search_response
            
        except OpenSearchConnectionError as e:
            logger.error("metadata_search_connection_error", error=str(e))
            raise SearchError("Failed to connect to search service")
        except RequestError as e:
            logger.error("metadata_search_request_error", error=str(e))
            raise InvalidQueryError(f"Invalid metadata search query: {str(e)}")
        except Exception as e:
            logger.error("metadata_search_failed", error=str(e))
            raise SearchError(f"Metadata field search operation failed: {str(e)}")
    
    def _build_search_body(self, query: SearchQuery) -> Dict[str, Any]:
        """Build OpenSearch query body from search parameters"""
        body = {
            "size": query.size,
            "from": query.from_,
            "track_total_hits": True
        }
        
        # Build query based on search type
        if query.search_type == SearchType.PHRASE:
            main_query = {
                "match_phrase": {
                    "_all": {
                        "query": query.query,
                        "slop": 2
                    }
                }
            }
        elif query.search_type == SearchType.FUZZY:
            # Use enhanced fuzzy search if fuzzy_config is provided
            if query.fuzzy_config:
                main_query = self._build_enhanced_fuzzy_query(query)
            else:
                main_query = {
                    "fuzzy": {
                        "_all": {
                            "value": query.query,
                            "fuzziness": "AUTO"
                        }
                    }
                }
        elif query.search_type == SearchType.FUZZY_PHRASE:
            main_query = self._build_fuzzy_phrase_query(query)
        elif query.search_type == SearchType.FUZZY_CROSS_FIELD:
            main_query = self._build_fuzzy_cross_field_query(query)
        elif query.search_type == SearchType.WILDCARD:
            main_query = {
                "wildcard": {
                    "_all": {
                        "value": f"*{query.query}*",
                        "case_insensitive": True
                    }
                }
            }
        elif query.search_type == SearchType.PHONETIC:
            # Use phonetic search service for phonetic queries
            from ..models.schemas import PhoneticAlgorithm, PhoneticMatchType
            phonetic_query = PhoneticSearchQuery(
                query=query.query,
                algorithm=PhoneticAlgorithm.SOUNDEX,
                match_type=PhoneticMatchType.ADAPTIVE,
                fields=None,
                indices=query.indices,
                size=query.size,
                from_=query.from_,
                sort_by=query.sort_by,
                sort_order=query.sort_order,
                highlight=query.highlight
            )
            # Return early since phonetic search is handled by phonetic service
            return await self.phonetic_service.phonetic_search(phonetic_query)
        elif query.search_type == SearchType.SYNONYM:
            # Use synonym search service for synonym queries
            from ..models.schemas import SynonymType, SynonymExpansionStrategy, SynonymConfig
            synonym_query = SynonymSearchQuery(
                query=query.query,
                synonym_config=SynonymConfig(
                    synonym_type=SynonymType.HYBRID,
                    expansion_strategy=SynonymExpansionStrategy.EXPAND
                ),
                fields=None,
                indices=query.indices,
                size=query.size,
                from_=query.from_,
                sort_by=query.sort_by,
                sort_order=query.sort_order,
                highlight=query.highlight
            )
            # Return early since synonym search is handled by synonym service
            return await self.synonym_service.synonym_search(synonym_query)
        else:  # BASIC search
            main_query = {
                "multi_match": {
                    "query": query.query,
                    "fields": self._get_search_fields(),
                    "type": "best_fields",
                    "operator": "OR",
                    "fuzziness": "AUTO"
                }
            }
        
        # Apply filters if provided
        if query.filters:
            body["query"] = {
                "bool": {
                    "must": [main_query],
                    "filter": self._build_filters(query.filters)
                }
            }
        else:
            body["query"] = main_query
        
        # Add sorting
        if query.sort_by:
            body["sort"] = [{
                query.sort_by: {
                    "order": query.sort_order.value
                }
            }]
        else:
            # Default sort by relevance score and then by created_at
            body["sort"] = [
                "_score",
                {
                    "created_at": {
                        "order": "desc",
                        "missing": "_last"
                    }
                }
            ]
        
        # Add highlighting
        if query.highlight:
            body["highlight"] = {
                "fields": {
                    "*": {
                        "fragment_size": 150,
                        "number_of_fragments": 3,
                        "pre_tags": ["<mark>"],
                        "post_tags": ["</mark>"]
                    }
                },
                "encoder": "html"
            }
        
        # Add aggregations
        if query.include_aggregations:
            body["aggs"] = self._build_aggregations()
        
        return body
    
    def _build_advanced_search_body(self, query: AdvancedSearchQuery) -> Dict[str, Any]:
        """Build OpenSearch query body for advanced search"""
        body = {
            "size": query.size,
            "from": query.from_,
            "track_total_hits": True
        }
        
        # Build bool query
        bool_query = {}
        
        if query.must:
            bool_query["must"] = [self._build_condition(cond) for cond in query.must]
        
        if query.should:
            bool_query["should"] = [self._build_condition(cond) for cond in query.should]
            bool_query["minimum_should_match"] = 1
        
        if query.must_not:
            bool_query["must_not"] = [self._build_condition(cond) for cond in query.must_not]
        
        if query.filters:
            bool_query["filter"] = self._build_filters(query.filters)
        
        body["query"] = {"bool": bool_query} if bool_query else {"match_all": {}}
        
        # Add sorting
        if query.sort_by:
            body["sort"] = [{
                query.sort_by: {
                    "order": query.sort_order.value
                }
            }]
        
        # Add highlighting
        if query.highlight:
            body["highlight"] = {
                "fields": {"*": {}},
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"]
            }
        
        # Add aggregations
        if query.include_aggregations:
            body["aggs"] = self._build_aggregations()
        
        return body
    
    def _build_metadata_field_search_body(self, query: MetadataFieldSearchQuery) -> Dict[str, Any]:
        """Build OpenSearch query body for metadata field search"""
        body = {
            "size": query.size,
            "from": query.from_,
            "track_total_hits": True
        }
        
        # Build field-specific queries
        field_queries = []
        for fq in query.field_queries:
            field = fq['field']
            value = fq['value']
            
            if query.fuzzy:
                # Fuzzy match for typo tolerance
                field_query = {
                    "fuzzy": {
                        field: {
                            "value": value,
                            "fuzziness": "AUTO",
                            "prefix_length": 1,
                            "max_expansions": 50
                        }
                    }
                }
            else:
                # Exact match or standard match
                if field.endswith('.keyword'):
                    # Exact match for keyword fields
                    field_query = {"term": {field: value}}
                else:
                    # Standard match for text fields
                    field_query = {"match": {field: {"query": value}}}
            
            # Apply boosting if specified
            if query.boost_fields and field in query.boost_fields:
                boost_value = query.boost_fields[field]
                if "match" in field_query:
                    field_query["match"][field]["boost"] = boost_value
                elif "fuzzy" in field_query:
                    field_query["fuzzy"][field]["boost"] = boost_value
                elif "term" in field_query:
                    field_query = {"constant_score": {"filter": field_query, "boost": boost_value}}
            
            field_queries.append(field_query)
        
        # Combine queries based on operator
        if query.operator == "AND":
            bool_query = {"must": field_queries}
        else:  # OR
            bool_query = {"should": field_queries, "minimum_should_match": 1}
        
        # Apply additional filters
        if query.filters:
            if "filter" not in bool_query:
                bool_query["filter"] = []
            bool_query["filter"].extend(self._build_filters(query.filters))
        
        body["query"] = {"bool": bool_query}
        
        # Add sorting
        if query.sort_by:
            body["sort"] = [{
                query.sort_by: {
                    "order": query.sort_order.value
                }
            }]
        else:
            # Default sort by relevance score
            body["sort"] = ["_score"]
        
        # Add highlighting
        if query.highlight:
            highlight_fields = {}
            for fq in query.field_queries:
                field = fq['field']
                highlight_fields[field] = {
                    "fragment_size": 150,
                    "number_of_fragments": 3,
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"]
                }
            
            body["highlight"] = {
                "fields": highlight_fields,
                "encoder": "html"
            }
        
        # Add aggregations
        if query.include_aggregations:
            body["aggs"] = self._build_metadata_aggregations()
        
        return body
    
    def _build_condition(self, condition: Dict[str, Any]) -> Dict[str, Any]:
        """Build a single condition for advanced search"""
        field = condition.get("field", "_all")
        operator = condition.get("operator", "contains")
        value = condition.get("value", "")
        
        if operator == "equals":
            return {"term": {field: value}}
        elif operator == "not_equals":
            return {"bool": {"must_not": {"term": {field: value}}}}
        elif operator == "contains":
            return {"match": {field: value}}
        elif operator == "starts_with":
            return {"prefix": {field: value}}
        elif operator == "ends_with":
            return {"wildcard": {field: f"*{value}"}}
        elif operator == "greater_than":
            return {"range": {field: {"gt": value}}}
        elif operator == "less_than":
            return {"range": {field: {"lt": value}}}
        elif operator == "between":
            return {"range": {field: {"gte": value.get("from"), "lte": value.get("to")}}}
        else:
            return {"match": {field: value}}
    
    def _build_filters(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build filter conditions from filter dictionary"""
        filter_conditions = []
        
        for field, value in filters.items():
            if isinstance(value, list):
                # Multiple values - use terms query
                filter_conditions.append({"terms": {field: value}})
            elif isinstance(value, dict):
                # Range filter
                filter_conditions.append({"range": {field: value}})
            else:
                # Single value - use term query
                filter_conditions.append({"term": {field: value}})
        
        return filter_conditions
    
    def _build_aggregations(self) -> Dict[str, Any]:
        """Build standard aggregations for search results"""
        return {
            "asset_types": {
                "terms": {
                    "field": "asset_type",
                    "size": 10
                }
            },
            "file_extensions": {
                "terms": {
                    "field": "file_extension",
                    "size": 20
                }
            },
            "mime_types": {
                "terms": {
                    "field": "mime_type",
                    "size": 20
                }
            },
            "status": {
                "terms": {
                    "field": "status",
                    "size": 10
                }
            },
            "tags": {
                "terms": {
                    "field": "tags",
                    "size": 50
                }
            },
            "date_histogram": {
                "date_histogram": {
                    "field": "created_at",
                    "calendar_interval": "month",
                    "format": "yyyy-MM"
                }
            }
        }
    
    def _build_metadata_aggregations(self) -> Dict[str, Any]:
        """Build metadata-specific aggregations"""
        return {
            "metadata_types": {
                "terms": {
                    "field": "metadata_type",
                    "size": 20
                }
            },
            "content_types": {
                "terms": {
                    "field": "content_type",
                    "size": 20
                }
            },
            "file_formats": {
                "terms": {
                    "field": "format",
                    "size": 30
                }
            },
            "languages": {
                "terms": {
                    "field": "language",
                    "size": 20
                }
            },
            "creators": {
                "terms": {
                    "field": "creator.keyword",
                    "size": 50
                }
            },
            "subjects": {
                "terms": {
                    "field": "subject.keyword",
                    "size": 50
                }
            },
            "keywords": {
                "terms": {
                    "field": "keywords",
                    "size": 100
                }
            },
            "date_created_histogram": {
                "date_histogram": {
                    "field": "date_created",
                    "calendar_interval": "month",
                    "format": "yyyy-MM"
                }
            }
        }
    
    def _get_search_fields(self) -> List[str]:
        """Get fields to search in based on index type"""
        return [
            # Asset fields
            "name^3",  # Boost name field
            "description^2",  # Boost description
            "file_name^2",
            "tags^2",
            
            # Metadata fields
            "title^3",
            "keywords^2",
            "custom_fields.*",
            
            # Content fields
            "content",
            "transcript",
            "ocr_text",
            "all_text",
            
            # General fields
            "asset_id",
            "project_id",
            "*"  # Catch-all
        ]
    
    def _get_search_indices(self, index_types: List[IndexType]) -> str:
        """Get comma-separated list of indices to search"""
        if IndexType.ALL in index_types:
            return self.index_mappings[IndexType.ALL]
        
        indices = []
        for index_type in index_types:
            if index_type in self.index_mappings:
                indices.append(self.index_mappings[index_type])
        
        return ",".join(indices) if indices else self.index_mappings[IndexType.ALL]
    
    async def _process_search_response(
        self, 
        response: Dict[str, Any], 
        query: SearchQuery,
        took_ms: int
    ) -> SearchResponse:
        """Process OpenSearch response into SearchResponse model"""
        # Extract hits
        hits = []
        for hit in response.get("hits", {}).get("hits", []):
            search_hit = SearchHit(
                id=hit["_id"],
                index=hit["_index"],
                score=hit.get("_score", 0.0),
                source=hit["_source"],
                highlight=hit.get("highlight", {})
            )
            hits.append(search_hit)
        
        # Apply custom ranking if ranking service is available and not using explicit sort
        if self.ranking_service and hits and not query.sort_by:
            hits = await self.ranking_service.rank_results(
                hits, 
                query.query,
                query.ranking_config
            )
            
            # Add ranking explanations if requested
            if query.include_ranking_explanation:
                for hit in hits:
                    hit.ranking_explanation = self.ranking_service.get_ranking_explanation(hit)
        
        # Extract aggregations
        aggregations = []
        if "aggregations" in response:
            for agg_name, agg_data in response["aggregations"].items():
                if "buckets" in agg_data:
                    aggregations.append(SearchAggregation(
                        name=agg_name,
                        buckets=agg_data["buckets"]
                    ))
        
        # Calculate pagination info
        total_hits = response["hits"]["total"]["value"]
        total_pages = (total_hits + query.size - 1) // query.size
        current_page = (query.from_ // query.size) + 1
        
        return SearchResponse(
            query=query.query,
            total_hits=total_hits,
            max_score=response["hits"].get("max_score"),
            hits=hits,
            aggregations=aggregations if aggregations else None,
            took=took_ms,
            timed_out=response.get("timed_out", False),
            page=current_page,
            per_page=query.size,
            total_pages=total_pages
        )
    
    async def filtered_search(self, query: FilteredSearchQuery) -> FilteredSearchResponse:
        """
        Perform search with advanced filtering and faceting
        
        Args:
            query: Filtered search query with filters and facets
            
        Returns:
            FilteredSearchResponse with results and facets
        """
        start_time = time.time()
        
        try:
            # Build query body
            body = self._build_filtered_search_body(query)
            
            # Determine indices to search
            indices = self._get_search_indices(query.indices)
            
            # Execute search
            response = await self.client.search(
                index=indices,
                body=body,
                timeout=f"{query.timeout or self.settings.search_timeout}s"
            )
            
            # Process response
            search_response = await self._process_filtered_search_response(
                response, 
                query,
                int((time.time() - start_time) * 1000)
            )
            
            logger.info(
                "filtered_search_completed",
                query=query.query,
                total_hits=search_response.total_hits,
                facet_count=len(search_response.facets or []),
                took_ms=search_response.took
            )
            
            return search_response
            
        except OpenSearchConnectionError as e:
            logger.error("filtered_search_connection_error", error=str(e))
            raise SearchError("Failed to connect to search service")
        except RequestError as e:
            logger.error("filtered_search_request_error", error=str(e))
            raise InvalidQueryError(f"Invalid search query: {str(e)}")
        except Exception as e:
            logger.error("filtered_search_failed", error=str(e))
            raise SearchError(f"Search operation failed: {str(e)}")
    
    def _build_filtered_search_body(self, query: FilteredSearchQuery) -> Dict[str, Any]:
        """Build OpenSearch query body for filtered search"""
        body = {
            "size": query.size,
            "from": query.from_,
            "track_total_hits": True
        }
        
        # Build main query
        main_query = self._build_main_query(query.query, query.search_type)
        
        # Build bool query with filters
        bool_query = {"must": [main_query]}
        
        # Add filters (affects both results and facets)
        if query.filters:
            filter_queries = self.facet_service.build_filter_query(query.filters)
            if filter_queries:
                bool_query["filter"] = filter_queries
        
        body["query"] = {"bool": bool_query}
        
        # Add post_filters (only affects results, not facets)
        if query.post_filters:
            post_filter_queries = self.facet_service.build_filter_query(query.post_filters)
            if post_filter_queries:
                body["post_filter"] = {"bool": {"must": post_filter_queries}}
        
        # Add aggregations for facets
        if query.facets:
            aggregations = self.facet_service.build_aggregations(query.facets)
            if aggregations:
                body["aggs"] = aggregations
        elif query.facets is None:
            # Use default facets if none specified
            default_facets = self.facet_service.get_default_facets()
            aggregations = self.facet_service.build_aggregations(default_facets)
            if aggregations:
                body["aggs"] = aggregations
        
        # Add sorting
        if query.sort_by:
            body["sort"] = [{
                query.sort_by: {"order": query.sort_order.value}
            }]
        else:
            body["sort"] = ["_score", {"created_at": {"order": "desc", "missing": "_last"}}]
        
        # Add highlighting
        if query.highlight:
            body["highlight"] = self._build_highlight_config()
        
        # Add source filtering
        if not query.include_source:
            body["_source"] = False
        elif query.source_fields:
            body["_source"] = query.source_fields
        
        return body
    
    def _build_enhanced_fuzzy_query(self, query: SearchQuery) -> Dict[str, Any]:
        """Build enhanced fuzzy query using fuzzy service"""
        config = query.fuzzy_config
        
        # Convert config to fuzzy service format
        from .fuzzy_service import FuzzyConfig, FuzzinessType as FuzzyFuzzinessType
        
        fuzzy_config = FuzzyConfig(
            fuzziness=FuzzyFuzzinessType(config.fuzziness.value),
            prefix_length=config.prefix_length,
            max_expansions=config.max_expansions,
            transpositions=config.transpositions,
            boost=1.0
        )
        
        # Use fuzzy service to build query
        if config.match_type == FuzzyMatchType.ADAPTIVE:
            return self.fuzzy_service.build_adaptive_fuzzy_query(
                query.query, 
                fields=self._get_search_fields(),
                match_type=config.match_type
            )
        elif config.match_type == FuzzyMatchType.CROSS_FIELD:
            return self.fuzzy_service.build_cross_field_fuzzy_query(
                query.query,
                fields=self._get_search_fields(),
                config=fuzzy_config
            )
        elif config.match_type == FuzzyMatchType.PHRASE:
            return self.fuzzy_service.build_fuzzy_phrase_query(
                query.query,
                fields=self._get_search_fields(),
                slop=config.slop,
                config=fuzzy_config
            )
        elif config.match_type == FuzzyMatchType.MULTI_TERM:
            terms = query.query.split()
            return self.fuzzy_service.build_multi_term_fuzzy_query(
                terms,
                fields=self._get_search_fields(),
                config=fuzzy_config
            )
        else:  # SINGLE_TERM
            return self.fuzzy_service.build_single_term_fuzzy_query(
                query.query,
                "_all",
                fuzzy_config
            )
    
    def _build_fuzzy_phrase_query(self, query: SearchQuery) -> Dict[str, Any]:
        """Build fuzzy phrase query"""
        config = query.fuzzy_config
        slop = config.slop if config else 2
        
        return self.fuzzy_service.build_fuzzy_phrase_query(
            query.query,
            fields=self._get_search_fields(),
            slop=slop
        )
    
    def _build_fuzzy_cross_field_query(self, query: SearchQuery) -> Dict[str, Any]:
        """Build fuzzy cross-field query"""
        return self.fuzzy_service.build_cross_field_fuzzy_query(
            query.query,
            fields=self._get_search_fields()
        )
    
    def _build_main_query(self, query_text: str, search_type: SearchType) -> Dict[str, Any]:
        """Build the main query based on search type"""
        if search_type == SearchType.PHRASE:
            return {
                "match_phrase": {
                    "_all": {
                        "query": query_text,
                        "slop": 2
                    }
                }
            }
        elif search_type == SearchType.FUZZY:
            return {
                "fuzzy": {
                    "_all": {
                        "value": query_text,
                        "fuzziness": "AUTO"
                    }
                }
            }
        elif search_type == SearchType.WILDCARD:
            return {
                "wildcard": {
                    "_all": {
                        "value": f"*{query_text}*",
                        "case_insensitive": True
                    }
                }
            }
        else:  # BASIC search
            return {
                "multi_match": {
                    "query": query_text,
                    "fields": self._get_search_fields(),
                    "type": "best_fields",
                    "operator": "OR",
                    "fuzziness": "AUTO"
                }
            }
    
    def _build_highlight_config(self) -> Dict[str, Any]:
        """Build highlighting configuration for search results"""
        return {
            "fields": {
                "*": {
                    "fragment_size": 150,
                    "number_of_fragments": 3,
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"]
                }
            },
            "encoder": "html"
        }
    
    async def _process_filtered_search_response(
        self,
        response: Dict[str, Any],
        query: FilteredSearchQuery,
        took_ms: int
    ) -> FilteredSearchResponse:
        """Process OpenSearch response into FilteredSearchResponse"""
        # Extract hits
        hits = []
        for hit in response.get("hits", {}).get("hits", []):
            search_hit = SearchHit(
                id=hit["_id"],
                index=hit["_index"],
                score=hit.get("_score", 0.0),
                source=hit["_source"] if query.include_source else {},
                highlight=hit.get("highlight", {}) if query.highlight else None
            )
            hits.append(search_hit)
        
        # Apply custom ranking if available
        if self.ranking_service and hits and not query.sort_by:
            hits = await self.ranking_service.rank_results(
                hits,
                query.query,
                query.ranking_config
            )
        
        # Parse facets
        facets = None
        if "aggregations" in response and query.facets is not None:
            facets = self.facet_service.parse_aggregation_results(
                response["aggregations"],
                query.facets
            )
        elif "aggregations" in response and query.facets is None:
            # Parse default facets
            default_facets = self.facet_service.get_default_facets()
            facets = self.facet_service.parse_aggregation_results(
                response["aggregations"],
                default_facets
            )
        
        # Calculate pagination
        total_hits = response.get("hits", {}).get("total", {}).get("value", 0)
        current_page = (query.from_ // query.size) + 1
        total_pages = max(1, (total_hits + query.size - 1) // query.size)
        
        return FilteredSearchResponse(
            query=query.query,
            total_hits=total_hits,
            max_score=response.get("hits", {}).get("max_score"),
            hits=hits,
            facets=facets,
            applied_filters=query.filters,
            took=took_ms,
            timed_out=response.get("timed_out", False),
            page=current_page,
            per_page=query.size,
            total_pages=total_pages
        )
    
    async def fuzzy_search(self, query: FuzzySearchQuery) -> FuzzySearchResponse:
        """
        Perform advanced fuzzy search with configurable parameters
        
        Args:
            query: Fuzzy search query parameters
            
        Returns:
            FuzzySearchResponse with results and fuzzy-specific metadata
        """
        try:
            start_time = time.time()
            
            # Convert fuzzy query to fuzzy service format
            from .fuzzy_service import FuzzyConfig, FuzzinessType as FuzzyFuzzinessType
            
            fuzzy_config = FuzzyConfig(
                fuzziness=FuzzyFuzzinessType(query.fuzziness.value),
                prefix_length=query.prefix_length,
                max_expansions=query.max_expansions,
                transpositions=query.transpositions,
                boost=1.0
            )
            
            # Get performance mode config
            if query.performance_mode in ["strict", "moderate", "loose"]:
                performance_config = self.fuzzy_service.get_fuzzy_config(query.performance_mode)
                fuzzy_config.fuzziness = performance_config.fuzziness
                fuzzy_config.prefix_length = performance_config.prefix_length
                fuzzy_config.max_expansions = performance_config.max_expansions
            
            # Build fuzzy query
            fields = query.fields or self._get_search_fields()
            
            if query.match_type == FuzzyMatchType.ADAPTIVE:
                main_query = self.fuzzy_service.build_adaptive_fuzzy_query(
                    query.query, 
                    fields=fields,
                    match_type=query.match_type
                )
            elif query.match_type == FuzzyMatchType.CROSS_FIELD:
                main_query = self.fuzzy_service.build_cross_field_fuzzy_query(
                    query.query,
                    fields=fields,
                    config=fuzzy_config
                )
            elif query.match_type == FuzzyMatchType.PHRASE:
                main_query = self.fuzzy_service.build_fuzzy_phrase_query(
                    query.query,
                    fields=fields,
                    slop=query.slop,
                    config=fuzzy_config
                )
            elif query.match_type == FuzzyMatchType.MULTI_TERM:
                terms = query.query.split()
                main_query = self.fuzzy_service.build_multi_term_fuzzy_query(
                    terms,
                    fields=fields,
                    config=fuzzy_config
                )
            else:  # SINGLE_TERM
                main_query = self.fuzzy_service.build_single_term_fuzzy_query(
                    query.query,
                    "_all",
                    fuzzy_config
                )
            
            # Build search body
            body = {
                "size": query.size,
                "from": query.from_,
                "track_total_hits": True,
                "query": main_query
            }
            
            # Add sorting
            if query.sort_by:
                body["sort"] = [{
                    query.sort_by: {"order": query.sort_order.value}
                }]
            else:
                body["sort"] = ["_score", {"created_at": {"order": "desc", "missing": "_last"}}]
            
            # Add highlighting
            if query.highlight:
                body["highlight"] = {
                    "fields": {
                        "*": {
                            "fragment_size": 150,
                            "number_of_fragments": 3,
                            "pre_tags": ["<mark>"],
                            "post_tags": ["</mark>"]
                        }
                    },
                    "encoder": "html"
                }
            
            # Add fuzzy suggestions if requested
            if query.include_suggestions:
                suggestion_query = self.fuzzy_service.build_fuzzy_suggestion_query(
                    query.query,
                    field="_all",
                    config=fuzzy_config
                )
                body.update(suggestion_query)
            
            # Determine indices to search
            indices = self._get_search_indices(query.indices)
            
            logger.info(
                "executing_fuzzy_search",
                query=query.query,
                match_type=query.match_type,
                fuzziness=query.fuzziness,
                performance_mode=query.performance_mode,
                indices=indices
            )
            
            # Execute search
            response = await self.client.search(
                index=indices,
                body=body,
                timeout=f"{self.settings.search_timeout}s"
            )
            
            # Process response
            search_response = await self._process_fuzzy_search_response(
                response,
                query,
                fuzzy_config,
                int((time.time() - start_time) * 1000)
            )
            
            logger.info(
                "fuzzy_search_completed",
                query=query.query,
                match_type=query.match_type,
                total_hits=search_response.total_hits,
                took_ms=search_response.took
            )
            
            return search_response
            
        except OpenSearchConnectionError as e:
            logger.error("fuzzy_search_connection_error", error=str(e))
            raise SearchError("Failed to connect to search service")
        except RequestError as e:
            logger.error("fuzzy_search_request_error", error=str(e))
            raise InvalidQueryError(f"Invalid fuzzy search query: {str(e)}")
        except Exception as e:
            logger.error("fuzzy_search_failed", error=str(e))
            raise SearchError(f"Fuzzy search operation failed: {str(e)}")
    
    async def _process_fuzzy_search_response(
        self,
        response: Dict[str, Any],
        query: FuzzySearchQuery,
        fuzzy_config,
        took_ms: int
    ) -> FuzzySearchResponse:
        """Process OpenSearch response into FuzzySearchResponse"""
        # Extract hits
        hits = []
        for hit in response.get("hits", {}).get("hits", []):
            search_hit = SearchHit(
                id=hit["_id"],
                index=hit["_index"],
                score=hit.get("_score", 0.0),
                source=hit["_source"],
                highlight=hit.get("highlight", {}) if query.highlight else None
            )
            hits.append(search_hit)
        
        # Extract suggestions if requested
        suggestions = None
        if query.include_suggestions and "suggest" in response:
            suggestions = []
            for suggest_name, suggest_results in response["suggest"].items():
                for result in suggest_results:
                    for option in result.get("options", []):
                        suggestions.append({
                            "text": option["text"],
                            "score": option["score"],
                            "freq": option.get("freq", 0)
                        })
        
        # Generate performance info if requested
        performance_info = None
        if query.include_performance_info:
            performance_info = self.fuzzy_service.estimate_fuzzy_performance(
                query.query, 
                fuzzy_config
            )
        
        # Generate query analysis
        query_analysis = self.fuzzy_service._analyze_query(query.query)
        
        # Calculate pagination
        total_hits = response.get("hits", {}).get("total", {}).get("value", 0)
        current_page = (query.from_ // query.size) + 1
        total_pages = max(1, (total_hits + query.size - 1) // query.size)
        
        return FuzzySearchResponse(
            query=query.query,
            match_type=query.match_type,
            fuzziness=query.fuzziness,
            total_hits=total_hits,
            max_score=response.get("hits", {}).get("max_score"),
            hits=hits,
            suggestions=suggestions,
            performance_info=performance_info,
            took=took_ms,
            timed_out=response.get("timed_out", False),
            page=current_page,
            per_page=query.size,
            total_pages=total_pages,
            query_analysis=query_analysis
        )
    
    async def phonetic_search(self, query: PhoneticSearchQuery) -> PhoneticSearchResponse:
        """
        Perform phonetic search using the phonetic service
        
        Args:
            query: Phonetic search query parameters
            
        Returns:
            PhoneticSearchResponse with results and metadata
        """
        return await self.phonetic_service.phonetic_search(query)
    
    async def phonetic_suggestions(self, query: PhoneticSuggestionQuery) -> PhoneticSuggestionResponse:
        """
        Get phonetic suggestions using the phonetic service
        
        Args:
            query: Phonetic suggestion query parameters
            
        Returns:
            PhoneticSuggestionResponse with suggestions and metadata
        """
        return await self.phonetic_service.phonetic_suggestions(query)
    
    async def synonym_search(self, query: SynonymSearchQuery) -> SynonymSearchResponse:
        """
        Perform synonym-enhanced search using the synonym service
        
        Args:
            query: Synonym search query parameters
            
        Returns:
            SynonymSearchResponse with results and metadata
        """
        return await self.synonym_service.synonym_search(query)
    
    async def synonym_suggestions(self, query: SynonymSuggestionQuery) -> SynonymSuggestionResponse:
        """
        Get synonym suggestions using the synonym service
        
        Args:
            query: Synonym suggestion query parameters
            
        Returns:
            SynonymSuggestionResponse with suggestions and metadata
        """
        return await self.synonym_service.get_synonym_suggestions(query)


async def get_search_service() -> SearchService:
    """Get search service instance"""
    client = await get_opensearch_client()
    ranking_service = await get_ranking_service()
    return SearchService(client, ranking_service)
"""
API routes for the Search Engine Service
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Request
from typing import List, Optional, Dict, Any
import structlog
from datetime import datetime

from ..models.schemas import (
    SearchQuery, AdvancedSearchQuery, MetadataFieldSearchQuery, SearchResponse, 
    SuggestionQuery, SuggestionResponse, IndexDocument, BulkIndexRequest, 
    IndexingResponse, BulkIndexingResponse, DeleteResponse, IndexStats, 
    SearchAnalytics, IndexType, FilteredSearchQuery, FilteredSearchResponse,
    SavedSearchCreate, SavedSearchUpdate, SavedSearch, SavedSearchList,
    SavedSearchExecute, SearchHistoryEntry, SearchHistoryList, SearchHistoryStats,
    SearchAnalyticsAggregation, SearchAnalyticsTimeRange, SearchAnalyticsFilter,
    SearchAnalyticsReport, SearchPerformanceMetrics, SearchTrendData,
    FuzzySearchQuery, FuzzySearchResponse, FuzzySuggestionQuery, FuzzySuggestionResponse,
    PhoneticSearchQuery, PhoneticSearchResponse, PhoneticSuggestionQuery, PhoneticSuggestionResponse,
    SynonymSearchQuery, SynonymSearchResponse, SynonymSuggestionQuery, SynonymSuggestionResponse,
    SynonymStats, SearchTemplateCreate, SearchTemplateUpdate, SearchTemplate, SearchTemplateList,
    SearchTemplateExecute, SearchTemplateExecuteResponse, SearchTemplateStats, SearchTemplateExport,
    SearchTemplateImport, SearchTemplateShare, SearchTemplateType, SearchTemplateCategory,
    TimecodeSearchQuery, TimecodeSearchResponse, TimecodeSearchStats, TimecodeValidationResult,
    TimecodeConversionRequest, TimecodeConversionResponse, TimecodeFormat,
    ColorSearchQuery, ColorSearchResponse, ColorSearchStats, ColorAnalysisRequest,
    ColorAnalysisResponse, ColorSpace, ColorSearchType,
    FaceSearchQuery, FaceSearchResponse, FaceSearchStats, FaceAnalysisRequest,
    FaceAnalysisResponse, FaceSearchType, FaceDetectionModel, FaceRecognitionModel,
    ImageSimilarityQuery, ImageSimilarityResponse, ImageSimilarityStats, ImageAnalysisRequest,
    ImageAnalysisResponse, ImageSimilarityType, ImageFeatureModel, SimilarityMetric,
    AudioFingerprintQuery, AudioFingerprintResponse, AudioFingerprintStats,
    AudioAnalysisRequest, AudioAnalysisResponse, AudioFingerprintingAlgorithm,
    AudioFingerprintType, AudioMatchType, AudioSearchType
)
from ..services.search_service import SearchService, get_search_service
from ..services.indexing_service import IndexingService, get_indexing_service
from ..services.suggestion_service import SuggestionService, get_suggestion_service
from ..services.analytics_service import AnalyticsService, get_analytics_service
from ..services.saved_search_service import SavedSearchService, get_saved_search_service
from ..services.search_history_service import SearchHistoryService, get_search_history_service
from ..services.search_analytics_service import SearchAnalyticsService, get_search_analytics_service
from ..services.nlp_search_service import NLPSearchService, get_nlp_search_service
from ..services.search_template_service import SearchTemplateService, get_search_template_service
from ..services.timecode_search_service import TimecodeSearchService, get_timecode_search_service
from ..services.color_search_service import ColorSearchService, get_color_search_service
from ..services.face_search_service import FaceSearchService, get_face_search_service
from ..services.image_similarity_service import ImageSimilarityService, get_image_similarity_service
from ..services.audio_fingerprinting_service import AudioFingerprintingService, get_audio_fingerprinting_service
from ..core.exceptions import SearchError, IndexError, NotFoundError, ValidationError
from .pipeline_routes import router as pipeline_router

logger = structlog.get_logger()
router = APIRouter()

# Include pipeline routes
router.include_router(pipeline_router)


async def get_optional_current_user() -> Optional[Dict[str, Any]]:
    """Get current user (placeholder for authentication integration)"""
    # TODO: Implement actual authentication integration
    return None


async def get_current_user() -> Dict[str, Any]:
    """Get current user (placeholder for authentication integration)"""
    # TODO: Implement actual authentication integration
    # For now, return a mock user
    return {"id": "test-user-123", "username": "testuser", "email": "test@example.com"}


@router.post("/search", response_model=SearchResponse)
async def search(
    query: SearchQuery,
    request: Request,
    search_service: SearchService = Depends(get_search_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> SearchResponse:
    """
    Perform a search across MAMS indices
    
    - **query**: Search query string
    - **search_type**: Type of search (basic, advanced, fuzzy, etc.)
    - **indices**: Which indices to search
    - **filters**: Additional filters to apply
    - **size**: Number of results to return
    - **from**: Offset for pagination
    - **sort_by**: Field to sort by
    - **sort_order**: Sort order (asc/desc)
    - **highlight**: Whether to highlight matches
    """
    try:
        start_time = datetime.utcnow()
        
        logger.info(
            "search_request_received",
            query=query.query,
            search_type=query.search_type,
            indices=query.indices,
            size=query.size,
            from_=query.from_
        )
        
        result = await search_service.search(query)
        
        # Log search analytics
        response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        analytics_data = SearchAnalytics(
            query=query.query,
            results_count=result.total_hits,
            response_time_ms=response_time,
            filters_used=query.filters
        )
        
        # Don't await analytics logging to avoid slowing down response
        try:
            analytics_service = await get_analytics_service()
            await analytics_service.log_search(analytics_data)
        except Exception as e:
            logger.warning("analytics_logging_failed", error=str(e))
        
        # Log search to history if user is authenticated
        if current_user:
            try:
                search_history_service = await get_search_history_service()
                request_info = search_history_service.extract_request_info(request)
                
                await search_history_service.log_search(
                    user_id=current_user["id"],
                    query=query.query,
                    search_type=query.search_type,
                    indices=query.indices,
                    filters=query.filters,
                    results_count=result.total_hits,
                    response_time_ms=response_time,
                    ip_address=request_info.get("ip_address"),
                    user_agent=request_info.get("user_agent")
                )
            except Exception as e:
                logger.warning("search_history_logging_failed", error=str(e))
        
        # Log search analytics (for both authenticated and anonymous users)
        try:
            search_analytics_service = await get_search_analytics_service()
            session_info = search_analytics_service.extract_session_info(request)
            
            await search_analytics_service.log_search_analytics(
                query=query.query,
                search_type=query.search_type,
                user_id=current_user["id"] if current_user else None,
                session_id=session_info.get("session_id"),
                indices=query.indices,
                filters=query.filters,
                results_count=result.total_hits,
                response_time_ms=response_time,
                ip_address=session_info.get("ip_address"),
                user_agent=session_info.get("user_agent"),
                referrer=session_info.get("referrer")
            )
        except Exception as e:
            logger.warning("search_analytics_logging_failed", error=str(e))
        
        logger.info(
            "search_request_completed",
            query=query.query,
            total_hits=result.total_hits,
            response_time_ms=response_time
        )
        
        return result
        
    except SearchError as e:
        logger.error("search_request_failed", error=str(e), query=query.query)
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("search_request_error", error=str(e), query=query.query)
        raise HTTPException(status_code=500, detail="Internal search error")


@router.post("/search/advanced", response_model=SearchResponse)
async def advanced_search(
    query: AdvancedSearchQuery,
    search_service: SearchService = Depends(get_search_service)
) -> SearchResponse:
    """
    Perform an advanced search with complex query conditions
    
    - **must**: Conditions that must match
    - **should**: Conditions that should match (boost relevance)
    - **must_not**: Conditions that must not match
    - **filters**: Filter conditions
    """
    try:
        logger.info("advanced_search_request_received")
        
        result = await search_service.advanced_search(query)
        
        logger.info(
            "advanced_search_completed",
            total_hits=result.total_hits
        )
        
        return result
        
    except SearchError as e:
        logger.error("advanced_search_failed", error=str(e))
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("advanced_search_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal search error")


@router.post("/search/metadata-fields", response_model=SearchResponse)
async def metadata_field_search(
    query: MetadataFieldSearchQuery,
    search_service: SearchService = Depends(get_search_service)
) -> SearchResponse:
    """
    Perform a search on specific metadata fields
    
    - **field_queries**: List of field-value pairs to search
    - **operator**: How to combine field queries (AND/OR)
    - **indices**: Which indices to search (defaults to metadata index)
    - **filters**: Additional filters to apply
    - **fuzzy**: Enable fuzzy matching for typo tolerance
    - **boost_fields**: Field boosting weights for relevance tuning
    
    Example:
    ```json
    {
        "field_queries": [
            {"field": "title", "value": "video"},
            {"field": "keywords", "value": "test"}
        ],
        "operator": "AND",
        "fuzzy": true,
        "boost_fields": {"title": 2.0}
    }
    ```
    """
    try:
        logger.info(
            "metadata_field_search_request",
            field_count=len(query.field_queries),
            operator=query.operator,
            fuzzy=query.fuzzy
        )
        
        result = await search_service.metadata_field_search(query)
        
        # Log search analytics
        analytics_data = SearchAnalytics(
            query=f"Metadata field search: {query.operator}",
            results_count=result.total_hits,
            response_time_ms=result.took,
            filters_used=query.filters
        )
        
        try:
            analytics_service = await get_analytics_service()
            await analytics_service.log_search(analytics_data)
        except Exception as e:
            logger.warning("analytics_logging_failed", error=str(e))
        
        logger.info(
            "metadata_field_search_completed",
            total_hits=result.total_hits,
            took_ms=result.took
        )
        
        return result
        
    except SearchError as e:
        logger.error("metadata_field_search_failed", error=str(e))
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("metadata_field_search_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal search error")


@router.post("/search/natural-language", response_model=FilteredSearchResponse)
async def natural_language_search(
    query: str,
    size: int = Query(default=20, ge=1, le=100, description="Number of results to return"),
    from_: int = Query(default=0, ge=0, description="Offset for pagination", alias="from"),
    request: Request = None,
    search_service: SearchService = Depends(get_search_service),
    nlp_service: NLPSearchService = Depends(get_nlp_search_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> FilteredSearchResponse:
    """
    Perform a natural language search with AI-powered query understanding
    
    This endpoint accepts natural language queries and automatically:
    - Detects search intent
    - Extracts entities (people, dates, projects, etc.)
    - Applies appropriate filters
    - Optimizes the search query
    
    Examples:
    - "Find all videos from last week"
    - "Show me images tagged as nature from project Summer Campaign"
    - "Recent 4K videos longer than 5 minutes"
    - "Documents created by John Smith in the last month"
    - "Audio files in MP3 format from yesterday"
    
    - **query**: Natural language search query
    - **size**: Number of results to return
    - **from**: Offset for pagination
    """
    try:
        start_time = datetime.utcnow()
        
        logger.info(
            "natural_language_search_request",
            query=query,
            size=size,
            from_=from_
        )
        
        # Parse the natural language query
        parsed_query = await nlp_service.parse_natural_language_query(query)
        
        logger.info(
            "natural_language_query_parsed",
            original_query=query,
            intent=parsed_query.intent.value,
            keywords=parsed_query.keywords,
            entity_count=len(parsed_query.entities),
            filter_count=len(parsed_query.filters),
            confidence=parsed_query.confidence
        )
        
        # Convert to structured search query
        search_query = await nlp_service.convert_to_search_query(parsed_query)
        
        # Update pagination from request
        search_query.size = size
        search_query.from_ = from_
        
        # Perform the search
        result = await search_service.filtered_search(search_query)
        
        # Add NLP parsing info to response metadata
        if result.metadata is None:
            result.metadata = {}
        
        result.metadata["nlp_parsed"] = {
            "intent": parsed_query.intent.value,
            "entities": parsed_query.entities,
            "keywords": parsed_query.keywords,
            "confidence": parsed_query.confidence,
            "extracted_filters": len(parsed_query.filters),
            "temporal_filters": len(parsed_query.temporal_filters),
            "technical_filters": len(parsed_query.technical_filters)
        }
        
        # Log analytics
        response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Log to search history if authenticated
        if current_user:
            try:
                search_history_service = await get_search_history_service()
                request_info = search_history_service.extract_request_info(request)
                
                await search_history_service.log_search(
                    user_id=current_user["id"],
                    query=query,
                    search_type="natural_language",
                    indices=search_query.indices,
                    filters=search_query.filters,
                    results_count=result.total_hits,
                    response_time_ms=response_time,
                    ip_address=request_info.get("ip_address"),
                    user_agent=request_info.get("user_agent"),
                    metadata={
                        "nlp_intent": parsed_query.intent.value,
                        "nlp_confidence": parsed_query.confidence
                    }
                )
            except Exception as e:
                logger.warning("search_history_logging_failed", error=str(e))
        
        # Log search analytics
        try:
            search_analytics_service = await get_search_analytics_service()
            session_info = search_analytics_service.extract_session_info(request)
            
            await search_analytics_service.log_search_analytics(
                query=query,
                search_type="natural_language",
                user_id=current_user["id"] if current_user else None,
                session_id=session_info.get("session_id"),
                indices=search_query.indices,
                filters=search_query.filters,
                results_count=result.total_hits,
                response_time_ms=response_time,
                ip_address=session_info.get("ip_address"),
                user_agent=session_info.get("user_agent"),
                referrer=session_info.get("referrer"),
                metadata={
                    "nlp_intent": parsed_query.intent.value,
                    "nlp_confidence": parsed_query.confidence,
                    "extracted_entities": list(parsed_query.entities.keys())
                }
            )
        except Exception as e:
            logger.warning("search_analytics_logging_failed", error=str(e))
        
        logger.info(
            "natural_language_search_completed",
            query=query,
            total_hits=result.total_hits,
            response_time_ms=response_time,
            nlp_confidence=parsed_query.confidence
        )
        
        return result
        
    except SearchError as e:
        logger.error("natural_language_search_failed", error=str(e), query=query)
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("natural_language_search_error", error=str(e), query=query)
        raise HTTPException(status_code=500, detail="Failed to process natural language query")


@router.get("/search/suggestions", response_model=SuggestionResponse)
async def get_suggestions(
    query: SuggestionQuery = Depends(),
    suggestion_service: SuggestionService = Depends(get_suggestion_service)
) -> SuggestionResponse:
    """
    Get search suggestions for auto-completion
    
    - **text**: Text to get suggestions for
    - **size**: Number of suggestions to return
    - **index_type**: Which index to search for suggestions
    """
    try:
        logger.info("suggestions_request_received", text=query.text)
        
        result = await suggestion_service.get_suggestions(query)
        
        logger.info(
            "suggestions_completed",
            text=query.text,
            suggestion_count=len(result.suggestions)
        )
        
        return result
        
    except Exception as e:
        logger.error("suggestions_error", error=str(e), text=query.text)
        raise HTTPException(status_code=500, detail="Failed to get suggestions")


@router.post("/index/document", response_model=IndexingResponse)
async def index_document(
    document: IndexDocument,
    indexing_service: IndexingService = Depends(get_indexing_service)
) -> IndexingResponse:
    """
    Index a single document
    
    - **id**: Document ID
    - **document**: Document data to index
    - **index_name**: Target index (optional, auto-detected if not provided)
    """
    try:
        logger.info("index_document_request", document_id=document.id)
        
        result = await indexing_service.index_document(document)
        
        logger.info(
            "document_indexed",
            document_id=document.id,
            index_name=result.index_name,
            result=result.result
        )
        
        return result
        
    except IndexError as e:
        logger.error("indexing_failed", error=str(e), document_id=document.id)
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("indexing_error", error=str(e), document_id=document.id)
        raise HTTPException(status_code=500, detail="Failed to index document")


@router.post("/index/bulk", response_model=BulkIndexingResponse)
async def bulk_index_documents(
    request: BulkIndexRequest,
    indexing_service: IndexingService = Depends(get_indexing_service)
) -> BulkIndexingResponse:
    """
    Index multiple documents in bulk
    
    - **documents**: List of documents to index
    - **refresh**: Whether to refresh indices after indexing
    """
    try:
        logger.info("bulk_index_request", document_count=len(request.documents))
        
        result = await indexing_service.bulk_index_documents(request)
        
        logger.info(
            "bulk_indexing_completed",
            total_documents=result.total_documents,
            successful_count=result.successful_count,
            failed_count=result.failed_count
        )
        
        return result
        
    except IndexError as e:
        logger.error("bulk_indexing_failed", error=str(e))
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("bulk_indexing_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to bulk index documents")


@router.delete("/index/document/{index_name}/{document_id}", response_model=DeleteResponse)
async def delete_document(
    index_name: str = Path(..., description="Index name"),
    document_id: str = Path(..., description="Document ID"),
    indexing_service: IndexingService = Depends(get_indexing_service)
) -> DeleteResponse:
    """
    Delete a document from an index
    
    - **index_name**: Name of the index
    - **document_id**: ID of the document to delete
    """
    try:
        logger.info("delete_document_request", index_name=index_name, document_id=document_id)
        
        result = await indexing_service.delete_document(index_name, document_id)
        
        logger.info(
            "document_deleted",
            index_name=index_name,
            document_id=document_id,
            result=result.result
        )
        
        return result
        
    except IndexError as e:
        logger.error("delete_failed", error=str(e), document_id=document_id)
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("delete_error", error=str(e), document_id=document_id)
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.get("/indices/stats", response_model=List[IndexStats])
async def get_indices_stats(
    indexing_service: IndexingService = Depends(get_indexing_service)
) -> List[IndexStats]:
    """
    Get statistics for all indices
    """
    try:
        logger.info("indices_stats_request")
        
        stats = await indexing_service.get_indices_stats()
        
        logger.info("indices_stats_completed", index_count=len(stats))
        
        return stats
        
    except Exception as e:
        logger.error("indices_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get indices stats")


@router.get("/indices/{index_name}/stats", response_model=IndexStats)
async def get_index_stats(
    index_name: str = Path(..., description="Index name"),
    indexing_service: IndexingService = Depends(get_indexing_service)
) -> IndexStats:
    """
    Get statistics for a specific index
    
    - **index_name**: Name of the index
    """
    try:
        logger.info("index_stats_request", index_name=index_name)
        
        stats = await indexing_service.get_index_stats(index_name)
        
        logger.info("index_stats_completed", index_name=index_name)
        
        return stats
        
    except IndexError as e:
        logger.error("index_stats_failed", error=str(e), index_name=index_name)
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("index_stats_error", error=str(e), index_name=index_name)
        raise HTTPException(status_code=500, detail="Failed to get index stats")


@router.post("/indices/{index_name}/refresh")
async def refresh_index(
    index_name: str = Path(..., description="Index name"),
    indexing_service: IndexingService = Depends(get_indexing_service)
):
    """
    Refresh an index to make recent changes searchable
    
    - **index_name**: Name of the index to refresh
    """
    try:
        logger.info("refresh_index_request", index_name=index_name)
        
        await indexing_service.refresh_index(index_name)
        
        logger.info("index_refreshed", index_name=index_name)
        
        return {"message": f"Index {index_name} refreshed successfully"}
        
    except IndexError as e:
        logger.error("refresh_failed", error=str(e), index_name=index_name)
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("refresh_error", error=str(e), index_name=index_name)
        raise HTTPException(status_code=500, detail="Failed to refresh index")


@router.get("/analytics/popular-queries")
async def get_popular_queries(
    limit: int = Query(default=10, ge=1, le=100, description="Number of queries to return"),
    days: int = Query(default=7, ge=1, le=30, description="Number of days to look back"),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> List[Dict[str, Any]]:
    """
    Get popular search queries
    
    - **limit**: Number of queries to return
    - **days**: Number of days to analyze
    """
    try:
        logger.info("popular_queries_request", limit=limit, days=days)
        
        queries = await analytics_service.get_popular_queries(limit, days)
        
        logger.info("popular_queries_completed", query_count=len(queries))
        
        return queries
        
    except Exception as e:
        logger.error("popular_queries_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get popular queries")


@router.get("/analytics/search-trends")
async def get_search_trends(
    days: int = Query(default=7, ge=1, le=30, description="Number of days to analyze"),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> Dict[str, Any]:
    """
    Get search trends and statistics
    
    - **days**: Number of days to analyze
    """
    try:
        logger.info("search_trends_request", days=days)
        
        trends = await analytics_service.get_search_trends(days)
        
        logger.info("search_trends_completed")
        
        return trends
        
    except Exception as e:
        logger.error("search_trends_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get search trends")


@router.post("/search/filtered", response_model=FilteredSearchResponse)
async def filtered_search(
    query: FilteredSearchQuery,
    request: Request,
    search_service: SearchService = Depends(get_search_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> FilteredSearchResponse:
    """
    Perform search with advanced filtering and faceting capabilities
    
    This endpoint provides enhanced search functionality with:
    
    - **Advanced Filtering**: Apply multiple filter conditions using various filter types
    - **Faceted Search**: Get aggregated counts for different fields to enable drill-down
    - **Post-Filters**: Apply filters that don't affect facet counts
    - **Custom Ranking**: Configure how results are ranked and sorted
    
    ## Filter Types Supported:
    - `term`: Exact match on a field
    - `terms`: Match any of multiple values
    - `range`: Numeric or date range filtering
    - `exists`: Check if field exists
    - `prefix`: Match field values starting with prefix
    - `wildcard`: Pattern matching with * and ?
    - `regexp`: Regular expression matching
    - `nested`: Filter on nested object fields
    
    ## Facet Types Supported:
    - `terms`: Count occurrences of distinct values
    - `range`: Count documents in numeric/date ranges
    - `date_histogram`: Count documents by time intervals
    - `histogram`: Count documents in numeric intervals
    - `stats`: Get min, max, avg, sum statistics
    - `cardinality`: Count distinct values
    
    ## Example Request:
    ```json
    {
        "query": "marketing video",
        "filters": [
            {
                "field": "asset_type",
                "type": "term",
                "value": "video"
            },
            {
                "field": "duration",
                "type": "range",
                "value": {"gte": 60, "lte": 300}
            }
        ],
        "facets": [
            {
                "name": "file_types",
                "field": "file_extension",
                "type": "terms",
                "size": 20
            },
            {
                "name": "date_ranges",
                "field": "created_at",
                "type": "date_histogram",
                "interval": "month"
            }
        ],
        "size": 20,
        "from": 0,
        "sort_by": "created_at",
        "sort_order": "desc"
    }
    ```
    """
    try:
        start_time = datetime.utcnow()
        
        logger.info(
            "filtered_search_request_received",
            query=query.query,
            search_type=query.search_type,
            indices=query.indices,
            filter_count=len(query.filters or []),
            post_filter_count=len(query.post_filters or []),
            facet_count=len(query.facets or []),
            size=query.size,
            from_=query.from_
        )
        
        result = await search_service.filtered_search(query)
        
        # Log search analytics
        response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        analytics_data = SearchAnalytics(
            query=query.query,
            results_count=result.total_hits,
            response_time_ms=response_time,
            filters_used={f.field: f.value for f in (query.filters or [])}
        )
        
        # Don't await analytics logging to avoid slowing down response
        try:
            analytics_service = await get_analytics_service()
            await analytics_service.log_search(analytics_data)
        except Exception as e:
            logger.warning("analytics_logging_failed", error=str(e))
        
        # Log search to history if user is authenticated
        if current_user:
            try:
                search_history_service = await get_search_history_service()
                request_info = search_history_service.extract_request_info(request)
                
                await search_history_service.log_search(
                    user_id=current_user["id"],
                    query=query.query,
                    search_type=query.search_type,
                    indices=query.indices,
                    filters={f.field: f.value for f in (query.filters or [])},
                    results_count=result.total_hits,
                    response_time_ms=response_time,
                    ip_address=request_info.get("ip_address"),
                    user_agent=request_info.get("user_agent")
                )
            except Exception as e:
                logger.warning("search_history_logging_failed", error=str(e))
        
        # Log search analytics (for both authenticated and anonymous users)
        try:
            search_analytics_service = await get_search_analytics_service()
            session_info = search_analytics_service.extract_session_info(request)
            
            await search_analytics_service.log_search_analytics(
                query=query.query,
                search_type=query.search_type,
                user_id=current_user["id"] if current_user else None,
                session_id=session_info.get("session_id"),
                indices=query.indices,
                filters={f.field: f.value for f in (query.filters or [])},
                results_count=result.total_hits,
                response_time_ms=response_time,
                ip_address=session_info.get("ip_address"),
                user_agent=session_info.get("user_agent"),
                referrer=session_info.get("referrer")
            )
        except Exception as e:
            logger.warning("search_analytics_logging_failed", error=str(e))
        
        logger.info(
            "filtered_search_request_completed",
            query=query.query,
            total_hits=result.total_hits,
            facet_results=len(result.facets or []),
            response_time_ms=response_time
        )
        
        return result
        
    except SearchError as e:
        logger.error("filtered_search_request_failed", error=str(e), query=query.query)
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("filtered_search_request_error", error=str(e), query=query.query)
        raise HTTPException(status_code=500, detail="Internal search error")


@router.post("/search/fuzzy", response_model=FuzzySearchResponse)
async def fuzzy_search(
    query: FuzzySearchQuery,
    request: Request,
    search_service: SearchService = Depends(get_search_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> FuzzySearchResponse:
    """
    Perform advanced fuzzy search with configurable parameters
    
    This endpoint provides sophisticated fuzzy matching capabilities with:
    - Multiple fuzzy matching algorithms (single_term, multi_term, phrase, cross_field, adaptive)
    - Configurable fuzziness levels (AUTO, 1, 2, 3, custom)
    - Performance modes (strict, moderate, loose)
    - Field-specific matching with custom boosts
    - Fuzzy suggestions and performance analysis
    
    Examples:
    - Fix typos: "vidoe" → "video"
    - Handle variations: "colour" → "color"
    - Phonetic matching: "smith" → "smyth"
    - Partial matching: "docu" → "document"
    
    - **query**: Text to search for (can contain typos)
    - **match_type**: Type of fuzzy matching (adaptive, single_term, multi_term, phrase, cross_field)
    - **fuzziness**: Fuzziness algorithm (AUTO, 1, 2, 3, 0.5)
    - **performance_mode**: Performance vs accuracy trade-off (strict, moderate, loose)
    - **fields**: Specific fields to search (optional)
    - **include_suggestions**: Include fuzzy suggestions
    - **include_performance_info**: Include performance analysis
    """
    try:
        start_time = datetime.utcnow()
        
        logger.info(
            "fuzzy_search_request",
            query=query.query,
            match_type=query.match_type,
            fuzziness=query.fuzziness,
            performance_mode=query.performance_mode,
            size=query.size,
            from_=query.from_
        )
        
        # Execute fuzzy search
        result = await search_service.fuzzy_search(query)
        
        # Log search analytics
        response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        analytics_data = SearchAnalytics(
            query=query.query,
            results_count=result.total_hits,
            response_time_ms=response_time,
            filters_used={"match_type": query.match_type.value, "fuzziness": query.fuzziness.value}
        )
        
        # Don't await analytics logging to avoid slowing down response
        try:
            analytics_service = await get_analytics_service()
            await analytics_service.log_search(analytics_data)
        except Exception as e:
            logger.warning("analytics_logging_failed", error=str(e))
        
        # Log search to history if user is authenticated
        if current_user:
            try:
                search_history_service = await get_search_history_service()
                request_info = search_history_service.extract_request_info(request)
                
                await search_history_service.log_search(
                    user_id=current_user["id"],
                    query=query.query,
                    search_type="fuzzy",
                    indices=[idx.value for idx in query.indices],
                    filters={"match_type": query.match_type.value, "fuzziness": query.fuzziness.value},
                    results_count=result.total_hits,
                    response_time_ms=response_time,
                    **request_info
                )
            except Exception as e:
                logger.warning("search_history_logging_failed", error=str(e))
        
        logger.info(
            "fuzzy_search_completed",
            query=query.query,
            match_type=query.match_type,
            total_hits=result.total_hits,
            took_ms=result.took
        )
        
        return result
        
    except SearchError as e:
        logger.error("fuzzy_search_error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except ValidationError as e:
        logger.error("fuzzy_search_validation_error", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("fuzzy_search_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal fuzzy search error")


@router.post("/search/fuzzy/suggestions", response_model=FuzzySuggestionResponse)
async def fuzzy_suggestions(
    query: FuzzySuggestionQuery,
    search_service: SearchService = Depends(get_search_service)
) -> FuzzySuggestionResponse:
    """
    Get fuzzy suggestions for search terms
    
    This endpoint provides intelligent search suggestions using fuzzy matching to:
    - Suggest corrections for misspelled terms
    - Provide alternative spellings and variations
    - Suggest popular terms based on usage patterns
    - Include recent terms from search history
    
    - **text**: Text to get suggestions for
    - **field**: Field to search for suggestions (default: all fields)
    - **size**: Number of suggestions to return
    - **fuzziness**: Fuzziness algorithm for suggestions
    - **include_popular**: Include popular suggestions
    - **include_recent**: Include recent suggestions
    """
    try:
        start_time = datetime.utcnow()
        
        logger.info(
            "fuzzy_suggestions_request",
            text=query.text,
            field=query.field,
            size=query.size,
            fuzziness=query.fuzziness
        )
        
        # Build fuzzy suggestion query
        from ..services.fuzzy_service import FuzzyConfig, FuzzinessType as FuzzyFuzzinessType
        
        fuzzy_config = FuzzyConfig(
            fuzziness=FuzzyFuzzinessType(query.fuzziness.value),
            prefix_length=1,
            max_expansions=50
        )
        
        # Get search service's fuzzy service
        suggestion_query = search_service.fuzzy_service.build_fuzzy_suggestion_query(
            query.text,
            field=query.field,
            size=query.size,
            config=fuzzy_config
        )
        
        # Execute suggestion query
        indices = search_service.index_mappings[IndexType.ALL]
        response = await search_service.client.search(
            index=indices,
            body=suggestion_query
        )
        
        # Process suggestions
        suggestions = []
        if "suggest" in response:
            for suggest_name, suggest_results in response["suggest"].items():
                for result in suggest_results:
                    for option in result.get("options", []):
                        suggestions.append({
                            "text": option["text"],
                            "score": option["score"],
                            "freq": option.get("freq", 0),
                            "highlighted": option.get("highlighted", option["text"])
                        })
        
        # Sort suggestions by score
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        suggestions = suggestions[:query.size]
        
        response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        logger.info(
            "fuzzy_suggestions_completed",
            text=query.text,
            suggestion_count=len(suggestions),
            took_ms=response_time
        )
        
        return FuzzySuggestionResponse(
            text=query.text,
            suggestions=suggestions,
            took=response_time,
            metadata={
                "field": query.field,
                "fuzziness": query.fuzziness.value,
                "total_suggestions": len(suggestions)
            }
        )
        
    except Exception as e:
        logger.error("fuzzy_suggestions_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal fuzzy suggestions error")


# Phonetic Search Endpoints

@router.post("/search/phonetic", response_model=PhoneticSearchResponse)
async def phonetic_search(
    query: PhoneticSearchQuery,
    request: Request,
    search_service: SearchService = Depends(get_search_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> PhoneticSearchResponse:
    """
    Perform phonetic search for sound-alike matching
    
    This endpoint provides sophisticated phonetic matching capabilities using:
    - Multiple phonetic algorithms (Soundex, Metaphone, NYSIIS, Phonex, etc.)
    - Sound-based matching for names, places, and words
    - Configurable matching types (single_term, multi_term, phrase, cross_field, adaptive)
    - Fallback to regular search if no phonetic matches found
    - Phonetic suggestions and analysis
    
    Perfect for:
    - Searching names with uncertain spelling
    - Finding similar-sounding words
    - Handling pronunciation-based queries
    - Cross-language name matching
    
    Parameters:
    - **query**: The search query text
    - **algorithm**: Phonetic algorithm (soundex, metaphone, nysiis, phonex, etc.)
    - **match_type**: Type of phonetic matching (adaptive, single_term, multi_term, phrase, cross_field)
    - **fields**: Specific fields to search (optional)
    - **boost_exact_matches**: Boost factor for exact matches (default: 2.0)
    - **boost_phonetic_matches**: Boost factor for phonetic matches (default: 1.0)
    - **min_similarity**: Minimum similarity threshold (default: 0.6)
    - **use_fallback_search**: Use fallback search if no phonetic matches (default: true)
    - **include_suggestions**: Include phonetic suggestions
    - **include_phonetic_analysis**: Include phonetic analysis information
    """
    try:
        logger.info(
            "phonetic_search_request",
            query=query.query,
            algorithm=query.algorithm,
            match_type=query.match_type,
            user_id=current_user.get("id") if current_user else None,
            ip_address=request.client.host if request.client else None
        )
        
        # Execute phonetic search
        result = await search_service.phonetic_search(query)
        
        # Log search analytics (if analytics service is available)
        try:
            from ..services.search_analytics_service import get_search_analytics_service
            analytics_service = await get_search_analytics_service()
            
            await analytics_service.log_search(
                query=query.query,
                search_type="phonetic",
                user_id=current_user.get("id") if current_user else None,
                session_id=request.headers.get("X-Session-ID"),
                results_count=result.total_hits,
                response_time_ms=result.took,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                metadata={
                    "algorithm": query.algorithm,
                    "match_type": query.match_type,
                    "phonetic_tokens": result.phonetic_tokens,
                    "fallback_used": result.fallback_used,
                    "exact_matches": result.exact_matches,
                    "phonetic_matches": result.phonetic_matches
                }
            )
        except Exception as analytics_error:
            logger.warning("phonetic_search_analytics_error", error=str(analytics_error))
        
        logger.info(
            "phonetic_search_completed",
            query=query.query,
            algorithm=query.algorithm,
            total_hits=result.total_hits,
            took_ms=result.took,
            fallback_used=result.fallback_used,
            exact_matches=result.exact_matches,
            phonetic_matches=result.phonetic_matches
        )
        
        return result
        
    except ValidationError as e:
        logger.error("phonetic_search_validation_error", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except SearchError as e:
        logger.error("phonetic_search_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal phonetic search error")


@router.post("/search/phonetic/suggestions", response_model=PhoneticSuggestionResponse)
async def phonetic_suggestions(
    query: PhoneticSuggestionQuery,
    request: Request,
    search_service: SearchService = Depends(get_search_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> PhoneticSuggestionResponse:
    """
    Get phonetic suggestions for search terms
    
    This endpoint provides intelligent search suggestions using phonetic matching to:
    - Suggest similar-sounding words
    - Handle name variations and pronunciations
    - Provide phonetic codes for analysis
    - Include similarity scores and frequencies
    
    Perfect for:
    - Auto-complete with phonetic matching
    - Typo correction based on sound
    - Name variation suggestions
    - Cross-language name matching
    
    Parameters:
    - **text**: The text to get phonetic suggestions for
    - **field**: Field to search for suggestions (default: _all)
    - **size**: Number of suggestions to return (1-20)
    - **algorithm**: Phonetic algorithm to use
    - **include_similar**: Include similar-sounding suggestions
    - **include_common**: Include common variations
    - **min_similarity**: Minimum similarity threshold
    """
    try:
        logger.info(
            "phonetic_suggestions_request",
            text=query.text,
            algorithm=query.algorithm,
            field=query.field,
            user_id=current_user.get("id") if current_user else None
        )
        
        # Get phonetic suggestions
        result = await search_service.phonetic_suggestions(query)
        
        logger.info(
            "phonetic_suggestions_completed",
            text=query.text,
            algorithm=query.algorithm,
            phonetic_code=result.phonetic_code,
            suggestion_count=len(result.suggestions),
            took_ms=result.took
        )
        
        return result
        
    except ValidationError as e:
        logger.error("phonetic_suggestions_validation_error", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("phonetic_suggestions_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal phonetic suggestions error")


# Synonym Search Endpoints

@router.post("/search/synonym", response_model=SynonymSearchResponse)
async def synonym_search(
    query: SynonymSearchQuery,
    request: Request,
    search_service: SearchService = Depends(get_search_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> SynonymSearchResponse:
    """
    Perform synonym-enhanced search across indexed content
    
    This endpoint provides intelligent search capabilities using synonym expansion to:
    - Find related terms and concepts
    - Expand queries with contextual synonyms
    - Use domain-specific synonym dictionaries
    - Combine multiple synonym sources (WordNet, custom, contextual)
    
    Perfect for:
    - Comprehensive content discovery
    - Overcoming vocabulary mismatches
    - Domain-specific search enhancement
    - Multilingual content search
    
    Parameters:
    - **query**: The search query to expand with synonyms
    - **synonym_config**: Configuration for synonym expansion
    - **fields**: Specific fields to search (default: all)
    - **indices**: Which indices to search
    - **size**: Number of results to return (1-1000)
    - **from**: Offset for pagination
    - **sort_by**: Field to sort by
    - **sort_order**: Sort order (asc/desc)
    - **highlight**: Enable result highlighting
    - **include_synonym_analysis**: Include synonym expansion analysis
    - **include_original_query**: Include original query in search
    - **filters**: Additional filters to apply
    """
    try:
        logger.info(
            "synonym_search_request",
            query=query.query,
            synonym_type=query.synonym_config.synonym_type if query.synonym_config else None,
            expansion_strategy=query.synonym_config.expansion_strategy if query.synonym_config else None,
            indices=[idx.value if hasattr(idx, 'value') else idx for idx in query.indices],
            size=query.size,
            user_id=current_user.get("id") if current_user else None
        )
        
        # Perform synonym search
        result = await search_service.synonym_search(query)
        
        logger.info(
            "synonym_search_completed",
            query=query.query,
            expanded_query=result.expanded_query,
            total_hits=result.total_hits,
            original_matches=result.original_matches,
            synonym_matches=result.synonym_matches,
            hybrid_matches=result.hybrid_matches,
            took_ms=result.took
        )
        
        return result
        
    except ValidationError as e:
        logger.error("synonym_search_validation_error", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except SearchError as e:
        logger.error("synonym_search_error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("synonym_search_internal_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal synonym search error")


@router.post("/search/synonym/suggestions", response_model=SynonymSuggestionResponse)
async def synonym_suggestions(
    query: SynonymSuggestionQuery,
    request: Request,
    search_service: SearchService = Depends(get_search_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> SynonymSuggestionResponse:
    """
    Get synonym suggestions for search terms
    
    This endpoint provides intelligent synonym suggestions to:
    - Suggest related terms and concepts
    - Provide domain-specific alternatives
    - Include similarity scores and frequencies
    - Support multiple synonym sources
    
    Perfect for:
    - Query expansion suggestions
    - Auto-complete with synonyms
    - Vocabulary enhancement
    - Content discovery assistance
    
    Parameters:
    - **term**: The term to get synonyms for
    - **synonym_type**: Type of synonym expansion (hybrid, wordnet, custom, etc.)
    - **size**: Number of synonyms to return (1-50)
    - **min_similarity**: Minimum similarity threshold
    - **include_definitions**: Include definitions for synonyms
    - **include_examples**: Include usage examples
    - **domain_context**: Domain context for contextual synonyms
    - **pos_tag**: Part-of-speech tag filter
    """
    try:
        logger.info(
            "synonym_suggestions_request",
            term=query.term,
            synonym_type=query.synonym_type,
            size=query.size,
            domain_context=query.domain_context,
            user_id=current_user.get("id") if current_user else None
        )
        
        # Get synonym suggestions
        result = await search_service.synonym_suggestions(query)
        
        logger.info(
            "synonym_suggestions_completed",
            term=query.term,
            synonym_type=query.synonym_type,
            total_synonyms=result.total_synonyms,
            suggestion_count=len(result.synonyms),
            took_ms=result.took
        )
        
        return result
        
    except ValidationError as e:
        logger.error("synonym_suggestions_validation_error", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("synonym_suggestions_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal synonym suggestions error")


@router.get("/search/synonym/stats", response_model=SynonymStats)
async def get_synonym_stats(
    request: Request,
    search_service: SearchService = Depends(get_search_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> SynonymStats:
    """
    Get synonym usage statistics
    
    This endpoint provides comprehensive statistics about synonym usage including:
    - Total synonyms and terms
    - Usage patterns by domain
    - Cache performance metrics
    - Expansion success rates
    
    Perfect for:
    - Monitoring synonym effectiveness
    - Understanding search patterns
    - Optimizing synonym dictionaries
    - Performance analysis
    """
    try:
        logger.info(
            "synonym_stats_request",
            user_id=current_user.get("id") if current_user else None
        )
        
        # Get synonym statistics
        result = await search_service.synonym_service.get_synonym_stats()
        
        logger.info(
            "synonym_stats_completed",
            total_synonyms=result.total_synonyms,
            total_terms=result.total_terms,
            avg_synonyms_per_term=result.avg_synonyms_per_term
        )
        
        return result
        
    except Exception as e:
        logger.error("synonym_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal synonym stats error")


# Saved Search Endpoints

@router.post("/search/saved", response_model=SavedSearch)
async def create_saved_search(
    saved_search: SavedSearchCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    saved_search_service: SavedSearchService = Depends(get_saved_search_service)
) -> SavedSearch:
    """
    Create a new saved search
    
    Allows users to save frequently used search queries with their filters and settings.
    
    - **name**: Unique name for the saved search (per user)
    - **description**: Optional description
    - **query**: The complete search query to save
    - **is_public**: Whether other users can see and use this search
    - **tags**: Tags for categorization
    - **notify_on_new_results**: Enable notifications for new matching results
    """
    try:
        return await saved_search_service.create_saved_search(
            user_id=current_user["id"],
            saved_search=saved_search
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("create_saved_search_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create saved search")


@router.get("/search/saved", response_model=SavedSearchList)
async def list_saved_searches(
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
    include_public: bool = Query(default=True, description="Include public searches"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    saved_search_service: SavedSearchService = Depends(get_saved_search_service)
) -> SavedSearchList:
    """
    List saved searches for the current user
    
    Returns both the user's own saved searches and optionally public searches from other users.
    """
    try:
        return await saved_search_service.list_user_searches(
            user_id=current_user["id"],
            page=page,
            per_page=per_page,
            include_public=include_public
        )
    except Exception as e:
        logger.error("list_saved_searches_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list saved searches")


@router.get("/search/saved/popular", response_model=List[SavedSearch])
async def get_popular_saved_searches(
    limit: int = Query(default=10, ge=1, le=50, description="Number of searches to return"),
    saved_search_service: SavedSearchService = Depends(get_saved_search_service)
) -> List[SavedSearch]:
    """
    Get most popular public saved searches
    
    Returns the most frequently used public saved searches across all users.
    """
    try:
        return await saved_search_service.get_popular_searches(limit=limit)
    except Exception as e:
        logger.error("get_popular_searches_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get popular searches")


@router.get("/search/saved/by-tags", response_model=SavedSearchList)
async def search_by_tags(
    tags: List[str] = Query(..., description="Tags to search for"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
    saved_search_service: SavedSearchService = Depends(get_saved_search_service)
) -> SavedSearchList:
    """
    Search public saved searches by tags
    
    Find public saved searches that have any of the specified tags.
    """
    try:
        return await saved_search_service.search_by_tags(
            tags=tags,
            page=page,
            per_page=per_page
        )
    except Exception as e:
        logger.error("search_by_tags_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to search by tags")


@router.get("/search/saved/{search_id}", response_model=SavedSearch)
async def get_saved_search(
    search_id: str = Path(..., description="Saved search ID"),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    saved_search_service: SavedSearchService = Depends(get_saved_search_service)
) -> SavedSearch:
    """
    Get a specific saved search by ID
    
    Users can access their own saved searches or public searches from other users.
    """
    try:
        user_id = current_user["id"] if current_user else None
        return await saved_search_service.get_saved_search(
            search_id=search_id,
            user_id=user_id
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("get_saved_search_error", error=str(e), search_id=search_id)
        raise HTTPException(status_code=500, detail="Failed to get saved search")


@router.put("/search/saved/{search_id}", response_model=SavedSearch)
async def update_saved_search(
    search_id: str = Path(..., description="Saved search ID"),
    update_data: SavedSearchUpdate = ...,
    current_user: Dict[str, Any] = Depends(get_current_user),
    saved_search_service: SavedSearchService = Depends(get_saved_search_service)
) -> SavedSearch:
    """
    Update a saved search
    
    Only the owner of a saved search can update it.
    """
    try:
        return await saved_search_service.update_saved_search(
            search_id=search_id,
            user_id=current_user["id"],
            update_data=update_data
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("update_saved_search_error", error=str(e), search_id=search_id)
        raise HTTPException(status_code=500, detail="Failed to update saved search")


@router.delete("/search/saved/{search_id}")
async def delete_saved_search(
    search_id: str = Path(..., description="Saved search ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    saved_search_service: SavedSearchService = Depends(get_saved_search_service)
):
    """
    Delete a saved search
    
    Only the owner of a saved search can delete it.
    """
    try:
        await saved_search_service.delete_saved_search(
            search_id=search_id,
            user_id=current_user["id"]
        )
        return {"message": "Saved search deleted successfully"}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("delete_saved_search_error", error=str(e), search_id=search_id)
        raise HTTPException(status_code=500, detail="Failed to delete saved search")


@router.post("/search/saved/{search_id}/execute", response_model=FilteredSearchResponse)
async def execute_saved_search(
    search_id: str = Path(..., description="Saved search ID"),
    execute_params: Optional[SavedSearchExecute] = None,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    saved_search_service: SavedSearchService = Depends(get_saved_search_service)
) -> FilteredSearchResponse:
    """
    Execute a saved search
    
    Run a saved search with optional parameter overrides. This increments the usage counter.
    
    ## Parameter Overrides
    You can override certain parameters of the saved search:
    - **size**: Number of results to return
    - **from**: Pagination offset
    - **sort_by**: Sort field
    - **sort_order**: Sort direction
    - **additional_filters**: Extra filters to apply on top of saved filters
    """
    try:
        user_id = current_user["id"] if current_user else None
        return await saved_search_service.execute_saved_search(
            search_id=search_id,
            user_id=user_id,
            execute_params=execute_params
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("execute_saved_search_error", error=str(e), search_id=search_id)
        raise HTTPException(status_code=500, detail="Failed to execute saved search")


# Helper dependencies for authentication
async def get_current_user(
    # This would normally validate JWT token and return user info
    # For now, returning a mock user
) -> Dict[str, Any]:
    """Get current authenticated user"""
    # TODO: Implement actual authentication
    return {"id": "user123", "username": "test_user"}


async def get_optional_current_user() -> Optional[Dict[str, Any]]:
    """Get current user if authenticated, None otherwise"""
    # TODO: Implement actual authentication check
    try:
        return await get_current_user()
    except:
        return None


# Search History Endpoints

@router.get("/search/history", response_model=SearchHistoryList)
async def get_search_history(
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
    search_type: Optional[str] = Query(default=None, description="Filter by search type"),
    query_filter: Optional[str] = Query(default=None, description="Filter by query text"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    search_history_service: SearchHistoryService = Depends(get_search_history_service)
) -> SearchHistoryList:
    """
    Get search history for the current user
    
    Returns the user's search history with optional filtering by search type or query text.
    """
    try:
        return await search_history_service.get_user_history(
            user_id=current_user["id"],
            page=page,
            per_page=per_page,
            search_type=search_type,
            query_filter=query_filter
        )
    except Exception as e:
        logger.error("get_search_history_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get search history")


@router.get("/search/history/stats", response_model=SearchHistoryStats)
async def get_search_history_stats(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    search_history_service: SearchHistoryService = Depends(get_search_history_service)
) -> SearchHistoryStats:
    """
    Get search history statistics for the current user
    
    Returns comprehensive statistics about the user's search behavior including:
    - Total searches and unique queries
    - Average response time and results per search
    - Most common search type
    - Top queries with usage counts
    - Search volume by day
    """
    try:
        return await search_history_service.get_user_stats(
            user_id=current_user["id"],
            days=days
        )
    except Exception as e:
        logger.error("get_search_history_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get search history stats")


@router.delete("/search/history")
async def delete_old_search_history(
    older_than_days: int = Query(default=90, ge=1, description="Delete entries older than this many days"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    search_history_service: SearchHistoryService = Depends(get_search_history_service)
):
    """
    Delete old search history entries for the current user
    
    Deletes search history entries that are older than the specified number of days.
    """
    try:
        deleted_count = await search_history_service.delete_user_history(
            user_id=current_user["id"],
            older_than_days=older_than_days
        )
        return {"message": f"Deleted {deleted_count} old search history entries"}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("delete_old_search_history_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete old search history")


@router.delete("/search/history/clear")
async def clear_search_history(
    current_user: Dict[str, Any] = Depends(get_current_user),
    search_history_service: SearchHistoryService = Depends(get_search_history_service)
):
    """
    Clear all search history for the current user
    
    Permanently deletes all search history entries for the current user.
    """
    try:
        deleted_count = await search_history_service.clear_user_history(
            user_id=current_user["id"]
        )
        return {"message": f"Cleared all search history ({deleted_count} entries)"}
    except Exception as e:
        logger.error("clear_search_history_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to clear search history")


# Search Analytics Endpoints

@router.post("/analytics/search", response_model=SearchAnalyticsAggregation)
async def get_search_analytics(
    time_range: SearchAnalyticsTimeRange,
    filters: Optional[SearchAnalyticsFilter] = None,
    search_analytics_service: SearchAnalyticsService = Depends(get_search_analytics_service)
) -> SearchAnalyticsAggregation:
    """
    Get aggregated search analytics
    
    Returns comprehensive analytics data including:
    - Total searches and unique queries/users/sessions
    - Performance metrics (response times, click-through rates)
    - Top queries and filters
    - Search patterns and trends
    """
    try:
        return await search_analytics_service.get_search_analytics(
            time_range=time_range,
            filters=filters
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("get_search_analytics_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get search analytics")


@router.post("/analytics/search/performance", response_model=SearchPerformanceMetrics)
async def get_search_performance_metrics(
    time_range: SearchAnalyticsTimeRange,
    filters: Optional[SearchAnalyticsFilter] = None,
    search_analytics_service: SearchAnalyticsService = Depends(get_search_analytics_service)
) -> SearchPerformanceMetrics:
    """
    Get detailed search performance metrics
    
    Returns performance-focused analytics including:
    - Response time percentiles (p50, p95, p99)
    - Slowest and fastest queries
    - Error and timeout rates
    """
    try:
        return await search_analytics_service.get_search_performance_metrics(
            time_range=time_range,
            filters=filters
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("get_search_performance_metrics_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")


@router.post("/analytics/search/trends", response_model=List[SearchTrendData])
async def get_search_trends(
    time_range: SearchAnalyticsTimeRange,
    filters: Optional[SearchAnalyticsFilter] = None,
    search_analytics_service: SearchAnalyticsService = Depends(get_search_analytics_service)
) -> List[SearchTrendData]:
    """
    Get search trends over time
    
    Returns time-series data showing:
    - Search volume over time
    - Response time trends
    - Click-through rate trends
    - User engagement patterns
    """
    try:
        return await search_analytics_service.get_search_trends(
            time_range=time_range,
            filters=filters
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("get_search_trends_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get search trends")


@router.post("/analytics/search/report", response_model=SearchAnalyticsReport)
async def generate_search_analytics_report(
    time_range: SearchAnalyticsTimeRange,
    filters: Optional[SearchAnalyticsFilter] = None,
    search_analytics_service: SearchAnalyticsService = Depends(get_search_analytics_service)
) -> SearchAnalyticsReport:
    """
    Generate a comprehensive search analytics report
    
    Returns a complete analytics report including:
    - Summary statistics
    - Trend analysis
    - Performance metrics
    - Top queries and user segments
    - Search behavior patterns
    """
    try:
        return await search_analytics_service.generate_analytics_report(
            time_range=time_range,
            filters=filters
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("generate_search_analytics_report_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate analytics report")


@router.post("/analytics/search/segments")
async def get_user_segments(
    time_range: SearchAnalyticsTimeRange,
    filters: Optional[SearchAnalyticsFilter] = None,
    search_analytics_service: SearchAnalyticsService = Depends(get_search_analytics_service)
):
    """
    Get user segment analysis
    
    Returns user behavior segments including:
    - Power users, regular users, casual users
    - Search patterns by user type
    - Engagement metrics per segment
    """
    try:
        return await search_analytics_service.get_user_segments(
            time_range=time_range,
            filters=filters
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("get_user_segments_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get user segments")


@router.post("/analytics/search/click")
async def log_search_click(
    search_id: str,
    asset_id: str,
    session_id: Optional[str] = None,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    search_analytics_service: SearchAnalyticsService = Depends(get_search_analytics_service)
):
    """
    Log a click on a search result
    
    This endpoint should be called when a user clicks on a search result
    to track click-through rates and user engagement.
    """
    try:
        user_id = current_user["id"] if current_user else None
        
        success = await search_analytics_service.log_search_click(
            search_id=search_id,
            asset_id=asset_id,
            user_id=user_id,
            session_id=session_id
        )
        
        if success:
            return {"message": "Click logged successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to log click")
            
    except Exception as e:
        logger.error("log_search_click_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to log search click")


@router.delete("/analytics/search/cleanup")
async def cleanup_search_analytics(
    older_than_days: int = Query(default=365, ge=1, description="Delete analytics older than this many days"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    search_analytics_service: SearchAnalyticsService = Depends(get_search_analytics_service)
):
    """
    Clean up old search analytics data
    
    This endpoint allows administrators to clean up old analytics data
    to manage storage costs and comply with data retention policies.
    """
    try:
        # Check if user has admin permissions (implement based on your auth system)
        # For now, we'll allow any authenticated user
        
        deleted_count = await search_analytics_service.cleanup_old_analytics(
            older_than_days=older_than_days
        )
        
        return {"message": f"Cleaned up {deleted_count} old analytics entries"}
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("cleanup_search_analytics_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to cleanup analytics")


# Search Templates Endpoints
@router.post("/search/templates", response_model=SearchTemplate, status_code=status.HTTP_201_CREATED)
async def create_search_template(
    template_data: SearchTemplateCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    search_template_service: SearchTemplateService = Depends(get_search_template_service)
) -> SearchTemplate:
    """
    Create a new search template
    
    Creates a reusable search template that can be executed with different parameters.
    Templates can be private (default) or public, and can be shared with specific users.
    """
    try:
        return await search_template_service.create_template(
            template_data=template_data,
            user_id=current_user["id"]
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("create_search_template_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create search template")


@router.get("/search/templates", response_model=SearchTemplateList)
async def list_search_templates(
    category: Optional[SearchTemplateCategory] = Query(default=None, description="Filter by category"),
    template_type: Optional[SearchTemplateType] = Query(default=None, description="Filter by template type"),
    is_public: Optional[bool] = Query(default=None, description="Filter by public/private"),
    created_by: Optional[str] = Query(default=None, description="Filter by creator"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    search_template_service: SearchTemplateService = Depends(get_search_template_service)
) -> SearchTemplateList:
    """
    List search templates
    
    Returns a paginated list of search templates accessible to the current user.
    Includes public templates, user's own templates, and templates shared with the user.
    """
    try:
        user_id = current_user["id"] if current_user else None
        
        return await search_template_service.list_templates(
            user_id=user_id,
            category=category,
            template_type=template_type,
            is_public=is_public,
            created_by=created_by,
            page=page,
            limit=limit
        )
    except Exception as e:
        logger.error("list_search_templates_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list search templates")


@router.get("/search/templates/{template_id}", response_model=SearchTemplate)
async def get_search_template(
    template_id: str = Path(..., description="Template ID"),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    search_template_service: SearchTemplateService = Depends(get_search_template_service)
) -> SearchTemplate:
    """
    Get a specific search template
    
    Returns the details of a search template if the user has access to it.
    """
    try:
        user_id = current_user["id"] if current_user else None
        
        return await search_template_service.get_template(
            template_id=template_id,
            user_id=user_id
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error("get_search_template_error", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get search template")


@router.put("/search/templates/{template_id}", response_model=SearchTemplate)
async def update_search_template(
    template_id: str = Path(..., description="Template ID"),
    template_data: SearchTemplateUpdate = ...,
    current_user: Dict[str, Any] = Depends(get_current_user),
    search_template_service: SearchTemplateService = Depends(get_search_template_service)
) -> SearchTemplate:
    """
    Update a search template
    
    Updates an existing search template. Only the template creator can update it.
    """
    try:
        return await search_template_service.update_template(
            template_id=template_id,
            template_data=template_data,
            user_id=current_user["id"]
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error("update_search_template_error", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update search template")


@router.delete("/search/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_search_template(
    template_id: str = Path(..., description="Template ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    search_template_service: SearchTemplateService = Depends(get_search_template_service)
):
    """
    Delete a search template
    
    Deletes a search template. Only the template creator can delete it.
    """
    try:
        await search_template_service.delete_template(
            template_id=template_id,
            user_id=current_user["id"]
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error("delete_search_template_error", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete search template")


@router.post("/search/templates/{template_id}/execute", response_model=SearchTemplateExecuteResponse)
async def execute_search_template(
    template_id: str = Path(..., description="Template ID"),
    execution_data: SearchTemplateExecute = ...,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    search_template_service: SearchTemplateService = Depends(get_search_template_service)
) -> SearchTemplateExecuteResponse:
    """
    Execute a search template
    
    Executes a search template with the provided parameters and returns the search results.
    """
    try:
        user_id = current_user["id"] if current_user else None
        
        return await search_template_service.execute_template(
            template_id=template_id,
            execution_data=execution_data,
            user_id=user_id
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error("execute_search_template_error", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to execute search template")


@router.post("/search/templates/{template_id}/favorites", status_code=status.HTTP_201_CREATED)
async def add_template_to_favorites(
    template_id: str = Path(..., description="Template ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    search_template_service: SearchTemplateService = Depends(get_search_template_service)
):
    """
    Add template to favorites
    
    Adds a search template to the user's favorites list.
    """
    try:
        await search_template_service.add_to_favorites(
            template_id=template_id,
            user_id=current_user["id"]
        )
        return {"message": "Template added to favorites"}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("add_template_to_favorites_error", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to add template to favorites")


@router.delete("/search/templates/{template_id}/favorites", status_code=status.HTTP_204_NO_CONTENT)
async def remove_template_from_favorites(
    template_id: str = Path(..., description="Template ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    search_template_service: SearchTemplateService = Depends(get_search_template_service)
):
    """
    Remove template from favorites
    
    Removes a search template from the user's favorites list.
    """
    try:
        await search_template_service.remove_from_favorites(
            template_id=template_id,
            user_id=current_user["id"]
        )
    except Exception as e:
        logger.error("remove_template_from_favorites_error", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to remove template from favorites")


@router.get("/search/templates/{template_id}/stats", response_model=SearchTemplateStats)
async def get_template_stats(
    template_id: str = Path(..., description="Template ID"),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    search_template_service: SearchTemplateService = Depends(get_search_template_service)
) -> SearchTemplateStats:
    """
    Get template statistics
    
    Returns usage statistics for a search template.
    """
    try:
        user_id = current_user["id"] if current_user else None
        
        return await search_template_service.get_template_stats(
            template_id=template_id,
            user_id=user_id
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error("get_template_stats_error", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get template stats")


@router.get("/search/templates/{template_id}/export", response_model=SearchTemplateExport)
async def export_search_template(
    template_id: str = Path(..., description="Template ID"),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    search_template_service: SearchTemplateService = Depends(get_search_template_service)
) -> SearchTemplateExport:
    """
    Export search template
    
    Exports a search template for sharing or backup purposes.
    """
    try:
        user_id = current_user["id"] if current_user else None
        
        return await search_template_service.export_template(
            template_id=template_id,
            user_id=user_id
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error("export_search_template_error", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to export search template")


@router.post("/search/templates/import", response_model=SearchTemplate, status_code=status.HTTP_201_CREATED)
async def import_search_template(
    import_data: SearchTemplateImport,
    current_user: Dict[str, Any] = Depends(get_current_user),
    search_template_service: SearchTemplateService = Depends(get_search_template_service)
) -> SearchTemplate:
    """
    Import search template
    
    Imports a search template from export data.
    """
    try:
        return await search_template_service.import_template(
            import_data=import_data,
            user_id=current_user["id"]
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("import_search_template_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to import search template")


@router.post("/search/templates/{template_id}/share", status_code=status.HTTP_201_CREATED)
async def share_search_template(
    template_id: str = Path(..., description="Template ID"),
    share_data: SearchTemplateShare = ...,
    current_user: Dict[str, Any] = Depends(get_current_user),
    search_template_service: SearchTemplateService = Depends(get_search_template_service)
):
    """
    Share search template
    
    Shares a search template with specific users.
    """
    try:
        await search_template_service.share_template(
            template_id=template_id,
            share_data=share_data,
            user_id=current_user["id"]
        )
        return {"message": "Template shared successfully"}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error("share_search_template_error", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to share search template")


# Timecode Search Endpoints
@router.post("/search/timecode", response_model=TimecodeSearchResponse)
async def search_by_timecode(
    query: TimecodeSearchQuery,
    request: Request,
    timecode_search_service: TimecodeSearchService = Depends(get_timecode_search_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> TimecodeSearchResponse:
    """
    Perform timecode-based search for video and audio assets
    
    This endpoint provides specialized search functionality for time-based media content:
    
    - **Simple Timecode Search**: Search for assets at specific timecodes
    - **Range-Based Search**: Find assets within timecode ranges
    - **Duration Search**: Filter by asset duration
    - **Segment Search**: Search within markers and chapters
    - **Subtitle Search**: Find content based on subtitle timecodes
    - **Metadata Search**: Filter by technical metadata (frame rate, resolution, etc.)
    
    ## Search Types Supported:
    - `simple`: Basic timecode or duration search
    - `advanced`: Complex queries with multiple criteria
    - `segment`: Search for segments within media
    - `marker`: Search based on markers/chapters
    - `subtitle`: Search based on subtitle timecodes
    - `metadata`: Search based on timecode metadata
    
    ## Timecode Formats Supported:
    - `drop_frame`: 29.97fps drop frame (HH:MM:SS;FF)
    - `non_drop_frame`: 30fps non-drop frame (HH:MM:SS:FF)
    - `film`: 24fps film (HH:MM:SS:FF)
    - `pal`: 25fps PAL (HH:MM:SS:FF)
    - `ntsc`: 29.97fps NTSC (HH:MM:SS:FF)
    - `custom`: Custom frame rate
    
    ## Range Types Supported:
    - `exact`: Exact timecode match
    - `range`: Within a specific range
    - `duration`: Assets with specific duration
    - `overlap`: Assets that overlap with range
    - `contains`: Assets that contain the range
    - `within`: Assets completely within range
    
    ## Example Request:
    ```json
    {
        "search_type": "simple",
        "timecode": {
            "hours": 0,
            "minutes": 5,
            "seconds": 30,
            "frames": 15,
            "format": "non_drop_frame"
        },
        "tolerance_seconds": 1.0,
        "asset_types": ["video"],
        "frame_rates": [24.0, 29.97, 30.0],
        "page": 1,
        "limit": 20
    }
    ```
    """
    try:
        logger.info("Timecode search request", 
                   search_type=query.search_type,
                   timecode=str(query.timecode) if query.timecode else None,
                   user_id=current_user.get("id") if current_user else None)
        
        return await timecode_search_service.search_by_timecode(query)
        
    except ValidationError as e:
        logger.error("Timecode search validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except SearchError as e:
        logger.error("Timecode search error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Unexpected timecode search error", error=str(e))
        raise HTTPException(status_code=500, detail="Timecode search failed")


@router.post("/search/timecode/validate", response_model=TimecodeValidationResult)
async def validate_timecode(
    timecode: str = Query(..., description="Timecode string to validate"),
    format: TimecodeFormat = Query(default=TimecodeFormat.NON_DROP_FRAME, description="Timecode format"),
    timecode_search_service: TimecodeSearchService = Depends(get_timecode_search_service)
) -> TimecodeValidationResult:
    """
    Validate a timecode string
    
    Validates timecode format and returns normalized information:
    - Format validation (HH:MM:SS:FF or HH:MM:SS;FF)
    - Frame rate compatibility checks
    - Conversion to seconds and frames
    - Format detection and suggestions
    
    ## Supported Formats:
    - `drop_frame`: 29.97fps drop frame (uses semicolon separator)
    - `non_drop_frame`: 30fps non-drop frame (uses colon separator)
    - `film`: 24fps film
    - `pal`: 25fps PAL
    - `ntsc`: 29.97fps NTSC
    - `custom`: Custom frame rate
    
    ## Examples:
    - `01:23:45:12` (valid non-drop frame)
    - `01:23:45;12` (valid drop frame)
    - `25:00:00:00` (invalid - hours > 23)
    - `01:23:45:30` (invalid for film format)
    """
    try:
        logger.info("Timecode validation request", timecode=timecode, format=format)
        
        return await timecode_search_service.validate_timecode(timecode, format)
        
    except Exception as e:
        logger.error("Timecode validation error", error=str(e))
        return TimecodeValidationResult(
            is_valid=False,
            errors=[str(e)],
            warnings=[]
        )


@router.post("/search/timecode/convert", response_model=TimecodeConversionResponse)
async def convert_timecode(
    conversion_request: TimecodeConversionRequest,
    timecode_search_service: TimecodeSearchService = Depends(get_timecode_search_service)
) -> TimecodeConversionResponse:
    """
    Convert timecode between different formats
    
    Converts timecode from one format to another with precision tracking:
    - Frame rate conversion between different formats
    - Drop frame to non-drop frame conversion
    - Custom frame rate support
    - Precision loss detection and warnings
    
    ## Conversion Examples:
    - Film (24fps) to PAL (25fps)
    - NTSC (29.97fps) to Non-Drop Frame (30fps)
    - Drop Frame to Non-Drop Frame
    - Custom frame rates
    
    ## Precision Notes:
    - Conversions between different frame rates may result in precision loss
    - The system will flag potential precision issues
    - Rounding may occur for non-integer frame conversions
    """
    try:
        logger.info("Timecode conversion request", 
                   source_format=conversion_request.source_format,
                   target_format=conversion_request.target_format,
                   timecode=conversion_request.source_timecode)
        
        return await timecode_search_service.convert_timecode(conversion_request)
        
    except ValidationError as e:
        logger.error("Timecode conversion validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Timecode conversion error", error=str(e))
        raise HTTPException(status_code=500, detail="Timecode conversion failed")


@router.get("/search/timecode/stats", response_model=TimecodeSearchStats)
async def get_timecode_search_stats(
    timecode_search_service: TimecodeSearchService = Depends(get_timecode_search_service)
) -> TimecodeSearchStats:
    """
    Get timecode search statistics
    
    Returns comprehensive statistics about timecode data in the system:
    - Total assets with timecode information
    - Duration statistics (min, max, average)
    - Frame rate distribution across all assets
    - Timecode format distribution
    - Search performance metrics
    
    ## Statistics Include:
    - **Asset Counts**: Total assets with timecode data
    - **Duration Stats**: Min, max, and average durations
    - **Frame Rate Distribution**: Breakdown by frame rate
    - **Format Distribution**: Usage of different timecode formats
    - **Performance Metrics**: Search timing and cache hit rates
    
    This endpoint helps administrators understand:
    - Media library composition
    - Technical standard usage
    - Search system performance
    - Storage optimization opportunities
    """
    try:
        logger.info("Timecode stats request")
        
        return await timecode_search_service.get_timecode_stats()
        
    except Exception as e:
        logger.error("Timecode stats error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get timecode statistics")


# Color Search Endpoints
@router.post("/search/color", response_model=ColorSearchResponse)
async def search_by_color(
    query: ColorSearchQuery,
    request: Request,
    color_search_service: ColorSearchService = Depends(get_color_search_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> ColorSearchResponse:
    """
    Perform color-based search for image and video assets
    
    This endpoint provides specialized search functionality for color-based media content:
    
    - **Dominant Color Search**: Search for assets with specific dominant colors
    - **Color Palette Search**: Find assets with similar color palettes
    - **Color Range Search**: Search within specific color ranges
    - **Color Harmony Search**: Find complementary, analogous, or triadic color schemes
    - **Color Temperature Search**: Filter by warm or cool colors
    - **Brightness/Saturation Search**: Filter by brightness or saturation ranges
    - **Hue Range Search**: Search within specific hue ranges
    
    ## Search Types Supported:
    - `dominant_color`: Search for assets with specific dominant colors
    - `color_palette`: Find assets with similar color palettes
    - `similar_colors`: Search for colors similar to a target color
    - `color_range`: Search within a specific color range
    - `complementary_colors`: Find complementary color schemes
    - `analogous_colors`: Find analogous color schemes
    - `triadic_colors`: Find triadic color schemes
    - `monochromatic`: Find monochromatic images
    - `warm_colors`: Find images with warm color tones
    - `cool_colors`: Find images with cool color tones
    - `brightness_range`: Filter by brightness range
    - `saturation_range`: Filter by saturation range
    - `hue_range`: Filter by hue range
    
    ## Color Spaces Supported:
    - `rgb`: Red, Green, Blue
    - `hsv`: Hue, Saturation, Value
    - `hsl`: Hue, Saturation, Lightness
    - `lab`: L*a*b* color space
    - `xyz`: CIE XYZ color space
    - `yuv`: YUV color space
    - `cmyk`: Cyan, Magenta, Yellow, Key (Black)
    - `hex`: Hexadecimal color representation
    
    ## Color Matching Types:
    - `exact`: Exact color match
    - `euclidean`: Euclidean distance in color space
    - `delta_e`: Delta E color difference (CIE76)
    - `cosine`: Cosine similarity
    - `manhattan`: Manhattan distance
    - `perceptual`: Perceptual color difference
    - `weighted`: Weighted color distance
    
    ## Example Request:
    ```json
    {
        "search_type": "dominant_color",
        "target_color": {
            "r": 120,
            "g": 80,
            "b": 200
        },
        "color_space": "rgb",
        "match_type": "euclidean",
        "tolerance": 15.0,
        "min_color_percentage": 10.0,
        "asset_types": ["image", "video"],
        "page": 1,
        "limit": 20
    }
    ```
    """
    try:
        logger.info("Color search request", 
                   search_type=query.search_type,
                   target_color=f"RGB({query.target_color.r},{query.target_color.g},{query.target_color.b})" if query.target_color else None,
                   color_space=query.color_space,
                   match_type=query.match_type,
                   user_id=current_user.get("id") if current_user else None)
        
        return await color_search_service.search_by_color(query)
        
    except ValidationError as e:
        logger.error("Color search validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except SearchError as e:
        logger.error("Color search error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Unexpected color search error", error=str(e))
        raise HTTPException(status_code=500, detail="Color search failed")


@router.post("/search/color/analyze", response_model=ColorAnalysisResponse)
async def analyze_asset_colors(
    request: ColorAnalysisRequest,
    color_search_service: ColorSearchService = Depends(get_color_search_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> ColorAnalysisResponse:
    """
    Analyze colors in a specific asset
    
    This endpoint provides detailed color analysis for individual assets:
    
    - **Color Extraction**: Extract dominant colors from images and videos
    - **Color Palette Generation**: Generate color palettes using various clustering methods
    - **Color Statistics**: Calculate color diversity, temperature, brightness, contrast
    - **Color Histogram**: Generate color histograms for detailed analysis
    - **Frame Analysis**: Analyze colors in video frames at specified intervals
    
    ## Analysis Methods:
    - `kmeans`: K-means clustering for color extraction
    - `dbscan`: DBSCAN clustering for density-based color grouping
    - `hierarchical`: Hierarchical clustering for color relationships
    - `meanshift`: Mean-shift clustering for automatic cluster detection
    - `spectral`: Spectral clustering for complex color patterns
    
    ## Color Spaces:
    - `rgb`: Standard RGB color space
    - `hsv`: Hue, Saturation, Value
    - `hsl`: Hue, Saturation, Lightness
    - `lab`: Perceptually uniform L*a*b* space
    
    ## Analysis Options:
    - **Color Extraction**: Number of colors to extract (1-20)
    - **Video Analysis**: Frame interval and sample frame count
    - **Histogram**: Optional color histogram generation
    - **Statistics**: Color diversity, temperature, brightness metrics
    - **Force Reanalysis**: Override cached analysis results
    
    ## Example Request:
    ```json
    {
        "asset_id": "asset-123",
        "color_space": "rgb",
        "clustering_method": "kmeans",
        "num_colors": 5,
        "frame_interval": 30,
        "sample_frames": 10,
        "include_histogram": true,
        "include_statistics": true,
        "force_reanalysis": false
    }
    ```
    """
    try:
        logger.info("Color analysis request", 
                   asset_id=request.asset_id,
                   color_space=request.color_space,
                   clustering_method=request.clustering_method,
                   num_colors=request.num_colors,
                   user_id=current_user.get("id") if current_user else None)
        
        return await color_search_service.analyze_asset_colors(request)
        
    except ValidationError as e:
        logger.error("Color analysis validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Color analysis error", error=str(e))
        raise HTTPException(status_code=500, detail="Color analysis failed")


@router.get("/search/color/stats", response_model=ColorSearchStats)
async def get_color_search_stats(
    color_search_service: ColorSearchService = Depends(get_color_search_service)
) -> ColorSearchStats:
    """
    Get comprehensive color search statistics
    
    This endpoint provides detailed statistics about color search usage and analysis:
    
    - **Search Statistics**: Total searches, performance metrics
    - **Asset Analysis**: Count of analyzed images and videos
    - **Color Distribution**: Most common colors across all assets
    - **Diversity Metrics**: Color diversity statistics
    - **Performance Data**: Search timing and cache hit rates
    
    ## Statistics Include:
    - **Search Metrics**: Total searches performed, average search time
    - **Asset Counts**: Images and videos analyzed, total frames processed
    - **Color Analysis**: Most common colors, color diversity distribution
    - **Performance**: Search timing, analysis timing, cache performance
    - **Usage Patterns**: Color space usage, clustering method preferences
    
    ## Color Distribution Data:
    - **Most Common Colors**: Top colors across all analyzed assets
    - **Color Temperature**: Distribution of warm vs cool colors
    - **Brightness/Saturation**: Distribution of brightness and saturation values
    - **Hue Distribution**: Distribution across the color spectrum
    
    ## Performance Metrics:
    - **Search Speed**: Average time for color searches
    - **Analysis Speed**: Average time for color analysis
    - **Cache Efficiency**: Hit rate for cached color data
    - **System Load**: Resource usage for color processing
    
    This endpoint helps administrators understand:
    - Color search usage patterns
    - System performance characteristics
    - Color distribution in media library
    - Optimization opportunities
    """
    try:
        logger.info("Color search stats request")
        
        return await color_search_service.get_color_search_stats()
        
    except Exception as e:
        logger.error("Color search stats error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get color search statistics")


# ==================== FACIAL RECOGNITION SEARCH ENDPOINTS ====================

@router.post("/search/face", response_model=FaceSearchResponse)
async def search_by_face(
    query: FaceSearchQuery,
    request: Request,
    face_search_service: FaceSearchService = Depends(get_face_search_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> FaceSearchResponse:
    """
    Perform comprehensive facial recognition search
    
    This endpoint provides advanced facial recognition search capabilities across images and videos:
    
    - **Person Search**: Find specific individuals by person ID or name
    - **Face Similarity**: Find faces similar to a reference image or encoding
    - **Demographic Search**: Search by age, gender, emotion, expression
    - **Quality Filtering**: Filter by face quality, confidence, blur level
    - **Celebrity Recognition**: Find assets containing celebrities
    - **Group Detection**: Search for group photos with specific size ranges
    - **Unknown Faces**: Find unidentified faces for manual tagging
    
    ## Search Types:
    - **person_search**: Search for specific person by ID or name
    - **face_similarity**: Find similar faces using reference image/encoding
    - **face_verification**: Verify if a person appears in assets
    - **demographic_search**: Search by age range, gender combinations
    - **emotion_search**: Find faces expressing specific emotions
    - **age_range_search**: Search within specific age ranges
    - **gender_search**: Filter by gender (male/female/unknown)
    - **expression_search**: Search by facial expressions (smiling, frowning, etc.)
    - **face_count**: Find assets with specific number of faces
    - **group_detection**: Find group photos with size ranges
    - **celebrity_recognition**: Find assets containing celebrities
    - **unknown_faces**: Find unidentified faces for tagging
    
    ## Quality Filters:
    - **min_confidence**: Minimum detection confidence (0.0-1.0)
    - **min_face_quality**: Minimum face quality level
    - **max_blur_score**: Maximum acceptable blur level
    - **min_face_size**: Minimum face size in pixels
    
    ## Privacy Features:
    - **Consent Tracking**: Respects person privacy settings
    - **Anonymization**: Can anonymize unknown faces
    - **Privacy Compliance**: Follows data protection regulations
    
    ## Advanced Features:
    - **Multiple Models**: Support for various detection/recognition models
    - **Video Analysis**: Frame-by-frame or scene-based analysis
    - **Timeline Tracking**: Track face appearances over time
    - **Demographic Analysis**: Age, gender, emotion distribution
    - **Quality Assessment**: Face quality scoring and filtering
    
    The response includes detected faces, person identifications, demographics,
    quality metrics, and optional timeline data for videos.
    """
    try:
        logger.info("Face search request", 
                   search_type=query.search_type.value, 
                   user_id=current_user.get("user_id") if current_user else None)
        
        # Log the search query for analytics
        await _log_search_query(query.dict(), "face_search", current_user)
        
        return await face_search_service.search_by_face(query)
        
    except ValidationError as e:
        logger.error("Face search validation error", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Face search error", error=str(e))
        raise HTTPException(status_code=500, detail="Face search failed")


@router.post("/search/face/analyze", response_model=FaceAnalysisResponse)
async def analyze_asset_faces(
    request_data: FaceAnalysisRequest,
    request: Request,
    face_search_service: FaceSearchService = Depends(get_face_search_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> FaceAnalysisResponse:
    """
    Analyze faces in a specific asset
    
    This endpoint performs comprehensive face analysis on an individual asset:
    
    - **Face Detection**: Detect all faces in image or video
    - **Person Identification**: Identify known persons from database
    - **Attribute Extraction**: Age, gender, emotion, expression analysis
    - **Quality Assessment**: Face quality, blur, brightness evaluation
    - **Encoding Generation**: Create face embeddings for similarity search
    - **Landmark Detection**: Facial landmark points for detailed analysis
    - **Celebrity Recognition**: Detect famous persons if enabled
    
    ## Analysis Options:
    - **extract_attributes**: Extract age, gender, emotion, expression
    - **extract_encodings**: Generate face embeddings for recognition
    - **extract_landmarks**: Detect facial landmark points
    - **identify_persons**: Attempt to identify known persons
    - **detect_celebrities**: Enable celebrity recognition
    
    ## Model Selection:
    - **Detection Models**: MTCNN, RetinaFace, MediaPipe, YOLO-Face, etc.
    - **Recognition Models**: FaceNet, ArcFace, CosFace, InsightFace, etc.
    - **Landmark Types**: 5, 68, 81, 106, or 468 point landmarks
    
    ## Quality Settings:
    - **min_face_size**: Minimum face size in pixels (default: 30)
    - **min_confidence**: Minimum detection confidence (default: 0.6)
    - **max_faces**: Maximum number of faces to process
    
    ## Video Settings:
    - **frame_interval**: Process every N frames (default: 30)
    - **max_frames**: Maximum frames to analyze
    - **scene_detection**: Enable scene-based analysis
    
    ## Processing Options:
    - **force_reanalysis**: Re-analyze even if results exist
    - **parallel_processing**: Enable parallel processing
    - **gpu_acceleration**: Use GPU acceleration if available
    
    ## Privacy Options:
    - **anonymize_unknown**: Anonymize faces of unknown persons
    - **respect_privacy_settings**: Honor person privacy preferences
    
    The response includes all detected faces with attributes, identifications,
    quality metrics, demographics analysis, and processing metadata.
    """
    try:
        logger.info("Face analysis request", 
                   asset_id=request_data.asset_id,
                   detection_model=request_data.detection_model.value,
                   recognition_model=request_data.recognition_model.value,
                   user_id=current_user.get("user_id") if current_user else None)
        
        return await face_search_service.analyze_asset_faces(request_data)
        
    except ValidationError as e:
        logger.error("Face analysis validation error", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Face analysis error", error=str(e))
        raise HTTPException(status_code=500, detail="Face analysis failed")


@router.get("/search/face/stats", response_model=FaceSearchStats)
async def get_face_search_stats(
    face_search_service: FaceSearchService = Depends(get_face_search_service)
) -> FaceSearchStats:
    """
    Get comprehensive facial recognition search statistics
    
    This endpoint provides detailed statistics about facial recognition usage and performance:
    
    - **Search Statistics**: Total searches, recognition accuracy, performance metrics
    - **Person Database**: Unique persons identified, database size
    - **Quality Metrics**: Face quality distribution, confidence levels
    - **Demographics**: Age, gender, emotion distribution across analyzed content
    - **Performance Data**: Search timing, detection speed, cache efficiency
    - **Privacy Compliance**: Consent tracking, anonymization statistics
    
    ## Statistics Include:
    - **Search Metrics**: Total searches, average search time, accuracy rates
    - **Detection Metrics**: Total faces detected, detection failure rates
    - **Recognition Metrics**: Person identification rates, false positive/negative rates
    - **Quality Distribution**: Face quality levels across all detections
    - **Demographics**: Age/gender/emotion distribution in analyzed content
    
    ## Performance Metrics:
    - **Search Speed**: Average time for face searches
    - **Detection Speed**: Average time for face detection
    - **Recognition Speed**: Average time for person identification
    - **Cache Efficiency**: Hit rate for cached face data
    
    ## Model Usage:
    - **Detection Models**: Usage statistics for different detection models
    - **Recognition Models**: Usage statistics for different recognition models
    - **Accuracy Comparison**: Performance comparison between models
    
    ## Privacy and Compliance:
    - **Consent Tracking**: Number of persons with/without consent
    - **Anonymization**: Number of anonymized faces
    - **Privacy Violations**: Any detected privacy violations
    
    ## Quality Assurance:
    - **Quality Distribution**: Breakdown by face quality levels
    - **Confidence Distribution**: Detection confidence distribution
    - **Error Rates**: Detection and recognition failure statistics
    
    This endpoint helps administrators understand:
    - Facial recognition system performance
    - User engagement with face search features
    - Quality and accuracy of face detection/recognition
    - Privacy compliance status
    - System optimization opportunities
    """
    try:
        logger.info("Face search stats request")
        
        return await face_search_service.get_face_search_stats()
        
    except Exception as e:
        logger.error("Face search stats error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get face search statistics")


# ========================================================================================
# Image Similarity Search Endpoints
# ========================================================================================

@router.post("/search/image-similarity", response_model=ImageSimilarityResponse)
async def search_similar_images(
    query: ImageSimilarityQuery,
    request: Request,
    image_similarity_service: ImageSimilarityService = Depends(get_image_similarity_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> ImageSimilarityResponse:
    """
    Perform comprehensive image similarity search
    
    This endpoint provides advanced image similarity search capabilities including:
    
    ## Input Options:
    - **Reference Asset ID**: Search using an existing asset as reference
    - **Reference Image URL**: Search using an external image URL
    - **Reference Features**: Search using pre-extracted feature vectors
    - **Reference Hash**: Search using perceptual hash values
    
    ## Similarity Types:
    - **Visual Similarity**: Overall visual appearance matching
    - **Content Similarity**: Object and scene content matching  
    - **Style Similarity**: Artistic style and technique matching
    - **Color Similarity**: Color palette and distribution matching
    - **Texture Similarity**: Surface texture pattern matching
    - **Shape Similarity**: Geometric shape and structure matching
    - **Semantic Similarity**: Conceptual meaning matching
    - **Perceptual Hash**: Fast duplicate and near-duplicate detection
    - **Duplicate Detection**: Exact and near-exact duplicate finding
    - **Reverse Image Search**: Find origins and variations of an image
    
    ## Feature Models:
    - **ResNet50**: General-purpose deep features (2048-dim)
    - **VGG16/VGG19**: Classic CNN features (4096-dim)
    - **EfficientNet**: Efficient deep features (1280-dim)
    - **CLIP**: Vision-language features (512-dim)
    - **Vision Transformer (ViT)**: Transformer-based features (768-dim)
    - **DINO**: Self-supervised features (768-dim)
    - **Swin Transformer**: Hierarchical vision transformer (1024-dim)
    - **MobileNet**: Lightweight mobile features (1024-dim)
    
    ## Similarity Metrics:
    - **Cosine Similarity**: Angle-based similarity (0-1, higher better)
    - **Euclidean Distance**: L2 distance (0+, lower better)
    - **Manhattan Distance**: L1 distance (0+, lower better) 
    - **Hamming Distance**: Bit difference for hashes
    - **Structural Similarity**: Spatial feature similarity
    
    ## Filtering Options:
    - **Asset Types**: Filter by image, video, document types
    - **File Formats**: Filter by JPEG, PNG, TIFF, etc.
    - **Size Range**: Filter by file size constraints
    - **Dimension Range**: Filter by image width/height
    - **Date Range**: Filter by creation/modification date
    - **Quality Threshold**: Exclude low-quality images
    
    ## Search Options:
    - **Similarity Threshold**: Minimum similarity score (0-1)
    - **Include Duplicates**: Whether to include exact duplicates
    - **Region-based Matching**: Enable regional similarity analysis
    - **Multi-scale Analysis**: Analyze at multiple image scales
    
    ## Response Features:
    - **Ranked Results**: Results sorted by similarity score
    - **Match Details**: Individual feature similarity scores
    - **Quality Metrics**: Image quality and match confidence
    - **Performance Data**: Search timing and execution metrics
    - **Clustering**: Optional result clustering and grouping
    
    ## Use Cases:
    - **Content Discovery**: Find visually similar content in large collections
    - **Duplicate Detection**: Identify and manage duplicate images
    - **Style Matching**: Find images with similar artistic style
    - **Brand Monitoring**: Find usage of branded visual content
    - **Quality Control**: Identify low-quality or corrupted images
    - **Content Organization**: Group similar visual content automatically
    
    ## Performance:
    - Search speed varies by feature model and dataset size
    - Feature extraction: 50-200ms per image
    - Search execution: 20-100ms for typical datasets
    - Results cached for improved performance
    
    ## Best Practices:
    - Use ResNet50 or EfficientNet for general-purpose similarity
    - Use CLIP for semantic/conceptual similarity
    - Use perceptual hashes for fast duplicate detection
    - Set appropriate similarity thresholds (0.7-0.9 typical)
    - Enable quality filtering for better results
    - Use region-based matching for partial image similarity
    """
    try:
        start_time = datetime.utcnow()
        
        logger.info(
            "image_similarity_search_request",
            similarity_type=query.similarity_type,
            feature_model=query.feature_model,
            similarity_metric=query.similarity_metric,
            similarity_threshold=query.similarity_threshold,
            user_id=current_user.get("id") if current_user else None
        )
        
        result = await image_similarity_service.search_similar_images(query)
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds() * 1000
        
        logger.info(
            "image_similarity_search_completed",
            query_id=result.query_id,
            matches_found=result.total,
            processing_time_ms=processing_time,
            similarity_type=query.similarity_type
        )
        
        return result
        
    except ValidationError as e:
        logger.error("image_similarity_search_validation_error", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("image_similarity_search_error", error=str(e))
        raise HTTPException(status_code=500, detail="Image similarity search failed")


@router.post("/search/image-similarity/analyze", response_model=ImageAnalysisResponse)
async def analyze_image_features(
    request_data: ImageAnalysisRequest,
    request: Request,
    image_similarity_service: ImageSimilarityService = Depends(get_image_similarity_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> ImageAnalysisResponse:
    """
    Analyze an image and extract comprehensive features
    
    This endpoint performs detailed analysis of an image asset and extracts
    various types of features that can be used for similarity search, content
    organization, and quality assessment.
    
    ## Analysis Capabilities:
    
    ### Feature Extraction:
    - **Deep Learning Features**: CNN-based feature vectors from multiple models
    - **Perceptual Hashes**: Fast similarity hashes for duplicate detection
    - **Color Analysis**: Dominant colors, palettes, histograms
    - **Texture Analysis**: Surface texture patterns and characteristics
    - **Shape Analysis**: Geometric shapes and structural elements
    - **Quality Assessment**: Image quality metrics and scores
    
    ### Supported Models:
    - **ResNet50**: Standard deep learning features (2048 dimensions)
    - **EfficientNet**: Efficient architecture features (1280 dimensions)
    - **CLIP**: Vision-language model features (512 dimensions)
    - **Vision Transformer**: Attention-based features (768 dimensions)
    - **VGG16/19**: Classic CNN features (4096 dimensions)
    - **MobileNet**: Lightweight features (1024 dimensions)
    
    ### Hash Algorithms:
    - **Perceptual Hash**: Robust to minor modifications
    - **Average Hash**: Fast computation for basic similarity
    - **Difference Hash**: Gradient-based hash for better accuracy
    - **Wavelet Hash**: Frequency domain analysis
    - **Color Hash**: Color-based similarity detection
    - **Crop Resistant Hash**: Robust to cropping and partial occlusion
    
    ### Color Analysis:
    - **Dominant Colors**: Most prominent colors in the image
    - **Color Palette**: Complete color distribution with percentages
    - **Color Histograms**: RGB channel distributions
    - **Color Statistics**: Brightness, contrast, saturation metrics
    - **Color Space Analysis**: Analysis in multiple color spaces
    
    ### Quality Metrics:
    - **Overall Quality Score**: Composite quality assessment (0-1)
    - **Sharpness**: Image sharpness and focus quality
    - **Blur Detection**: Blur amount and type identification
    - **Noise Analysis**: Image noise levels and characteristics
    - **Exposure Assessment**: Over/under exposure detection
    - **Artifact Detection**: Compression and processing artifacts
    
    ### Processing Options:
    - **Preprocessing**: Image enhancement and normalization
    - **GPU Acceleration**: Faster processing on compatible hardware
    - **Parallel Processing**: Multi-threaded feature extraction
    - **Force Reanalysis**: Override cached results
    - **Target Sizing**: Resize for optimal analysis performance
    
    ## Use Cases:
    - **Similarity Search Preparation**: Extract features for future searches
    - **Content Organization**: Automatic categorization by visual features
    - **Quality Control**: Identify low-quality or problematic images
    - **Duplicate Detection**: Generate hashes for duplicate identification
    - **Content Understanding**: Analyze visual characteristics of content
    - **Asset Management**: Comprehensive metadata extraction
    
    ## Performance:
    - Analysis time varies by image size and selected features
    - Typical processing: 100-500ms per image
    - GPU acceleration can reduce time by 2-5x
    - Results are cached for subsequent requests
    - Parallel processing supported for multiple feature types
    
    ## Response Data:
    - **Feature Vectors**: Numerical representations for similarity search
    - **Perceptual Hashes**: Hash values for fast comparison
    - **Visual Characteristics**: Color, texture, shape analysis
    - **Quality Metrics**: Comprehensive quality assessment
    - **Processing Metadata**: Timing, models used, preprocessing applied
    - **Error Handling**: Detailed error reporting and recovery
    
    ## Best Practices:
    - Select appropriate models based on use case requirements
    - Enable quality assessment for content curation
    - Use multiple hash types for robust duplicate detection
    - Consider GPU acceleration for large-scale processing
    - Cache results for frequently accessed images
    """
    try:
        start_time = datetime.utcnow()
        
        logger.info(
            "image_analysis_request",
            asset_id=request_data.asset_id,
            feature_models=request_data.feature_models,
            extract_hashes=request_data.extract_hashes,
            analyze_color=request_data.analyze_color,
            user_id=current_user.get("id") if current_user else None
        )
        
        result = await image_similarity_service.analyze_image(request_data)
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds() * 1000
        
        logger.info(
            "image_analysis_completed",
            asset_id=request_data.asset_id,
            processing_time_ms=processing_time,
            analysis_success=result.analysis_success,
            features_extracted=len(result.analysis.feature_vectors),
            hashes_computed=len(result.analysis.perceptual_hashes)
        )
        
        return result
        
    except ValidationError as e:
        logger.error("image_analysis_validation_error", asset_id=request_data.asset_id, error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("image_analysis_error", asset_id=request_data.asset_id, error=str(e))
        raise HTTPException(status_code=500, detail="Image analysis failed")


@router.get("/search/image-similarity/stats", response_model=ImageSimilarityStats)
async def get_image_similarity_stats(
    image_similarity_service: ImageSimilarityService = Depends(get_image_similarity_service)
) -> ImageSimilarityStats:
    """
    Get comprehensive image similarity search statistics
    
    This endpoint provides detailed analytics and performance metrics for the
    image similarity search system, helping administrators understand usage
    patterns, performance characteristics, and system health.
    
    ## Statistics Categories:
    
    ### Search Performance:
    - **Total Searches**: Number of similarity searches performed
    - **Average Search Time**: Mean search execution time
    - **Cache Hit Rate**: Percentage of feature cache hits
    - **Search Success Rate**: Percentage of successful searches
    
    ### Feature Extraction:
    - **Images Analyzed**: Total number of images processed
    - **Features Extracted**: Total feature vectors generated
    - **Hashes Computed**: Total perceptual hashes calculated
    - **Average Extraction Time**: Mean feature extraction time
    
    ### Model Usage:
    - **Feature Model Distribution**: Usage statistics for each model
    - **Similarity Metric Usage**: Distribution of similarity metrics used
    - **Hash Algorithm Usage**: Usage patterns for different hash types
    - **Model Performance**: Accuracy and speed comparison between models
    
    ### Search Patterns:
    - **Search Type Distribution**: Breakdown by similarity search types
    - **Similarity Score Distribution**: Distribution of match quality scores
    - **Filter Usage**: Most commonly used search filters
    - **Result Set Sizes**: Distribution of search result counts
    
    ### Quality Metrics:
    - **Average Image Quality**: Mean quality score across all analyzed images
    - **Quality Distribution**: Breakdown by quality levels (excellent/good/fair/poor)
    - **Low Quality Detection**: Number of images flagged as low quality
    - **Quality Improvement**: Trends in image quality over time
    
    ### System Health:
    - **Error Rates**: Feature extraction and search failure rates
    - **Performance Trends**: Search speed and accuracy trends over time
    - **Resource Usage**: Computational resource utilization
    - **Cache Efficiency**: Feature cache performance metrics
    
    ### Usage Analytics:
    - **Active Users**: Number of users performing similarity searches
    - **Popular Features**: Most frequently used search features
    - **Peak Usage Times**: Temporal usage patterns
    - **Geographic Distribution**: Usage patterns by region/location
    
    ## Key Metrics:
    - **Search Volume**: Total number of searches performed
    - **Performance**: Average search and extraction times
    - **Quality**: Image quality and match accuracy statistics
    - **Efficiency**: Cache hit rates and resource utilization
    - **Reliability**: Error rates and system availability
    
    ## Use Cases:
    - **Performance Monitoring**: Track system performance over time
    - **Capacity Planning**: Understand usage patterns for scaling decisions
    - **Quality Assurance**: Monitor accuracy and reliability metrics
    - **User Behavior Analysis**: Understand how users interact with the system
    - **Optimization**: Identify areas for performance improvements
    - **Reporting**: Generate reports for stakeholders and management
    
    ## Insights Provided:
    - **Most Effective Models**: Which feature models provide best results
    - **Popular Search Types**: Most commonly used similarity search types
    - **Performance Bottlenecks**: Areas where optimization is needed
    - **Quality Trends**: Changes in image quality over time
    - **Usage Patterns**: Peak times and common search scenarios
    
    This data helps in:
    - **System Optimization**: Improve performance based on usage patterns
    - **Resource Planning**: Scale infrastructure based on demand
    - **Feature Development**: Prioritize new features based on user needs
    - **Quality Control**: Maintain high-quality search results
    - **User Experience**: Improve usability based on behavior analysis
    """
    try:
        logger.info("Image similarity stats request")
        
        return await image_similarity_service.get_similarity_stats()
        
    except Exception as e:
        logger.error("Image similarity stats error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get image similarity statistics")


# Audio Fingerprinting Endpoints


@router.post("/search/audio-fingerprint", response_model=AudioFingerprintResponse)
async def search_audio_fingerprint(
    query: AudioFingerprintQuery,
    request: Request,
    audio_fingerprinting_service: AudioFingerprintingService = Depends(get_audio_fingerprinting_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> AudioFingerprintResponse:
    """
    Perform audio fingerprint search for duplicate detection and music identification
    
    This endpoint provides comprehensive audio fingerprinting capabilities including:
    
    ## Input Options:
    - **Reference Asset ID**: Search using an existing audio asset as reference
    - **Reference Audio URL**: Search using an external audio URL
    - **Reference Fingerprint**: Search using pre-computed fingerprint data
    - **Audio Data Base64**: Search using raw audio data in base64 format
    
    ## Search Types:
    - **Duplicate Detection**: Find exact and near-duplicate audio files
    - **Music Identification**: Identify songs and match against music database
    - **Copyright Monitoring**: Detect copyrighted content usage
    - **Broadcast Monitoring**: Track broadcast content and advertisements
    - **Sample Detection**: Find audio samples and loops
    - **Cover Detection**: Identify cover versions and remixes
    - **Podcast Tracking**: Monitor podcast distribution
    - **Voice Matching**: Match voice recordings (for authorized use)
    - **Sound Effect Search**: Find similar sound effects
    - **Audio Quality Check**: Identify quality issues and degradation
    
    ## Fingerprinting Algorithms:
    - **Chromaprint**: Open-source acoustic fingerprinting (default)
    - **Echoprint**: Music identification optimized
    - **Dejavu**: High accuracy for exact matching
    - **Audfprint**: Robust to speed/pitch changes
    - **Panako**: Efficient for large-scale matching
    - **Shazam**: Commercial-grade music identification
    - **SoundHound**: Query by humming support
    - **MusicBrainz**: Open music database integration
    
    ## Match Types:
    - **Exact Match**: Identical audio content
    - **Partial Match**: Segment or portion matches
    - **Time-shifted**: Same content with time offset
    - **Speed-altered**: Playback speed variations
    - **Pitch-shifted**: Pitch modifications detected
    - **Filtered**: EQ or filter modifications
    - **Compressed**: Different compression levels
    - **Noisy**: Matches despite added noise
    - **Cover Version**: Different performance of same song
    - **Remix**: Remixed versions detected
    
    ## Advanced Features:
    - **Confidence Scoring**: Match confidence from 0.0 to 1.0
    - **Time Alignment**: Precise temporal alignment of matches
    - **Multi-algorithm Fusion**: Combine multiple algorithms for accuracy
    - **Segment Matching**: Match specific portions of audio
    - **Robustness**: Handles various audio transformations
    
    ## Response Includes:
    - Matching audio assets with confidence scores
    - Temporal alignment information
    - Music metadata (if identified)
    - Match statistics and performance metrics
    - Applied filters and search parameters
    
    ## Performance:
    - Fingerprint generation: ~100-500ms per minute of audio
    - Search time: ~50-200ms for millions of fingerprints
    - Optimized for real-time applications
    
    ## Use Cases:
    - **Content Protection**: Detect unauthorized use of audio
    - **Music Discovery**: Identify unknown songs
    - **Broadcast Compliance**: Monitor ad playback and content
    - **Quality Control**: Find degraded or altered audio
    - **Content Organization**: Group similar audio automatically
    - **Royalty Tracking**: Track music usage for payments
    """
    try:
        start_time = datetime.utcnow()
        
        logger.info(
            "audio_fingerprint_search_request",
            search_type=query.search_type,
            algorithm=query.fingerprint_algorithm,
            has_reference_asset=bool(query.reference_asset_id),
            has_reference_url=bool(query.reference_audio_url),
            has_fingerprint=bool(query.reference_fingerprint),
            has_audio_data=bool(query.audio_data_base64)
        )
        
        result = await audio_fingerprinting_service.search_audio_fingerprint(query)
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds() * 1000
        
        logger.info(
            "audio_fingerprint_search_completed",
            search_id=result.search_id,
            total_matches=result.total_matches,
            processing_time_ms=processing_time,
            algorithm_used=result.algorithm_used,
            fingerprint_version=result.fingerprint_version
        )
        
        return result
        
    except ValidationError as e:
        logger.error("audio_fingerprint_validation_error", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("audio_fingerprint_search_error", error=str(e))
        raise HTTPException(status_code=500, detail="Audio fingerprint search failed")


@router.post("/search/audio-fingerprint/analyze", response_model=AudioAnalysisResponse)
async def analyze_audio(
    request_data: AudioAnalysisRequest,
    request: Request,
    audio_fingerprinting_service: AudioFingerprintingService = Depends(get_audio_fingerprinting_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> AudioAnalysisResponse:
    """
    Analyze audio and extract comprehensive features and fingerprints
    
    This endpoint performs detailed analysis of an audio asset and extracts
    various types of features and fingerprints that can be used for search,
    classification, and quality assessment.
    
    ## Analysis Capabilities:
    
    ### Fingerprint Extraction:
    - **Multiple Algorithms**: Extract fingerprints using various algorithms
    - **Segment Fingerprints**: Generate fingerprints for audio segments
    - **Robust Fingerprints**: Create transformation-resistant fingerprints
    - **Lightweight Fingerprints**: Fast matching for real-time apps
    
    ### Feature Extraction:
    - **Chromagram**: Pitch class profiles for harmonic analysis
    - **MFCC**: Mel-frequency cepstral coefficients for timbre
    - **Spectral Features**: Centroid, rolloff, contrast, bandwidth
    - **Rhythm Features**: Tempo, beat positions, rhythm patterns
    - **Onset Detection**: Note and event onset times
    - **Zero Crossing Rate**: For speech/music discrimination
    - **RMS Energy**: Audio energy over time
    - **Spectral Contrast**: Frequency band energy differences
    - **Tonnetz**: Tonal centroid features for harmony
    
    ### Music Analysis:
    - **Key Detection**: Musical key identification
    - **Tempo Estimation**: BPM calculation
    - **Time Signature**: Meter detection (4/4, 3/4, etc.)
    - **Genre Classification**: Automatic genre detection
    - **Mood Analysis**: Emotional characteristics
    - **Instrument Detection**: Identify instruments present
    
    ### Audio Segmentation:
    - **Speech vs Music**: Classify audio segments
    - **Speaker Segments**: Identify different speakers
    - **Music Structure**: Verse, chorus, bridge detection
    - **Silence Detection**: Identify quiet sections
    - **Scene Changes**: Detect audio scene boundaries
    
    ### Quality Assessment:
    - **Overall Quality Score**: 0-100 quality rating
    - **Technical Metrics**: Sample rate, bit depth, codec
    - **Loudness Analysis**: LUFS, peak, dynamic range
    - **Frequency Response**: Spectrum analysis
    - **Distortion Detection**: THD, IMD measurements
    - **Noise Analysis**: SNR, noise floor
    - **Clipping Detection**: Identify clipped samples
    - **Phase Issues**: Detect phase problems
    
    ## Response Includes:
    - Extracted fingerprints for all requested algorithms
    - Comprehensive audio features and measurements
    - Segment analysis with timestamps
    - Music metadata and characteristics
    - Quality metrics and issues detected
    - Processing time and performance stats
    
    ## Processing Options:
    - **extract_fingerprints**: Generate audio fingerprints
    - **extract_features**: Extract acoustic features
    - **analyze_segments**: Perform segment-level analysis
    - **assess_quality**: Evaluate audio quality
    - **detect_music**: Extract music-specific features
    
    ## Use Cases:
    - **Content Preparation**: Pre-process audio for search
    - **Quality Control**: Assess audio quality issues
    - **Music Analysis**: Extract musical characteristics
    - **Content Classification**: Categorize audio content
    - **Feature Extraction**: Prepare features for ML models
    """
    try:
        start_time = datetime.utcnow()
        
        logger.info(
            "audio_analysis_request",
            asset_id=request_data.asset_id,
            extract_fingerprints=request_data.extract_fingerprints,
            extract_features=request_data.extract_features,
            analyze_segments=request_data.analyze_segments,
            assess_quality=request_data.assess_quality
        )
        
        result = await audio_fingerprinting_service.analyze_audio(request_data)
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds() * 1000
        
        logger.info(
            "audio_analysis_completed",
            asset_id=request_data.asset_id,
            processing_time_ms=processing_time,
            analysis_success=result.analysis_success,
            fingerprints_extracted=len(result.analysis.fingerprints),
            features_extracted=len(result.analysis.features)
        )
        
        return result
        
    except ValidationError as e:
        logger.error("audio_analysis_validation_error", asset_id=request_data.asset_id, error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("audio_analysis_error", asset_id=request_data.asset_id, error=str(e))
        raise HTTPException(status_code=500, detail="Audio analysis failed")


@router.get("/search/audio-fingerprint/stats", response_model=AudioFingerprintStats)
async def get_audio_fingerprint_stats(
    audio_fingerprinting_service: AudioFingerprintingService = Depends(get_audio_fingerprinting_service)
) -> AudioFingerprintStats:
    """
    Get comprehensive audio fingerprinting system statistics
    
    This endpoint provides detailed analytics and performance metrics for the
    audio fingerprinting system, helping administrators understand usage
    patterns, performance characteristics, and system health.
    
    ## Statistics Categories:
    
    ### Search Performance:
    - **Total Searches**: Number of fingerprint searches performed
    - **Average Search Time**: Mean time to complete searches
    - **Search Success Rate**: Percentage of successful searches
    - **Cache Hit Rate**: Fingerprint cache effectiveness
    
    ### Algorithm Performance:
    - **Algorithm Usage**: Distribution of algorithm usage
    - **Algorithm Accuracy**: Match accuracy by algorithm
    - **Algorithm Speed**: Processing time by algorithm
    - **Algorithm Reliability**: Success rates by algorithm
    
    ### Match Statistics:
    - **Total Matches Found**: Cumulative match count
    - **Average Confidence**: Mean match confidence scores
    - **Match Type Distribution**: Breakdown by match types
    - **False Positive Rate**: Estimated false match rate
    
    ### Audio Analysis:
    - **Total Audio Analyzed**: Hours of audio processed
    - **Average Processing Time**: Mean analysis time
    - **Feature Extraction Rate**: Features per second
    - **Quality Distribution**: Audio quality breakdown
    
    ### Content Statistics:
    - **Indexed Audio**: Total fingerprinted audio assets
    - **Database Size**: Fingerprint database metrics
    - **Content Types**: Distribution of audio types
    - **Duration Distribution**: Audio length statistics
    
    ### System Health:
    - **Error Rates**: Analysis and search failure rates
    - **Resource Usage**: CPU and memory utilization
    - **Queue Status**: Processing queue metrics
    - **Service Availability**: Uptime and reliability
    
    ### Usage Patterns:
    - **Peak Usage Times**: Temporal usage patterns
    - **User Distribution**: Usage by user types
    - **Search Type Popularity**: Most common search types
    - **Geographic Distribution**: Usage by region
    
    ## Key Metrics:
    - **Performance**: Search and analysis speeds
    - **Accuracy**: Match precision and recall
    - **Scale**: Database size and growth rate
    - **Reliability**: Error rates and uptime
    - **Efficiency**: Resource utilization
    
    ## Use Cases:
    - **Performance Monitoring**: Track system performance
    - **Capacity Planning**: Plan for scaling needs
    - **Algorithm Optimization**: Improve matching accuracy
    - **Quality Assurance**: Monitor system reliability
    - **Usage Analytics**: Understand user behavior
    - **Cost Analysis**: Optimize resource usage
    
    ## Insights Provided:
    - **Popular Algorithms**: Most effective algorithms
    - **Content Trends**: Types of audio being processed
    - **Performance Bottlenecks**: Areas needing optimization
    - **User Behavior**: How the system is being used
    - **Growth Patterns**: System usage trends
    
    This data helps in:
    - **System Optimization**: Improve performance
    - **Resource Planning**: Scale infrastructure
    - **Feature Development**: Prioritize improvements
    - **Quality Control**: Maintain high accuracy
    - **User Experience**: Enhance usability
    """
    try:
        logger.info("Audio fingerprint stats request")
        
        return await audio_fingerprinting_service.get_fingerprint_stats()
        
    except Exception as e:
        logger.error("Audio fingerprint stats error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get audio fingerprint statistics")
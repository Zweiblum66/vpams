"""
Pydantic schemas for the Search Engine Service
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum


class SearchType(str, Enum):
    """Supported search types"""
    BASIC = "basic"
    ADVANCED = "advanced"
    FUZZY = "fuzzy"
    FUZZY_PHRASE = "fuzzy_phrase"
    FUZZY_CROSS_FIELD = "fuzzy_cross_field"
    WILDCARD = "wildcard"
    PHRASE = "phrase"
    SEMANTIC = "semantic"
    PHONETIC = "phonetic"
    SYNONYM = "synonym"


class RankingType(str, Enum):
    """Supported ranking algorithms"""
    RELEVANCE = "relevance"
    RECENCY = "recency"
    POPULARITY = "popularity"
    HYBRID = "hybrid"
    CUSTOM = "custom"


class FuzzinessType(str, Enum):
    """Types of fuzziness algorithms"""
    AUTO = "AUTO"
    DISTANCE_1 = "1"
    DISTANCE_2 = "2"
    DISTANCE_3 = "3"
    CUSTOM = "0.5"


class FuzzyMatchType(str, Enum):
    """Types of fuzzy matching"""
    SINGLE_TERM = "single_term"
    MULTI_TERM = "multi_term"
    PHRASE = "phrase"
    CROSS_FIELD = "cross_field"
    ADAPTIVE = "adaptive"


class SortOrder(str, Enum):
    """Sort order options"""
    ASC = "asc"
    DESC = "desc"


class IndexType(str, Enum):
    """Available index types"""
    ASSETS = "assets"
    METADATA = "metadata"
    CONTENT = "content"
    ALL = "all"


class RankingConfig(BaseModel):
    """Configuration for search result ranking"""
    ranking_type: RankingType = Field(default=RankingType.HYBRID, description="Ranking algorithm to use")
    
    # Hybrid ranking weights
    hybrid_weights: Dict[str, float] = Field(
        default={
            "relevance": 1.0,
            "recency": 0.3,
            "popularity": 0.2,
            "quality": 0.1
        },
        description="Weights for hybrid ranking factors"
    )
    
    # Recency decay parameter
    recency_decay_days: int = Field(default=30, description="Days for exponential decay in recency scoring")
    
    # Popularity weights
    popularity_weights: Dict[str, float] = Field(
        default={
            "views": 1.0,
            "downloads": 2.0,
            "shares": 3.0,
            "ratings": 1.5
        },
        description="Weights for different popularity metrics"
    )
    
    # Custom ranking weights
    custom_weights: Dict[str, float] = Field(
        default={
            "field_boost": 1.0,
            "asset_type": 0.5,
            "quality": 0.5
        },
        description="Weights for custom ranking components"
    )
    
    # Field boosts for custom ranking
    field_boosts: Dict[str, float] = Field(
        default={
            "title": 2.0,
            "description": 1.0,
            "tags": 1.5
        },
        description="Boost scores for matches in specific fields"
    )
    
    # Asset type preferences
    asset_type_boosts: Dict[str, float] = Field(
        default={
            "video": 1.0,
            "image": 0.9,
            "audio": 0.8,
            "document": 0.7
        },
        description="Preference scores for different asset types"
    )


class FuzzySearchConfig(BaseModel):
    """Configuration for fuzzy search"""
    fuzziness: FuzzinessType = Field(default=FuzzinessType.AUTO, description="Fuzziness algorithm")
    prefix_length: int = Field(default=1, ge=0, le=10, description="Prefix length for fuzzy matching")
    max_expansions: int = Field(default=50, ge=1, le=1000, description="Maximum number of term expansions")
    transpositions: bool = Field(default=True, description="Enable transposition of adjacent characters")
    match_type: FuzzyMatchType = Field(default=FuzzyMatchType.ADAPTIVE, description="Type of fuzzy matching")
    field_boosts: Optional[Dict[str, float]] = Field(default=None, description="Field-specific boost values")
    performance_mode: str = Field(default="moderate", description="Performance mode: strict, moderate, loose")
    slop: int = Field(default=2, ge=0, le=10, description="Slop for phrase fuzzy matching")
    
    @validator('performance_mode')
    def validate_performance_mode(cls, v):
        if v not in ['strict', 'moderate', 'loose']:
            raise ValueError('Performance mode must be strict, moderate, or loose')
        return v


class SearchQuery(BaseModel):
    """Search query parameters"""
    query: str = Field(..., description="Search query string")
    search_type: SearchType = Field(default=SearchType.BASIC, description="Type of search to perform")
    indices: List[IndexType] = Field(default=[IndexType.ALL], description="Indices to search")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Additional filters")
    size: int = Field(default=20, ge=1, le=1000, description="Number of results to return")
    from_: int = Field(default=0, ge=0, alias="from", description="Offset for pagination")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="Sort order")
    highlight: bool = Field(default=True, description="Whether to highlight matches")
    include_aggregations: bool = Field(default=False, description="Include aggregations in response")
    timeout: Optional[int] = Field(default=None, ge=1, le=60, description="Search timeout in seconds")
    ranking_config: Optional[RankingConfig] = Field(default=None, description="Custom ranking configuration")
    include_ranking_explanation: bool = Field(default=False, description="Include ranking explanation in results")
    fuzzy_config: Optional[FuzzySearchConfig] = Field(default=None, description="Fuzzy search configuration")

    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        if len(v) > 1000:
            raise ValueError('Query too long (max 1000 characters)')
        return v.strip()


class MetadataFieldSearchQuery(BaseModel):
    """Metadata field-specific search query"""
    field_queries: List[Dict[str, str]] = Field(
        ..., 
        description="List of field-value pairs to search",
        example=[{"field": "title", "value": "test"}, {"field": "keywords", "value": "video"}]
    )
    operator: str = Field(default="AND", description="Operator to combine field queries (AND/OR)")
    indices: List[IndexType] = Field(default=[IndexType.METADATA], description="Indices to search")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Additional filters")
    size: int = Field(default=20, ge=1, le=1000, description="Number of results to return")
    from_: int = Field(default=0, ge=0, alias="from", description="Offset for pagination")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="Sort order")
    highlight: bool = Field(default=True, description="Whether to highlight matches")
    include_aggregations: bool = Field(default=False, description="Include aggregations in response")
    fuzzy: bool = Field(default=False, description="Enable fuzzy matching on field values")
    boost_fields: Optional[Dict[str, float]] = Field(
        default=None, 
        description="Field boosting weights",
        example={"title": 2.0, "description": 1.5}
    )

    @validator('operator')
    def validate_operator(cls, v):
        if v.upper() not in ['AND', 'OR']:
            raise ValueError('Operator must be AND or OR')
        return v.upper()

    @validator('field_queries')
    def validate_field_queries(cls, v):
        if not v:
            raise ValueError('At least one field query is required')
        for fq in v:
            if 'field' not in fq or 'value' not in fq:
                raise ValueError('Each field query must have "field" and "value" keys')
            if not fq['field'].strip() or not fq['value'].strip():
                raise ValueError('Field and value cannot be empty')
        return v


class AdvancedSearchQuery(BaseModel):
    """Advanced search query with multiple conditions"""
    must: Optional[List[Dict[str, Any]]] = Field(default=None, description="Must match conditions")
    should: Optional[List[Dict[str, Any]]] = Field(default=None, description="Should match conditions")
    must_not: Optional[List[Dict[str, Any]]] = Field(default=None, description="Must not match conditions")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Filter conditions")
    size: int = Field(default=20, ge=1, le=1000)
    from_: int = Field(default=0, ge=0, alias="from")
    sort_by: Optional[str] = Field(default=None)
    sort_order: SortOrder = Field(default=SortOrder.DESC)
    highlight: bool = Field(default=True)
    include_aggregations: bool = Field(default=False)


class SearchHit(BaseModel):
    """Individual search result"""
    id: str = Field(..., description="Document ID")
    index: str = Field(..., description="Source index")
    score: float = Field(..., description="Relevance score")
    source: Dict[str, Any] = Field(..., description="Document source")
    highlight: Optional[Dict[str, List[str]]] = Field(default=None, description="Highlighted snippets")
    ranking_explanation: Optional[Dict[str, Any]] = Field(default=None, description="Explanation of ranking factors")


class SearchAggregation(BaseModel):
    """Search aggregation result"""
    name: str = Field(..., description="Aggregation name")
    buckets: List[Dict[str, Any]] = Field(..., description="Aggregation buckets")


class SearchResponse(BaseModel):
    """Search response structure"""
    query: str = Field(..., description="Original query")
    total_hits: int = Field(..., description="Total number of matching documents")
    max_score: Optional[float] = Field(default=None, description="Maximum relevance score")
    hits: List[SearchHit] = Field(..., description="Search results")
    aggregations: Optional[List[SearchAggregation]] = Field(default=None, description="Aggregation results")
    took: int = Field(..., description="Time taken in milliseconds")
    timed_out: bool = Field(..., description="Whether the search timed out")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Results per page")
    total_pages: int = Field(..., description="Total number of pages")


class SuggestionQuery(BaseModel):
    """Search suggestion query"""
    text: str = Field(..., min_length=1, max_length=100, description="Text to get suggestions for")
    size: int = Field(default=5, ge=1, le=20, description="Number of suggestions to return")
    index_type: IndexType = Field(default=IndexType.ASSETS, description="Index to search for suggestions")


class SuggestionItem(BaseModel):
    """Individual suggestion item"""
    text: str = Field(..., description="Suggested text")
    score: float = Field(..., description="Suggestion score")


class SuggestionResponse(BaseModel):
    """Suggestion response"""
    suggestions: List[SuggestionItem] = Field(..., description="List of suggestions")
    took: int = Field(..., description="Time taken in milliseconds")


class IndexDocument(BaseModel):
    """Document to be indexed"""
    id: str = Field(..., description="Document ID")
    document: Dict[str, Any] = Field(..., description="Document to index")
    index_name: Optional[str] = Field(default=None, description="Target index name")


class BulkIndexRequest(BaseModel):
    """Bulk indexing request"""
    documents: List[IndexDocument] = Field(..., description="Documents to index")
    refresh: bool = Field(default=False, description="Whether to refresh indices after indexing")


class IndexingResponse(BaseModel):
    """Indexing operation response"""
    success: bool = Field(..., description="Whether the operation succeeded")
    document_id: str = Field(..., description="Document ID")
    index_name: str = Field(..., description="Target index name")
    version: Optional[int] = Field(default=None, description="Document version")
    result: str = Field(..., description="Operation result (created, updated, etc.)")


class BulkIndexingResponse(BaseModel):
    """Bulk indexing response"""
    success: bool = Field(..., description="Whether all operations succeeded")
    total_documents: int = Field(..., description="Total number of documents processed")
    successful_count: int = Field(..., description="Number of successful operations")
    failed_count: int = Field(..., description="Number of failed operations")
    errors: List[Dict[str, Any]] = Field(default=[], description="Error details for failed operations")
    took: int = Field(..., description="Time taken in milliseconds")


class DeleteResponse(BaseModel):
    """Document deletion response"""
    success: bool = Field(..., description="Whether the deletion succeeded")
    document_id: str = Field(..., description="Document ID")
    index_name: str = Field(..., description="Source index name")
    result: str = Field(..., description="Deletion result")


class IndexStats(BaseModel):
    """Index statistics"""
    index_name: str = Field(..., description="Index name")
    document_count: int = Field(..., description="Number of documents")
    store_size: str = Field(..., description="Storage size")
    primary_shards: int = Field(..., description="Number of primary shards")
    replica_shards: int = Field(..., description="Number of replica shards")
    status: str = Field(..., description="Index status")


class HealthResponse(BaseModel):
    """Service health response"""
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    opensearch_status: str = Field(..., description="OpenSearch cluster status")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")


class ErrorResponse(BaseModel):
    """Error response structure"""
    error: Dict[str, Any] = Field(..., description="Error details")


class FilterType(str, Enum):
    """Types of filters supported"""
    TERM = "term"
    TERMS = "terms"
    RANGE = "range"
    EXISTS = "exists"
    PREFIX = "prefix"
    WILDCARD = "wildcard"
    REGEXP = "regexp"
    NESTED = "nested"


class FilterCondition(BaseModel):
    """Individual filter condition"""
    field: str = Field(..., description="Field to filter on")
    type: FilterType = Field(..., description="Type of filter")
    value: Union[str, List[str], Dict[str, Any]] = Field(..., description="Filter value(s)")
    nested_path: Optional[str] = Field(default=None, description="Path for nested fields")
    
    @validator('value')
    def validate_value(cls, v, values):
        filter_type = values.get('type')
        if filter_type == FilterType.TERMS and not isinstance(v, list):
            raise ValueError('TERMS filter requires list value')
        if filter_type == FilterType.RANGE and not isinstance(v, dict):
            raise ValueError('RANGE filter requires dict value with gte/lte/gt/lt keys')
        return v


class FacetType(str, Enum):
    """Types of facets/aggregations supported"""
    TERMS = "terms"
    RANGE = "range"
    DATE_HISTOGRAM = "date_histogram"
    HISTOGRAM = "histogram"
    STATS = "stats"
    CARDINALITY = "cardinality"


class FacetConfig(BaseModel):
    """Configuration for a facet/aggregation"""
    name: str = Field(..., description="Facet name")
    field: str = Field(..., description="Field to aggregate on")
    type: FacetType = Field(..., description="Type of facet")
    size: Optional[int] = Field(default=10, description="Number of buckets for terms facet")
    interval: Optional[Union[int, str]] = Field(default=None, description="Interval for histogram facets")
    ranges: Optional[List[Dict[str, Any]]] = Field(default=None, description="Ranges for range facet")
    nested_path: Optional[str] = Field(default=None, description="Path for nested fields")
    missing_value: Optional[str] = Field(default=None, description="Value for missing documents")


class FilteredSearchQuery(BaseModel):
    """Enhanced search query with advanced filtering and faceting"""
    query: str = Field(..., description="Search query string")
    search_type: SearchType = Field(default=SearchType.BASIC, description="Type of search to perform")
    indices: List[IndexType] = Field(default=[IndexType.ALL], description="Indices to search")
    
    # Enhanced filtering
    filters: Optional[List[FilterCondition]] = Field(default=None, description="Filter conditions")
    post_filters: Optional[List[FilterCondition]] = Field(default=None, description="Post-filters (don't affect facets)")
    
    # Faceting
    facets: Optional[List[FacetConfig]] = Field(default=None, description="Facets to compute")
    
    # Pagination and sorting
    size: int = Field(default=20, ge=1, le=1000, description="Number of results to return")
    from_: int = Field(default=0, ge=0, alias="from", description="Offset for pagination")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="Sort order")
    
    # Other options
    highlight: bool = Field(default=True, description="Whether to highlight matches")
    include_source: bool = Field(default=True, description="Include full document source")
    source_fields: Optional[List[str]] = Field(default=None, description="Specific fields to include")
    ranking_config: Optional[RankingConfig] = Field(default=None, description="Custom ranking configuration")
    include_ranking_explanation: bool = Field(default=False, description="Include ranking explanation")
    timeout: Optional[int] = Field(default=None, ge=1, le=60, description="Search timeout in seconds")


class FacetBucket(BaseModel):
    """Individual facet bucket result"""
    key: Union[str, int, float] = Field(..., description="Bucket key")
    doc_count: int = Field(..., description="Number of documents in bucket")
    from_: Optional[Union[int, float]] = Field(default=None, alias="from", description="Range start")
    to: Optional[Union[int, float]] = Field(default=None, description="Range end")
    
    class Config:
        allow_population_by_field_name = True


class FacetResult(BaseModel):
    """Facet/aggregation result"""
    name: str = Field(..., description="Facet name")
    type: FacetType = Field(..., description="Facet type")
    buckets: Optional[List[FacetBucket]] = Field(default=None, description="Facet buckets")
    value: Optional[Union[int, float]] = Field(default=None, description="Value for metric facets")
    sum: Optional[float] = Field(default=None, description="Sum for stats facets")
    avg: Optional[float] = Field(default=None, description="Average for stats facets")
    min: Optional[float] = Field(default=None, description="Minimum for stats facets")
    max: Optional[float] = Field(default=None, description="Maximum for stats facets")
    count: Optional[int] = Field(default=None, description="Count for stats/cardinality facets")


class FilteredSearchResponse(BaseModel):
    """Enhanced search response with facets"""
    query: str = Field(..., description="Original query")
    total_hits: int = Field(..., description="Total number of matching documents")
    max_score: Optional[float] = Field(default=None, description="Maximum relevance score")
    hits: List[SearchHit] = Field(..., description="Search results")
    facets: Optional[List[FacetResult]] = Field(default=None, description="Facet results")
    applied_filters: Optional[List[FilterCondition]] = Field(default=None, description="Filters that were applied")
    took: int = Field(..., description="Time taken in milliseconds")
    timed_out: bool = Field(..., description="Whether the search timed out")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Results per page")
    total_pages: int = Field(..., description="Total number of pages")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional response metadata")


class SearchAnalytics(BaseModel):
    """Search analytics data"""
    query: str = Field(..., description="Search query")
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    results_count: int = Field(..., description="Number of results returned")
    response_time_ms: int = Field(..., description="Response time in milliseconds")
    filters_used: Optional[Dict[str, Any]] = Field(default=None, description="Filters applied")
    clicked_result: Optional[str] = Field(default=None, description="ID of clicked result")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Analytics timestamp")


class SavedSearchCreate(BaseModel):
    """Create a new saved search"""
    name: str = Field(..., min_length=1, max_length=255, description="Name for the saved search")
    description: Optional[str] = Field(default=None, max_length=1000, description="Description of the search")
    query: FilteredSearchQuery = Field(..., description="The search query to save")
    is_public: bool = Field(default=False, description="Whether this search is public")
    tags: Optional[List[str]] = Field(default=None, description="Tags for categorizing the search")
    notify_on_new_results: bool = Field(default=False, description="Send notifications for new results")
    
    @validator('tags')
    def validate_tags(cls, v):
        if v:
            # Remove duplicates and empty tags
            return list(set(tag.strip() for tag in v if tag.strip()))
        return v


class SavedSearchUpdate(BaseModel):
    """Update a saved search"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255, description="Name for the saved search")
    description: Optional[str] = Field(default=None, max_length=1000, description="Description of the search")
    query: Optional[FilteredSearchQuery] = Field(default=None, description="The search query to save")
    is_public: Optional[bool] = Field(default=None, description="Whether this search is public")
    tags: Optional[List[str]] = Field(default=None, description="Tags for categorizing the search")
    notify_on_new_results: Optional[bool] = Field(default=None, description="Send notifications for new results")


class SavedSearch(BaseModel):
    """Saved search response model"""
    id: str = Field(..., description="Unique identifier")
    user_id: str = Field(..., description="Owner user ID")
    name: str = Field(..., description="Name of the saved search")
    description: Optional[str] = Field(default=None, description="Description")
    query: FilteredSearchQuery = Field(..., description="The saved query")
    is_public: bool = Field(..., description="Whether this search is public")
    tags: List[str] = Field(default=[], description="Tags for categorization")
    notify_on_new_results: bool = Field(..., description="Notification setting")
    usage_count: int = Field(default=0, description="Number of times this search has been used")
    last_used_at: Optional[datetime] = Field(default=None, description="Last time this search was executed")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class SavedSearchList(BaseModel):
    """List of saved searches"""
    searches: List[SavedSearch] = Field(..., description="List of saved searches")
    total: int = Field(..., description="Total number of saved searches")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total pages")


class SavedSearchExecute(BaseModel):
    """Execute a saved search with optional overrides"""
    size: Optional[int] = Field(default=None, ge=1, le=1000, description="Override result size")
    from_: Optional[int] = Field(default=None, ge=0, alias="from", description="Override pagination offset")
    sort_by: Optional[str] = Field(default=None, description="Override sort field")
    sort_order: Optional[SortOrder] = Field(default=None, description="Override sort order")
    additional_filters: Optional[List[FilterCondition]] = Field(default=None, description="Additional filters to apply")


# Search History Schemas

class SearchHistoryEntry(BaseModel):
    """Search history entry response model"""
    id: str = Field(..., description="Unique identifier")
    user_id: str = Field(..., description="User who performed the search")
    query: str = Field(..., description="The search query")
    search_type: SearchType = Field(..., description="Type of search performed")
    indices: List[str] = Field(default=[], description="Indices that were searched")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Filters applied to the search")
    results_count: int = Field(default=0, description="Number of results returned")
    response_time_ms: int = Field(default=0, description="Response time in milliseconds")
    ip_address: Optional[str] = Field(default=None, description="IP address of the user")
    user_agent: Optional[str] = Field(default=None, description="User agent string")
    timestamp: datetime = Field(..., description="When the search was performed")


class SearchHistoryList(BaseModel):
    """List of search history entries"""
    entries: List[SearchHistoryEntry] = Field(..., description="List of search history entries")
    total: int = Field(..., description="Total number of entries")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total pages")


class SearchHistoryStats(BaseModel):
    """Search history statistics"""
    total_searches: int = Field(..., description="Total number of searches")
    unique_queries: int = Field(..., description="Number of unique queries")
    avg_response_time_ms: float = Field(..., description="Average response time in milliseconds")
    most_common_search_type: SearchType = Field(..., description="Most frequently used search type")
    top_queries: List[Dict[str, Any]] = Field(..., description="Top queries with counts")
    search_volume_by_day: List[Dict[str, Any]] = Field(..., description="Search volume by day")
    avg_results_per_search: float = Field(..., description="Average number of results per search")


class SearchHistoryCreate(BaseModel):
    """Create a new search history entry"""
    user_id: str = Field(..., description="User who performed the search")
    query: str = Field(..., description="The search query")
    search_type: SearchType = Field(..., description="Type of search performed")
    indices: List[str] = Field(default=[], description="Indices that were searched")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Filters applied to the search")
    results_count: int = Field(default=0, description="Number of results returned")
    response_time_ms: int = Field(default=0, description="Response time in milliseconds")
    ip_address: Optional[str] = Field(default=None, description="IP address of the user")
    user_agent: Optional[str] = Field(default=None, description="User agent string")


# Search Analytics Schemas

class SearchAnalyticsCreate(BaseModel):
    """Create a new search analytics entry"""
    query: str = Field(..., description="The search query")
    search_type: SearchType = Field(..., description="Type of search performed")
    user_id: Optional[str] = Field(default=None, description="User ID (if authenticated)")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    indices: List[str] = Field(default=[], description="Indices that were searched")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Filters applied")
    results_count: int = Field(default=0, description="Number of results returned")
    response_time_ms: int = Field(default=0, description="Response time in milliseconds")
    clicked_results: List[str] = Field(default=[], description="Asset IDs that were clicked")
    ip_address: Optional[str] = Field(default=None, description="IP address")
    user_agent: Optional[str] = Field(default=None, description="User agent string")
    referrer: Optional[str] = Field(default=None, description="HTTP referrer")
    location: Optional[Dict[str, Any]] = Field(default=None, description="Geolocation data")


class SearchAnalyticsEntry(BaseModel):
    """Search analytics entry response model"""
    id: str = Field(..., description="Unique identifier")
    query: str = Field(..., description="The search query")
    search_type: SearchType = Field(..., description="Type of search performed")
    user_id: Optional[str] = Field(default=None, description="User ID (if authenticated)")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    indices: List[str] = Field(default=[], description="Indices that were searched")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Filters applied")
    results_count: int = Field(default=0, description="Number of results returned")
    response_time_ms: int = Field(default=0, description="Response time in milliseconds")
    clicked_results: List[str] = Field(default=[], description="Asset IDs that were clicked")
    ip_address: Optional[str] = Field(default=None, description="IP address")
    user_agent: Optional[str] = Field(default=None, description="User agent string")
    referrer: Optional[str] = Field(default=None, description="HTTP referrer")
    location: Optional[Dict[str, Any]] = Field(default=None, description="Geolocation data")
    timestamp: datetime = Field(..., description="When the search was performed")


class SearchAnalyticsAggregation(BaseModel):
    """Search analytics aggregation response"""
    total_searches: int = Field(..., description="Total number of searches")
    unique_queries: int = Field(..., description="Number of unique queries")
    unique_users: int = Field(..., description="Number of unique users")
    unique_sessions: int = Field(..., description="Number of unique sessions")
    avg_response_time_ms: float = Field(..., description="Average response time")
    avg_results_per_search: float = Field(..., description="Average results per search")
    avg_clicks_per_search: float = Field(..., description="Average clicks per search")
    click_through_rate: float = Field(..., description="Click-through rate percentage")
    zero_result_rate: float = Field(..., description="Zero result rate percentage")
    top_queries: List[Dict[str, Any]] = Field(..., description="Most popular queries")
    top_filters: List[Dict[str, Any]] = Field(..., description="Most used filters")
    search_patterns: List[Dict[str, Any]] = Field(..., description="Search patterns by time")
    performance_metrics: Dict[str, Any] = Field(..., description="Performance metrics")


class SearchAnalyticsTimeRange(BaseModel):
    """Time range for analytics queries"""
    start_time: datetime = Field(..., description="Start of time range")
    end_time: datetime = Field(..., description="End of time range")
    interval: str = Field(default="1h", description="Aggregation interval (1h, 1d, 1w, 1M)")


class SearchAnalyticsFilter(BaseModel):
    """Filter for analytics queries"""
    search_type: Optional[SearchType] = Field(default=None, description="Filter by search type")
    user_id: Optional[str] = Field(default=None, description="Filter by user ID")
    query_contains: Optional[str] = Field(default=None, description="Filter queries containing text")
    min_results: Optional[int] = Field(default=None, description="Minimum result count")
    max_results: Optional[int] = Field(default=None, description="Maximum result count")
    min_response_time: Optional[int] = Field(default=None, description="Minimum response time")
    max_response_time: Optional[int] = Field(default=None, description="Maximum response time")
    indices: Optional[List[str]] = Field(default=None, description="Filter by indices")
    has_clicks: Optional[bool] = Field(default=None, description="Filter by whether search had clicks")


class SearchAnalyticsQuery(BaseModel):
    """Query parameters for search analytics"""
    time_range: SearchAnalyticsTimeRange = Field(..., description="Time range for analysis")
    filters: Optional[SearchAnalyticsFilter] = Field(default=None, description="Additional filters")
    group_by: Optional[List[str]] = Field(default=None, description="Group results by fields")
    metrics: Optional[List[str]] = Field(default=None, description="Specific metrics to calculate")
    limit: Optional[int] = Field(default=100, description="Limit for top results")


class SearchPerformanceMetrics(BaseModel):
    """Search performance metrics"""
    avg_response_time_ms: float = Field(..., description="Average response time")
    p50_response_time_ms: float = Field(..., description="50th percentile response time")
    p95_response_time_ms: float = Field(..., description="95th percentile response time")
    p99_response_time_ms: float = Field(..., description="99th percentile response time")
    slowest_queries: List[Dict[str, Any]] = Field(..., description="Slowest queries")
    fastest_queries: List[Dict[str, Any]] = Field(..., description="Fastest queries")
    error_rate: float = Field(..., description="Error rate percentage")
    timeout_rate: float = Field(..., description="Timeout rate percentage")


class SearchTrendData(BaseModel):
    """Search trend data over time"""
    timestamp: datetime = Field(..., description="Time point")
    search_count: int = Field(..., description="Number of searches at this time")
    unique_users: int = Field(..., description="Number of unique users")
    avg_response_time_ms: float = Field(..., description="Average response time")
    avg_results: float = Field(..., description="Average results per search")
    click_through_rate: float = Field(..., description="Click-through rate")


class SearchAnalyticsReport(BaseModel):
    """Comprehensive search analytics report"""
    summary: SearchAnalyticsAggregation = Field(..., description="Summary statistics")
    trends: List[SearchTrendData] = Field(..., description="Trend data over time")
    performance: SearchPerformanceMetrics = Field(..., description="Performance metrics")
    top_queries: List[Dict[str, Any]] = Field(..., description="Top queries with details")
    search_patterns: List[Dict[str, Any]] = Field(..., description="Search behavior patterns")
    user_segments: List[Dict[str, Any]] = Field(..., description="User segment analysis")
    generated_at: datetime = Field(..., description="Report generation time")
    time_range: SearchAnalyticsTimeRange = Field(..., description="Report time range")


class FuzzySearchQuery(BaseModel):
    """Dedicated fuzzy search query"""
    query: str = Field(..., description="Search query string")
    match_type: FuzzyMatchType = Field(default=FuzzyMatchType.ADAPTIVE, description="Type of fuzzy matching")
    fuzziness: FuzzinessType = Field(default=FuzzinessType.AUTO, description="Fuzziness algorithm")
    performance_mode: str = Field(default="moderate", description="Performance mode: strict, moderate, loose")
    fields: Optional[List[str]] = Field(default=None, description="Fields to search (default: all)")
    indices: List[IndexType] = Field(default=[IndexType.ALL], description="Indices to search")
    
    # Advanced fuzzy options
    prefix_length: int = Field(default=1, ge=0, le=10, description="Prefix length for fuzzy matching")
    max_expansions: int = Field(default=50, ge=1, le=1000, description="Maximum number of term expansions")
    transpositions: bool = Field(default=True, description="Enable transposition of adjacent characters")
    slop: int = Field(default=2, ge=0, le=10, description="Slop for phrase fuzzy matching")
    
    # Search options
    size: int = Field(default=20, ge=1, le=1000, description="Number of results to return")
    from_: int = Field(default=0, ge=0, alias="from", description="Offset for pagination")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="Sort order")
    highlight: bool = Field(default=True, description="Whether to highlight matches")
    include_suggestions: bool = Field(default=False, description="Include fuzzy suggestions")
    include_performance_info: bool = Field(default=False, description="Include performance analysis")
    
    @validator('performance_mode')
    def validate_performance_mode(cls, v):
        if v not in ['strict', 'moderate', 'loose']:
            raise ValueError('Performance mode must be strict, moderate, or loose')
        return v

    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        if len(v) > 1000:
            raise ValueError('Query too long (max 1000 characters)')
        return v.strip()


class FuzzySearchResponse(BaseModel):
    """Response from fuzzy search"""
    query: str = Field(..., description="Original query")
    match_type: FuzzyMatchType = Field(..., description="Type of fuzzy matching used")
    fuzziness: FuzzinessType = Field(..., description="Fuzziness algorithm used")
    total_hits: int = Field(..., description="Total number of matching documents")
    max_score: Optional[float] = Field(default=None, description="Maximum relevance score")
    hits: List[SearchHit] = Field(..., description="Search results")
    suggestions: Optional[List[Dict[str, Any]]] = Field(default=None, description="Fuzzy suggestions")
    performance_info: Optional[Dict[str, Any]] = Field(default=None, description="Performance analysis")
    took: int = Field(..., description="Time taken in milliseconds")
    timed_out: bool = Field(..., description="Whether the search timed out")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Results per page")
    total_pages: int = Field(..., description="Total number of pages")
    query_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Query analysis information")


class FuzzySuggestionQuery(BaseModel):
    """Query for fuzzy suggestions"""
    text: str = Field(..., min_length=1, max_length=100, description="Text to get fuzzy suggestions for")
    field: str = Field(default="_all", description="Field to search for suggestions")
    size: int = Field(default=5, ge=1, le=20, description="Number of suggestions to return")
    fuzziness: FuzzinessType = Field(default=FuzzinessType.AUTO, description="Fuzziness algorithm")
    include_popular: bool = Field(default=True, description="Include popular suggestions")
    include_recent: bool = Field(default=True, description="Include recent suggestions")


class FuzzySuggestionResponse(BaseModel):
    """Response from fuzzy suggestions"""
    text: str = Field(..., description="Original text")
    suggestions: List[Dict[str, Any]] = Field(..., description="Fuzzy suggestions")
    took: int = Field(..., description="Time taken in milliseconds")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class PhoneticAlgorithm(str, Enum):
    """Phonetic matching algorithms"""
    SOUNDEX = "soundex"
    METAPHONE = "metaphone"
    DOUBLE_METAPHONE = "double_metaphone"
    NYSIIS = "nysiis"
    PHONEX = "phonex"
    FUZZY_SOUNDEX = "fuzzy_soundex"
    BEIDER_MORSE = "beider_morse"


class PhoneticMatchType(str, Enum):
    """Types of phonetic matching"""
    SINGLE_TERM = "single_term"
    MULTI_TERM = "multi_term"
    PHRASE = "phrase"
    CROSS_FIELD = "cross_field"
    ADAPTIVE = "adaptive"


class PhoneticSearchQuery(BaseModel):
    """Phonetic search query parameters"""
    query: str = Field(..., description="Search query string")
    algorithm: PhoneticAlgorithm = Field(default=PhoneticAlgorithm.SOUNDEX, description="Phonetic algorithm to use")
    match_type: PhoneticMatchType = Field(default=PhoneticMatchType.ADAPTIVE, description="Type of phonetic matching")
    fields: Optional[List[str]] = Field(default=None, description="Fields to search (default: all)")
    indices: List[IndexType] = Field(default=[IndexType.ALL], description="Indices to search")
    
    # Search options
    size: int = Field(default=20, ge=1, le=1000, description="Number of results to return")
    from_: int = Field(default=0, ge=0, alias="from", description="Offset for pagination")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="Sort order")
    highlight: bool = Field(default=True, description="Whether to highlight matches")
    include_suggestions: bool = Field(default=False, description="Include phonetic suggestions")
    include_original_tokens: bool = Field(default=True, description="Include original tokens in results")
    include_phonetic_analysis: bool = Field(default=False, description="Include phonetic analysis")
    
    # Phonetic-specific options
    boost_exact_matches: float = Field(default=2.0, ge=0.1, le=10.0, description="Boost for exact matches")
    boost_phonetic_matches: float = Field(default=1.0, ge=0.1, le=10.0, description="Boost for phonetic matches")
    min_similarity: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum similarity threshold")
    use_fallback_search: bool = Field(default=True, description="Use fallback search if no phonetic matches")
    
    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        if len(v) > 1000:
            raise ValueError('Query too long (max 1000 characters)')
        return v.strip()


class PhoneticSearchResponse(BaseModel):
    """Response from phonetic search"""
    query: str = Field(..., description="Original query")
    algorithm: PhoneticAlgorithm = Field(..., description="Phonetic algorithm used")
    match_type: PhoneticMatchType = Field(..., description="Type of phonetic matching used")
    phonetic_tokens: List[str] = Field(..., description="Phonetic tokens generated from query")
    total_hits: int = Field(..., description="Total number of matching documents")
    max_score: Optional[float] = Field(default=None, description="Maximum relevance score")
    hits: List[SearchHit] = Field(..., description="Search results")
    suggestions: Optional[List[Dict[str, Any]]] = Field(default=None, description="Phonetic suggestions")
    phonetic_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Phonetic analysis information")
    took: int = Field(..., description="Time taken in milliseconds")
    timed_out: bool = Field(..., description="Whether the search timed out")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Results per page")
    total_pages: int = Field(..., description="Total number of pages")
    fallback_used: bool = Field(default=False, description="Whether fallback search was used")
    exact_matches: int = Field(default=0, description="Number of exact matches found")
    phonetic_matches: int = Field(default=0, description="Number of phonetic matches found")


class PhoneticSuggestionQuery(BaseModel):
    """Query for phonetic suggestions"""
    text: str = Field(..., min_length=1, max_length=100, description="Text to get phonetic suggestions for")
    field: str = Field(default="_all", description="Field to search for suggestions")
    size: int = Field(default=5, ge=1, le=20, description="Number of suggestions to return")
    algorithm: PhoneticAlgorithm = Field(default=PhoneticAlgorithm.SOUNDEX, description="Phonetic algorithm to use")
    include_similar: bool = Field(default=True, description="Include similar-sounding suggestions")
    include_common: bool = Field(default=True, description="Include common variations")
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")


class PhoneticSuggestionResponse(BaseModel):
    """Response from phonetic suggestions"""
    text: str = Field(..., description="Original text")
    algorithm: PhoneticAlgorithm = Field(..., description="Phonetic algorithm used")
    phonetic_code: str = Field(..., description="Phonetic code for the text")
    suggestions: List[Dict[str, Any]] = Field(..., description="Phonetic suggestions")
    took: int = Field(..., description="Time taken in milliseconds")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


# Synonym Support Schemas

class SynonymType(str, Enum):
    """Types of synonym expansion"""
    EXPLICIT = "explicit"         # Use predefined synonym lists
    WORDNET = "wordnet"          # Use WordNet linguistic database
    CUSTOM = "custom"            # Use custom synonym dictionaries
    CONTEXTUAL = "contextual"    # Use context-aware synonyms (domain-specific)
    HYBRID = "hybrid"            # Combine multiple synonym sources


class SynonymExpansionStrategy(str, Enum):
    """Strategies for synonym expansion"""
    REPLACE = "replace"          # Replace original terms with synonyms
    EXPAND = "expand"            # Add synonyms to original terms
    BOOST = "boost"              # Boost synonym matches with lower score
    FALLBACK = "fallback"        # Use synonyms only if no direct matches


class SynonymConfig(BaseModel):
    """Configuration for synonym search"""
    synonym_type: SynonymType = Field(default=SynonymType.HYBRID, description="Type of synonym expansion")
    expansion_strategy: SynonymExpansionStrategy = Field(default=SynonymExpansionStrategy.EXPAND, description="Strategy for synonym expansion")
    max_synonyms_per_term: int = Field(default=5, ge=1, le=20, description="Maximum synonyms per term")
    min_similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity for synonym matching")
    boost_original_terms: float = Field(default=1.0, ge=0.1, le=10.0, description="Boost factor for original terms")
    boost_synonyms: float = Field(default=0.8, ge=0.1, le=10.0, description="Boost factor for synonym matches")
    include_domain_specific: bool = Field(default=True, description="Include domain-specific synonyms")
    domain_context: Optional[str] = Field(default=None, description="Domain context for contextual synonyms")
    
    # Custom synonym dictionaries
    custom_synonyms: Optional[Dict[str, List[str]]] = Field(default=None, description="Custom synonym mappings")
    
    # WordNet specific settings
    wordnet_synsets: Optional[List[str]] = Field(default=None, description="Specific WordNet synsets to use")
    wordnet_pos_tags: Optional[List[str]] = Field(default=None, description="Part-of-speech tags for WordNet")
    
    # Performance settings
    enable_caching: bool = Field(default=True, description="Enable synonym caching")
    cache_ttl_seconds: int = Field(default=3600, ge=60, le=86400, description="Cache TTL in seconds")


class SynonymSearchQuery(BaseModel):
    """Synonym search query parameters"""
    query: str = Field(..., description="Search query string")
    synonym_config: Optional[SynonymConfig] = Field(default=None, description="Synonym configuration")
    fields: Optional[List[str]] = Field(default=None, description="Fields to search (default: all)")
    indices: List[IndexType] = Field(default=[IndexType.ALL], description="Indices to search")
    
    # Search options
    size: int = Field(default=20, ge=1, le=1000, description="Number of results to return")
    from_: int = Field(default=0, ge=0, alias="from", description="Offset for pagination")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="Sort order")
    highlight: bool = Field(default=True, description="Whether to highlight matches")
    include_synonym_analysis: bool = Field(default=False, description="Include synonym expansion analysis")
    include_original_query: bool = Field(default=True, description="Include original query in results")
    
    # Filtering options
    filters: Optional[List[FilterCondition]] = Field(default=None, description="Additional filters")
    
    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        if len(v) > 1000:
            raise ValueError('Query too long (max 1000 characters)')
        return v.strip()


class SynonymExpansion(BaseModel):
    """Information about synonym expansion for a term"""
    original_term: str = Field(..., description="Original search term")
    synonyms: List[str] = Field(..., description="List of synonyms found")
    synonym_type: SynonymType = Field(..., description="Type of synonym expansion used")
    similarity_scores: Optional[Dict[str, float]] = Field(default=None, description="Similarity scores for synonyms")
    source: str = Field(..., description="Source of synonyms (wordnet, custom, etc.)")
    pos_tag: Optional[str] = Field(default=None, description="Part-of-speech tag")
    synset_id: Optional[str] = Field(default=None, description="WordNet synset ID")
    domain_context: Optional[str] = Field(default=None, description="Domain context used")


class SynonymAnalysis(BaseModel):
    """Analysis of synonym expansion for the query"""
    original_query: str = Field(..., description="Original query")
    expanded_query: str = Field(..., description="Query after synonym expansion")
    term_expansions: List[SynonymExpansion] = Field(..., description="Synonym expansions for each term")
    expansion_strategy: SynonymExpansionStrategy = Field(..., description="Strategy used for expansion")
    total_synonyms_added: int = Field(..., description="Total number of synonyms added")
    expansion_time_ms: int = Field(..., description="Time taken for expansion in milliseconds")
    cache_hit_rate: float = Field(..., description="Cache hit rate for synonym lookups")
    
    # Query characteristics
    query_characteristics: Dict[str, Any] = Field(default_factory=dict, description="Analysis of query characteristics")


class SynonymSearchResponse(BaseModel):
    """Response from synonym search"""
    query: str = Field(..., description="Original query")
    expanded_query: str = Field(..., description="Query after synonym expansion")
    total_hits: int = Field(..., description="Total number of matching documents")
    max_score: Optional[float] = Field(default=None, description="Maximum relevance score")
    hits: List[SearchHit] = Field(..., description="Search results")
    synonym_analysis: Optional[SynonymAnalysis] = Field(default=None, description="Synonym expansion analysis")
    took: int = Field(..., description="Time taken in milliseconds")
    timed_out: bool = Field(..., description="Whether the search timed out")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Results per page")
    total_pages: int = Field(..., description="Total number of pages")
    
    # Result breakdown
    original_matches: int = Field(default=0, description="Matches from original terms")
    synonym_matches: int = Field(default=0, description="Matches from synonyms")
    hybrid_matches: int = Field(default=0, description="Matches from both original and synonyms")


class SynonymSuggestionQuery(BaseModel):
    """Query for synonym suggestions"""
    term: str = Field(..., min_length=1, max_length=100, description="Term to get synonyms for")
    synonym_type: SynonymType = Field(default=SynonymType.HYBRID, description="Type of synonym expansion")
    size: int = Field(default=10, ge=1, le=50, description="Number of synonyms to return")
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")
    include_definitions: bool = Field(default=False, description="Include definitions for synonyms")
    include_examples: bool = Field(default=False, description="Include usage examples")
    domain_context: Optional[str] = Field(default=None, description="Domain context for contextual synonyms")
    pos_tag: Optional[str] = Field(default=None, description="Part-of-speech tag filter")


class SynonymSuggestion(BaseModel):
    """Individual synonym suggestion"""
    term: str = Field(..., description="Synonym term")
    similarity_score: float = Field(..., description="Similarity score to original term")
    frequency: int = Field(default=0, description="Usage frequency in corpus")
    synonym_type: SynonymType = Field(..., description="Type of synonym")
    source: str = Field(..., description="Source of synonym")
    pos_tag: Optional[str] = Field(default=None, description="Part-of-speech tag")
    definition: Optional[str] = Field(default=None, description="Definition of the synonym")
    examples: Optional[List[str]] = Field(default=None, description="Usage examples")
    domain_context: Optional[str] = Field(default=None, description="Domain context")


class SynonymSuggestionResponse(BaseModel):
    """Response from synonym suggestions"""
    term: str = Field(..., description="Original term")
    synonyms: List[SynonymSuggestion] = Field(..., description="List of synonyms")
    synonym_type: SynonymType = Field(..., description="Type of synonym expansion used")
    total_synonyms: int = Field(..., description="Total number of synonyms available")
    took: int = Field(..., description="Time taken in milliseconds")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class SynonymDictionary(BaseModel):
    """Synonym dictionary entry"""
    term: str = Field(..., description="Original term")
    synonyms: List[str] = Field(..., description="List of synonyms")
    domain: Optional[str] = Field(default=None, description="Domain context")
    pos_tag: Optional[str] = Field(default=None, description="Part-of-speech tag")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in synonym mappings")
    source: str = Field(..., description="Source of synonym mapping")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")


class SynonymDictionaryCreate(BaseModel):
    """Create a new synonym dictionary entry"""
    term: str = Field(..., min_length=1, max_length=100, description="Original term")
    synonyms: List[str] = Field(..., min_items=1, description="List of synonyms")
    domain: Optional[str] = Field(default=None, description="Domain context")
    pos_tag: Optional[str] = Field(default=None, description="Part-of-speech tag")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in synonym mappings")
    source: str = Field(default="custom", description="Source of synonym mapping")
    
    @validator('synonyms')
    def validate_synonyms(cls, v):
        if not v:
            raise ValueError('At least one synonym is required')
        # Remove duplicates and empty strings
        cleaned = list(set(s.strip() for s in v if s.strip()))
        if not cleaned:
            raise ValueError('At least one non-empty synonym is required')
        return cleaned


class SynonymDictionaryUpdate(BaseModel):
    """Update a synonym dictionary entry"""
    synonyms: Optional[List[str]] = Field(default=None, description="Updated list of synonyms")
    domain: Optional[str] = Field(default=None, description="Domain context")
    pos_tag: Optional[str] = Field(default=None, description="Part-of-speech tag")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Confidence in synonym mappings")
    source: Optional[str] = Field(default=None, description="Source of synonym mapping")


class SynonymDictionaryList(BaseModel):
    """List of synonym dictionary entries"""
    entries: List[SynonymDictionary] = Field(..., description="List of synonym entries")
    total: int = Field(..., description="Total number of entries")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total pages")


class SynonymStats(BaseModel):
    """Statistics about synonym usage"""
    total_synonyms: int = Field(..., description="Total number of synonym mappings")
    total_terms: int = Field(..., description="Total number of terms with synonyms")
    avg_synonyms_per_term: float = Field(..., description="Average number of synonyms per term")
    most_common_domains: List[Dict[str, Any]] = Field(..., description="Most common domains")
    synonym_usage_stats: Dict[str, Any] = Field(..., description="Usage statistics")
    cache_stats: Dict[str, Any] = Field(..., description="Cache performance statistics")
    performance_metrics: Dict[str, Any] = Field(..., description="Performance metrics")


# Search Templates Schemas

class SearchTemplateType(str, Enum):
    """Types of search templates"""
    BASIC = "basic"              # Simple search with basic filters
    ADVANCED = "advanced"        # Complex search with multiple criteria
    FILTERED = "filtered"        # Search with predefined filters and facets
    FUZZY = "fuzzy"             # Fuzzy search with specific configuration
    PHONETIC = "phonetic"       # Phonetic search with algorithm settings
    SYNONYM = "synonym"         # Synonym search with expansion settings
    NATURAL_LANGUAGE = "natural_language"  # NLP-powered search
    METADATA_FOCUSED = "metadata_focused"  # Metadata field-specific search
    CUSTOM = "custom"           # User-defined custom search


class SearchTemplateCategory(str, Enum):
    """Categories for organizing search templates"""
    GENERAL = "general"         # General-purpose searches
    MEDIA_TYPE = "media_type"   # Video, audio, image specific
    WORKFLOW = "workflow"       # Workflow-specific searches
    TECHNICAL = "technical"     # Technical metadata searches
    EDITORIAL = "editorial"     # Editorial workflow searches
    ARCHIVE = "archive"         # Archive and storage searches
    RIGHTS = "rights"           # Rights and licensing searches
    CUSTOM = "custom"           # Custom user categories


class SearchTemplateConfig(BaseModel):
    """Configuration for search template"""
    # Basic search configuration
    search_type: SearchType = Field(default=SearchType.BASIC, description="Type of search")
    default_query: Optional[str] = Field(default=None, description="Default query text")
    
    # Index and field configuration
    indices: List[IndexType] = Field(default=[IndexType.ALL], description="Default indices to search")
    fields: Optional[List[str]] = Field(default=None, description="Specific fields to search")
    
    # Filter and facet configuration
    default_filters: Optional[List[FilterCondition]] = Field(default=None, description="Default filters")
    facets: Optional[List[FacetConfig]] = Field(default=None, description="Facet configurations")
    
    # Search-specific configurations
    fuzzy_config: Optional[FuzzySearchConfig] = Field(default=None, description="Fuzzy search configuration")
    synonym_config: Optional[SynonymConfig] = Field(default=None, description="Synonym search configuration")
    ranking_config: Optional[RankingConfig] = Field(default=None, description="Ranking configuration")
    
    # UI and display settings
    default_sort_by: Optional[str] = Field(default=None, description="Default sort field")
    default_sort_order: SortOrder = Field(default=SortOrder.DESC, description="Default sort order")
    default_page_size: int = Field(default=20, ge=1, le=100, description="Default page size")
    
    # Advanced settings
    highlight_enabled: bool = Field(default=True, description="Enable highlighting by default")
    include_aggregations: bool = Field(default=False, description="Include aggregations by default")
    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=60, description="Default timeout")
    
    # Template-specific metadata
    required_parameters: Optional[List[str]] = Field(default=None, description="Required parameters for template")
    optional_parameters: Optional[List[str]] = Field(default=None, description="Optional parameters for template")
    parameter_defaults: Optional[Dict[str, Any]] = Field(default=None, description="Default values for parameters")
    
    # Usage hints and documentation
    usage_hints: Optional[List[str]] = Field(default=None, description="Usage hints for the template")
    example_queries: Optional[List[str]] = Field(default=None, description="Example queries for the template")


class SearchTemplateCreate(BaseModel):
    """Create a new search template"""
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(default=None, max_length=1000, description="Template description")
    category: SearchTemplateCategory = Field(..., description="Template category")
    template_type: SearchTemplateType = Field(..., description="Template type")
    config: SearchTemplateConfig = Field(..., description="Template configuration")
    
    # Visibility and sharing
    is_public: bool = Field(default=False, description="Whether template is public")
    is_system: bool = Field(default=False, description="Whether template is system-provided")
    shared_with_groups: Optional[List[str]] = Field(default=None, description="Groups with access")
    
    # Metadata
    tags: Optional[List[str]] = Field(default=None, description="Tags for categorization")
    icon: Optional[str] = Field(default=None, description="Icon identifier")
    color: Optional[str] = Field(default=None, description="Color theme")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Template name cannot be empty')
        return v.strip()
    
    @validator('tags')
    def validate_tags(cls, v):
        if v:
            # Remove duplicates and empty tags
            return list(set(tag.strip() for tag in v if tag.strip()))
        return v


class SearchTemplateUpdate(BaseModel):
    """Update a search template"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(default=None, max_length=1000, description="Template description")
    category: Optional[SearchTemplateCategory] = Field(default=None, description="Template category")
    template_type: Optional[SearchTemplateType] = Field(default=None, description="Template type")
    config: Optional[SearchTemplateConfig] = Field(default=None, description="Template configuration")
    
    # Visibility and sharing
    is_public: Optional[bool] = Field(default=None, description="Whether template is public")
    shared_with_groups: Optional[List[str]] = Field(default=None, description="Groups with access")
    
    # Metadata
    tags: Optional[List[str]] = Field(default=None, description="Tags for categorization")
    icon: Optional[str] = Field(default=None, description="Icon identifier")
    color: Optional[str] = Field(default=None, description="Color theme")


class SearchTemplate(BaseModel):
    """Search template response model"""
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(default=None, description="Template description")
    category: SearchTemplateCategory = Field(..., description="Template category")
    template_type: SearchTemplateType = Field(..., description="Template type")
    config: SearchTemplateConfig = Field(..., description="Template configuration")
    
    # Ownership and sharing
    owner_id: str = Field(..., description="Template owner ID")
    is_public: bool = Field(..., description="Whether template is public")
    is_system: bool = Field(..., description="Whether template is system-provided")
    shared_with_groups: List[str] = Field(default=[], description="Groups with access")
    
    # Metadata
    tags: List[str] = Field(default=[], description="Tags for categorization")
    icon: Optional[str] = Field(default=None, description="Icon identifier")
    color: Optional[str] = Field(default=None, description="Color theme")
    
    # Usage statistics
    usage_count: int = Field(default=0, description="Number of times template has been used")
    last_used_at: Optional[datetime] = Field(default=None, description="Last time template was used")
    favorite_count: int = Field(default=0, description="Number of users who favorited this template")
    
    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    # Version information
    version: int = Field(default=1, description="Template version")
    is_active: bool = Field(default=True, description="Whether template is active")


class SearchTemplateList(BaseModel):
    """List of search templates"""
    templates: List[SearchTemplate] = Field(..., description="List of search templates")
    total: int = Field(..., description="Total number of templates")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total pages")
    categories: List[Dict[str, Any]] = Field(default=[], description="Available categories with counts")
    tags: List[Dict[str, Any]] = Field(default=[], description="Available tags with counts")


class SearchTemplateExecute(BaseModel):
    """Execute a search template"""
    # Parameter overrides
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Template parameters")
    query_override: Optional[str] = Field(default=None, description="Override default query")
    
    # Search execution settings
    size: Optional[int] = Field(default=None, ge=1, le=1000, description="Override result size")
    from_: Optional[int] = Field(default=None, ge=0, alias="from", description="Override pagination offset")
    sort_by: Optional[str] = Field(default=None, description="Override sort field")
    sort_order: Optional[SortOrder] = Field(default=None, description="Override sort order")
    
    # Additional filters
    additional_filters: Optional[List[FilterCondition]] = Field(default=None, description="Additional filters")
    
    # Execution options
    include_template_info: bool = Field(default=False, description="Include template information in response")
    track_usage: bool = Field(default=True, description="Track template usage statistics")


class SearchTemplateExecuteResponse(BaseModel):
    """Response from executing a search template"""
    # Template information
    template_id: str = Field(..., description="Template ID")
    template_name: str = Field(..., description="Template name")
    template_info: Optional[Dict[str, Any]] = Field(default=None, description="Template metadata")
    
    # Search results (using existing search response structure)
    query: str = Field(..., description="Executed query")
    total_hits: int = Field(..., description="Total number of matching documents")
    max_score: Optional[float] = Field(default=None, description="Maximum relevance score")
    hits: List[SearchHit] = Field(..., description="Search results")
    facets: Optional[List[FacetResult]] = Field(default=None, description="Facet results")
    
    # Execution metadata
    parameters_used: Dict[str, Any] = Field(default_factory=dict, description="Parameters used in execution")
    filters_applied: Optional[List[FilterCondition]] = Field(default=None, description="Filters applied")
    took: int = Field(..., description="Time taken in milliseconds")
    timed_out: bool = Field(..., description="Whether search timed out")
    
    # Pagination
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Results per page")
    total_pages: int = Field(..., description="Total pages")


class SearchTemplateFavorite(BaseModel):
    """User's favorite search template"""
    user_id: str = Field(..., description="User ID")
    template_id: str = Field(..., description="Template ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When favorited")
    custom_name: Optional[str] = Field(default=None, description="User's custom name for template")
    notes: Optional[str] = Field(default=None, description="User's notes about template")


class SearchTemplateStats(BaseModel):
    """Statistics about search template usage"""
    total_templates: int = Field(..., description="Total number of templates")
    public_templates: int = Field(..., description="Number of public templates")
    private_templates: int = Field(..., description="Number of private templates")
    system_templates: int = Field(..., description="Number of system templates")
    
    # Usage statistics
    total_executions: int = Field(..., description="Total template executions")
    unique_users: int = Field(..., description="Number of unique users")
    avg_executions_per_template: float = Field(..., description="Average executions per template")
    avg_executions_per_user: float = Field(..., description="Average executions per user")
    
    # Category breakdown
    category_distribution: List[Dict[str, Any]] = Field(..., description="Templates by category")
    type_distribution: List[Dict[str, Any]] = Field(..., description="Templates by type")
    
    # Most popular templates
    most_used_templates: List[Dict[str, Any]] = Field(..., description="Most frequently used templates")
    most_favorited_templates: List[Dict[str, Any]] = Field(..., description="Most favorited templates")
    
    # Recent activity
    recent_activity: List[Dict[str, Any]] = Field(..., description="Recent template activity")
    
    # Performance metrics
    avg_execution_time_ms: float = Field(..., description="Average execution time")
    success_rate: float = Field(..., description="Template execution success rate")


class SearchTemplateImport(BaseModel):
    """Import search templates from file or URL"""
    source_type: str = Field(..., description="Source type: file, url, or json")
    source_data: Union[str, Dict[str, Any]] = Field(..., description="Source data")
    import_options: Optional[Dict[str, Any]] = Field(default=None, description="Import options")
    overwrite_existing: bool = Field(default=False, description="Overwrite existing templates")
    make_public: bool = Field(default=False, description="Make imported templates public")
    category_override: Optional[SearchTemplateCategory] = Field(default=None, description="Override category")


class SearchTemplateExport(BaseModel):
    """Export search templates"""
    template_ids: Optional[List[str]] = Field(default=None, description="Specific template IDs to export")
    categories: Optional[List[SearchTemplateCategory]] = Field(default=None, description="Categories to export")
    include_usage_stats: bool = Field(default=False, description="Include usage statistics")
    include_private: bool = Field(default=False, description="Include private templates")
    export_format: str = Field(default="json", description="Export format: json, yaml, or csv")


class SearchTemplateShare(BaseModel):
    """Share search template with users or groups"""
    template_id: str = Field(..., description="Template ID to share")
    share_with_users: Optional[List[str]] = Field(default=None, description="User IDs to share with")
    share_with_groups: Optional[List[str]] = Field(default=None, description="Group IDs to share with")
    permissions: List[str] = Field(default=["read"], description="Permissions to grant")
    message: Optional[str] = Field(default=None, description="Message to recipients")
    expires_at: Optional[datetime] = Field(default=None, description="Share expiration date")


# Timecode Search Schemas
class TimecodeFormat(str, Enum):
    """Supported timecode formats"""
    DROP_FRAME = "drop_frame"  # 29.97fps drop frame
    NON_DROP_FRAME = "non_drop_frame"  # 30fps non-drop frame
    FILM = "film"  # 24fps film
    PAL = "pal"  # 25fps PAL
    NTSC = "ntsc"  # 29.97fps NTSC
    CUSTOM = "custom"  # Custom frame rate


class TimecodeRangeType(str, Enum):
    """Types of timecode range searches"""
    EXACT = "exact"  # Exact timecode match
    RANGE = "range"  # Within a specific range
    DURATION = "duration"  # Assets with specific duration
    OVERLAP = "overlap"  # Assets that overlap with range
    CONTAINS = "contains"  # Assets that contain the range
    WITHIN = "within"  # Assets completely within range


class TimecodeSearchType(str, Enum):
    """Types of timecode searches"""
    SIMPLE = "simple"  # Simple timecode search
    ADVANCED = "advanced"  # Advanced timecode search with multiple criteria
    SEGMENT = "segment"  # Search for segments within media
    MARKER = "marker"  # Search based on markers/chapters
    SUBTITLE = "subtitle"  # Search based on subtitle timecodes
    METADATA = "metadata"  # Search based on timecode metadata


class Timecode(BaseModel):
    """Timecode representation"""
    hours: int = Field(..., ge=0, le=23, description="Hours component")
    minutes: int = Field(..., ge=0, le=59, description="Minutes component")
    seconds: int = Field(..., ge=0, le=59, description="Seconds component")
    frames: int = Field(..., ge=0, description="Frames component")
    format: TimecodeFormat = Field(default=TimecodeFormat.NON_DROP_FRAME, description="Timecode format")
    frame_rate: Optional[float] = Field(default=None, description="Custom frame rate for CUSTOM format")
    
    @validator('frames')
    def validate_frames(cls, v, values):
        """Validate frames based on format"""
        if 'format' in values:
            format_type = values['format']
            if format_type == TimecodeFormat.FILM and v >= 24:
                raise ValueError("Frames must be less than 24 for FILM format")
            elif format_type == TimecodeFormat.PAL and v >= 25:
                raise ValueError("Frames must be less than 25 for PAL format")
            elif format_type in [TimecodeFormat.NTSC, TimecodeFormat.DROP_FRAME] and v >= 30:
                raise ValueError("Frames must be less than 30 for NTSC/DROP_FRAME format")
            elif format_type == TimecodeFormat.NON_DROP_FRAME and v >= 30:
                raise ValueError("Frames must be less than 30 for NON_DROP_FRAME format")
        return v
    
    def to_seconds(self) -> float:
        """Convert timecode to total seconds"""
        frame_rate = self.frame_rate
        if frame_rate is None:
            frame_rate_map = {
                TimecodeFormat.FILM: 24.0,
                TimecodeFormat.PAL: 25.0,
                TimecodeFormat.NTSC: 29.97,
                TimecodeFormat.DROP_FRAME: 29.97,
                TimecodeFormat.NON_DROP_FRAME: 30.0
            }
            frame_rate = frame_rate_map.get(self.format, 30.0)
        
        total_seconds = (self.hours * 3600 + 
                        self.minutes * 60 + 
                        self.seconds + 
                        self.frames / frame_rate)
        return total_seconds
    
    def to_frames(self) -> int:
        """Convert timecode to total frames"""
        frame_rate = self.frame_rate
        if frame_rate is None:
            frame_rate_map = {
                TimecodeFormat.FILM: 24,
                TimecodeFormat.PAL: 25,
                TimecodeFormat.NTSC: 30,  # Simplified for calculation
                TimecodeFormat.DROP_FRAME: 30,
                TimecodeFormat.NON_DROP_FRAME: 30
            }
            frame_rate = frame_rate_map.get(self.format, 30)
        
        total_frames = (self.hours * 3600 * frame_rate + 
                       self.minutes * 60 * frame_rate + 
                       self.seconds * frame_rate + 
                       self.frames)
        return int(total_frames)
    
    def __str__(self) -> str:
        """String representation in HH:MM:SS:FF format"""
        separator = ";" if self.format == TimecodeFormat.DROP_FRAME else ":"
        return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}{separator}{self.frames:02d}"
    
    @classmethod
    def from_string(cls, timecode_str: str, format: TimecodeFormat = TimecodeFormat.NON_DROP_FRAME) -> 'Timecode':
        """Create timecode from string representation"""
        # Handle both : and ; separators
        if ";" in timecode_str:
            parts = timecode_str.replace(";", ":").split(":")
            format = TimecodeFormat.DROP_FRAME
        else:
            parts = timecode_str.split(":")
        
        if len(parts) != 4:
            raise ValueError("Timecode must be in HH:MM:SS:FF format")
        
        try:
            hours, minutes, seconds, frames = map(int, parts)
            return cls(
                hours=hours,
                minutes=minutes,
                seconds=seconds,
                frames=frames,
                format=format
            )
        except ValueError:
            raise ValueError("Invalid timecode format")
    
    @classmethod
    def from_seconds(cls, seconds: float, format: TimecodeFormat = TimecodeFormat.NON_DROP_FRAME) -> 'Timecode':
        """Create timecode from total seconds"""
        frame_rate_map = {
            TimecodeFormat.FILM: 24.0,
            TimecodeFormat.PAL: 25.0,
            TimecodeFormat.NTSC: 29.97,
            TimecodeFormat.DROP_FRAME: 29.97,
            TimecodeFormat.NON_DROP_FRAME: 30.0
        }
        frame_rate = frame_rate_map.get(format, 30.0)
        
        total_frames = int(seconds * frame_rate)
        
        hours = total_frames // (3600 * int(frame_rate))
        remaining_frames = total_frames % (3600 * int(frame_rate))
        
        minutes = remaining_frames // (60 * int(frame_rate))
        remaining_frames = remaining_frames % (60 * int(frame_rate))
        
        secs = remaining_frames // int(frame_rate)
        frames = remaining_frames % int(frame_rate)
        
        return cls(
            hours=hours,
            minutes=minutes,
            seconds=secs,
            frames=frames,
            format=format
        )


class TimecodeRange(BaseModel):
    """Timecode range for search queries"""
    start: Timecode = Field(..., description="Start timecode")
    end: Timecode = Field(..., description="End timecode")
    type: TimecodeRangeType = Field(default=TimecodeRangeType.RANGE, description="Type of range search")
    
    @validator('end')
    def validate_end_after_start(cls, v, values):
        """Validate end is after start"""
        if 'start' in values and v.to_seconds() <= values['start'].to_seconds():
            raise ValueError("End timecode must be after start timecode")
        return v
    
    def duration(self) -> float:
        """Get duration in seconds"""
        return self.end.to_seconds() - self.start.to_seconds()
    
    def duration_frames(self) -> int:
        """Get duration in frames"""
        return self.end.to_frames() - self.start.to_frames()
    
    def contains_timecode(self, timecode: Timecode) -> bool:
        """Check if range contains a specific timecode"""
        tc_seconds = timecode.to_seconds()
        return self.start.to_seconds() <= tc_seconds <= self.end.to_seconds()
    
    def overlaps_with(self, other: 'TimecodeRange') -> bool:
        """Check if this range overlaps with another"""
        return (self.start.to_seconds() <= other.end.to_seconds() and 
                self.end.to_seconds() >= other.start.to_seconds())


class TimecodeSearchQuery(BaseModel):
    """Timecode-based search query"""
    search_type: TimecodeSearchType = Field(default=TimecodeSearchType.SIMPLE, description="Type of timecode search")
    
    # Basic timecode search
    timecode: Optional[Timecode] = Field(default=None, description="Specific timecode to search for")
    timecode_range: Optional[TimecodeRange] = Field(default=None, description="Timecode range to search within")
    
    # Duration search
    min_duration: Optional[float] = Field(default=None, description="Minimum duration in seconds")
    max_duration: Optional[float] = Field(default=None, description="Maximum duration in seconds")
    duration_format: TimecodeFormat = Field(default=TimecodeFormat.NON_DROP_FRAME, description="Duration format")
    
    # Advanced search options
    tolerance_seconds: float = Field(default=0.5, description="Tolerance for timecode matching in seconds")
    tolerance_frames: int = Field(default=1, description="Tolerance for timecode matching in frames")
    
    # Asset type filters
    asset_types: Optional[List[str]] = Field(default=None, description="Asset types to search (video, audio)")
    video_formats: Optional[List[str]] = Field(default=None, description="Video formats to include")
    audio_formats: Optional[List[str]] = Field(default=None, description="Audio formats to include")
    
    # Metadata filters
    frame_rates: Optional[List[float]] = Field(default=None, description="Frame rates to filter by")
    resolutions: Optional[List[str]] = Field(default=None, description="Video resolutions to filter by")
    
    # Segment search
    segment_markers: Optional[List[str]] = Field(default=None, description="Marker names to search for")
    chapter_titles: Optional[List[str]] = Field(default=None, description="Chapter titles to search for")
    
    # Subtitle search
    subtitle_text: Optional[str] = Field(default=None, description="Subtitle text to search for")
    subtitle_language: Optional[str] = Field(default=None, description="Subtitle language")
    
    # Search configuration
    indices: List[IndexType] = Field(default=[IndexType.ASSETS], description="Indices to search")
    fields: Optional[List[str]] = Field(default=None, description="Specific fields to search")
    
    # Pagination
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Number of results per page")
    
    # Sorting
    sort_by: str = Field(default="relevance", description="Sort field")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="Sort order")


class TimecodeSearchResult(BaseModel):
    """Individual timecode search result"""
    asset_id: str = Field(..., description="Asset ID")
    asset_name: str = Field(..., description="Asset name")
    asset_type: str = Field(..., description="Asset type")
    
    # Timecode information
    duration: float = Field(..., description="Asset duration in seconds")
    duration_timecode: str = Field(..., description="Duration as timecode string")
    frame_rate: float = Field(..., description="Asset frame rate")
    timecode_format: TimecodeFormat = Field(..., description="Timecode format used")
    
    # Match information
    matched_timecode: Optional[str] = Field(default=None, description="Matched timecode")
    matched_range: Optional[Dict[str, Any]] = Field(default=None, description="Matched timecode range")
    match_score: float = Field(..., description="Match relevance score")
    match_type: str = Field(..., description="Type of match found")
    
    # Segment information (if applicable)
    segment_title: Optional[str] = Field(default=None, description="Segment or chapter title")
    segment_description: Optional[str] = Field(default=None, description="Segment description")
    markers: Optional[List[Dict[str, Any]]] = Field(default=None, description="Timeline markers")
    
    # Subtitle information (if applicable)
    subtitle_matches: Optional[List[Dict[str, Any]]] = Field(default=None, description="Subtitle matches")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    created_at: datetime = Field(..., description="Asset creation date")
    updated_at: datetime = Field(..., description="Asset last update date")


class TimecodeSearchResponse(BaseModel):
    """Response from timecode search"""
    results: List[TimecodeSearchResult] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    took: int = Field(..., description="Time taken for search in milliseconds")
    
    # Pagination
    page: int = Field(..., description="Current page")
    limit: int = Field(..., description="Results per page")
    pages: int = Field(..., description="Total pages")
    
    # Aggregations
    aggregations: Dict[str, Any] = Field(default_factory=dict, description="Search aggregations")
    
    # Search metadata
    search_metadata: Dict[str, Any] = Field(default_factory=dict, description="Search execution metadata")
    
    # Statistics
    duration_stats: Optional[Dict[str, Any]] = Field(default=None, description="Duration statistics")
    frame_rate_distribution: Optional[Dict[str, Any]] = Field(default=None, description="Frame rate distribution")
    format_distribution: Optional[Dict[str, Any]] = Field(default=None, description="Format distribution")


class TimecodeSearchStats(BaseModel):
    """Statistics for timecode searches"""
    total_searches: int = Field(..., description="Total timecode searches performed")
    total_assets_with_timecode: int = Field(..., description="Total assets with timecode data")
    
    # Duration statistics
    avg_duration: float = Field(..., description="Average asset duration in seconds")
    min_duration: float = Field(..., description="Minimum asset duration in seconds")
    max_duration: float = Field(..., description="Maximum asset duration in seconds")
    
    # Frame rate statistics
    frame_rate_distribution: Dict[str, int] = Field(..., description="Distribution of frame rates")
    most_common_frame_rate: float = Field(..., description="Most common frame rate")
    
    # Format statistics
    format_distribution: Dict[str, int] = Field(..., description="Distribution of timecode formats")
    most_common_format: TimecodeFormat = Field(..., description="Most common timecode format")
    
    # Search performance
    avg_search_time_ms: float = Field(..., description="Average search time in milliseconds")
    cache_hit_rate: float = Field(..., description="Cache hit rate for timecode searches")


class TimecodeValidationResult(BaseModel):
    """Result of timecode validation"""
    is_valid: bool = Field(..., description="Whether the timecode is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    
    # Normalized timecode
    normalized_timecode: Optional[str] = Field(default=None, description="Normalized timecode string")
    total_seconds: Optional[float] = Field(default=None, description="Total seconds")
    total_frames: Optional[int] = Field(default=None, description="Total frames")
    
    # Format information
    detected_format: Optional[TimecodeFormat] = Field(default=None, description="Detected timecode format")
    suggested_format: Optional[TimecodeFormat] = Field(default=None, description="Suggested timecode format")


class TimecodeConversionRequest(BaseModel):
    """Request to convert timecode between formats"""
    source_timecode: str = Field(..., description="Source timecode string")
    source_format: TimecodeFormat = Field(..., description="Source timecode format")
    target_format: TimecodeFormat = Field(..., description="Target timecode format")
    custom_frame_rate: Optional[float] = Field(default=None, description="Custom frame rate if needed")


class TimecodeConversionResponse(BaseModel):
    """Response from timecode conversion"""
    source_timecode: str = Field(..., description="Original timecode")
    target_timecode: str = Field(..., description="Converted timecode")
    source_format: TimecodeFormat = Field(..., description="Source format")
    target_format: TimecodeFormat = Field(..., description="Target format")
    
    # Calculation details
    source_seconds: float = Field(..., description="Source timecode in seconds")
    target_seconds: float = Field(..., description="Target timecode in seconds")
    source_frames: int = Field(..., description="Source timecode in frames")
    target_frames: int = Field(..., description="Target timecode in frames")
    
    # Conversion metadata
    conversion_method: str = Field(..., description="Method used for conversion")
    precision_loss: bool = Field(..., description="Whether precision was lost in conversion")
    warnings: List[str] = Field(default_factory=list, description="Conversion warnings")


# Color-based Search Schemas

class ColorSpace(str, Enum):
    """Color spaces for color analysis"""
    RGB = "rgb"
    HSV = "hsv"
    HSL = "hsl"
    LAB = "lab"
    XYZ = "xyz"
    YUV = "yuv"
    CMYK = "cmyk"
    HEX = "hex"


class ColorSearchType(str, Enum):
    """Types of color-based searches"""
    DOMINANT_COLOR = "dominant_color"
    COLOR_PALETTE = "color_palette"
    SIMILAR_COLORS = "similar_colors"
    COLOR_RANGE = "color_range"
    COMPLEMENTARY_COLORS = "complementary_colors"
    ANALOGOUS_COLORS = "analogous_colors"
    TRIADIC_COLORS = "triadic_colors"
    MONOCHROMATIC = "monochromatic"
    WARM_COLORS = "warm_colors"
    COOL_COLORS = "cool_colors"
    BRIGHTNESS_RANGE = "brightness_range"
    SATURATION_RANGE = "saturation_range"
    HUE_RANGE = "hue_range"


class ColorMatchType(str, Enum):
    """Types of color matching algorithms"""
    EXACT = "exact"
    EUCLIDEAN = "euclidean"
    DELTA_E = "delta_e"
    COSINE = "cosine"
    MANHATTAN = "manhattan"
    PERCEPTUAL = "perceptual"
    WEIGHTED = "weighted"


class ColorClusteringMethod(str, Enum):
    """Methods for color clustering"""
    KMEANS = "kmeans"
    DBSCAN = "dbscan"
    HIERARCHICAL = "hierarchical"
    MEANSHIFT = "meanshift"
    SPECTRAL = "spectral"


class Color(BaseModel):
    """Color representation with multiple color spaces"""
    # Primary color space (RGB)
    r: int = Field(..., ge=0, le=255, description="Red component (0-255)")
    g: int = Field(..., ge=0, le=255, description="Green component (0-255)")
    b: int = Field(..., ge=0, le=255, description="Blue component (0-255)")
    a: Optional[int] = Field(default=255, ge=0, le=255, description="Alpha component (0-255)")
    
    # Alternative representations
    hex: Optional[str] = Field(default=None, description="Hexadecimal color representation")
    hsv: Optional[Dict[str, float]] = Field(default=None, description="HSV color representation")
    hsl: Optional[Dict[str, float]] = Field(default=None, description="HSL color representation")
    lab: Optional[Dict[str, float]] = Field(default=None, description="LAB color representation")
    
    # Color metadata
    name: Optional[str] = Field(default=None, description="Human-readable color name")
    frequency: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Color frequency in image")
    percentage: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Color percentage in image")
    
    @validator('hex')
    def validate_hex(cls, v):
        if v is not None:
            if not v.startswith('#'):
                v = f'#{v}'
            if len(v) not in [4, 7]:  # #RGB or #RRGGBB
                raise ValueError('Hex color must be in format #RGB or #RRGGBB')
        return v
    
    def to_hex(self) -> str:
        """Convert RGB to hex"""
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"
    
    def to_hsv(self) -> Dict[str, float]:
        """Convert RGB to HSV"""
        r, g, b = self.r / 255.0, self.g / 255.0, self.b / 255.0
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        diff = max_val - min_val
        
        # Hue
        if diff == 0:
            h = 0
        elif max_val == r:
            h = (60 * ((g - b) / diff) + 360) % 360
        elif max_val == g:
            h = (60 * ((b - r) / diff) + 120) % 360
        else:
            h = (60 * ((r - g) / diff) + 240) % 360
        
        # Saturation
        s = 0 if max_val == 0 else diff / max_val
        
        # Value
        v = max_val
        
        return {"h": h, "s": s, "v": v}
    
    def to_hsl(self) -> Dict[str, float]:
        """Convert RGB to HSL"""
        r, g, b = self.r / 255.0, self.g / 255.0, self.b / 255.0
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        diff = max_val - min_val
        
        # Lightness
        l = (max_val + min_val) / 2
        
        if diff == 0:
            h = s = 0
        else:
            # Saturation
            s = diff / (2 - max_val - min_val) if l > 0.5 else diff / (max_val + min_val)
            
            # Hue
            if max_val == r:
                h = (60 * ((g - b) / diff) + 360) % 360
            elif max_val == g:
                h = (60 * ((b - r) / diff) + 120) % 360
            else:
                h = (60 * ((r - g) / diff) + 240) % 360
        
        return {"h": h, "s": s, "l": l}


class ColorRange(BaseModel):
    """Color range for range-based searches"""
    min_color: Color = Field(..., description="Minimum color in range")
    max_color: Color = Field(..., description="Maximum color in range")
    color_space: ColorSpace = Field(default=ColorSpace.RGB, description="Color space for range")
    tolerance: float = Field(default=10.0, ge=0.0, le=100.0, description="Tolerance for color matching")
    
    @validator('max_color')
    def validate_range(cls, v, values):
        if 'min_color' in values:
            min_color = values['min_color']
            # Basic validation that max >= min for RGB
            if (v.r < min_color.r or v.g < min_color.g or v.b < min_color.b):
                raise ValueError('Maximum color values must be >= minimum color values')
        return v


class ColorPalette(BaseModel):
    """Color palette representation"""
    colors: List[Color] = Field(..., min_items=1, description="List of colors in palette")
    palette_type: Optional[str] = Field(default=None, description="Type of palette (e.g., dominant, complementary)")
    extraction_method: Optional[str] = Field(default=None, description="Method used to extract palette")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Confidence in palette extraction")
    
    @validator('colors')
    def validate_colors(cls, v):
        if len(v) > 20:
            raise ValueError('Color palette cannot have more than 20 colors')
        return v
    
    def get_dominant_color(self) -> Color:
        """Get the dominant color from the palette"""
        if not self.colors:
            raise ValueError('Palette is empty')
        
        # Return the color with highest frequency/percentage
        return max(self.colors, key=lambda c: c.frequency or 0.0)


class ColorSearchQuery(BaseModel):
    """Query for color-based searches"""
    search_type: ColorSearchType = Field(..., description="Type of color search")
    
    # Color criteria
    target_color: Optional[Color] = Field(default=None, description="Target color to search for")
    color_palette: Optional[ColorPalette] = Field(default=None, description="Color palette to match")
    color_range: Optional[ColorRange] = Field(default=None, description="Color range to search within")
    
    # Search parameters
    color_space: ColorSpace = Field(default=ColorSpace.RGB, description="Color space for comparison")
    match_type: ColorMatchType = Field(default=ColorMatchType.EUCLIDEAN, description="Color matching algorithm")
    tolerance: float = Field(default=10.0, ge=0.0, le=100.0, description="Color matching tolerance")
    
    # Advanced options
    min_color_percentage: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Minimum percentage of color in image")
    max_color_percentage: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Maximum percentage of color in image")
    clustering_method: ColorClusteringMethod = Field(default=ColorClusteringMethod.KMEANS, description="Color clustering method")
    num_clusters: int = Field(default=5, ge=1, le=20, description="Number of color clusters")
    
    # Brightness and saturation filters
    min_brightness: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum brightness")
    max_brightness: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Maximum brightness")
    min_saturation: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum saturation")
    max_saturation: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Maximum saturation")
    
    # Hue filters
    min_hue: Optional[float] = Field(default=None, ge=0.0, le=360.0, description="Minimum hue")
    max_hue: Optional[float] = Field(default=None, ge=0.0, le=360.0, description="Maximum hue")
    
    # Asset filters
    asset_types: List[str] = Field(default=["image", "video"], description="Types of assets to search")
    video_formats: Optional[List[str]] = Field(default=None, description="Video formats to include")
    image_formats: Optional[List[str]] = Field(default=None, description="Image formats to include")
    
    # Search configuration
    indices: List[IndexType] = Field(default=[IndexType.ASSETS], description="Indices to search")
    include_frames: bool = Field(default=False, description="Include video frame analysis")
    frame_interval: Optional[int] = Field(default=None, ge=1, description="Interval for frame analysis (seconds)")
    
    # Pagination and sorting
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Number of results per page")
    sort_by: str = Field(default="relevance", description="Sort by field")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="Sort order")
    
    @validator('max_color_percentage')
    def validate_percentage_range(cls, v, values):
        if v is not None and 'min_color_percentage' in values and values['min_color_percentage'] is not None:
            if v < values['min_color_percentage']:
                raise ValueError('max_color_percentage must be >= min_color_percentage')
        return v
    
    @validator('max_brightness')
    def validate_brightness_range(cls, v, values):
        if v is not None and 'min_brightness' in values and values['min_brightness'] is not None:
            if v < values['min_brightness']:
                raise ValueError('max_brightness must be >= min_brightness')
        return v
    
    @validator('max_saturation')
    def validate_saturation_range(cls, v, values):
        if v is not None and 'min_saturation' in values and values['min_saturation'] is not None:
            if v < values['min_saturation']:
                raise ValueError('max_saturation must be >= min_saturation')
        return v
    
    @validator('max_hue')
    def validate_hue_range(cls, v, values):
        if v is not None and 'min_hue' in values and values['min_hue'] is not None:
            if v < values['min_hue']:
                raise ValueError('max_hue must be >= min_hue')
        return v


class ColorSearchResult(BaseModel):
    """Result from color-based search"""
    asset_id: str = Field(..., description="Asset ID")
    asset_name: str = Field(..., description="Asset name")
    asset_type: str = Field(..., description="Asset type")
    
    # Color analysis results
    dominant_colors: List[Color] = Field(..., description="Dominant colors in asset")
    color_palette: ColorPalette = Field(..., description="Full color palette")
    color_histogram: Optional[Dict[str, Any]] = Field(default=None, description="Color histogram data")
    
    # Match information
    matched_colors: List[Color] = Field(default_factory=list, description="Colors that matched the query")
    match_score: float = Field(..., description="Color match score")
    match_type: str = Field(..., description="Type of color match")
    color_similarity: float = Field(..., description="Color similarity score")
    
    # Color statistics
    color_diversity: Optional[float] = Field(default=None, description="Color diversity score")
    dominant_color_percentage: Optional[float] = Field(default=None, description="Percentage of dominant color")
    color_temperature: Optional[float] = Field(default=None, description="Color temperature (warm/cool)")
    
    # Image/video specific
    brightness: Optional[float] = Field(default=None, description="Overall brightness")
    contrast: Optional[float] = Field(default=None, description="Overall contrast")
    saturation: Optional[float] = Field(default=None, description="Overall saturation")
    
    # Frame analysis (for videos)
    frame_colors: Optional[List[Dict[str, Any]]] = Field(default=None, description="Color analysis per frame")
    color_timeline: Optional[List[Dict[str, Any]]] = Field(default=None, description="Color changes over time")
    
    # Asset metadata
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    dimensions: Optional[Dict[str, int]] = Field(default=None, description="Image/video dimensions")
    duration: Optional[float] = Field(default=None, description="Video duration in seconds")
    format: Optional[str] = Field(default=None, description="File format")
    
    # Timestamps
    created_at: datetime = Field(..., description="Asset creation date")
    updated_at: datetime = Field(..., description="Asset last update date")
    analyzed_at: Optional[datetime] = Field(default=None, description="Color analysis date")


class ColorSearchResponse(BaseModel):
    """Response from color-based search"""
    results: List[ColorSearchResult] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    took: int = Field(..., description="Time taken in milliseconds")
    
    # Pagination
    page: int = Field(..., description="Current page")
    limit: int = Field(..., description="Results per page")
    pages: int = Field(..., description="Total pages")
    
    # Aggregations
    aggregations: Dict[str, Any] = Field(default_factory=dict, description="Color aggregations")
    color_distribution: Optional[Dict[str, Any]] = Field(default=None, description="Color distribution statistics")
    palette_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Palette analysis results")
    
    # Search metadata
    search_metadata: Dict[str, Any] = Field(default_factory=dict, description="Search execution metadata")


class ColorSearchStats(BaseModel):
    """Statistics for color-based searches"""
    total_searches: int = Field(..., description="Total number of color searches performed")
    total_assets_analyzed: int = Field(..., description="Total number of assets with color analysis")
    
    # Color statistics
    most_common_colors: List[Dict[str, Any]] = Field(..., description="Most common colors across all assets")
    color_diversity_stats: Dict[str, Any] = Field(..., description="Color diversity statistics")
    dominant_color_distribution: Dict[str, Any] = Field(..., description="Distribution of dominant colors")
    
    # Search performance
    avg_search_time_ms: float = Field(..., description="Average search time in milliseconds")
    avg_analysis_time_ms: float = Field(..., description="Average color analysis time in milliseconds")
    cache_hit_rate: float = Field(..., description="Cache hit rate for color analysis")
    
    # Asset statistics
    images_analyzed: int = Field(..., description="Number of images analyzed")
    videos_analyzed: int = Field(..., description="Number of videos analyzed")
    frames_analyzed: int = Field(..., description="Number of video frames analyzed")
    
    # Color space statistics
    color_space_usage: Dict[str, int] = Field(..., description="Usage statistics by color space")
    clustering_method_usage: Dict[str, int] = Field(..., description="Usage statistics by clustering method")


class ColorAnalysisRequest(BaseModel):
    """Request for color analysis of an asset"""
    asset_id: str = Field(..., description="Asset ID to analyze")
    
    # Analysis parameters
    color_space: ColorSpace = Field(default=ColorSpace.RGB, description="Color space for analysis")
    clustering_method: ColorClusteringMethod = Field(default=ColorClusteringMethod.KMEANS, description="Clustering method")
    num_colors: int = Field(default=5, ge=1, le=20, description="Number of colors to extract")
    
    # Video-specific parameters
    frame_interval: Optional[int] = Field(default=None, ge=1, description="Frame analysis interval in seconds")
    sample_frames: Optional[int] = Field(default=None, ge=1, le=100, description="Number of frames to sample")
    
    # Advanced options
    include_histogram: bool = Field(default=False, description="Include color histogram")
    include_statistics: bool = Field(default=True, description="Include color statistics")
    force_reanalysis: bool = Field(default=False, description="Force re-analysis even if cached")


class ColorAnalysisResponse(BaseModel):
    """Response from color analysis"""
    asset_id: str = Field(..., description="Asset ID")
    analysis_success: bool = Field(..., description="Whether analysis was successful")
    
    # Color analysis results
    dominant_colors: List[Color] = Field(default_factory=list, description="Dominant colors")
    color_palette: Optional[ColorPalette] = Field(default=None, description="Color palette")
    color_histogram: Optional[Dict[str, Any]] = Field(default=None, description="Color histogram")
    
    # Statistics
    color_diversity: Optional[float] = Field(default=None, description="Color diversity score")
    color_temperature: Optional[float] = Field(default=None, description="Color temperature")
    brightness: Optional[float] = Field(default=None, description="Overall brightness")
    contrast: Optional[float] = Field(default=None, description="Overall contrast")
    saturation: Optional[float] = Field(default=None, description="Overall saturation")
    
    # Processing metadata
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    analysis_method: str = Field(..., description="Analysis method used")
    color_space_used: ColorSpace = Field(..., description="Color space used for analysis")
    
    # Error handling
    errors: List[str] = Field(default_factory=list, description="Analysis errors")
    warnings: List[str] = Field(default_factory=list, description="Analysis warnings")
    
    # Timestamps
    analyzed_at: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")


# ==================== FACIAL RECOGNITION SEARCH SCHEMAS ====================

class FaceDetectionModel(str, Enum):
    """Supported face detection models"""
    MTCNN = "mtcnn"
    RETINAFACE = "retinaface"
    OPENCV_DNN = "opencv_dnn"
    DLIB_HOG = "dlib_hog"
    DLIB_CNN = "dlib_cnn"
    MEDIAPIPE = "mediapipe"
    YOLO_FACE = "yolo_face"
    BLAZEFACE = "blazeface"


class FaceRecognitionModel(str, Enum):
    """Supported face recognition models"""
    FACENET = "facenet"
    ARCFACE = "arcface"
    COSFACE = "cosface"
    SPHEREFACE = "sphereface"
    OPENFACE = "openface"
    DEEPFACE = "deepface"
    INSIGHTFACE = "insightface"
    FACE_RECOGNITION = "face_recognition"


class FaceSearchType(str, Enum):
    """Types of facial recognition searches"""
    PERSON_SEARCH = "person_search"
    FACE_SIMILARITY = "face_similarity"
    FACE_VERIFICATION = "face_verification"
    DEMOGRAPHIC_SEARCH = "demographic_search"
    EMOTION_SEARCH = "emotion_search"
    AGE_RANGE_SEARCH = "age_range_search"
    GENDER_SEARCH = "gender_search"
    EXPRESSION_SEARCH = "expression_search"
    FACE_COUNT = "face_count"
    GROUP_DETECTION = "group_detection"
    CELEBRITY_RECOGNITION = "celebrity_recognition"
    UNKNOWN_FACES = "unknown_faces"


class FaceMatchType(str, Enum):
    """Face matching algorithms"""
    COSINE_SIMILARITY = "cosine_similarity"
    EUCLIDEAN_DISTANCE = "euclidean_distance"
    MANHATTAN_DISTANCE = "manhattan_distance"
    CORRELATION = "correlation"
    CHI_SQUARED = "chi_squared"
    INTERSECTION = "intersection"
    DEEP_METRIC = "deep_metric"
    THRESHOLD_BASED = "threshold_based"


class Gender(str, Enum):
    """Gender options"""
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class Emotion(str, Enum):
    """Facial expressions/emotions"""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    NEUTRAL = "neutral"
    CONTEMPT = "contempt"


class FaceExpression(str, Enum):
    """Facial expressions"""
    SMILING = "smiling"
    FROWNING = "frowning"
    LAUGHING = "laughing"
    CRYING = "crying"
    WINKING = "winking"
    BLINKING = "blinking"
    MOUTH_OPEN = "mouth_open"
    EYES_CLOSED = "eyes_closed"
    TONGUE_OUT = "tongue_out"
    NEUTRAL = "neutral"


class FaceQuality(str, Enum):
    """Face quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNUSABLE = "unusable"


class FaceLandmarkType(str, Enum):
    """Face landmark detection types"""
    LANDMARKS_5 = "landmarks_5"
    LANDMARKS_68 = "landmarks_68"
    LANDMARKS_81 = "landmarks_81"
    LANDMARKS_106 = "landmarks_106"
    LANDMARKS_468 = "landmarks_468"
    MEDIAPIPE_468 = "mediapipe_468"


class BoundingBox(BaseModel):
    """Face bounding box coordinates"""
    x: float = Field(..., ge=0, description="X coordinate (left)")
    y: float = Field(..., ge=0, description="Y coordinate (top)")
    width: float = Field(..., gt=0, description="Box width")
    height: float = Field(..., gt=0, description="Box height")
    confidence: Optional[float] = Field(default=None, ge=0, le=1, description="Detection confidence")


class FaceLandmarks(BaseModel):
    """Face landmark points"""
    landmark_type: FaceLandmarkType = Field(..., description="Type of landmarks")
    points: List[Dict[str, float]] = Field(..., description="Landmark points as [{'x': x, 'y': y}]")
    confidence: Optional[float] = Field(default=None, ge=0, le=1, description="Landmark detection confidence")
    
    @validator('points')
    def validate_points(cls, v, values):
        if not v:
            raise ValueError('Landmark points cannot be empty')
        for point in v:
            if 'x' not in point or 'y' not in point:
                raise ValueError('Each landmark point must have x and y coordinates')
            if not isinstance(point['x'], (int, float)) or not isinstance(point['y'], (int, float)):
                raise ValueError('Landmark coordinates must be numeric')
        return v


class FaceAttributes(BaseModel):
    """Facial attributes analysis"""
    age: Optional[float] = Field(default=None, ge=0, le=120, description="Estimated age")
    age_range: Optional[Dict[str, float]] = Field(default=None, description="Age range estimate")
    gender: Optional[Gender] = Field(default=None, description="Detected gender")
    gender_confidence: Optional[float] = Field(default=None, ge=0, le=1, description="Gender confidence")
    
    # Emotions
    emotion: Optional[Emotion] = Field(default=None, description="Primary emotion")
    emotion_confidence: Optional[float] = Field(default=None, ge=0, le=1, description="Emotion confidence")
    emotion_scores: Optional[Dict[str, float]] = Field(default=None, description="All emotion scores")
    
    # Expressions
    expression: Optional[FaceExpression] = Field(default=None, description="Facial expression")
    expression_confidence: Optional[float] = Field(default=None, ge=0, le=1, description="Expression confidence")
    
    # Physical attributes
    glasses: Optional[bool] = Field(default=None, description="Wearing glasses")
    glasses_confidence: Optional[float] = Field(default=None, ge=0, le=1, description="Glasses detection confidence")
    
    beard: Optional[bool] = Field(default=None, description="Has beard")
    beard_confidence: Optional[float] = Field(default=None, ge=0, le=1, description="Beard detection confidence")
    
    mustache: Optional[bool] = Field(default=None, description="Has mustache")
    mustache_confidence: Optional[float] = Field(default=None, ge=0, le=1, description="Mustache detection confidence")
    
    # Face pose
    head_pose: Optional[Dict[str, float]] = Field(default=None, description="Head pose angles (yaw, pitch, roll)")
    face_angle: Optional[float] = Field(default=None, ge=-180, le=180, description="Face angle in degrees")
    
    # Quality metrics
    face_quality: Optional[FaceQuality] = Field(default=None, description="Overall face quality")
    blur_score: Optional[float] = Field(default=None, ge=0, le=1, description="Face blur score")
    brightness: Optional[float] = Field(default=None, ge=0, le=1, description="Face brightness")
    sharpness: Optional[float] = Field(default=None, ge=0, le=1, description="Face sharpness")
    occlusion: Optional[float] = Field(default=None, ge=0, le=1, description="Face occlusion score")


class FaceEncoding(BaseModel):
    """Face encoding/embedding vector"""
    model: FaceRecognitionModel = Field(..., description="Model used for encoding")
    encoding: List[float] = Field(..., description="Face encoding vector")
    dimension: int = Field(..., gt=0, description="Encoding dimension")
    confidence: Optional[float] = Field(default=None, ge=0, le=1, description="Encoding confidence")
    
    @validator('encoding')
    def validate_encoding(cls, v):
        if not v:
            raise ValueError('Face encoding cannot be empty')
        if not all(isinstance(x, (int, float)) for x in v):
            raise ValueError('All encoding values must be numeric')
        return v
    
    @validator('dimension')
    def validate_dimension(cls, v, values):
        if 'encoding' in values and len(values['encoding']) != v:
            raise ValueError('Dimension must match encoding length')
        return v


class DetectedFace(BaseModel):
    """A detected face in an image/video"""
    face_id: str = Field(..., description="Unique face ID")
    bounding_box: BoundingBox = Field(..., description="Face bounding box")
    landmarks: Optional[FaceLandmarks] = Field(default=None, description="Face landmarks")
    attributes: Optional[FaceAttributes] = Field(default=None, description="Face attributes")
    encoding: Optional[FaceEncoding] = Field(default=None, description="Face encoding")
    
    # Identity information
    person_id: Optional[str] = Field(default=None, description="Identified person ID")
    person_name: Optional[str] = Field(default=None, description="Person name")
    celebrity_name: Optional[str] = Field(default=None, description="Celebrity name if recognized")
    similarity_score: Optional[float] = Field(default=None, ge=0, le=1, description="Identity similarity score")
    
    # Detection metadata
    detection_model: FaceDetectionModel = Field(..., description="Model used for detection")
    detection_confidence: float = Field(..., ge=0, le=1, description="Detection confidence")
    detection_time_ms: Optional[int] = Field(default=None, description="Detection processing time")
    
    # Frame information (for videos)
    frame_number: Optional[int] = Field(default=None, ge=0, description="Frame number in video")
    timestamp: Optional[float] = Field(default=None, ge=0, description="Timestamp in video")


class PersonIdentity(BaseModel):
    """Person identity for face recognition"""
    person_id: str = Field(..., description="Unique person identifier")
    person_name: str = Field(..., description="Person name")
    known_faces: List[str] = Field(default_factory=list, description="List of known face IDs")
    reference_encoding: Optional[FaceEncoding] = Field(default=None, description="Reference face encoding")
    
    # Person metadata
    description: Optional[str] = Field(default=None, description="Person description")
    tags: List[str] = Field(default_factory=list, description="Person tags")
    department: Optional[str] = Field(default=None, description="Department/organization")
    role: Optional[str] = Field(default=None, description="Person role/title")
    
    # Statistics
    total_appearances: int = Field(default=0, ge=0, description="Total appearances in assets")
    last_seen: Optional[datetime] = Field(default=None, description="Last appearance date")
    confidence_avg: Optional[float] = Field(default=None, ge=0, le=1, description="Average recognition confidence")
    
    # Privacy settings
    privacy_level: Optional[str] = Field(default="public", description="Privacy level")
    consent_given: bool = Field(default=False, description="Consent for face recognition")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Person record creation")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update")


class FaceSearchQuery(BaseModel):
    """Face search query parameters"""
    search_type: FaceSearchType = Field(..., description="Type of face search")
    
    # Person-based search
    person_id: Optional[str] = Field(default=None, description="Search for specific person")
    person_name: Optional[str] = Field(default=None, description="Search by person name")
    reference_image: Optional[str] = Field(default=None, description="Reference image for similarity search")
    reference_encoding: Optional[List[float]] = Field(default=None, description="Reference face encoding")
    
    # Similarity search
    similarity_threshold: float = Field(default=0.6, ge=0, le=1, description="Similarity threshold")
    match_type: FaceMatchType = Field(default=FaceMatchType.COSINE_SIMILARITY, description="Matching algorithm")
    max_distance: Optional[float] = Field(default=None, ge=0, description="Maximum distance for matching")
    
    # Attribute-based search
    age_range: Optional[Dict[str, float]] = Field(default=None, description="Age range filter")
    gender: Optional[Gender] = Field(default=None, description="Gender filter")
    emotion: Optional[Emotion] = Field(default=None, description="Emotion filter")
    expression: Optional[FaceExpression] = Field(default=None, description="Expression filter")
    
    # Quality filters
    min_face_quality: Optional[FaceQuality] = Field(default=None, description="Minimum face quality")
    min_confidence: float = Field(default=0.5, ge=0, le=1, description="Minimum detection confidence")
    max_blur_score: Optional[float] = Field(default=None, ge=0, le=1, description="Maximum blur tolerance")
    min_face_size: Optional[int] = Field(default=None, ge=1, description="Minimum face size in pixels")
    
    # Count and group filters
    min_face_count: Optional[int] = Field(default=None, ge=0, description="Minimum faces in image/video")
    max_face_count: Optional[int] = Field(default=None, ge=0, description="Maximum faces in image/video")
    group_size_range: Optional[Dict[str, int]] = Field(default=None, description="Group size range")
    
    # Technical filters
    asset_types: List[str] = Field(default=["image", "video"], description="Asset types to search")
    face_detection_model: Optional[FaceDetectionModel] = Field(default=None, description="Required detection model")
    face_recognition_model: Optional[FaceRecognitionModel] = Field(default=None, description="Required recognition model")
    
    # Video-specific filters
    frame_interval: int = Field(default=30, ge=1, description="Frame interval for video analysis")
    min_duration: Optional[float] = Field(default=None, ge=0, description="Minimum video duration")
    max_duration: Optional[float] = Field(default=None, ge=0, description="Maximum video duration")
    
    # Result preferences
    include_landmarks: bool = Field(default=False, description="Include face landmarks in results")
    include_attributes: bool = Field(default=True, description="Include face attributes in results")
    include_encodings: bool = Field(default=False, description="Include face encodings in results")
    include_unknown_faces: bool = Field(default=False, description="Include unidentified faces")
    
    # Pagination and sorting
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Results per page")
    sort_by: str = Field(default="confidence", description="Sort field")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="Sort order")
    
    @validator('age_range')
    def validate_age_range(cls, v):
        if v is not None:
            if 'min' not in v or 'max' not in v:
                raise ValueError('Age range must have min and max values')
            if v['min'] < 0 or v['max'] > 120:
                raise ValueError('Age range must be between 0 and 120')
            if v['min'] > v['max']:
                raise ValueError('Age range min must be <= max')
        return v
    
    @validator('group_size_range')
    def validate_group_size_range(cls, v):
        if v is not None:
            if 'min' not in v or 'max' not in v:
                raise ValueError('Group size range must have min and max values')
            if v['min'] < 0 or v['max'] < 0:
                raise ValueError('Group size range must be non-negative')
            if v['min'] > v['max']:
                raise ValueError('Group size range min must be <= max')
        return v
    
    @validator('max_face_count')
    def validate_face_count_range(cls, v, values):
        if v is not None and 'min_face_count' in values and values['min_face_count'] is not None:
            if v < values['min_face_count']:
                raise ValueError('max_face_count must be >= min_face_count')
        return v


class FaceSearchResult(BaseModel):
    """Result from facial recognition search"""
    asset_id: str = Field(..., description="Asset ID")
    asset_name: str = Field(..., description="Asset name")
    asset_type: str = Field(..., description="Asset type")
    
    # Face detection results
    detected_faces: List[DetectedFace] = Field(..., description="All detected faces")
    face_count: int = Field(..., ge=0, description="Total number of faces")
    
    # Match information
    matched_faces: List[DetectedFace] = Field(default_factory=list, description="Faces that matched the query")
    match_score: float = Field(..., description="Overall match score")
    match_type: str = Field(..., description="Type of face match")
    best_match_confidence: Optional[float] = Field(default=None, description="Best face match confidence")
    
    # Person identification
    identified_persons: List[PersonIdentity] = Field(default_factory=list, description="Identified persons")
    unknown_faces: List[DetectedFace] = Field(default_factory=list, description="Unidentified faces")
    celebrity_matches: List[Dict[str, Any]] = Field(default_factory=list, description="Celebrity matches")
    
    # Demographics summary
    demographics: Optional[Dict[str, Any]] = Field(default=None, description="Demographics analysis")
    emotions_summary: Optional[Dict[str, int]] = Field(default=None, description="Emotions distribution")
    age_distribution: Optional[Dict[str, int]] = Field(default=None, description="Age distribution")
    gender_distribution: Optional[Dict[str, int]] = Field(default=None, description="Gender distribution")
    
    # Video-specific data
    face_timeline: Optional[List[Dict[str, Any]]] = Field(default=None, description="Face appearances over time")
    scene_faces: Optional[List[Dict[str, Any]]] = Field(default=None, description="Faces per scene/segment")
    
    # Quality metrics
    average_face_quality: Optional[float] = Field(default=None, description="Average face quality score")
    detection_quality: Optional[str] = Field(default=None, description="Overall detection quality")
    
    # Asset metadata
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    dimensions: Optional[Dict[str, int]] = Field(default=None, description="Image/video dimensions")
    duration: Optional[float] = Field(default=None, description="Video duration in seconds")
    format: Optional[str] = Field(default=None, description="File format")
    
    # Processing metadata
    processing_time_ms: Optional[int] = Field(default=None, description="Processing time in milliseconds")
    detection_model: Optional[FaceDetectionModel] = Field(default=None, description="Detection model used")
    recognition_model: Optional[FaceRecognitionModel] = Field(default=None, description="Recognition model used")
    
    # Timestamps
    created_at: datetime = Field(..., description="Asset creation date")
    updated_at: datetime = Field(..., description="Asset last update date")
    analyzed_at: Optional[datetime] = Field(default=None, description="Face analysis date")


class FaceSearchResponse(BaseModel):
    """Response from facial recognition search"""
    results: List[FaceSearchResult] = Field(..., description="Search results")
    total: int = Field(..., ge=0, description="Total number of results")
    took: int = Field(..., description="Search time in milliseconds")
    page: int = Field(..., ge=1, description="Current page")
    limit: int = Field(..., ge=1, description="Results per page")
    pages: int = Field(..., ge=0, description="Total pages")
    
    # Aggregations
    aggregations: Dict[str, Any] = Field(default_factory=dict, description="Search aggregations")
    
    # Face statistics
    total_faces_found: int = Field(default=0, ge=0, description="Total faces found across all results")
    unique_persons: int = Field(default=0, ge=0, description="Number of unique persons identified")
    unknown_faces_count: int = Field(default=0, ge=0, description="Number of unknown faces")
    celebrity_matches_count: int = Field(default=0, ge=0, description="Number of celebrity matches")
    
    # Quality distribution
    quality_distribution: Optional[Dict[str, int]] = Field(default=None, description="Quality distribution")
    confidence_distribution: Optional[Dict[str, int]] = Field(default=None, description="Confidence distribution")
    
    # Demographics summary
    overall_demographics: Optional[Dict[str, Any]] = Field(default=None, description="Overall demographics")
    
    # Search metadata
    search_metadata: Dict[str, Any] = Field(default_factory=dict, description="Search metadata")


class FaceAnalysisRequest(BaseModel):
    """Request for face analysis"""
    asset_id: str = Field(..., description="Asset ID to analyze")
    detection_model: FaceDetectionModel = Field(default=FaceDetectionModel.RETINAFACE, description="Face detection model")
    recognition_model: FaceRecognitionModel = Field(default=FaceRecognitionModel.FACENET, description="Face recognition model")
    landmark_type: FaceLandmarkType = Field(default=FaceLandmarkType.LANDMARKS_68, description="Landmark detection type")
    
    # Analysis options
    extract_attributes: bool = Field(default=True, description="Extract facial attributes")
    extract_encodings: bool = Field(default=True, description="Extract face encodings")
    extract_landmarks: bool = Field(default=False, description="Extract face landmarks")
    identify_persons: bool = Field(default=True, description="Attempt person identification")
    detect_celebrities: bool = Field(default=False, description="Detect celebrities")
    
    # Quality settings
    min_face_size: int = Field(default=30, ge=10, description="Minimum face size in pixels")
    min_confidence: float = Field(default=0.6, ge=0, le=1, description="Minimum detection confidence")
    max_faces: Optional[int] = Field(default=None, ge=1, description="Maximum faces to process")
    
    # Video settings
    frame_interval: int = Field(default=30, ge=1, description="Frame interval for video analysis")
    max_frames: Optional[int] = Field(default=None, ge=1, description="Maximum frames to analyze")
    scene_detection: bool = Field(default=False, description="Enable scene-based analysis")
    
    # Processing options
    force_reanalysis: bool = Field(default=False, description="Force re-analysis even if exists")
    parallel_processing: bool = Field(default=True, description="Enable parallel processing")
    gpu_acceleration: bool = Field(default=True, description="Use GPU acceleration if available")
    
    # Privacy options
    anonymize_unknown: bool = Field(default=False, description="Anonymize unknown faces")
    respect_privacy_settings: bool = Field(default=True, description="Respect person privacy settings")


class FaceAnalysisResponse(BaseModel):
    """Response from face analysis"""
    asset_id: str = Field(..., description="Asset ID")
    analysis_success: bool = Field(..., description="Whether analysis succeeded")
    
    # Analysis results
    detected_faces: List[DetectedFace] = Field(default_factory=list, description="All detected faces")
    face_count: int = Field(default=0, ge=0, description="Total number of faces detected")
    
    # Person identification
    identified_persons: List[PersonIdentity] = Field(default_factory=list, description="Identified persons")
    unknown_faces: List[DetectedFace] = Field(default_factory=list, description="Unidentified faces")
    celebrity_matches: List[Dict[str, Any]] = Field(default_factory=list, description="Celebrity matches")
    
    # Demographics analysis
    demographics: Optional[Dict[str, Any]] = Field(default=None, description="Demographics summary")
    age_statistics: Optional[Dict[str, float]] = Field(default=None, description="Age statistics")
    gender_distribution: Optional[Dict[str, int]] = Field(default=None, description="Gender distribution")
    emotion_distribution: Optional[Dict[str, int]] = Field(default=None, description="Emotion distribution")
    
    # Quality metrics
    average_face_quality: Optional[float] = Field(default=None, description="Average face quality")
    quality_distribution: Optional[Dict[str, int]] = Field(default=None, description="Quality distribution")
    detection_quality_score: Optional[float] = Field(default=None, description="Overall detection quality")
    
    # Video-specific results
    face_timeline: Optional[List[Dict[str, Any]]] = Field(default=None, description="Face timeline for videos")
    scene_analysis: Optional[List[Dict[str, Any]]] = Field(default=None, description="Scene-based analysis")
    frame_analysis: Optional[List[Dict[str, Any]]] = Field(default=None, description="Per-frame analysis")
    
    # Processing metadata
    processing_time_ms: int = Field(..., description="Total processing time")
    detection_model: FaceDetectionModel = Field(..., description="Detection model used")
    recognition_model: FaceRecognitionModel = Field(..., description="Recognition model used")
    frames_analyzed: Optional[int] = Field(default=None, description="Number of frames analyzed")
    
    # Error handling
    errors: List[str] = Field(default_factory=list, description="Analysis errors")
    warnings: List[str] = Field(default_factory=list, description="Analysis warnings")
    
    # Timestamps
    analyzed_at: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")


class FaceSearchStats(BaseModel):
    """Statistics for facial recognition searches"""
    total_searches: int = Field(..., ge=0, description="Total face searches performed")
    total_faces_detected: int = Field(..., ge=0, description="Total faces detected")
    total_persons_identified: int = Field(..., ge=0, description="Total persons identified")
    unique_persons_database: int = Field(..., ge=0, description="Unique persons in database")
    
    # Recognition accuracy
    identification_accuracy: Optional[float] = Field(default=None, ge=0, le=1, description="Overall identification accuracy")
    false_positive_rate: Optional[float] = Field(default=None, ge=0, le=1, description="False positive rate")
    false_negative_rate: Optional[float] = Field(default=None, ge=0, le=1, description="False negative rate")
    
    # Performance metrics
    avg_search_time_ms: float = Field(..., ge=0, description="Average search time")
    avg_detection_time_ms: float = Field(..., ge=0, description="Average detection time")
    avg_recognition_time_ms: float = Field(..., ge=0, description="Average recognition time")
    cache_hit_rate: float = Field(..., ge=0, le=1, description="Cache hit rate")
    
    # Asset statistics
    images_analyzed: int = Field(default=0, ge=0, description="Number of images analyzed")
    videos_analyzed: int = Field(default=0, ge=0, description="Number of videos analyzed")
    frames_analyzed: int = Field(default=0, ge=0, description="Total video frames analyzed")
    
    # Model usage statistics
    detection_model_usage: Dict[str, int] = Field(default_factory=dict, description="Detection model usage")
    recognition_model_usage: Dict[str, int] = Field(default_factory=dict, description="Recognition model usage")
    
    # Quality distribution
    face_quality_distribution: Dict[str, int] = Field(default_factory=dict, description="Face quality distribution")
    confidence_distribution: Dict[str, int] = Field(default_factory=dict, description="Confidence distribution")
    
    # Demographics statistics
    age_distribution: Dict[str, int] = Field(default_factory=dict, description="Age distribution")
    gender_distribution: Dict[str, int] = Field(default_factory=dict, description="Gender distribution")
    emotion_distribution: Dict[str, int] = Field(default_factory=dict, description="Emotion distribution")
    
    # Privacy and compliance
    consent_given_persons: int = Field(default=0, ge=0, description="Persons with consent")
    anonymized_faces: int = Field(default=0, ge=0, description="Anonymized faces")
    privacy_violations: int = Field(default=0, ge=0, description="Privacy violations detected")
    
    # Error statistics
    detection_failures: int = Field(default=0, ge=0, description="Detection failures")
    recognition_failures: int = Field(default=0, ge=0, description="Recognition failures")
    low_quality_faces: int = Field(default=0, ge=0, description="Low quality face detections")


# ========================================================================================
# Image Similarity Search Schemas
# ========================================================================================

class ImageFeatureModel(str, Enum):
    """Image feature extraction models"""
    RESNET50 = "resnet50"
    VGG16 = "vgg16"
    VGG19 = "vgg19"
    MOBILENET = "mobilenet"
    EFFICIENTNET = "efficientnet"
    INCEPTION_V3 = "inception_v3"
    DENSENET = "densenet"
    CLIP = "clip"
    DINO = "dino"
    SWIN_TRANSFORMER = "swin_transformer"
    VIT = "vision_transformer"
    CONVNEXT = "convnext"


class ImageSimilarityType(str, Enum):
    """Types of image similarity searches"""
    VISUAL_SIMILARITY = "visual_similarity"
    CONTENT_SIMILARITY = "content_similarity"
    STYLE_SIMILARITY = "style_similarity"
    COLOR_SIMILARITY = "color_similarity"
    TEXTURE_SIMILARITY = "texture_similarity"
    SHAPE_SIMILARITY = "shape_similarity"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    PERCEPTUAL_HASH = "perceptual_hash"
    DUPLICATE_DETECTION = "duplicate_detection"
    NEAR_DUPLICATE = "near_duplicate"
    REVERSE_IMAGE_SEARCH = "reverse_image_search"


class SimilarityMetric(str, Enum):
    """Similarity calculation metrics"""
    COSINE_SIMILARITY = "cosine_similarity"
    EUCLIDEAN_DISTANCE = "euclidean_distance"
    MANHATTAN_DISTANCE = "manhattan_distance"
    HAMMING_DISTANCE = "hamming_distance"
    JACCARD_SIMILARITY = "jaccard_similarity"
    PEARSON_CORRELATION = "pearson_correlation"
    SPEARMAN_CORRELATION = "spearman_correlation"
    CHI_SQUARED = "chi_squared"
    KULLBACK_LEIBLER = "kullback_leibler"
    EARTH_MOVER_DISTANCE = "earth_mover_distance"
    STRUCTURAL_SIMILARITY = "structural_similarity"


class ImageHashType(str, Enum):
    """Perceptual hash algorithms"""
    AVERAGE_HASH = "average_hash"
    PERCEPTUAL_HASH = "perceptual_hash"
    DIFFERENCE_HASH = "difference_hash"
    WAVELET_HASH = "wavelet_hash"
    COLOR_HASH = "color_hash"
    CROP_RESISTANT_HASH = "crop_resistant_hash"


class ImageQualityMetric(str, Enum):
    """Image quality assessment metrics"""
    BRISQUE = "brisque"
    NIQE = "niqe"
    PIQE = "piqe"
    SSIM = "ssim"
    PSNR = "psnr"
    MSE = "mse"
    BLUR_DETECTION = "blur_detection"
    BRIGHTNESS = "brightness"
    CONTRAST = "contrast"
    SHARPNESS = "sharpness"


class ImageProcessingType(str, Enum):
    """Image preprocessing types"""
    RESIZE = "resize"
    CROP = "crop"
    NORMALIZE = "normalize"
    AUGMENT = "augment"
    DENOISE = "denoise"
    ENHANCE = "enhance"
    HISTOGRAM_EQUALIZATION = "histogram_equalization"
    GAMMA_CORRECTION = "gamma_correction"


class BoundingBox(BaseModel):
    """Bounding box coordinates"""
    x: int = Field(..., ge=0, description="X coordinate")
    y: int = Field(..., ge=0, description="Y coordinate")
    width: int = Field(..., gt=0, description="Width")
    height: int = Field(..., gt=0, description="Height")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Detection confidence")


class ImageFeatureVector(BaseModel):
    """Image feature vector representation"""
    model: ImageFeatureModel = Field(..., description="Feature extraction model")
    features: List[float] = Field(..., description="Feature vector")
    dimension: int = Field(..., gt=0, description="Feature vector dimension")
    layer: Optional[str] = Field(default=None, description="Layer from which features were extracted")
    preprocessing: Optional[List[str]] = Field(default=None, description="Applied preprocessing steps")
    extraction_time_ms: Optional[float] = Field(default=None, ge=0, description="Feature extraction time")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Feature quality confidence")


class ImageHash(BaseModel):
    """Perceptual hash representation"""
    hash_type: ImageHashType = Field(..., description="Hash algorithm used")
    hash_value: str = Field(..., description="Hash value as hexadecimal string")
    bit_length: int = Field(..., gt=0, description="Hash bit length")
    normalized: bool = Field(default=True, description="Whether hash is normalized")
    rotation_invariant: bool = Field(default=False, description="Rotation invariance")
    scale_invariant: bool = Field(default=False, description="Scale invariance")


class ImageColorProfile(BaseModel):
    """Image color characteristics"""
    dominant_colors: List[str] = Field(..., description="Dominant colors (hex codes)")
    color_palette: List[Dict[str, Any]] = Field(..., description="Color palette with percentages")
    average_color: str = Field(..., description="Average color (hex code)")
    brightness: float = Field(..., ge=0.0, le=1.0, description="Overall brightness")
    contrast: float = Field(..., ge=0.0, description="Contrast level")
    saturation: float = Field(..., ge=0.0, le=1.0, description="Color saturation")
    color_space: str = Field(default="RGB", description="Color space")
    histogram: Optional[Dict[str, List[int]]] = Field(default=None, description="Color histograms")


class ImageTexture(BaseModel):
    """Image texture analysis"""
    lbp_histogram: Optional[List[float]] = Field(default=None, description="Local Binary Pattern histogram")
    glcm_features: Optional[Dict[str, float]] = Field(default=None, description="Gray-Level Co-occurrence Matrix features")
    entropy: Optional[float] = Field(default=None, ge=0.0, description="Texture entropy")
    energy: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Texture energy")
    homogeneity: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Texture homogeneity")
    contrast: Optional[float] = Field(default=None, ge=0.0, description="Texture contrast")


class ImageShape(BaseModel):
    """Image shape characteristics"""
    edges: Optional[int] = Field(default=None, ge=0, description="Number of detected edges")
    contours: Optional[int] = Field(default=None, ge=0, description="Number of contours")
    corners: Optional[int] = Field(default=None, ge=0, description="Number of corner points")
    symmetry_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Symmetry score")
    complexity_score: Optional[float] = Field(default=None, ge=0.0, description="Shape complexity")
    roundness: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Roundness measure")


class ImageQuality(BaseModel):
    """Image quality metrics"""
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score")
    sharpness: Optional[float] = Field(default=None, ge=0.0, description="Sharpness score")
    blur_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Blur level (0=sharp, 1=blurred)")
    noise_level: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Noise level")
    brightness: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Brightness level")
    contrast: Optional[float] = Field(default=None, ge=0.0, description="Contrast level")
    exposure: Optional[str] = Field(default=None, description="Exposure assessment")
    artifacts: Optional[List[str]] = Field(default=None, description="Detected artifacts")


class ImageAnalysis(BaseModel):
    """Comprehensive image analysis result"""
    asset_id: str = Field(..., description="Asset identifier")
    image_path: str = Field(..., description="Image file path")
    dimensions: Dict[str, int] = Field(..., description="Image dimensions (width, height)")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    format: str = Field(..., description="Image format")
    
    # Feature vectors
    feature_vectors: List[ImageFeatureVector] = Field(default_factory=list, description="Extracted feature vectors")
    
    # Hashes
    perceptual_hashes: List[ImageHash] = Field(default_factory=list, description="Perceptual hashes")
    
    # Visual characteristics
    color_profile: Optional[ImageColorProfile] = Field(default=None, description="Color analysis")
    texture: Optional[ImageTexture] = Field(default=None, description="Texture analysis")
    shape: Optional[ImageShape] = Field(default=None, description="Shape analysis")
    quality: Optional[ImageQuality] = Field(default=None, description="Quality assessment")
    
    # Metadata
    analyzed_at: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")
    analysis_version: str = Field(default="1.0", description="Analysis version")
    processing_time_ms: float = Field(..., ge=0, description="Analysis processing time")
    
    # Object detection (if applicable)
    detected_objects: Optional[List[Dict[str, Any]]] = Field(default=None, description="Detected objects")
    object_count: int = Field(default=0, ge=0, description="Number of detected objects")


class SimilarityMatch(BaseModel):
    """Single similarity match result"""
    asset_id: str = Field(..., description="Matched asset ID")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    distance: Optional[float] = Field(default=None, ge=0.0, description="Distance metric value")
    match_type: str = Field(..., description="Type of similarity match")
    
    # Asset information
    asset_name: Optional[str] = Field(default=None, description="Asset name")
    asset_type: Optional[str] = Field(default=None, description="Asset type")
    file_path: Optional[str] = Field(default=None, description="File path")
    thumbnail_url: Optional[str] = Field(default=None, description="Thumbnail URL")
    
    # Similarity details
    matched_features: Optional[List[str]] = Field(default=None, description="Matching feature types")
    feature_similarities: Optional[Dict[str, float]] = Field(default=None, description="Individual feature similarities")
    regions_of_interest: Optional[List[BoundingBox]] = Field(default=None, description="Similar regions")
    
    # Quality metrics
    match_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Match confidence")
    quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Match quality")


class ImageSimilarityQuery(BaseModel):
    """Image similarity search query"""
    # Input specification
    reference_asset_id: Optional[str] = Field(default=None, description="Reference asset ID")
    reference_image_url: Optional[str] = Field(default=None, description="Reference image URL")
    reference_features: Optional[List[float]] = Field(default=None, description="Pre-extracted features")
    reference_hash: Optional[str] = Field(default=None, description="Reference hash value")
    
    # Search type and parameters
    similarity_type: ImageSimilarityType = Field(default=ImageSimilarityType.VISUAL_SIMILARITY, description="Type of similarity")
    feature_model: ImageFeatureModel = Field(default=ImageFeatureModel.RESNET50, description="Feature extraction model")
    similarity_metric: SimilarityMetric = Field(default=SimilarityMetric.COSINE_SIMILARITY, description="Similarity metric")
    
    # Thresholds
    similarity_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Minimum similarity score")
    max_distance: Optional[float] = Field(default=None, ge=0.0, description="Maximum distance threshold")
    
    # Filters
    asset_types: Optional[List[str]] = Field(default=None, description="Asset types to search")
    file_formats: Optional[List[str]] = Field(default=None, description="File formats to include")
    size_range: Optional[Dict[str, int]] = Field(default=None, description="File size range")
    dimension_range: Optional[Dict[str, Dict[str, int]]] = Field(default=None, description="Image dimension range")
    date_range: Optional[Dict[str, datetime]] = Field(default=None, description="Date range filter")
    
    # Quality filters
    min_quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum quality score")
    exclude_low_quality: bool = Field(default=False, description="Exclude low quality images")
    
    # Search options
    include_duplicates: bool = Field(default=False, description="Include duplicate matches")
    include_near_duplicates: bool = Field(default=True, description="Include near-duplicate matches")
    region_based: bool = Field(default=False, description="Enable region-based matching")
    multi_scale: bool = Field(default=False, description="Enable multi-scale analysis")
    
    # Output options
    include_features: bool = Field(default=False, description="Include feature vectors in response")
    include_analysis: bool = Field(default=False, description="Include detailed analysis")
    include_thumbnails: bool = Field(default=True, description="Include thumbnail URLs")
    
    # Pagination
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Results per page")
    
    # Sorting
    sort_by: str = Field(default="similarity_score", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order")
    
    @validator('reference_asset_id', 'reference_image_url', 'reference_features', 'reference_hash')
    def validate_reference_input(cls, v, values):
        """Ensure at least one reference input is provided"""
        if not any([values.get('reference_asset_id'), values.get('reference_image_url'), 
                   values.get('reference_features'), values.get('reference_hash')]):
            if not v:
                raise ValueError("At least one reference input must be provided")
        return v


class ImageSimilarityResponse(BaseModel):
    """Image similarity search response"""
    # Query information
    query_id: str = Field(..., description="Unique query identifier")
    reference_asset_id: Optional[str] = Field(default=None, description="Reference asset ID")
    similarity_type: ImageSimilarityType = Field(..., description="Search type used")
    
    # Results
    matches: List[SimilarityMatch] = Field(..., description="Similarity matches")
    total: int = Field(..., ge=0, description="Total number of matches")
    page: int = Field(..., ge=1, description="Current page")
    limit: int = Field(..., ge=1, description="Results per page")
    pages: int = Field(..., ge=0, description="Total pages")
    
    # Statistics
    max_similarity: Optional[float] = Field(default=None, description="Highest similarity score")
    avg_similarity: Optional[float] = Field(default=None, description="Average similarity score")
    min_similarity: Optional[float] = Field(default=None, description="Lowest similarity score")
    
    # Performance metrics
    took: int = Field(..., ge=0, description="Query execution time in milliseconds")
    feature_extraction_time: Optional[int] = Field(default=None, ge=0, description="Feature extraction time")
    search_time: Optional[int] = Field(default=None, ge=0, description="Search time")
    
    # Search metadata
    search_metadata: Dict[str, Any] = Field(default_factory=dict, description="Search execution metadata")
    
    # Clustering information (if applicable)
    clusters: Optional[List[Dict[str, Any]]] = Field(default=None, description="Result clusters")
    cluster_count: int = Field(default=0, ge=0, description="Number of clusters")


class ImageAnalysisRequest(BaseModel):
    """Request for image analysis and feature extraction"""
    asset_id: str = Field(..., description="Asset identifier")
    
    # Feature extraction options
    feature_models: List[ImageFeatureModel] = Field(
        default=[ImageFeatureModel.RESNET50], 
        description="Feature extraction models to use"
    )
    extract_hashes: bool = Field(default=True, description="Extract perceptual hashes")
    hash_types: List[ImageHashType] = Field(
        default=[ImageHashType.PERCEPTUAL_HASH], 
        description="Hash algorithms to use"
    )
    
    # Analysis options
    analyze_color: bool = Field(default=True, description="Perform color analysis")
    analyze_texture: bool = Field(default=False, description="Perform texture analysis")
    analyze_shape: bool = Field(default=False, description="Perform shape analysis")
    assess_quality: bool = Field(default=True, description="Assess image quality")
    detect_objects: bool = Field(default=False, description="Detect objects in image")
    
    # Processing options
    preprocessing: Optional[List[ImageProcessingType]] = Field(default=None, description="Preprocessing steps")
    resize_for_analysis: bool = Field(default=True, description="Resize image for analysis")
    target_size: Optional[Dict[str, int]] = Field(default=None, description="Target size for analysis")
    
    # Performance options
    parallel_processing: bool = Field(default=True, description="Enable parallel processing")
    gpu_acceleration: bool = Field(default=False, description="Use GPU acceleration")
    force_reanalysis: bool = Field(default=False, description="Force re-analysis even if cached")


class ImageAnalysisResponse(BaseModel):
    """Response for image analysis"""
    asset_id: str = Field(..., description="Asset identifier")
    analysis: ImageAnalysis = Field(..., description="Analysis results")
    analysis_success: bool = Field(..., description="Whether analysis succeeded")
    
    # Processing information
    processing_time_ms: float = Field(..., ge=0, description="Total processing time")
    models_used: List[str] = Field(..., description="Models used for analysis")
    preprocessing_applied: List[str] = Field(default_factory=list, description="Applied preprocessing")
    
    # Errors and warnings
    errors: List[str] = Field(default_factory=list, description="Error messages")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    
    # Cache information
    from_cache: bool = Field(default=False, description="Result retrieved from cache")
    cached_at: Optional[datetime] = Field(default=None, description="Cache timestamp")


class ImageSimilarityStats(BaseModel):
    """Image similarity search statistics"""
    # Search statistics
    total_searches: int = Field(default=0, ge=0, description="Total similarity searches performed")
    total_comparisons: int = Field(default=0, ge=0, description="Total image comparisons")
    total_matches_found: int = Field(default=0, ge=0, description="Total similarity matches found")
    unique_assets_searched: int = Field(default=0, ge=0, description="Unique assets used as reference")
    
    # Performance metrics
    avg_search_time_ms: float = Field(default=0.0, ge=0, description="Average search time")
    avg_feature_extraction_time_ms: float = Field(default=0.0, ge=0, description="Average feature extraction time")
    cache_hit_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Feature cache hit rate")
    
    # Asset statistics
    images_analyzed: int = Field(default=0, ge=0, description="Total images analyzed")
    total_features_extracted: int = Field(default=0, ge=0, description="Total feature vectors extracted")
    total_hashes_computed: int = Field(default=0, ge=0, description="Total perceptual hashes computed")
    
    # Model usage statistics
    feature_model_usage: Dict[str, int] = Field(default_factory=dict, description="Feature model usage")
    similarity_metric_usage: Dict[str, int] = Field(default_factory=dict, description="Similarity metric usage")
    hash_type_usage: Dict[str, int] = Field(default_factory=dict, description="Hash type usage")
    
    # Search type distribution
    search_type_distribution: Dict[str, int] = Field(default_factory=dict, description="Search type distribution")
    similarity_score_distribution: Dict[str, int] = Field(default_factory=dict, description="Similarity score distribution")
    
    # Quality statistics
    avg_image_quality: float = Field(default=0.0, ge=0.0, le=1.0, description="Average image quality")
    quality_distribution: Dict[str, int] = Field(default_factory=dict, description="Image quality distribution")
    
    # Error statistics
    feature_extraction_failures: int = Field(default=0, ge=0, description="Feature extraction failures")
    search_failures: int = Field(default=0, ge=0, description="Search failures")
    low_quality_images: int = Field(default=0, ge=0, description="Low quality images excluded")


# ========================================================================================
# Audio Fingerprinting Schemas
# ========================================================================================

class AudioFingerprintingAlgorithm(str, Enum):
    """Audio fingerprinting algorithms"""
    CHROMAPRINT = "chromaprint"
    ECHOPRINT = "echoprint"
    DEJAVU = "dejavu"
    AUDFPRINT = "audfprint"
    PANAKO = "panako"
    SHAZAM = "shazam"
    SOUNDHOUND = "soundhound"
    MUSICBRAINZ = "musicbrainz"


class AudioFingerprintType(str, Enum):
    """Types of audio fingerprints"""
    FULL_TRACK = "full_track"
    SEGMENT = "segment"
    ROBUST = "robust"
    FAST = "fast"
    HIGH_PRECISION = "high_precision"
    BROADCAST = "broadcast"
    MUSIC = "music"
    SPEECH = "speech"


class AudioMatchType(str, Enum):
    """Types of audio matches"""
    EXACT_MATCH = "exact_match"
    PARTIAL_MATCH = "partial_match"
    SIMILAR_AUDIO = "similar_audio"
    COVER_VERSION = "cover_version"
    REMIX = "remix"
    SAMPLE = "sample"
    BROADCAST_MATCH = "broadcast_match"
    MUSIC_IDENTIFICATION = "music_identification"
    SPEECH_MATCH = "speech_match"
    COPYRIGHT_MATCH = "copyright_match"


class AudioSearchType(str, Enum):
    """Types of audio fingerprint searches"""
    DUPLICATE_DETECTION = "duplicate_detection"
    MUSIC_IDENTIFICATION = "music_identification"
    COPYRIGHT_MONITORING = "copyright_monitoring"
    BROADCAST_MONITORING = "broadcast_monitoring"
    SAMPLE_DETECTION = "sample_detection"
    COVER_DETECTION = "cover_detection"
    SPEECH_MATCHING = "speech_matching"
    AUDIO_VERIFICATION = "audio_verification"
    PLAYLIST_GENERATION = "playlist_generation"
    SIMILAR_AUDIO = "similar_audio"


class AudioFeatureType(str, Enum):
    """Types of audio features for analysis"""
    CHROMAGRAM = "chromagram"
    MFCC = "mfcc"
    SPECTRAL_CENTROID = "spectral_centroid"
    SPECTRAL_ROLLOFF = "spectral_rolloff"
    SPECTRAL_BANDWIDTH = "spectral_bandwidth"
    ZERO_CROSSING_RATE = "zero_crossing_rate"
    TEMPO = "tempo"
    BEAT = "beat"
    PITCH = "pitch"
    TIMBRE = "timbre"
    LOUDNESS = "loudness"
    HARMONY = "harmony"
    RHYTHM = "rhythm"


class AudioQualityLevel(str, Enum):
    """Audio quality levels"""
    PRISTINE = "pristine"
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNUSABLE = "unusable"


class AudioFingerprint(BaseModel):
    """Audio fingerprint representation"""
    algorithm: AudioFingerprintingAlgorithm = Field(..., description="Fingerprinting algorithm used")
    fingerprint_type: AudioFingerprintType = Field(..., description="Type of fingerprint")
    fingerprint_data: str = Field(..., description="Fingerprint data (base64 or hex encoded)")
    duration_ms: int = Field(..., gt=0, description="Duration of fingerprinted audio in milliseconds")
    sample_rate: int = Field(..., gt=0, description="Sample rate in Hz")
    channels: int = Field(..., gt=0, le=32, description="Number of audio channels")
    bit_depth: Optional[int] = Field(default=None, gt=0, le=64, description="Bit depth")
    offset_ms: Optional[int] = Field(default=None, ge=0, description="Offset from start in milliseconds")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Fingerprint quality confidence")
    is_robust: bool = Field(default=True, description="Whether fingerprint is robust to distortions")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class AudioFeatures(BaseModel):
    """Extracted audio features for analysis"""
    chromagram: Optional[List[List[float]]] = Field(default=None, description="Chroma feature matrix")
    mfcc: Optional[List[List[float]]] = Field(default=None, description="MFCC coefficients")
    spectral_centroid: Optional[List[float]] = Field(default=None, description="Spectral centroid values")
    spectral_rolloff: Optional[List[float]] = Field(default=None, description="Spectral rolloff values")
    spectral_bandwidth: Optional[List[float]] = Field(default=None, description="Spectral bandwidth values")
    zero_crossing_rate: Optional[List[float]] = Field(default=None, description="Zero crossing rate values")
    tempo: Optional[float] = Field(default=None, gt=0, description="Tempo in BPM")
    beat_positions: Optional[List[float]] = Field(default=None, description="Beat positions in seconds")
    key: Optional[str] = Field(default=None, description="Musical key")
    mode: Optional[str] = Field(default=None, description="Musical mode (major/minor)")
    time_signature: Optional[str] = Field(default=None, description="Time signature")
    loudness_db: Optional[float] = Field(default=None, description="Average loudness in dB")
    dynamic_range_db: Optional[float] = Field(default=None, ge=0, description="Dynamic range in dB")
    pitch_hz: Optional[float] = Field(default=None, gt=0, description="Average pitch in Hz")


class AudioSegment(BaseModel):
    """Audio segment information"""
    start_time_ms: int = Field(..., ge=0, description="Start time in milliseconds")
    end_time_ms: int = Field(..., gt=0, description="End time in milliseconds")
    duration_ms: int = Field(..., gt=0, description="Duration in milliseconds")
    fingerprint: Optional[AudioFingerprint] = Field(default=None, description="Segment fingerprint")
    features: Optional[AudioFeatures] = Field(default=None, description="Segment audio features")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Segment detection confidence")
    label: Optional[str] = Field(default=None, description="Segment label or category")
    
    @validator('end_time_ms')
    def validate_times(cls, v, values):
        """Ensure end time is after start time"""
        if 'start_time_ms' in values and v <= values['start_time_ms']:
            raise ValueError("End time must be after start time")
        return v
    
    @validator('duration_ms')
    def validate_duration(cls, v, values):
        """Ensure duration matches time range"""
        if 'start_time_ms' in values and 'end_time_ms' in values:
            expected_duration = values['end_time_ms'] - values['start_time_ms']
            if v != expected_duration:
                return expected_duration
        return v


class MusicMetadata(BaseModel):
    """Music identification metadata"""
    title: Optional[str] = Field(default=None, description="Track title")
    artist: Optional[str] = Field(default=None, description="Artist name")
    album: Optional[str] = Field(default=None, description="Album name")
    album_artist: Optional[str] = Field(default=None, description="Album artist")
    composer: Optional[str] = Field(default=None, description="Composer")
    genre: Optional[List[str]] = Field(default=None, description="Music genres")
    year: Optional[int] = Field(default=None, ge=1000, le=9999, description="Release year")
    track_number: Optional[int] = Field(default=None, gt=0, description="Track number")
    duration_ms: Optional[int] = Field(default=None, gt=0, description="Track duration")
    isrc: Optional[str] = Field(default=None, description="International Standard Recording Code")
    musicbrainz_id: Optional[str] = Field(default=None, description="MusicBrainz track ID")
    spotify_id: Optional[str] = Field(default=None, description="Spotify track ID")
    label: Optional[str] = Field(default=None, description="Record label")
    copyright: Optional[str] = Field(default=None, description="Copyright information")
    lyrics_snippet: Optional[str] = Field(default=None, description="Lyrics snippet")


class AudioQualityMetrics(BaseModel):
    """Audio quality assessment metrics"""
    overall_quality: AudioQualityLevel = Field(..., description="Overall quality level")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Quality score (0-1)")
    
    # Technical metrics
    sample_rate: int = Field(..., gt=0, description="Sample rate in Hz")
    bit_depth: int = Field(..., gt=0, description="Bit depth")
    bitrate_kbps: Optional[int] = Field(default=None, gt=0, description="Bitrate in kbps")
    codec: Optional[str] = Field(default=None, description="Audio codec")
    
    # Quality indicators
    clipping_detected: bool = Field(default=False, description="Whether clipping is detected")
    noise_level_db: Optional[float] = Field(default=None, description="Noise level in dB")
    snr_db: Optional[float] = Field(default=None, ge=0, description="Signal-to-noise ratio in dB")
    thd_percent: Optional[float] = Field(default=None, ge=0, le=100, description="Total harmonic distortion %")
    
    # Perceptual metrics
    clarity_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Clarity score")
    presence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Presence score")
    warmth_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Warmth score")
    
    # Issues detected
    issues: List[str] = Field(default_factory=list, description="Quality issues detected")
    warnings: List[str] = Field(default_factory=list, description="Quality warnings")


class AudioAnalysis(BaseModel):
    """Comprehensive audio analysis result"""
    asset_id: str = Field(..., description="Asset identifier")
    audio_path: str = Field(..., description="Audio file path")
    duration_ms: int = Field(..., gt=0, description="Total duration in milliseconds")
    format: str = Field(..., description="Audio format")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    
    # Fingerprints
    fingerprints: List[AudioFingerprint] = Field(default_factory=list, description="Audio fingerprints")
    
    # Features
    features: Optional[AudioFeatures] = Field(default=None, description="Extracted audio features")
    
    # Segmentation
    segments: List[AudioSegment] = Field(default_factory=list, description="Audio segments")
    
    # Music metadata (if identified)
    music_metadata: Optional[MusicMetadata] = Field(default=None, description="Identified music metadata")
    
    # Quality assessment
    quality_metrics: Optional[AudioQualityMetrics] = Field(default=None, description="Audio quality metrics")
    
    # Analysis metadata
    analyzed_at: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")
    analysis_version: str = Field(default="1.0", description="Analysis version")
    processing_time_ms: float = Field(..., ge=0, description="Analysis processing time")
    
    # Speech detection (if applicable)
    speech_segments: List[AudioSegment] = Field(default_factory=list, description="Detected speech segments")
    music_segments: List[AudioSegment] = Field(default_factory=list, description="Detected music segments")
    silence_segments: List[AudioSegment] = Field(default_factory=list, description="Detected silence segments")


class AudioMatch(BaseModel):
    """Single audio match result"""
    asset_id: str = Field(..., description="Matched asset ID")
    match_score: float = Field(..., ge=0.0, le=1.0, description="Match confidence score")
    match_type: AudioMatchType = Field(..., description="Type of match")
    
    # Asset information
    asset_name: Optional[str] = Field(default=None, description="Asset name")
    asset_type: Optional[str] = Field(default=None, description="Asset type")
    file_path: Optional[str] = Field(default=None, description="File path")
    
    # Match details
    time_offset_ms: Optional[int] = Field(default=None, description="Time offset of match in milliseconds")
    matched_duration_ms: Optional[int] = Field(default=None, gt=0, description="Duration of matched segment")
    
    # For music identification
    music_metadata: Optional[MusicMetadata] = Field(default=None, description="Identified music metadata")
    
    # Match segments
    query_segment: Optional[AudioSegment] = Field(default=None, description="Query audio segment")
    matched_segment: Optional[AudioSegment] = Field(default=None, description="Matched audio segment")
    
    # Additional info
    confidence_details: Optional[Dict[str, float]] = Field(default=None, description="Detailed confidence scores")
    match_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional match metadata")


class AudioFingerprintQuery(BaseModel):
    """Audio fingerprint search query"""
    # Input options (one required)
    reference_asset_id: Optional[str] = Field(default=None, description="Reference asset ID")
    reference_audio_url: Optional[str] = Field(default=None, description="Reference audio URL")
    reference_fingerprint: Optional[str] = Field(default=None, description="Pre-computed fingerprint")
    audio_data_base64: Optional[str] = Field(default=None, description="Audio data in base64")
    
    # Search parameters
    search_type: AudioSearchType = Field(default=AudioSearchType.DUPLICATE_DETECTION, description="Type of search")
    fingerprint_algorithm: AudioFingerprintingAlgorithm = Field(default=AudioFingerprintingAlgorithm.CHROMAPRINT, description="Fingerprinting algorithm")
    
    # Match criteria
    min_match_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Minimum match score")
    min_match_duration_ms: Optional[int] = Field(default=None, gt=0, description="Minimum match duration")
    allow_time_stretch: bool = Field(default=True, description="Allow tempo variations")
    allow_pitch_shift: bool = Field(default=True, description="Allow pitch variations")
    
    # Search scope
    asset_types: Optional[List[str]] = Field(default=None, description="Asset types to search")
    date_range: Optional[Dict[str, datetime]] = Field(default=None, description="Date range filter")
    duration_range_ms: Optional[Dict[str, int]] = Field(default=None, description="Duration range filter")
    
    # Music-specific options
    search_music_databases: bool = Field(default=False, description="Search external music databases")
    include_cover_versions: bool = Field(default=False, description="Include cover versions")
    include_remixes: bool = Field(default=False, description="Include remixes")
    include_samples: bool = Field(default=False, description="Include samples")
    
    # Output options
    include_features: bool = Field(default=False, description="Include audio features")
    include_segments: bool = Field(default=False, description="Include matched segments")
    include_quality_metrics: bool = Field(default=False, description="Include quality metrics")
    max_matches_per_asset: int = Field(default=1, ge=1, le=10, description="Max matches per asset")
    
    # Pagination
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Results per page")
    
    # Sorting
    sort_by: str = Field(default="match_score", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order")
    
    @validator('reference_asset_id', 'reference_audio_url', 'reference_fingerprint', 'audio_data_base64')
    def validate_reference_input(cls, v, values):
        """Ensure at least one reference input is provided"""
        if not any([values.get('reference_asset_id'), values.get('reference_audio_url'), 
                   values.get('reference_fingerprint'), values.get('audio_data_base64')]):
            if not v:
                raise ValueError("At least one reference input must be provided")
        return v


class AudioFingerprintResponse(BaseModel):
    """Audio fingerprint search response"""
    # Query information
    query_id: str = Field(..., description="Unique query identifier")
    reference_asset_id: Optional[str] = Field(default=None, description="Reference asset ID")
    search_type: AudioSearchType = Field(..., description="Search type used")
    
    # Results
    matches: List[AudioMatch] = Field(..., description="Audio matches")
    total: int = Field(..., ge=0, description="Total number of matches")
    page: int = Field(..., ge=1, description="Current page")
    limit: int = Field(..., ge=1, description="Results per page")
    pages: int = Field(..., ge=0, description="Total pages")
    
    # Music identification results
    identified_music: Optional[MusicMetadata] = Field(default=None, description="Identified music metadata")
    music_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Music ID confidence")
    
    # Statistics
    best_match_score: Optional[float] = Field(default=None, description="Best match score")
    avg_match_score: Optional[float] = Field(default=None, description="Average match score")
    unique_matches: int = Field(default=0, ge=0, description="Number of unique matches")
    
    # Performance metrics
    took: int = Field(..., ge=0, description="Query execution time in milliseconds")
    fingerprint_time: Optional[int] = Field(default=None, ge=0, description="Fingerprinting time")
    search_time: Optional[int] = Field(default=None, ge=0, description="Search time")
    
    # Search metadata
    search_metadata: Dict[str, Any] = Field(default_factory=dict, description="Search execution metadata")


class AudioAnalysisRequest(BaseModel):
    """Request for audio analysis and fingerprinting"""
    asset_id: str = Field(..., description="Asset identifier")
    
    # Fingerprinting options
    fingerprint_algorithms: List[AudioFingerprintingAlgorithm] = Field(
        default=[AudioFingerprintingAlgorithm.CHROMAPRINT],
        description="Fingerprinting algorithms to use"
    )
    fingerprint_types: List[AudioFingerprintType] = Field(
        default=[AudioFingerprintType.FULL_TRACK],
        description="Types of fingerprints to generate"
    )
    
    # Feature extraction
    extract_features: bool = Field(default=True, description="Extract audio features")
    feature_types: Optional[List[AudioFeatureType]] = Field(default=None, description="Specific features to extract")
    
    # Segmentation
    segment_audio: bool = Field(default=False, description="Perform audio segmentation")
    detect_speech: bool = Field(default=False, description="Detect speech segments")
    detect_music: bool = Field(default=False, description="Detect music segments")
    detect_silence: bool = Field(default=False, description="Detect silence segments")
    
    # Quality assessment
    assess_quality: bool = Field(default=True, description="Assess audio quality")
    
    # Music identification
    identify_music: bool = Field(default=False, description="Attempt music identification")
    
    # Processing options
    segment_duration_ms: Optional[int] = Field(default=None, gt=0, description="Segment duration for analysis")
    overlap_ms: Optional[int] = Field(default=None, ge=0, description="Segment overlap")
    
    # Performance options
    parallel_processing: bool = Field(default=True, description="Enable parallel processing")
    gpu_acceleration: bool = Field(default=False, description="Use GPU acceleration if available")
    force_reanalysis: bool = Field(default=False, description="Force re-analysis even if cached")


class AudioAnalysisResponse(BaseModel):
    """Response for audio analysis"""
    asset_id: str = Field(..., description="Asset identifier")
    analysis: AudioAnalysis = Field(..., description="Analysis results")
    analysis_success: bool = Field(..., description="Whether analysis succeeded")
    
    # Processing information
    processing_time_ms: float = Field(..., ge=0, description="Total processing time")
    algorithms_used: List[str] = Field(..., description="Algorithms used for analysis")
    
    # Errors and warnings
    errors: List[str] = Field(default_factory=list, description="Error messages")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    
    # Cache information
    from_cache: bool = Field(default=False, description="Result retrieved from cache")
    cached_at: Optional[datetime] = Field(default=None, description="Cache timestamp")


class AudioFingerprintStats(BaseModel):
    """Audio fingerprinting system statistics"""
    # Search statistics
    total_searches: int = Field(default=0, ge=0, description="Total fingerprint searches performed")
    total_matches_found: int = Field(default=0, ge=0, description="Total matches found")
    unique_assets_searched: int = Field(default=0, ge=0, description="Unique assets used as reference")
    
    # Performance metrics
    avg_search_time_ms: float = Field(default=0.0, ge=0, description="Average search time")
    avg_fingerprint_time_ms: float = Field(default=0.0, ge=0, description="Average fingerprinting time")
    avg_match_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Average match score")
    
    # Asset statistics
    audio_files_analyzed: int = Field(default=0, ge=0, description="Total audio files analyzed")
    total_fingerprints_generated: int = Field(default=0, ge=0, description="Total fingerprints generated")
    total_duration_analyzed_hours: float = Field(default=0.0, ge=0, description="Total audio duration analyzed")
    
    # Algorithm usage
    algorithm_usage: Dict[str, int] = Field(default_factory=dict, description="Fingerprinting algorithm usage")
    search_type_distribution: Dict[str, int] = Field(default_factory=dict, description="Search type distribution")
    match_type_distribution: Dict[str, int] = Field(default_factory=dict, description="Match type distribution")
    
    # Music identification
    music_tracks_identified: int = Field(default=0, ge=0, description="Music tracks identified")
    music_identification_accuracy: float = Field(default=0.0, ge=0.0, le=1.0, description="Music ID accuracy")
    
    # Quality statistics
    avg_audio_quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Average audio quality")
    quality_distribution: Dict[str, int] = Field(default_factory=dict, description="Audio quality distribution")
    
    # Copyright monitoring
    copyright_matches_found: int = Field(default=0, ge=0, description="Copyright matches found")
    potential_violations: int = Field(default=0, ge=0, description="Potential copyright violations")
    
    # Error statistics
    fingerprinting_failures: int = Field(default=0, ge=0, description="Fingerprinting failures")
    search_failures: int = Field(default=0, ge=0, description="Search failures")
    low_quality_audio_excluded: int = Field(default=0, ge=0, description="Low quality audio excluded")
"""Pydantic schemas for AI-powered search features"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

from .schemas import SearchFilter


class SearchIntent(str, Enum):
    """Search intent types"""
    SEARCH = "search"
    FILTER = "filter"
    BROWSE = "browse"
    DISCOVER = "discover"
    QUESTION = "question"
    COMMAND = "command"


class EntityType(str, Enum):
    """Entity types for extraction"""
    PERSON = "person"
    LOCATION = "location"
    ORGANIZATION = "organization"
    DATE = "date"
    EVENT = "event"
    PRODUCT = "product"
    CONCEPT = "concept"


class Entity(BaseModel):
    """Extracted entity"""
    type: EntityType
    value: str
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    position: Optional[Dict[str, int]] = None  # Start and end positions


class TemporalReference(BaseModel):
    """Temporal reference in query"""
    type: str = Field(..., description="absolute, relative, range")
    value: Optional[str] = None
    range: Optional[Dict[str, str]] = None
    parsed_date: Optional[datetime] = None


class QueryAnalysis(BaseModel):
    """Query analysis results"""
    intent: SearchIntent = SearchIntent.SEARCH
    entities: List[Entity] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)
    temporal: Optional[TemporalReference] = None
    sentiment: Optional[str] = None
    language: str = Field("en", description="Detected language")
    topics: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class AISearchRequest(BaseModel):
    """AI-powered search request"""
    query: str = Field(..., min_length=1, max_length=500)
    filters: Optional[List[SearchFilter]] = Field(default_factory=list)
    use_semantic: bool = Field(True, description="Use semantic search")
    use_entities: bool = Field(True, description="Extract and use entities")
    use_temporal: bool = Field(True, description="Parse temporal references")
    personalize: bool = Field(True, description="Personalize results")
    explain_results: bool = Field(False, description="Include explanations")
    max_suggestions: int = Field(5, ge=0, le=20)
    sort_by: Optional[str] = None
    sort_order: str = Field("desc", regex="^(asc|desc)$")
    offset: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)
    
    class Config:
        schema_extra = {
            "example": {
                "query": "videos about climate change from last month",
                "use_semantic": True,
                "use_entities": True,
                "use_temporal": True,
                "limit": 20
            }
        }


class AISearchResult(BaseModel):
    """Enhanced search result with AI features"""
    id: str
    type: str
    title: str
    description: str
    score: float
    highlights: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    explanations: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Explanations for why this result matched"
    )
    ai_score: float = Field(0.0, description="AI-enhanced relevance score")
    matched_entities: List[Entity] = Field(default_factory=list)
    semantic_similarity: Optional[float] = None
    personalization_score: Optional[float] = None


class AISearchResponse(BaseModel):
    """AI-powered search response"""
    query: str
    enhanced_query: Optional[str] = None
    total: int
    results: List[Dict[str, Any]]  # Changed to accept dictionary format
    facets: Dict[str, List[Dict[str, Any]]]
    suggestions: List[str] = Field(default_factory=list)
    query_analysis: Optional[QueryAnalysis] = None
    search_time: float
    ai_features_used: List[str] = Field(default_factory=list)
    debug_info: Optional[Dict[str, Any]] = None


class QueryAnalysisResponse(BaseModel):
    """Response for query analysis endpoint"""
    original_query: str
    enhanced_query: str
    intent: SearchIntent
    entities: List[Entity]
    filters: Dict[str, Any]
    temporal: Optional[TemporalReference]
    suggestions: List[str]
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    
    class Config:
        schema_extra = {
            "example": {
                "original_query": "john smith videos from yesterday",
                "enhanced_query": "john smith videos from yesterday interview documentary",
                "intent": "search",
                "entities": [
                    {"type": "person", "value": "John Smith", "confidence": 0.95}
                ],
                "temporal": {
                    "type": "relative",
                    "value": "yesterday",
                    "parsed_date": "2024-01-14T00:00:00Z"
                },
                "suggestions": ["john smith interview", "john smith documentary"],
                "confidence": 0.85
            }
        }


class SemanticSearchRequest(BaseModel):
    """Semantic similarity search request"""
    query: str = Field(..., min_length=1, max_length=500)
    threshold: float = Field(0.7, ge=0.0, le=1.0, description="Similarity threshold")
    use_cache: bool = Field(True, description="Use embedding cache")
    limit: int = Field(20, ge=1, le=100)


class SimilaritySearchRequest(BaseModel):
    """Find similar items request"""
    item_id: str = Field(..., description="Reference item ID")
    similarity_type: str = Field("content", description="content, visual, metadata")
    threshold: float = Field(0.7, ge=0.0, le=1.0)
    include_self: bool = Field(False)
    limit: int = Field(20, ge=1, le=100)


class NaturalLanguageQuery(BaseModel):
    """Natural language question"""
    question: str = Field(..., min_length=1, max_length=500)
    context: Optional[str] = Field(None, description="Additional context")
    return_sources: bool = Field(True, description="Include source documents")
    max_sources: int = Field(5, ge=1, le=10)


class NaturalLanguageResponse(BaseModel):
    """Natural language answer"""
    question: str
    answer: str
    sources: List[AISearchResult] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    answer_type: str = Field("direct", description="direct, summary, not_found")
    follow_up_questions: List[str] = Field(default_factory=list)


class SearchSuggestion(BaseModel):
    """Search suggestion with metadata"""
    text: str
    type: str = Field("completion", description="completion, correction, related")
    score: float = Field(0.0, ge=0.0, le=1.0)
    source: str = Field("ai", description="ai, history, trending")


class TrendingSearch(BaseModel):
    """Trending search item"""
    query: str
    score: int
    trend: str = Field("stable", description="up, down, stable, new")
    category: Optional[str] = None
    timeframe: str


class SearchFeedback(BaseModel):
    """Search result feedback"""
    query: str
    result_id: str
    feedback_type: str = Field(..., description="clicked, relevant, irrelevant, reported")
    position: Optional[int] = Field(None, description="Result position when clicked")
    dwell_time: Optional[int] = Field(None, description="Time spent on result in seconds")
    comment: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AISearchConfig(BaseModel):
    """AI search configuration"""
    semantic_model: Optional[str] = Field(None, description="Semantic model name")
    embedding_dimension: int = Field(384, description="Embedding vector dimension")
    query_enhancement_model: Optional[str] = Field(None, description="Query enhancement model")
    entity_extraction_model: Optional[str] = Field(None, description="NER model")
    reranking_model: Optional[str] = Field(None, description="Result reranking model")
    personalization_enabled: bool = Field(False)
    explanation_enabled: bool = Field(False)
    cache_embeddings: bool = Field(True)
    cache_ttl: int = Field(3600, description="Cache TTL in seconds")


class AIIndexRequest(BaseModel):
    """Request to index document with AI enhancements"""
    document: Dict[str, Any]
    generate_embeddings: bool = Field(True)
    extract_entities: bool = Field(True)
    generate_tags: bool = Field(True)
    generate_summary: bool = Field(True)
    custom_processors: List[str] = Field(default_factory=list)


class AIIndexResponse(BaseModel):
    """Response from AI-enhanced indexing"""
    document_id: str
    status: str = Field("success", description="success, partial, failed")
    enhancements: Dict[str, bool] = Field(default_factory=dict)
    processing_time: float
    errors: List[str] = Field(default_factory=list)


class SearchExplanation(BaseModel):
    """Explanation for search result ranking"""
    result_id: str
    total_score: float
    score_breakdown: Dict[str, float] = Field(
        default_factory=dict,
        description="Breakdown of scoring components"
    )
    matched_terms: List[str] = Field(default_factory=list)
    matched_fields: List[str] = Field(default_factory=list)
    boost_factors: Dict[str, float] = Field(default_factory=dict)
    penalties: Dict[str, float] = Field(default_factory=dict)


class BatchSearchRequest(BaseModel):
    """Batch search request for multiple queries"""
    queries: List[AISearchRequest]
    parallel: bool = Field(True, description="Execute queries in parallel")
    dedup_results: bool = Field(True, description="Deduplicate results across queries")
    merge_strategy: str = Field("score", description="score, relevance, diversity")


class BatchSearchResponse(BaseModel):
    """Batch search response"""
    results: List[AISearchResponse]
    merged_results: Optional[List[AISearchResult]] = None
    total_time: float
    query_times: List[float] = Field(default_factory=list)
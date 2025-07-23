"""
Fuzzy Search Service - Enhanced fuzzy matching capabilities
"""

import re
from typing import Dict, Any, List, Optional, Tuple, Union
from enum import Enum
from dataclasses import dataclass
import structlog
from opensearchpy import AsyncOpenSearch

from ..models.schemas import SearchQuery, IndexType, SearchType, SortOrder
from ..core.config import get_settings
from ..core.exceptions import SearchError, InvalidQueryError

logger = structlog.get_logger()


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


@dataclass
class FuzzyConfig:
    """Configuration for fuzzy matching"""
    fuzziness: FuzzinessType = FuzzinessType.AUTO
    prefix_length: int = 1
    max_expansions: int = 50
    transpositions: bool = True
    rewrite: str = "top_terms_boost_1024"
    boost: float = 1.0


@dataclass
class FuzzyFieldConfig:
    """Configuration for field-specific fuzzy matching"""
    field: str
    boost: float = 1.0
    fuzziness: Optional[FuzzinessType] = None
    prefix_length: Optional[int] = None
    max_expansions: Optional[int] = None


class FuzzySearchService:
    """Service for advanced fuzzy search capabilities"""
    
    def __init__(self, opensearch_client: AsyncOpenSearch):
        self.client = opensearch_client
        self.settings = get_settings()
        
        # Default fuzzy configurations for different contexts
        self.default_configs = {
            "strict": FuzzyConfig(
                fuzziness=FuzzinessType.DISTANCE_1,
                prefix_length=2,
                max_expansions=10
            ),
            "moderate": FuzzyConfig(
                fuzziness=FuzzinessType.AUTO,
                prefix_length=1,
                max_expansions=50
            ),
            "loose": FuzzyConfig(
                fuzziness=FuzzinessType.DISTANCE_2,
                prefix_length=0,
                max_expansions=100
            )
        }
        
        # Field-specific configurations
        self.field_configs = {
            "name": FuzzyFieldConfig("name^3", boost=3.0, fuzziness=FuzzinessType.AUTO),
            "title": FuzzyFieldConfig("title^3", boost=3.0, fuzziness=FuzzinessType.AUTO),
            "description": FuzzyFieldConfig("description^2", boost=2.0, fuzziness=FuzzinessType.AUTO),
            "tags": FuzzyFieldConfig("tags^2", boost=2.0, fuzziness=FuzzinessType.DISTANCE_1),
            "keywords": FuzzyFieldConfig("keywords^2", boost=2.0, fuzziness=FuzzinessType.DISTANCE_1),
            "file_name": FuzzyFieldConfig("file_name^2", boost=2.0, fuzziness=FuzzinessType.AUTO),
            "creator": FuzzyFieldConfig("creator", boost=1.5, fuzziness=FuzzinessType.AUTO),
            "content": FuzzyFieldConfig("content", boost=1.0, fuzziness=FuzzinessType.AUTO),
            "transcript": FuzzyFieldConfig("transcript", boost=1.0, fuzziness=FuzzinessType.AUTO),
            "ocr_text": FuzzyFieldConfig("ocr_text", boost=1.0, fuzziness=FuzzinessType.AUTO),
        }
    
    def build_single_term_fuzzy_query(
        self, 
        term: str, 
        field: str = "_all", 
        config: Optional[FuzzyConfig] = None
    ) -> Dict[str, Any]:
        """Build a single-term fuzzy query"""
        if config is None:
            config = self.default_configs["moderate"]
        
        query = {
            "fuzzy": {
                field: {
                    "value": term,
                    "fuzziness": config.fuzziness.value,
                    "prefix_length": config.prefix_length,
                    "max_expansions": config.max_expansions,
                    "transpositions": config.transpositions,
                    "rewrite": config.rewrite
                }
            }
        }
        
        if config.boost != 1.0:
            query["fuzzy"][field]["boost"] = config.boost
            
        return query
    
    def build_multi_term_fuzzy_query(
        self, 
        terms: List[str], 
        fields: List[str] = None,
        config: Optional[FuzzyConfig] = None,
        operator: str = "OR"
    ) -> Dict[str, Any]:
        """Build a multi-term fuzzy query"""
        if config is None:
            config = self.default_configs["moderate"]
        
        if fields is None:
            fields = ["_all"]
        
        # Build individual fuzzy queries for each term
        term_queries = []
        for term in terms:
            if len(term.strip()) < 2:  # Skip very short terms
                continue
                
            for field in fields:
                field_config = self.field_configs.get(field.split("^")[0], None)
                if field_config:
                    # Use field-specific config
                    fuzziness = field_config.fuzziness or config.fuzziness
                    boost = field_config.boost
                else:
                    fuzziness = config.fuzziness
                    boost = config.boost
                
                term_query = {
                    "fuzzy": {
                        field: {
                            "value": term,
                            "fuzziness": fuzziness.value,
                            "prefix_length": config.prefix_length,
                            "max_expansions": config.max_expansions,
                            "transpositions": config.transpositions,
                            "boost": boost
                        }
                    }
                }
                term_queries.append(term_query)
        
        # Combine based on operator
        if operator == "AND":
            return {
                "bool": {
                    "must": term_queries
                }
            }
        else:  # OR
            return {
                "bool": {
                    "should": term_queries,
                    "minimum_should_match": 1
                }
            }
    
    def build_fuzzy_phrase_query(
        self, 
        phrase: str, 
        fields: List[str] = None,
        slop: int = 2,
        config: Optional[FuzzyConfig] = None
    ) -> Dict[str, Any]:
        """Build a fuzzy phrase query using span queries"""
        if config is None:
            config = self.default_configs["moderate"]
        
        if fields is None:
            fields = ["_all"]
        
        # Split phrase into terms
        terms = self._tokenize_phrase(phrase)
        
        # Build span queries for each field
        field_queries = []
        for field in fields:
            span_queries = []
            for term in terms:
                span_queries.append({
                    "span_multi": {
                        "match": {
                            "fuzzy": {
                                field: {
                                    "value": term,
                                    "fuzziness": config.fuzziness.value,
                                    "prefix_length": config.prefix_length,
                                    "max_expansions": config.max_expansions
                                }
                            }
                        }
                    }
                })
            
            field_query = {
                "span_near": {
                    "clauses": span_queries,
                    "slop": slop,
                    "in_order": True
                }
            }
            field_queries.append(field_query)
        
        if len(field_queries) == 1:
            return field_queries[0]
        else:
            return {
                "bool": {
                    "should": field_queries,
                    "minimum_should_match": 1
                }
            }
    
    def build_cross_field_fuzzy_query(
        self, 
        query_text: str, 
        fields: List[str] = None,
        config: Optional[FuzzyConfig] = None
    ) -> Dict[str, Any]:
        """Build a cross-field fuzzy query"""
        if config is None:
            config = self.default_configs["moderate"]
        
        if fields is None:
            fields = list(self.field_configs.keys())
        
        # Prepare fields with their configurations
        prepared_fields = []
        for field in fields:
            field_config = self.field_configs.get(field, None)
            if field_config:
                prepared_fields.append(field_config.field)
            else:
                prepared_fields.append(field)
        
        return {
            "multi_match": {
                "query": query_text,
                "fields": prepared_fields,
                "type": "cross_fields",
                "fuzziness": config.fuzziness.value,
                "prefix_length": config.prefix_length,
                "max_expansions": config.max_expansions,
                "operator": "and"
            }
        }
    
    def build_adaptive_fuzzy_query(
        self, 
        query_text: str, 
        fields: List[str] = None,
        match_type: FuzzyMatchType = FuzzyMatchType.MULTI_TERM
    ) -> Dict[str, Any]:
        """Build an adaptive fuzzy query based on query characteristics"""
        
        # Analyze query to determine optimal fuzzy strategy
        query_analysis = self._analyze_query(query_text)
        
        # Select appropriate configuration
        if query_analysis["avg_word_length"] < 4:
            config = self.default_configs["strict"]
        elif query_analysis["contains_technical_terms"]:
            config = self.default_configs["moderate"]
        else:
            config = self.default_configs["loose"]
        
        # Build query based on type and analysis
        if match_type == FuzzyMatchType.SINGLE_TERM and query_analysis["word_count"] == 1:
            return self.build_single_term_fuzzy_query(query_text, "_all", config)
        elif match_type == FuzzyMatchType.PHRASE or query_analysis["is_phrase"]:
            return self.build_fuzzy_phrase_query(query_text, fields, config=config)
        elif match_type == FuzzyMatchType.CROSS_FIELD:
            return self.build_cross_field_fuzzy_query(query_text, fields, config)
        else:
            terms = self._tokenize_phrase(query_text)
            return self.build_multi_term_fuzzy_query(terms, fields, config)
    
    def build_fuzzy_suggestion_query(
        self, 
        text: str, 
        field: str = "_all",
        size: int = 5,
        config: Optional[FuzzyConfig] = None
    ) -> Dict[str, Any]:
        """Build a fuzzy query for search suggestions"""
        if config is None:
            config = self.default_configs["moderate"]
        
        return {
            "suggest": {
                "text": text,
                "fuzzy_suggest": {
                    "term": {
                        "field": field,
                        "size": size,
                        "sort": "score",
                        "suggest_mode": "popular",
                        "string_distance": "internal",
                        "max_edits": 2,
                        "max_inspections": 5,
                        "max_term_freq": 0.01,
                        "prefix_length": config.prefix_length,
                        "min_word_length": 2,
                        "min_doc_freq": 0.01
                    }
                }
            }
        }
    
    def _analyze_query(self, query_text: str) -> Dict[str, Any]:
        """Analyze query text to determine optimal fuzzy strategy"""
        terms = self._tokenize_phrase(query_text)
        
        # Check for technical terms (file extensions, technical patterns)
        technical_patterns = [
            r'\.(mp4|avi|mov|mkv|wmv|flv|webm|m4v)',  # Video extensions
            r'\.(jpg|jpeg|png|gif|bmp|tiff|svg|webp)',  # Image extensions
            r'\.(mp3|wav|flac|aac|ogg|wma|m4a)',  # Audio extensions
            r'\.(pdf|doc|docx|xls|xlsx|ppt|pptx)',  # Document extensions
            r'\b\d+[kK]\b',  # Resolution (4K, 1080p, etc.)
            r'\b\d+p\b',  # Resolution
            r'\b\d+fps\b',  # Frame rate
            r'\bHD\b|\bFHD\b|\bUHD\b',  # Video quality
        ]
        
        contains_technical = any(
            re.search(pattern, query_text, re.IGNORECASE) 
            for pattern in technical_patterns
        )
        
        # Check if it's a phrase (quoted or natural phrase)
        is_phrase = (
            query_text.startswith('"') and query_text.endswith('"') or
            len(terms) > 1 and not any(
                word.lower() in ['and', 'or', 'not', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
                for word in terms
            )
        )
        
        return {
            "word_count": len(terms),
            "avg_word_length": sum(len(term) for term in terms) / len(terms) if terms else 0,
            "contains_technical_terms": contains_technical,
            "is_phrase": is_phrase,
            "has_special_chars": bool(re.search(r'[^\w\s]', query_text)),
            "terms": terms
        }
    
    def _tokenize_phrase(self, phrase: str) -> List[str]:
        """Tokenize phrase into terms"""
        # Remove quotes if present
        if phrase.startswith('"') and phrase.endswith('"'):
            phrase = phrase[1:-1]
        
        # Split on whitespace and filter out empty strings
        terms = [term.strip() for term in phrase.split() if term.strip()]
        return terms
    
    def get_fuzzy_config(self, config_name: str) -> FuzzyConfig:
        """Get a fuzzy configuration by name"""
        return self.default_configs.get(config_name, self.default_configs["moderate"])
    
    def estimate_fuzzy_performance(self, query: str, config: FuzzyConfig) -> Dict[str, Any]:
        """Estimate performance impact of fuzzy query"""
        terms = self._tokenize_phrase(query)
        
        # Estimate based on configuration and query complexity
        complexity_score = 0
        
        # Factor in number of terms
        complexity_score += len(terms) * 10
        
        # Factor in fuzziness level
        if config.fuzziness == FuzzinessType.DISTANCE_2:
            complexity_score += 50
        elif config.fuzziness == FuzzinessType.DISTANCE_3:
            complexity_score += 100
        elif config.fuzziness == FuzzinessType.AUTO:
            complexity_score += 30
        
        # Factor in max expansions
        complexity_score += config.max_expansions * 0.5
        
        # Factor in prefix length (lower = higher complexity)
        complexity_score += (3 - config.prefix_length) * 20
        
        return {
            "complexity_score": complexity_score,
            "estimated_time_ms": min(complexity_score * 2, 5000),  # Cap at 5 seconds
            "performance_impact": (
                "low" if complexity_score < 100 else
                "moderate" if complexity_score < 300 else
                "high"
            ),
            "recommendations": self._get_performance_recommendations(complexity_score)
        }
    
    def _get_performance_recommendations(self, complexity_score: int) -> List[str]:
        """Get performance optimization recommendations"""
        recommendations = []
        
        if complexity_score > 300:
            recommendations.append("Consider using stricter fuzziness settings")
            recommendations.append("Reduce max_expansions parameter")
            recommendations.append("Increase prefix_length for better performance")
        
        if complexity_score > 500:
            recommendations.append("Consider using wildcard or phrase queries instead")
            recommendations.append("Implement query caching for frequently used terms")
        
        return recommendations


async def get_fuzzy_search_service() -> FuzzySearchService:
    """Get fuzzy search service instance"""
    from ..db.opensearch import get_opensearch_client
    
    client = await get_opensearch_client()
    return FuzzySearchService(client)
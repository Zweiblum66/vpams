"""
Natural Language Processing Search Service

Provides natural language understanding capabilities for search queries,
including intent detection, entity extraction, and query enhancement.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import structlog
from dataclasses import dataclass
from enum import Enum

from ..models.schemas import SearchQuery, AdvancedSearchQuery, FilteredSearchQuery, SearchType
from ..core.exceptions import InvalidQueryError

logger = structlog.get_logger()


class QueryIntent(Enum):
    """Types of search intents"""
    FIND_BY_NAME = "find_by_name"
    FIND_BY_TYPE = "find_by_type"
    FIND_BY_DATE = "find_by_date"
    FIND_BY_PERSON = "find_by_person"
    FIND_BY_LOCATION = "find_by_location"
    FIND_BY_PROJECT = "find_by_project"
    FIND_BY_DURATION = "find_by_duration"
    FIND_BY_TECHNICAL = "find_by_technical"
    FIND_RECENT = "find_recent"
    FIND_SIMILAR = "find_similar"
    COMPLEX_QUERY = "complex_query"


@dataclass
class ParsedQuery:
    """Parsed natural language query with extracted components"""
    original_query: str
    intent: QueryIntent
    keywords: List[str]
    entities: Dict[str, Any]
    filters: Dict[str, Any]
    temporal_filters: Dict[str, Any]
    technical_filters: Dict[str, Any]
    modifiers: List[str]
    confidence: float


class NLPSearchService:
    """Service for natural language search processing"""
    
    def __init__(self):
        """Initialize NLP search service with patterns and rules"""
        self.temporal_patterns = self._compile_temporal_patterns()
        self.type_patterns = self._compile_type_patterns()
        self.technical_patterns = self._compile_technical_patterns()
        self.modifier_patterns = self._compile_modifier_patterns()
        self.entity_patterns = self._compile_entity_patterns()
    
    async def parse_natural_language_query(self, query: str) -> ParsedQuery:
        """
        Parse natural language query into structured components
        
        Args:
            query: Natural language search query
            
        Returns:
            ParsedQuery with extracted components
        """
        query_lower = query.lower().strip()
        
        # Detect intent
        intent = self._detect_intent(query_lower)
        
        # Extract entities and filters based on intent
        entities = self._extract_entities(query_lower)
        filters = self._extract_filters(query_lower)
        temporal_filters = self._extract_temporal_filters(query_lower)
        technical_filters = self._extract_technical_filters(query_lower)
        
        # Extract keywords (remaining after entity extraction)
        keywords = self._extract_keywords(query_lower, entities, filters)
        
        # Extract modifiers (latest, recent, old, etc.)
        modifiers = self._extract_modifiers(query_lower)
        
        # Calculate confidence score
        confidence = self._calculate_confidence(
            query_lower, intent, entities, filters, keywords
        )
        
        parsed = ParsedQuery(
            original_query=query,
            intent=intent,
            keywords=keywords,
            entities=entities,
            filters=filters,
            temporal_filters=temporal_filters,
            technical_filters=technical_filters,
            modifiers=modifiers,
            confidence=confidence
        )
        
        logger.info(
            "parsed_natural_language_query",
            query=query,
            intent=intent.value,
            entity_count=len(entities),
            filter_count=len(filters),
            keyword_count=len(keywords),
            confidence=confidence
        )
        
        return parsed
    
    async def convert_to_search_query(self, parsed: ParsedQuery) -> FilteredSearchQuery:
        """
        Convert parsed natural language query to structured search query
        
        Args:
            parsed: Parsed natural language query
            
        Returns:
            FilteredSearchQuery ready for execution
        """
        # Build base query from keywords
        query_text = " ".join(parsed.keywords) if parsed.keywords else parsed.original_query
        
        # Determine search type based on intent and modifiers
        search_type = self._determine_search_type(parsed)
        
        # Build filters
        filters = []
        
        # Add entity-based filters
        if parsed.entities:
            filters.extend(self._build_entity_filters(parsed.entities))
        
        # Add explicit filters
        if parsed.filters:
            filters.extend(self._build_explicit_filters(parsed.filters))
        
        # Add temporal filters
        if parsed.temporal_filters:
            filters.extend(self._build_temporal_filters(parsed.temporal_filters))
        
        # Add technical filters
        if parsed.technical_filters:
            filters.extend(self._build_technical_filters(parsed.technical_filters))
        
        # Build facets based on intent
        facets = self._build_facets_for_intent(parsed.intent)
        
        # Apply modifiers
        sort_by, sort_order = self._apply_modifiers(parsed.modifiers)
        
        return FilteredSearchQuery(
            query=query_text,
            search_type=search_type,
            filters=filters,
            facets=facets,
            sort_by=sort_by,
            sort_order=sort_order,
            size=20,
            from_=0,
            highlight=True,
            include_source=True
        )
    
    def _detect_intent(self, query: str) -> QueryIntent:
        """Detect the primary intent of the query"""
        # Check for specific patterns
        if any(pattern in query for pattern in ["show me", "find", "search for", "looking for"]):
            if any(word in query for word in ["video", "image", "audio", "document", "file"]):
                return QueryIntent.FIND_BY_TYPE
            elif any(word in query for word in ["from", "by", "created by", "uploaded by"]):
                return QueryIntent.FIND_BY_PERSON
            elif any(word in query for word in ["yesterday", "today", "last week", "last month"]):
                return QueryIntent.FIND_BY_DATE
            elif any(word in query for word in ["project", "folder", "collection"]):
                return QueryIntent.FIND_BY_PROJECT
        
        # Check for temporal queries
        if any(word in query for word in ["recent", "latest", "newest", "oldest"]):
            return QueryIntent.FIND_RECENT
        
        # Check for duration queries
        if any(pattern in query for pattern in ["longer than", "shorter than", "duration", "minutes", "seconds"]):
            return QueryIntent.FIND_BY_DURATION
        
        # Check for technical queries
        if any(pattern in query for pattern in ["resolution", "fps", "bitrate", "format", "codec"]):
            return QueryIntent.FIND_BY_TECHNICAL
        
        # Check for similarity queries
        if any(pattern in query for pattern in ["similar to", "like", "same as"]):
            return QueryIntent.FIND_SIMILAR
        
        # Check if it's a complex query with multiple conditions
        if " and " in query or " or " in query or " not " in query:
            return QueryIntent.COMPLEX_QUERY
        
        # Default to name-based search
        return QueryIntent.FIND_BY_NAME
    
    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract named entities from the query"""
        entities = {}
        
        # Extract person names (simple pattern matching)
        person_patterns = [
            r"by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"from\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"created by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"uploaded by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
        ]
        
        for pattern in person_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                entities["person"] = match.group(1)
                break
        
        # Extract project/folder names
        project_patterns = [
            r"in project\s+[\"']?([^\"']+)[\"']?",
            r"from project\s+[\"']?([^\"']+)[\"']?",
            r"in folder\s+[\"']?([^\"']+)[\"']?",
            r"from folder\s+[\"']?([^\"']+)[\"']?"
        ]
        
        for pattern in project_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                entities["project"] = match.group(1).strip()
                break
        
        # Extract file types
        type_keywords = {
            "videos": "video",
            "images": "image",
            "photos": "image",
            "pictures": "image",
            "audio": "audio",
            "sounds": "audio",
            "documents": "document",
            "pdfs": "pdf",
            "spreadsheets": "spreadsheet"
        }
        
        for keyword, type_value in type_keywords.items():
            if keyword in query:
                entities["type"] = type_value
                break
        
        return entities
    
    def _extract_filters(self, query: str) -> Dict[str, Any]:
        """Extract explicit filters from the query"""
        filters = {}
        
        # Extract tag filters
        tag_pattern = r"tagged? (?:as |with )?[\"']?([^\"']+)[\"']?"
        tag_match = re.search(tag_pattern, query, re.IGNORECASE)
        if tag_match:
            filters["tags"] = [tag.strip() for tag in tag_match.group(1).split(",")]
        
        # Extract status filters
        if "published" in query:
            filters["status"] = "published"
        elif "draft" in query:
            filters["status"] = "draft"
        elif "archived" in query:
            filters["status"] = "archived"
        
        # Extract format filters
        format_patterns = {
            r"\b(mp4|mov|avi|mkv)\b": "video_format",
            r"\b(jpg|jpeg|png|gif|webp)\b": "image_format",
            r"\b(mp3|wav|aac|flac)\b": "audio_format",
            r"\b(pdf|doc|docx|txt)\b": "document_format"
        }
        
        for pattern, filter_type in format_patterns.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                filters[filter_type] = match.group(1).lower()
        
        return filters
    
    def _extract_temporal_filters(self, query: str) -> Dict[str, Any]:
        """Extract temporal filters from the query"""
        temporal = {}
        now = datetime.utcnow()
        
        # Relative date patterns
        relative_patterns = {
            "today": (now.replace(hour=0, minute=0, second=0), now),
            "yesterday": (
                (now - timedelta(days=1)).replace(hour=0, minute=0, second=0),
                (now - timedelta(days=1)).replace(hour=23, minute=59, second=59)
            ),
            "this week": (
                now - timedelta(days=now.weekday()),
                now
            ),
            "last week": (
                now - timedelta(days=now.weekday() + 7),
                now - timedelta(days=now.weekday())
            ),
            "this month": (
                now.replace(day=1, hour=0, minute=0, second=0),
                now
            ),
            "last month": (
                (now.replace(day=1) - timedelta(days=1)).replace(day=1),
                now.replace(day=1) - timedelta(seconds=1)
            )
        }
        
        for pattern, (start, end) in relative_patterns.items():
            if pattern in query:
                temporal["created_at"] = {
                    "gte": start.isoformat(),
                    "lte": end.isoformat()
                }
                break
        
        # "Last N days/weeks/months" patterns
        last_n_pattern = r"last (\d+) (days?|weeks?|months?)"
        match = re.search(last_n_pattern, query, re.IGNORECASE)
        if match:
            n = int(match.group(1))
            unit = match.group(2).rstrip('s')
            
            if unit == "day":
                start_date = now - timedelta(days=n)
            elif unit == "week":
                start_date = now - timedelta(weeks=n)
            elif unit == "month":
                start_date = now - timedelta(days=n * 30)  # Approximate
            
            temporal["created_at"] = {
                "gte": start_date.isoformat(),
                "lte": now.isoformat()
            }
        
        # Specific date patterns (simplified)
        date_pattern = r"on (\d{4}-\d{2}-\d{2})"
        match = re.search(date_pattern, query)
        if match:
            date_str = match.group(1)
            date = datetime.fromisoformat(date_str)
            temporal["created_at"] = {
                "gte": date.replace(hour=0, minute=0, second=0).isoformat(),
                "lte": date.replace(hour=23, minute=59, second=59).isoformat()
            }
        
        return temporal
    
    def _extract_technical_filters(self, query: str) -> Dict[str, Any]:
        """Extract technical specification filters"""
        technical = {}
        
        # Resolution patterns
        resolution_pattern = r"(\d+)p|(\d+)x(\d+)|([48]k|hd|fhd|uhd)"
        match = re.search(resolution_pattern, query, re.IGNORECASE)
        if match:
            if match.group(1):  # 1080p format
                height = int(match.group(1))
                technical["resolution_height"] = height
            elif match.group(2) and match.group(3):  # 1920x1080 format
                technical["resolution_width"] = int(match.group(2))
                technical["resolution_height"] = int(match.group(3))
            elif match.group(4):  # HD/4K format
                resolution_map = {
                    "hd": 720,
                    "fhd": 1080,
                    "4k": 2160,
                    "8k": 4320,
                    "uhd": 2160
                }
                res_key = match.group(4).lower()
                if res_key in resolution_map:
                    technical["resolution_height"] = resolution_map[res_key]
        
        # Frame rate patterns
        fps_pattern = r"(\d+)\s*fps|(\d+)\s*frames? per second"
        match = re.search(fps_pattern, query, re.IGNORECASE)
        if match:
            fps = int(match.group(1) or match.group(2))
            technical["frame_rate"] = fps
        
        # Duration patterns
        duration_patterns = [
            (r"longer than (\d+) (minutes?|mins?)", "gt"),
            (r"shorter than (\d+) (minutes?|mins?)", "lt"),
            (r"(\d+) (minutes?|mins?) long", "eq"),
            (r"between (\d+) and (\d+) (minutes?|mins?)", "between")
        ]
        
        for pattern, op in duration_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                if op == "between":
                    min_duration = int(match.group(1)) * 60
                    max_duration = int(match.group(2)) * 60
                    technical["duration"] = {
                        "gte": min_duration,
                        "lte": max_duration
                    }
                else:
                    duration = int(match.group(1)) * 60  # Convert to seconds
                    if op == "gt":
                        technical["duration"] = {"gt": duration}
                    elif op == "lt":
                        technical["duration"] = {"lt": duration}
                    elif op == "eq":
                        technical["duration"] = {
                            "gte": duration - 30,  # Allow 30 seconds tolerance
                            "lte": duration + 30
                        }
                break
        
        # File size patterns
        size_pattern = r"(larger|smaller|bigger) than (\d+)\s*(mb|gb|kb)"
        match = re.search(size_pattern, query, re.IGNORECASE)
        if match:
            op = "gt" if match.group(1) in ["larger", "bigger"] else "lt"
            size = int(match.group(2))
            unit = match.group(3).lower()
            
            # Convert to bytes
            multipliers = {"kb": 1024, "mb": 1024*1024, "gb": 1024*1024*1024}
            size_bytes = size * multipliers.get(unit, 1)
            
            technical["file_size"] = {op: size_bytes}
        
        return technical
    
    def _extract_keywords(
        self, 
        query: str, 
        entities: Dict[str, Any], 
        filters: Dict[str, Any]
    ) -> List[str]:
        """Extract keywords after removing entities and filter terms"""
        # Remove common search phrases
        query = re.sub(
            r"\b(show me|find|search for|looking for|get me|i need|i want)\b",
            "", 
            query, 
            flags=re.IGNORECASE
        )
        
        # Remove extracted entities
        if "person" in entities:
            query = query.replace(entities["person"].lower(), "")
        if "project" in entities:
            query = query.replace(entities["project"].lower(), "")
        
        # Remove filter-related terms
        filter_terms = [
            "videos?", "images?", "photos?", "pictures?", "audio", "documents?",
            "tagged?", "with", "as", "in project", "from project", "in folder",
            "from folder", "by", "from", "created by", "uploaded by",
            "today", "yesterday", "this week", "last week", "this month", "last month",
            "recent", "latest", "newest", "oldest", "published", "draft", "archived",
            "longer than", "shorter than", "minutes?", "seconds?", "fps", "frames? per second"
        ]
        
        for term in filter_terms:
            query = re.sub(rf"\b{term}\b", "", query, flags=re.IGNORECASE)
        
        # Remove format extensions
        query = re.sub(r"\b(mp4|mov|avi|jpg|jpeg|png|mp3|wav|pdf|doc)\b", "", query, re.IGNORECASE)
        
        # Remove technical terms that were extracted
        query = re.sub(r"\b(\d+p|\d+x\d+|4k|hd|uhd|fhd)\b", "", query, re.IGNORECASE)
        
        # Clean up and split into keywords
        query = re.sub(r"\s+", " ", query).strip()
        keywords = [word for word in query.split() if len(word) > 2]
        
        return keywords
    
    def _extract_modifiers(self, query: str) -> List[str]:
        """Extract query modifiers"""
        modifiers = []
        
        modifier_keywords = {
            "recent": "recent",
            "latest": "latest",
            "newest": "newest",
            "oldest": "oldest",
            "popular": "popular",
            "most viewed": "most_viewed",
            "most downloaded": "most_downloaded",
            "high quality": "high_quality",
            "low quality": "low_quality"
        }
        
        for keyword, modifier in modifier_keywords.items():
            if keyword in query:
                modifiers.append(modifier)
        
        return modifiers
    
    def _calculate_confidence(
        self,
        query: str,
        intent: QueryIntent,
        entities: Dict[str, Any],
        filters: Dict[str, Any],
        keywords: List[str]
    ) -> float:
        """Calculate confidence score for the parsed query"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence for recognized intent
        if intent != QueryIntent.COMPLEX_QUERY:
            confidence += 0.2
        
        # Increase confidence for extracted entities
        confidence += min(0.2, len(entities) * 0.05)
        
        # Increase confidence for filters
        confidence += min(0.2, len(filters) * 0.05)
        
        # Decrease confidence if no keywords remain
        if not keywords and not entities and not filters:
            confidence -= 0.3
        
        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, confidence))
    
    def _determine_search_type(self, parsed: ParsedQuery) -> SearchType:
        """Determine the appropriate search type"""
        # Use phrase search for queries with quotes
        if '"' in parsed.original_query:
            return SearchType.PHRASE
        
        # Use fuzzy search for name-based queries
        if parsed.intent == QueryIntent.FIND_BY_NAME:
            return SearchType.FUZZY
        
        # Use wildcard for partial matches
        if "*" in parsed.original_query or "?" in parsed.original_query:
            return SearchType.WILDCARD
        
        # Default to basic search
        return SearchType.BASIC
    
    def _build_entity_filters(self, entities: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build filters from extracted entities"""
        filters = []
        
        if "type" in entities:
            filters.append({
                "field": "asset_type",
                "operator": "equals",
                "value": entities["type"]
            })
        
        if "person" in entities:
            filters.append({
                "field": "creator",
                "operator": "contains",
                "value": entities["person"]
            })
        
        if "project" in entities:
            filters.append({
                "field": "project_name",
                "operator": "contains",
                "value": entities["project"]
            })
        
        return filters
    
    def _build_explicit_filters(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build filters from explicit filter values"""
        filter_list = []
        
        for field, value in filters.items():
            if isinstance(value, list):
                filter_list.append({
                    "field": field,
                    "operator": "in",
                    "value": value
                })
            else:
                filter_list.append({
                    "field": field,
                    "operator": "equals",
                    "value": value
                })
        
        return filter_list
    
    def _build_temporal_filters(self, temporal: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build temporal filters"""
        filters = []
        
        for field, value in temporal.items():
            if isinstance(value, dict) and "gte" in value and "lte" in value:
                filters.append({
                    "field": field,
                    "operator": "range",
                    "value": value
                })
        
        return filters
    
    def _build_technical_filters(self, technical: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build technical specification filters"""
        filters = []
        
        for field, value in technical.items():
            if isinstance(value, dict):
                # Range filter
                filters.append({
                    "field": field,
                    "operator": "range",
                    "value": value
                })
            else:
                # Exact match
                filters.append({
                    "field": field,
                    "operator": "equals",
                    "value": value
                })
        
        return filters
    
    def _build_facets_for_intent(self, intent: QueryIntent) -> List[Dict[str, Any]]:
        """Build appropriate facets based on query intent"""
        base_facets = [
            {"field": "asset_type", "size": 10},
            {"field": "status", "size": 5}
        ]
        
        intent_facets = {
            QueryIntent.FIND_BY_TYPE: [
                {"field": "file_extension", "size": 20},
                {"field": "mime_type", "size": 10}
            ],
            QueryIntent.FIND_BY_PERSON: [
                {"field": "creator", "size": 20},
                {"field": "owner", "size": 20}
            ],
            QueryIntent.FIND_BY_PROJECT: [
                {"field": "project_name", "size": 20},
                {"field": "folder_path", "size": 20}
            ],
            QueryIntent.FIND_BY_DATE: [
                {
                    "field": "created_at",
                    "type": "date_histogram",
                    "interval": "month"
                }
            ],
            QueryIntent.FIND_BY_TECHNICAL: [
                {"field": "resolution_height", "size": 10},
                {"field": "frame_rate", "size": 10},
                {"field": "codec", "size": 10}
            ]
        }
        
        # Combine base facets with intent-specific facets
        facets = base_facets.copy()
        if intent in intent_facets:
            facets.extend(intent_facets[intent])
        
        return facets
    
    def _apply_modifiers(self, modifiers: List[str]) -> Tuple[Optional[str], str]:
        """Apply modifiers to determine sort order"""
        if "latest" in modifiers or "newest" in modifiers or "recent" in modifiers:
            return "created_at", "desc"
        elif "oldest" in modifiers:
            return "created_at", "asc"
        elif "popular" in modifiers or "most_viewed" in modifiers:
            return "view_count", "desc"
        elif "most_downloaded" in modifiers:
            return "download_count", "desc"
        elif "high_quality" in modifiers:
            return "quality_score", "desc"
        elif "low_quality" in modifiers:
            return "quality_score", "asc"
        
        # Default: sort by relevance (no explicit sort)
        return None, "desc"
    
    def _compile_temporal_patterns(self) -> Dict[str, re.Pattern]:
        """Compile temporal regex patterns"""
        return {
            "relative_date": re.compile(
                r"\b(today|yesterday|tomorrow|this week|last week|this month|last month)\b",
                re.IGNORECASE
            ),
            "last_n": re.compile(
                r"\blast (\d+) (days?|weeks?|months?|years?)\b",
                re.IGNORECASE
            ),
            "specific_date": re.compile(
                r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b"
            )
        }
    
    def _compile_type_patterns(self) -> Dict[str, re.Pattern]:
        """Compile media type patterns"""
        return {
            "video": re.compile(r"\b(videos?|movies?|clips?|footage)\b", re.IGNORECASE),
            "image": re.compile(r"\b(images?|photos?|pictures?|graphics?)\b", re.IGNORECASE),
            "audio": re.compile(r"\b(audio|sounds?|music|tracks?)\b", re.IGNORECASE),
            "document": re.compile(r"\b(documents?|files?|pdfs?|texts?)\b", re.IGNORECASE)
        }
    
    def _compile_technical_patterns(self) -> Dict[str, re.Pattern]:
        """Compile technical specification patterns"""
        return {
            "resolution": re.compile(
                r"\b(\d+p|\d+x\d+|4k|8k|hd|fhd|uhd)\b",
                re.IGNORECASE
            ),
            "fps": re.compile(
                r"\b(\d+)\s*(fps|frames?\s*per\s*second)\b",
                re.IGNORECASE
            ),
            "duration": re.compile(
                r"\b(longer|shorter)\s+than\s+(\d+)\s*(minutes?|mins?|seconds?|secs?)\b",
                re.IGNORECASE
            ),
            "size": re.compile(
                r"\b(larger|smaller|bigger)\s+than\s+(\d+)\s*(mb|gb|kb)\b",
                re.IGNORECASE
            )
        }
    
    def _compile_modifier_patterns(self) -> Dict[str, re.Pattern]:
        """Compile query modifier patterns"""
        return {
            "sort": re.compile(
                r"\b(recent|latest|newest|oldest|popular|most viewed|most downloaded)\b",
                re.IGNORECASE
            ),
            "quality": re.compile(
                r"\b(high quality|low quality|best quality)\b",
                re.IGNORECASE
            )
        }
    
    def _compile_entity_patterns(self) -> Dict[str, re.Pattern]:
        """Compile entity extraction patterns"""
        return {
            "person": re.compile(
                r"\b(?:by|from|created by|uploaded by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                re.IGNORECASE
            ),
            "project": re.compile(
                r"\b(?:in|from)\s+(?:project|folder)\s+[\"']?([^\"']+)[\"']?",
                re.IGNORECASE
            ),
            "tag": re.compile(
                r"\btagged?\s+(?:as|with)?\s+[\"']?([^\"']+)[\"']?",
                re.IGNORECASE
            )
        }


# Singleton instance
_nlp_service = None


async def get_nlp_search_service() -> NLPSearchService:
    """Get NLP search service instance"""
    global _nlp_service
    if _nlp_service is None:
        _nlp_service = NLPSearchService()
    return _nlp_service
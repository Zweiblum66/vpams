"""
Suggestion Service - Search suggestions and auto-completion
"""

import structlog
from typing import List, Dict, Any
import time
from opensearchpy import AsyncOpenSearch
from opensearchpy.exceptions import RequestError, OpenSearchException

from ..models.schemas import (
    SuggestionQuery, 
    SuggestionResponse, 
    SuggestionItem,
    IndexType
)
from ..db.opensearch import get_opensearch_client
from ..core.exceptions import SearchError

logger = structlog.get_logger()


class SuggestionService:
    """Service for handling search suggestions"""
    
    def __init__(self, opensearch_client: AsyncOpenSearch):
        self.client = opensearch_client
        self.index_mappings = {
            IndexType.ASSETS: "mams_assets",
            IndexType.METADATA: "mams_metadata",
            IndexType.PROJECTS: "mams_projects",
            IndexType.ANALYTICS: "mams_analytics",
            IndexType.ALL: "mams_*"
        }
    
    async def get_suggestions(self, query: SuggestionQuery) -> SuggestionResponse:
        """
        Get search suggestions using OpenSearch completion suggester
        
        Args:
            query: Suggestion query parameters
            
        Returns:
            SuggestionResponse with suggestions
        """
        start_time = time.time()
        
        try:
            # Determine which index to search
            index_name = self.index_mappings.get(query.index_type, self.index_mappings[IndexType.ALL])
            
            # Build suggestion query
            suggestion_query = self._build_suggestion_query(query)
            
            # Execute suggestion search
            response = await self.client.search(
                index=index_name,
                body=suggestion_query,
                size=0  # We don't need regular search results
            )
            
            # Parse suggestions from response
            suggestions = self._parse_suggestions(response, query.text)
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            return SuggestionResponse(
                suggestions=suggestions[:query.size],
                took=elapsed_ms
            )
            
        except RequestError as e:
            logger.error("opensearch_request_error", error=str(e), query=query.text)
            raise SearchError(f"Invalid suggestion request: {str(e)}")
        except OpenSearchException as e:
            logger.error("opensearch_error", error=str(e), query=query.text)
            raise SearchError(f"OpenSearch error: {str(e)}")
        except Exception as e:
            logger.error("suggestion_error", error=str(e), query=query.text)
            raise SearchError(f"Failed to get suggestions: {str(e)}")
    
    def _build_suggestion_query(self, query: SuggestionQuery) -> Dict[str, Any]:
        """
        Build OpenSearch suggestion query
        
        Args:
            query: Suggestion query parameters
            
        Returns:
            OpenSearch suggestion query body
        """
        # Use multi-field suggestion for better results
        suggestion_query = {
            "suggest": {
                # Completion suggester for name field
                "name_suggest": {
                    "text": query.text,
                    "completion": {
                        "field": "name.suggest",
                        "size": query.size * 2,  # Get more to filter duplicates
                        "skip_duplicates": True,
                        "fuzzy": {
                            "fuzziness": "AUTO",
                            "transpositions": True,
                            "min_length": 3
                        }
                    }
                }
            }
        }
        
        # Add phrase suggester for better multi-word suggestions
        if len(query.text.split()) > 1:
            suggestion_query["suggest"]["phrase_suggest"] = {
                "text": query.text,
                "phrase": {
                    "field": "name",
                    "size": query.size,
                    "gram_size": 2,
                    "direct_generator": [{
                        "field": "name",
                        "suggest_mode": "popular",
                        "min_word_length": 3
                    }],
                    "highlight": {
                        "pre_tag": "<em>",
                        "post_tag": "</em>"
                    }
                }
            }
        
        # Add term suggester for simple typo corrections
        suggestion_query["suggest"]["term_suggest"] = {
            "text": query.text,
            "term": {
                "field": "name",
                "size": query.size,
                "sort": "score",
                "suggest_mode": "popular",
                "min_word_length": 3,
                "prefix_length": 2
            }
        }
        
        return suggestion_query
    
    def _parse_suggestions(self, response: Dict[str, Any], original_text: str) -> List[SuggestionItem]:
        """
        Parse suggestions from OpenSearch response
        
        Args:
            response: OpenSearch response
            original_text: Original query text
            
        Returns:
            List of suggestion items
        """
        suggestions = []
        seen_texts = set()
        
        # Parse completion suggestions
        if "suggest" in response:
            # Completion suggestions (highest priority)
            if "name_suggest" in response["suggest"]:
                for suggestion in response["suggest"]["name_suggest"][0].get("options", []):
                    text = suggestion.get("text", "")
                    if text and text.lower() != original_text.lower() and text not in seen_texts:
                        suggestions.append(SuggestionItem(
                            text=text,
                            score=suggestion.get("score", 0.0) * 2.0  # Boost completion suggestions
                        ))
                        seen_texts.add(text)
            
            # Phrase suggestions (for multi-word queries)
            if "phrase_suggest" in response["suggest"]:
                for suggestion in response["suggest"]["phrase_suggest"][0].get("options", []):
                    text = suggestion.get("text", "")
                    if text and text.lower() != original_text.lower() and text not in seen_texts:
                        suggestions.append(SuggestionItem(
                            text=text,
                            score=suggestion.get("score", 0.0) * 1.5  # Medium boost
                        ))
                        seen_texts.add(text)
            
            # Term suggestions (for typo corrections)
            if "term_suggest" in response["suggest"]:
                for term_suggestion in response["suggest"]["term_suggest"]:
                    for option in term_suggestion.get("options", []):
                        text = option.get("text", "")
                        if text and text.lower() != original_text.lower() and text not in seen_texts:
                            suggestions.append(SuggestionItem(
                                text=text,
                                score=option.get("score", 0.0)
                            ))
                            seen_texts.add(text)
        
        # Sort by score descending
        suggestions.sort(key=lambda x: x.score, reverse=True)
        
        return suggestions
    
    async def update_suggestion_data(self, asset_id: str, name: str) -> None:
        """
        Update suggestion data when an asset is added or modified
        
        Args:
            asset_id: Asset ID
            name: Asset name to index for suggestions
        """
        try:
            # Update the asset document with completion field
            await self.client.update(
                index="mams_assets",
                id=asset_id,
                body={
                    "doc": {
                        "name.suggest": {
                            "input": [name] + name.split(),  # Index full name and individual words
                            "weight": 1  # Can be adjusted based on popularity
                        }
                    }
                }
            )
        except Exception as e:
            logger.error("update_suggestion_error", error=str(e), asset_id=asset_id)
            # Don't raise - this is a non-critical operation
    
    async def get_popular_searches(self, size: int = 10) -> List[str]:
        """
        Get popular search terms based on analytics
        
        Args:
            size: Number of popular searches to return
            
        Returns:
            List of popular search terms
        """
        try:
            # Query analytics index for popular searches
            response = await self.client.search(
                index="mams_analytics",
                body={
                    "size": 0,
                    "aggs": {
                        "popular_searches": {
                            "terms": {
                                "field": "search_query.keyword",
                                "size": size,
                                "order": {"_count": "desc"}
                            }
                        }
                    }
                }
            )
            
            # Extract popular search terms
            popular_terms = []
            if "aggregations" in response:
                for bucket in response["aggregations"]["popular_searches"]["buckets"]:
                    popular_terms.append(bucket["key"])
            
            return popular_terms
            
        except Exception as e:
            logger.error("popular_searches_error", error=str(e))
            return []


async def get_suggestion_service() -> SuggestionService:
    """Get suggestion service instance"""
    client = await get_opensearch_client()
    return SuggestionService(client)
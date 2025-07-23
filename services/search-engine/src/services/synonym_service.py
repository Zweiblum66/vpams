"""
Synonym Service for the Search Engine

This service provides synonym expansion capabilities for search queries,
supporting multiple synonym sources including WordNet, custom dictionaries,
and domain-specific synonyms.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from functools import lru_cache
import re
import json
from datetime import datetime, timedelta

try:
    import nltk
    from nltk.corpus import wordnet as wn
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    from nltk.stem import WordNetLemmatizer
    from nltk.tag import pos_tag
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    logging.warning("NLTK not available. WordNet synonyms will be disabled.")

from ..models.schemas import (
    SynonymType, SynonymExpansionStrategy, SynonymConfig, SynonymSearchQuery,
    SynonymSearchResponse, SynonymExpansion, SynonymAnalysis, SynonymSuggestionQuery,
    SynonymSuggestionResponse, SynonymSuggestion, SynonymStats, SearchHit
)
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SynonymExpander:
    """Core synonym expansion engine"""
    
    def __init__(self):
        self.lemmatizer = None
        self.stopwords_set = set()
        self.custom_synonyms = {}
        self.domain_synonyms = {}
        self.synonym_cache = {}
        self.cache_ttl = 3600  # 1 hour
        
        # Initialize NLTK components if available
        if NLTK_AVAILABLE:
            try:
                self.lemmatizer = WordNetLemmatizer()
                self.stopwords_set = set(stopwords.words('english'))
                self._download_nltk_data()
            except Exception as e:
                logger.warning(f"Failed to initialize NLTK components: {e}")
                NLTK_AVAILABLE = False
    
    def _download_nltk_data(self):
        """Download required NLTK data"""
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        
        try:
            nltk.data.find('corpora/wordnet')
        except LookupError:
            nltk.download('wordnet')
        
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
        
        try:
            nltk.data.find('taggers/averaged_perceptron_tagger')
        except LookupError:
            nltk.download('averaged_perceptron_tagger')
    
    def _get_wordnet_pos(self, treebank_tag: str) -> str:
        """Convert treebank POS tag to WordNet POS tag"""
        if treebank_tag.startswith('J'):
            return wn.ADJ
        elif treebank_tag.startswith('V'):
            return wn.VERB
        elif treebank_tag.startswith('N'):
            return wn.NOUN
        elif treebank_tag.startswith('R'):
            return wn.ADV
        else:
            return wn.NOUN  # Default to noun
    
    def _clean_token(self, token: str) -> str:
        """Clean and normalize a token"""
        # Remove punctuation and convert to lowercase
        cleaned = re.sub(r'[^\w\s]', '', token.lower())
        return cleaned.strip()
    
    def _is_valid_token(self, token: str) -> bool:
        """Check if token is valid for synonym expansion"""
        if not token or len(token) < 2:
            return False
        if token in self.stopwords_set:
            return False
        if token.isdigit():
            return False
        return True
    
    def _get_cache_key(self, term: str, synonym_type: SynonymType, domain: str = None) -> str:
        """Generate cache key for synonym lookup"""
        return f"{term}:{synonym_type.value}:{domain or 'default'}"
    
    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid"""
        return time.time() - cache_entry.get('timestamp', 0) < self.cache_ttl
    
    def _get_cached_synonyms(self, term: str, synonym_type: SynonymType, domain: str = None) -> Optional[List[str]]:
        """Get synonyms from cache if available and valid"""
        cache_key = self._get_cache_key(term, synonym_type, domain)
        cache_entry = self.synonym_cache.get(cache_key)
        
        if cache_entry and self._is_cache_valid(cache_entry):
            return cache_entry['synonyms']
        
        return None
    
    def _cache_synonyms(self, term: str, synonym_type: SynonymType, synonyms: List[str], domain: str = None):
        """Cache synonyms for future use"""
        cache_key = self._get_cache_key(term, synonym_type, domain)
        self.synonym_cache[cache_key] = {
            'synonyms': synonyms,
            'timestamp': time.time()
        }
    
    def _get_wordnet_synonyms(self, term: str, pos_tag: str = None, max_synonyms: int = 5) -> List[str]:
        """Get synonyms from WordNet"""
        if not NLTK_AVAILABLE:
            return []
        
        try:
            synonyms = set()
            
            # Get synsets for the term
            if pos_tag:
                wordnet_pos = self._get_wordnet_pos(pos_tag)
                synsets = wn.synsets(term, pos=wordnet_pos)
            else:
                synsets = wn.synsets(term)
            
            # Extract synonyms from synsets
            for synset in synsets[:3]:  # Limit to first 3 synsets
                for lemma in synset.lemmas():
                    lemma_name = lemma.name().replace('_', ' ')
                    if lemma_name.lower() != term.lower():
                        synonyms.add(lemma_name)
                        if len(synonyms) >= max_synonyms:
                            break
                
                if len(synonyms) >= max_synonyms:
                    break
            
            return list(synonyms)
            
        except Exception as e:
            logger.error(f"Error getting WordNet synonyms for '{term}': {e}")
            return []
    
    def _get_custom_synonyms(self, term: str, custom_dict: Dict[str, List[str]]) -> List[str]:
        """Get synonyms from custom dictionary"""
        synonyms = []
        
        # Direct lookup
        if term in custom_dict:
            synonyms.extend(custom_dict[term])
        
        # Case-insensitive lookup
        for key, values in custom_dict.items():
            if key.lower() == term.lower():
                synonyms.extend(values)
                break
        
        return synonyms
    
    def _get_domain_synonyms(self, term: str, domain: str) -> List[str]:
        """Get domain-specific synonyms"""
        if domain not in self.domain_synonyms:
            self._load_domain_synonyms(domain)
        
        domain_dict = self.domain_synonyms.get(domain, {})
        return self._get_custom_synonyms(term, domain_dict)
    
    def _load_domain_synonyms(self, domain: str):
        """Load domain-specific synonym dictionary"""
        # This would load from a file or database in a real implementation
        # For now, we'll use some predefined domain synonyms
        
        domain_mappings = {
            'media': {
                'video': ['movie', 'film', 'clip', 'footage', 'recording'],
                'audio': ['sound', 'music', 'voice', 'recording', 'track'],
                'image': ['photo', 'picture', 'graphic', 'visual', 'artwork'],
                'document': ['file', 'text', 'paper', 'report', 'manuscript'],
                'edit': ['modify', 'change', 'revise', 'update', 'adjust'],
                'project': ['work', 'task', 'assignment', 'job', 'production'],
                'quality': ['resolution', 'definition', 'clarity', 'standard'],
                'format': ['type', 'extension', 'codec', 'encoding']
            },
            'broadcast': {
                'news': ['report', 'story', 'bulletin', 'update', 'coverage'],
                'live': ['broadcast', 'streaming', 'real-time', 'current'],
                'archive': ['library', 'storage', 'repository', 'collection'],
                'segment': ['clip', 'piece', 'portion', 'section', 'part'],
                'interview': ['conversation', 'discussion', 'talk', 'chat'],
                'breaking': ['urgent', 'immediate', 'developing', 'latest']
            },
            'production': {
                'shot': ['take', 'scene', 'capture', 'frame', 'angle'],
                'cut': ['edit', 'trim', 'splice', 'transition'],
                'render': ['export', 'output', 'generate', 'produce'],
                'timeline': ['sequence', 'track', 'arrangement', 'order'],
                'effect': ['filter', 'transition', 'enhancement', 'treatment'],
                'color': ['grade', 'correction', 'balance', 'tone']
            }
        }
        
        self.domain_synonyms[domain] = domain_mappings.get(domain, {})
    
    def get_synonyms(self, term: str, synonym_type: SynonymType, config: SynonymConfig) -> Tuple[List[str], str]:
        """Get synonyms for a term based on type and configuration"""
        term_clean = self._clean_token(term)
        
        if not self._is_valid_token(term_clean):
            return [], "invalid_token"
        
        # Check cache first
        if config.enable_caching:
            cached_synonyms = self._get_cached_synonyms(term_clean, synonym_type, config.domain_context)
            if cached_synonyms is not None:
                return cached_synonyms, "cache"
        
        synonyms = []
        source = "none"
        
        try:
            if synonym_type == SynonymType.WORDNET:
                synonyms = self._get_wordnet_synonyms(term_clean, max_synonyms=config.max_synonyms_per_term)
                source = "wordnet"
                
            elif synonym_type == SynonymType.CUSTOM:
                if config.custom_synonyms:
                    synonyms = self._get_custom_synonyms(term_clean, config.custom_synonyms)
                    source = "custom"
                    
            elif synonym_type == SynonymType.CONTEXTUAL:
                if config.domain_context:
                    synonyms = self._get_domain_synonyms(term_clean, config.domain_context)
                    source = "domain"
                    
            elif synonym_type == SynonymType.EXPLICIT:
                # Use predefined explicit synonyms
                synonyms = self._get_explicit_synonyms(term_clean)
                source = "explicit"
                
            elif synonym_type == SynonymType.HYBRID:
                # Combine multiple sources
                all_synonyms = []
                
                # WordNet synonyms
                if NLTK_AVAILABLE:
                    wn_synonyms = self._get_wordnet_synonyms(term_clean, max_synonyms=3)
                    all_synonyms.extend(wn_synonyms)
                
                # Custom synonyms
                if config.custom_synonyms:
                    custom_synonyms = self._get_custom_synonyms(term_clean, config.custom_synonyms)
                    all_synonyms.extend(custom_synonyms)
                
                # Domain synonyms
                if config.domain_context:
                    domain_synonyms = self._get_domain_synonyms(term_clean, config.domain_context)
                    all_synonyms.extend(domain_synonyms)
                
                # Remove duplicates and limit
                synonyms = list(set(all_synonyms))[:config.max_synonyms_per_term]
                source = "hybrid"
            
            # Filter by similarity threshold if needed
            if config.min_similarity_threshold > 0:
                synonyms = self._filter_by_similarity(term_clean, synonyms, config.min_similarity_threshold)
            
            # Cache the results
            if config.enable_caching:
                self._cache_synonyms(term_clean, synonym_type, synonyms, config.domain_context)
            
            return synonyms, source
            
        except Exception as e:
            logger.error(f"Error getting synonyms for '{term}': {e}")
            return [], "error"
    
    def _get_explicit_synonyms(self, term: str) -> List[str]:
        """Get explicit synonyms from predefined lists"""
        explicit_synonyms = {
            'video': ['movie', 'film', 'clip', 'footage'],
            'audio': ['sound', 'music', 'voice', 'recording'],
            'image': ['photo', 'picture', 'graphic', 'visual'],
            'document': ['file', 'text', 'paper', 'report'],
            'big': ['large', 'huge', 'massive', 'enormous'],
            'small': ['little', 'tiny', 'minor', 'compact'],
            'fast': ['quick', 'rapid', 'swift', 'speedy'],
            'slow': ['sluggish', 'gradual', 'delayed', 'leisurely'],
            'good': ['excellent', 'great', 'fine', 'quality'],
            'bad': ['poor', 'terrible', 'awful', 'defective'],
            'new': ['recent', 'fresh', 'latest', 'modern'],
            'old': ['ancient', 'vintage', 'dated', 'classic']
        }
        
        return explicit_synonyms.get(term.lower(), [])
    
    def _filter_by_similarity(self, original_term: str, synonyms: List[str], threshold: float) -> List[str]:
        """Filter synonyms by similarity threshold"""
        # Simple similarity based on character overlap
        # In a real implementation, you might use more sophisticated similarity measures
        filtered = []
        
        for synonym in synonyms:
            similarity = self._calculate_similarity(original_term, synonym)
            if similarity >= threshold:
                filtered.append(synonym)
        
        return filtered
    
    def _calculate_similarity(self, term1: str, term2: str) -> float:
        """Calculate similarity between two terms"""
        # Simple Jaccard similarity based on character bigrams
        def get_bigrams(word):
            return set(word[i:i+2] for i in range(len(word)-1))
        
        bigrams1 = get_bigrams(term1.lower())
        bigrams2 = get_bigrams(term2.lower())
        
        if not bigrams1 and not bigrams2:
            return 1.0
        if not bigrams1 or not bigrams2:
            return 0.0
        
        intersection = len(bigrams1 & bigrams2)
        union = len(bigrams1 | bigrams2)
        
        return intersection / union if union > 0 else 0.0
    
    def expand_query(self, query: str, config: SynonymConfig) -> Tuple[str, List[SynonymExpansion]]:
        """Expand a query with synonyms"""
        start_time = time.time()
        
        # Tokenize and tag the query
        tokens = word_tokenize(query.lower()) if NLTK_AVAILABLE else query.lower().split()
        pos_tags = pos_tag(tokens) if NLTK_AVAILABLE else [(token, None) for token in tokens]
        
        expansions = []
        expanded_terms = []
        
        for token, pos_tag in pos_tags:
            clean_token = self._clean_token(token)
            
            if not self._is_valid_token(clean_token):
                expanded_terms.append(token)
                continue
            
            # Get synonyms for this token
            synonyms, source = self.get_synonyms(clean_token, config.synonym_type, config)
            
            if synonyms:
                expansion = SynonymExpansion(
                    original_term=clean_token,
                    synonyms=synonyms,
                    synonym_type=config.synonym_type,
                    source=source,
                    pos_tag=pos_tag,
                    domain_context=config.domain_context
                )
                expansions.append(expansion)
                
                # Apply expansion strategy
                if config.expansion_strategy == SynonymExpansionStrategy.REPLACE:
                    # Replace with best synonym
                    expanded_terms.append(synonyms[0] if synonyms else token)
                elif config.expansion_strategy == SynonymExpansionStrategy.EXPAND:
                    # Add synonyms to the query
                    expanded_terms.append(f"({token} {' '.join(synonyms)})")
                elif config.expansion_strategy == SynonymExpansionStrategy.BOOST:
                    # Keep original with boosted synonyms
                    expanded_terms.append(f"{token}^{config.boost_original_terms}")
                    if synonyms:
                        boosted_synonyms = [f"{syn}^{config.boost_synonyms}" for syn in synonyms]
                        expanded_terms.extend(boosted_synonyms)
                else:  # FALLBACK
                    expanded_terms.append(token)
            else:
                expanded_terms.append(token)
        
        expanded_query = ' '.join(expanded_terms)
        expansion_time = int((time.time() - start_time) * 1000)
        
        return expanded_query, expansions


class SynonymService:
    """Service for synonym-based search operations"""
    
    def __init__(self, opensearch_client):
        self.opensearch_client = opensearch_client
        self.expander = SynonymExpander()
        self.settings = get_settings()
    
    async def synonym_search(self, query: SynonymSearchQuery) -> SynonymSearchResponse:
        """Perform synonym-enhanced search"""
        start_time = time.time()
        
        # Use default config if none provided
        config = query.synonym_config or SynonymConfig()
        
        # Expand the query with synonyms
        expanded_query, expansions = self.expander.expand_query(query.query, config)
        
        # Build the search request
        search_body = self._build_synonym_search_body(
            original_query=query.query,
            expanded_query=expanded_query,
            config=config,
            query_params=query
        )
        
        # Execute the search
        try:
            response = await self.opensearch_client.search(
                index=self._get_index_names(query.indices),
                body=search_body,
                timeout=f"{self.settings.SEARCH_TIMEOUT}s"
            )
            
            # Process results
            total_hits = response['hits']['total']['value']
            max_score = response['hits']['max_score']
            
            # Convert hits to SearchHit objects
            hits = []
            for hit in response['hits']['hits']:
                search_hit = SearchHit(
                    id=hit['_id'],
                    index=hit['_index'],
                    score=hit['_score'],
                    source=hit['_source'],
                    highlight=hit.get('highlight')
                )
                hits.append(search_hit)
            
            # Calculate result breakdown
            original_matches, synonym_matches, hybrid_matches = self._analyze_matches(hits, query.query, expansions)
            
            # Build synonym analysis if requested
            synonym_analysis = None
            if query.include_synonym_analysis:
                synonym_analysis = SynonymAnalysis(
                    original_query=query.query,
                    expanded_query=expanded_query,
                    term_expansions=expansions,
                    expansion_strategy=config.expansion_strategy,
                    total_synonyms_added=sum(len(exp.synonyms) for exp in expansions),
                    expansion_time_ms=int((time.time() - start_time) * 1000),
                    cache_hit_rate=self._calculate_cache_hit_rate(),
                    query_characteristics=self._analyze_query_characteristics(query.query)
                )
            
            took = int((time.time() - start_time) * 1000)
            per_page = query.size
            page = (query.from_ // per_page) + 1
            total_pages = (total_hits + per_page - 1) // per_page
            
            return SynonymSearchResponse(
                query=query.query,
                expanded_query=expanded_query,
                total_hits=total_hits,
                max_score=max_score,
                hits=hits,
                synonym_analysis=synonym_analysis,
                took=took,
                timed_out=response.get('timed_out', False),
                page=page,
                per_page=per_page,
                total_pages=total_pages,
                original_matches=original_matches,
                synonym_matches=synonym_matches,
                hybrid_matches=hybrid_matches
            )
            
        except Exception as e:
            logger.error(f"Error performing synonym search: {e}")
            raise
    
    def _build_synonym_search_body(self, original_query: str, expanded_query: str, config: SynonymConfig, query_params: SynonymSearchQuery) -> Dict:
        """Build the OpenSearch query body for synonym search"""
        search_body = {
            "query": {
                "bool": {
                    "should": []
                }
            },
            "size": query_params.size,
            "from": query_params.from_,
            "track_total_hits": True
        }
        
        # Add the expanded query
        if config.expansion_strategy == SynonymExpansionStrategy.BOOST:
            # Use multi_match with field boosts
            search_body["query"]["bool"]["should"].append({
                "multi_match": {
                    "query": expanded_query,
                    "fields": query_params.fields or ["*"],
                    "type": "best_fields",
                    "tie_breaker": 0.3
                }
            })
        else:
            # Use query_string for complex expansions
            search_body["query"]["bool"]["should"].append({
                "query_string": {
                    "query": expanded_query,
                    "fields": query_params.fields or ["*"],
                    "default_operator": "OR",
                    "boost": config.boost_synonyms
                }
            })
        
        # Add original query with higher boost if requested
        if query_params.include_original_query:
            search_body["query"]["bool"]["should"].append({
                "multi_match": {
                    "query": original_query,
                    "fields": query_params.fields or ["*"],
                    "type": "best_fields",
                    "boost": config.boost_original_terms
                }
            })
        
        # Add filters if provided
        if query_params.filters:
            search_body["query"]["bool"]["filter"] = self._build_filters(query_params.filters)
        
        # Add sorting
        if query_params.sort_by:
            search_body["sort"] = [
                {query_params.sort_by: {"order": query_params.sort_order.value}}
            ]
        
        # Add highlighting
        if query_params.highlight:
            search_body["highlight"] = {
                "fields": {
                    "*": {"pre_tags": ["<mark>"], "post_tags": ["</mark>"]}
                },
                "require_field_match": False
            }
        
        return search_body
    
    def _get_index_names(self, indices: List) -> str:
        """Get comma-separated index names"""
        index_map = {
            'assets': self.settings.ASSETS_INDEX_NAME,
            'metadata': self.settings.METADATA_INDEX_NAME,
            'content': self.settings.CONTENT_INDEX_NAME,
            'all': f"{self.settings.ASSETS_INDEX_NAME},{self.settings.METADATA_INDEX_NAME},{self.settings.CONTENT_INDEX_NAME}"
        }
        
        index_names = []
        for index in indices:
            if hasattr(index, 'value'):
                index_names.append(index_map.get(index.value, index.value))
            else:
                index_names.append(index_map.get(index, index))
        
        return ','.join(index_names)
    
    def _build_filters(self, filters) -> List[Dict]:
        """Build OpenSearch filters from FilterCondition objects"""
        filter_queries = []
        
        for filter_condition in filters:
            if filter_condition.type.value == "term":
                filter_queries.append({
                    "term": {filter_condition.field: filter_condition.value}
                })
            elif filter_condition.type.value == "range":
                filter_queries.append({
                    "range": {filter_condition.field: filter_condition.value}
                })
            # Add more filter types as needed
        
        return filter_queries
    
    def _analyze_matches(self, hits: List[SearchHit], original_query: str, expansions: List[SynonymExpansion]) -> Tuple[int, int, int]:
        """Analyze search results to categorize matches"""
        original_matches = 0
        synonym_matches = 0
        hybrid_matches = 0
        
        # Get original query terms
        original_terms = set(word.lower() for word in original_query.split())
        
        # Get all synonym terms
        synonym_terms = set()
        for expansion in expansions:
            synonym_terms.update(syn.lower() for syn in expansion.synonyms)
        
        for hit in hits:
            # Check if hit contains original terms or synonyms
            hit_text = ' '.join(str(v) for v in hit.source.values()).lower()
            
            has_original = any(term in hit_text for term in original_terms)
            has_synonym = any(term in hit_text for term in synonym_terms)
            
            if has_original and has_synonym:
                hybrid_matches += 1
            elif has_original:
                original_matches += 1
            elif has_synonym:
                synonym_matches += 1
        
        return original_matches, synonym_matches, hybrid_matches
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate for synonym lookups"""
        # This would track actual cache hits in a real implementation
        # For now, return a placeholder value
        return 0.75
    
    def _analyze_query_characteristics(self, query: str) -> Dict[str, Any]:
        """Analyze query characteristics for synonym analysis"""
        tokens = query.split()
        
        return {
            "word_count": len(tokens),
            "avg_word_length": sum(len(token) for token in tokens) / len(tokens) if tokens else 0,
            "has_numbers": any(token.isdigit() for token in tokens),
            "has_special_chars": any(not token.isalnum() for token in tokens),
            "unique_words": len(set(token.lower() for token in tokens)),
            "query_length": len(query),
            "estimated_domain": self._estimate_domain(query)
        }
    
    def _estimate_domain(self, query: str) -> str:
        """Estimate the domain context of a query"""
        media_keywords = {'video', 'audio', 'image', 'movie', 'film', 'photo', 'music', 'sound'}
        broadcast_keywords = {'news', 'live', 'broadcast', 'report', 'breaking', 'interview'}
        production_keywords = {'edit', 'cut', 'render', 'timeline', 'shot', 'scene', 'effect'}
        
        query_lower = query.lower()
        
        media_score = sum(1 for keyword in media_keywords if keyword in query_lower)
        broadcast_score = sum(1 for keyword in broadcast_keywords if keyword in query_lower)
        production_score = sum(1 for keyword in production_keywords if keyword in query_lower)
        
        if media_score >= broadcast_score and media_score >= production_score:
            return "media"
        elif broadcast_score >= production_score:
            return "broadcast"
        elif production_score > 0:
            return "production"
        else:
            return "general"
    
    async def get_synonym_suggestions(self, query: SynonymSuggestionQuery) -> SynonymSuggestionResponse:
        """Get synonym suggestions for a term"""
        start_time = time.time()
        
        # Use default config for suggestions
        config = SynonymConfig(
            synonym_type=query.synonym_type,
            max_synonyms_per_term=query.size,
            min_similarity_threshold=query.min_similarity,
            domain_context=query.domain_context
        )
        
        # Get synonyms for the term
        synonyms, source = self.expander.get_synonyms(query.term, query.synonym_type, config)
        
        # Build suggestion objects
        suggestions = []
        for synonym in synonyms:
            similarity_score = self.expander._calculate_similarity(query.term, synonym)
            
            suggestion = SynonymSuggestion(
                term=synonym,
                similarity_score=similarity_score,
                frequency=0,  # Would be calculated from corpus in real implementation
                synonym_type=query.synonym_type,
                source=source,
                pos_tag=query.pos_tag,
                domain_context=query.domain_context
            )
            suggestions.append(suggestion)
        
        # Sort by similarity score
        suggestions.sort(key=lambda x: x.similarity_score, reverse=True)
        
        took = int((time.time() - start_time) * 1000)
        
        return SynonymSuggestionResponse(
            term=query.term,
            synonyms=suggestions,
            synonym_type=query.synonym_type,
            total_synonyms=len(suggestions),
            took=took,
            metadata={
                "source": source,
                "domain_context": query.domain_context,
                "pos_tag": query.pos_tag,
                "min_similarity": query.min_similarity
            }
        )
    
    async def get_synonym_stats(self) -> SynonymStats:
        """Get synonym usage statistics"""
        # This would be implemented with real data in production
        return SynonymStats(
            total_synonyms=1250,
            total_terms=425,
            avg_synonyms_per_term=2.94,
            most_common_domains=[
                {"domain": "media", "count": 180},
                {"domain": "broadcast", "count": 125},
                {"domain": "production", "count": 90}
            ],
            synonym_usage_stats={
                "wordnet_usage": 0.45,
                "custom_usage": 0.30,
                "domain_usage": 0.25
            },
            cache_stats={
                "hit_rate": 0.78,
                "total_requests": 5420,
                "cache_hits": 4228
            },
            performance_metrics={
                "avg_expansion_time_ms": 12.5,
                "avg_synonyms_per_query": 3.2,
                "expansion_success_rate": 0.85
            }
        )
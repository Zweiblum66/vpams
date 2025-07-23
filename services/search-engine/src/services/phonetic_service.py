"""
Phonetic Search Service - Sound-based matching capabilities
"""

import re
import time
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
import structlog
from opensearchpy import AsyncOpenSearch
from opensearchpy.exceptions import RequestError, ConnectionError as OpenSearchConnectionError

from ..models.schemas import (
    PhoneticAlgorithm, PhoneticMatchType, PhoneticSearchQuery, PhoneticSearchResponse,
    PhoneticSuggestionQuery, PhoneticSuggestionResponse, SearchHit, IndexType
)
from ..core.config import get_settings
from ..core.exceptions import SearchError, InvalidQueryError

logger = structlog.get_logger()


@dataclass
class PhoneticConfig:
    """Configuration for phonetic matching"""
    algorithm: PhoneticAlgorithm
    boost_exact: float = 2.0
    boost_phonetic: float = 1.0
    min_similarity: float = 0.6
    max_edits: int = 2


class PhoneticEncoder:
    """Handles phonetic encoding using various algorithms"""
    
    @staticmethod
    def soundex(text: str) -> str:
        """
        Generate Soundex code for a given text.
        Soundex is a phonetic algorithm for indexing names by sound.
        """
        if not text:
            return ""
        
        text = text.upper()
        text = re.sub(r'[^A-Z]', '', text)
        
        if not text:
            return ""
        
        # Keep the first letter
        soundex_code = text[0]
        
        # Soundex mapping
        mapping = {
            'B': '1', 'F': '1', 'P': '1', 'V': '1',
            'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
            'D': '3', 'T': '3',
            'L': '4',
            'M': '5', 'N': '5',
            'R': '6'
        }
        
        # Convert letters to numbers
        for char in text[1:]:
            if char in mapping:
                code = mapping[char]
                # Avoid consecutive duplicates
                if not soundex_code or soundex_code[-1] != code:
                    soundex_code += code
        
        # Remove vowels and specific consonants
        soundex_code = soundex_code.replace('A', '').replace('E', '').replace('I', '').replace('O', '').replace('U', '')
        soundex_code = soundex_code.replace('Y', '').replace('H', '').replace('W', '')
        
        # Pad with zeros or truncate to 4 characters
        soundex_code = (soundex_code + '000')[:4]
        
        return soundex_code
    
    @staticmethod
    def metaphone(text: str) -> str:
        """
        Generate Metaphone code for a given text.
        Metaphone is more accurate than Soundex for English.
        """
        if not text:
            return ""
        
        text = text.upper()
        text = re.sub(r'[^A-Z]', '', text)
        
        if not text:
            return ""
        
        # Simplified Metaphone implementation
        # This is a basic version - full implementation would be more complex
        metaphone_code = ""
        i = 0
        
        while i < len(text):
            char = text[i]
            
            if char in 'AEIOU':
                if i == 0:
                    metaphone_code += char
            elif char == 'B':
                metaphone_code += 'B'
            elif char == 'C':
                if i + 1 < len(text) and text[i + 1] == 'H':
                    metaphone_code += 'X'
                    i += 1
                elif i + 1 < len(text) and text[i + 1] in 'EIY':
                    metaphone_code += 'S'
                else:
                    metaphone_code += 'K'
            elif char == 'D':
                if i + 1 < len(text) and text[i + 1] == 'G':
                    metaphone_code += 'J'
                    i += 1
                else:
                    metaphone_code += 'T'
            elif char == 'F':
                metaphone_code += 'F'
            elif char == 'G':
                if i + 1 < len(text) and text[i + 1] == 'H':
                    metaphone_code += 'F'
                    i += 1
                elif i + 1 < len(text) and text[i + 1] in 'EIY':
                    metaphone_code += 'J'
                else:
                    metaphone_code += 'K'
            elif char == 'H':
                if i == 0 or text[i - 1] in 'AEIOU':
                    metaphone_code += 'H'
            elif char == 'J':
                metaphone_code += 'J'
            elif char == 'K':
                if i == 0 or text[i - 1] != 'C':
                    metaphone_code += 'K'
            elif char == 'L':
                metaphone_code += 'L'
            elif char == 'M':
                metaphone_code += 'M'
            elif char == 'N':
                metaphone_code += 'N'
            elif char == 'P':
                if i + 1 < len(text) and text[i + 1] == 'H':
                    metaphone_code += 'F'
                    i += 1
                else:
                    metaphone_code += 'P'
            elif char == 'Q':
                metaphone_code += 'K'
            elif char == 'R':
                metaphone_code += 'R'
            elif char == 'S':
                if i + 1 < len(text) and text[i + 1] == 'H':
                    metaphone_code += 'X'
                    i += 1
                else:
                    metaphone_code += 'S'
            elif char == 'T':
                if i + 1 < len(text) and text[i + 1] == 'H':
                    metaphone_code += '0'
                    i += 1
                else:
                    metaphone_code += 'T'
            elif char == 'V':
                metaphone_code += 'F'
            elif char == 'W':
                if i + 1 < len(text) and text[i + 1] in 'AEIOU':
                    metaphone_code += 'W'
            elif char == 'X':
                metaphone_code += 'KS'
            elif char == 'Y':
                if i + 1 < len(text) and text[i + 1] in 'AEIOU':
                    metaphone_code += 'Y'
            elif char == 'Z':
                metaphone_code += 'S'
            
            i += 1
        
        return metaphone_code
    
    @staticmethod
    def nysiis(text: str) -> str:
        """
        Generate NYSIIS (New York State Identification and Intelligence System) code.
        NYSIIS is designed to be more accurate than Soundex for names.
        """
        if not text:
            return ""
        
        text = text.upper()
        text = re.sub(r'[^A-Z]', '', text)
        
        if not text:
            return ""
        
        # Simplified NYSIIS implementation
        # Replace specific patterns at the beginning
        if text.startswith('MAC'):
            text = 'MCC' + text[3:]
        elif text.startswith('KN'):
            text = 'NN' + text[2:]
        elif text.startswith('K'):
            text = 'C' + text[1:]
        elif text.startswith('PH'):
            text = 'FF' + text[2:]
        elif text.startswith('PF'):
            text = 'FF' + text[2:]
        elif text.startswith('SCH'):
            text = 'SSS' + text[3:]
        
        # Replace specific patterns at the end
        if text.endswith('EE') or text.endswith('IE'):
            text = text[:-2] + 'Y'
        elif text.endswith('DT') or text.endswith('RT') or text.endswith('RD') or text.endswith('NT') or text.endswith('ND'):
            text = text[:-2] + 'D'
        
        # Apply transformation rules
        nysiis_code = ""
        for char in text:
            if char in 'AEIOU':
                nysiis_code += 'A'
            elif char == 'Q':
                nysiis_code += 'G'
            elif char == 'Z':
                nysiis_code += 'S'
            elif char in 'MN':
                nysiis_code += 'N'
            elif char in 'KQ':
                nysiis_code += 'C'
            elif char in 'SCH':
                nysiis_code += 'S'
            elif char in 'PH':
                nysiis_code += 'F'
            elif char == 'H':
                # Keep H if preceded by vowel
                if nysiis_code and nysiis_code[-1] == 'A':
                    nysiis_code += 'H'
            elif char == 'W':
                # Keep W if preceded by vowel
                if nysiis_code and nysiis_code[-1] == 'A':
                    nysiis_code += 'W'
            else:
                nysiis_code += char
        
        # Remove consecutive duplicates
        final_code = ""
        for char in nysiis_code:
            if not final_code or final_code[-1] != char:
                final_code += char
        
        return final_code[:6]  # NYSIIS codes are typically 6 characters
    
    @staticmethod
    def phonex(text: str) -> str:
        """
        Generate Phonex code - a variation of Soundex with improvements.
        """
        if not text:
            return ""
        
        text = text.upper()
        text = re.sub(r'[^A-Z]', '', text)
        
        if not text:
            return ""
        
        # Start with the first letter
        phonex_code = text[0]
        
        # Phonex mapping (similar to Soundex but with refinements)
        mapping = {
            'B': '1', 'F': '1', 'P': '1', 'V': '1',
            'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
            'D': '3', 'T': '3',
            'L': '4',
            'M': '5', 'N': '5',
            'R': '6'
        }
        
        # Convert letters to numbers
        for i, char in enumerate(text[1:], 1):
            if char in mapping:
                code = mapping[char]
                # Avoid consecutive duplicates
                if not phonex_code or phonex_code[-1] != code:
                    phonex_code += code
                    
                # Phonex improvement: handle H and W better
                if char in 'HW' and i > 0 and i < len(text) - 1:
                    if text[i - 1] in 'AEIOU' and text[i + 1] in 'AEIOU':
                        continue  # Skip H and W between vowels
        
        # Pad with zeros or truncate to 4 characters
        phonex_code = (phonex_code + '000')[:4]
        
        return phonex_code
    
    @classmethod
    def encode(cls, text: str, algorithm: PhoneticAlgorithm) -> str:
        """Encode text using the specified phonetic algorithm"""
        if algorithm == PhoneticAlgorithm.SOUNDEX:
            return cls.soundex(text)
        elif algorithm == PhoneticAlgorithm.METAPHONE:
            return cls.metaphone(text)
        elif algorithm == PhoneticAlgorithm.NYSIIS:
            return cls.nysiis(text)
        elif algorithm == PhoneticAlgorithm.PHONEX:
            return cls.phonex(text)
        elif algorithm == PhoneticAlgorithm.FUZZY_SOUNDEX:
            # Fuzzy Soundex - use Soundex with additional fuzzy matching
            return cls.soundex(text)
        else:
            # Default to Soundex for unsupported algorithms
            return cls.soundex(text)


class PhoneticSearchService:
    """Service for phonetic search capabilities"""
    
    def __init__(self, opensearch_client: AsyncOpenSearch):
        self.client = opensearch_client
        self.settings = get_settings()
        self.encoder = PhoneticEncoder()
        
        # Field-specific phonetic configurations
        self.field_configs = {
            "name": {"boost": 3.0, "algorithm": PhoneticAlgorithm.SOUNDEX},
            "title": {"boost": 3.0, "algorithm": PhoneticAlgorithm.METAPHONE},
            "description": {"boost": 2.0, "algorithm": PhoneticAlgorithm.SOUNDEX},
            "tags": {"boost": 2.0, "algorithm": PhoneticAlgorithm.SOUNDEX},
            "keywords": {"boost": 2.0, "algorithm": PhoneticAlgorithm.SOUNDEX},
            "file_name": {"boost": 2.0, "algorithm": PhoneticAlgorithm.SOUNDEX},
            "creator": {"boost": 1.5, "algorithm": PhoneticAlgorithm.METAPHONE},
            "content": {"boost": 1.0, "algorithm": PhoneticAlgorithm.METAPHONE},
            "transcript": {"boost": 1.0, "algorithm": PhoneticAlgorithm.METAPHONE},
        }
    
    def encode_query_terms(self, query: str, algorithm: PhoneticAlgorithm) -> List[Tuple[str, str]]:
        """
        Encode all terms in a query using the specified phonetic algorithm
        
        Returns:
            List of (original_term, phonetic_code) tuples
        """
        # Clean and split the query
        terms = re.findall(r'\b\w+\b', query.lower())
        
        encoded_terms = []
        for term in terms:
            if len(term) >= 2:  # Only encode terms with 2+ characters
                phonetic_code = self.encoder.encode(term, algorithm)
                if phonetic_code:
                    encoded_terms.append((term, phonetic_code))
        
        return encoded_terms
    
    def build_single_term_phonetic_query(
        self, 
        term: str, 
        phonetic_code: str,
        fields: List[str],
        config: PhoneticConfig
    ) -> Dict[str, Any]:
        """Build a phonetic query for a single term"""
        should_queries = []
        
        # Exact match (boosted)
        should_queries.append({
            "multi_match": {
                "query": term,
                "fields": fields,
                "type": "best_fields",
                "boost": config.boost_exact
            }
        })
        
        # Phonetic match using wildcard patterns
        phonetic_patterns = self._generate_phonetic_patterns(phonetic_code)
        
        for pattern in phonetic_patterns:
            should_queries.append({
                "multi_match": {
                    "query": pattern,
                    "fields": fields,
                    "type": "phrase_prefix",
                    "boost": config.boost_phonetic,
                    "fuzziness": "AUTO"
                }
            })
        
        return {
            "bool": {
                "should": should_queries,
                "minimum_should_match": 1
            }
        }
    
    def build_multi_term_phonetic_query(
        self,
        encoded_terms: List[Tuple[str, str]],
        fields: List[str],
        config: PhoneticConfig
    ) -> Dict[str, Any]:
        """Build a phonetic query for multiple terms"""
        term_queries = []
        
        for original_term, phonetic_code in encoded_terms:
            term_query = self.build_single_term_phonetic_query(
                original_term, phonetic_code, fields, config
            )
            term_queries.append(term_query)
        
        return {
            "bool": {
                "should": term_queries,
                "minimum_should_match": max(1, len(term_queries) // 2)  # At least half of terms should match
            }
        }
    
    def build_phrase_phonetic_query(
        self,
        encoded_terms: List[Tuple[str, str]],
        fields: List[str],
        config: PhoneticConfig
    ) -> Dict[str, Any]:
        """Build a phonetic query for phrase matching"""
        should_queries = []
        
        # Extract original terms and phonetic codes
        original_terms = [term for term, _ in encoded_terms]
        phonetic_codes = [code for _, code in encoded_terms]
        
        # Exact phrase match (boosted)
        should_queries.append({
            "multi_match": {
                "query": " ".join(original_terms),
                "fields": fields,
                "type": "phrase",
                "boost": config.boost_exact,
                "slop": 1
            }
        })
        
        # Phonetic phrase-like matching
        for field in fields:
            # Create individual term queries for the field
            term_queries = []
            for original_term, phonetic_code in encoded_terms:
                patterns = self._generate_phonetic_patterns(phonetic_code)
                field_term_queries = []
                
                # Add exact term
                field_term_queries.append({
                    "match": {
                        field: {
                            "query": original_term,
                            "boost": config.boost_exact
                        }
                    }
                })
                
                # Add phonetic patterns
                for pattern in patterns:
                    field_term_queries.append({
                        "match": {
                            field: {
                                "query": pattern,
                                "boost": config.boost_phonetic,
                                "fuzziness": "AUTO"
                            }
                        }
                    })
                
                term_queries.append({
                    "bool": {
                        "should": field_term_queries,
                        "minimum_should_match": 1
                    }
                })
            
            # Combine term queries for this field
            should_queries.append({
                "bool": {
                    "must": term_queries,
                    "boost": self._get_field_boost(field)
                }
            })
        
        return {
            "bool": {
                "should": should_queries,
                "minimum_should_match": 1
            }
        }
    
    def build_adaptive_phonetic_query(
        self,
        query: str,
        encoded_terms: List[Tuple[str, str]],
        fields: List[str],
        config: PhoneticConfig
    ) -> Dict[str, Any]:
        """Build an adaptive phonetic query based on query characteristics"""
        
        # Analyze query characteristics
        is_single_term = len(encoded_terms) == 1
        is_short_query = len(query.split()) <= 2
        has_numbers = bool(re.search(r'\d', query))
        
        if is_single_term:
            # Single term - use single term phonetic query
            original_term, phonetic_code = encoded_terms[0]
            return self.build_single_term_phonetic_query(
                original_term, phonetic_code, fields, config
            )
        elif is_short_query:
            # Short query - use phrase matching
            return self.build_phrase_phonetic_query(encoded_terms, fields, config)
        else:
            # Long query - use multi-term matching
            return self.build_multi_term_phonetic_query(encoded_terms, fields, config)
    
    def _generate_phonetic_patterns(self, phonetic_code: str) -> List[str]:
        """Generate search patterns from phonetic code"""
        patterns = []
        
        # Add the exact phonetic code
        patterns.append(phonetic_code)
        
        # Add variations with wildcards
        if len(phonetic_code) > 2:
            # Prefix pattern
            patterns.append(phonetic_code[:2] + "*")
            
            # Suffix pattern
            patterns.append("*" + phonetic_code[-2:])
            
            # Middle pattern (for longer codes)
            if len(phonetic_code) > 3:
                patterns.append(phonetic_code[0] + "*" + phonetic_code[-1])
        
        return patterns
    
    def _get_field_boost(self, field: str) -> float:
        """Get boost value for a specific field"""
        field_name = field.split("^")[0]  # Remove existing boost notation
        return self.field_configs.get(field_name, {}).get("boost", 1.0)
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query characteristics for phonetic search"""
        words = query.split()
        
        return {
            "word_count": len(words),
            "avg_word_length": sum(len(word) for word in words) / len(words) if words else 0,
            "has_numbers": bool(re.search(r'\d', query)),
            "has_special_chars": bool(re.search(r'[^a-zA-Z0-9\s]', query)),
            "is_likely_name": self._is_likely_name(query),
            "is_technical_term": self._is_technical_term(query)
        }
    
    def _is_likely_name(self, query: str) -> bool:
        """Check if query is likely a person's name"""
        words = query.split()
        if len(words) == 2:
            # Two words might be first name + last name
            return all(word.isalpha() and word.istitle() for word in words)
        return False
    
    def _is_technical_term(self, query: str) -> bool:
        """Check if query contains technical terms"""
        technical_patterns = [
            r'\d+[kKmMgGtT][bB]',  # File sizes (KB, MB, GB, TB)
            r'\d+[pP]',  # Resolutions (720p, 1080p, 4K)
            r'\d+[xX]\d+',  # Dimensions (1920x1080)
            r'\d+fps',  # Frame rates
            r'\.(mp4|avi|mov|wmv|flv|webm|mkv|jpg|png|gif|pdf|doc|docx)',  # File extensions
        ]
        
        for pattern in technical_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False
    
    async def phonetic_search(self, query: PhoneticSearchQuery) -> PhoneticSearchResponse:
        """
        Perform phonetic search with the specified parameters
        
        Args:
            query: Phonetic search query parameters
            
        Returns:
            PhoneticSearchResponse with results and metadata
        """
        try:
            start_time = time.time()
            
            # Encode query terms
            encoded_terms = self.encode_query_terms(query.query, query.algorithm)
            
            if not encoded_terms:
                # No valid terms for phonetic encoding
                if query.use_fallback_search:
                    # Fall back to regular search
                    return await self._fallback_search(query, int((time.time() - start_time) * 1000))
                else:
                    # Return empty results
                    return self._empty_response(query, int((time.time() - start_time) * 1000))
            
            # Create phonetic configuration
            config = PhoneticConfig(
                algorithm=query.algorithm,
                boost_exact=query.boost_exact_matches,
                boost_phonetic=query.boost_phonetic_matches,
                min_similarity=query.min_similarity
            )
            
            # Get fields to search
            fields = query.fields or self._get_default_fields()
            
            # Build phonetic query based on match type
            if query.match_type == PhoneticMatchType.SINGLE_TERM:
                if encoded_terms:
                    original_term, phonetic_code = encoded_terms[0]
                    main_query = self.build_single_term_phonetic_query(
                        original_term, phonetic_code, fields, config
                    )
                else:
                    main_query = {"match_all": {}}
            elif query.match_type == PhoneticMatchType.PHRASE:
                main_query = self.build_phrase_phonetic_query(encoded_terms, fields, config)
            elif query.match_type == PhoneticMatchType.MULTI_TERM:
                main_query = self.build_multi_term_phonetic_query(encoded_terms, fields, config)
            else:  # ADAPTIVE or CROSS_FIELD
                main_query = self.build_adaptive_phonetic_query(
                    query.query, encoded_terms, fields, config
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
            
            # Add phonetic suggestions if requested
            if query.include_suggestions:
                suggestion_body = self._build_phonetic_suggestions(
                    query.query, query.algorithm, fields
                )
                body.update(suggestion_body)
            
            # Determine indices to search
            indices = self._get_search_indices(query.indices)
            
            logger.info(
                "executing_phonetic_search",
                query=query.query,
                algorithm=query.algorithm,
                match_type=query.match_type,
                encoded_terms=[code for _, code in encoded_terms],
                indices=indices
            )
            
            # Execute search
            response = await self.client.search(
                index=indices,
                body=body,
                timeout=f"{self.settings.search_timeout}s"
            )
            
            # Process response
            search_response = await self._process_phonetic_search_response(
                response,
                query,
                encoded_terms,
                int((time.time() - start_time) * 1000)
            )
            
            logger.info(
                "phonetic_search_completed",
                query=query.query,
                algorithm=query.algorithm,
                total_hits=search_response.total_hits,
                took_ms=search_response.took,
                fallback_used=search_response.fallback_used
            )
            
            return search_response
            
        except OpenSearchConnectionError as e:
            logger.error("phonetic_search_connection_error", error=str(e))
            raise SearchError("Failed to connect to search service")
        except RequestError as e:
            logger.error("phonetic_search_request_error", error=str(e))
            raise InvalidQueryError(f"Invalid phonetic search query: {str(e)}")
        except Exception as e:
            logger.error("phonetic_search_failed", error=str(e))
            raise SearchError(f"Phonetic search operation failed: {str(e)}")
    
    async def _fallback_search(self, query: PhoneticSearchQuery, took_ms: int) -> PhoneticSearchResponse:
        """Perform fallback search using regular matching"""
        try:
            # Build simple multi-match query
            body = {
                "size": query.size,
                "from": query.from_,
                "track_total_hits": True,
                "query": {
                    "multi_match": {
                        "query": query.query,
                        "fields": query.fields or self._get_default_fields(),
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                }
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
                    "fields": {"*": {}},
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"]
                }
            
            # Execute search
            indices = self._get_search_indices(query.indices)
            response = await self.client.search(
                index=indices,
                body=body,
                timeout=f"{self.settings.search_timeout}s"
            )
            
            # Process response
            return await self._process_phonetic_search_response(
                response, query, [], took_ms, fallback_used=True
            )
            
        except Exception as e:
            logger.error("fallback_search_failed", error=str(e))
            return self._empty_response(query, took_ms, fallback_used=True)
    
    def _empty_response(self, query: PhoneticSearchQuery, took_ms: int, fallback_used: bool = False) -> PhoneticSearchResponse:
        """Create empty response for phonetic search"""
        return PhoneticSearchResponse(
            query=query.query,
            algorithm=query.algorithm,
            match_type=query.match_type,
            phonetic_tokens=[],
            total_hits=0,
            max_score=None,
            hits=[],
            suggestions=None,
            phonetic_analysis=None,
            took=took_ms,
            timed_out=False,
            page=1,
            per_page=query.size,
            total_pages=0,
            fallback_used=fallback_used,
            exact_matches=0,
            phonetic_matches=0
        )
    
    async def _process_phonetic_search_response(
        self,
        response: Dict[str, Any],
        query: PhoneticSearchQuery,
        encoded_terms: List[Tuple[str, str]],
        took_ms: int,
        fallback_used: bool = False
    ) -> PhoneticSearchResponse:
        """Process OpenSearch response into PhoneticSearchResponse"""
        # Extract hits
        hits = []
        exact_matches = 0
        phonetic_matches = 0
        
        for hit in response.get("hits", {}).get("hits", []):
            search_hit = SearchHit(
                id=hit["_id"],
                index=hit["_index"],
                score=hit.get("_score", 0.0),
                source=hit["_source"],
                highlight=hit.get("highlight", {}) if query.highlight else None
            )
            hits.append(search_hit)
            
            # Classify match type based on score or content analysis
            if self._is_exact_match(hit, query.query):
                exact_matches += 1
            else:
                phonetic_matches += 1
        
        # Extract suggestions if requested
        suggestions = None
        if query.include_suggestions and "suggest" in response:
            suggestions = self._extract_phonetic_suggestions(response["suggest"])
        
        # Generate phonetic analysis if requested
        phonetic_analysis = None
        if query.include_phonetic_analysis:
            phonetic_analysis = self._generate_phonetic_analysis(
                query.query, encoded_terms, query.algorithm
            )
        
        # Calculate pagination
        total_hits = response.get("hits", {}).get("total", {}).get("value", 0)
        current_page = (query.from_ // query.size) + 1
        total_pages = max(1, (total_hits + query.size - 1) // query.size)
        
        return PhoneticSearchResponse(
            query=query.query,
            algorithm=query.algorithm,
            match_type=query.match_type,
            phonetic_tokens=[code for _, code in encoded_terms],
            total_hits=total_hits,
            max_score=response.get("hits", {}).get("max_score"),
            hits=hits,
            suggestions=suggestions,
            phonetic_analysis=phonetic_analysis,
            took=took_ms,
            timed_out=response.get("timed_out", False),
            page=current_page,
            per_page=query.size,
            total_pages=total_pages,
            fallback_used=fallback_used,
            exact_matches=exact_matches,
            phonetic_matches=phonetic_matches
        )
    
    def _is_exact_match(self, hit: Dict[str, Any], query: str) -> bool:
        """Check if hit represents an exact match"""
        source = hit.get("_source", {})
        query_lower = query.lower()
        
        # Check various fields for exact matches
        for field in ["name", "title", "description", "file_name"]:
            if field in source:
                field_value = str(source[field]).lower()
                if query_lower in field_value:
                    return True
        
        return False
    
    def _extract_phonetic_suggestions(self, suggest_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract phonetic suggestions from OpenSearch suggest response"""
        suggestions = []
        
        for suggest_name, suggest_results in suggest_data.items():
            for result in suggest_results:
                for option in result.get("options", []):
                    suggestions.append({
                        "text": option["text"],
                        "score": option.get("score", 0.0),
                        "freq": option.get("freq", 0)
                    })
        
        return suggestions
    
    def _generate_phonetic_analysis(
        self, 
        query: str, 
        encoded_terms: List[Tuple[str, str]], 
        algorithm: PhoneticAlgorithm
    ) -> Dict[str, Any]:
        """Generate phonetic analysis information"""
        analysis = {
            "original_query": query,
            "algorithm_used": algorithm.value,
            "encoded_terms": [
                {
                    "original": original,
                    "phonetic_code": code,
                    "algorithm": algorithm.value
                }
                for original, code in encoded_terms
            ],
            "query_characteristics": self._analyze_query(query)
        }
        
        return analysis
    
    def _build_phonetic_suggestions(
        self, 
        query: str, 
        algorithm: PhoneticAlgorithm, 
        fields: List[str]
    ) -> Dict[str, Any]:
        """Build phonetic suggestions query"""
        # Generate phonetic codes for the query
        encoded_terms = self.encode_query_terms(query, algorithm)
        
        suggest_body = {
            "suggest": {
                "phonetic_suggest": {
                    "text": query,
                    "term": {
                        "field": "_all",
                        "size": 5,
                        "suggest_mode": "popular"
                    }
                }
            }
        }
        
        # Add phonetic-specific suggestions
        if encoded_terms:
            phonetic_suggestions = {}
            for i, (original, code) in enumerate(encoded_terms):
                phonetic_suggestions[f"phonetic_{i}"] = {
                    "text": original,
                    "term": {
                        "field": "_all",
                        "size": 3,
                        "suggest_mode": "popular"
                    }
                }
            suggest_body["suggest"].update(phonetic_suggestions)
        
        return suggest_body
    
    def _get_default_fields(self) -> List[str]:
        """Get default fields for phonetic search"""
        return [
            "name^3",
            "title^3",
            "description^2",
            "file_name^2",
            "tags^2",
            "keywords^2",
            "creator^1.5",
            "content",
            "transcript",
            "ocr_text",
            "*"
        ]
    
    def _get_search_indices(self, index_types: List[IndexType]) -> str:
        """Get comma-separated list of indices to search"""
        index_mappings = {
            IndexType.ASSETS: self.settings.assets_index_name,
            IndexType.METADATA: self.settings.metadata_index_name,
            IndexType.CONTENT: self.settings.content_index_name,
            IndexType.ALL: f"{self.settings.assets_index_name},{self.settings.metadata_index_name},{self.settings.content_index_name}"
        }
        
        if IndexType.ALL in index_types:
            return index_mappings[IndexType.ALL]
        
        indices = []
        for index_type in index_types:
            if index_type in index_mappings:
                indices.append(index_mappings[index_type])
        
        return ",".join(indices) if indices else index_mappings[IndexType.ALL]
    
    async def phonetic_suggestions(self, query: PhoneticSuggestionQuery) -> PhoneticSuggestionResponse:
        """
        Get phonetic suggestions for a given text
        
        Args:
            query: Phonetic suggestion query parameters
            
        Returns:
            PhoneticSuggestionResponse with suggestions and metadata
        """
        try:
            start_time = time.time()
            
            # Generate phonetic code for the input text
            phonetic_code = self.encoder.encode(query.text, query.algorithm)
            
            # Build suggestions query
            body = {
                "suggest": {
                    "phonetic_suggest": {
                        "text": query.text,
                        "term": {
                            "field": query.field,
                            "size": query.size,
                            "suggest_mode": "popular"
                        }
                    }
                }
            }
            
            # Execute suggestions request
            indices = self._get_search_indices([IndexType.ALL])
            response = await self.client.search(
                index=indices,
                body=body,
                timeout=f"{self.settings.search_timeout}s"
            )
            
            # Process suggestions
            suggestions = []
            if "suggest" in response:
                for suggest_name, suggest_results in response["suggest"].items():
                    for result in suggest_results:
                        for option in result.get("options", []):
                            # Calculate phonetic similarity
                            option_phonetic = self.encoder.encode(option["text"], query.algorithm)
                            similarity = self._calculate_phonetic_similarity(
                                phonetic_code, option_phonetic
                            )
                            
                            if similarity >= query.min_similarity:
                                suggestions.append({
                                    "text": option["text"],
                                    "score": option.get("score", 0.0),
                                    "freq": option.get("freq", 0),
                                    "phonetic_code": option_phonetic,
                                    "similarity": similarity
                                })
            
            # Sort suggestions by similarity and score
            suggestions.sort(key=lambda x: (x["similarity"], x["score"]), reverse=True)
            suggestions = suggestions[:query.size]
            
            took_ms = int((time.time() - start_time) * 1000)
            
            return PhoneticSuggestionResponse(
                text=query.text,
                algorithm=query.algorithm,
                phonetic_code=phonetic_code,
                suggestions=suggestions,
                took=took_ms,
                metadata={
                    "field": query.field,
                    "algorithm": query.algorithm.value,
                    "min_similarity": query.min_similarity,
                    "total_suggestions": len(suggestions)
                }
            )
            
        except Exception as e:
            logger.error("phonetic_suggestions_failed", error=str(e))
            raise SearchError(f"Phonetic suggestions failed: {str(e)}")
    
    def _calculate_phonetic_similarity(self, code1: str, code2: str) -> float:
        """Calculate similarity between two phonetic codes"""
        if not code1 or not code2:
            return 0.0
        
        if code1 == code2:
            return 1.0
        
        # Calculate Levenshtein distance
        len1, len2 = len(code1), len(code2)
        if len1 > len2:
            code1, code2 = code2, code1
            len1, len2 = len2, len1
        
        current_row = range(len1 + 1)
        for i in range(1, len2 + 1):
            previous_row, current_row = current_row, [i] + [0] * len1
            for j in range(1, len1 + 1):
                add, delete, change = previous_row[j] + 1, current_row[j - 1] + 1, previous_row[j - 1]
                if code1[j - 1] != code2[i - 1]:
                    change += 1
                current_row[j] = min(add, delete, change)
        
        # Convert distance to similarity
        max_len = max(len1, len2)
        if max_len == 0:
            return 1.0
        
        return 1.0 - (current_row[len1] / max_len)
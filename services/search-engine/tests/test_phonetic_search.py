"""
Tests for Phonetic Search functionality
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from src.services.phonetic_service import PhoneticSearchService, PhoneticEncoder
from src.models.schemas import (
    PhoneticSearchQuery, PhoneticSearchResponse, PhoneticSuggestionQuery, 
    PhoneticSuggestionResponse, PhoneticAlgorithm, PhoneticMatchType, 
    IndexType, SortOrder
)
from src.core.exceptions import SearchError, InvalidQueryError


class TestPhoneticEncoder:
    """Test phonetic encoding algorithms"""
    
    def test_soundex_basic(self):
        """Test basic Soundex encoding"""
        encoder = PhoneticEncoder()
        
        # Test common names
        assert encoder.soundex("Smith") == "S530"
        assert encoder.soundex("Johnson") == "J525"
        assert encoder.soundex("Williams") == "W452"
        assert encoder.soundex("Brown") == "B650"
        assert encoder.soundex("Jones") == "J520"
        
        # Test similar sounding names
        assert encoder.soundex("Smith") == encoder.soundex("Smyth")
        assert encoder.soundex("Johnson") == encoder.soundex("Jonsen")
        
    def test_soundex_edge_cases(self):
        """Test Soundex with edge cases"""
        encoder = PhoneticEncoder()
        
        # Empty string
        assert encoder.soundex("") == ""
        
        # Single character
        assert encoder.soundex("A") == "A000"
        
        # Numbers and special characters
        assert encoder.soundex("A1B2C3") == "A120"
        assert encoder.soundex("A-B-C") == "A120"
        
        # Case insensitive
        assert encoder.soundex("smith") == encoder.soundex("SMITH")
        assert encoder.soundex("Smith") == encoder.soundex("smith")
    
    def test_metaphone_basic(self):
        """Test basic Metaphone encoding"""
        encoder = PhoneticEncoder()
        
        # Test common words
        metaphone_smith = encoder.metaphone("Smith")
        metaphone_johnson = encoder.metaphone("Johnson")
        metaphone_williams = encoder.metaphone("Williams")
        
        # Should return non-empty strings
        assert len(metaphone_smith) > 0
        assert len(metaphone_johnson) > 0
        assert len(metaphone_williams) > 0
        
        # Similar sounding words should have similar codes
        assert encoder.metaphone("Smith") == encoder.metaphone("Smyth")
        assert encoder.metaphone("Phone") == encoder.metaphone("Fone")
    
    def test_nysiis_basic(self):
        """Test basic NYSIIS encoding"""
        encoder = PhoneticEncoder()
        
        # Test common names
        nysiis_smith = encoder.nysiis("Smith")
        nysiis_johnson = encoder.nysiis("Johnson")
        
        # Should return non-empty strings
        assert len(nysiis_smith) > 0
        assert len(nysiis_johnson) > 0
        
        # Should be 6 characters or less
        assert len(nysiis_smith) <= 6
        assert len(nysiis_johnson) <= 6
    
    def test_phonex_basic(self):
        """Test basic Phonex encoding"""
        encoder = PhoneticEncoder()
        
        # Test common names
        phonex_smith = encoder.phonex("Smith")
        phonex_johnson = encoder.phonex("Johnson")
        
        # Should return 4-character codes
        assert len(phonex_smith) == 4
        assert len(phonex_johnson) == 4
        
        # Similar to Soundex but with improvements
        assert phonex_smith.startswith("S")
        assert phonex_johnson.startswith("J")
    
    def test_encode_with_different_algorithms(self):
        """Test encoding with different algorithms"""
        encoder = PhoneticEncoder()
        test_word = "Smith"
        
        # Test all algorithms
        soundex_code = encoder.encode(test_word, PhoneticAlgorithm.SOUNDEX)
        metaphone_code = encoder.encode(test_word, PhoneticAlgorithm.METAPHONE)
        nysiis_code = encoder.encode(test_word, PhoneticAlgorithm.NYSIIS)
        phonex_code = encoder.encode(test_word, PhoneticAlgorithm.PHONEX)
        
        # All should return non-empty codes
        assert len(soundex_code) > 0
        assert len(metaphone_code) > 0
        assert len(nysiis_code) > 0
        assert len(phonex_code) > 0
        
        # Codes should be different (mostly)
        codes = [soundex_code, metaphone_code, nysiis_code, phonex_code]
        assert len(set(codes)) >= 2  # At least some variation


class TestPhoneticSearchService:
    """Test phonetic search service"""
    
    @pytest.fixture
    def mock_opensearch_client(self):
        """Create mock OpenSearch client"""
        client = AsyncMock()
        client.search = AsyncMock()
        return client
    
    @pytest.fixture
    def phonetic_service(self, mock_opensearch_client):
        """Create phonetic search service with mock client"""
        with patch('src.services.phonetic_service.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                assets_index_name="test_assets",
                metadata_index_name="test_metadata",
                content_index_name="test_content",
                search_timeout=30
            )
            return PhoneticSearchService(mock_opensearch_client)
    
    def test_encode_query_terms(self, phonetic_service):
        """Test encoding query terms"""
        # Test single term
        encoded = phonetic_service.encode_query_terms("Smith", PhoneticAlgorithm.SOUNDEX)
        assert len(encoded) == 1
        assert encoded[0][0] == "smith"
        assert encoded[0][1] == "S530"
        
        # Test multiple terms
        encoded = phonetic_service.encode_query_terms("John Smith", PhoneticAlgorithm.SOUNDEX)
        assert len(encoded) == 2
        assert encoded[0][0] == "john"
        assert encoded[1][0] == "smith"
        
        # Test with special characters
        encoded = phonetic_service.encode_query_terms("John-Smith Jr.", PhoneticAlgorithm.SOUNDEX)
        assert len(encoded) == 3
        assert "john" in [term for term, _ in encoded]
        assert "smith" in [term for term, _ in encoded]
        assert "jr" in [term for term, _ in encoded]
        
        # Test empty query
        encoded = phonetic_service.encode_query_terms("", PhoneticAlgorithm.SOUNDEX)
        assert len(encoded) == 0
        
        # Test short terms (should be filtered out)
        encoded = phonetic_service.encode_query_terms("a b", PhoneticAlgorithm.SOUNDEX)
        assert len(encoded) == 0
    
    def test_build_single_term_phonetic_query(self, phonetic_service):
        """Test building single term phonetic query"""
        from src.services.phonetic_service import PhoneticConfig
        
        config = PhoneticConfig(
            algorithm=PhoneticAlgorithm.SOUNDEX,
            boost_exact=2.0,
            boost_phonetic=1.0,
            min_similarity=0.6
        )
        
        fields = ["name", "title", "description"]
        query = phonetic_service.build_single_term_phonetic_query(
            "Smith", "S530", fields, config
        )
        
        # Should return a bool query with should clauses
        assert "bool" in query
        assert "should" in query["bool"]
        assert "minimum_should_match" in query["bool"]
        assert len(query["bool"]["should"]) >= 2  # At least exact and phonetic matches
    
    def test_build_multi_term_phonetic_query(self, phonetic_service):
        """Test building multi-term phonetic query"""
        from src.services.phonetic_service import PhoneticConfig
        
        config = PhoneticConfig(
            algorithm=PhoneticAlgorithm.SOUNDEX,
            boost_exact=2.0,
            boost_phonetic=1.0,
            min_similarity=0.6
        )
        
        encoded_terms = [("john", "J500"), ("smith", "S530")]
        fields = ["name", "title", "description"]
        
        query = phonetic_service.build_multi_term_phonetic_query(
            encoded_terms, fields, config
        )
        
        # Should return a bool query with should clauses
        assert "bool" in query
        assert "should" in query["bool"]
        assert "minimum_should_match" in query["bool"]
        assert len(query["bool"]["should"]) == 2  # One for each term
    
    def test_build_phrase_phonetic_query(self, phonetic_service):
        """Test building phrase phonetic query"""
        from src.services.phonetic_service import PhoneticConfig
        
        config = PhoneticConfig(
            algorithm=PhoneticAlgorithm.SOUNDEX,
            boost_exact=2.0,
            boost_phonetic=1.0,
            min_similarity=0.6
        )
        
        encoded_terms = [("john", "J500"), ("smith", "S530")]
        fields = ["name^3", "title^2", "description"]
        
        query = phonetic_service.build_phrase_phonetic_query(
            encoded_terms, fields, config
        )
        
        # Should return a bool query with should clauses
        assert "bool" in query
        assert "should" in query["bool"]
        assert "minimum_should_match" in query["bool"]
        # Should have queries for phrase matching
        assert len(query["bool"]["should"]) >= 1
    
    def test_build_adaptive_phonetic_query(self, phonetic_service):
        """Test building adaptive phonetic query"""
        from src.services.phonetic_service import PhoneticConfig
        
        config = PhoneticConfig(
            algorithm=PhoneticAlgorithm.SOUNDEX,
            boost_exact=2.0,
            boost_phonetic=1.0,
            min_similarity=0.6
        )
        
        fields = ["name", "title", "description"]
        
        # Test single term
        single_term = [("smith", "S530")]
        query = phonetic_service.build_adaptive_phonetic_query(
            "Smith", single_term, fields, config
        )
        assert "bool" in query
        
        # Test phrase
        phrase_terms = [("john", "J500"), ("smith", "S530")]
        query = phonetic_service.build_adaptive_phonetic_query(
            "John Smith", phrase_terms, fields, config
        )
        assert "bool" in query
        
        # Test long query
        long_terms = [("john", "J500"), ("smith", "S530"), ("junior", "J560")]
        query = phonetic_service.build_adaptive_phonetic_query(
            "John Smith Junior Engineer", long_terms, fields, config
        )
        assert "bool" in query
    
    def test_generate_phonetic_patterns(self, phonetic_service):
        """Test generating phonetic patterns"""
        patterns = phonetic_service._generate_phonetic_patterns("S530")
        
        # Should include the exact code
        assert "S530" in patterns
        
        # Should include wildcard patterns
        assert len(patterns) > 1
        
        # Check pattern types
        has_prefix = any(p.endswith("*") for p in patterns)
        has_suffix = any(p.startswith("*") for p in patterns)
        assert has_prefix or has_suffix  # Should have at least one wildcard pattern
    
    def test_analyze_query(self, phonetic_service):
        """Test query analysis"""
        # Test name-like query
        analysis = phonetic_service._analyze_query("John Smith")
        assert analysis["word_count"] == 2
        assert analysis["avg_word_length"] == 4.5
        assert analysis["is_likely_name"] is True
        
        # Test technical query
        analysis = phonetic_service._analyze_query("1080p video file")
        assert analysis["word_count"] == 3
        assert analysis["is_technical_term"] is True
        
        # Test query with numbers
        analysis = phonetic_service._analyze_query("video123")
        assert analysis["has_numbers"] is True
        
        # Test query with special characters
        analysis = phonetic_service._analyze_query("test@example.com")
        assert analysis["has_special_chars"] is True
    
    @pytest.mark.asyncio
    async def test_phonetic_search_success(self, phonetic_service, mock_opensearch_client):
        """Test successful phonetic search"""
        # Mock OpenSearch response
        mock_response = {
            "hits": {
                "total": {"value": 2},
                "max_score": 1.5,
                "hits": [
                    {
                        "_id": "1",
                        "_index": "test_assets",
                        "_score": 1.5,
                        "_source": {
                            "name": "John Smith Video",
                            "description": "Video by John Smith"
                        },
                        "highlight": {
                            "name": ["<mark>John</mark> <mark>Smith</mark> Video"]
                        }
                    },
                    {
                        "_id": "2",
                        "_index": "test_assets",
                        "_score": 1.2,
                        "_source": {
                            "name": "Jon Smyth Interview",
                            "description": "Interview with Jon Smyth"
                        },
                        "highlight": {
                            "name": ["<mark>Jon</mark> <mark>Smyth</mark> Interview"]
                        }
                    }
                ]
            },
            "timed_out": False
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Create query
        query = PhoneticSearchQuery(
            query="John Smith",
            algorithm=PhoneticAlgorithm.SOUNDEX,
            match_type=PhoneticMatchType.ADAPTIVE,
            size=10
        )
        
        # Execute search
        result = await phonetic_service.phonetic_search(query)
        
        # Verify results
        assert isinstance(result, PhoneticSearchResponse)
        assert result.query == "John Smith"
        assert result.algorithm == PhoneticAlgorithm.SOUNDEX
        assert result.match_type == PhoneticMatchType.ADAPTIVE
        assert result.total_hits == 2
        assert len(result.hits) == 2
        assert len(result.phonetic_tokens) == 2  # ["J500", "S530"]
        assert result.fallback_used is False
        
        # Verify OpenSearch was called
        mock_opensearch_client.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_phonetic_search_with_suggestions(self, phonetic_service, mock_opensearch_client):
        """Test phonetic search with suggestions"""
        # Mock OpenSearch response with suggestions
        mock_response = {
            "hits": {
                "total": {"value": 1},
                "max_score": 1.0,
                "hits": [
                    {
                        "_id": "1",
                        "_index": "test_assets",
                        "_score": 1.0,
                        "_source": {"name": "John Smith Video"}
                    }
                ]
            },
            "suggest": {
                "phonetic_suggest": [
                    {
                        "text": "John Smith",
                        "offset": 0,
                        "length": 10,
                        "options": [
                            {"text": "Jon Smith", "score": 0.8, "freq": 5},
                            {"text": "John Smyth", "score": 0.7, "freq": 3}
                        ]
                    }
                ]
            },
            "timed_out": False
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Create query with suggestions
        query = PhoneticSearchQuery(
            query="John Smith",
            algorithm=PhoneticAlgorithm.SOUNDEX,
            match_type=PhoneticMatchType.ADAPTIVE,
            include_suggestions=True,
            size=10
        )
        
        # Execute search
        result = await phonetic_service.phonetic_search(query)
        
        # Verify suggestions
        assert result.suggestions is not None
        assert len(result.suggestions) == 2
        assert result.suggestions[0]["text"] == "Jon Smith"
        assert result.suggestions[1]["text"] == "John Smyth"
    
    @pytest.mark.asyncio
    async def test_phonetic_search_with_analysis(self, phonetic_service, mock_opensearch_client):
        """Test phonetic search with analysis"""
        # Mock OpenSearch response
        mock_response = {
            "hits": {
                "total": {"value": 1},
                "max_score": 1.0,
                "hits": [
                    {
                        "_id": "1",
                        "_index": "test_assets",
                        "_score": 1.0,
                        "_source": {"name": "John Smith Video"}
                    }
                ]
            },
            "timed_out": False
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Create query with analysis
        query = PhoneticSearchQuery(
            query="John Smith",
            algorithm=PhoneticAlgorithm.SOUNDEX,
            match_type=PhoneticMatchType.ADAPTIVE,
            include_phonetic_analysis=True,
            size=10
        )
        
        # Execute search
        result = await phonetic_service.phonetic_search(query)
        
        # Verify analysis
        assert result.phonetic_analysis is not None
        assert "original_query" in result.phonetic_analysis
        assert "algorithm_used" in result.phonetic_analysis
        assert "encoded_terms" in result.phonetic_analysis
        assert "query_characteristics" in result.phonetic_analysis
        
        # Verify encoded terms
        encoded_terms = result.phonetic_analysis["encoded_terms"]
        assert len(encoded_terms) == 2
        assert encoded_terms[0]["original"] == "john"
        assert encoded_terms[1]["original"] == "smith"
    
    @pytest.mark.asyncio
    async def test_phonetic_search_fallback(self, phonetic_service, mock_opensearch_client):
        """Test phonetic search with fallback"""
        # Mock OpenSearch response for fallback
        mock_response = {
            "hits": {
                "total": {"value": 1},
                "max_score": 1.0,
                "hits": [
                    {
                        "_id": "1",
                        "_index": "test_assets",
                        "_score": 1.0,
                        "_source": {"name": "Special Characters !@#$"}
                    }
                ]
            },
            "timed_out": False
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Create query with special characters (no phonetic encoding)
        query = PhoneticSearchQuery(
            query="!@#$",
            algorithm=PhoneticAlgorithm.SOUNDEX,
            match_type=PhoneticMatchType.ADAPTIVE,
            use_fallback_search=True,
            size=10
        )
        
        # Execute search
        result = await phonetic_service.phonetic_search(query)
        
        # Verify fallback was used
        assert result.fallback_used is True
        assert result.total_hits == 1
        assert len(result.phonetic_tokens) == 0  # No valid phonetic tokens
    
    @pytest.mark.asyncio
    async def test_phonetic_search_no_fallback(self, phonetic_service, mock_opensearch_client):
        """Test phonetic search without fallback"""
        # Create query with special characters and no fallback
        query = PhoneticSearchQuery(
            query="!@#$",
            algorithm=PhoneticAlgorithm.SOUNDEX,
            match_type=PhoneticMatchType.ADAPTIVE,
            use_fallback_search=False,
            size=10
        )
        
        # Execute search
        result = await phonetic_service.phonetic_search(query)
        
        # Verify empty results
        assert result.fallback_used is False
        assert result.total_hits == 0
        assert len(result.hits) == 0
        assert len(result.phonetic_tokens) == 0
    
    @pytest.mark.asyncio
    async def test_phonetic_search_error_handling(self, phonetic_service, mock_opensearch_client):
        """Test phonetic search error handling"""
        # Mock OpenSearch error
        mock_opensearch_client.search.side_effect = Exception("OpenSearch error")
        
        # Create query
        query = PhoneticSearchQuery(
            query="John Smith",
            algorithm=PhoneticAlgorithm.SOUNDEX,
            match_type=PhoneticMatchType.ADAPTIVE,
            size=10
        )
        
        # Execute search should raise SearchError
        with pytest.raises(SearchError):
            await phonetic_service.phonetic_search(query)
    
    @pytest.mark.asyncio
    async def test_phonetic_suggestions_success(self, phonetic_service, mock_opensearch_client):
        """Test successful phonetic suggestions"""
        # Mock OpenSearch response
        mock_response = {
            "suggest": {
                "phonetic_suggest": [
                    {
                        "text": "Smith",
                        "offset": 0,
                        "length": 5,
                        "options": [
                            {"text": "Smith", "score": 1.0, "freq": 100},
                            {"text": "Smyth", "score": 0.8, "freq": 50},
                            {"text": "Smythe", "score": 0.7, "freq": 30}
                        ]
                    }
                ]
            }
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Create suggestion query
        query = PhoneticSuggestionQuery(
            text="Smith",
            algorithm=PhoneticAlgorithm.SOUNDEX,
            size=5
        )
        
        # Execute suggestions
        result = await phonetic_service.phonetic_suggestions(query)
        
        # Verify results
        assert isinstance(result, PhoneticSuggestionResponse)
        assert result.text == "Smith"
        assert result.algorithm == PhoneticAlgorithm.SOUNDEX
        assert result.phonetic_code == "S530"
        assert len(result.suggestions) == 3
        
        # Verify suggestions have required fields
        for suggestion in result.suggestions:
            assert "text" in suggestion
            assert "score" in suggestion
            assert "freq" in suggestion
            assert "phonetic_code" in suggestion
            assert "similarity" in suggestion
    
    @pytest.mark.asyncio
    async def test_phonetic_suggestions_with_similarity_filter(self, phonetic_service, mock_opensearch_client):
        """Test phonetic suggestions with similarity filtering"""
        # Mock OpenSearch response
        mock_response = {
            "suggest": {
                "phonetic_suggest": [
                    {
                        "text": "Smith",
                        "offset": 0,
                        "length": 5,
                        "options": [
                            {"text": "Smith", "score": 1.0, "freq": 100},
                            {"text": "Smyth", "score": 0.8, "freq": 50},
                            {"text": "Jones", "score": 0.3, "freq": 80}  # Different phonetic code
                        ]
                    }
                ]
            }
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Create suggestion query with high similarity threshold
        query = PhoneticSuggestionQuery(
            text="Smith",
            algorithm=PhoneticAlgorithm.SOUNDEX,
            size=5,
            min_similarity=0.7
        )
        
        # Execute suggestions
        result = await phonetic_service.phonetic_suggestions(query)
        
        # Verify filtering (should exclude "Jones" due to different phonetic code)
        assert len(result.suggestions) == 2  # Only Smith and Smyth
        suggestion_texts = [s["text"] for s in result.suggestions]
        assert "Smith" in suggestion_texts
        assert "Smyth" in suggestion_texts
        assert "Jones" not in suggestion_texts
    
    def test_calculate_phonetic_similarity(self, phonetic_service):
        """Test phonetic similarity calculation"""
        # Identical codes
        assert phonetic_service._calculate_phonetic_similarity("S530", "S530") == 1.0
        
        # Different codes
        similarity = phonetic_service._calculate_phonetic_similarity("S530", "J500")
        assert 0.0 <= similarity <= 1.0
        assert similarity < 1.0
        
        # Similar codes
        similarity = phonetic_service._calculate_phonetic_similarity("S530", "S531")
        assert 0.5 <= similarity <= 1.0
        
        # Empty codes
        assert phonetic_service._calculate_phonetic_similarity("", "") == 0.0
        assert phonetic_service._calculate_phonetic_similarity("S530", "") == 0.0
        assert phonetic_service._calculate_phonetic_similarity("", "S530") == 0.0
    
    def test_get_field_boost(self, phonetic_service):
        """Test field boost calculation"""
        # Test configured fields
        assert phonetic_service._get_field_boost("name") == 3.0
        assert phonetic_service._get_field_boost("title") == 3.0
        assert phonetic_service._get_field_boost("description") == 2.0
        assert phonetic_service._get_field_boost("content") == 1.0
        
        # Test field with boost notation
        assert phonetic_service._get_field_boost("name^2") == 3.0  # Should use config, not notation
        
        # Test unknown field
        assert phonetic_service._get_field_boost("unknown_field") == 1.0
    
    def test_get_search_indices(self, phonetic_service):
        """Test search indices generation"""
        # Test ALL index
        indices = phonetic_service._get_search_indices([IndexType.ALL])
        assert "test_assets" in indices
        assert "test_metadata" in indices
        assert "test_content" in indices
        
        # Test specific indices
        indices = phonetic_service._get_search_indices([IndexType.ASSETS])
        assert indices == "test_assets"
        
        indices = phonetic_service._get_search_indices([IndexType.METADATA, IndexType.CONTENT])
        assert "test_metadata" in indices
        assert "test_content" in indices
        assert "test_assets" not in indices
    
    def test_get_default_fields(self, phonetic_service):
        """Test default fields generation"""
        fields = phonetic_service._get_default_fields()
        
        # Should include key fields with boosts
        assert "name^3" in fields
        assert "title^3" in fields
        assert "description^2" in fields
        assert "content" in fields
        assert "*" in fields  # Catch-all
        
        # Should have reasonable number of fields
        assert len(fields) >= 10
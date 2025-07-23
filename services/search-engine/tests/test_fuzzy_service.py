"""
Tests for the Fuzzy Search Service
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.services.fuzzy_service import FuzzySearchService, FuzzinessType, FuzzyMatchType, FuzzyConfig
from src.core.exceptions import SearchError, InvalidQueryError


@pytest.fixture
def mock_opensearch_client():
    """Mock OpenSearch client"""
    client = AsyncMock()
    return client


@pytest.fixture
def fuzzy_service(mock_opensearch_client):
    """Fuzzy search service with mocked client"""
    return FuzzySearchService(mock_opensearch_client)


@pytest.fixture
def sample_fuzzy_config():
    """Sample fuzzy configuration"""
    return FuzzyConfig(
        fuzziness=FuzzinessType.AUTO,
        prefix_length=1,
        max_expansions=50,
        transpositions=True,
        boost=1.0
    )


@pytest.mark.asyncio
class TestFuzzySearchService:
    """Test fuzzy search service functionality"""
    
    def test_build_single_term_fuzzy_query(self, fuzzy_service, sample_fuzzy_config):
        """Test building single term fuzzy query"""
        query = fuzzy_service.build_single_term_fuzzy_query(
            "test", 
            "title", 
            sample_fuzzy_config
        )
        
        assert "fuzzy" in query
        assert query["fuzzy"]["title"]["value"] == "test"
        assert query["fuzzy"]["title"]["fuzziness"] == "AUTO"
        assert query["fuzzy"]["title"]["prefix_length"] == 1
        assert query["fuzzy"]["title"]["max_expansions"] == 50
        assert query["fuzzy"]["title"]["transpositions"] == True
    
    def test_build_multi_term_fuzzy_query(self, fuzzy_service, sample_fuzzy_config):
        """Test building multi-term fuzzy query"""
        terms = ["test", "video"]
        query = fuzzy_service.build_multi_term_fuzzy_query(
            terms, 
            ["title", "description"], 
            sample_fuzzy_config
        )
        
        assert "bool" in query
        assert "should" in query["bool"]
        assert len(query["bool"]["should"]) > 0
        assert query["bool"]["minimum_should_match"] == 1
        
        # Check that each term has fuzzy queries for each field
        fuzzy_queries = query["bool"]["should"]
        assert len(fuzzy_queries) >= 2  # At least one for each term
    
    def test_build_fuzzy_phrase_query(self, fuzzy_service, sample_fuzzy_config):
        """Test building fuzzy phrase query"""
        phrase = "test video file"
        query = fuzzy_service.build_fuzzy_phrase_query(
            phrase, 
            ["title"], 
            slop=2,
            config=sample_fuzzy_config
        )
        
        assert "span_near" in query
        assert query["span_near"]["slop"] == 2
        assert query["span_near"]["in_order"] == True
        assert "clauses" in query["span_near"]
        assert len(query["span_near"]["clauses"]) == 3  # Three words
    
    def test_build_cross_field_fuzzy_query(self, fuzzy_service, sample_fuzzy_config):
        """Test building cross-field fuzzy query"""
        query = fuzzy_service.build_cross_field_fuzzy_query(
            "test video", 
            ["title", "description"], 
            sample_fuzzy_config
        )
        
        assert "multi_match" in query
        assert query["multi_match"]["query"] == "test video"
        assert query["multi_match"]["type"] == "cross_fields"
        assert query["multi_match"]["fuzziness"] == "AUTO"
        assert query["multi_match"]["operator"] == "and"
    
    def test_build_adaptive_fuzzy_query_short_words(self, fuzzy_service):
        """Test adaptive fuzzy query with short words"""
        query = fuzzy_service.build_adaptive_fuzzy_query(
            "cat dog", 
            ["title"], 
            FuzzyMatchType.ADAPTIVE
        )
        
        # Should use strict config for short words
        assert query is not None
    
    def test_build_adaptive_fuzzy_query_technical_terms(self, fuzzy_service):
        """Test adaptive fuzzy query with technical terms"""
        query = fuzzy_service.build_adaptive_fuzzy_query(
            "test.mp4 video", 
            ["title"], 
            FuzzyMatchType.ADAPTIVE
        )
        
        # Should detect technical terms and use appropriate config
        assert query is not None
    
    def test_build_adaptive_fuzzy_query_long_words(self, fuzzy_service):
        """Test adaptive fuzzy query with long words"""
        query = fuzzy_service.build_adaptive_fuzzy_query(
            "configuration management", 
            ["title"], 
            FuzzyMatchType.ADAPTIVE
        )
        
        # Should use loose config for long words
        assert query is not None
    
    def test_build_fuzzy_suggestion_query(self, fuzzy_service, sample_fuzzy_config):
        """Test building fuzzy suggestion query"""
        query = fuzzy_service.build_fuzzy_suggestion_query(
            "test", 
            "title", 
            5,
            sample_fuzzy_config
        )
        
        assert "suggest" in query
        assert query["suggest"]["text"] == "test"
        assert "fuzzy_suggest" in query["suggest"]
        assert query["suggest"]["fuzzy_suggest"]["term"]["field"] == "title"
        assert query["suggest"]["fuzzy_suggest"]["term"]["size"] == 5
    
    def test_analyze_query_simple_text(self, fuzzy_service):
        """Test query analysis for simple text"""
        analysis = fuzzy_service._analyze_query("hello world")
        
        assert analysis["word_count"] == 2
        assert analysis["avg_word_length"] == 5.0
        assert analysis["contains_technical_terms"] == False
        assert analysis["is_phrase"] == True
        assert analysis["has_special_chars"] == False
        assert analysis["terms"] == ["hello", "world"]
    
    def test_analyze_query_technical_terms(self, fuzzy_service):
        """Test query analysis for technical terms"""
        analysis = fuzzy_service._analyze_query("video.mp4 1080p")
        
        assert analysis["word_count"] == 2
        assert analysis["contains_technical_terms"] == True
        assert analysis["has_special_chars"] == True
    
    def test_analyze_query_quoted_phrase(self, fuzzy_service):
        """Test query analysis for quoted phrases"""
        analysis = fuzzy_service._analyze_query('"exact phrase"')
        
        assert analysis["word_count"] == 2
        assert analysis["is_phrase"] == True
        assert analysis["terms"] == ["exact", "phrase"]
    
    def test_tokenize_phrase_simple(self, fuzzy_service):
        """Test tokenizing simple phrase"""
        terms = fuzzy_service._tokenize_phrase("hello world")
        assert terms == ["hello", "world"]
    
    def test_tokenize_phrase_quoted(self, fuzzy_service):
        """Test tokenizing quoted phrase"""
        terms = fuzzy_service._tokenize_phrase('"hello world"')
        assert terms == ["hello", "world"]
    
    def test_tokenize_phrase_with_extra_spaces(self, fuzzy_service):
        """Test tokenizing phrase with extra spaces"""
        terms = fuzzy_service._tokenize_phrase("  hello   world  ")
        assert terms == ["hello", "world"]
    
    def test_get_fuzzy_config(self, fuzzy_service):
        """Test getting fuzzy configuration by name"""
        strict_config = fuzzy_service.get_fuzzy_config("strict")
        assert strict_config.fuzziness == FuzzinessType.DISTANCE_1
        assert strict_config.prefix_length == 2
        assert strict_config.max_expansions == 10
        
        moderate_config = fuzzy_service.get_fuzzy_config("moderate")
        assert moderate_config.fuzziness == FuzzinessType.AUTO
        assert moderate_config.prefix_length == 1
        assert moderate_config.max_expansions == 50
        
        loose_config = fuzzy_service.get_fuzzy_config("loose")
        assert loose_config.fuzziness == FuzzinessType.DISTANCE_2
        assert loose_config.prefix_length == 0
        assert loose_config.max_expansions == 100
    
    def test_get_fuzzy_config_invalid_name(self, fuzzy_service):
        """Test getting fuzzy configuration with invalid name"""
        config = fuzzy_service.get_fuzzy_config("invalid")
        # Should return moderate config as default
        assert config.fuzziness == FuzzinessType.AUTO
    
    def test_estimate_fuzzy_performance_simple(self, fuzzy_service, sample_fuzzy_config):
        """Test performance estimation for simple query"""
        estimation = fuzzy_service.estimate_fuzzy_performance("test", sample_fuzzy_config)
        
        assert "complexity_score" in estimation
        assert "estimated_time_ms" in estimation
        assert "performance_impact" in estimation
        assert "recommendations" in estimation
        assert estimation["performance_impact"] in ["low", "moderate", "high"]
    
    def test_estimate_fuzzy_performance_complex(self, fuzzy_service, sample_fuzzy_config):
        """Test performance estimation for complex query"""
        complex_config = FuzzyConfig(
            fuzziness=FuzzinessType.DISTANCE_3,
            prefix_length=0,
            max_expansions=1000
        )
        estimation = fuzzy_service.estimate_fuzzy_performance(
            "very long complex query with many terms", 
            complex_config
        )
        
        assert estimation["complexity_score"] > 100
        assert estimation["performance_impact"] in ["moderate", "high"]
        assert len(estimation["recommendations"]) > 0
    
    def test_field_configurations(self, fuzzy_service):
        """Test field-specific configurations"""
        # Test that field configurations are properly set
        assert "name" in fuzzy_service.field_configs
        assert "title" in fuzzy_service.field_configs
        assert "description" in fuzzy_service.field_configs
        
        name_config = fuzzy_service.field_configs["name"]
        assert name_config.boost == 3.0
        assert name_config.fuzziness == FuzzinessType.AUTO
        
        tags_config = fuzzy_service.field_configs["tags"]
        assert tags_config.boost == 2.0
        assert tags_config.fuzziness == FuzzinessType.DISTANCE_1
    
    def test_performance_recommendations(self, fuzzy_service):
        """Test performance recommendations"""
        # Test low complexity
        recommendations = fuzzy_service._get_performance_recommendations(50)
        assert len(recommendations) == 0
        
        # Test moderate complexity
        recommendations = fuzzy_service._get_performance_recommendations(350)
        assert len(recommendations) > 0
        assert any("stricter fuzziness" in rec for rec in recommendations)
        
        # Test high complexity
        recommendations = fuzzy_service._get_performance_recommendations(600)
        assert len(recommendations) > 0
        assert any("wildcard or phrase" in rec for rec in recommendations)


@pytest.mark.asyncio
class TestFuzzySearchIntegration:
    """Test fuzzy search integration scenarios"""
    
    def test_typo_correction_scenarios(self, fuzzy_service):
        """Test various typo correction scenarios"""
        test_cases = [
            ("vidoe", "video"),
            ("documnet", "document"),
            ("imag", "image"),
            ("musci", "music"),
            ("photot", "photo")
        ]
        
        for typo, _ in test_cases:
            query = fuzzy_service.build_single_term_fuzzy_query(typo, "title")
            assert "fuzzy" in query
            assert query["fuzzy"]["title"]["value"] == typo
    
    def test_phrase_fuzzy_matching(self, fuzzy_service):
        """Test phrase fuzzy matching scenarios"""
        test_cases = [
            "test vidoe file",
            "documnet managment",
            "imag procesing",
            "musci productoin"
        ]
        
        for phrase in test_cases:
            query = fuzzy_service.build_fuzzy_phrase_query(phrase, ["title"])
            assert "span_near" in query
            assert len(query["span_near"]["clauses"]) == len(phrase.split())
    
    def test_cross_field_fuzzy_scenarios(self, fuzzy_service):
        """Test cross-field fuzzy matching scenarios"""
        test_cases = [
            "test video",
            "document management",
            "image processing",
            "music production"
        ]
        
        fields = ["title", "description", "tags"]
        
        for text in test_cases:
            query = fuzzy_service.build_cross_field_fuzzy_query(text, fields)
            assert "multi_match" in query
            assert query["multi_match"]["query"] == text
            assert query["multi_match"]["type"] == "cross_fields"
    
    def test_adaptive_matching_scenarios(self, fuzzy_service):
        """Test adaptive matching for different query types"""
        test_cases = [
            ("cat", FuzzyMatchType.SINGLE_TERM),  # Single short word
            ("video file", FuzzyMatchType.MULTI_TERM),  # Multiple words
            ('"exact phrase"', FuzzyMatchType.PHRASE),  # Quoted phrase
            ("test.mp4 video", FuzzyMatchType.MULTI_TERM),  # Technical terms
            ("configuration management system", FuzzyMatchType.MULTI_TERM)  # Long phrase
        ]
        
        for query_text, expected_type in test_cases:
            query = fuzzy_service.build_adaptive_fuzzy_query(query_text, ["title"])
            assert query is not None
            # The query structure depends on the adaptive logic
    
    def test_multilingual_fuzzy_support(self, fuzzy_service):
        """Test fuzzy matching with multilingual content"""
        # Note: This tests the structure, actual multilingual fuzzy matching
        # would require specific language analyzers in OpenSearch
        test_cases = [
            "café",
            "naïve",
            "résumé",
            "señor",
            "Müller"
        ]
        
        for term in test_cases:
            query = fuzzy_service.build_single_term_fuzzy_query(term, "title")
            assert "fuzzy" in query
            assert query["fuzzy"]["title"]["value"] == term
    
    def test_performance_vs_accuracy_tradeoffs(self, fuzzy_service):
        """Test different performance vs accuracy configurations"""
        configs = [
            ("strict", FuzzinessType.DISTANCE_1, 2, 10),
            ("moderate", FuzzinessType.AUTO, 1, 50),
            ("loose", FuzzinessType.DISTANCE_2, 0, 100)
        ]
        
        for config_name, expected_fuzziness, expected_prefix, expected_expansions in configs:
            config = fuzzy_service.get_fuzzy_config(config_name)
            assert config.fuzziness == expected_fuzziness
            assert config.prefix_length == expected_prefix
            assert config.max_expansions == expected_expansions
    
    def test_field_specific_fuzzy_configurations(self, fuzzy_service):
        """Test field-specific fuzzy configurations"""
        # Test that different fields have appropriate configurations
        field_tests = [
            ("name", 3.0, FuzzinessType.AUTO),
            ("tags", 2.0, FuzzinessType.DISTANCE_1),
            ("content", 1.0, FuzzinessType.AUTO)
        ]
        
        for field, expected_boost, expected_fuzziness in field_tests:
            if field in fuzzy_service.field_configs:
                config = fuzzy_service.field_configs[field]
                assert config.boost == expected_boost
                assert config.fuzziness == expected_fuzziness
    
    def test_suggestion_query_generation(self, fuzzy_service):
        """Test fuzzy suggestion query generation"""
        suggestion_query = fuzzy_service.build_fuzzy_suggestion_query(
            "test", 
            "title", 
            5
        )
        
        assert "suggest" in suggestion_query
        assert suggestion_query["suggest"]["text"] == "test"
        
        fuzzy_suggest = suggestion_query["suggest"]["fuzzy_suggest"]
        assert fuzzy_suggest["term"]["field"] == "title"
        assert fuzzy_suggest["term"]["size"] == 5
        assert fuzzy_suggest["term"]["max_edits"] == 2
        assert fuzzy_suggest["term"]["suggest_mode"] == "popular"


@pytest.mark.asyncio
class TestFuzzySearchEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_query_handling(self, fuzzy_service):
        """Test handling of empty queries"""
        analysis = fuzzy_service._analyze_query("")
        assert analysis["word_count"] == 0
        assert analysis["avg_word_length"] == 0
        assert analysis["terms"] == []
    
    def test_very_long_query_handling(self, fuzzy_service):
        """Test handling of very long queries"""
        long_query = " ".join(["word"] * 100)
        analysis = fuzzy_service._analyze_query(long_query)
        assert analysis["word_count"] == 100
        assert len(analysis["terms"]) == 100
    
    def test_special_characters_handling(self, fuzzy_service):
        """Test handling of special characters"""
        special_queries = [
            "test@example.com",
            "file-name_with_underscores",
            "query with (parentheses)",
            "query with [brackets]",
            "query with {braces}"
        ]
        
        for query in special_queries:
            analysis = fuzzy_service._analyze_query(query)
            assert analysis["has_special_chars"] == True
    
    def test_numeric_content_handling(self, fuzzy_service):
        """Test handling of numeric content"""
        numeric_queries = [
            "1080p",
            "60fps",
            "4K",
            "2023",
            "version 1.2.3"
        ]
        
        for query in numeric_queries:
            analysis = fuzzy_service._analyze_query(query)
            # Should be able to analyze numeric content
            assert analysis["word_count"] > 0
    
    def test_mixed_case_handling(self, fuzzy_service):
        """Test handling of mixed case queries"""
        mixed_case_queries = [
            "Test Video",
            "DOCUMENT",
            "CamelCase",
            "snake_case",
            "PascalCase"
        ]
        
        for query in mixed_case_queries:
            fuzzy_query = fuzzy_service.build_single_term_fuzzy_query(query, "title")
            assert "fuzzy" in fuzzy_query
            assert fuzzy_query["fuzzy"]["title"]["value"] == query
    
    def test_whitespace_handling(self, fuzzy_service):
        """Test handling of various whitespace scenarios"""
        whitespace_queries = [
            "  test  video  ",
            "\ttest\tvideo\t",
            "test\nvideo",
            "test\r\nvideo"
        ]
        
        for query in whitespace_queries:
            terms = fuzzy_service._tokenize_phrase(query)
            assert terms == ["test", "video"]
    
    def test_unicode_handling(self, fuzzy_service):
        """Test handling of unicode characters"""
        unicode_queries = [
            "café",
            "naïve",
            "résumé",
            "中文",
            "العربية"
        ]
        
        for query in unicode_queries:
            fuzzy_query = fuzzy_service.build_single_term_fuzzy_query(query, "title")
            assert "fuzzy" in fuzzy_query
            assert fuzzy_query["fuzzy"]["title"]["value"] == query
    
    def test_performance_edge_cases(self, fuzzy_service):
        """Test performance estimation edge cases"""
        edge_cases = [
            ("", FuzzyConfig()),  # Empty query
            ("a", FuzzyConfig()),  # Single character
            ("a" * 1000, FuzzyConfig()),  # Very long term
        ]
        
        for query, config in edge_cases:
            estimation = fuzzy_service.estimate_fuzzy_performance(query, config)
            assert "complexity_score" in estimation
            assert "performance_impact" in estimation
            assert estimation["estimated_time_ms"] >= 0
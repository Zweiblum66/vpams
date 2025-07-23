"""
Unit tests for synonym search functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.services.synonym_service import SynonymService, SynonymExpander
from src.models.schemas import (
    SynonymType, SynonymExpansionStrategy, SynonymConfig, SynonymSearchQuery,
    SynonymSearchResponse, SynonymSuggestionQuery, SynonymSuggestionResponse,
    IndexType, SortOrder, SearchHit
)


class TestSynonymExpander:
    """Test the SynonymExpander class"""
    
    def test_init(self):
        """Test SynonymExpander initialization"""
        expander = SynonymExpander()
        assert expander is not None
        assert expander.synonym_cache == {}
        assert expander.cache_ttl == 3600
    
    def test_clean_token(self):
        """Test token cleaning"""
        expander = SynonymExpander()
        
        # Test basic cleaning
        assert expander._clean_token("Hello!") == "hello"
        assert expander._clean_token("Test123") == "test123"
        assert expander._clean_token("  Word  ") == "word"
        assert expander._clean_token("multi-word") == "multiword"
        assert expander._clean_token("") == ""
    
    def test_is_valid_token(self):
        """Test token validation"""
        expander = SynonymExpander()
        
        # Valid tokens
        assert expander._is_valid_token("video") is True
        assert expander._is_valid_token("test") is True
        assert expander._is_valid_token("content") is True
        
        # Invalid tokens
        assert expander._is_valid_token("") is False
        assert expander._is_valid_token("a") is False
        assert expander._is_valid_token("123") is False
        assert expander._is_valid_token("the") is False  # stopword
        assert expander._is_valid_token("and") is False  # stopword
    
    def test_get_cache_key(self):
        """Test cache key generation"""
        expander = SynonymExpander()
        
        key1 = expander._get_cache_key("video", SynonymType.WORDNET)
        key2 = expander._get_cache_key("video", SynonymType.WORDNET, "media")
        key3 = expander._get_cache_key("audio", SynonymType.CUSTOM)
        
        assert key1 == "video:wordnet:default"
        assert key2 == "video:wordnet:media"
        assert key3 == "audio:custom:default"
        assert key1 != key2
        assert key1 != key3
    
    def test_get_explicit_synonyms(self):
        """Test explicit synonym retrieval"""
        expander = SynonymExpander()
        
        # Test known synonyms
        video_synonyms = expander._get_explicit_synonyms("video")
        assert "movie" in video_synonyms
        assert "film" in video_synonyms
        assert "clip" in video_synonyms
        
        audio_synonyms = expander._get_explicit_synonyms("audio")
        assert "sound" in audio_synonyms
        assert "music" in audio_synonyms
        
        # Test unknown word
        unknown_synonyms = expander._get_explicit_synonyms("unknown")
        assert unknown_synonyms == []
    
    def test_get_custom_synonyms(self):
        """Test custom synonym retrieval"""
        expander = SynonymExpander()
        
        custom_dict = {
            "video": ["movie", "film", "clip"],
            "audio": ["sound", "music", "voice"],
            "Document": ["file", "text"]  # Test case insensitive
        }
        
        # Test direct lookup
        synonyms = expander._get_custom_synonyms("video", custom_dict)
        assert synonyms == ["movie", "film", "clip"]
        
        # Test case insensitive lookup
        synonyms = expander._get_custom_synonyms("document", custom_dict)
        assert synonyms == ["file", "text"]
        
        # Test unknown word
        synonyms = expander._get_custom_synonyms("unknown", custom_dict)
        assert synonyms == []
    
    def test_calculate_similarity(self):
        """Test similarity calculation"""
        expander = SynonymExpander()
        
        # Test identical terms
        assert expander._calculate_similarity("video", "video") == 1.0
        
        # Test similar terms
        sim1 = expander._calculate_similarity("video", "audio")
        sim2 = expander._calculate_similarity("test", "text")
        assert 0.0 < sim1 < 1.0
        assert 0.0 < sim2 < 1.0
        
        # Test completely different terms
        sim3 = expander._calculate_similarity("abc", "xyz")
        assert sim3 == 0.0
    
    def test_filter_by_similarity(self):
        """Test synonym filtering by similarity"""
        expander = SynonymExpander()
        
        synonyms = ["movie", "film", "clip", "xyz"]
        filtered = expander._filter_by_similarity("video", synonyms, 0.3)
        
        # Should filter out very dissimilar terms
        assert len(filtered) <= len(synonyms)
        assert "xyz" not in filtered or expander._calculate_similarity("video", "xyz") >= 0.3
    
    def test_estimate_domain(self):
        """Test domain estimation"""
        expander = SynonymExpander()
        
        # Test media domain
        assert expander._estimate_domain("video editing software") == "media"
        assert expander._estimate_domain("audio music file") == "media"
        
        # Test broadcast domain
        assert expander._estimate_domain("breaking news report") == "broadcast"
        assert expander._estimate_domain("live interview broadcast") == "broadcast"
        
        # Test production domain
        assert expander._estimate_domain("edit cut render timeline") == "production"
        assert expander._estimate_domain("shot scene effect") == "production"
        
        # Test general domain
        assert expander._estimate_domain("random text query") == "general"
    
    def test_get_synonyms_explicit(self):
        """Test explicit synonym retrieval"""
        expander = SynonymExpander()
        config = SynonymConfig(
            synonym_type=SynonymType.EXPLICIT,
            max_synonyms_per_term=5,
            enable_caching=False
        )
        
        synonyms, source = expander.get_synonyms("video", SynonymType.EXPLICIT, config)
        
        assert source == "explicit"
        assert len(synonyms) <= 5
        assert "movie" in synonyms or "film" in synonyms
    
    def test_get_synonyms_custom(self):
        """Test custom synonym retrieval"""
        expander = SynonymExpander()
        config = SynonymConfig(
            synonym_type=SynonymType.CUSTOM,
            max_synonyms_per_term=3,
            enable_caching=False,
            custom_synonyms={"video": ["movie", "film", "clip", "footage"]}
        )
        
        synonyms, source = expander.get_synonyms("video", SynonymType.CUSTOM, config)
        
        assert source == "custom"
        assert len(synonyms) <= 3
        assert all(syn in ["movie", "film", "clip", "footage"] for syn in synonyms)
    
    def test_get_synonyms_contextual(self):
        """Test contextual synonym retrieval"""
        expander = SynonymExpander()
        config = SynonymConfig(
            synonym_type=SynonymType.CONTEXTUAL,
            max_synonyms_per_term=5,
            enable_caching=False,
            domain_context="media"
        )
        
        synonyms, source = expander.get_synonyms("video", SynonymType.CONTEXTUAL, config)
        
        assert source == "domain"
        assert len(synonyms) <= 5
    
    def test_get_synonyms_hybrid(self):
        """Test hybrid synonym retrieval"""
        expander = SynonymExpander()
        config = SynonymConfig(
            synonym_type=SynonymType.HYBRID,
            max_synonyms_per_term=5,
            enable_caching=False,
            custom_synonyms={"video": ["movie", "film"]},
            domain_context="media"
        )
        
        synonyms, source = expander.get_synonyms("video", SynonymType.HYBRID, config)
        
        assert source == "hybrid"
        assert len(synonyms) <= 5
    
    def test_get_synonyms_invalid_token(self):
        """Test synonym retrieval with invalid token"""
        expander = SynonymExpander()
        config = SynonymConfig(enable_caching=False)
        
        synonyms, source = expander.get_synonyms("a", SynonymType.EXPLICIT, config)
        
        assert synonyms == []
        assert source == "invalid_token"
    
    def test_expand_query_basic(self):
        """Test basic query expansion"""
        expander = SynonymExpander()
        config = SynonymConfig(
            synonym_type=SynonymType.EXPLICIT,
            expansion_strategy=SynonymExpansionStrategy.EXPAND,
            max_synonyms_per_term=3,
            enable_caching=False
        )
        
        expanded_query, expansions = expander.expand_query("video content", config)
        
        assert isinstance(expanded_query, str)
        assert isinstance(expansions, list)
        assert len(expansions) <= 2  # Maximum 2 terms in query
    
    def test_expand_query_replace_strategy(self):
        """Test query expansion with replace strategy"""
        expander = SynonymExpander()
        config = SynonymConfig(
            synonym_type=SynonymType.EXPLICIT,
            expansion_strategy=SynonymExpansionStrategy.REPLACE,
            max_synonyms_per_term=3,
            enable_caching=False
        )
        
        expanded_query, expansions = expander.expand_query("video", config)
        
        assert isinstance(expanded_query, str)
        assert "video" not in expanded_query.lower() or expansions == []
    
    def test_expand_query_boost_strategy(self):
        """Test query expansion with boost strategy"""
        expander = SynonymExpander()
        config = SynonymConfig(
            synonym_type=SynonymType.EXPLICIT,
            expansion_strategy=SynonymExpansionStrategy.BOOST,
            max_synonyms_per_term=3,
            boost_original_terms=2.0,
            boost_synonyms=1.5,
            enable_caching=False
        )
        
        expanded_query, expansions = expander.expand_query("video", config)
        
        assert isinstance(expanded_query, str)
        assert "^2.0" in expanded_query or "^1.5" in expanded_query or expansions == []
    
    def test_expand_query_fallback_strategy(self):
        """Test query expansion with fallback strategy"""
        expander = SynonymExpander()
        config = SynonymConfig(
            synonym_type=SynonymType.EXPLICIT,
            expansion_strategy=SynonymExpansionStrategy.FALLBACK,
            max_synonyms_per_term=3,
            enable_caching=False
        )
        
        expanded_query, expansions = expander.expand_query("video", config)
        
        assert isinstance(expanded_query, str)
        assert isinstance(expansions, list)
    
    def test_caching_functionality(self):
        """Test synonym caching"""
        expander = SynonymExpander()
        config = SynonymConfig(
            synonym_type=SynonymType.EXPLICIT,
            enable_caching=True,
            cache_ttl_seconds=3600
        )
        
        # First call
        synonyms1, source1 = expander.get_synonyms("video", SynonymType.EXPLICIT, config)
        
        # Second call (should hit cache)
        synonyms2, source2 = expander.get_synonyms("video", SynonymType.EXPLICIT, config)
        
        assert synonyms1 == synonyms2
        # Note: source might be different due to caching behavior


class TestSynonymService:
    """Test the SynonymService class"""
    
    @pytest.fixture
    def mock_opensearch_client(self):
        """Create mock OpenSearch client"""
        client = AsyncMock()
        client.search.return_value = {
            "hits": {
                "total": {"value": 2},
                "max_score": 1.5,
                "hits": [
                    {
                        "_id": "doc1",
                        "_index": "test_index",
                        "_score": 1.5,
                        "_source": {"title": "Test Video", "description": "A test video file"},
                        "highlight": {"title": ["Test <mark>Video</mark>"]}
                    },
                    {
                        "_id": "doc2",
                        "_index": "test_index",
                        "_score": 1.0,
                        "_source": {"title": "Test Movie", "description": "A test movie file"},
                        "highlight": {"title": ["Test <mark>Movie</mark>"]}
                    }
                ]
            },
            "timed_out": False
        }
        return client
    
    @pytest.fixture
    def synonym_service(self, mock_opensearch_client):
        """Create SynonymService instance"""
        return SynonymService(mock_opensearch_client)
    
    @pytest.mark.asyncio
    async def test_synonym_search_basic(self, synonym_service):
        """Test basic synonym search"""
        query = SynonymSearchQuery(
            query="video content",
            size=10
        )
        
        result = await synonym_service.synonym_search(query)
        
        assert isinstance(result, SynonymSearchResponse)
        assert result.query == "video content"
        assert result.total_hits == 2
        assert len(result.hits) == 2
        assert result.max_score == 1.5
    
    @pytest.mark.asyncio
    async def test_synonym_search_with_config(self, synonym_service):
        """Test synonym search with custom config"""
        config = SynonymConfig(
            synonym_type=SynonymType.CUSTOM,
            expansion_strategy=SynonymExpansionStrategy.EXPAND,
            max_synonyms_per_term=5,
            custom_synonyms={"video": ["movie", "film", "clip"]}
        )
        
        query = SynonymSearchQuery(
            query="video content",
            synonym_config=config,
            size=10
        )
        
        result = await synonym_service.synonym_search(query)
        
        assert isinstance(result, SynonymSearchResponse)
        assert result.query == "video content"
        assert result.total_hits == 2
    
    @pytest.mark.asyncio
    async def test_synonym_search_with_analysis(self, synonym_service):
        """Test synonym search with analysis enabled"""
        query = SynonymSearchQuery(
            query="video content",
            include_synonym_analysis=True,
            size=10
        )
        
        result = await synonym_service.synonym_search(query)
        
        assert isinstance(result, SynonymSearchResponse)
        assert result.synonym_analysis is not None
        assert result.synonym_analysis.original_query == "video content"
        assert isinstance(result.synonym_analysis.term_expansions, list)
    
    @pytest.mark.asyncio
    async def test_synonym_search_with_filters(self, synonym_service):
        """Test synonym search with filters"""
        from src.models.schemas import FilterCondition, FilterType
        
        filters = [
            FilterCondition(
                field="asset_type",
                type=FilterType.TERM,
                value="video"
            )
        ]
        
        query = SynonymSearchQuery(
            query="video content",
            filters=filters,
            size=10
        )
        
        result = await synonym_service.synonym_search(query)
        
        assert isinstance(result, SynonymSearchResponse)
        assert result.total_hits == 2
    
    @pytest.mark.asyncio
    async def test_synonym_search_pagination(self, synonym_service):
        """Test synonym search with pagination"""
        query = SynonymSearchQuery(
            query="video content",
            size=5,
            from_=10
        )
        
        result = await synonym_service.synonym_search(query)
        
        assert isinstance(result, SynonymSearchResponse)
        assert result.per_page == 5
        assert result.page == 3  # (10 / 5) + 1
    
    @pytest.mark.asyncio
    async def test_synonym_search_sorting(self, synonym_service):
        """Test synonym search with sorting"""
        query = SynonymSearchQuery(
            query="video content",
            sort_by="created_at",
            sort_order=SortOrder.ASC,
            size=10
        )
        
        result = await synonym_service.synonym_search(query)
        
        assert isinstance(result, SynonymSearchResponse)
        assert result.total_hits == 2
    
    @pytest.mark.asyncio
    async def test_get_synonym_suggestions(self, synonym_service):
        """Test synonym suggestions"""
        query = SynonymSuggestionQuery(
            term="video",
            synonym_type=SynonymType.EXPLICIT,
            size=5
        )
        
        result = await synonym_service.get_synonym_suggestions(query)
        
        assert isinstance(result, SynonymSuggestionResponse)
        assert result.term == "video"
        assert isinstance(result.synonyms, list)
        assert len(result.synonyms) <= 5
    
    @pytest.mark.asyncio
    async def test_get_synonym_suggestions_with_domain(self, synonym_service):
        """Test synonym suggestions with domain context"""
        query = SynonymSuggestionQuery(
            term="video",
            synonym_type=SynonymType.CONTEXTUAL,
            domain_context="media",
            size=5
        )
        
        result = await synonym_service.get_synonym_suggestions(query)
        
        assert isinstance(result, SynonymSuggestionResponse)
        assert result.term == "video"
        assert result.metadata["domain_context"] == "media"
    
    @pytest.mark.asyncio
    async def test_get_synonym_suggestions_with_similarity(self, synonym_service):
        """Test synonym suggestions with similarity threshold"""
        query = SynonymSuggestionQuery(
            term="video",
            synonym_type=SynonymType.EXPLICIT,
            min_similarity=0.8,
            size=5
        )
        
        result = await synonym_service.get_synonym_suggestions(query)
        
        assert isinstance(result, SynonymSuggestionResponse)
        assert result.metadata["min_similarity"] == 0.8
        
        # Check that all suggestions meet similarity threshold
        for suggestion in result.synonyms:
            assert suggestion.similarity_score >= 0.8
    
    @pytest.mark.asyncio
    async def test_get_synonym_stats(self, synonym_service):
        """Test synonym statistics"""
        result = await synonym_service.get_synonym_stats()
        
        assert isinstance(result, SynonymStats)
        assert result.total_synonyms > 0
        assert result.total_terms > 0
        assert result.avg_synonyms_per_term > 0
        assert isinstance(result.most_common_domains, list)
        assert isinstance(result.synonym_usage_stats, dict)
        assert isinstance(result.cache_stats, dict)
        assert isinstance(result.performance_metrics, dict)
    
    def test_get_index_names(self, synonym_service):
        """Test index name resolution"""
        # Test individual indices
        indices = [IndexType.ASSETS]
        result = synonym_service._get_index_names(indices)
        assert "assets" in result
        
        # Test all indices
        indices = [IndexType.ALL]
        result = synonym_service._get_index_names(indices)
        assert "," in result  # Should be comma-separated
    
    def test_analyze_matches(self, synonym_service):
        """Test match analysis"""
        hits = [
            SearchHit(
                id="doc1",
                index="test_index",
                score=1.5,
                source={"title": "Test Video", "description": "A test video file"}
            ),
            SearchHit(
                id="doc2",
                index="test_index",
                score=1.0,
                source={"title": "Test Movie", "description": "A test movie file"}
            )
        ]
        
        from src.models.schemas import SynonymExpansion, SynonymType
        expansions = [
            SynonymExpansion(
                original_term="video",
                synonyms=["movie", "film"],
                synonym_type=SynonymType.EXPLICIT,
                source="explicit"
            )
        ]
        
        original_matches, synonym_matches, hybrid_matches = synonym_service._analyze_matches(
            hits, "video", expansions
        )
        
        assert original_matches >= 0
        assert synonym_matches >= 0
        assert hybrid_matches >= 0
        assert original_matches + synonym_matches + hybrid_matches == len(hits)
    
    def test_analyze_query_characteristics(self, synonym_service):
        """Test query characteristics analysis"""
        characteristics = synonym_service._analyze_query_characteristics("video editing software")
        
        assert isinstance(characteristics, dict)
        assert "word_count" in characteristics
        assert "avg_word_length" in characteristics
        assert "has_numbers" in characteristics
        assert "has_special_chars" in characteristics
        assert "unique_words" in characteristics
        assert "query_length" in characteristics
        assert "estimated_domain" in characteristics
        
        assert characteristics["word_count"] == 3
        assert characteristics["estimated_domain"] in ["media", "production", "general"]
    
    def test_build_synonym_search_body(self, synonym_service):
        """Test search body building"""
        from src.models.schemas import SynonymConfig, SynonymExpansionStrategy
        
        config = SynonymConfig(
            expansion_strategy=SynonymExpansionStrategy.EXPAND,
            boost_original_terms=2.0,
            boost_synonyms=1.5
        )
        
        query = SynonymSearchQuery(
            query="video content",
            synonym_config=config,
            size=10,
            from_=0
        )
        
        search_body = synonym_service._build_synonym_search_body(
            original_query="video content",
            expanded_query="video content (movie film)",
            config=config,
            query_params=query
        )
        
        assert isinstance(search_body, dict)
        assert "query" in search_body
        assert "size" in search_body
        assert "from" in search_body
        assert search_body["size"] == 10
        assert search_body["from"] == 0
    
    @pytest.mark.asyncio
    async def test_synonym_search_error_handling(self, synonym_service):
        """Test synonym search error handling"""
        # Make the client raise an exception
        synonym_service.opensearch_client.search.side_effect = Exception("Search failed")
        
        query = SynonymSearchQuery(
            query="video content",
            size=10
        )
        
        with pytest.raises(Exception):
            await synonym_service.synonym_search(query)
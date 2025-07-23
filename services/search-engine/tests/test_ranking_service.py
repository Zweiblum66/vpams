"""
Tests for Search Result Ranking Service
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.services.ranking_service import RankingService
from src.models.schemas import SearchHit, RankingConfig, RankingType


@pytest.fixture
def ranking_service():
    """Create ranking service instance"""
    return RankingService()


@pytest.fixture
def sample_hits():
    """Create sample search hits for testing"""
    now = datetime.utcnow()
    
    return [
        SearchHit(
            id="hit1",
            index="mams_assets",
            score=2.5,
            source={
                "asset_id": "asset1",
                "name": "Important Video",
                "title": "Important Video Production",
                "description": "A critical video for testing",
                "asset_type": "video",
                "created_at": now.isoformat() + "Z",
                "view_count": 1000,
                "download_count": 50,
                "tags": ["important", "video", "test"]
            }
        ),
        SearchHit(
            id="hit2",
            index="mams_assets",
            score=1.8,
            source={
                "asset_id": "asset2",
                "name": "Recent Image",
                "description": "A recently uploaded image",
                "asset_type": "image",
                "created_at": (now - timedelta(days=2)).isoformat() + "Z",
                "view_count": 100,
                "download_count": 5,
                "tags": ["recent", "image"]
            }
        ),
        SearchHit(
            id="hit3",
            index="mams_metadata",
            score=3.0,
            source={
                "asset_id": "asset3",
                "title": "Old Document",
                "description": "An older document with high relevance",
                "asset_type": "document",
                "created_at": (now - timedelta(days=60)).isoformat() + "Z",
                "view_count": 5000,
                "download_count": 200,
                "rating": 4.5,
                "rating_count": 20
            }
        ),
        SearchHit(
            id="hit4",
            index="mams_content",
            score=1.2,
            source={
                "asset_id": "asset4",
                "content": "Text content from audio transcription",
                "asset_type": "audio",
                "created_at": (now - timedelta(days=30)).isoformat() + "Z",
                "view_count": 300,
                "metadata": {"duration": "00:05:30"},
                "thumbnail_path": "/thumbnails/asset4.jpg",
                "proxy_paths": ["/proxies/asset4_low.mp3"]
            }
        )
    ]


@pytest.mark.asyncio
async def test_rank_by_relevance(ranking_service, sample_hits):
    """Test ranking by relevance score"""
    config = RankingConfig(ranking_type=RankingType.RELEVANCE)
    
    ranked = await ranking_service.rank_results(sample_hits, "test query", config)
    
    # Should be sorted by score descending
    assert ranked[0].id == "hit3"  # score: 3.0
    assert ranked[1].id == "hit1"  # score: 2.5
    assert ranked[2].id == "hit2"  # score: 1.8
    assert ranked[3].id == "hit4"  # score: 1.2


@pytest.mark.asyncio
async def test_rank_by_recency(ranking_service, sample_hits):
    """Test ranking by recency"""
    config = RankingConfig(ranking_type=RankingType.RECENCY)
    
    ranked = await ranking_service.rank_results(sample_hits, "test query", config)
    
    # Should be sorted by creation date descending
    assert ranked[0].id == "hit1"  # today
    assert ranked[1].id == "hit2"  # 2 days ago
    assert ranked[2].id == "hit4"  # 30 days ago
    assert ranked[3].id == "hit3"  # 60 days ago


@pytest.mark.asyncio
async def test_rank_by_popularity(ranking_service, sample_hits):
    """Test ranking by popularity"""
    config = RankingConfig(ranking_type=RankingType.POPULARITY)
    
    ranked = await ranking_service.rank_results(sample_hits, "test query", config)
    
    # hit3 has highest combined popularity (5000 views + 200 downloads + ratings)
    assert ranked[0].id == "hit3"
    # Verify popularity scores were calculated
    assert hasattr(ranked[0], '_popularity_score')


@pytest.mark.asyncio
async def test_rank_by_hybrid(ranking_service, sample_hits):
    """Test hybrid ranking combining multiple factors"""
    config = RankingConfig(
        ranking_type=RankingType.HYBRID,
        hybrid_weights={
            "relevance": 1.0,
            "recency": 0.5,
            "popularity": 0.3,
            "quality": 0.2
        }
    )
    
    ranked = await ranking_service.rank_results(sample_hits, "test query", config)
    
    # Verify hybrid scores were calculated
    assert all(hasattr(hit, '_hybrid_score') for hit in ranked)
    assert all(hasattr(hit, '_ranking_factors') for hit in ranked)
    
    # Check that ranking factors are present
    factors = ranked[0]._ranking_factors
    assert 'relevance' in factors
    assert 'recency' in factors
    assert 'popularity' in factors
    assert 'quality' in factors
    assert 'final_score' in factors


@pytest.mark.asyncio
async def test_rank_by_custom(ranking_service, sample_hits):
    """Test custom ranking with field boosts and asset type preferences"""
    config = RankingConfig(
        ranking_type=RankingType.CUSTOM,
        field_boosts={
            "title": 3.0,
            "description": 1.5,
            "tags": 2.0
        },
        asset_type_boosts={
            "video": 2.0,
            "image": 1.5,
            "audio": 1.0,
            "document": 0.8
        },
        custom_weights={
            "field_boost": 1.0,
            "asset_type": 0.5,
            "quality": 0.3
        }
    )
    
    ranked = await ranking_service.rank_results(sample_hits, "video test", config)
    
    # Verify custom scores were calculated
    assert all(hasattr(hit, '_custom_score') for hit in ranked)
    assert all(hasattr(hit, '_score_components') for hit in ranked)
    
    # hit1 should rank high due to video asset type and title match
    assert ranked[0].id == "hit1"


@pytest.mark.asyncio
async def test_empty_hits_list(ranking_service):
    """Test ranking with empty hits list"""
    config = RankingConfig()
    
    ranked = await ranking_service.rank_results([], "test query", config)
    
    assert ranked == []


@pytest.mark.asyncio
async def test_recency_with_missing_dates(ranking_service):
    """Test recency ranking with missing date fields"""
    hits = [
        SearchHit(
            id="no_date",
            index="mams_assets",
            score=1.0,
            source={"title": "No date"}
        ),
        SearchHit(
            id="with_date",
            index="mams_assets",
            score=1.0,
            source={
                "title": "With date",
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
        )
    ]
    
    config = RankingConfig(ranking_type=RankingType.RECENCY)
    ranked = await ranking_service.rank_results(hits, "test", config)
    
    # Hit with date should rank higher
    assert ranked[0].id == "with_date"
    assert ranked[1].id == "no_date"


@pytest.mark.asyncio
async def test_ranking_explanation(ranking_service, sample_hits):
    """Test getting ranking explanations"""
    config = RankingConfig(ranking_type=RankingType.HYBRID)
    
    ranked = await ranking_service.rank_results(sample_hits, "test query", config)
    
    # Get explanation for first result
    explanation = ranking_service.get_ranking_explanation(ranked[0])
    
    assert 'original_score' in explanation
    assert 'id' in explanation
    assert 'index' in explanation
    assert 'factors' in explanation
    assert 'hybrid_score' in explanation


@pytest.mark.asyncio
async def test_quality_score_calculation(ranking_service):
    """Test quality score calculation based on content indicators"""
    hits = [
        SearchHit(
            id="high_quality",
            index="mams_assets",
            score=1.0,
            source={
                "title": "High Quality Asset",
                "metadata": {"width": 1920, "height": 1080, "codec": "h264"},
                "thumbnail_path": "/thumb.jpg",
                "proxy_paths": ["/proxy.mp4"],
                "transcript": "Full transcript text",
                "file_size": 500_000_000  # 500MB
            }
        ),
        SearchHit(
            id="low_quality",
            index="mams_assets",
            score=1.0,
            source={
                "title": "Low Quality Asset",
                "file_size": 1_000_000  # 1MB
            }
        )
    ]
    
    config = RankingConfig(ranking_type=RankingType.CUSTOM)
    ranked = await ranking_service.rank_results(hits, "quality", config)
    
    # High quality asset should rank higher
    assert ranked[0].id == "high_quality"
    assert ranked[0]._score_components['quality'] > ranked[1]._score_components['quality']


@pytest.mark.asyncio
async def test_field_boost_scoring(ranking_service):
    """Test field boost scoring based on query term matches"""
    hits = [
        SearchHit(
            id="title_match",
            index="mams_assets",
            score=1.0,
            source={
                "title": "Important video production",
                "description": "Some description"
            }
        ),
        SearchHit(
            id="description_match",
            index="mams_assets",
            score=1.0,
            source={
                "title": "Some title",
                "description": "Important video content here"
            }
        ),
        SearchHit(
            id="tag_match",
            index="mams_assets",
            score=1.0,
            source={
                "title": "Another title",
                "description": "Another description",
                "tags": ["important", "video"]
            }
        )
    ]
    
    config = RankingConfig(
        ranking_type=RankingType.CUSTOM,
        field_boosts={
            "title": 3.0,
            "description": 1.0,
            "tags": 2.0
        }
    )
    
    ranked = await ranking_service.rank_results(hits, "important video", config)
    
    # Title match should score highest due to boost
    assert ranked[0].id == "title_match"


@pytest.mark.asyncio
async def test_preserve_explicit_sort(ranking_service, sample_hits):
    """Test that explicit sorting is preserved when sort_by is specified"""
    # This test would be in the search service, but including here for completeness
    # When sort_by is specified, ranking service should not be applied
    pass


@pytest.mark.asyncio
async def test_custom_recency_decay(ranking_service, sample_hits):
    """Test custom recency decay parameter"""
    # Fast decay (7 days)
    config_fast = RankingConfig(
        ranking_type=RankingType.RECENCY,
        recency_decay_days=7
    )
    
    # Slow decay (90 days)
    config_slow = RankingConfig(
        ranking_type=RankingType.RECENCY,
        recency_decay_days=90
    )
    
    ranked_fast = await ranking_service.rank_results(sample_hits.copy(), "test", config_fast)
    ranked_slow = await ranking_service.rank_results(sample_hits.copy(), "test", config_slow)
    
    # With fast decay, older items should have much lower scores
    # With slow decay, the difference should be smaller
    fast_scores = [hit._recency_score for hit in ranked_fast]
    slow_scores = [hit._recency_score for hit in ranked_slow]
    
    # The difference between newest and oldest should be greater with fast decay
    fast_diff = fast_scores[0] - fast_scores[-1]
    slow_diff = slow_scores[0] - slow_scores[-1]
    
    assert fast_diff > slow_diff
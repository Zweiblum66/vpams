"""
Tests for User Behavior Tracking Service

This module contains comprehensive tests for the behavior tracking functionality.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.behavior_tracker import (
    BehaviorTracker, UserSegment, ActivityLevel, BehaviorPattern, UserJourney
)
from src.models.analytics import UserBehavior, Event, EventType


@pytest.fixture
def behavior_tracker():
    """Create a behavior tracker instance for testing."""
    return BehaviorTracker()


@pytest.fixture
async def mock_db():
    """Create a mock database session."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def sample_user_behavior():
    """Create sample user behavior data."""
    return UserBehavior(
        user_id="test-user-123",
        period_start=datetime.utcnow() - timedelta(days=7),
        period_end=datetime.utcnow(),
        period_type="weekly",
        sessions_count=25,
        total_time_minutes=480,
        page_views=150,
        actions_count=75,
        assets_viewed=30,
        assets_uploaded=5,
        assets_downloaded=10,
        searches_performed=20,
        workflows_created=2,
        workflows_executed=8,
        bounce_rate=0.15,
        avg_session_duration=19.2,
        features_used=["search", "upload", "download", "workflow"],
        user_segment=UserSegment.POWER_USER,
        activity_level=ActivityLevel.HIGH
    )


class TestBehaviorTracker:
    """Test cases for the BehaviorTracker class."""
    
    @pytest.mark.asyncio
    async def test_track_user_action(self, behavior_tracker, mock_db):
        """Test tracking a user action."""
        user_id = "test-user-123"
        session_id = "session-456"
        action = "asset_upload"
        context = {"asset_id": "asset-789", "file_size": 1024000}
        
        await behavior_tracker.track_user_action(user_id, session_id, action, context, mock_db)
        
        # Verify event was added to database
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        
        # Check the event object
        event_call = mock_db.add.call_args[0][0]
        assert isinstance(event_call, Event)
        assert event_call.event_type == EventType.USER_ACTION
        assert event_call.event_name == action
        assert event_call.user_id == user_id
        assert event_call.session_id == session_id
        assert event_call.properties == context
    
    @pytest.mark.asyncio
    async def test_track_user_action_with_redis_update(self, behavior_tracker, mock_db):
        """Test tracking user action updates Redis cache."""
        with patch.object(behavior_tracker, '_get_redis') as mock_redis_getter:
            mock_redis = AsyncMock()
            mock_redis_getter.return_value = mock_redis
            
            user_id = "test-user-123"
            session_id = "session-456"
            action = "search"
            context = {"feature": "advanced_search", "query": "test video"}
            
            await behavior_tracker.track_user_action(user_id, session_id, action, context, mock_db)
            
            # Verify Redis calls
            mock_redis.hincrby.assert_any_call(f"user_behavior:{user_id}", "total_actions", 1)
            mock_redis.hincrby.assert_any_call(f"user_behavior:{user_id}", f"action:{action}", 1)
            mock_redis.hincrby.assert_any_call(f"user_behavior:{user_id}", "feature:advanced_search", 1)
            mock_redis.hset.assert_called()
            mock_redis.expire.assert_called_with(f"user_behavior:{user_id}", 86400 * 7)
    
    @pytest.mark.asyncio
    async def test_determine_user_segment_power_user(self, behavior_tracker, sample_user_behavior):
        """Test user segmentation for power users."""
        sample_user_behavior.sessions_count = 35
        sample_user_behavior.total_time_minutes = 800
        sample_user_behavior.actions_count = 250
        
        segment = behavior_tracker._determine_user_segment(sample_user_behavior)
        assert segment == UserSegment.POWER_USER
    
    @pytest.mark.asyncio
    async def test_determine_user_segment_content_creator(self, behavior_tracker, sample_user_behavior):
        """Test user segmentation for content creators."""
        sample_user_behavior.assets_uploaded = 25
        
        segment = behavior_tracker._determine_user_segment(sample_user_behavior)
        assert segment == UserSegment.CONTENT_CREATOR
    
    @pytest.mark.asyncio
    async def test_determine_user_segment_searcher(self, behavior_tracker, sample_user_behavior):
        """Test user segmentation for searchers."""
        sample_user_behavior.searches_performed = 60
        sample_user_behavior.assets_uploaded = 1
        
        segment = behavior_tracker._determine_user_segment(sample_user_behavior)
        assert segment == UserSegment.SEARCHER
    
    @pytest.mark.asyncio
    async def test_determine_user_segment_workflow_user(self, behavior_tracker, sample_user_behavior):
        """Test user segmentation for workflow users."""
        sample_user_behavior.workflows_executed = 15
        sample_user_behavior.assets_uploaded = 5
        
        segment = behavior_tracker._determine_user_segment(sample_user_behavior)
        assert segment == UserSegment.WORKFLOW_USER
    
    @pytest.mark.asyncio
    async def test_determine_user_segment_explorer(self, behavior_tracker, sample_user_behavior):
        """Test user segmentation for explorers."""
        sample_user_behavior.page_views = 120
        sample_user_behavior.features_used = ["search", "browse", "projects", "workflows", "upload", "share"]
        sample_user_behavior.assets_uploaded = 3
        sample_user_behavior.workflows_executed = 2
        
        segment = behavior_tracker._determine_user_segment(sample_user_behavior)
        assert segment == UserSegment.EXPLORER
    
    @pytest.mark.asyncio
    async def test_determine_user_segment_new_user(self, behavior_tracker, sample_user_behavior):
        """Test user segmentation for new users."""
        sample_user_behavior.sessions_count = 3
        sample_user_behavior.assets_uploaded = 0
        
        segment = behavior_tracker._determine_user_segment(sample_user_behavior)
        assert segment == UserSegment.NEW_USER
    
    @pytest.mark.asyncio
    async def test_determine_user_segment_inactive_user(self, behavior_tracker, sample_user_behavior):
        """Test user segmentation for inactive users."""
        sample_user_behavior.sessions_count = 1
        sample_user_behavior.total_time_minutes = 20
        
        segment = behavior_tracker._determine_user_segment(sample_user_behavior)
        assert segment == UserSegment.INACTIVE_USER
    
    @pytest.mark.asyncio
    async def test_determine_user_segment_casual_user(self, behavior_tracker, sample_user_behavior):
        """Test user segmentation for casual users (fallback)."""
        sample_user_behavior.sessions_count = 8
        sample_user_behavior.total_time_minutes = 120
        sample_user_behavior.actions_count = 30
        sample_user_behavior.assets_uploaded = 2
        sample_user_behavior.workflows_executed = 1
        sample_user_behavior.searches_performed = 15
        
        segment = behavior_tracker._determine_user_segment(sample_user_behavior)
        assert segment == UserSegment.CASUAL_USER
    
    @pytest.mark.asyncio
    async def test_classify_behavior_pattern_power_user(self, behavior_tracker):
        """Test behavior pattern classification for power users."""
        metrics = {
            "avg_sessions": 25,
            "avg_time_minutes": 400,
            "avg_actions": 150,
            "avg_uploads": 5,
            "avg_searches": 20
        }
        
        pattern_name, description = behavior_tracker._classify_behavior_pattern(metrics)
        assert pattern_name == "power_user"
        assert "Highly engaged users" in description
    
    @pytest.mark.asyncio
    async def test_classify_behavior_pattern_content_creator(self, behavior_tracker):
        """Test behavior pattern classification for content creators."""
        metrics = {
            "avg_sessions": 15,
            "avg_time_minutes": 200,
            "avg_actions": 50,
            "avg_uploads": 15,
            "avg_searches": 10
        }
        
        pattern_name, description = behavior_tracker._classify_behavior_pattern(metrics)
        assert pattern_name == "content_creator"
        assert "frequently upload" in description
    
    @pytest.mark.asyncio
    async def test_classify_behavior_pattern_searcher(self, behavior_tracker):
        """Test behavior pattern classification for searchers."""
        metrics = {
            "avg_sessions": 10,
            "avg_time_minutes": 150,
            "avg_actions": 40,
            "avg_uploads": 2,
            "avg_searches": 60
        }
        
        pattern_name, description = behavior_tracker._classify_behavior_pattern(metrics)
        assert pattern_name == "searcher"
        assert "search functionality" in description
    
    @pytest.mark.asyncio
    async def test_classify_behavior_pattern_browser(self, behavior_tracker):
        """Test behavior pattern classification for browsers."""
        metrics = {
            "avg_sessions": 8,
            "avg_time_minutes": 100,
            "avg_actions": 15,
            "avg_uploads": 1,
            "avg_searches": 20,
            "avg_assets_viewed": 25
        }
        
        pattern_name, description = behavior_tracker._classify_behavior_pattern(metrics)
        assert pattern_name == "browser"
        assert "browse content" in description
    
    @pytest.mark.asyncio
    async def test_classify_behavior_pattern_casual_user(self, behavior_tracker):
        """Test behavior pattern classification for casual users."""
        metrics = {
            "avg_sessions": 3,
            "avg_time_minutes": 45,
            "avg_actions": 10,
            "avg_uploads": 1,
            "avg_searches": 5,
            "avg_assets_viewed": 8
        }
        
        pattern_name, description = behavior_tracker._classify_behavior_pattern(metrics)
        assert pattern_name == "casual_user"
        assert "Infrequent users" in description
    
    @pytest.mark.asyncio
    async def test_classify_behavior_pattern_balanced_user(self, behavior_tracker):
        """Test behavior pattern classification for balanced users."""
        metrics = {
            "avg_sessions": 12,
            "avg_time_minutes": 180,
            "avg_actions": 60,
            "avg_uploads": 4,
            "avg_searches": 25,
            "avg_assets_viewed": 15
        }
        
        pattern_name, description = behavior_tracker._classify_behavior_pattern(metrics)
        assert pattern_name == "balanced_user"
        assert "moderate engagement" in description
    
    @pytest.mark.asyncio
    async def test_analyze_user_patterns_insufficient_data(self, behavior_tracker, mock_db):
        """Test pattern analysis with insufficient data."""
        # Mock database to return insufficient behaviors
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []  # Empty list
        mock_db.execute.return_value = mock_result
        
        patterns = await behavior_tracker.analyze_user_patterns(mock_db)
        assert patterns == []
    
    @pytest.mark.asyncio
    async def test_generate_user_recommendations_workflow(self, behavior_tracker, sample_user_behavior):
        """Test recommendation generation for workflow features."""
        sample_user_behavior.assets_uploaded = 10
        sample_user_behavior.workflows_executed = 0
        
        recommendations = behavior_tracker._generate_user_recommendations(sample_user_behavior)
        assert any("automated workflows" in rec for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_generate_user_recommendations_search_exploration(self, behavior_tracker, sample_user_behavior):
        """Test recommendation generation for search exploration."""
        sample_user_behavior.searches_performed = 30
        sample_user_behavior.assets_viewed = 15
        
        recommendations = behavior_tracker._generate_user_recommendations(sample_user_behavior)
        assert any("search results more thoroughly" in rec for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_generate_user_recommendations_efficiency(self, behavior_tracker, sample_user_behavior):
        """Test recommendation generation for efficiency improvements."""
        sample_user_behavior.sessions_count = 15
        sample_user_behavior.avg_session_duration = 12
        
        recommendations = behavior_tracker._generate_user_recommendations(sample_user_behavior)
        assert any("keyboard shortcuts" in rec for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_generate_user_recommendations_content_creation(self, behavior_tracker, sample_user_behavior):
        """Test recommendation generation for content creation."""
        sample_user_behavior.assets_viewed = 120
        sample_user_behavior.assets_uploaded = 2
        
        recommendations = behavior_tracker._generate_user_recommendations(sample_user_behavior)
        assert any("uploading your own content" in rec for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_generate_user_recommendations_by_segment(self, behavior_tracker, sample_user_behavior):
        """Test segment-based recommendations."""
        # Test searcher segment
        sample_user_behavior.user_segment = UserSegment.SEARCHER
        recommendations = behavior_tracker._generate_user_recommendations(sample_user_behavior)
        assert any("advanced search filters" in rec for rec in recommendations)
        
        # Test content creator segment
        sample_user_behavior.user_segment = UserSegment.CONTENT_CREATOR
        recommendations = behavior_tracker._generate_user_recommendations(sample_user_behavior)
        assert any("batch upload" in rec for rec in recommendations)
        
        # Test casual user segment
        sample_user_behavior.user_segment = UserSegment.CASUAL_USER
        recommendations = behavior_tracker._generate_user_recommendations(sample_user_behavior)
        assert any("quick start guide" in rec for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_process_user_journey_insufficient_steps(self, behavior_tracker, mock_db):
        """Test journey processing with insufficient steps."""
        user_id = "test-user-123"
        session_id = "session-456"
        
        # Mock minimal journey buffer
        behavior_tracker.journey_buffer[f"{user_id}:{session_id}"] = [
            {"action": "login", "timestamp": datetime.utcnow(), "context": {}}
        ]
        
        journey = await behavior_tracker._process_user_journey(user_id, session_id, mock_db)
        assert journey is None
    
    @pytest.mark.asyncio
    async def test_process_user_journey_complete(self, behavior_tracker, mock_db):
        """Test complete journey processing."""
        user_id = "test-user-123"
        session_id = "session-456"
        
        # Mock journey with sufficient steps
        now = datetime.utcnow()
        journey_steps = [
            {"action": "login", "timestamp": now - timedelta(minutes=30), "context": {}},
            {"action": "search", "timestamp": now - timedelta(minutes=25), "context": {"query": "test"}},
            {"action": "asset_view", "timestamp": now - timedelta(minutes=20), "context": {"asset_id": "123"}},
            {"action": "asset_upload", "timestamp": now - timedelta(minutes=15), "context": {"file": "test.mp4"}},
            {"action": "workflow_complete", "timestamp": now - timedelta(minutes=10), "context": {"workflow_id": "456"}},
            {"action": "logout", "timestamp": now, "context": {}}
        ]
        
        behavior_tracker.journey_buffer[f"{user_id}:{session_id}"] = journey_steps
        
        journey = await behavior_tracker._process_user_journey(user_id, session_id, mock_db)
        
        assert journey is not None
        assert journey.user_id == user_id
        assert journey.session_id == session_id
        assert len(journey.journey_steps) == 6
        assert journey.duration_minutes == 30.0
        assert "workflow_complete" in journey.conversion_events
        
        # Verify event was stored
        mock_db.add.assert_called()
        mock_db.commit.assert_awaited()
    
    @pytest.mark.asyncio
    async def test_process_user_journey_drop_off_detection(self, behavior_tracker, mock_db):
        """Test drop-off point detection in user journeys."""
        user_id = "test-user-123"
        session_id = "session-456"
        
        # Mock journey with repetitive search pattern
        now = datetime.utcnow()
        journey_steps = [
            {"action": "login", "timestamp": now - timedelta(minutes=10), "context": {}},
            {"action": "search", "timestamp": now - timedelta(minutes=9), "context": {"query": "test1"}},
            {"action": "search", "timestamp": now - timedelta(minutes=8), "context": {"query": "test2"}},
            {"action": "search", "timestamp": now - timedelta(minutes=7), "context": {"query": "test3"}},
            {"action": "search", "timestamp": now - timedelta(minutes=6), "context": {"query": "test4"}},
            {"action": "logout", "timestamp": now, "context": {}}
        ]
        
        behavior_tracker.journey_buffer[f"{user_id}:{session_id}"] = journey_steps
        
        journey = await behavior_tracker._process_user_journey(user_id, session_id, mock_db)
        
        assert journey is not None
        assert journey.drop_off_point == "search_loop"
    
    @pytest.mark.asyncio
    async def test_segment_users_empty_database(self, behavior_tracker, mock_db):
        """Test user segmentation with empty database."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        segments = await behavior_tracker.segment_users(mock_db)
        assert segments == {}
    
    @pytest.mark.asyncio
    async def test_segment_users_with_data(self, behavior_tracker, mock_db, sample_user_behavior):
        """Test user segmentation with sample data."""
        # Create multiple behavior records
        behaviors = [
            sample_user_behavior,  # Power user
            UserBehavior(
                user_id="casual-user-456",
                period_start=datetime.utcnow() - timedelta(days=7),
                period_end=datetime.utcnow(),
                period_type="weekly",
                sessions_count=3,
                total_time_minutes=60,
                actions_count=15
            ),  # Casual user
            UserBehavior(
                user_id="creator-user-789",
                period_start=datetime.utcnow() - timedelta(days=7),
                period_end=datetime.utcnow(),
                period_type="weekly",
                sessions_count=12,
                total_time_minutes=240,
                actions_count=50,
                assets_uploaded=25
            )  # Content creator
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = behaviors
        mock_db.execute.return_value = mock_result
        
        segments = await behavior_tracker.segment_users(mock_db)
        
        assert UserSegment.POWER_USER in segments
        assert UserSegment.CASUAL_USER in segments
        assert UserSegment.CONTENT_CREATOR in segments
        assert "test-user-123" in segments[UserSegment.POWER_USER]
        assert "casual-user-456" in segments[UserSegment.CASUAL_USER]
        assert "creator-user-789" in segments[UserSegment.CONTENT_CREATOR]


class TestUserJourney:
    """Test cases for UserJourney data class."""
    
    def test_user_journey_creation(self):
        """Test UserJourney data class creation."""
        journey_steps = [
            {"action": "login", "timestamp": datetime.utcnow(), "context": {}},
            {"action": "search", "timestamp": datetime.utcnow(), "context": {"query": "test"}}
        ]
        
        journey = UserJourney(
            user_id="test-user",
            session_id="test-session",
            journey_steps=journey_steps,
            duration_minutes=15.5,
            conversion_events=["asset_upload"],
            drop_off_point=None
        )
        
        assert journey.user_id == "test-user"
        assert journey.session_id == "test-session"
        assert len(journey.journey_steps) == 2
        assert journey.duration_minutes == 15.5
        assert journey.conversion_events == ["asset_upload"]
        assert journey.drop_off_point is None


class TestBehaviorPattern:
    """Test cases for BehaviorPattern data class."""
    
    def test_behavior_pattern_creation(self):
        """Test BehaviorPattern data class creation."""
        metrics = {
            "avg_sessions": 20.5,
            "avg_time_minutes": 300.0,
            "avg_actions": 150.0
        }
        
        pattern = BehaviorPattern(
            pattern_id="pattern_1",
            pattern_name="power_user",
            description="Highly engaged users",
            metrics=metrics,
            users_count=25,
            confidence=0.85
        )
        
        assert pattern.pattern_id == "pattern_1"
        assert pattern.pattern_name == "power_user"
        assert pattern.description == "Highly engaged users"
        assert pattern.metrics == metrics
        assert pattern.users_count == 25
        assert pattern.confidence == 0.85


@pytest.mark.asyncio
async def test_behavior_tracker_redis_error_handling(behavior_tracker, mock_db):
    """Test Redis error handling in behavior tracker."""
    with patch.object(behavior_tracker, '_get_redis', side_effect=Exception("Redis connection failed")):
        # Should not raise exception, just log error
        await behavior_tracker.track_user_action(
            "test-user", "test-session", "test_action", {}, mock_db
        )
        
        # Event should still be added to database
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_behavior_tracker_cleanup():
    """Test behavior tracker cleanup."""
    tracker = BehaviorTracker()
    mock_redis = AsyncMock()
    tracker.redis_client = mock_redis
    
    await tracker.close()
    mock_redis.close.assert_awaited_once()
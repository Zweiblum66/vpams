"""
Tests for Video Summarizer Service
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import numpy as np
import tempfile
import os

from src.services.video_summarizer import VideoSummarizer
from src.models.schemas import (
    VideoSummary, SummarySegment, SummaryType, KeyFrame,
    TranscriptHighlight, ModelType
)
from src.db.models import VideoSummaryModel, SummarySegmentModel


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = Mock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    return redis


@pytest.fixture
def video_summarizer(mock_db, mock_redis):
    """Create video summarizer instance"""
    return VideoSummarizer(db=mock_db, redis=redis)


@pytest.fixture
def sample_video_path():
    """Create a temporary video file path"""
    temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    temp_file.close()
    yield temp_file.name
    # Cleanup
    try:
        os.unlink(temp_file.name)
    except FileNotFoundError:
        pass


@pytest.fixture
def mock_video_processor():
    """Mock video processor"""
    processor = Mock()
    processor.get_video_info = AsyncMock(return_value={
        'duration': 300.0,  # 5 minutes
        'fps': 30.0,
        'width': 1920,
        'height': 1080,
        'frame_count': 9000,
        'codec': 'h264',
        'bitrate': 5000000,
        'has_audio': True
    })
    return processor


class TestVideoSummarizer:
    """Test video summarization functionality"""
    
    @pytest.mark.asyncio
    async def test_initialize(self, video_summarizer):
        """Test summarizer initialization"""
        with patch.object(video_summarizer, '_load_models') as mock_load:
            await video_summarizer.initialize()
            mock_load.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_summarize_video_highlights(self, video_summarizer, sample_video_path, mock_video_processor):
        """Test video summarization with highlights type"""
        # Mock dependencies
        video_summarizer.video_processor = mock_video_processor
        
        # Mock scene detection
        with patch.object(video_summarizer, '_detect_scenes') as mock_scenes:
            mock_scenes.return_value = [
                (0.0, 30.0),    # Scene 1: 0-30s
                (30.0, 60.0),   # Scene 2: 30-60s
                (60.0, 90.0),   # Scene 3: 60-90s
                (90.0, 120.0),  # Scene 4: 90-120s
            ]
            
            # Mock scene scoring
            with patch.object(video_summarizer, '_score_scene_importance') as mock_score:
                mock_score.side_effect = [0.9, 0.7, 0.8, 0.6]  # Different scores
                
                # Mock other methods
                with patch.object(video_summarizer, '_extract_keyframes') as mock_keyframes:
                    mock_keyframes.return_value = []
                    
                    with patch.object(video_summarizer, '_get_transcript_highlights') as mock_transcript:
                        mock_transcript.return_value = []
                        
                        with patch.object(video_summarizer, '_store_summary') as mock_store:
                            
                            # Test summarization
                            summary = await video_summarizer.summarize_video(
                                asset_id="test_asset",
                                video_path=sample_video_path,
                                target_duration_percent=20,
                                summary_type=SummaryType.HIGHLIGHTS
                            )
                            
                            assert isinstance(summary, VideoSummary)
                            assert summary.asset_id == "test_asset"
                            assert summary.summary_type == SummaryType.HIGHLIGHTS
                            assert len(summary.segments) > 0
                            assert summary.original_duration == 300.0
                            assert summary.confidence_score > 0
                            
                            # Check that segments are sorted by importance
                            scores = [s.importance_score for s in summary.segments]
                            assert scores == sorted(scores, reverse=True)
                            
                            mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_detect_scenes(self, video_summarizer, sample_video_path):
        """Test scene detection"""
        # Mock PySceneDetect
        with patch('src.services.video_summarizer.detect') as mock_detect:
            # Mock scene list with timestamps
            mock_scene_list = [
                (Mock(get_seconds=Mock(return_value=0.0)), Mock(get_seconds=Mock(return_value=30.0))),
                (Mock(get_seconds=Mock(return_value=30.0)), Mock(get_seconds=Mock(return_value=60.0))),
                (Mock(get_seconds=Mock(return_value=60.0)), Mock(get_seconds=Mock(return_value=90.0))),
            ]
            mock_detect.return_value = mock_scene_list
            
            scenes = await video_summarizer._detect_scenes(sample_video_path)
            
            assert len(scenes) == 3
            assert scenes[0] == (0.0, 30.0)
            assert scenes[1] == (30.0, 60.0)
            assert scenes[2] == (60.0, 90.0)
    
    @pytest.mark.asyncio
    async def test_detect_scenes_fallback(self, video_summarizer, sample_video_path):
        """Test scene detection fallback when PySceneDetect fails"""
        # Mock PySceneDetect to raise exception
        with patch('src.services.video_summarizer.detect', side_effect=Exception("Test error")):
            # Mock OpenCV
            with patch('cv2.VideoCapture') as mock_cap:
                mock_cap_instance = Mock()
                mock_cap_instance.get.side_effect = [30.0, 3000, 1920, 1080]  # fps, frame_count, width, height
                mock_cap_instance.release = Mock()
                mock_cap.return_value = mock_cap_instance
                
                scenes = await video_summarizer._detect_scenes(sample_video_path)
                
                # Should create 10-second intervals
                assert len(scenes) > 0
                assert scenes[0][0] == 0.0
                assert scenes[0][1] == 10.0
    
    @pytest.mark.asyncio
    async def test_score_scene_importance(self, video_summarizer, sample_video_path):
        """Test scene importance scoring"""
        # Mock OpenCV
        with patch('cv2.VideoCapture') as mock_cap:
            # Create mock frame
            mock_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            mock_cap_instance = Mock()
            mock_cap_instance.get.side_effect = [30.0]  # fps
            mock_cap_instance.set = Mock()
            mock_cap_instance.read.return_value = (True, mock_frame)
            mock_cap_instance.release = Mock()
            mock_cap.return_value = mock_cap_instance
            
            # Mock OpenCV functions
            with patch('cv2.cvtColor', return_value=np.random.randint(0, 255, (480, 640), dtype=np.uint8)):
                with patch('cv2.Laplacian', return_value=np.random.randn(480, 640) * 100):
                    with patch('cv2.calcHist', return_value=np.random.randn(8*8*8, 1)):
                        
                        score = await video_summarizer._score_scene_importance(
                            sample_video_path, (0.0, 30.0), 30.0
                        )
                        
                        assert isinstance(score, float)
                        assert 0.0 <= score <= 1.0
    
    @pytest.mark.asyncio
    async def test_detect_high_motion_segments(self, video_summarizer, sample_video_path):
        """Test high motion segment detection"""
        # Mock OpenCV
        with patch('cv2.VideoCapture') as mock_cap:
            # Create mock frames
            frame1 = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            frame2 = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            mock_cap_instance = Mock()
            mock_cap_instance.read.side_effect = [
                (True, frame1), (True, frame2), (False, None)
            ]
            mock_cap_instance.release = Mock()
            mock_cap.return_value = mock_cap_instance
            
            # Mock OpenCV functions
            with patch('cv2.cvtColor', side_effect=[
                np.random.randint(0, 255, (480, 640), dtype=np.uint8),
                np.random.randint(0, 255, (480, 640), dtype=np.uint8)
            ]):
                with patch('cv2.absdiff', return_value=np.random.randint(0, 50, (480, 640), dtype=np.uint8)):
                    
                    segments = await video_summarizer._detect_high_motion_segments(
                        sample_video_path, 30.0
                    )
                    
                    assert isinstance(segments, list)
                    # May or may not have segments depending on mock motion scores
    
    @pytest.mark.asyncio
    async def test_extract_transcript(self, video_summarizer, sample_video_path):
        """Test transcript extraction"""
        # Mock Whisper model
        mock_whisper_model = Mock()
        mock_whisper_model.transcribe.return_value = {
            'segments': [
                {
                    'start': 0.0,
                    'end': 5.0,
                    'text': 'Hello world',
                    'confidence': 0.95
                },
                {
                    'start': 5.0,
                    'end': 10.0,
                    'text': 'This is a test',
                    'confidence': 0.89
                }
            ]
        }
        video_summarizer.whisper_model = mock_whisper_model
        
        transcript = await video_summarizer._extract_transcript(sample_video_path)
        
        assert len(transcript) == 2
        assert transcript[0]['text'] == 'Hello world'
        assert transcript[0]['confidence'] == 0.95
        assert transcript[1]['text'] == 'This is a test'
        assert transcript[1]['confidence'] == 0.89
    
    @pytest.mark.asyncio
    async def test_extract_transcript_no_model(self, video_summarizer, sample_video_path):
        """Test transcript extraction when no model is loaded"""
        video_summarizer.whisper_model = None
        
        transcript = await video_summarizer._extract_transcript(sample_video_path)
        
        assert transcript is None
    
    def test_calculate_confidence(self, video_summarizer):
        """Test confidence score calculation"""
        segments = [
            SummarySegment(
                start_time=0.0,
                end_time=30.0,
                duration=30.0,
                importance_score=0.9,
                scene_type="highlight",
                description="High importance segment"
            ),
            SummarySegment(
                start_time=60.0,
                end_time=90.0,
                duration=30.0,
                importance_score=0.7,
                scene_type="dialogue",
                description="Medium importance segment"
            ),
            SummarySegment(
                start_time=120.0,
                end_time=150.0,
                duration=30.0,
                importance_score=0.8,
                scene_type="action",
                description="Good segment"
            )
        ]
        
        confidence = video_summarizer._calculate_confidence(segments)
        
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        
        # Should be close to average importance (0.8)
        expected_avg = (0.9 + 0.7 + 0.8) / 3
        assert abs(confidence - expected_avg) < 0.2  # Allow some variance for coverage calculation
    
    def test_calculate_confidence_empty(self, video_summarizer):
        """Test confidence calculation with empty segments"""
        confidence = video_summarizer._calculate_confidence([])
        assert confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_store_summary(self, video_summarizer, mock_db):
        """Test storing summary in database"""
        summary = VideoSummary(
            asset_id="test_asset",
            original_duration=300.0,
            summary_duration=60.0,
            target_duration_percent=20,
            actual_duration_percent=20.0,
            summary_type=SummaryType.HIGHLIGHTS,
            segments=[
                SummarySegment(
                    start_time=0.0,
                    end_time=30.0,
                    duration=30.0,
                    importance_score=0.9,
                    scene_type="highlight",
                    description="Test segment"
                )
            ],
            keyframes=[],
            transcript_highlights=[],
            confidence_score=0.85,
            processing_time=15.5,
            model_used=ModelType.CUSTOM
        )
        
        await video_summarizer._store_summary(summary)
        
        # Verify database calls
        assert mock_db.add.call_count == 2  # Summary + 1 segment
        assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_generate_summary_video(self, video_summarizer, sample_video_path):
        """Test generating summary video file"""
        segments = [
            SummarySegment(
                start_time=0.0,
                end_time=30.0,
                duration=30.0,
                importance_score=0.9,
                scene_type="highlight",
                description="First segment"
            ),
            SummarySegment(
                start_time=60.0,
                end_time=90.0,
                duration=30.0,
                importance_score=0.8,
                scene_type="action",
                description="Second segment"
            )
        ]
        
        output_path = tempfile.mktemp(suffix=".mp4")
        
        # Mock MoviePy
        with patch('src.services.video_summarizer.VideoFileClip') as mock_video_clip:
            with patch('src.services.video_summarizer.concatenate_videoclips') as mock_concat:
                # Mock video clip
                mock_clip = Mock()
                mock_subclip = Mock()
                mock_clip.subclip.return_value = mock_subclip
                mock_video_clip.return_value = mock_clip
                
                # Mock concatenated video
                mock_final = Mock()
                mock_final.write_videofile = Mock()
                mock_final.close = Mock()
                mock_concat.return_value = mock_final
                
                result_path = await video_summarizer.generate_summary_video(
                    sample_video_path, segments, output_path
                )
                
                assert result_path == output_path
                mock_clip.subclip.assert_called()
                mock_concat.assert_called_once()
                mock_final.write_videofile.assert_called_once_with(
                    output_path, codec='libx264', audio_codec='aac'
                )
    
    @pytest.mark.asyncio
    async def test_different_summary_types(self, video_summarizer, sample_video_path, mock_video_processor):
        """Test different summary types"""
        video_summarizer.video_processor = mock_video_processor
        
        # Mock all required methods
        with patch.object(video_summarizer, '_detect_scenes', return_value=[(0.0, 30.0), (30.0, 60.0)]):
            with patch.object(video_summarizer, '_score_scene_importance', return_value=0.8):
                with patch.object(video_summarizer, '_extract_keyframes', return_value=[]):
                    with patch.object(video_summarizer, '_get_transcript_highlights', return_value=[]):
                        with patch.object(video_summarizer, '_store_summary'):
                            
                            # Test each summary type
                            for summary_type in [SummaryType.HIGHLIGHTS, SummaryType.SCENES, 
                                               SummaryType.ACTION, SummaryType.INTELLIGENT]:
                                
                                summary = await video_summarizer.summarize_video(
                                    asset_id="test_asset",
                                    video_path=sample_video_path,
                                    target_duration_percent=15,
                                    summary_type=summary_type
                                )
                                
                                assert summary.summary_type == summary_type
                                assert len(summary.segments) > 0
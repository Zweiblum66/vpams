"""
Tests for Auto-Tagging Service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import numpy as np
from datetime import datetime
from typing import List, Dict, Any

from src.services.auto_tagger import AutoTagger
from src.models.schemas import AutoTag, TagCategory, TagSource
from src.db.models import AutoTagModel, ContentModerationModel


@pytest.fixture
def mock_db():
    """Mock database session"""
    return AsyncMock()


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    return AsyncMock()


@pytest.fixture
def auto_tagger(mock_db, mock_redis):
    """Create AutoTagger instance with mocked dependencies"""
    return AutoTagger(db=mock_db, redis=mock_redis)


class TestAutoTagger:
    """Test cases for AutoTagger service"""

    @pytest.mark.asyncio
    async def test_initialize(self, auto_tagger):
        """Test auto-tagger initialization"""
        with patch.object(auto_tagger, '_load_models', new_callable=AsyncMock):
            await auto_tagger.initialize()
            assert auto_tagger._load_models.called

    @pytest.mark.asyncio
    async def test_analyze_image_basic(self, auto_tagger):
        """Test basic image analysis"""
        # Mock image loading
        mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        with patch('cv2.imread', return_value=mock_image), \
             patch.object(auto_tagger, '_detect_objects_in_image', new_callable=AsyncMock, return_value=[]), \
             patch.object(auto_tagger, '_classify_image_scene', new_callable=AsyncMock, return_value=[]), \
             patch.object(auto_tagger, '_extract_text_from_image', new_callable=AsyncMock, return_value=[]), \
             patch.object(auto_tagger, '_analyze_image_colors', new_callable=AsyncMock, return_value=[]), \
             patch.object(auto_tagger, '_analyze_image_composition', new_callable=AsyncMock, return_value=[]), \
             patch.object(auto_tagger, '_moderate_image_content', new_callable=AsyncMock, return_value=[]), \
             patch.object(auto_tagger, '_extract_image_technical_tags', new_callable=AsyncMock, return_value=[]):
            
            tags = await auto_tagger._analyze_image('/path/to/image.jpg', 'asset123')
            assert isinstance(tags, list)

    @pytest.mark.asyncio
    async def test_detect_objects_with_yolo(self, auto_tagger):
        """Test object detection with YOLO model"""
        # Mock YOLO model
        mock_box = Mock()
        mock_box.cls = [0]  # Class ID
        mock_box.conf = [0.85]  # Confidence
        mock_box.xyxy = [[10, 20, 100, 200]]  # Bounding box
        
        mock_result = Mock()
        mock_result.boxes = [mock_box]
        
        auto_tagger.object_detection_model = Mock()
        auto_tagger.object_detection_model.return_value = [mock_result]
        auto_tagger.object_detection_model.names = {0: 'person'}
        
        # Mock settings
        with patch('src.services.auto_tagger.settings') as mock_settings:
            mock_settings.AUTO_TAGGING_CONFIDENCE_THRESHOLD = 0.7
            
            mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
            tags = await auto_tagger._detect_objects_in_image(mock_image, 'asset123')
            
            assert len(tags) == 1
            assert tags[0].tag_name == 'person'
            assert tags[0].confidence == 0.85
            assert tags[0].category == TagCategory.OBJECT
            assert tags[0].source == TagSource.YOLO

    @pytest.mark.asyncio
    async def test_extract_text_with_ocr(self, auto_tagger):
        """Test text extraction with OCR"""
        # Mock OCR reader
        auto_tagger.ocr_reader = Mock()
        auto_tagger.ocr_reader.readtext.return_value = [
            ([(0, 0), (100, 0), (100, 30), (0, 30)], 'Sample Text', 0.9),
            ([(0, 40), (80, 40), (80, 70), (0, 70)], 'More Text', 0.8)
        ]
        
        with patch.object(auto_tagger, '_analyze_extracted_text', new_callable=AsyncMock, return_value=[]):
            mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
            tags = await auto_tagger._extract_text_from_image(mock_image, 'asset123')
            
            assert len(tags) == 1
            assert tags[0].tag_name == 'contains_text'
            assert tags[0].category == TagCategory.CONTENT
            assert tags[0].source == TagSource.OCR
            assert 'Sample Text More Text' in tags[0].metadata['extracted_text']

    @pytest.mark.asyncio
    async def test_analyze_image_colors(self, auto_tagger):
        """Test color analysis"""
        # Create a simple colored image
        mock_image = np.ones((100, 100, 3), dtype=np.uint8)
        mock_image[:, :, 0] = 255  # Red channel
        mock_image[:, :, 1] = 0    # Green channel
        mock_image[:, :, 2] = 0    # Blue channel
        
        with patch('sklearn.cluster.KMeans') as mock_kmeans:
            # Mock KMeans clustering
            mock_kmeans_instance = Mock()
            mock_kmeans_instance.cluster_centers_ = np.array([[255, 0, 0]])  # Red
            mock_kmeans_instance.labels_ = np.zeros(10000)  # All pixels belong to cluster 0
            mock_kmeans.return_value = mock_kmeans_instance
            
            tags = await auto_tagger._analyze_image_colors(mock_image, 'asset123')
            
            assert len(tags) >= 1  # Should have color tags
            # Check that we have color and temperature tags
            color_tags = [tag for tag in tags if tag.tag_name.startswith('color_')]
            temp_tags = [tag for tag in tags if tag.tag_name.startswith('temperature_')]
            assert len(color_tags) >= 1
            assert len(temp_tags) == 1

    @pytest.mark.asyncio
    async def test_content_moderation(self, auto_tagger):
        """Test content moderation"""
        # Mock moderation model
        auto_tagger.content_moderation_model = Mock()
        auto_tagger.content_moderation_model.return_value = [
            {'label': 'safe', 'score': 0.9},
            {'label': 'nsfw', 'score': 0.1}
        ]
        
        with patch.object(auto_tagger, '_store_moderation_result', new_callable=AsyncMock):
            mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
            tags = await auto_tagger._moderate_image_content(mock_image, 'asset123')
            
            assert len(tags) == 2
            safe_tag = next((tag for tag in tags if 'safe' in tag.tag_name), None)
            assert safe_tag is not None
            assert safe_tag.category == TagCategory.MODERATION
            assert safe_tag.source == TagSource.MODERATION

    @pytest.mark.asyncio
    async def test_filter_and_rank_tags(self, auto_tagger):
        """Test tag filtering and ranking"""
        # Create test tags with duplicates and different confidence levels
        tags = [
            AutoTag(
                asset_id='asset123',
                tag_name='person',
                category=TagCategory.OBJECT,
                confidence=0.9,
                source=TagSource.YOLO,
                metadata={}
            ),
            AutoTag(
                asset_id='asset123',
                tag_name='person',
                category=TagCategory.OBJECT,
                confidence=0.8,
                source=TagSource.YOLO,
                metadata={}
            ),
            AutoTag(
                asset_id='asset123',
                tag_name='low_confidence_tag',
                category=TagCategory.OBJECT,
                confidence=0.3,
                source=TagSource.YOLO,
                metadata={}
            )
        ]
        
        with patch('src.services.auto_tagger.settings') as mock_settings:
            mock_settings.AUTO_TAGGING_CONFIDENCE_THRESHOLD = 0.5
            mock_settings.MAX_AUTO_TAGS_PER_ASSET = 50
            
            filtered_tags = await auto_tagger._filter_and_rank_tags(tags)
            
            # Should merge duplicates and filter low confidence
            assert len(filtered_tags) == 1
            assert filtered_tags[0].tag_name == 'person'
            assert filtered_tags[0].confidence == 0.9  # Highest confidence kept

    @pytest.mark.asyncio
    async def test_analyze_and_tag_asset_image(self, auto_tagger):
        """Test complete auto-tagging workflow for image"""
        # Mock all internal methods
        with patch.object(auto_tagger, '_analyze_image', new_callable=AsyncMock) as mock_analyze_image, \
             patch.object(auto_tagger, '_filter_and_rank_tags', new_callable=AsyncMock) as mock_filter, \
             patch.object(auto_tagger, '_store_tags', new_callable=AsyncMock):
            
            # Setup mock returns
            mock_tags = [
                AutoTag(
                    asset_id='asset123',
                    tag_name='person',
                    category=TagCategory.OBJECT,
                    confidence=0.9,
                    source=TagSource.YOLO,
                    metadata={}
                )
            ]
            mock_analyze_image.return_value = mock_tags
            mock_filter.return_value = mock_tags
            
            # Test the main method
            result = await auto_tagger.analyze_and_tag_asset(
                asset_id='asset123',
                file_path='/path/to/image.jpg',
                asset_type='image/jpeg'
            )
            
            assert len(result) == 1
            assert result[0].tag_name == 'person'
            mock_analyze_image.assert_called_once()
            mock_filter.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_video_frames(self, auto_tagger):
        """Test video frame analysis"""
        # Mock video capture
        with patch('cv2.VideoCapture') as mock_cap:
            mock_cap_instance = Mock()
            mock_cap_instance.isOpened.return_value = True
            mock_cap_instance.get.side_effect = lambda prop: {
                'fps': 30.0,
                'frame_count': 300.0
            }.get(prop, 0)
            
            # Mock frame reading
            mock_frame = np.zeros((100, 100, 3), dtype=np.uint8)
            mock_cap_instance.read.return_value = (True, mock_frame)
            mock_cap.return_value = mock_cap_instance
            
            # Mock analysis methods
            with patch.object(auto_tagger, '_detect_objects_in_image', new_callable=AsyncMock, return_value=[]), \
                 patch.object(auto_tagger, '_classify_image_scene', new_callable=AsyncMock, return_value=[]), \
                 patch.object(auto_tagger, '_analyze_video_audio', new_callable=AsyncMock, return_value=[]), \
                 patch.object(auto_tagger, '_analyze_video_motion', new_callable=AsyncMock, return_value=[]), \
                 patch.object(auto_tagger, '_extract_video_technical_tags', new_callable=AsyncMock, return_value=[]):
                
                tags = await auto_tagger._analyze_video('/path/to/video.mp4', 'asset123')
                assert isinstance(tags, list)

    def test_rgb_to_color_name(self, auto_tagger):
        """Test RGB to color name conversion"""
        # Test basic colors
        assert auto_tagger._rgb_to_color_name(np.array([255, 0, 0])) == 'red'
        assert auto_tagger._rgb_to_color_name(np.array([0, 255, 0])) == 'green'
        assert auto_tagger._rgb_to_color_name(np.array([0, 0, 255])) == 'blue'
        assert auto_tagger._rgb_to_color_name(np.array([255, 255, 255])) == 'white'
        assert auto_tagger._rgb_to_color_name(np.array([0, 0, 0])) == 'black'

    def test_categorize_file_size(self, auto_tagger):
        """Test file size categorization"""
        assert auto_tagger._categorize_file_size(5 * 1024 * 1024) == 'small'  # 5MB
        assert auto_tagger._categorize_file_size(50 * 1024 * 1024) == 'medium'  # 50MB
        assert auto_tagger._categorize_file_size(500 * 1024 * 1024) == 'large'  # 500MB
        assert auto_tagger._categorize_file_size(5000 * 1024 * 1024) == 'very_large'  # 5GB

    def test_categorize_aspect_ratio(self, auto_tagger):
        """Test aspect ratio categorization"""
        assert auto_tagger._categorize_aspect_ratio(1.0) == 'square'
        assert auto_tagger._categorize_aspect_ratio(0.8) == 'portrait'
        assert auto_tagger._categorize_aspect_ratio(1.3) == 'landscape'
        assert auto_tagger._categorize_aspect_ratio(1.8) == 'wide'
        assert auto_tagger._categorize_aspect_ratio(2.5) == 'ultra_wide'

    @pytest.mark.asyncio
    async def test_store_tags(self, auto_tagger, mock_db):
        """Test storing tags in database"""
        tags = [
            AutoTag(
                asset_id='asset123',
                tag_name='person',
                category=TagCategory.OBJECT,
                confidence=0.9,
                source=TagSource.YOLO,
                metadata={}
            )
        ]
        
        await auto_tagger._store_tags(tags)
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_moderation_result(self, auto_tagger, mock_db):
        """Test storing moderation results"""
        results = [
            {'label': 'safe', 'score': 0.9},
            {'label': 'nsfw', 'score': 0.1}
        ]
        
        await auto_tagger._store_moderation_result('asset123', results)
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in auto-tagger"""
    mock_db = AsyncMock()
    mock_redis = AsyncMock()
    auto_tagger = AutoTagger(db=mock_db, redis=mock_redis)
    
    # Test with invalid file path
    with patch('cv2.imread', return_value=None):
        tags = await auto_tagger._analyze_image('/invalid/path', 'asset123')
        assert tags == []

    # Test with exception in object detection
    with patch('cv2.imread', return_value=np.zeros((100, 100, 3))), \
         patch.object(auto_tagger, 'object_detection_model', side_effect=Exception("Model error")):
        
        # Should not raise exception, should return empty list
        tags = await auto_tagger._detect_objects_in_image(np.zeros((100, 100, 3)), 'asset123')
        assert tags == []


class TestAutoTaggerIntegration:
    """Integration tests for auto-tagger with real-like scenarios"""

    @pytest.mark.asyncio
    async def test_complete_image_workflow(self):
        """Test complete image auto-tagging workflow"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        auto_tagger = AutoTagger(db=mock_db, redis=mock_redis)
        
        # Mock a realistic image analysis scenario
        with patch('cv2.imread') as mock_imread, \
             patch.object(auto_tagger, '_load_models', new_callable=AsyncMock), \
             patch.object(auto_tagger, 'object_detection_model') as mock_yolo, \
             patch.object(auto_tagger, 'ocr_reader') as mock_ocr, \
             patch('sklearn.cluster.KMeans') as mock_kmeans:
            
            # Setup mocks
            mock_imread.return_value = np.ones((100, 100, 3), dtype=np.uint8) * 128
            
            # Mock YOLO detection
            mock_box = Mock()
            mock_box.cls = [0]
            mock_box.conf = [0.85]
            mock_box.xyxy = [[10, 20, 100, 200]]
            mock_result = Mock()
            mock_result.boxes = [mock_box]
            mock_yolo.return_value = [mock_result]
            mock_yolo.names = {0: 'person'}
            
            # Mock OCR
            mock_ocr.readtext.return_value = [
                ([(0, 0), (100, 0), (100, 30), (0, 30)], 'Test Text', 0.9)
            ]
            
            # Mock color clustering
            mock_kmeans_instance = Mock()
            mock_kmeans_instance.cluster_centers_ = np.array([[128, 128, 128]])
            mock_kmeans_instance.labels_ = np.zeros(10000)
            mock_kmeans.return_value = mock_kmeans_instance
            
            with patch('src.services.auto_tagger.settings') as mock_settings:
                mock_settings.AUTO_TAGGING_CONFIDENCE_THRESHOLD = 0.5
                mock_settings.MAX_AUTO_TAGS_PER_ASSET = 50
                
                await auto_tagger.initialize()
                
                # Run analysis
                tags = await auto_tagger.analyze_and_tag_asset(
                    asset_id='test_asset',
                    file_path='/path/to/test_image.jpg',
                    asset_type='image/jpeg'
                )
                
                # Verify we got various types of tags
                tag_categories = {tag.category for tag in tags}
                assert TagCategory.OBJECT in tag_categories  # From YOLO
                assert TagCategory.CONTENT in tag_categories  # From OCR
                assert TagCategory.VISUAL in tag_categories   # From color analysis
                assert TagCategory.TECHNICAL in tag_categories  # From composition
                
                # Verify tags have proper structure
                for tag in tags:
                    assert hasattr(tag, 'asset_id')
                    assert hasattr(tag, 'tag_name')
                    assert hasattr(tag, 'confidence')
                    assert 0 <= tag.confidence <= 1
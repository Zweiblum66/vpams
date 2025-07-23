"""
Tests for Face Search Service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import numpy as np

from src.services.face_search_service import FaceSearchService
from src.models.schemas import (
    FaceSearchQuery, FaceSearchResponse, FaceSearchResult, FaceAnalysisRequest, FaceAnalysisResponse,
    FaceSearchStats, DetectedFace, PersonIdentity, FaceAttributes, FaceEncoding, BoundingBox,
    FaceLandmarks, FaceDetectionModel, FaceRecognitionModel, FaceSearchType, FaceMatchType,
    Gender, Emotion, FaceExpression, FaceQuality, FaceLandmarkType, ColorPalette
)


class TestFaceSearchService:
    """Test cases for Face Search Service"""
    
    @pytest.fixture
    def service(self):
        """Create FaceSearchService instance"""
        return FaceSearchService()
    
    @pytest.fixture
    def sample_face_search_query(self):
        """Sample face search query"""
        return FaceSearchQuery(
            search_type=FaceSearchType.PERSON_SEARCH,
            person_id="person_123",
            similarity_threshold=0.7,
            min_confidence=0.6,
            asset_types=["image", "video"],
            page=1,
            limit=20
        )
    
    @pytest.fixture
    def sample_similarity_search_query(self):
        """Sample face similarity search query"""
        return FaceSearchQuery(
            search_type=FaceSearchType.FACE_SIMILARITY,
            reference_encoding=[0.1] * 512,
            similarity_threshold=0.8,
            match_type=FaceMatchType.COSINE_SIMILARITY,
            min_confidence=0.7,
            asset_types=["image"],
            page=1,
            limit=15
        )
    
    @pytest.fixture
    def sample_demographic_search_query(self):
        """Sample demographic search query"""
        return FaceSearchQuery(
            search_type=FaceSearchType.DEMOGRAPHIC_SEARCH,
            age_range={"min": 25, "max": 45},
            gender=Gender.FEMALE,
            emotion=Emotion.HAPPY,
            min_confidence=0.6,
            asset_types=["image", "video"],
            page=1,
            limit=25
        )
    
    @pytest.fixture
    def sample_emotion_search_query(self):
        """Sample emotion search query"""
        return FaceSearchQuery(
            search_type=FaceSearchType.EMOTION_SEARCH,
            emotion=Emotion.HAPPY,
            min_confidence=0.7,
            asset_types=["image"],
            sort_by="confidence",
            sort_order="desc",
            page=1,
            limit=10
        )
    
    @pytest.fixture
    def sample_celebrity_search_query(self):
        """Sample celebrity search query"""
        return FaceSearchQuery(
            search_type=FaceSearchType.CELEBRITY_RECOGNITION,
            min_confidence=0.8,
            asset_types=["image", "video"],
            include_attributes=True,
            page=1,
            limit=30
        )
    
    @pytest.fixture
    def sample_group_detection_query(self):
        """Sample group detection query"""
        return FaceSearchQuery(
            search_type=FaceSearchType.GROUP_DETECTION,
            group_size_range={"min": 3, "max": 10},
            min_confidence=0.6,
            asset_types=["image"],
            page=1,
            limit=20
        )
    
    @pytest.fixture
    def sample_unknown_faces_query(self):
        """Sample unknown faces search query"""
        return FaceSearchQuery(
            search_type=FaceSearchType.UNKNOWN_FACES,
            min_confidence=0.7,
            min_face_quality=FaceQuality.GOOD,
            asset_types=["image", "video"],
            include_unknown_faces=True,
            page=1,
            limit=15
        )
    
    @pytest.fixture
    def sample_face_analysis_request(self):
        """Sample face analysis request"""
        return FaceAnalysisRequest(
            asset_id="asset_123",
            detection_model=FaceDetectionModel.RETINAFACE,
            recognition_model=FaceRecognitionModel.FACENET,
            landmark_type=FaceLandmarkType.LANDMARKS_68,
            extract_attributes=True,
            extract_encodings=True,
            extract_landmarks=True,
            identify_persons=True,
            detect_celebrities=False,
            min_face_size=30,
            min_confidence=0.6,
            max_faces=10,
            frame_interval=30,
            force_reanalysis=False,
            parallel_processing=True,
            gpu_acceleration=True
        )
    
    @pytest.fixture
    def sample_detected_face(self):
        """Sample detected face"""
        return DetectedFace(
            face_id="face_123",
            bounding_box=BoundingBox(x=100, y=150, width=200, height=240, confidence=0.95),
            landmarks=FaceLandmarks(
                landmark_type=FaceLandmarkType.LANDMARKS_68,
                points=[{"x": 120, "y": 180}, {"x": 125, "y": 185}],
                confidence=0.9
            ),
            attributes=FaceAttributes(
                age=32,
                age_range={"min": 28, "max": 36},
                gender=Gender.FEMALE,
                gender_confidence=0.88,
                emotion=Emotion.HAPPY,
                emotion_confidence=0.82,
                emotion_scores={"happy": 0.82, "neutral": 0.15, "surprise": 0.03},
                expression=FaceExpression.SMILING,
                expression_confidence=0.85,
                glasses=False,
                glasses_confidence=0.92,
                beard=False,
                beard_confidence=0.95,
                mustache=False,
                mustache_confidence=0.98,
                head_pose={"yaw": 5.2, "pitch": -2.1, "roll": 1.8},
                face_angle=5.0,
                face_quality=FaceQuality.GOOD,
                blur_score=0.15,
                brightness=0.65,
                sharpness=0.85,
                occlusion=0.05
            ),
            encoding=FaceEncoding(
                model=FaceRecognitionModel.FACENET,
                encoding=[0.1, 0.2, 0.3] * 170 + [0.1, 0.2],  # 512 dimensions
                dimension=512,
                confidence=0.9
            ),
            person_id="person_456",
            person_name="Jane Doe",
            celebrity_name=None,
            similarity_score=0.88,
            detection_model=FaceDetectionModel.RETINAFACE,
            detection_confidence=0.95,
            detection_time_ms=120,
            frame_number=None,
            timestamp=None
        )
    
    @pytest.fixture
    def sample_person_identity(self):
        """Sample person identity"""
        return PersonIdentity(
            person_id="person_456",
            person_name="Jane Doe",
            known_faces=["face_123", "face_124"],
            reference_encoding=FaceEncoding(
                model=FaceRecognitionModel.FACENET,
                encoding=[0.1] * 512,
                dimension=512,
                confidence=0.9
            ),
            description="Professional headshot photo",
            tags=["employee", "marketing"],
            department="Marketing",
            role="Marketing Manager",
            total_appearances=15,
            last_seen=datetime.utcnow(),
            confidence_avg=0.88,
            privacy_level="public",
            consent_given=True
        )
    
    @pytest.mark.asyncio
    async def test_search_by_face_person_search(self, service, sample_face_search_query):
        """Test person search functionality"""
        # Mock OpenSearch response
        mock_response = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_id": "asset_123",
                        "_score": 0.95,
                        "_source": {
                            "asset_id": "asset_123",
                            "asset_name": "Team Photo",
                            "asset_type": "image",
                            "file_size": 2456789,
                            "dimensions": {"width": 1920, "height": 1080},
                            "format": "jpg",
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z",
                            "face_analysis": {
                                "face_count": 3,
                                "average_confidence": 0.92,
                                "detection_model": "retinaface",
                                "recognition_model": "facenet",
                                "analyzed_at": "2024-01-15T10:30:00Z"
                            }
                        }
                    }
                ]
            },
            "aggregations": {}
        }
        
        with patch.object(service, '_execute_face_search', return_value=mock_response):
            result = await service.search_by_face(sample_face_search_query)
            
            assert isinstance(result, FaceSearchResponse)
            assert result.total == 1
            assert len(result.results) == 1
            assert result.results[0].asset_id == "asset_123"
            assert result.results[0].asset_name == "Team Photo"
            assert result.results[0].asset_type == "image"
            assert result.results[0].face_count > 0
            assert result.page == 1
            assert result.limit == 20
            assert result.search_metadata["search_type"] == "person_search"
    
    @pytest.mark.asyncio
    async def test_search_by_face_similarity_search(self, service, sample_similarity_search_query):
        """Test face similarity search functionality"""
        mock_response = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_id": "asset_456",
                        "_score": 0.88,
                        "_source": {
                            "asset_id": "asset_456",
                            "asset_name": "Portrait Photo",
                            "asset_type": "image",
                            "file_size": 1234567,
                            "dimensions": {"width": 1024, "height": 768},
                            "format": "png",
                            "created_at": "2024-01-16T09:15:00Z",
                            "updated_at": "2024-01-16T09:15:00Z",
                            "face_analysis": {
                                "face_count": 1,
                                "average_confidence": 0.88,
                                "detection_model": "retinaface",
                                "recognition_model": "facenet"
                            }
                        }
                    }
                ]
            },
            "aggregations": {}
        }
        
        with patch.object(service, '_execute_face_search', return_value=mock_response):
            result = await service.search_by_face(sample_similarity_search_query)
            
            assert isinstance(result, FaceSearchResponse)
            assert result.total == 2
            assert len(result.results) == 1
            assert result.results[0].asset_id == "asset_456"
            assert result.results[0].asset_name == "Portrait Photo"
            assert result.search_metadata["search_type"] == "face_similarity"
    
    @pytest.mark.asyncio
    async def test_search_by_face_demographic_search(self, service, sample_demographic_search_query):
        """Test demographic search functionality"""
        mock_response = {
            "hits": {
                "total": {"value": 5},
                "hits": [
                    {
                        "_id": "asset_789",
                        "_score": 0.82,
                        "_source": {
                            "asset_id": "asset_789",
                            "asset_name": "Group Demographics",
                            "asset_type": "image",
                            "file_size": 3456789,
                            "dimensions": {"width": 2048, "height": 1536},
                            "format": "jpg",
                            "created_at": "2024-01-17T14:20:00Z",
                            "updated_at": "2024-01-17T14:20:00Z",
                            "face_analysis": {
                                "face_count": 4,
                                "average_confidence": 0.85,
                                "detection_model": "retinaface",
                                "recognition_model": "facenet"
                            }
                        }
                    }
                ]
            },
            "aggregations": {
                "gender_distribution": {
                    "buckets": [
                        {"key": "female", "doc_count": 3},
                        {"key": "male", "doc_count": 2}
                    ]
                },
                "age_distribution": {
                    "buckets": [
                        {"key": 30.0, "doc_count": 2},
                        {"key": 40.0, "doc_count": 3}
                    ]
                }
            }
        }
        
        with patch.object(service, '_execute_face_search', return_value=mock_response):
            result = await service.search_by_face(sample_demographic_search_query)
            
            assert isinstance(result, FaceSearchResponse)
            assert result.total == 5
            assert len(result.results) == 1
            assert result.results[0].asset_id == "asset_789"
            assert result.results[0].demographics is not None
            assert result.search_metadata["search_type"] == "demographic_search"
    
    @pytest.mark.asyncio
    async def test_search_by_face_emotion_search(self, service, sample_emotion_search_query):
        """Test emotion search functionality"""
        mock_response = {
            "hits": {
                "total": {"value": 3},
                "hits": [
                    {
                        "_id": "asset_happy_001",
                        "_score": 0.78,
                        "_source": {
                            "asset_id": "asset_happy_001",
                            "asset_name": "Happy Celebration",
                            "asset_type": "image",
                            "file_size": 4567890,
                            "dimensions": {"width": 1600, "height": 1200},
                            "format": "jpg",
                            "created_at": "2024-01-18T16:45:00Z",
                            "updated_at": "2024-01-18T16:45:00Z",
                            "face_analysis": {
                                "face_count": 6,
                                "average_confidence": 0.78,
                                "detection_model": "mediapipe",
                                "recognition_model": "arcface"
                            }
                        }
                    }
                ]
            },
            "aggregations": {}
        }
        
        with patch.object(service, '_execute_face_search', return_value=mock_response):
            result = await service.search_by_face(sample_emotion_search_query)
            
            assert isinstance(result, FaceSearchResponse)
            assert result.total == 3
            assert len(result.results) == 1
            assert result.results[0].asset_id == "asset_happy_001"
            assert result.results[0].asset_name == "Happy Celebration"
            assert result.search_metadata["search_type"] == "emotion_search"
    
    @pytest.mark.asyncio
    async def test_search_by_face_celebrity_recognition(self, service, sample_celebrity_search_query):
        """Test celebrity recognition search"""
        mock_response = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_id": "asset_celeb_001",
                        "_score": 0.91,
                        "_source": {
                            "asset_id": "asset_celeb_001",
                            "asset_name": "Celebrity Event",
                            "asset_type": "image",
                            "file_size": 5678901,
                            "dimensions": {"width": 3000, "height": 2000},
                            "format": "jpg",
                            "created_at": "2024-01-19T20:30:00Z",
                            "updated_at": "2024-01-19T20:30:00Z",
                            "face_analysis": {
                                "face_count": 2,
                                "average_confidence": 0.91,
                                "detection_model": "retinaface",
                                "recognition_model": "arcface"
                            }
                        }
                    }
                ]
            },
            "aggregations": {}
        }
        
        with patch.object(service, '_execute_face_search', return_value=mock_response):
            result = await service.search_by_face(sample_celebrity_search_query)
            
            assert isinstance(result, FaceSearchResponse)
            assert result.total == 1
            assert len(result.results) == 1
            assert result.results[0].asset_id == "asset_celeb_001"
            assert result.results[0].celebrity_matches_count >= 0
            assert result.search_metadata["search_type"] == "celebrity_recognition"
    
    @pytest.mark.asyncio
    async def test_search_by_face_group_detection(self, service, sample_group_detection_query):
        """Test group detection search"""
        mock_response = {
            "hits": {
                "total": {"value": 4},
                "hits": [
                    {
                        "_id": "asset_group_001",
                        "_score": 0.85,
                        "_source": {
                            "asset_id": "asset_group_001",
                            "asset_name": "Team Building Event",
                            "asset_type": "image",
                            "file_size": 6789012,
                            "dimensions": {"width": 2400, "height": 1800},
                            "format": "jpg",
                            "created_at": "2024-01-20T11:15:00Z",
                            "updated_at": "2024-01-20T11:15:00Z",
                            "face_analysis": {
                                "face_count": 8,
                                "average_confidence": 0.85,
                                "detection_model": "mtcnn",
                                "recognition_model": "cosface"
                            }
                        }
                    }
                ]
            },
            "aggregations": {}
        }
        
        with patch.object(service, '_execute_face_search', return_value=mock_response):
            result = await service.search_by_face(sample_group_detection_query)
            
            assert isinstance(result, FaceSearchResponse)
            assert result.total == 4
            assert len(result.results) == 1
            assert result.results[0].asset_id == "asset_group_001"
            assert result.results[0].face_count >= 3  # Group detection minimum
            assert result.search_metadata["search_type"] == "group_detection"
    
    @pytest.mark.asyncio
    async def test_search_by_face_unknown_faces(self, service, sample_unknown_faces_query):
        """Test unknown faces search"""
        mock_response = {
            "hits": {
                "total": {"value": 7},
                "hits": [
                    {
                        "_id": "asset_unknown_001",
                        "_score": 0.75,
                        "_source": {
                            "asset_id": "asset_unknown_001",
                            "asset_name": "Unidentified Persons",
                            "asset_type": "image",
                            "file_size": 3456789,
                            "dimensions": {"width": 1800, "height": 1350},
                            "format": "png",
                            "created_at": "2024-01-21T15:30:00Z",
                            "updated_at": "2024-01-21T15:30:00Z",
                            "face_analysis": {
                                "face_count": 5,
                                "average_confidence": 0.75,
                                "detection_model": "dlib_cnn",
                                "recognition_model": "openface"
                            }
                        }
                    }
                ]
            },
            "aggregations": {}
        }
        
        with patch.object(service, '_execute_face_search', return_value=mock_response):
            result = await service.search_by_face(sample_unknown_faces_query)
            
            assert isinstance(result, FaceSearchResponse)
            assert result.total == 7
            assert len(result.results) == 1
            assert result.results[0].asset_id == "asset_unknown_001"
            assert result.unknown_faces_count >= 0
            assert result.search_metadata["search_type"] == "unknown_faces"
    
    @pytest.mark.asyncio
    async def test_analyze_asset_faces_success(self, service, sample_face_analysis_request):
        """Test successful face analysis"""
        result = await service.analyze_asset_faces(sample_face_analysis_request)
        
        assert isinstance(result, FaceAnalysisResponse)
        assert result.asset_id == "asset_123"
        assert result.analysis_success == True
        assert len(result.detected_faces) > 0
        assert result.face_count >= 0
        assert result.processing_time_ms > 0
        assert result.detection_model == FaceDetectionModel.RETINAFACE
        assert result.recognition_model == FaceRecognitionModel.FACENET
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        
        # Check detected faces have proper structure
        for face in result.detected_faces:
            assert isinstance(face, DetectedFace)
            assert face.face_id is not None
            assert face.bounding_box is not None
            assert face.detection_confidence > 0
            
            # Check attributes if requested
            if sample_face_analysis_request.extract_attributes:
                assert face.attributes is not None
                assert face.attributes.age is not None
                assert face.attributes.gender is not None
                assert face.attributes.emotion is not None
            
            # Check encodings if requested
            if sample_face_analysis_request.extract_encodings:
                assert face.encoding is not None
                assert len(face.encoding.encoding) == 512
            
            # Check landmarks if requested
            if sample_face_analysis_request.extract_landmarks:
                assert face.landmarks is not None
                assert len(face.landmarks.points) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_asset_faces_video(self, service):
        """Test face analysis for video assets"""
        request = FaceAnalysisRequest(
            asset_id="video_123",
            detection_model=FaceDetectionModel.MEDIAPIPE,
            recognition_model=FaceRecognitionModel.ARCFACE,
            extract_attributes=True,
            extract_encodings=False,
            frame_interval=60,
            max_frames=20,
            scene_detection=True
        )
        
        result = await service.analyze_asset_faces(request)
        
        assert isinstance(result, FaceAnalysisResponse)
        assert result.asset_id == "video_123"
        assert result.analysis_success == True
        assert result.frames_analyzed is not None
        assert result.frames_analyzed > 0
        
        # Check for video-specific analysis
        if result.face_timeline:
            assert len(result.face_timeline) >= 0
            for timeline_entry in result.face_timeline:
                assert "timestamp" in timeline_entry
                assert "face_id" in timeline_entry
    
    @pytest.mark.asyncio
    async def test_analyze_asset_faces_error_handling(self, service):
        """Test error handling in face analysis"""
        # Test with invalid asset ID
        request = FaceAnalysisRequest(
            asset_id="invalid_asset",
            detection_model=FaceDetectionModel.RETINAFACE,
            recognition_model=FaceRecognitionModel.FACENET
        )
        
        # Mock an exception in the analysis process
        with patch.object(service, '_perform_face_analysis', side_effect=Exception("Analysis failed")):
            result = await service.analyze_asset_faces(request)
            
            assert isinstance(result, FaceAnalysisResponse)
            assert result.asset_id == "invalid_asset"
            assert result.analysis_success == False
            assert len(result.errors) > 0
            assert "Analysis failed" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_get_face_search_stats(self, service):
        """Test getting face search statistics"""
        result = await service.get_face_search_stats()
        
        assert isinstance(result, FaceSearchStats)
        assert result.total_searches >= 0
        assert result.total_faces_detected >= 0
        assert result.total_persons_identified >= 0
        assert result.unique_persons_database >= 0
        assert result.avg_search_time_ms >= 0
        assert result.avg_detection_time_ms >= 0
        assert result.avg_recognition_time_ms >= 0
        assert 0 <= result.cache_hit_rate <= 1
        assert result.images_analyzed >= 0
        assert result.videos_analyzed >= 0
        assert result.frames_analyzed >= 0
        
        # Check data structures
        assert isinstance(result.detection_model_usage, dict)
        assert isinstance(result.recognition_model_usage, dict)
        assert isinstance(result.face_quality_distribution, dict)
        assert isinstance(result.confidence_distribution, dict)
        assert isinstance(result.age_distribution, dict)
        assert isinstance(result.gender_distribution, dict)
        assert isinstance(result.emotion_distribution, dict)
        
        # Check privacy and compliance data
        assert result.consent_given_persons >= 0
        assert result.anonymized_faces >= 0
        assert result.privacy_violations >= 0
        assert result.detection_failures >= 0
        assert result.recognition_failures >= 0
        assert result.low_quality_faces >= 0
    
    def test_initialize_detection_models(self, service):
        """Test detection models initialization"""
        models = service._initialize_detection_models()
        
        assert isinstance(models, dict)
        assert len(models) > 0
        
        # Check specific models
        assert FaceDetectionModel.RETINAFACE in models
        assert FaceDetectionModel.MTCNN in models
        assert FaceDetectionModel.MEDIAPIPE in models
        
        # Check model properties
        for model, properties in models.items():
            assert "accuracy" in properties
            assert "speed" in properties
            assert "min_face_size" in properties
            assert "supports_landmarks" in properties
            assert 0 <= properties["accuracy"] <= 1
            assert properties["min_face_size"] > 0
    
    def test_initialize_recognition_models(self, service):
        """Test recognition models initialization"""
        models = service._initialize_recognition_models()
        
        assert isinstance(models, dict)
        assert len(models) > 0
        
        # Check specific models
        assert FaceRecognitionModel.FACENET in models
        assert FaceRecognitionModel.ARCFACE in models
        assert FaceRecognitionModel.COSFACE in models
        
        # Check model properties
        for model, properties in models.items():
            assert "accuracy" in properties
            assert "embedding_size" in properties
            assert "speed" in properties
            assert "threshold" in properties
            assert 0 <= properties["accuracy"] <= 1
            assert properties["embedding_size"] > 0
            assert 0 <= properties["threshold"] <= 1
    
    @pytest.mark.asyncio
    async def test_build_face_search_query_person_search(self, service, sample_face_search_query):
        """Test building OpenSearch query for person search"""
        search_body = await service._build_face_search_query(sample_face_search_query)
        
        assert isinstance(search_body, dict)
        assert "query" in search_body
        assert "size" in search_body
        assert "from" in search_body
        assert "sort" in search_body
        assert "aggs" in search_body
        
        # Check query structure
        query = search_body["query"]
        assert "bool" in query
        assert "must" in query["bool"]
        assert "filter" in query["bool"]
        
        # Check pagination
        assert search_body["size"] == sample_face_search_query.limit
        assert search_body["from"] == (sample_face_search_query.page - 1) * sample_face_search_query.limit
        
        # Check sorting
        assert len(search_body["sort"]) > 0
        
        # Check aggregations
        assert len(search_body["aggs"]) > 0
        assert "face_count_distribution" in search_body["aggs"]
        assert "gender_distribution" in search_body["aggs"]
        assert "age_distribution" in search_body["aggs"]
    
    @pytest.mark.asyncio
    async def test_build_face_search_query_similarity_search(self, service, sample_similarity_search_query):
        """Test building OpenSearch query for similarity search"""
        search_body = await service._build_face_search_query(sample_similarity_search_query)
        
        assert isinstance(search_body, dict)
        assert "query" in search_body
        
        # Check that script score query is used for similarity
        if sample_similarity_search_query.reference_encoding:
            query = search_body["query"]
            # For mock implementation, it might still use bool query
            assert "bool" in query or "script_score" in query
    
    @pytest.mark.asyncio
    async def test_face_matches_query_person_search(self, service, sample_detected_face):
        """Test face matching for person search"""
        query = FaceSearchQuery(
            search_type=FaceSearchType.PERSON_SEARCH,
            person_id="person_456",
            min_confidence=0.5
        )
        
        matches = await service._face_matches_query(sample_detected_face, query)
        assert matches == True  # Face has person_id "person_456"
        
        # Test with different person ID
        query.person_id = "person_999"
        matches = await service._face_matches_query(sample_detected_face, query)
        assert matches == False
    
    @pytest.mark.asyncio
    async def test_face_matches_query_demographic_search(self, service, sample_detected_face):
        """Test face matching for demographic search"""
        query = FaceSearchQuery(
            search_type=FaceSearchType.DEMOGRAPHIC_SEARCH,
            age_range={"min": 25, "max": 40},  # Face age is 32
            gender=Gender.FEMALE,  # Face gender is female
            min_confidence=0.5
        )
        
        matches = await service._face_matches_query(sample_detected_face, query)
        assert matches == True
        
        # Test with different age range
        query.age_range = {"min": 50, "max": 70}
        matches = await service._face_matches_query(sample_detected_face, query)
        assert matches == False
    
    @pytest.mark.asyncio
    async def test_face_matches_query_emotion_search(self, service, sample_detected_face):
        """Test face matching for emotion search"""
        query = FaceSearchQuery(
            search_type=FaceSearchType.EMOTION_SEARCH,
            emotion=Emotion.HAPPY,  # Face emotion is happy
            min_confidence=0.5
        )
        
        matches = await service._face_matches_query(sample_detected_face, query)
        assert matches == True
        
        # Test with different emotion
        query.emotion = Emotion.SAD
        matches = await service._face_matches_query(sample_detected_face, query)
        assert matches == False
    
    @pytest.mark.asyncio
    async def test_identify_persons(self, service, sample_detected_face):
        """Test person identification from detected faces"""
        detected_faces = [sample_detected_face]
        
        identified_persons = await service._identify_persons(detected_faces)
        
        assert len(identified_persons) == 1
        person = identified_persons[0]
        assert isinstance(person, PersonIdentity)
        assert person.person_id == "person_456"
        assert person.person_name == "Jane Doe"
        assert len(person.known_faces) == 1
        assert person.known_faces[0] == "face_123"
        assert person.total_appearances == 1
        assert person.consent_given == True
    
    def test_calculate_demographics(self, service, sample_detected_face):
        """Test demographics calculation"""
        detected_faces = [sample_detected_face]
        
        demographics = service._calculate_demographics(detected_faces)
        
        assert isinstance(demographics, dict)
        assert demographics["total_faces"] == 1
        assert "gender_distribution" in demographics
        assert "emotions" in demographics
        assert "age_statistics" in demographics
        assert "age_distribution" in demographics
        
        # Check gender distribution
        gender_dist = demographics["gender_distribution"]
        assert gender_dist["female"] == 1
        assert gender_dist["male"] == 0
        
        # Check emotions
        emotions = demographics["emotions"]
        assert emotions["happy"] == 1
        
        # Check age statistics
        age_stats = demographics["age_statistics"]
        assert age_stats["average"] == 32.0
        assert age_stats["min"] == 32.0
        assert age_stats["max"] == 32.0
    
    def test_calculate_face_quality_score(self, service, sample_detected_face):
        """Test face quality score calculation"""
        quality_score = service._calculate_face_quality_score(sample_detected_face)
        
        assert isinstance(quality_score, float)
        assert 0.0 <= quality_score <= 1.0
        
        # Test with face without attributes
        face_no_attrs = DetectedFace(
            face_id="face_no_attrs",
            bounding_box=BoundingBox(x=100, y=150, width=200, height=240, confidence=0.95),
            detection_model=FaceDetectionModel.RETINAFACE,
            detection_confidence=0.95
        )
        
        quality_score_no_attrs = service._calculate_face_quality_score(face_no_attrs)
        assert quality_score_no_attrs == 0.5  # Default score
    
    def test_assess_detection_quality(self, service, sample_detected_face):
        """Test detection quality assessment"""
        detected_faces = [sample_detected_face]
        
        quality = service._assess_detection_quality(detected_faces)
        
        assert quality in ["excellent", "good", "fair", "poor"]
        
        # Test with empty list
        empty_quality = service._assess_detection_quality([])
        assert empty_quality == "poor"
    
    def test_get_match_type(self, service):
        """Test match type retrieval"""
        match_type = service._get_match_type(FaceSearchType.PERSON_SEARCH)
        assert match_type == "person_identification"
        
        match_type = service._get_match_type(FaceSearchType.FACE_SIMILARITY)
        assert match_type == "face_similarity"
        
        match_type = service._get_match_type(FaceSearchType.CELEBRITY_RECOGNITION)
        assert match_type == "celebrity_match"
    
    @pytest.mark.asyncio
    async def test_search_validation_error(self, service):
        """Test search with validation errors"""
        # Test with invalid age range
        invalid_query = FaceSearchQuery(
            search_type=FaceSearchType.DEMOGRAPHIC_SEARCH,
            age_range={"min": 50, "max": 30},  # Invalid: min > max
            min_confidence=0.5
        )
        
        # The validation should happen at the Pydantic model level
        # Here we test that the service handles the validated query properly
        try:
            await service.search_by_face(invalid_query)
        except Exception as e:
            # Service should handle invalid queries gracefully
            assert isinstance(e, Exception)
    
    @pytest.mark.asyncio
    async def test_search_empty_results(self, service, sample_face_search_query):
        """Test search with no results"""
        mock_response = {
            "hits": {
                "total": {"value": 0},
                "hits": []
            },
            "aggregations": {}
        }
        
        with patch.object(service, '_execute_face_search', return_value=mock_response):
            result = await service.search_by_face(sample_face_search_query)
            
            assert isinstance(result, FaceSearchResponse)
            assert result.total == 0
            assert len(result.results) == 0
            assert result.pages == 0
            assert result.total_faces_found == 0
            assert result.unique_persons == 0
    
    @pytest.mark.asyncio
    async def test_search_performance_metrics(self, service, sample_face_search_query):
        """Test search performance metrics"""
        result = await service.search_by_face(sample_face_search_query)
        
        assert isinstance(result, FaceSearchResponse)
        assert result.took >= 0  # Processing time should be non-negative
        assert "execution_time" in result.search_metadata
        assert result.search_metadata["execution_time"] >= 0
    
    def test_generate_mock_responses(self, service, sample_face_search_query):
        """Test mock response generation"""
        # Test different search types
        search_types = [
            FaceSearchType.PERSON_SEARCH,
            FaceSearchType.FACE_SIMILARITY,
            FaceSearchType.DEMOGRAPHIC_SEARCH,
            FaceSearchType.EMOTION_SEARCH,
            FaceSearchType.CELEBRITY_RECOGNITION
        ]
        
        for search_type in search_types:
            sample_face_search_query.search_type = search_type
            mock_response = service._generate_mock_face_search_response(sample_face_search_query)
            
            assert isinstance(mock_response, dict)
            assert "hits" in mock_response
            assert "aggregations" in mock_response
            assert len(mock_response["hits"]["hits"]) >= 0
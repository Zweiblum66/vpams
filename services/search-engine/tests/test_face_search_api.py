"""
Tests for Face Search API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json
from datetime import datetime

from src.main import app
from src.models.schemas import (
    FaceSearchResponse, FaceSearchResult, FaceSearchStats, FaceAnalysisResponse,
    FaceSearchType, FaceDetectionModel, FaceRecognitionModel, FaceMatchType,
    Gender, Emotion, FaceExpression, FaceQuality, FaceLandmarkType,
    DetectedFace, PersonIdentity, FaceAttributes, FaceEncoding, BoundingBox, FaceLandmarks
)


class TestFaceSearchAPI:
    """Test cases for Face Search API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_person_search_data(self):
        """Sample person search request data"""
        return {
            "search_type": "person_search",
            "person_id": "person_123",
            "similarity_threshold": 0.7,
            "min_confidence": 0.6,
            "asset_types": ["image", "video"],
            "include_attributes": True,
            "include_encodings": False,
            "page": 1,
            "limit": 20
        }
    
    @pytest.fixture
    def sample_similarity_search_data(self):
        """Sample face similarity search request data"""
        return {
            "search_type": "face_similarity",
            "reference_encoding": [0.1] * 512,
            "similarity_threshold": 0.8,
            "match_type": "cosine_similarity",
            "min_confidence": 0.7,
            "asset_types": ["image"],
            "page": 1,
            "limit": 15
        }
    
    @pytest.fixture
    def sample_demographic_search_data(self):
        """Sample demographic search request data"""
        return {
            "search_type": "demographic_search",
            "age_range": {"min": 25, "max": 45},
            "gender": "female",
            "emotion": "happy",
            "min_confidence": 0.6,
            "asset_types": ["image", "video"],
            "include_attributes": True,
            "page": 1,
            "limit": 25
        }
    
    @pytest.fixture
    def sample_emotion_search_data(self):
        """Sample emotion search request data"""
        return {
            "search_type": "emotion_search",
            "emotion": "happy",
            "min_confidence": 0.7,
            "asset_types": ["image"],
            "sort_by": "confidence",
            "sort_order": "desc",
            "page": 1,
            "limit": 10
        }
    
    @pytest.fixture
    def sample_age_range_search_data(self):
        """Sample age range search request data"""
        return {
            "search_type": "age_range_search",
            "age_range": {"min": 18, "max": 35},
            "min_confidence": 0.65,
            "asset_types": ["image", "video"],
            "include_attributes": True,
            "page": 1,
            "limit": 20
        }
    
    @pytest.fixture
    def sample_gender_search_data(self):
        """Sample gender search request data"""
        return {
            "search_type": "gender_search",
            "gender": "male",
            "min_confidence": 0.7,
            "asset_types": ["image"],
            "page": 1,
            "limit": 15
        }
    
    @pytest.fixture
    def sample_expression_search_data(self):
        """Sample expression search request data"""
        return {
            "search_type": "expression_search",
            "expression": "smiling",
            "min_confidence": 0.6,
            "asset_types": ["image"],
            "page": 1,
            "limit": 12
        }
    
    @pytest.fixture
    def sample_face_count_search_data(self):
        """Sample face count search request data"""
        return {
            "search_type": "face_count",
            "min_face_count": 2,
            "max_face_count": 8,
            "min_confidence": 0.6,
            "asset_types": ["image", "video"],
            "page": 1,
            "limit": 18
        }
    
    @pytest.fixture
    def sample_group_detection_data(self):
        """Sample group detection search request data"""
        return {
            "search_type": "group_detection",
            "group_size_range": {"min": 3, "max": 10},
            "min_confidence": 0.6,
            "asset_types": ["image"],
            "include_attributes": True,
            "page": 1,
            "limit": 20
        }
    
    @pytest.fixture
    def sample_celebrity_search_data(self):
        """Sample celebrity recognition search request data"""
        return {
            "search_type": "celebrity_recognition",
            "min_confidence": 0.8,
            "asset_types": ["image", "video"],
            "include_attributes": True,
            "page": 1,
            "limit": 30
        }
    
    @pytest.fixture
    def sample_unknown_faces_data(self):
        """Sample unknown faces search request data"""
        return {
            "search_type": "unknown_faces",
            "min_confidence": 0.7,
            "min_face_quality": "good",
            "asset_types": ["image", "video"],
            "include_unknown_faces": True,
            "page": 1,
            "limit": 15
        }
    
    @pytest.fixture
    def sample_face_verification_data(self):
        """Sample face verification search request data"""
        return {
            "search_type": "face_verification",
            "person_id": "person_456",
            "reference_encoding": [0.2] * 512,
            "similarity_threshold": 0.75,
            "match_type": "euclidean_distance",
            "min_confidence": 0.8,
            "asset_types": ["image"],
            "page": 1,
            "limit": 5
        }
    
    @pytest.fixture
    def sample_search_response(self):
        """Sample face search response"""
        return FaceSearchResponse(
            results=[
                FaceSearchResult(
                    asset_id="asset-face-123",
                    asset_name="Team Meeting Photo",
                    asset_type="image",
                    detected_faces=[
                        DetectedFace(
                            face_id="face_001",
                            bounding_box=BoundingBox(x=100, y=150, width=200, height=240, confidence=0.95),
                            landmarks=FaceLandmarks(
                                landmark_type=FaceLandmarkType.LANDMARKS_68,
                                points=[{"x": 120, "y": 180}, {"x": 125, "y": 185}],
                                confidence=0.9
                            ),
                            attributes=FaceAttributes(
                                age=28,
                                age_range={"min": 25, "max": 31},
                                gender=Gender.FEMALE,
                                gender_confidence=0.92,
                                emotion=Emotion.HAPPY,
                                emotion_confidence=0.85,
                                emotion_scores={"happy": 0.85, "neutral": 0.12, "surprise": 0.03},
                                expression=FaceExpression.SMILING,
                                expression_confidence=0.88,
                                glasses=False,
                                glasses_confidence=0.95,
                                beard=False,
                                beard_confidence=0.98,
                                mustache=False,
                                mustache_confidence=0.99,
                                head_pose={"yaw": 2.1, "pitch": -1.5, "roll": 0.8},
                                face_angle=2.0,
                                face_quality=FaceQuality.EXCELLENT,
                                blur_score=0.08,
                                brightness=0.68,
                                sharpness=0.92,
                                occlusion=0.02
                            ),
                            encoding=FaceEncoding(
                                model=FaceRecognitionModel.FACENET,
                                encoding=[0.1, 0.2, 0.3] * 170 + [0.1, 0.2],
                                dimension=512,
                                confidence=0.94
                            ),
                            person_id="person_123",
                            person_name="Alice Johnson",
                            celebrity_name=None,
                            similarity_score=0.91,
                            detection_model=FaceDetectionModel.RETINAFACE,
                            detection_confidence=0.95,
                            detection_time_ms=125,
                            frame_number=None,
                            timestamp=None
                        )
                    ],
                    face_count=1,
                    matched_faces=[],
                    match_score=0.91,
                    match_type="person_identification",
                    best_match_confidence=0.95,
                    identified_persons=[
                        PersonIdentity(
                            person_id="person_123",
                            person_name="Alice Johnson",
                            known_faces=["face_001"],
                            reference_encoding=None,
                            description="Marketing team member",
                            tags=["employee", "marketing"],
                            department="Marketing",
                            role="Marketing Specialist",
                            total_appearances=12,
                            last_seen=datetime.utcnow(),
                            confidence_avg=0.89,
                            privacy_level="public",
                            consent_given=True
                        )
                    ],
                    unknown_faces=[],
                    celebrity_matches=[],
                    demographics={
                        "total_faces": 1,
                        "gender_distribution": {"female": 1, "male": 0, "unknown": 0},
                        "emotions": {"happy": 1},
                        "age_statistics": {"min": 28, "max": 28, "average": 28.0}
                    },
                    emotions_summary={"happy": 1},
                    age_distribution={"21-40": 1},
                    gender_distribution={"female": 1},
                    face_timeline=None,
                    scene_faces=None,
                    average_face_quality=0.85,
                    detection_quality="excellent",
                    file_size=2456789,
                    dimensions={"width": 1920, "height": 1080},
                    duration=None,
                    format="jpg",
                    processing_time_ms=1250,
                    detection_model=FaceDetectionModel.RETINAFACE,
                    recognition_model=FaceRecognitionModel.FACENET,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    analyzed_at=datetime.utcnow()
                )
            ],
            total=1,
            took=185,
            page=1,
            limit=20,
            pages=1,
            aggregations={},
            total_faces_found=1,
            unique_persons=1,
            unknown_faces_count=0,
            celebrity_matches_count=0,
            quality_distribution={"excellent": 1},
            confidence_distribution={"high": 1},
            overall_demographics={
                "total_faces": 1,
                "gender_distribution": {"female": 1},
                "emotions": {"happy": 1}
            },
            search_metadata={"search_type": "person_search", "execution_time": 0.185}
        )
    
    @pytest.fixture
    def sample_analysis_request_data(self):
        """Sample face analysis request data"""
        return {
            "asset_id": "asset_123",
            "detection_model": "retinaface",
            "recognition_model": "facenet",
            "landmark_type": "landmarks_68",
            "extract_attributes": True,
            "extract_encodings": True,
            "extract_landmarks": True,
            "identify_persons": True,
            "detect_celebrities": False,
            "min_face_size": 30,
            "min_confidence": 0.6,
            "max_faces": 10,
            "frame_interval": 30,
            "max_frames": 100,
            "scene_detection": False,
            "force_reanalysis": False,
            "parallel_processing": True,
            "gpu_acceleration": True,
            "anonymize_unknown": False,
            "respect_privacy_settings": True
        }
    
    @patch('src.services.face_search_service.get_face_search_service')
    def test_search_by_face_person_search(self, mock_get_service, client, sample_person_search_data, sample_search_response):
        """Test person search endpoint"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_face.return_value = sample_search_response
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/face", json=sample_person_search_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["asset_id"] == "asset-face-123"
        assert data["results"][0]["asset_name"] == "Team Meeting Photo"
        assert data["results"][0]["asset_type"] == "image"
        assert data["results"][0]["face_count"] == 1
        assert data["results"][0]["match_score"] == 0.91
        assert data["results"][0]["match_type"] == "person_identification"
        assert len(data["results"][0]["detected_faces"]) == 1
        assert len(data["results"][0]["identified_persons"]) == 1
        assert data["took"] == 185
        assert data["search_metadata"]["search_type"] == "person_search"
        
        # Verify service was called
        mock_service.search_by_face.assert_called_once()
    
    @patch('src.services.face_search_service.get_face_search_service')
    def test_search_by_face_similarity_search(self, mock_get_service, client, sample_similarity_search_data):
        """Test face similarity search endpoint"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_face.return_value = FaceSearchResponse(
            results=[],
            total=0,
            took=95,
            page=1,
            limit=15,
            pages=0,
            aggregations={},
            total_faces_found=0,
            unique_persons=0,
            unknown_faces_count=0,
            celebrity_matches_count=0,
            search_metadata={"search_type": "face_similarity"}
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/face", json=sample_similarity_search_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["results"]) == 0
        assert data["search_metadata"]["search_type"] == "face_similarity"
        assert data["took"] == 95
        assert data["limit"] == 15
        
        # Verify service was called with correct parameters
        mock_service.search_by_face.assert_called_once()
        call_args = mock_service.search_by_face.call_args[0][0]
        assert call_args.search_type.value == "face_similarity"
        assert call_args.reference_encoding == [0.1] * 512
        assert call_args.similarity_threshold == 0.8
        assert call_args.match_type.value == "cosine_similarity"
    
    @patch('src.services.face_search_service.get_face_search_service')
    def test_search_by_face_demographic_search(self, mock_get_service, client, sample_demographic_search_data):
        """Test demographic search endpoint"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_face.return_value = FaceSearchResponse(
            results=[],
            total=8,
            took=125,
            page=1,
            limit=25,
            pages=1,
            aggregations={},
            total_faces_found=15,
            unique_persons=5,
            unknown_faces_count=3,
            celebrity_matches_count=0,
            overall_demographics={
                "gender_distribution": {"female": 10, "male": 5},
                "emotions": {"happy": 12, "neutral": 3}
            },
            search_metadata={"search_type": "demographic_search"}
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/face", json=sample_demographic_search_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 8
        assert data["total_faces_found"] == 15
        assert data["unique_persons"] == 5
        assert data["search_metadata"]["search_type"] == "demographic_search"
        assert "overall_demographics" in data
        
        # Verify service was called with correct parameters
        mock_service.search_by_face.assert_called_once()
        call_args = mock_service.search_by_face.call_args[0][0]
        assert call_args.search_type.value == "demographic_search"
        assert call_args.age_range == {"min": 25, "max": 45}
        assert call_args.gender.value == "female"
        assert call_args.emotion.value == "happy"
    
    @patch('src.services.face_search_service.get_face_search_service')
    def test_search_by_face_emotion_search(self, mock_get_service, client, sample_emotion_search_data):
        """Test emotion search endpoint"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_face.return_value = FaceSearchResponse(
            results=[],
            total=12,
            took=75,
            page=1,
            limit=10,
            pages=2,
            aggregations={},
            total_faces_found=18,
            unique_persons=8,
            unknown_faces_count=2,
            celebrity_matches_count=0,
            search_metadata={"search_type": "emotion_search"}
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/face", json=sample_emotion_search_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 12
        assert data["pages"] == 2
        assert data["search_metadata"]["search_type"] == "emotion_search"
        
        # Verify service was called with correct parameters
        mock_service.search_by_face.assert_called_once()
        call_args = mock_service.search_by_face.call_args[0][0]
        assert call_args.search_type.value == "emotion_search"
        assert call_args.emotion.value == "happy"
        assert call_args.sort_by == "confidence"
        assert call_args.sort_order.value == "desc"
    
    @patch('src.services.face_search_service.get_face_search_service')
    def test_search_by_face_age_range_search(self, mock_get_service, client, sample_age_range_search_data):
        """Test age range search endpoint"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_face.return_value = FaceSearchResponse(
            results=[],
            total=22,
            took=110,
            page=1,
            limit=20,
            pages=2,
            aggregations={},
            total_faces_found=35,
            unique_persons=15,
            unknown_faces_count=8,
            celebrity_matches_count=1,
            search_metadata={"search_type": "age_range_search"}
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/face", json=sample_age_range_search_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 22
        assert data["total_faces_found"] == 35
        assert data["unique_persons"] == 15
        assert data["celebrity_matches_count"] == 1
        assert data["search_metadata"]["search_type"] == "age_range_search"
        
        # Verify service was called
        mock_service.search_by_face.assert_called_once()
        call_args = mock_service.search_by_face.call_args[0][0]
        assert call_args.search_type.value == "age_range_search"
        assert call_args.age_range == {"min": 18, "max": 35}
    
    @patch('src.services.face_search_service.get_face_search_service')
    def test_search_by_face_gender_search(self, mock_get_service, client, sample_gender_search_data):
        """Test gender search endpoint"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_face.return_value = FaceSearchResponse(
            results=[],
            total=18,
            took=88,
            page=1,
            limit=15,
            pages=2,
            aggregations={},
            total_faces_found=25,
            unique_persons=12,
            unknown_faces_count=5,
            celebrity_matches_count=0,
            search_metadata={"search_type": "gender_search"}
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/face", json=sample_gender_search_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 18
        assert data["search_metadata"]["search_type"] == "gender_search"
        
        # Verify service was called
        mock_service.search_by_face.assert_called_once()
        call_args = mock_service.search_by_face.call_args[0][0]
        assert call_args.search_type.value == "gender_search"
        assert call_args.gender.value == "male"
    
    @patch('src.services.face_search_service.get_face_search_service')
    def test_search_by_face_expression_search(self, mock_get_service, client, sample_expression_search_data):
        """Test expression search endpoint"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_face.return_value = FaceSearchResponse(
            results=[],
            total=14,
            took=92,
            page=1,
            limit=12,
            pages=2,
            aggregations={},
            total_faces_found=20,
            unique_persons=9,
            unknown_faces_count=3,
            celebrity_matches_count=0,
            search_metadata={"search_type": "expression_search"}
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/face", json=sample_expression_search_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 14
        assert data["search_metadata"]["search_type"] == "expression_search"
        
        # Verify service was called
        mock_service.search_by_face.assert_called_once()
        call_args = mock_service.search_by_face.call_args[0][0]
        assert call_args.search_type.value == "expression_search"
        assert call_args.expression.value == "smiling"
    
    @patch('src.services.face_search_service.get_face_search_service')
    def test_search_by_face_face_count_search(self, mock_get_service, client, sample_face_count_search_data):
        """Test face count search endpoint"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_face.return_value = FaceSearchResponse(
            results=[],
            total=28,
            took=145,
            page=1,
            limit=18,
            pages=2,
            aggregations={},
            total_faces_found=85,
            unique_persons=32,
            unknown_faces_count=15,
            celebrity_matches_count=2,
            search_metadata={"search_type": "face_count"}
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/face", json=sample_face_count_search_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 28
        assert data["total_faces_found"] == 85
        assert data["search_metadata"]["search_type"] == "face_count"
        
        # Verify service was called
        mock_service.search_by_face.assert_called_once()
        call_args = mock_service.search_by_face.call_args[0][0]
        assert call_args.search_type.value == "face_count"
        assert call_args.min_face_count == 2
        assert call_args.max_face_count == 8
    
    @patch('src.services.face_search_service.get_face_search_service')
    def test_search_by_face_group_detection(self, mock_get_service, client, sample_group_detection_data):
        """Test group detection search endpoint"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_face.return_value = FaceSearchResponse(
            results=[],
            total=16,
            took=165,
            page=1,
            limit=20,
            pages=1,
            aggregations={},
            total_faces_found=95,
            unique_persons=45,
            unknown_faces_count=25,
            celebrity_matches_count=3,
            search_metadata={"search_type": "group_detection"}
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/face", json=sample_group_detection_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 16
        assert data["total_faces_found"] == 95
        assert data["unique_persons"] == 45
        assert data["search_metadata"]["search_type"] == "group_detection"
        
        # Verify service was called
        mock_service.search_by_face.assert_called_once()
        call_args = mock_service.search_by_face.call_args[0][0]
        assert call_args.search_type.value == "group_detection"
        assert call_args.group_size_range == {"min": 3, "max": 10}
    
    @patch('src.services.face_search_service.get_face_search_service')
    def test_search_by_face_celebrity_recognition(self, mock_get_service, client, sample_celebrity_search_data):
        """Test celebrity recognition search endpoint"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_face.return_value = FaceSearchResponse(
            results=[],
            total=5,
            took=220,
            page=1,
            limit=30,
            pages=1,
            aggregations={},
            total_faces_found=8,
            unique_persons=3,
            unknown_faces_count=0,
            celebrity_matches_count=8,
            search_metadata={"search_type": "celebrity_recognition"}
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/face", json=sample_celebrity_search_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert data["celebrity_matches_count"] == 8
        assert data["search_metadata"]["search_type"] == "celebrity_recognition"
        
        # Verify service was called
        mock_service.search_by_face.assert_called_once()
        call_args = mock_service.search_by_face.call_args[0][0]
        assert call_args.search_type.value == "celebrity_recognition"
        assert call_args.min_confidence == 0.8
    
    @patch('src.services.face_search_service.get_face_search_service')
    def test_search_by_face_unknown_faces(self, mock_get_service, client, sample_unknown_faces_data):
        """Test unknown faces search endpoint"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_face.return_value = FaceSearchResponse(
            results=[],
            total=35,
            took=135,
            page=1,
            limit=15,
            pages=3,
            aggregations={},
            total_faces_found=42,
            unique_persons=0,
            unknown_faces_count=42,
            celebrity_matches_count=0,
            search_metadata={"search_type": "unknown_faces"}
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/face", json=sample_unknown_faces_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 35
        assert data["unknown_faces_count"] == 42
        assert data["unique_persons"] == 0
        assert data["search_metadata"]["search_type"] == "unknown_faces"
        
        # Verify service was called
        mock_service.search_by_face.assert_called_once()
        call_args = mock_service.search_by_face.call_args[0][0]
        assert call_args.search_type.value == "unknown_faces"
        assert call_args.min_face_quality.value == "good"
        assert call_args.include_unknown_faces == True
    
    @patch('src.services.face_search_service.get_face_search_service')
    def test_search_by_face_verification(self, mock_get_service, client, sample_face_verification_data):
        """Test face verification search endpoint"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.search_by_face.return_value = FaceSearchResponse(
            results=[],
            total=3,
            took=95,
            page=1,
            limit=5,
            pages=1,
            aggregations={},
            total_faces_found=4,
            unique_persons=1,
            unknown_faces_count=0,
            celebrity_matches_count=0,
            search_metadata={"search_type": "face_verification"}
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/face", json=sample_face_verification_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["unique_persons"] == 1
        assert data["search_metadata"]["search_type"] == "face_verification"
        
        # Verify service was called
        mock_service.search_by_face.assert_called_once()
        call_args = mock_service.search_by_face.call_args[0][0]
        assert call_args.search_type.value == "face_verification"
        assert call_args.person_id == "person_456"
        assert call_args.match_type.value == "euclidean_distance"
    
    @patch('src.services.face_search_service.get_face_search_service')
    def test_search_invalid_data(self, mock_get_service, client):
        """Test search with invalid data"""
        # Mock service
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        
        # Make request with invalid data
        invalid_data = {
            "search_type": "invalid_type",
            "min_confidence": 1.5  # Invalid confidence value
        }
        
        response = client.post("/search/face", json=invalid_data)
        
        # Verify response
        assert response.status_code == 422  # Validation error
    
    @patch('src.services.face_search_service.get_face_search_service')
    def test_analyze_asset_faces_success(self, mock_get_service, client, sample_analysis_request_data):
        """Test successful asset face analysis"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.analyze_asset_faces.return_value = FaceAnalysisResponse(
            asset_id="asset_123",
            analysis_success=True,
            detected_faces=[
                DetectedFace(
                    face_id="face_001",
                    bounding_box=BoundingBox(x=120, y=80, width=200, height=240, confidence=0.92),
                    attributes=FaceAttributes(
                        age=35,
                        age_range={"min": 32, "max": 38},
                        gender=Gender.MALE,
                        gender_confidence=0.88,
                        emotion=Emotion.NEUTRAL,
                        emotion_confidence=0.75,
                        emotion_scores={"neutral": 0.75, "happy": 0.18, "sad": 0.07},
                        expression=FaceExpression.NEUTRAL,
                        expression_confidence=0.82,
                        glasses=True,
                        glasses_confidence=0.94,
                        beard=True,
                        beard_confidence=0.89,
                        mustache=False,
                        mustache_confidence=0.92,
                        head_pose={"yaw": -5.2, "pitch": 1.8, "roll": -0.5},
                        face_angle=-5.0,
                        face_quality=FaceQuality.GOOD,
                        blur_score=0.12,
                        brightness=0.62,
                        sharpness=0.88,
                        occlusion=0.05
                    ),
                    encoding=FaceEncoding(
                        model=FaceRecognitionModel.FACENET,
                        encoding=[0.15] * 512,
                        dimension=512,
                        confidence=0.91
                    ),
                    person_id="person_789",
                    person_name="Bob Smith",
                    detection_model=FaceDetectionModel.RETINAFACE,
                    detection_confidence=0.92,
                    detection_time_ms=135
                )
            ],
            face_count=1,
            identified_persons=[
                PersonIdentity(
                    person_id="person_789",
                    person_name="Bob Smith",
                    known_faces=["face_001"],
                    description="Engineering team lead",
                    tags=["employee", "engineering"],
                    department="Engineering",
                    role="Team Lead",
                    total_appearances=8,
                    last_seen=datetime.utcnow(),
                    confidence_avg=0.87,
                    privacy_level="public",
                    consent_given=True
                )
            ],
            unknown_faces=[],
            celebrity_matches=[],
            demographics={
                "total_faces": 1,
                "gender_distribution": {"male": 1, "female": 0},
                "emotions": {"neutral": 1},
                "age_statistics": {"min": 35, "max": 35, "average": 35.0}
            },
            age_statistics={"min": 35, "max": 35, "average": 35.0},
            gender_distribution={"male": 1, "female": 0},
            emotion_distribution={"neutral": 1},
            average_face_quality=0.82,
            quality_distribution={"good": 1},
            detection_quality_score=0.82,
            face_timeline=None,
            scene_analysis=None,
            frame_analysis=None,
            processing_time_ms=2250,
            detection_model=FaceDetectionModel.RETINAFACE,
            recognition_model=FaceRecognitionModel.FACENET,
            frames_analyzed=None,
            errors=[],
            warnings=[]
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.post("/search/face/analyze", json=sample_analysis_request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["asset_id"] == "asset_123"
        assert data["analysis_success"] == True
        assert len(data["detected_faces"]) == 1
        assert data["face_count"] == 1
        assert len(data["identified_persons"]) == 1
        assert data["processing_time_ms"] == 2250
        assert data["detection_model"] == "retinaface"
        assert data["recognition_model"] == "facenet"
        assert len(data["errors"]) == 0
        assert len(data["warnings"]) == 0
        
        # Check detected face details
        face = data["detected_faces"][0]
        assert face["face_id"] == "face_001"
        assert face["person_id"] == "person_789"
        assert face["person_name"] == "Bob Smith"
        assert face["detection_confidence"] == 0.92
        assert face["attributes"]["age"] == 35
        assert face["attributes"]["gender"] == "male"
        assert face["attributes"]["emotion"] == "neutral"
        assert face["attributes"]["glasses"] == True
        assert face["attributes"]["beard"] == True
        
        # Verify service was called
        mock_service.analyze_asset_faces.assert_called_once()
    
    @patch('src.services.face_search_service.get_face_search_service')
    def test_analyze_asset_faces_failure(self, mock_get_service, client):
        """Test asset face analysis failure"""
        # Mock service to raise an error
        mock_service = AsyncMock()
        mock_service.analyze_asset_faces.side_effect = Exception("Analysis failed")
        mock_get_service.return_value = mock_service
        
        # Create analysis request
        analysis_data = {
            "asset_id": "invalid_asset",
            "detection_model": "retinaface",
            "recognition_model": "facenet"
        }
        
        # Make request
        response = client.post("/search/face/analyze", json=analysis_data)
        
        # Verify response
        assert response.status_code == 500
        data = response.json()
        assert "Face analysis failed" in data["detail"]
    
    @patch('src.services.face_search_service.get_face_search_service')
    def test_get_face_search_stats(self, mock_get_service, client):
        """Test getting face search statistics"""
        # Mock service
        mock_service = AsyncMock()
        mock_service.get_face_search_stats.return_value = FaceSearchStats(
            total_searches=2500,
            total_faces_detected=15000,
            total_persons_identified=3200,
            unique_persons_database=850,
            identification_accuracy=0.92,
            false_positive_rate=0.03,
            false_negative_rate=0.08,
            avg_search_time_ms=185.0,
            avg_detection_time_ms=95.0,
            avg_recognition_time_ms=140.0,
            cache_hit_rate=0.78,
            images_analyzed=4200,
            videos_analyzed=1800,
            frames_analyzed=180000,
            detection_model_usage={
                "retinaface": 3500,
                "mtcnn": 1800,
                "mediapipe": 1200
            },
            recognition_model_usage={
                "facenet": 3200,
                "arcface": 2100,
                "cosface": 1500
            },
            face_quality_distribution={
                "excellent": 4500,
                "good": 6200,
                "fair": 3800,
                "poor": 500
            },
            confidence_distribution={
                "high": 8500,
                "medium": 5200,
                "low": 1300
            },
            age_distribution={
                "0-20": 2800,
                "21-40": 7200,
                "41-60": 4100,
                "60+": 900
            },
            gender_distribution={
                "male": 7800,
                "female": 6900,
                "unknown": 300
            },
            emotion_distribution={
                "happy": 5200,
                "neutral": 6800,
                "surprise": 1500,
                "sad": 800
            },
            consent_given_persons=720,
            anonymized_faces=1200,
            privacy_violations=0,
            detection_failures=150,
            recognition_failures=280,
            low_quality_faces=850
        )
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.get("/search/face/stats")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_searches"] == 2500
        assert data["total_faces_detected"] == 15000
        assert data["total_persons_identified"] == 3200
        assert data["unique_persons_database"] == 850
        assert data["identification_accuracy"] == 0.92
        assert data["avg_search_time_ms"] == 185.0
        assert data["avg_detection_time_ms"] == 95.0
        assert data["avg_recognition_time_ms"] == 140.0
        assert data["cache_hit_rate"] == 0.78
        assert data["images_analyzed"] == 4200
        assert data["videos_analyzed"] == 1800
        assert data["frames_analyzed"] == 180000
        
        # Check distributions
        assert data["detection_model_usage"]["retinaface"] == 3500
        assert data["recognition_model_usage"]["facenet"] == 3200
        assert data["face_quality_distribution"]["excellent"] == 4500
        assert data["confidence_distribution"]["high"] == 8500
        assert data["age_distribution"]["21-40"] == 7200
        assert data["gender_distribution"]["male"] == 7800
        assert data["emotion_distribution"]["happy"] == 5200
        
        # Check privacy metrics
        assert data["consent_given_persons"] == 720
        assert data["anonymized_faces"] == 1200
        assert data["privacy_violations"] == 0
        
        # Verify service was called
        mock_service.get_face_search_stats.assert_called_once()
    
    @patch('src.services.face_search_service.get_face_search_service')
    def test_get_face_search_stats_error(self, mock_get_service, client):
        """Test getting face search statistics with error"""
        # Mock service to raise error
        mock_service = AsyncMock()
        mock_service.get_face_search_stats.side_effect = Exception("Database connection failed")
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.get("/search/face/stats")
        
        # Verify response
        assert response.status_code == 500
        data = response.json()
        assert "Failed to get face search statistics" in data["detail"]
    
    def test_face_search_endpoints_exist(self, client):
        """Test that all face search endpoints exist"""
        # Test main search endpoint
        response = client.post("/search/face", json={
            "search_type": "person_search",
            "person_id": "person_123"
        })
        assert response.status_code != 404
        
        # Test analysis endpoint
        response = client.post("/search/face/analyze", json={
            "asset_id": "asset_123",
            "detection_model": "retinaface",
            "recognition_model": "facenet"
        })
        assert response.status_code != 404
        
        # Test stats endpoint
        response = client.get("/search/face/stats")
        assert response.status_code != 404
    
    def test_face_search_request_validation(self, client):
        """Test request validation for face search endpoint"""
        # Test with completely invalid data
        response = client.post("/search/face", json={})
        assert response.status_code == 422
        
        # Test with invalid search type
        response = client.post("/search/face", json={
            "search_type": "invalid_type"
        })
        assert response.status_code == 422
        
        # Test with invalid confidence value
        response = client.post("/search/face", json={
            "search_type": "person_search",
            "person_id": "person_123",
            "min_confidence": 1.5  # Invalid: > 1.0
        })
        assert response.status_code == 422
        
        # Test with invalid similarity threshold
        response = client.post("/search/face", json={
            "search_type": "face_similarity",
            "similarity_threshold": -0.1  # Invalid: < 0.0
        })
        assert response.status_code == 422
        
        # Test with invalid age range
        response = client.post("/search/face", json={
            "search_type": "demographic_search",
            "age_range": {"min": 50, "max": 30}  # Invalid: min > max
        })
        assert response.status_code == 422
        
        # Test with invalid group size range
        response = client.post("/search/face", json={
            "search_type": "group_detection",
            "group_size_range": {"min": 10, "max": 5}  # Invalid: min > max
        })
        assert response.status_code == 422
    
    def test_face_analysis_request_validation(self, client):
        """Test request validation for face analysis endpoint"""
        # Test without required asset_id
        response = client.post("/search/face/analyze", json={})
        assert response.status_code == 422
        
        # Test with invalid detection model
        response = client.post("/search/face/analyze", json={
            "asset_id": "asset_123",
            "detection_model": "invalid_model"
        })
        assert response.status_code == 422
        
        # Test with invalid recognition model
        response = client.post("/search/face/analyze", json={
            "asset_id": "asset_123",
            "recognition_model": "invalid_model"
        })
        assert response.status_code == 422
        
        # Test with invalid landmark type
        response = client.post("/search/face/analyze", json={
            "asset_id": "asset_123",
            "landmark_type": "invalid_landmarks"
        })
        assert response.status_code == 422
        
        # Test with invalid min_face_size
        response = client.post("/search/face/analyze", json={
            "asset_id": "asset_123",
            "min_face_size": 0  # Should be >= 10
        })
        assert response.status_code == 422
        
        # Test with invalid min_confidence
        response = client.post("/search/face/analyze", json={
            "asset_id": "asset_123",
            "min_confidence": 1.5  # Should be <= 1.0
        })
        assert response.status_code == 422
        
        # Test with invalid frame_interval
        response = client.post("/search/face/analyze", json={
            "asset_id": "asset_123",
            "frame_interval": 0  # Should be >= 1
        })
        assert response.status_code == 422
"""
Facial Recognition Search Service

This service provides comprehensive facial recognition search capabilities including:
- Person identification and verification
- Face similarity search
- Demographic-based search (age, gender, emotion)
- Celebrity recognition
- Group detection and analysis
- Privacy-compliant facial recognition
"""

import asyncio
import logging
import time
import math
import uuid
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
import numpy as np

from src.models.schemas import (
    FaceSearchQuery, FaceSearchResponse, FaceSearchResult, FaceAnalysisRequest, FaceAnalysisResponse,
    FaceSearchStats, DetectedFace, PersonIdentity, FaceAttributes, FaceEncoding, BoundingBox,
    FaceLandmarks, FaceDetectionModel, FaceRecognitionModel, FaceSearchType, FaceMatchType,
    Gender, Emotion, FaceExpression, FaceQuality, FaceLandmarkType
)

logger = logging.getLogger(__name__)


class FaceSearchService:
    """Service for handling facial recognition searches and analysis"""
    
    def __init__(self, opensearch_client=None, cache_client=None):
        self.opensearch_client = opensearch_client
        self.cache_client = cache_client
        self.face_detection_models = self._initialize_detection_models()
        self.face_recognition_models = self._initialize_recognition_models()
        self.persons_database = {}  # In-memory person database (would be persistent in production)
        self.celebrity_database = self._load_celebrity_database()
        
    def _initialize_detection_models(self) -> Dict[str, Any]:
        """Initialize available face detection models"""
        return {
            FaceDetectionModel.MTCNN: {
                "accuracy": 0.95,
                "speed": "medium",
                "min_face_size": 20,
                "supports_landmarks": True
            },
            FaceDetectionModel.RETINAFACE: {
                "accuracy": 0.97,
                "speed": "fast",
                "min_face_size": 15,
                "supports_landmarks": True
            },
            FaceDetectionModel.OPENCV_DNN: {
                "accuracy": 0.92,
                "speed": "fast",
                "min_face_size": 25,
                "supports_landmarks": False
            },
            FaceDetectionModel.DLIB_HOG: {
                "accuracy": 0.88,
                "speed": "slow",
                "min_face_size": 30,
                "supports_landmarks": True
            },
            FaceDetectionModel.DLIB_CNN: {
                "accuracy": 0.94,
                "speed": "slow",
                "min_face_size": 20,
                "supports_landmarks": True
            },
            FaceDetectionModel.MEDIAPIPE: {
                "accuracy": 0.93,
                "speed": "very_fast",
                "min_face_size": 25,
                "supports_landmarks": True
            },
            FaceDetectionModel.YOLO_FACE: {
                "accuracy": 0.96,
                "speed": "fast",
                "min_face_size": 20,
                "supports_landmarks": False
            },
            FaceDetectionModel.BLAZEFACE: {
                "accuracy": 0.91,
                "speed": "very_fast",
                "min_face_size": 15,
                "supports_landmarks": True
            }
        }
    
    def _initialize_recognition_models(self) -> Dict[str, Any]:
        """Initialize available face recognition models"""
        return {
            FaceRecognitionModel.FACENET: {
                "accuracy": 0.96,
                "embedding_size": 512,
                "speed": "medium",
                "threshold": 0.6
            },
            FaceRecognitionModel.ARCFACE: {
                "accuracy": 0.98,
                "embedding_size": 512,
                "speed": "medium",
                "threshold": 0.55
            },
            FaceRecognitionModel.COSFACE: {
                "accuracy": 0.97,
                "embedding_size": 512,
                "speed": "medium",
                "threshold": 0.6
            },
            FaceRecognitionModel.SPHEREFACE: {
                "accuracy": 0.95,
                "embedding_size": 256,
                "speed": "fast",
                "threshold": 0.65
            },
            FaceRecognitionModel.OPENFACE: {
                "accuracy": 0.92,
                "embedding_size": 128,
                "speed": "fast",
                "threshold": 0.7
            },
            FaceRecognitionModel.DEEPFACE: {
                "accuracy": 0.94,
                "embedding_size": 4096,
                "speed": "slow",
                "threshold": 0.68
            },
            FaceRecognitionModel.INSIGHTFACE: {
                "accuracy": 0.97,
                "embedding_size": 512,
                "speed": "medium",
                "threshold": 0.6
            },
            FaceRecognitionModel.FACE_RECOGNITION: {
                "accuracy": 0.93,
                "embedding_size": 128,
                "speed": "fast",
                "threshold": 0.6
            }
        }
    
    def _load_celebrity_database(self) -> Dict[str, Any]:
        """Load celebrity recognition database"""
        # In production, this would load from a real celebrity database
        return {
            "celebrity_001": {
                "name": "John Doe",
                "profession": "Actor",
                "confidence_threshold": 0.85,
                "reference_encoding": [0.1] * 512
            },
            "celebrity_002": {
                "name": "Jane Smith",
                "profession": "Musician",
                "confidence_threshold": 0.88,
                "reference_encoding": [0.2] * 512
            }
        }
    
    async def search_by_face(self, query: FaceSearchQuery) -> FaceSearchResponse:
        """Perform facial recognition search"""
        start_time = time.time()
        
        try:
            # Build OpenSearch query based on search type
            search_body = await self._build_face_search_query(query)
            
            # Execute search
            response = await self._execute_face_search(search_body, query)
            
            # Process results
            results = await self._process_face_search_results(response, query)
            
            # Calculate statistics
            face_stats = await self._calculate_face_statistics(results)
            
            # Calculate pagination
            total = response.get('hits', {}).get('total', {}).get('value', 0)
            pages = math.ceil(total / query.limit) if total > 0 else 0
            took = int((time.time() - start_time) * 1000)
            
            return FaceSearchResponse(
                results=results,
                total=total,
                took=took,
                page=query.page,
                limit=query.limit,
                pages=pages,
                aggregations=response.get('aggregations', {}),
                total_faces_found=face_stats['total_faces'],
                unique_persons=face_stats['unique_persons'],
                unknown_faces_count=face_stats['unknown_faces'],
                celebrity_matches_count=face_stats['celebrity_matches'],
                quality_distribution=face_stats['quality_distribution'],
                confidence_distribution=face_stats['confidence_distribution'],
                overall_demographics=face_stats['demographics'],
                search_metadata={
                    "search_type": query.search_type.value,
                    "execution_time": took / 1000,
                    "detection_model": query.face_detection_model.value if query.face_detection_model else None,
                    "recognition_model": query.face_recognition_model.value if query.face_recognition_model else None
                }
            )
            
        except Exception as e:
            logger.error(f"Face search failed: {e}")
            raise
    
    async def _build_face_search_query(self, query: FaceSearchQuery) -> Dict[str, Any]:
        """Build OpenSearch query for face search"""
        search_body = {
            "query": {
                "bool": {
                    "must": [],
                    "filter": [],
                    "should": [],
                    "must_not": []
                }
            },
            "size": query.limit,
            "from": (query.page - 1) * query.limit,
            "sort": [],
            "aggs": {}
        }
        
        # Asset type filter
        if query.asset_types:
            search_body["query"]["bool"]["filter"].append({
                "terms": {"asset_type": query.asset_types}
            })
        
        # Face analysis exists filter
        search_body["query"]["bool"]["filter"].append({
            "exists": {"field": "face_analysis"}
        })
        
        # Search type specific queries
        if query.search_type == FaceSearchType.PERSON_SEARCH:
            await self._add_person_search_query(search_body, query)
        elif query.search_type == FaceSearchType.FACE_SIMILARITY:
            await self._add_similarity_search_query(search_body, query)
        elif query.search_type == FaceSearchType.DEMOGRAPHIC_SEARCH:
            await self._add_demographic_search_query(search_body, query)
        elif query.search_type == FaceSearchType.EMOTION_SEARCH:
            await self._add_emotion_search_query(search_body, query)
        elif query.search_type == FaceSearchType.AGE_RANGE_SEARCH:
            await self._add_age_range_search_query(search_body, query)
        elif query.search_type == FaceSearchType.GENDER_SEARCH:
            await self._add_gender_search_query(search_body, query)
        elif query.search_type == FaceSearchType.EXPRESSION_SEARCH:
            await self._add_expression_search_query(search_body, query)
        elif query.search_type == FaceSearchType.FACE_COUNT:
            await self._add_face_count_search_query(search_body, query)
        elif query.search_type == FaceSearchType.GROUP_DETECTION:
            await self._add_group_detection_query(search_body, query)
        elif query.search_type == FaceSearchType.CELEBRITY_RECOGNITION:
            await self._add_celebrity_search_query(search_body, query)
        elif query.search_type == FaceSearchType.UNKNOWN_FACES:
            await self._add_unknown_faces_query(search_body, query)
        
        # Quality filters
        if query.min_confidence:
            search_body["query"]["bool"]["filter"].append({
                "range": {
                    "face_analysis.average_confidence": {"gte": query.min_confidence}
                }
            })
        
        if query.min_face_quality:
            search_body["query"]["bool"]["filter"].append({
                "term": {
                    "face_analysis.min_quality": {"value": query.min_face_quality.value, "boost": 1.0}
                }
            })
        
        if query.max_blur_score:
            search_body["query"]["bool"]["filter"].append({
                "range": {
                    "face_analysis.average_blur_score": {"lte": query.max_blur_score}
                }
            })
        
        if query.min_face_size:
            search_body["query"]["bool"]["filter"].append({
                "range": {
                    "face_analysis.min_face_size": {"gte": query.min_face_size}
                }
            })
        
        # Face count filters
        if query.min_face_count is not None:
            search_body["query"]["bool"]["filter"].append({
                "range": {
                    "face_analysis.face_count": {"gte": query.min_face_count}
                }
            })
        
        if query.max_face_count is not None:
            search_body["query"]["bool"]["filter"].append({
                "range": {
                    "face_analysis.face_count": {"lte": query.max_face_count}
                }
            })
        
        # Video duration filters
        if query.min_duration:
            search_body["query"]["bool"]["filter"].append({
                "range": {"duration": {"gte": query.min_duration}}
            })
        
        if query.max_duration:
            search_body["query"]["bool"]["filter"].append({
                "range": {"duration": {"lte": query.max_duration}}
            })
        
        # Model filters
        if query.face_detection_model:
            search_body["query"]["bool"]["filter"].append({
                "term": {"face_analysis.detection_model": query.face_detection_model.value}
            })
        
        if query.face_recognition_model:
            search_body["query"]["bool"]["filter"].append({
                "term": {"face_analysis.recognition_model": query.face_recognition_model.value}
            })
        
        # Sorting
        sort_field = f"face_analysis.{query.sort_by}"
        search_body["sort"].append({
            sort_field: {"order": query.sort_order.value}
        })
        
        # Add relevance sorting for similarity searches
        if query.search_type in [FaceSearchType.FACE_SIMILARITY, FaceSearchType.PERSON_SEARCH]:
            search_body["sort"].insert(0, {"_score": {"order": "desc"}})
        
        # Aggregations for statistics
        search_body["aggs"] = {
            "face_count_distribution": {
                "histogram": {
                    "field": "face_analysis.face_count",
                    "interval": 1
                }
            },
            "gender_distribution": {
                "terms": {
                    "field": "face_analysis.demographics.gender_distribution.keyword",
                    "size": 10
                }
            },
            "age_distribution": {
                "histogram": {
                    "field": "face_analysis.demographics.average_age",
                    "interval": 10
                }
            },
            "emotion_distribution": {
                "terms": {
                    "field": "face_analysis.demographics.primary_emotion.keyword",
                    "size": 10
                }
            },
            "quality_distribution": {
                "terms": {
                    "field": "face_analysis.average_quality.keyword",
                    "size": 5
                }
            }
        }
        
        return search_body
    
    async def _add_person_search_query(self, search_body: Dict[str, Any], query: FaceSearchQuery):
        """Add person-specific search query"""
        if query.person_id:
            search_body["query"]["bool"]["must"].append({
                "nested": {
                    "path": "face_analysis.detected_faces",
                    "query": {
                        "term": {"face_analysis.detected_faces.person_id": query.person_id}
                    }
                }
            })
        
        if query.person_name:
            search_body["query"]["bool"]["must"].append({
                "nested": {
                    "path": "face_analysis.detected_faces",
                    "query": {
                        "match": {"face_analysis.detected_faces.person_name": query.person_name}
                    }
                }
            })
    
    async def _add_similarity_search_query(self, search_body: Dict[str, Any], query: FaceSearchQuery):
        """Add face similarity search query"""
        if query.reference_encoding:
            # Use script score for similarity calculation
            search_body["query"] = {
                "script_score": {
                    "query": search_body["query"],
                    "script": {
                        "source": f"""
                        double similarity = 0.0;
                        if (doc['face_analysis.reference_encoding'].size() > 0) {{
                            def encoding = doc['face_analysis.reference_encoding'];
                            def reference = params.reference;
                            double dotProduct = 0.0;
                            double normA = 0.0;
                            double normB = 0.0;
                            for (int i = 0; i < Math.min(encoding.size(), reference.size()); i++) {{
                                dotProduct += encoding[i] * reference[i];
                                normA += encoding[i] * encoding[i];
                                normB += reference[i] * reference[i];
                            }}
                            if (normA > 0 && normB > 0) {{
                                similarity = dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
                            }}
                        }}
                        return Math.max(0, similarity);
                        """,
                        "params": {
                            "reference": query.reference_encoding
                        }
                    },
                    "min_score": query.similarity_threshold
                }
            }
    
    async def _add_demographic_search_query(self, search_body: Dict[str, Any], query: FaceSearchQuery):
        """Add demographic-based search query"""
        demographic_filters = []
        
        if query.age_range:
            demographic_filters.append({
                "range": {
                    "face_analysis.demographics.average_age": {
                        "gte": query.age_range["min"],
                        "lte": query.age_range["max"]
                    }
                }
            })
        
        if query.gender:
            demographic_filters.append({
                "term": {"face_analysis.demographics.primary_gender": query.gender.value}
            })
        
        if demographic_filters:
            search_body["query"]["bool"]["filter"].extend(demographic_filters)
    
    async def _add_emotion_search_query(self, search_body: Dict[str, Any], query: FaceSearchQuery):
        """Add emotion-based search query"""
        if query.emotion:
            search_body["query"]["bool"]["must"].append({
                "nested": {
                    "path": "face_analysis.detected_faces",
                    "query": {
                        "term": {"face_analysis.detected_faces.attributes.emotion": query.emotion.value}
                    }
                }
            })
    
    async def _add_age_range_search_query(self, search_body: Dict[str, Any], query: FaceSearchQuery):
        """Add age range search query"""
        if query.age_range:
            search_body["query"]["bool"]["must"].append({
                "nested": {
                    "path": "face_analysis.detected_faces",
                    "query": {
                        "range": {
                            "face_analysis.detected_faces.attributes.age": {
                                "gte": query.age_range["min"],
                                "lte": query.age_range["max"]
                            }
                        }
                    }
                }
            })
    
    async def _add_gender_search_query(self, search_body: Dict[str, Any], query: FaceSearchQuery):
        """Add gender search query"""
        if query.gender:
            search_body["query"]["bool"]["must"].append({
                "nested": {
                    "path": "face_analysis.detected_faces",
                    "query": {
                        "term": {"face_analysis.detected_faces.attributes.gender": query.gender.value}
                    }
                }
            })
    
    async def _add_expression_search_query(self, search_body: Dict[str, Any], query: FaceSearchQuery):
        """Add expression search query"""
        if query.expression:
            search_body["query"]["bool"]["must"].append({
                "nested": {
                    "path": "face_analysis.detected_faces",
                    "query": {
                        "term": {"face_analysis.detected_faces.attributes.expression": query.expression.value}
                    }
                }
            })
    
    async def _add_face_count_search_query(self, search_body: Dict[str, Any], query: FaceSearchQuery):
        """Add face count search query"""
        # Face count filters are already handled in the main query building
        pass
    
    async def _add_group_detection_query(self, search_body: Dict[str, Any], query: FaceSearchQuery):
        """Add group detection query"""
        if query.group_size_range:
            search_body["query"]["bool"]["filter"].append({
                "range": {
                    "face_analysis.face_count": {
                        "gte": query.group_size_range["min"],
                        "lte": query.group_size_range["max"]
                    }
                }
            })
    
    async def _add_celebrity_search_query(self, search_body: Dict[str, Any], query: FaceSearchQuery):
        """Add celebrity recognition query"""
        search_body["query"]["bool"]["must"].append({
            "nested": {
                "path": "face_analysis.detected_faces",
                "query": {
                    "exists": {"field": "face_analysis.detected_faces.celebrity_name"}
                }
            }
        })
    
    async def _add_unknown_faces_query(self, search_body: Dict[str, Any], query: FaceSearchQuery):
        """Add unknown faces query"""
        search_body["query"]["bool"]["must"].append({
            "nested": {
                "path": "face_analysis.detected_faces",
                "query": {
                    "bool": {
                        "must_not": [
                            {"exists": {"field": "face_analysis.detected_faces.person_id"}},
                            {"exists": {"field": "face_analysis.detected_faces.celebrity_name"}}
                        ]
                    }
                }
            }
        })
    
    async def _execute_face_search(self, search_body: Dict[str, Any], query: FaceSearchQuery) -> Dict[str, Any]:
        """Execute the face search query"""
        index_name = "mams_assets"
        
        if self.opensearch_client:
            response = await self.opensearch_client.search(
                index=index_name,
                body=search_body
            )
            return response
        else:
            # Mock response for testing
            return self._generate_mock_face_search_response(query)
    
    def _generate_mock_face_search_response(self, query: FaceSearchQuery) -> Dict[str, Any]:
        """Generate mock search response for testing"""
        mock_hits = []
        
        # Generate different mock responses based on search type
        if query.search_type == FaceSearchType.PERSON_SEARCH:
            mock_hits = self._generate_person_search_hits(query)
        elif query.search_type == FaceSearchType.FACE_SIMILARITY:
            mock_hits = self._generate_similarity_search_hits(query)
        elif query.search_type == FaceSearchType.DEMOGRAPHIC_SEARCH:
            mock_hits = self._generate_demographic_search_hits(query)
        elif query.search_type == FaceSearchType.EMOTION_SEARCH:
            mock_hits = self._generate_emotion_search_hits(query)
        elif query.search_type == FaceSearchType.CELEBRITY_RECOGNITION:
            mock_hits = self._generate_celebrity_search_hits(query)
        else:
            mock_hits = self._generate_generic_face_hits(query)
        
        return {
            "hits": {
                "total": {"value": len(mock_hits)},
                "hits": mock_hits
            },
            "aggregations": {
                "face_count_distribution": {
                    "buckets": [
                        {"key": 1.0, "doc_count": 15},
                        {"key": 2.0, "doc_count": 8},
                        {"key": 3.0, "doc_count": 5}
                    ]
                },
                "gender_distribution": {
                    "buckets": [
                        {"key": "male", "doc_count": 18},
                        {"key": "female", "doc_count": 15},
                        {"key": "unknown", "doc_count": 2}
                    ]
                },
                "emotion_distribution": {
                    "buckets": [
                        {"key": "happy", "doc_count": 12},
                        {"key": "neutral", "doc_count": 10},
                        {"key": "surprise", "doc_count": 5}
                    ]
                }
            }
        }
    
    def _generate_person_search_hits(self, query: FaceSearchQuery) -> List[Dict[str, Any]]:
        """Generate mock hits for person search"""
        return [
            {
                "_id": "asset-face-001",
                "_score": 0.95,
                "_source": {
                    "asset_id": "asset-face-001",
                    "asset_name": "Team Meeting Photo",
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
    
    def _generate_similarity_search_hits(self, query: FaceSearchQuery) -> List[Dict[str, Any]]:
        """Generate mock hits for similarity search"""
        return [
            {
                "_id": "asset-similar-001",
                "_score": 0.88,
                "_source": {
                    "asset_id": "asset-similar-001",
                    "asset_name": "Similar Person Portrait",
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
                        "recognition_model": "facenet",
                        "analyzed_at": "2024-01-16T09:15:00Z"
                    }
                }
            }
        ]
    
    def _generate_demographic_search_hits(self, query: FaceSearchQuery) -> List[Dict[str, Any]]:
        """Generate mock hits for demographic search"""
        return [
            {
                "_id": "asset-demo-001",
                "_score": 0.82,
                "_source": {
                    "asset_id": "asset-demo-001",
                    "asset_name": "Group Demographics",
                    "asset_type": "image",
                    "file_size": 3456789,
                    "dimensions": {"width": 2048, "height": 1536},
                    "format": "jpg",
                    "created_at": "2024-01-17T14:20:00Z",
                    "updated_at": "2024-01-17T14:20:00Z",
                    "face_analysis": {
                        "face_count": 5,
                        "average_confidence": 0.85,
                        "detection_model": "retinaface",
                        "recognition_model": "facenet",
                        "analyzed_at": "2024-01-17T14:20:00Z"
                    }
                }
            }
        ]
    
    def _generate_emotion_search_hits(self, query: FaceSearchQuery) -> List[Dict[str, Any]]:
        """Generate mock hits for emotion search"""
        return [
            {
                "_id": "asset-emotion-001",
                "_score": 0.78,
                "_source": {
                    "asset_id": "asset-emotion-001",
                    "asset_name": "Happy Celebration",
                    "asset_type": "video",
                    "file_size": 15678901,
                    "dimensions": {"width": 1920, "height": 1080},
                    "duration": 120.5,
                    "format": "mp4",
                    "created_at": "2024-01-18T16:45:00Z",
                    "updated_at": "2024-01-18T16:45:00Z",
                    "face_analysis": {
                        "face_count": 8,
                        "average_confidence": 0.78,
                        "detection_model": "mediapipe",
                        "recognition_model": "arcface",
                        "analyzed_at": "2024-01-18T16:45:00Z"
                    }
                }
            }
        ]
    
    def _generate_celebrity_search_hits(self, query: FaceSearchQuery) -> List[Dict[str, Any]]:
        """Generate mock hits for celebrity search"""
        return [
            {
                "_id": "asset-celeb-001",
                "_score": 0.91,
                "_source": {
                    "asset_id": "asset-celeb-001",
                    "asset_name": "Celebrity Event",
                    "asset_type": "image",
                    "file_size": 4567890,
                    "dimensions": {"width": 3000, "height": 2000},
                    "format": "jpg",
                    "created_at": "2024-01-19T20:30:00Z",
                    "updated_at": "2024-01-19T20:30:00Z",
                    "face_analysis": {
                        "face_count": 2,
                        "average_confidence": 0.91,
                        "detection_model": "retinaface",
                        "recognition_model": "arcface",
                        "analyzed_at": "2024-01-19T20:30:00Z"
                    }
                }
            }
        ]
    
    def _generate_generic_face_hits(self, query: FaceSearchQuery) -> List[Dict[str, Any]]:
        """Generate generic mock hits for face search"""
        return [
            {
                "_id": "asset-face-generic-001",
                "_score": 0.75,
                "_source": {
                    "asset_id": "asset-face-generic-001",
                    "asset_name": "General Face Detection",
                    "asset_type": "image",
                    "file_size": 2345678,
                    "dimensions": {"width": 1600, "height": 1200},
                    "format": "png",
                    "created_at": "2024-01-20T11:15:00Z",
                    "updated_at": "2024-01-20T11:15:00Z",
                    "face_analysis": {
                        "face_count": 4,
                        "average_confidence": 0.75,
                        "detection_model": "mtcnn",
                        "recognition_model": "facenet",
                        "analyzed_at": "2024-01-20T11:15:00Z"
                    }
                }
            }
        ]
    
    async def _process_face_search_results(self, response: Dict[str, Any], query: FaceSearchQuery) -> List[FaceSearchResult]:
        """Process search results into FaceSearchResult objects"""
        results = []
        
        for hit in response.get('hits', {}).get('hits', []):
            source = hit['_source']
            score = hit.get('_score', 0.0)
            
            # Generate mock detected faces based on search type
            detected_faces = await self._generate_detected_faces(source, query)
            
            # Filter matched faces based on query
            matched_faces = await self._filter_matched_faces(detected_faces, query)
            
            # Identify persons
            identified_persons = await self._identify_persons(detected_faces)
            
            # Filter unknown faces
            unknown_faces = [face for face in detected_faces if not face.person_id and not face.celebrity_name]
            
            # Generate demographics summary
            demographics = self._calculate_demographics(detected_faces)
            
            # Generate face timeline for videos
            face_timeline = None
            scene_faces = None
            if source.get('asset_type') == 'video':
                face_timeline = self._generate_face_timeline(detected_faces, source.get('duration', 0))
                scene_faces = self._generate_scene_faces(detected_faces)
            
            result = FaceSearchResult(
                asset_id=source['asset_id'],
                asset_name=source['asset_name'],
                asset_type=source['asset_type'],
                detected_faces=detected_faces,
                face_count=len(detected_faces),
                matched_faces=matched_faces,
                match_score=score,
                match_type=self._get_match_type(query.search_type),
                best_match_confidence=max([f.detection_confidence for f in matched_faces]) if matched_faces else None,
                identified_persons=identified_persons,
                unknown_faces=unknown_faces,
                celebrity_matches=self._find_celebrity_matches(detected_faces),
                demographics=demographics,
                emotions_summary=demographics.get('emotions', {}),
                age_distribution=demographics.get('age_distribution', {}),
                gender_distribution=demographics.get('gender_distribution', {}),
                face_timeline=face_timeline,
                scene_faces=scene_faces,
                average_face_quality=sum([self._calculate_face_quality_score(f) for f in detected_faces]) / len(detected_faces) if detected_faces else None,
                detection_quality=self._assess_detection_quality(detected_faces),
                file_size=source.get('file_size'),
                dimensions=source.get('dimensions'),
                duration=source.get('duration'),
                format=source.get('format'),
                processing_time_ms=source.get('face_analysis', {}).get('processing_time_ms'),
                detection_model=FaceDetectionModel(source.get('face_analysis', {}).get('detection_model', 'retinaface')),
                recognition_model=FaceRecognitionModel(source.get('face_analysis', {}).get('recognition_model', 'facenet')),
                created_at=datetime.fromisoformat(source['created_at'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(source['updated_at'].replace('Z', '+00:00')),
                analyzed_at=datetime.fromisoformat(source.get('face_analysis', {}).get('analyzed_at', source['created_at']).replace('Z', '+00:00'))
            )
            
            results.append(result)
        
        return results
    
    async def _generate_detected_faces(self, source: Dict[str, Any], query: FaceSearchQuery) -> List[DetectedFace]:
        """Generate mock detected faces for testing"""
        face_count = source.get('face_analysis', {}).get('face_count', 1)
        detected_faces = []
        
        for i in range(face_count):
            face_id = f"face_{source['asset_id']}_{i+1}"
            
            # Generate mock face attributes based on search type
            attributes = self._generate_mock_face_attributes(query, i)
            
            # Generate mock face encoding
            encoding = None
            if query.include_encodings:
                model = query.face_recognition_model or FaceRecognitionModel.FACENET
                encoding = FaceEncoding(
                    model=model,
                    encoding=[0.1 + (i * 0.05)] * 512,
                    dimension=512,
                    confidence=0.85 + (i * 0.02)
                )
            
            # Generate mock landmarks
            landmarks = None
            if query.include_landmarks:
                landmark_points = [{"x": 100 + i*10, "y": 200 + i*5} for i in range(68)]
                landmarks = FaceLandmarks(
                    landmark_type=FaceLandmarkType.LANDMARKS_68,
                    points=landmark_points,
                    confidence=0.9
                )
            
            face = DetectedFace(
                face_id=face_id,
                bounding_box=BoundingBox(
                    x=50 + i*100,
                    y=75 + i*50,
                    width=150,
                    height=180,
                    confidence=0.92 - i*0.02
                ),
                landmarks=landmarks,
                attributes=attributes,
                encoding=encoding,
                person_id=f"person_{i+1}" if i < 2 else None,  # First 2 faces are identified
                person_name=f"Person {i+1}" if i < 2 else None,
                celebrity_name="John Doe" if i == 0 and query.search_type == FaceSearchType.CELEBRITY_RECOGNITION else None,
                similarity_score=0.85 - i*0.05 if query.search_type == FaceSearchType.FACE_SIMILARITY else None,
                detection_model=FaceDetectionModel.RETINAFACE,
                detection_confidence=0.92 - i*0.02,
                detection_time_ms=150 + i*20,
                frame_number=i*30 if source.get('asset_type') == 'video' else None,
                timestamp=i*5.0 if source.get('asset_type') == 'video' else None
            )
            
            detected_faces.append(face)
        
        return detected_faces
    
    def _generate_mock_face_attributes(self, query: FaceSearchQuery, face_index: int) -> FaceAttributes:
        """Generate mock face attributes"""
        # Base attributes
        age = 25 + face_index * 10
        emotions = [Emotion.HAPPY, Emotion.NEUTRAL, Emotion.SURPRISE]
        expressions = [FaceExpression.SMILING, FaceExpression.NEUTRAL, FaceExpression.LAUGHING]
        genders = [Gender.FEMALE, Gender.MALE, Gender.FEMALE]
        
        # Adjust based on query filters
        if query.age_range:
            age = (query.age_range["min"] + query.age_range["max"]) / 2
        
        emotion = query.emotion if query.emotion else emotions[face_index % len(emotions)]
        expression = query.expression if query.expression else expressions[face_index % len(expressions)]
        gender = query.gender if query.gender else genders[face_index % len(genders)]
        
        return FaceAttributes(
            age=age,
            age_range={"min": age-5, "max": age+5},
            gender=gender,
            gender_confidence=0.88 + face_index*0.02,
            emotion=emotion,
            emotion_confidence=0.82 + face_index*0.03,
            emotion_scores={
                "happy": 0.7 if emotion == Emotion.HAPPY else 0.2,
                "neutral": 0.8 if emotion == Emotion.NEUTRAL else 0.1,
                "surprise": 0.75 if emotion == Emotion.SURPRISE else 0.15
            },
            expression=expression,
            expression_confidence=0.85 + face_index*0.02,
            glasses=face_index % 3 == 0,
            glasses_confidence=0.92,
            beard=gender == Gender.MALE and face_index % 2 == 0,
            beard_confidence=0.88,
            mustache=gender == Gender.MALE and face_index % 3 == 1,
            mustache_confidence=0.85,
            head_pose={"yaw": face_index*5-10, "pitch": face_index*2-5, "roll": face_index-2},
            face_angle=face_index*10-15,
            face_quality=FaceQuality.GOOD,
            blur_score=0.1 + face_index*0.05,
            brightness=0.6 + face_index*0.1,
            sharpness=0.8 - face_index*0.05,
            occlusion=0.05 + face_index*0.02
        )
    
    async def _filter_matched_faces(self, detected_faces: List[DetectedFace], query: FaceSearchQuery) -> List[DetectedFace]:
        """Filter faces that match the search criteria"""
        matched_faces = []
        
        for face in detected_faces:
            if await self._face_matches_query(face, query):
                matched_faces.append(face)
        
        return matched_faces
    
    async def _face_matches_query(self, face: DetectedFace, query: FaceSearchQuery) -> bool:
        """Check if a face matches the search query"""
        # Person search
        if query.search_type == FaceSearchType.PERSON_SEARCH:
            if query.person_id and face.person_id == query.person_id:
                return True
            if query.person_name and face.person_name == query.person_name:
                return True
        
        # Face similarity
        if query.search_type == FaceSearchType.FACE_SIMILARITY:
            if face.similarity_score and face.similarity_score >= query.similarity_threshold:
                return True
        
        # Demographic search
        if query.search_type == FaceSearchType.DEMOGRAPHIC_SEARCH:
            if not face.attributes:
                return False
            
            if query.age_range:
                if not face.attributes.age:
                    return False
                if not (query.age_range["min"] <= face.attributes.age <= query.age_range["max"]):
                    return False
            
            if query.gender and face.attributes.gender != query.gender:
                return False
            
            return True
        
        # Emotion search
        if query.search_type == FaceSearchType.EMOTION_SEARCH:
            if query.emotion and face.attributes and face.attributes.emotion == query.emotion:
                return True
        
        # Age range search
        if query.search_type == FaceSearchType.AGE_RANGE_SEARCH:
            if query.age_range and face.attributes and face.attributes.age:
                if query.age_range["min"] <= face.attributes.age <= query.age_range["max"]:
                    return True
        
        # Gender search
        if query.search_type == FaceSearchType.GENDER_SEARCH:
            if query.gender and face.attributes and face.attributes.gender == query.gender:
                return True
        
        # Expression search
        if query.search_type == FaceSearchType.EXPRESSION_SEARCH:
            if query.expression and face.attributes and face.attributes.expression == query.expression:
                return True
        
        # Celebrity recognition
        if query.search_type == FaceSearchType.CELEBRITY_RECOGNITION:
            if face.celebrity_name:
                return True
        
        # Unknown faces
        if query.search_type == FaceSearchType.UNKNOWN_FACES:
            if not face.person_id and not face.celebrity_name:
                return True
        
        # Default: include all faces for general searches
        return True
    
    async def _identify_persons(self, detected_faces: List[DetectedFace]) -> List[PersonIdentity]:
        """Identify persons from detected faces"""
        persons = {}
        
        for face in detected_faces:
            if face.person_id and face.person_name:
                if face.person_id not in persons:
                    persons[face.person_id] = PersonIdentity(
                        person_id=face.person_id,
                        person_name=face.person_name,
                        known_faces=[face.face_id],
                        reference_encoding=face.encoding,
                        description=f"Identified person: {face.person_name}",
                        tags=["identified", "person"],
                        total_appearances=1,
                        last_seen=datetime.utcnow(),
                        confidence_avg=face.detection_confidence,
                        privacy_level="public",
                        consent_given=True
                    )
                else:
                    persons[face.person_id].known_faces.append(face.face_id)
                    persons[face.person_id].total_appearances += 1
        
        return list(persons.values())
    
    def _find_celebrity_matches(self, detected_faces: List[DetectedFace]) -> List[Dict[str, Any]]:
        """Find celebrity matches in detected faces"""
        celebrity_matches = []
        
        for face in detected_faces:
            if face.celebrity_name:
                celebrity_matches.append({
                    "face_id": face.face_id,
                    "celebrity_name": face.celebrity_name,
                    "confidence": face.similarity_score or 0.85,
                    "profession": "Actor",  # Mock data
                    "verified": True
                })
        
        return celebrity_matches
    
    def _calculate_demographics(self, detected_faces: List[DetectedFace]) -> Dict[str, Any]:
        """Calculate demographics summary from detected faces"""
        if not detected_faces:
            return {}
        
        ages = []
        genders = {"male": 0, "female": 0, "unknown": 0}
        emotions = {}
        
        for face in detected_faces:
            if face.attributes:
                if face.attributes.age:
                    ages.append(face.attributes.age)
                
                if face.attributes.gender:
                    genders[face.attributes.gender.value] += 1
                
                if face.attributes.emotion:
                    emotion_key = face.attributes.emotion.value
                    emotions[emotion_key] = emotions.get(emotion_key, 0) + 1
        
        demographics = {
            "total_faces": len(detected_faces),
            "gender_distribution": genders,
            "emotions": emotions
        }
        
        if ages:
            demographics["age_statistics"] = {
                "min": min(ages),
                "max": max(ages),
                "average": sum(ages) / len(ages),
                "median": sorted(ages)[len(ages)//2]
            }
            demographics["age_distribution"] = {
                "0-20": len([a for a in ages if a <= 20]),
                "21-40": len([a for a in ages if 21 <= a <= 40]),
                "41-60": len([a for a in ages if 41 <= a <= 60]),
                "60+": len([a for a in ages if a > 60])
            }
        
        return demographics
    
    def _generate_face_timeline(self, detected_faces: List[DetectedFace], duration: float) -> List[Dict[str, Any]]:
        """Generate face timeline for video assets"""
        timeline = []
        
        for face in detected_faces:
            if face.timestamp is not None:
                timeline.append({
                    "timestamp": face.timestamp,
                    "face_id": face.face_id,
                    "person_id": face.person_id,
                    "person_name": face.person_name,
                    "confidence": face.detection_confidence,
                    "bounding_box": {
                        "x": face.bounding_box.x,
                        "y": face.bounding_box.y,
                        "width": face.bounding_box.width,
                        "height": face.bounding_box.height
                    }
                })
        
        return sorted(timeline, key=lambda x: x["timestamp"])
    
    def _generate_scene_faces(self, detected_faces: List[DetectedFace]) -> List[Dict[str, Any]]:
        """Generate scene-based face analysis"""
        scenes = []
        
        # Group faces by timestamp ranges (mock scene detection)
        scene_duration = 30.0  # 30 seconds per scene
        scene_faces = {}
        
        for face in detected_faces:
            if face.timestamp is not None:
                scene_index = int(face.timestamp // scene_duration)
                if scene_index not in scene_faces:
                    scene_faces[scene_index] = []
                scene_faces[scene_index].append(face)
        
        for scene_index, faces in scene_faces.items():
            scenes.append({
                "scene_index": scene_index,
                "start_time": scene_index * scene_duration,
                "end_time": (scene_index + 1) * scene_duration,
                "face_count": len(faces),
                "unique_persons": len(set(f.person_id for f in faces if f.person_id)),
                "faces": [f.face_id for f in faces]
            })
        
        return scenes
    
    def _calculate_face_quality_score(self, face: DetectedFace) -> float:
        """Calculate overall face quality score"""
        if not face.attributes:
            return 0.5
        
        quality_score = 0.0
        factors = 0
        
        if face.attributes.blur_score is not None:
            quality_score += (1.0 - face.attributes.blur_score)
            factors += 1
        
        if face.attributes.sharpness is not None:
            quality_score += face.attributes.sharpness
            factors += 1
        
        if face.attributes.brightness is not None:
            # Optimal brightness is around 0.5-0.7
            brightness_score = 1.0 - abs(face.attributes.brightness - 0.6) * 2
            quality_score += max(0, brightness_score)
            factors += 1
        
        if face.attributes.occlusion is not None:
            quality_score += (1.0 - face.attributes.occlusion)
            factors += 1
        
        return quality_score / factors if factors > 0 else 0.5
    
    def _assess_detection_quality(self, detected_faces: List[DetectedFace]) -> str:
        """Assess overall detection quality"""
        if not detected_faces:
            return "poor"
        
        avg_confidence = sum(f.detection_confidence for f in detected_faces) / len(detected_faces)
        avg_quality = sum(self._calculate_face_quality_score(f) for f in detected_faces) / len(detected_faces)
        
        overall_score = (avg_confidence + avg_quality) / 2
        
        if overall_score >= 0.9:
            return "excellent"
        elif overall_score >= 0.8:
            return "good"
        elif overall_score >= 0.6:
            return "fair"
        else:
            return "poor"
    
    def _get_match_type(self, search_type: FaceSearchType) -> str:
        """Get match type description based on search type"""
        match_types = {
            FaceSearchType.PERSON_SEARCH: "person_identification",
            FaceSearchType.FACE_SIMILARITY: "face_similarity",
            FaceSearchType.FACE_VERIFICATION: "face_verification",
            FaceSearchType.DEMOGRAPHIC_SEARCH: "demographic_match",
            FaceSearchType.EMOTION_SEARCH: "emotion_match",
            FaceSearchType.AGE_RANGE_SEARCH: "age_range_match",
            FaceSearchType.GENDER_SEARCH: "gender_match",
            FaceSearchType.EXPRESSION_SEARCH: "expression_match",
            FaceSearchType.FACE_COUNT: "face_count_match",
            FaceSearchType.GROUP_DETECTION: "group_detection",
            FaceSearchType.CELEBRITY_RECOGNITION: "celebrity_match",
            FaceSearchType.UNKNOWN_FACES: "unknown_face_match"
        }
        return match_types.get(search_type, "general_match")
    
    async def _calculate_face_statistics(self, results: List[FaceSearchResult]) -> Dict[str, Any]:
        """Calculate face search statistics"""
        total_faces = sum(r.face_count for r in results)
        unique_persons = len(set(p.person_id for r in results for p in r.identified_persons))
        unknown_faces = sum(len(r.unknown_faces) for r in results)
        celebrity_matches = sum(len(r.celebrity_matches) for r in results)
        
        # Quality distribution
        quality_scores = []
        for result in results:
            for face in result.detected_faces:
                quality_scores.append(self._calculate_face_quality_score(face))
        
        quality_distribution = {}
        if quality_scores:
            for score in quality_scores:
                if score >= 0.9:
                    quality_distribution["excellent"] = quality_distribution.get("excellent", 0) + 1
                elif score >= 0.8:
                    quality_distribution["good"] = quality_distribution.get("good", 0) + 1
                elif score >= 0.6:
                    quality_distribution["fair"] = quality_distribution.get("fair", 0) + 1
                else:
                    quality_distribution["poor"] = quality_distribution.get("poor", 0) + 1
        
        # Confidence distribution
        confidence_scores = []
        for result in results:
            for face in result.detected_faces:
                confidence_scores.append(face.detection_confidence)
        
        confidence_distribution = {}
        if confidence_scores:
            for score in confidence_scores:
                if score >= 0.9:
                    confidence_distribution["high"] = confidence_distribution.get("high", 0) + 1
                elif score >= 0.7:
                    confidence_distribution["medium"] = confidence_distribution.get("medium", 0) + 1
                else:
                    confidence_distribution["low"] = confidence_distribution.get("low", 0) + 1
        
        # Overall demographics
        all_faces = [face for result in results for face in result.detected_faces]
        demographics = self._calculate_demographics(all_faces)
        
        return {
            "total_faces": total_faces,
            "unique_persons": unique_persons,
            "unknown_faces": unknown_faces,
            "celebrity_matches": celebrity_matches,
            "quality_distribution": quality_distribution,
            "confidence_distribution": confidence_distribution,
            "demographics": demographics
        }
    
    async def analyze_asset_faces(self, request: FaceAnalysisRequest) -> FaceAnalysisResponse:
        """Analyze faces in an asset"""
        start_time = time.time()
        
        try:
            # Mock face analysis (in production, this would use actual AI models)
            detected_faces = await self._perform_face_analysis(request)
            
            # Identify persons
            identified_persons = await self._identify_persons(detected_faces)
            
            # Filter unknown faces
            unknown_faces = [face for face in detected_faces if not face.person_id and not face.celebrity_name]
            
            # Find celebrity matches
            celebrity_matches = self._find_celebrity_matches(detected_faces)
            
            # Calculate demographics
            demographics = self._calculate_demographics(detected_faces)
            
            # Calculate quality metrics
            quality_scores = [self._calculate_face_quality_score(face) for face in detected_faces]
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            
            # Quality distribution
            quality_distribution = {}
            for score in quality_scores:
                if score >= 0.9:
                    quality_distribution["excellent"] = quality_distribution.get("excellent", 0) + 1
                elif score >= 0.8:
                    quality_distribution["good"] = quality_distribution.get("good", 0) + 1
                elif score >= 0.6:
                    quality_distribution["fair"] = quality_distribution.get("fair", 0) + 1
                else:
                    quality_distribution["poor"] = quality_distribution.get("poor", 0) + 1
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return FaceAnalysisResponse(
                asset_id=request.asset_id,
                analysis_success=True,
                detected_faces=detected_faces,
                face_count=len(detected_faces),
                identified_persons=identified_persons,
                unknown_faces=unknown_faces,
                celebrity_matches=celebrity_matches,
                demographics=demographics,
                age_statistics=demographics.get("age_statistics"),
                gender_distribution=demographics.get("gender_distribution"),
                emotion_distribution=demographics.get("emotions"),
                average_face_quality=avg_quality,
                quality_distribution=quality_distribution,
                detection_quality_score=avg_quality,
                face_timeline=self._generate_analysis_timeline(detected_faces) if request.asset_id.startswith("video") else None,
                scene_analysis=None,  # Would be implemented with actual scene detection
                frame_analysis=None,  # Would be implemented with frame-by-frame analysis
                processing_time_ms=processing_time,
                detection_model=request.detection_model,
                recognition_model=request.recognition_model,
                frames_analyzed=10 if request.asset_id.startswith("video") else None,
                errors=[],
                warnings=[]
            )
            
        except Exception as e:
            logger.error(f"Face analysis failed: {e}")
            return FaceAnalysisResponse(
                asset_id=request.asset_id,
                analysis_success=False,
                errors=[str(e)],
                processing_time_ms=int((time.time() - start_time) * 1000),
                detection_model=request.detection_model,
                recognition_model=request.recognition_model
            )
    
    async def _perform_face_analysis(self, request: FaceAnalysisRequest) -> List[DetectedFace]:
        """Perform actual face analysis (mock implementation)"""
        # Mock face detection and analysis
        face_count = 3  # Mock: 3 faces detected
        detected_faces = []
        
        for i in range(face_count):
            face_id = f"face_{request.asset_id}_{i+1}"
            
            # Generate mock attributes
            attributes = FaceAttributes(
                age=25 + i*15,
                age_range={"min": 20 + i*15, "max": 30 + i*15},
                gender=Gender.FEMALE if i % 2 == 0 else Gender.MALE,
                gender_confidence=0.85 + i*0.05,
                emotion=Emotion.HAPPY if i == 0 else Emotion.NEUTRAL,
                emotion_confidence=0.8 + i*0.05,
                emotion_scores={
                    "happy": 0.8 if i == 0 else 0.2,
                    "neutral": 0.7 if i != 0 else 0.1,
                    "surprise": 0.1
                },
                expression=FaceExpression.SMILING if i == 0 else FaceExpression.NEUTRAL,
                expression_confidence=0.85,
                glasses=i == 2,
                glasses_confidence=0.9,
                beard=i == 1,
                beard_confidence=0.85,
                mustache=False,
                mustache_confidence=0.95,
                head_pose={"yaw": i*5-5, "pitch": i*2, "roll": i-1},
                face_angle=i*10-10,
                face_quality=FaceQuality.GOOD,
                blur_score=0.1 + i*0.05,
                brightness=0.6 + i*0.1,
                sharpness=0.9 - i*0.05,
                occlusion=0.05
            )
            
            # Generate mock encoding
            encoding = None
            if request.extract_encodings:
                encoding = FaceEncoding(
                    model=request.recognition_model,
                    encoding=[0.1 + i*0.1] * 512,
                    dimension=512,
                    confidence=0.9 - i*0.05
                )
            
            # Generate mock landmarks
            landmarks = None
            if request.extract_landmarks:
                landmark_points = [{"x": 100 + i*10 + j, "y": 200 + i*5 + j} for j in range(68)]
                landmarks = FaceLandmarks(
                    landmark_type=request.landmark_type,
                    points=landmark_points,
                    confidence=0.85
                )
            
            face = DetectedFace(
                face_id=face_id,
                bounding_box=BoundingBox(
                    x=50 + i*120,
                    y=75 + i*60,
                    width=100 + i*10,
                    height=120 + i*15,
                    confidence=0.9 - i*0.05
                ),
                landmarks=landmarks,
                attributes=attributes if request.extract_attributes else None,
                encoding=encoding,
                person_id=f"person_{i+1}" if request.identify_persons and i < 2 else None,
                person_name=f"Person {i+1}" if request.identify_persons and i < 2 else None,
                celebrity_name="Celebrity A" if request.detect_celebrities and i == 0 else None,
                similarity_score=0.85 - i*0.1,
                detection_model=request.detection_model,
                detection_confidence=0.9 - i*0.05,
                detection_time_ms=100 + i*20,
                frame_number=i*30 if request.asset_id.startswith("video") else None,
                timestamp=i*10.0 if request.asset_id.startswith("video") else None
            )
            
            detected_faces.append(face)
        
        return detected_faces
    
    def _generate_analysis_timeline(self, detected_faces: List[DetectedFace]) -> List[Dict[str, Any]]:
        """Generate timeline for face analysis"""
        timeline = []
        
        for face in detected_faces:
            if face.timestamp is not None:
                timeline.append({
                    "timestamp": face.timestamp,
                    "face_id": face.face_id,
                    "person_id": face.person_id,
                    "confidence": face.detection_confidence,
                    "attributes": {
                        "age": face.attributes.age if face.attributes else None,
                        "gender": face.attributes.gender.value if face.attributes and face.attributes.gender else None,
                        "emotion": face.attributes.emotion.value if face.attributes and face.attributes.emotion else None
                    }
                })
        
        return sorted(timeline, key=lambda x: x["timestamp"])
    
    async def get_face_search_stats(self) -> FaceSearchStats:
        """Get facial recognition search statistics"""
        try:
            # Mock statistics (in production, would query actual databases)
            return FaceSearchStats(
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
                    "mediapipe": 1200,
                    "opencv_dnn": 500
                },
                recognition_model_usage={
                    "facenet": 3200,
                    "arcface": 2100,
                    "cosface": 1500,
                    "insightface": 1200
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
                    "sad": 800,
                    "angry": 400,
                    "fear": 200,
                    "disgust": 100
                },
                consent_given_persons=720,
                anonymized_faces=1200,
                privacy_violations=0,
                detection_failures=150,
                recognition_failures=280,
                low_quality_faces=850
            )
            
        except Exception as e:
            logger.error(f"Failed to get face search statistics: {e}")
            raise


# Service instance
_face_search_service = None

def get_face_search_service() -> FaceSearchService:
    """Get face search service instance"""
    global _face_search_service
    if _face_search_service is None:
        _face_search_service = FaceSearchService()
    return _face_search_service
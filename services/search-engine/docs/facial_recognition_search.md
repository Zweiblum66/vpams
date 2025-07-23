# Facial Recognition Search

The Facial Recognition Search feature provides comprehensive face detection, recognition, and search capabilities for image and video assets. This advanced system enables users to find media content based on facial characteristics, person identity, demographics, emotions, and more while maintaining privacy compliance and high accuracy.

## Overview

Facial Recognition Search allows users to:
- Search for specific individuals by person ID or name
- Find faces similar to a reference image or encoding
- Filter content by demographics (age, gender, emotion)
- Detect and analyze facial expressions
- Find group photos or videos with specific size criteria
- Identify celebrities in media content
- Locate unidentified faces for manual tagging
- Analyze facial attributes and quality metrics
- Track face appearances across video timelines

## Core Features

### Face Detection Models

The system supports multiple state-of-the-art face detection models:

1. **MTCNN** (Multi-task CNN)
   - High accuracy (95%)
   - Medium speed
   - Supports landmarks
   - Minimum face size: 20 pixels

2. **RetinaFace** (Recommended)
   - Excellent accuracy (97%)
   - Fast processing
   - Supports landmarks
   - Minimum face size: 15 pixels

3. **OpenCV DNN**
   - Good accuracy (92%)
   - Fast processing
   - No landmark support
   - Minimum face size: 25 pixels

4. **DLIB HOG**
   - Good accuracy (88%)
   - Slow processing
   - Supports landmarks
   - Minimum face size: 30 pixels

5. **DLIB CNN**
   - High accuracy (94%)
   - Slow processing
   - Supports landmarks
   - Minimum face size: 20 pixels

6. **MediaPipe**
   - High accuracy (93%)
   - Very fast processing
   - Supports landmarks
   - Minimum face size: 25 pixels

7. **YOLO-Face**
   - Excellent accuracy (96%)
   - Fast processing
   - No landmark support
   - Minimum face size: 20 pixels

8. **BlazeFace**
   - Good accuracy (91%)
   - Very fast processing
   - Supports landmarks
   - Minimum face size: 15 pixels

### Face Recognition Models

The system supports various face recognition models for person identification:

1. **FaceNet**
   - High accuracy (96%)
   - 512-dimensional embeddings
   - Medium speed
   - Threshold: 0.6

2. **ArcFace** (Recommended)
   - Excellent accuracy (98%)
   - 512-dimensional embeddings
   - Medium speed
   - Threshold: 0.55

3. **CosFace**
   - Excellent accuracy (97%)
   - 512-dimensional embeddings
   - Medium speed
   - Threshold: 0.6

4. **SphereFace**
   - High accuracy (95%)
   - 256-dimensional embeddings
   - Fast processing
   - Threshold: 0.65

5. **OpenFace**
   - Good accuracy (92%)
   - 128-dimensional embeddings
   - Fast processing
   - Threshold: 0.7

6. **DeepFace**
   - High accuracy (94%)
   - 4096-dimensional embeddings
   - Slow processing
   - Threshold: 0.68

7. **InsightFace**
   - Excellent accuracy (97%)
   - 512-dimensional embeddings
   - Medium speed
   - Threshold: 0.6

8. **Face Recognition Library**
   - Good accuracy (93%)
   - 128-dimensional embeddings
   - Fast processing
   - Threshold: 0.6

### Search Types

#### 1. Person Search
Search for specific individuals by person ID or name:

```json
{
  "search_type": "person_search",
  "person_id": "person_123",
  "person_name": "John Doe",
  "similarity_threshold": 0.7,
  "min_confidence": 0.6,
  "asset_types": ["image", "video"],
  "page": 1,
  "limit": 20
}
```

**Use Cases:**
- Find all media containing a specific employee
- Locate appearances of VIP individuals
- Track person appearances across events
- Compliance and security monitoring

#### 2. Face Similarity Search
Find faces similar to a reference image or encoding:

```json
{
  "search_type": "face_similarity",
  "reference_image": "path/to/reference.jpg",
  "reference_encoding": [0.1, 0.2, ...],
  "similarity_threshold": 0.8,
  "match_type": "cosine_similarity",
  "min_confidence": 0.7,
  "asset_types": ["image"]
}
```

**Matching Algorithms:**
- **Cosine Similarity**: Measures angle between vectors
- **Euclidean Distance**: Straight-line distance in feature space
- **Manhattan Distance**: City-block distance
- **Correlation**: Statistical correlation measure
- **Chi-Squared**: Chi-squared distance
- **Intersection**: Histogram intersection
- **Deep Metric**: Advanced deep learning metrics
- **Threshold-Based**: Binary threshold matching

#### 3. Demographic Search
Search by age, gender, and other demographic attributes:

```json
{
  "search_type": "demographic_search",
  "age_range": {"min": 25, "max": 45},
  "gender": "female",
  "emotion": "happy",
  "expression": "smiling",
  "min_confidence": 0.6,
  "asset_types": ["image", "video"]
}
```

**Demographics Include:**
- **Age**: Estimated age with confidence ranges
- **Gender**: Male, female, or unknown
- **Emotion**: Happy, sad, angry, fear, surprise, disgust, neutral, contempt
- **Expression**: Smiling, frowning, laughing, crying, winking, etc.

#### 4. Emotion Search
Find faces expressing specific emotions:

```json
{
  "search_type": "emotion_search",
  "emotion": "happy",
  "min_confidence": 0.7,
  "emotion_threshold": 0.8,
  "asset_types": ["image"],
  "sort_by": "confidence",
  "sort_order": "desc"
}
```

**Supported Emotions:**
- **Happy**: Joy, satisfaction, contentment
- **Sad**: Sadness, sorrow, melancholy
- **Angry**: Anger, frustration, irritation
- **Fear**: Fear, anxiety, worry
- **Surprise**: Surprise, amazement, shock
- **Disgust**: Disgust, revulsion, disdain
- **Neutral**: Neutral, calm, composed
- **Contempt**: Contempt, scorn, disdain

#### 5. Age Range Search
Search within specific age ranges:

```json
{
  "search_type": "age_range_search",
  "age_range": {"min": 18, "max": 35},
  "min_confidence": 0.65,
  "asset_types": ["image", "video"],
  "include_age_statistics": true
}
```

#### 6. Gender Search
Filter by gender:

```json
{
  "search_type": "gender_search",
  "gender": "male",
  "min_confidence": 0.7,
  "gender_confidence_threshold": 0.8,
  "asset_types": ["image"]
}
```

#### 7. Expression Search
Search by facial expressions:

```json
{
  "search_type": "expression_search",
  "expression": "smiling",
  "min_confidence": 0.6,
  "expression_confidence_threshold": 0.8,
  "asset_types": ["image"]
}
```

**Supported Expressions:**
- **Smiling**: Various degrees of smiling
- **Frowning**: Frowning, scowling
- **Laughing**: Open-mouth laughter
- **Crying**: Crying, tears
- **Winking**: One-eye wink
- **Blinking**: Eye blinking
- **Mouth Open**: Open mouth (speaking, yawning)
- **Eyes Closed**: Closed eyes
- **Tongue Out**: Tongue sticking out
- **Neutral**: Neutral expression

#### 8. Face Count Search
Find assets with specific numbers of faces:

```json
{
  "search_type": "face_count",
  "min_face_count": 2,
  "max_face_count": 8,
  "exact_count": 5,
  "min_confidence": 0.6,
  "asset_types": ["image", "video"]
}
```

#### 9. Group Detection
Search for group photos/videos:

```json
{
  "search_type": "group_detection",
  "group_size_range": {"min": 3, "max": 10},
  "min_confidence": 0.6,
  "include_group_analysis": true,
  "asset_types": ["image"]
}
```

#### 10. Celebrity Recognition
Find assets containing celebrities:

```json
{
  "search_type": "celebrity_recognition",
  "celebrity_name": "John Doe",
  "min_confidence": 0.8,
  "verified_only": true,
  "asset_types": ["image", "video"]
}
```

#### 11. Unknown Faces
Find unidentified faces for manual tagging:

```json
{
  "search_type": "unknown_faces",
  "min_confidence": 0.7,
  "min_face_quality": "good",
  "exclude_poor_quality": true,
  "asset_types": ["image", "video"],
  "include_unknown_faces": true
}
```

#### 12. Face Verification
Verify if a specific person appears in assets:

```json
{
  "search_type": "face_verification",
  "person_id": "person_456",
  "reference_encoding": [0.2, 0.3, ...],
  "similarity_threshold": 0.75,
  "verification_threshold": 0.8,
  "asset_types": ["image"]
}
```

## API Endpoints

### Search by Face

**Endpoint:** `POST /search/face`

**Request Body:**
```json
{
  "search_type": "person_search",
  "person_id": "person_123",
  "similarity_threshold": 0.7,
  "min_confidence": 0.6,
  "asset_types": ["image", "video"],
  "include_attributes": true,
  "include_encodings": false,
  "include_landmarks": false,
  "include_unknown_faces": false,
  "page": 1,
  "limit": 20,
  "sort_by": "confidence",
  "sort_order": "desc"
}
```

**Response:**
```json
{
  "results": [
    {
      "asset_id": "asset-123",
      "asset_name": "Team Meeting Photo",
      "asset_type": "image",
      "detected_faces": [
        {
          "face_id": "face_001",
          "bounding_box": {
            "x": 100,
            "y": 150,
            "width": 200,
            "height": 240,
            "confidence": 0.95
          },
          "landmarks": {
            "landmark_type": "landmarks_68",
            "points": [
              {"x": 120, "y": 180},
              {"x": 125, "y": 185}
            ],
            "confidence": 0.9
          },
          "attributes": {
            "age": 28,
            "age_range": {"min": 25, "max": 31},
            "gender": "female",
            "gender_confidence": 0.92,
            "emotion": "happy",
            "emotion_confidence": 0.85,
            "emotion_scores": {
              "happy": 0.85,
              "neutral": 0.12,
              "surprise": 0.03
            },
            "expression": "smiling",
            "expression_confidence": 0.88,
            "glasses": false,
            "glasses_confidence": 0.95,
            "beard": false,
            "beard_confidence": 0.98,
            "mustache": false,
            "mustache_confidence": 0.99,
            "head_pose": {
              "yaw": 2.1,
              "pitch": -1.5,
              "roll": 0.8
            },
            "face_angle": 2.0,
            "face_quality": "excellent",
            "blur_score": 0.08,
            "brightness": 0.68,
            "sharpness": 0.92,
            "occlusion": 0.02
          },
          "encoding": {
            "model": "facenet",
            "encoding": [0.1, 0.2, 0.3, ...],
            "dimension": 512,
            "confidence": 0.94
          },
          "person_id": "person_123",
          "person_name": "Alice Johnson",
          "celebrity_name": null,
          "similarity_score": 0.91,
          "detection_model": "retinaface",
          "detection_confidence": 0.95,
          "detection_time_ms": 125
        }
      ],
      "face_count": 1,
      "matched_faces": [
        {
          "face_id": "face_001",
          "match_score": 0.91,
          "match_reason": "person_identification"
        }
      ],
      "match_score": 0.91,
      "match_type": "person_identification",
      "best_match_confidence": 0.95,
      "identified_persons": [
        {
          "person_id": "person_123",
          "person_name": "Alice Johnson",
          "known_faces": ["face_001"],
          "description": "Marketing team member",
          "tags": ["employee", "marketing"],
          "department": "Marketing",
          "role": "Marketing Specialist",
          "total_appearances": 12,
          "last_seen": "2024-01-15T10:30:00Z",
          "confidence_avg": 0.89,
          "privacy_level": "public",
          "consent_given": true
        }
      ],
      "unknown_faces": [],
      "celebrity_matches": [],
      "demographics": {
        "total_faces": 1,
        "gender_distribution": {"female": 1, "male": 0, "unknown": 0},
        "emotions": {"happy": 1},
        "age_statistics": {"min": 28, "max": 28, "average": 28.0}
      },
      "emotions_summary": {"happy": 1},
      "age_distribution": {"21-40": 1},
      "gender_distribution": {"female": 1},
      "average_face_quality": 0.85,
      "detection_quality": "excellent",
      "file_size": 2456789,
      "dimensions": {"width": 1920, "height": 1080},
      "format": "jpg",
      "processing_time_ms": 1250,
      "detection_model": "retinaface",
      "recognition_model": "facenet",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "analyzed_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "took": 185,
  "page": 1,
  "limit": 20,
  "pages": 1,
  "aggregations": {
    "face_count_distribution": {
      "buckets": [
        {"key": 1.0, "doc_count": 15},
        {"key": 2.0, "doc_count": 8}
      ]
    },
    "gender_distribution": {
      "buckets": [
        {"key": "female", "doc_count": 12},
        {"key": "male", "doc_count": 8}
      ]
    },
    "emotion_distribution": {
      "buckets": [
        {"key": "happy", "doc_count": 10},
        {"key": "neutral", "doc_count": 6}
      ]
    }
  },
  "total_faces_found": 1,
  "unique_persons": 1,
  "unknown_faces_count": 0,
  "celebrity_matches_count": 0,
  "quality_distribution": {"excellent": 1},
  "confidence_distribution": {"high": 1},
  "overall_demographics": {
    "total_faces": 1,
    "gender_distribution": {"female": 1},
    "emotions": {"happy": 1}
  },
  "search_metadata": {
    "search_type": "person_search",
    "execution_time": 0.185,
    "detection_model": "retinaface",
    "recognition_model": "facenet"
  }
}
```

### Analyze Asset Faces

**Endpoint:** `POST /search/face/analyze`

**Request Body:**
```json
{
  "asset_id": "asset_123",
  "detection_model": "retinaface",
  "recognition_model": "facenet",
  "landmark_type": "landmarks_68",
  "extract_attributes": true,
  "extract_encodings": true,
  "extract_landmarks": true,
  "identify_persons": true,
  "detect_celebrities": false,
  "min_face_size": 30,
  "min_confidence": 0.6,
  "max_faces": 10,
  "frame_interval": 30,
  "max_frames": 100,
  "scene_detection": false,
  "force_reanalysis": false,
  "parallel_processing": true,
  "gpu_acceleration": true,
  "anonymize_unknown": false,
  "respect_privacy_settings": true
}
```

**Response:**
```json
{
  "asset_id": "asset_123",
  "analysis_success": true,
  "detected_faces": [
    {
      "face_id": "face_001",
      "bounding_box": {
        "x": 120,
        "y": 80,
        "width": 200,
        "height": 240,
        "confidence": 0.92
      },
      "attributes": {
        "age": 35,
        "gender": "male",
        "emotion": "neutral",
        "expression": "neutral",
        "glasses": true,
        "beard": true,
        "face_quality": "good"
      },
      "encoding": {
        "model": "facenet",
        "encoding": [0.15, ...],
        "dimension": 512,
        "confidence": 0.91
      },
      "person_id": "person_789",
      "person_name": "Bob Smith",
      "detection_model": "retinaface",
      "detection_confidence": 0.92
    }
  ],
  "face_count": 1,
  "identified_persons": [
    {
      "person_id": "person_789",
      "person_name": "Bob Smith",
      "known_faces": ["face_001"],
      "department": "Engineering",
      "role": "Team Lead",
      "consent_given": true
    }
  ],
  "unknown_faces": [],
  "celebrity_matches": [],
  "demographics": {
    "total_faces": 1,
    "gender_distribution": {"male": 1, "female": 0},
    "emotions": {"neutral": 1},
    "age_statistics": {"average": 35.0}
  },
  "average_face_quality": 0.82,
  "quality_distribution": {"good": 1},
  "detection_quality_score": 0.82,
  "processing_time_ms": 2250,
  "detection_model": "retinaface",
  "recognition_model": "facenet",
  "errors": [],
  "warnings": [],
  "analyzed_at": "2024-01-15T10:30:00Z"
}
```

### Get Search Statistics

**Endpoint:** `GET /search/face/stats`

**Response:**
```json
{
  "total_searches": 2500,
  "total_faces_detected": 15000,
  "total_persons_identified": 3200,
  "unique_persons_database": 850,
  "identification_accuracy": 0.92,
  "false_positive_rate": 0.03,
  "false_negative_rate": 0.08,
  "avg_search_time_ms": 185.0,
  "avg_detection_time_ms": 95.0,
  "avg_recognition_time_ms": 140.0,
  "cache_hit_rate": 0.78,
  "images_analyzed": 4200,
  "videos_analyzed": 1800,
  "frames_analyzed": 180000,
  "detection_model_usage": {
    "retinaface": 3500,
    "mtcnn": 1800,
    "mediapipe": 1200
  },
  "recognition_model_usage": {
    "facenet": 3200,
    "arcface": 2100,
    "cosface": 1500
  },
  "face_quality_distribution": {
    "excellent": 4500,
    "good": 6200,
    "fair": 3800,
    "poor": 500
  },
  "confidence_distribution": {
    "high": 8500,
    "medium": 5200,
    "low": 1300
  },
  "age_distribution": {
    "0-20": 2800,
    "21-40": 7200,
    "41-60": 4100,
    "60+": 900
  },
  "gender_distribution": {
    "male": 7800,
    "female": 6900,
    "unknown": 300
  },
  "emotion_distribution": {
    "happy": 5200,
    "neutral": 6800,
    "surprise": 1500,
    "sad": 800
  },
  "consent_given_persons": 720,
  "anonymized_faces": 1200,
  "privacy_violations": 0,
  "detection_failures": 150,
  "recognition_failures": 280,
  "low_quality_faces": 850
}
```

## Advanced Features

### Facial Landmarks

The system supports multiple landmark detection types:

#### 5-Point Landmarks
- Both eyes (2 points)
- Nose tip (1 point)
- Mouth corners (2 points)
- Fast processing, basic alignment

#### 68-Point Landmarks (Most Common)
- Facial contour (17 points)
- Right eyebrow (5 points)
- Left eyebrow (5 points)
- Nose bridge (4 points)
- Lower nose (5 points)
- Right eye (6 points)
- Left eye (6 points)
- Outer lip (12 points)
- Inner lip (8 points)

#### 81-Point Landmarks
- Extended 68-point set
- Additional pupil points
- Enhanced eye tracking

#### 106-Point Landmarks
- Dense facial feature points
- Better expression analysis
- Higher accuracy alignment

#### 468-Point Landmarks (MediaPipe)
- Ultra-dense landmark detection
- Real-time processing optimized
- Comprehensive facial geometry

### Video Analysis Features

#### Frame-by-Frame Analysis
```json
{
  "frame_interval": 30,
  "max_frames": 100,
  "include_frame_analysis": true
}
```

#### Scene-Based Analysis
```json
{
  "scene_detection": true,
  "scene_threshold": 0.3,
  "min_scene_duration": 2.0
}
```

#### Face Timeline Tracking
```json
{
  "face_timeline": [
    {
      "timestamp": 0.0,
      "face_id": "face_001",
      "person_id": "person_123",
      "confidence": 0.92,
      "bounding_box": {"x": 100, "y": 150, "width": 200, "height": 240}
    },
    {
      "timestamp": 5.0,
      "face_id": "face_001",
      "person_id": "person_123",
      "confidence": 0.88,
      "bounding_box": {"x": 110, "y": 155, "width": 195, "height": 235}
    }
  ]
}
```

### Quality Assessment

#### Face Quality Levels
- **Excellent** (0.9-1.0): High resolution, good lighting, minimal blur
- **Good** (0.7-0.9): Acceptable quality for recognition
- **Fair** (0.5-0.7): Usable but may have issues
- **Poor** (0.3-0.5): Low quality, recognition may fail
- **Unusable** (0.0-0.3): Too poor for reliable recognition

#### Quality Metrics
- **Blur Score**: 0.0 (sharp) to 1.0 (very blurry)
- **Brightness**: 0.0 (very dark) to 1.0 (very bright)
- **Sharpness**: 0.0 (very soft) to 1.0 (very sharp)
- **Occlusion**: 0.0 (no occlusion) to 1.0 (heavily occluded)

### Privacy and Compliance

#### Privacy Settings
```json
{
  "privacy_level": "public",
  "consent_given": true,
  "anonymize_unknown": false,
  "respect_privacy_settings": true
}
```

#### Privacy Levels
- **Public**: Face can be used for all purposes
- **Internal**: Face can be used within organization
- **Restricted**: Face can only be used with explicit permission
- **Private**: Face should not be used for recognition

#### Compliance Features
- **GDPR Compliance**: Right to be forgotten, data portability
- **CCPA Compliance**: California Consumer Privacy Act compliance
- **HIPAA Compatibility**: Healthcare privacy protection (when applicable)
- **BIPA Compliance**: Illinois Biometric Information Privacy Act

### Performance Optimization

#### GPU Acceleration
```json
{
  "gpu_acceleration": true,
  "gpu_memory_limit": 4096,
  "batch_processing": true,
  "parallel_streams": 4
}
```

#### Caching Strategy
- **Face Encodings**: Cache computed embeddings
- **Detection Results**: Cache face detection results
- **Person Database**: Cache person information
- **Model Weights**: Cache loaded model weights

#### Processing Options
```json
{
  "parallel_processing": true,
  "max_concurrent_jobs": 4,
  "processing_priority": "normal",
  "timeout_seconds": 300
}
```

## Use Cases

### 1. Employee Recognition
**Scenario**: Corporate environment tracking employee appearances

```json
{
  "search_type": "person_search",
  "person_id": "emp_12345",
  "asset_types": ["image", "video"],
  "include_timeline": true,
  "respect_privacy_settings": true
}
```

**Benefits:**
- Automatic attendance tracking
- Security monitoring
- Event documentation
- Compliance auditing

### 2. Content Moderation
**Scenario**: Detecting inappropriate content based on facial expressions

```json
{
  "search_type": "emotion_search",
  "emotion": "angry",
  "min_confidence": 0.8,
  "include_context_analysis": true
}
```

**Benefits:**
- Automatic content flagging
- Safety monitoring
- Quality control
- Brand protection

### 3. Media Asset Organization
**Scenario**: Organizing family photos by family members

```json
{
  "search_type": "person_search",
  "person_name": "John Smith",
  "include_family_members": true,
  "group_by_events": true
}
```

**Benefits:**
- Automatic photo organization
- Quick content retrieval
- Memory preservation
- Event documentation

### 4. Security and Surveillance
**Scenario**: Security monitoring and threat detection

```json
{
  "search_type": "unknown_faces",
  "min_confidence": 0.9,
  "alert_on_unknown": true,
  "real_time_monitoring": true
}
```

**Benefits:**
- Unauthorized access detection
- Visitor tracking
- Incident investigation
- Perimeter security

### 5. Marketing and Analytics
**Scenario**: Analyzing customer demographics and emotions

```json
{
  "search_type": "demographic_search",
  "age_range": {"min": 18, "max": 35},
  "emotion": "happy",
  "include_analytics": true,
  "anonymize_results": true
}
```

**Benefits:**
- Customer behavior analysis
- Marketing effectiveness
- Demographic insights
- Engagement metrics

### 6. Accessibility Features
**Scenario**: Helping visually impaired users identify people in photos

```json
{
  "search_type": "person_search",
  "include_detailed_descriptions": true,
  "audio_descriptions": true,
  "relationship_context": true
}
```

**Benefits:**
- Accessibility enhancement
- Social inclusion
- Photo narration
- Context understanding

## Integration Examples

### React Component

```jsx
import React, { useState } from 'react';
import { searchByFace } from './api';

const FaceSearchComponent = () => {
  const [searchType, setSearchType] = useState('person_search');
  const [personId, setPersonId] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    try {
      const response = await searchByFace({
        search_type: searchType,
        person_id: personId,
        min_confidence: 0.7,
        asset_types: ['image', 'video'],
        include_attributes: true,
        page: 1,
        limit: 20
      });
      setResults(response.results);
    } catch (error) {
      console.error('Face search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="face-search">
      <div className="search-form">
        <select 
          value={searchType} 
          onChange={(e) => setSearchType(e.target.value)}
        >
          <option value="person_search">Person Search</option>
          <option value="emotion_search">Emotion Search</option>
          <option value="demographic_search">Demographics</option>
          <option value="celebrity_recognition">Celebrities</option>
        </select>
        
        {searchType === 'person_search' && (
          <input
            type="text"
            placeholder="Person ID"
            value={personId}
            onChange={(e) => setPersonId(e.target.value)}
          />
        )}
        
        <button onClick={handleSearch} disabled={loading}>
          {loading ? 'Searching...' : 'Search Faces'}
        </button>
      </div>

      <div className="results">
        {results.map(result => (
          <div key={result.asset_id} className="result-item">
            <img src={result.thumbnail_url} alt={result.asset_name} />
            <div className="face-info">
              <h4>{result.asset_name}</h4>
              <p>Faces: {result.face_count}</p>
              <p>Match Score: {result.match_score.toFixed(2)}</p>
              
              {result.identified_persons.map(person => (
                <div key={person.person_id} className="person-info">
                  <strong>{person.person_name}</strong>
                  <span>{person.department} - {person.role}</span>
                </div>
              ))}
              
              {result.demographics && (
                <div className="demographics">
                  <p>Gender: {Object.entries(result.demographics.gender_distribution).map(([gender, count]) => `${gender}: ${count}`).join(', ')}</p>
                  <p>Emotions: {Object.entries(result.demographics.emotions).map(([emotion, count]) => `${emotion}: ${count}`).join(', ')}</p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default FaceSearchComponent;
```

### Python SDK

```python
import requests
from typing import Dict, List, Optional

class FaceSearchClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def search_by_face(self, 
                      search_type: str,
                      person_id: Optional[str] = None,
                      person_name: Optional[str] = None,
                      age_range: Optional[Dict[str, int]] = None,
                      gender: Optional[str] = None,
                      emotion: Optional[str] = None,
                      min_confidence: float = 0.6,
                      asset_types: Optional[List[str]] = None,
                      page: int = 1,
                      limit: int = 20) -> Dict:
        """Search for faces in assets"""
        payload = {
            'search_type': search_type,
            'min_confidence': min_confidence,
            'asset_types': asset_types or ['image', 'video'],
            'page': page,
            'limit': limit
        }
        
        if person_id:
            payload['person_id'] = person_id
        if person_name:
            payload['person_name'] = person_name
        if age_range:
            payload['age_range'] = age_range
        if gender:
            payload['gender'] = gender
        if emotion:
            payload['emotion'] = emotion
        
        response = requests.post(
            f'{self.base_url}/search/face',
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def analyze_faces(self, 
                     asset_id: str,
                     detection_model: str = 'retinaface',
                     recognition_model: str = 'facenet',
                     extract_attributes: bool = True,
                     extract_encodings: bool = True,
                     identify_persons: bool = True) -> Dict:
        """Analyze faces in an asset"""
        payload = {
            'asset_id': asset_id,
            'detection_model': detection_model,
            'recognition_model': recognition_model,
            'extract_attributes': extract_attributes,
            'extract_encodings': extract_encodings,
            'identify_persons': identify_persons
        }
        
        response = requests.post(
            f'{self.base_url}/search/face/analyze',
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_statistics(self) -> Dict:
        """Get face search statistics"""
        response = requests.get(
            f'{self.base_url}/search/face/stats',
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# Usage Examples
client = FaceSearchClient('https://api.mams.com', 'your-api-key')

# Search for a specific person
person_results = client.search_by_face(
    search_type='person_search',
    person_id='emp_12345',
    min_confidence=0.8
)

# Search by demographics
demo_results = client.search_by_face(
    search_type='demographic_search',
    age_range={'min': 25, 'max': 40},
    gender='female',
    emotion='happy'
)

# Analyze faces in an asset
analysis = client.analyze_faces(
    asset_id='asset_123',
    extract_attributes=True,
    identify_persons=True
)

# Get system statistics
stats = client.get_statistics()
print(f"Total faces detected: {stats['total_faces_detected']}")
print(f"Recognition accuracy: {stats['identification_accuracy']:.2%}")
```

### Command Line Interface

```bash
# Search for a specific person
curl -X POST "https://api.mams.com/search/face" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "search_type": "person_search",
    "person_id": "emp_12345",
    "min_confidence": 0.8,
    "asset_types": ["image", "video"],
    "page": 1,
    "limit": 20
  }'

# Search by emotion
curl -X POST "https://api.mams.com/search/face" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "search_type": "emotion_search",
    "emotion": "happy",
    "min_confidence": 0.7,
    "asset_types": ["image"]
  }'

# Analyze faces in an asset
curl -X POST "https://api.mams.com/search/face/analyze" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "asset_123",
    "detection_model": "retinaface",
    "recognition_model": "facenet",
    "extract_attributes": true,
    "identify_persons": true
  }'

# Get statistics
curl -X GET "https://api.mams.com/search/face/stats" \
  -H "Authorization: Bearer your-api-key"
```

## Error Handling

### Common Errors

#### 1. Invalid Search Parameters
```json
{
  "error": {
    "code": "INVALID_SEARCH_PARAMETERS",
    "message": "Invalid age range: min must be less than max",
    "details": {
      "field": "age_range",
      "provided": {"min": 50, "max": 30},
      "valid_format": "min must be <= max"
    }
  }
}
```

#### 2. Asset Not Found
```json
{
  "error": {
    "code": "ASSET_NOT_FOUND",
    "message": "Asset not found or not accessible",
    "details": {
      "asset_id": "asset_123"
    }
  }
}
```

#### 3. Face Analysis Failed
```json
{
  "error": {
    "code": "FACE_ANALYSIS_FAILED",
    "message": "Could not analyze faces in asset",
    "details": {
      "asset_id": "asset_123",
      "reason": "Unsupported file format",
      "supported_formats": ["jpg", "png", "mp4", "mov"]
    }
  }
}
```

#### 4. Insufficient Permissions
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "message": "User does not have permission to access this person's data",
    "details": {
      "person_id": "person_123",
      "required_permission": "face_search_access",
      "privacy_level": "restricted"
    }
  }
}
```

## Best Practices

### Search Optimization
1. **Use Appropriate Confidence Thresholds**: Balance between precision and recall
2. **Choose Right Models**: RetinaFace + ArcFace for best accuracy
3. **Implement Caching**: Cache frequently accessed face encodings
4. **Batch Processing**: Process multiple assets together for efficiency

### Privacy Compliance
1. **Obtain Consent**: Always get explicit consent for face recognition
2. **Respect Privacy Settings**: Honor individual privacy preferences
3. **Anonymize Data**: Use anonymization for analytics and research
4. **Regular Audits**: Conduct regular privacy compliance audits

### Performance Optimization
1. **GPU Utilization**: Use GPU acceleration for large-scale processing
2. **Model Selection**: Choose appropriate models based on use case
3. **Quality Filtering**: Filter low-quality faces to improve accuracy
4. **Incremental Updates**: Update face database incrementally

### Security Considerations
1. **Access Control**: Implement proper authentication and authorization
2. **Data Encryption**: Encrypt face encodings and personal data
3. **Audit Logging**: Log all face search activities
4. **Regular Updates**: Keep detection and recognition models updated

This comprehensive facial recognition search system provides powerful capabilities for finding and analyzing faces in media content while maintaining high accuracy, privacy compliance, and performance standards. The flexible API design allows for integration into various applications and workflows, making it suitable for everything from personal photo organization to enterprise security systems.
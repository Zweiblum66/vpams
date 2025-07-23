# Audio Fingerprinting Feature Documentation

## Overview

The Audio Fingerprinting feature in MAMS provides comprehensive audio content identification, duplicate detection, and music recognition capabilities. It uses advanced acoustic fingerprinting algorithms to create unique digital signatures of audio content that can be matched against a database of known audio.

## Key Features

### 1. Multiple Fingerprinting Algorithms
- **Chromaprint**: Open-source acoustic fingerprinting (default)
- **Echoprint**: Optimized for music identification
- **Dejavu**: High accuracy for exact matching
- **Audfprint**: Robust to speed/pitch changes
- **Panako**: Efficient for large-scale matching
- **Shazam**: Commercial-grade music identification
- **SoundHound**: Query by humming support
- **MusicBrainz**: Open music database integration

### 2. Search Types
- **Duplicate Detection**: Find exact and near-duplicate audio files
- **Music Identification**: Identify songs and match against music database
- **Copyright Monitoring**: Detect copyrighted content usage
- **Broadcast Monitoring**: Track broadcast content and advertisements
- **Sample Detection**: Find audio samples and loops
- **Cover Detection**: Identify cover versions and remixes
- **Podcast Tracking**: Monitor podcast distribution
- **Voice Matching**: Match voice recordings (for authorized use)
- **Sound Effect Search**: Find similar sound effects
- **Audio Quality Check**: Identify quality issues and degradation

### 3. Match Types
- **Exact Match**: Identical audio content
- **Partial Match**: Segment or portion matches
- **Time-shifted**: Same content with time offset
- **Speed-altered**: Playback speed variations
- **Pitch-shifted**: Pitch modifications detected
- **Filtered**: EQ or filter modifications
- **Compressed**: Different compression levels
- **Noisy**: Matches despite added noise
- **Cover Version**: Different performance of same song
- **Remix**: Remixed versions detected

## API Endpoints

### 1. Search Audio Fingerprint
```
POST /api/v1/search/audio-fingerprint
```

Search for audio content using fingerprint matching.

#### Request Body
```json
{
  "reference_asset_id": "audio_001",
  "reference_audio_url": "https://example.com/audio.mp3",
  "reference_fingerprint": "fingerprint_data",
  "audio_data_base64": "base64_encoded_audio",
  "search_type": "duplicate_detection",
  "fingerprint_algorithm": "chromaprint",
  "fingerprint_type": "full_track",
  "min_match_score": 0.8,
  "max_results": 20,
  "include_partial_matches": true,
  "min_match_duration_ms": 5000,
  "time_range_ms": {
    "start": 0,
    "end": 300000
  },
  "asset_types": ["audio/mp3", "audio/wav"],
  "date_range": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-12-31T23:59:59Z"
  },
  "duration_range_ms": {
    "min": 30000,
    "max": 600000
  }
}
```

#### Response
```json
{
  "search_id": "search_123",
  "search_type": "duplicate_detection",
  "algorithm_used": "chromaprint",
  "fingerprint_version": "v1.0",
  "total_matches": 5,
  "matches": [
    {
      "match_id": "match_001",
      "asset_id": "audio_456",
      "asset_name": "Track 01.mp3",
      "match_score": 0.95,
      "match_type": "exact",
      "confidence": 0.98,
      "time_offset_ms": 0,
      "duration_matched_ms": 180000,
      "match_segments": [
        {
          "query_start_ms": 0,
          "query_end_ms": 180000,
          "reference_start_ms": 0,
          "reference_end_ms": 180000,
          "confidence": 0.98
        }
      ]
    }
  ],
  "music_metadata": {
    "title": "Song Title",
    "artist": "Artist Name",
    "album": "Album Name",
    "year": 2024,
    "genre": "Rock",
    "duration_ms": 180000,
    "isrc": "USRC12345678",
    "musicbrainz_id": "mb_123"
  },
  "query_audio_duration_ms": 180000,
  "processing_time_ms": 150,
  "applied_filters": ["min_match_score", "asset_types"],
  "search_metadata": {
    "fingerprint_time": 120,
    "search_time": 30,
    "total_candidates": 1000
  }
}
```

### 2. Analyze Audio
```
POST /api/v1/search/audio-fingerprint/analyze
```

Analyze audio content and extract fingerprints, features, and quality metrics.

#### Request Body
```json
{
  "asset_id": "audio_001",
  "audio_url": "https://example.com/audio.mp3",
  "extract_fingerprints": true,
  "fingerprint_algorithms": ["chromaprint", "echoprint"],
  "fingerprint_types": ["full_track", "robust"],
  "extract_features": true,
  "feature_types": ["mfcc", "chromagram", "tempo"],
  "analyze_segments": true,
  "segment_duration_ms": 5000,
  "assess_quality": true,
  "detect_music": true
}
```

#### Response
```json
{
  "analysis_id": "analysis_123",
  "asset_id": "audio_001",
  "analysis_success": true,
  "analysis": {
    "asset_id": "audio_001",
    "audio_path": "/storage/audio/audio_001.mp3",
    "duration_ms": 180000,
    "format": "mp3",
    "file_size": 5242880,
    "processing_time_ms": 500,
    "fingerprints": [
      {
        "algorithm": "chromaprint",
        "fingerprint_type": "full_track",
        "fingerprint_data": "AQAAD...",
        "fingerprint_size": 1024,
        "duration_covered_ms": 180000,
        "version": "1.0",
        "confidence": 0.99
      }
    ],
    "features": [
      {
        "feature_type": "mfcc",
        "feature_data": [1.2, 2.3, 3.4],
        "dimensions": 13,
        "time_step_ms": 10,
        "extraction_params": {
          "n_mfcc": 13,
          "hop_length": 512
        }
      }
    ],
    "segments": [
      {
        "segment_id": "seg_001",
        "start_time_ms": 0,
        "end_time_ms": 5000,
        "segment_type": "music",
        "confidence": 0.95,
        "features": {},
        "fingerprint": "segment_fingerprint"
      }
    ],
    "music_metadata": {
      "detected_key": "C_major",
      "detected_tempo": 120,
      "time_signature": "4/4",
      "mood_tags": ["energetic", "upbeat"],
      "instrument_tags": ["guitar", "drums", "bass"]
    },
    "quality_metrics": {
      "overall_quality_score": 85,
      "quality_level": "good",
      "sample_rate": 44100,
      "bit_depth": 16,
      "bitrate_kbps": 256,
      "codec": "mp3",
      "clipping_detected": false,
      "noise_level_db": -60,
      "snr_db": 55,
      "thd_percent": 0.5,
      "issues": [],
      "warnings": ["slight compression artifacts"]
    }
  },
  "errors": [],
  "warnings": []
}
```

### 3. Get Audio Fingerprint Statistics
```
GET /api/v1/search/audio-fingerprint/stats
```

Get comprehensive statistics about the audio fingerprinting system.

#### Response
```json
{
  "total_searches": 15000,
  "total_matches": 45000,
  "total_audio_analyzed": 5000,
  "total_fingerprints_stored": 100000,
  "avg_search_time_ms": 120,
  "avg_analysis_time_ms": 450,
  "avg_match_confidence": 0.87,
  "algorithm_performance": {
    "chromaprint": {
      "usage_count": 8000,
      "avg_accuracy": 0.92,
      "avg_speed_ms": 100
    },
    "echoprint": {
      "usage_count": 4000,
      "avg_accuracy": 0.88,
      "avg_speed_ms": 120
    }
  },
  "search_type_distribution": {
    "duplicate_detection": 6000,
    "music_identification": 5000,
    "copyright_monitoring": 2000
  },
  "match_type_distribution": {
    "exact": 20000,
    "partial": 15000,
    "time_shifted": 5000
  },
  "audio_format_distribution": {
    "mp3": 60000,
    "wav": 25000,
    "flac": 10000
  },
  "quality_distribution": {
    "excellent": 20000,
    "good": 50000,
    "fair": 25000,
    "poor": 5000
  },
  "content_type_distribution": {
    "music": 70000,
    "speech": 20000,
    "mixed": 10000
  }
}
```

## Use Cases

### 1. Duplicate Detection
```python
# Find duplicate audio files in the system
query = {
    "reference_asset_id": "audio_master_001",
    "search_type": "duplicate_detection",
    "min_match_score": 0.95
}
```

### 2. Music Identification
```python
# Identify a song from audio data
query = {
    "audio_data_base64": base64_encoded_audio,
    "search_type": "music_identification",
    "fingerprint_algorithm": "shazam"
}
```

### 3. Copyright Monitoring
```python
# Monitor for copyrighted content usage
query = {
    "reference_asset_id": "copyrighted_track_001",
    "search_type": "copyright_monitoring",
    "include_partial_matches": true,
    "min_match_duration_ms": 10000
}
```

### 4. Broadcast Monitoring
```python
# Track advertisement playback
query = {
    "reference_asset_id": "advertisement_001",
    "search_type": "broadcast_monitoring",
    "date_range": {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-31T23:59:59Z"
    }
}
```

## Technical Details

### Fingerprint Generation Process
1. **Audio Loading**: Load audio file and convert to standard format (mono, 44.1kHz)
2. **Preprocessing**: Apply noise reduction and normalization
3. **Feature Extraction**: Extract acoustic features (spectral, temporal, rhythmic)
4. **Hash Generation**: Create compact hash representation
5. **Storage**: Store fingerprint in optimized index structure

### Matching Process
1. **Query Fingerprint**: Generate fingerprint from query audio
2. **Candidate Selection**: Use hash index to find potential matches
3. **Detailed Comparison**: Compare full fingerprints of candidates
4. **Time Alignment**: Align temporal positions for partial matches
5. **Confidence Scoring**: Calculate match confidence based on similarity

### Performance Characteristics
- **Fingerprint Generation**: ~100-500ms per minute of audio
- **Search Time**: ~50-200ms for millions of fingerprints
- **Storage**: ~1KB per minute of audio (varies by algorithm)
- **Accuracy**: 95%+ for exact matches, 85%+ for transformed audio

### Robustness
The fingerprinting system is robust to:
- **Audio Compression**: MP3, AAC encoding
- **Speed Changes**: ±10% playback speed variation
- **Pitch Shifting**: ±5% pitch modification
- **Noise Addition**: Moderate background noise
- **Filtering**: EQ and frequency filtering
- **Time Shifting**: Temporal offsets
- **Format Conversion**: Different audio formats

## Best Practices

### 1. Algorithm Selection
- Use **Chromaprint** for general-purpose fingerprinting
- Use **Shazam/SoundHound** for music identification
- Use **Dejavu** for exact duplicate detection
- Use **Audfprint** when robustness to transformations is needed

### 2. Performance Optimization
- Pre-compute fingerprints during ingestion
- Use appropriate fingerprint types (lightweight for real-time)
- Cache frequently accessed fingerprints
- Use batch processing for large-scale analysis

### 3. Quality Considerations
- Ensure source audio quality is sufficient (≥128kbps)
- Use lossless formats for reference audio when possible
- Monitor fingerprint database size and optimize periodically
- Regularly validate fingerprint accuracy

### 4. Privacy and Legal
- Obtain necessary rights for audio fingerprinting
- Implement access controls for voice matching features
- Comply with copyright and privacy regulations
- Maintain audit logs for fingerprint usage

## Integration Examples

### Python Client
```python
import requests
import base64

# Search for duplicates
def find_duplicates(asset_id):
    response = requests.post(
        "https://api.mams.com/v1/search/audio-fingerprint",
        json={
            "reference_asset_id": asset_id,
            "search_type": "duplicate_detection",
            "min_match_score": 0.9
        },
        headers={"Authorization": "Bearer YOUR_TOKEN"}
    )
    return response.json()

# Identify music
def identify_music(audio_file_path):
    with open(audio_file_path, "rb") as f:
        audio_data = base64.b64encode(f.read()).decode()
    
    response = requests.post(
        "https://api.mams.com/v1/search/audio-fingerprint",
        json={
            "audio_data_base64": audio_data,
            "search_type": "music_identification",
            "fingerprint_algorithm": "shazam"
        },
        headers={"Authorization": "Bearer YOUR_TOKEN"}
    )
    return response.json()

# Analyze audio quality
def analyze_audio(asset_id):
    response = requests.post(
        "https://api.mams.com/v1/search/audio-fingerprint/analyze",
        json={
            "asset_id": asset_id,
            "assess_quality": True,
            "extract_features": True
        },
        headers={"Authorization": "Bearer YOUR_TOKEN"}
    )
    return response.json()
```

### JavaScript/TypeScript Client
```typescript
interface AudioFingerprintQuery {
  reference_asset_id?: string;
  search_type: string;
  min_match_score?: number;
}

class AudioFingerprintClient {
  private apiUrl = 'https://api.mams.com/v1';
  private token: string;

  constructor(token: string) {
    this.token = token;
  }

  async searchFingerprint(query: AudioFingerprintQuery) {
    const response = await fetch(`${this.apiUrl}/search/audio-fingerprint`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`
      },
      body: JSON.stringify(query)
    });
    return response.json();
  }

  async analyzeAudio(assetId: string) {
    const response = await fetch(`${this.apiUrl}/search/audio-fingerprint/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`
      },
      body: JSON.stringify({
        asset_id: assetId,
        extract_fingerprints: true,
        assess_quality: true
      })
    });
    return response.json();
  }
}
```

## Troubleshooting

### Common Issues

1. **No Matches Found**
   - Verify audio quality is sufficient
   - Try different fingerprinting algorithms
   - Lower the minimum match score
   - Check if audio is in the database

2. **Slow Performance**
   - Use lightweight fingerprint types
   - Implement caching for frequent queries
   - Consider batch processing
   - Optimize database indices

3. **False Positives**
   - Increase minimum match score
   - Use more robust algorithms
   - Verify match duration thresholds
   - Check for overly compressed audio

4. **Memory Issues**
   - Limit concurrent analysis operations
   - Use streaming for large files
   - Implement fingerprint pruning
   - Monitor cache size

## Future Enhancements

1. **Machine Learning Integration**
   - Deep learning-based fingerprinting
   - Adaptive algorithm selection
   - Improved music metadata extraction

2. **Real-time Processing**
   - Live stream fingerprinting
   - Sub-second matching
   - Edge computing support

3. **Advanced Features**
   - Multi-language speech recognition
   - Emotion detection in audio
   - Source separation before fingerprinting

4. **Integration Expansion**
   - Spotify/Apple Music integration
   - Podcast platform APIs
   - Broadcast monitoring systems
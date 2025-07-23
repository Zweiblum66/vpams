# Timecode Search

The Timecode Search feature provides specialized search capabilities for time-based media content, enabling precise searches based on timecodes, durations, segments, and temporal metadata. This is essential for professional video and audio workflows where frame-accurate access is required.

## Overview

Timecode Search allows users to:
- Search for assets at specific timecodes
- Find content within timecode ranges
- Filter by duration and technical specifications
- Search within segments, markers, and chapters
- Find content based on subtitle timecodes
- Validate and convert between timecode formats

## Core Features

### Timecode Formats Supported

1. **Drop Frame** (29.97fps) - `HH:MM:SS;FF`
   - NTSC standard with frame dropping
   - Uses semicolon separator
   - Accounts for 29.97fps vs 30fps discrepancy

2. **Non-Drop Frame** (30fps) - `HH:MM:SS:FF`
   - Standard 30fps without frame dropping
   - Uses colon separator
   - Simpler calculation, no frame adjustments

3. **Film** (24fps) - `HH:MM:SS:FF`
   - Cinema standard 24fps
   - Frames 0-23 per second
   - Used in film and some digital cinema

4. **PAL** (25fps) - `HH:MM:SS:FF`
   - European broadcast standard
   - Frames 0-24 per second
   - Used in PAL regions

5. **NTSC** (29.97fps) - `HH:MM:SS:FF`
   - North American broadcast standard
   - Similar to drop frame but without dropping
   - Frames 0-29 per second

6. **Custom** - User-defined frame rates
   - Supports non-standard frame rates
   - Requires explicit frame rate specification

### Search Types

#### 1. Simple Search
Basic timecode or duration-based searches:
```json
{
  "search_type": "simple",
  "timecode": {
    "hours": 1,
    "minutes": 23,
    "seconds": 45,
    "frames": 12,
    "format": "non_drop_frame"
  },
  "tolerance_seconds": 1.0
}
```

#### 2. Advanced Search
Complex queries with multiple criteria:
```json
{
  "search_type": "advanced",
  "timecode_range": {
    "start": {"hours": 1, "minutes": 0, "seconds": 0, "frames": 0},
    "end": {"hours": 1, "minutes": 30, "seconds": 0, "frames": 0},
    "type": "overlap"
  },
  "min_duration": 60.0,
  "max_duration": 3600.0,
  "frame_rates": [24.0, 29.97, 30.0]
}
```

#### 3. Segment Search
Search within markers and chapters:
```json
{
  "search_type": "segment",
  "segment_markers": ["intro", "outro", "commercial_break"],
  "chapter_titles": ["Opening", "Act 1", "Conclusion"]
}
```

#### 4. Marker Search
Search based on timeline markers:
```json
{
  "search_type": "marker",
  "segment_markers": ["interview_start", "b_roll", "graphics"]
}
```

#### 5. Subtitle Search
Search based on subtitle content and timecodes:
```json
{
  "search_type": "subtitle",
  "subtitle_text": "important dialogue",
  "subtitle_language": "en"
}
```

#### 6. Metadata Search
Search based on technical metadata:
```json
{
  "search_type": "metadata",
  "frame_rates": [29.97, 30.0],
  "resolutions": ["1920x1080", "3840x2160"],
  "video_formats": ["mp4", "mov"]
}
```

### Range Types

#### Exact Match
Find assets with exact timecode matches:
```json
{
  "timecode_range": {
    "start": {"hours": 1, "minutes": 0, "seconds": 0, "frames": 0},
    "end": {"hours": 1, "minutes": 0, "seconds": 5, "frames": 0},
    "type": "exact"
  }
}
```

#### Range Search
Find assets within a specific range:
```json
{
  "timecode_range": {
    "start": {"hours": 0, "minutes": 0, "seconds": 0, "frames": 0},
    "end": {"hours": 1, "minutes": 0, "seconds": 0, "frames": 0},
    "type": "range"
  }
}
```

#### Overlap Search
Find assets that overlap with the specified range:
```json
{
  "timecode_range": {
    "start": {"hours": 1, "minutes": 0, "seconds": 0, "frames": 0},
    "end": {"hours": 1, "minutes": 30, "seconds": 0, "frames": 0},
    "type": "overlap"
  }
}
```

#### Contains Search
Find assets that contain the specified range:
```json
{
  "timecode_range": {
    "start": {"hours": 1, "minutes": 5, "seconds": 0, "frames": 0},
    "end": {"hours": 1, "minutes": 10, "seconds": 0, "frames": 0},
    "type": "contains"
  }
}
```

#### Within Search
Find assets completely within the specified range:
```json
{
  "timecode_range": {
    "start": {"hours": 0, "minutes": 0, "seconds": 0, "frames": 0},
    "end": {"hours": 2, "minutes": 0, "seconds": 0, "frames": 0},
    "type": "within"
  }
}
```

## API Endpoints

### Search by Timecode
```http
POST /search/timecode
Content-Type: application/json

{
  "search_type": "simple",
  "timecode": {
    "hours": 1,
    "minutes": 23,
    "seconds": 45,
    "frames": 12,
    "format": "non_drop_frame"
  },
  "tolerance_seconds": 1.0,
  "asset_types": ["video"],
  "frame_rates": [24.0, 29.97, 30.0],
  "page": 1,
  "limit": 20
}
```

Response:
```json
{
  "results": [
    {
      "asset_id": "asset-123",
      "asset_name": "Interview_Final.mp4",
      "asset_type": "video",
      "duration": 1800.0,
      "duration_timecode": "00:30:00:00",
      "frame_rate": 29.97,
      "timecode_format": "non_drop_frame",
      "matched_timecode": "01:23:45:12",
      "matched_range": null,
      "match_score": 1.5,
      "match_type": "exact_timecode",
      "segment_title": null,
      "segment_description": null,
      "markers": null,
      "subtitle_matches": null,
      "metadata": {
        "codec": "H.264",
        "resolution": "1920x1080",
        "bitrate": 5000000
      },
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "took": 45,
  "page": 1,
  "limit": 20,
  "pages": 1,
  "aggregations": {
    "duration_stats": {
      "min": 30.0,
      "max": 7200.0,
      "avg": 1800.0
    },
    "frame_rate_distribution": {
      "buckets": [
        {"key": 29.97, "doc_count": 150},
        {"key": 24.0, "doc_count": 100}
      ]
    }
  },
  "search_metadata": {
    "search_type": "simple",
    "execution_time": 0.045
  }
}
```

### Validate Timecode
```http
POST /search/timecode/validate?timecode=01:23:45:12&format=non_drop_frame
```

Response:
```json
{
  "is_valid": true,
  "errors": [],
  "warnings": [],
  "normalized_timecode": "01:23:45:12",
  "total_seconds": 5025.4,
  "total_frames": 150762,
  "detected_format": "non_drop_frame",
  "suggested_format": "non_drop_frame"
}
```

### Convert Timecode
```http
POST /search/timecode/convert
Content-Type: application/json

{
  "source_timecode": "01:00:00:00",
  "source_format": "film",
  "target_format": "pal"
}
```

Response:
```json
{
  "source_timecode": "01:00:00:00",
  "target_timecode": "00:57:36:00",
  "source_format": "film",
  "target_format": "pal",
  "source_seconds": 3600.0,
  "target_seconds": 3456.0,
  "source_frames": 86400,
  "target_frames": 86400,
  "conversion_method": "frame_rate_conversion",
  "precision_loss": true,
  "warnings": [
    "Precision loss possible when converting from 24.0fps to 25.0fps"
  ]
}
```

### Get Timecode Statistics
```http
GET /search/timecode/stats
```

Response:
```json
{
  "total_searches": 1000,
  "total_assets_with_timecode": 2500,
  "avg_duration": 1800.0,
  "min_duration": 30.0,
  "max_duration": 7200.0,
  "frame_rate_distribution": {
    "29.97": 1000,
    "24.0": 800,
    "30.0": 700
  },
  "most_common_frame_rate": 29.97,
  "format_distribution": {
    "non_drop_frame": 1500,
    "film": 800,
    "pal": 200
  },
  "most_common_format": "non_drop_frame",
  "avg_search_time_ms": 45.0,
  "cache_hit_rate": 0.85
}
```

## Advanced Features

### Tolerance and Precision

#### Timecode Tolerance
Search with configurable tolerance for approximate matches:
```json
{
  "timecode": {
    "hours": 1,
    "minutes": 23,
    "seconds": 45,
    "frames": 12
  },
  "tolerance_seconds": 2.0,
  "tolerance_frames": 5
}
```

#### Precision Control
Control precision for different use cases:
- **Frame-accurate**: 0.0 seconds tolerance
- **Rough cut**: 1-5 seconds tolerance
- **Scene level**: 10-30 seconds tolerance

### Duration Filtering

#### Exact Duration
```json
{
  "min_duration": 1800.0,
  "max_duration": 1800.0
}
```

#### Duration Range
```json
{
  "min_duration": 60.0,
  "max_duration": 3600.0
}
```

#### Duration Categories
```json
{
  "duration_categories": ["short", "medium", "long"]
}
```

### Technical Metadata Filtering

#### Frame Rate Filtering
```json
{
  "frame_rates": [23.976, 24.0, 25.0, 29.97, 30.0, 50.0, 59.94, 60.0]
}
```

#### Resolution Filtering
```json
{
  "resolutions": [
    "720x480",    # SD
    "1280x720",   # HD
    "1920x1080",  # Full HD
    "2560x1440",  # QHD
    "3840x2160",  # 4K UHD
    "4096x2160"   # DCI 4K
  ]
}
```

#### Format Filtering
```json
{
  "video_formats": ["mp4", "mov", "avi", "mkv", "mxf"],
  "audio_formats": ["wav", "mp3", "aac", "flac", "opus"]
}
```

### Segment and Marker Search

#### Marker Types
- **Edit Points**: In/out points, cuts, transitions
- **Content Markers**: Intro, outro, commercial breaks
- **Technical Markers**: Audio peaks, scene changes
- **Custom Markers**: User-defined markers

#### Chapter Search
```json
{
  "chapter_titles": ["Opening", "Act 1", "Climax", "Resolution"],
  "chapter_descriptions": ["introduction", "conflict", "resolution"]
}
```

### Subtitle Integration

#### Subtitle Search
```json
{
  "subtitle_text": "important dialogue",
  "subtitle_language": "en",
  "subtitle_confidence": 0.8
}
```

#### Multi-language Support
```json
{
  "subtitle_languages": ["en", "es", "fr", "de"],
  "subtitle_text": "hello world"
}
```

## Data Model

### Asset Timecode Schema
```json
{
  "asset_id": "asset-123",
  "duration": 1800.0,
  "duration_timecode": "00:30:00:00",
  "frame_rate": 29.97,
  "timecode_format": "non_drop_frame",
  "timecode_start": 0.0,
  "timecode_end": 1800.0,
  "start_timecode": "00:00:00:00",
  "end_timecode": "00:30:00:00",
  "markers": [
    {
      "name": "intro",
      "timecode": "00:00:10:00",
      "timecode_seconds": 10.0,
      "type": "content",
      "description": "Opening sequence"
    }
  ],
  "chapters": [
    {
      "title": "Introduction",
      "description": "Opening chapter",
      "start_timecode": "00:00:00:00",
      "end_timecode": "00:05:00:00",
      "start_seconds": 0.0,
      "end_seconds": 300.0
    }
  ],
  "subtitles": [
    {
      "text": "Welcome to our program",
      "start_timecode": "00:00:05:00",
      "end_timecode": "00:00:08:00",
      "start_seconds": 5.0,
      "end_seconds": 8.0,
      "language": "en",
      "confidence": 0.95
    }
  ]
}
```

### Search Index Mapping
```json
{
  "mappings": {
    "properties": {
      "duration": {"type": "float"},
      "frame_rate": {"type": "float"},
      "timecode_format": {"type": "keyword"},
      "timecode_start": {"type": "float"},
      "timecode_end": {"type": "float"},
      "resolution": {"type": "keyword"},
      "video_format": {"type": "keyword"},
      "audio_format": {"type": "keyword"},
      "markers": {
        "type": "nested",
        "properties": {
          "name": {"type": "keyword"},
          "timecode_seconds": {"type": "float"},
          "type": {"type": "keyword"}
        }
      },
      "chapters": {
        "type": "nested",
        "properties": {
          "title": {"type": "text"},
          "start_seconds": {"type": "float"},
          "end_seconds": {"type": "float"}
        }
      },
      "subtitles": {
        "type": "nested",
        "properties": {
          "text": {"type": "text"},
          "start_seconds": {"type": "float"},
          "end_seconds": {"type": "float"},
          "language": {"type": "keyword"}
        }
      }
    }
  }
}
```

## Use Cases

### 1. Editorial Workflows
- **Rough Cut Assembly**: Find specific scenes and shots
- **Fine Cut Editing**: Frame-accurate content location
- **Color Correction**: Locate specific timecode ranges
- **Audio Sweetening**: Find dialogue and music segments

### 2. Content Review
- **Quality Control**: Review specific time ranges
- **Compliance Check**: Verify content at exact timecodes
- **Client Review**: Navigate to specific feedback points
- **Version Comparison**: Compare timecode ranges across versions

### 3. Archive Management
- **Content Discovery**: Find archived content by timecode
- **Tape Digitization**: Locate specific segments on tapes
- **Legacy Content**: Search old content with timecode metadata
- **Preservation**: Verify content integrity at specific points

### 4. Live Production
- **Replay Systems**: Quick access to specific moments
- **Highlight Reels**: Compile specific timecode ranges
- **Live Editing**: Real-time content location
- **Broadcasting**: Precise content scheduling

### 5. Post-Production
- **Conform Process**: Match timecodes across systems
- **VFX Pipeline**: Locate shots requiring effects
- **Audio Post**: Sync and locate audio elements
- **Finishing**: Final quality control at specific points

## Integration Examples

### NLE Integration
```javascript
// Adobe Premiere Pro Panel
function searchByTimecode(timecode) {
    const searchParams = {
        search_type: 'simple',
        timecode: {
            hours: timecode.hours,
            minutes: timecode.minutes,
            seconds: timecode.seconds,
            frames: timecode.frames,
            format: 'non_drop_frame'
        },
        tolerance_seconds: 0.5,
        asset_types: ['video']
    };
    
    return fetch('/search/timecode', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(searchParams)
    });
}
```

### Avid Media Composer
```javascript
// Avid Script API
function findClipAtTimecode(timecode) {
    const searchQuery = {
        search_type: 'simple',
        timecode: parseAvidTimecode(timecode),
        tolerance_frames: 2,
        asset_types: ['video', 'audio']
    };
    
    return searchTimecode(searchQuery);
}
```

### DaVinci Resolve
```lua
-- DaVinci Resolve Lua Script
function searchTimecodeRange(startTC, endTC)
    local searchData = {
        search_type = "advanced",
        timecode_range = {
            start = parseTimecode(startTC),
            ["end"] = parseTimecode(endTC),
            type = "range"
        },
        frame_rates = {23.976, 24.0, 25.0, 29.97}
    }
    
    return callTimecodeSearch(searchData)
end
```

## Performance Considerations

### Indexing Strategy
1. **Dual Indexing**: Store both timecode strings and seconds
2. **Range Indexing**: Pre-calculate range boundaries
3. **Segment Indexing**: Index markers and chapters separately
4. **Nested Fields**: Use nested mappings for complex structures

### Query Optimization
1. **Range Queries**: Use numeric range queries for performance
2. **Filtering**: Apply filters before full-text search
3. **Aggregations**: Pre-calculate common statistics
4. **Caching**: Cache frequent timecode conversions

### Scaling Considerations
1. **Sharding**: Distribute by date or project
2. **Replica Sets**: Read replicas for search queries
3. **Hot/Cold Storage**: Archive old timecode data
4. **Compression**: Compress rarely-accessed timecode data

## Error Handling

### Common Errors
1. **Invalid Timecode Format**: Malformed timecode strings
2. **Frame Rate Mismatch**: Incompatible frame rates
3. **Range Errors**: Invalid timecode ranges
4. **Precision Loss**: Conversion between formats

### Error Responses
```json
{
  "error": {
    "code": "INVALID_TIMECODE_FORMAT",
    "message": "Timecode must be in HH:MM:SS:FF format",
    "details": {
      "provided_timecode": "1:23:45:12",
      "expected_format": "01:23:45:12"
    }
  }
}
```

## Best Practices

### Timecode Management
1. **Consistent Formats**: Use consistent timecode formats within projects
2. **Validation**: Always validate timecodes before indexing
3. **Conversion**: Convert to common format for searching
4. **Precision**: Consider precision requirements for use case

### Search Optimization
1. **Narrow Searches**: Use specific filters to reduce result sets
2. **Tolerance Settings**: Adjust tolerance based on use case
3. **Batch Processing**: Process multiple timecode searches together
4. **Caching**: Cache frequent search patterns

### Data Quality
1. **Metadata Validation**: Ensure accurate timecode metadata
2. **Synchronization**: Keep timecodes synchronized across systems
3. **Version Control**: Track timecode changes across versions
4. **Audit Trail**: Log all timecode-related operations

This comprehensive timecode search system provides the foundation for professional video and audio workflows, enabling precise, frame-accurate content discovery and management across the MAMS platform.
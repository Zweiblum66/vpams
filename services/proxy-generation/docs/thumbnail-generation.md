# Thumbnail Generation Guide

## Overview

The Proxy Generation Service provides comprehensive thumbnail generation capabilities for video files, including single thumbnails, batch generation, and contact sheets (sprite/mosaic).

## Features

### 1. Single Thumbnail Generation
- Extract a single frame from video at specified time offset
- Automatic time offset selection (10% of duration)
- Customizable dimensions and quality
- Support for multiple formats (JPEG, PNG, WebP)

### 2. Batch Thumbnail Generation
- Generate multiple thumbnails from a video
- Three selection methods:
  - **Interval**: Extract frames at regular intervals
  - **Scene**: Extract frames at scene changes
  - **Keyframe**: Extract I-frames (keyframes)
- GPU acceleration support for scaling
- Configurable count and quality

### 3. Contact Sheet Generation
- Create a grid/mosaic of video thumbnails
- Customizable grid dimensions
- Optional timestamp overlays
- Configurable padding and background color
- Font customization for timestamps

## API Endpoints

### Single Thumbnail

```http
POST /api/v1/thumbnails/single
Authorization: Bearer {token}
Content-Type: application/json
```

Request body:
```json
{
  "asset_id": "asset-123",
  "input_path": "/storage/videos/sample.mp4",
  "time_offset": "auto",  // or specific seconds like "10.5"
  "width": 640,
  "height": 360,
  "format": "jpg",
  "quality": 90,
  "priority": "normal"
}
```

Response:
```json
{
  "job_id": "job-456",
  "status": "queued",
  "message": "Single thumbnail generation job created"
}
```

### Batch Thumbnails

```http
POST /api/v1/thumbnails/batch
Authorization: Bearer {token}
Content-Type: application/json
```

Request body:
```json
{
  "asset_id": "asset-123",
  "input_path": "/storage/videos/sample.mp4",
  "count": 10,
  "width": 320,
  "height": 180,
  "format": "jpg",
  "quality": 85,
  "start_time": 0,
  "duration": null,  // null = entire video
  "method": "interval",  // interval, scene, or keyframe
  "priority": "normal"
}
```

### Contact Sheet

```http
POST /api/v1/thumbnails/contact-sheet
Authorization: Bearer {token}
Content-Type: application/json
```

Request body:
```json
{
  "asset_id": "asset-123",
  "input_path": "/storage/videos/sample.mp4",
  "grid_size": [4, 4],  // [columns, rows]
  "thumb_width": 320,
  "thumb_height": 180,
  "padding": 5,
  "background_color": "black",
  "include_timestamps": true,
  "font_size": 12,
  "font_color": "white",
  "priority": "normal"
}
```

## Thumbnail Selection Methods

### 1. Interval Method
- Divides video duration by thumbnail count
- Extracts frames at regular intervals
- Best for overview of entire video
- Most predictable results

Example FFmpeg filter:
```
fps=1/{interval}
```

### 2. Scene Detection Method
- Uses FFmpeg scene detection algorithm
- Extracts frames at significant visual changes
- Good for videos with distinct scenes
- May produce fewer thumbnails than requested

Example FFmpeg filter:
```
select='gt(scene,0.3)'
```

### 3. Keyframe Method
- Extracts only I-frames (keyframes)
- Typically higher quality frames
- Good for videos with motion
- Frame count depends on video encoding

Example FFmpeg filter:
```
select='eq(pict_type,I)'
```

## Output Formats

### Supported Formats
- **JPEG** (.jpg, .jpeg)
  - Best for photos and complex images
  - Smaller file sizes
  - Quality setting: 1-100
- **PNG** (.png)
  - Lossless compression
  - Best for graphics with transparency
  - Larger file sizes
- **WebP** (.webp)
  - Modern format with good compression
  - Supports both lossy and lossless
  - Quality setting: 1-100

### Quality Settings
- JPEG: 1-100 (higher is better, 85 recommended)
- PNG: Compression level 0-9 (6 default)
- WebP: 1-100 (85 recommended)

## Contact Sheet Options

### Grid Configuration
- **Columns**: 1-10 (default: 4)
- **Rows**: 1-10 (default: 4)
- Total thumbnails = columns × rows

### Visual Options
- **Padding**: Space between thumbnails (0-50 pixels)
- **Background Color**: Any valid color name or hex
- **Thumbnail Size**: Individual thumbnail dimensions

### Timestamp Options
- **Include Timestamps**: Show time position
- **Font Size**: 8-48 pixels
- **Font Color**: Any valid color name
- **Position**: Bottom-left of each thumbnail

## Performance Considerations

### GPU Acceleration
When GPU acceleration is enabled:
- Thumbnail scaling uses GPU (scale_cuda, scale_qsv)
- Significantly faster for batch operations
- Automatic fallback to CPU if GPU unavailable

### Processing Time Estimates
| Operation | Count | CPU Time | GPU Time |
|-----------|-------|----------|----------|
| Single Thumb | 1 | ~1s | ~0.5s |
| Batch (Interval) | 10 | ~5s | ~2s |
| Batch (Scene) | 10 | ~10s | ~5s |
| Contact Sheet 4x4 | 16 | ~8s | ~3s |

### Resource Usage
- **Memory**: ~50MB per concurrent job
- **Disk Space**: Temporary files in processing
- **CPU/GPU**: Varies by resolution and codec

## Best Practices

### 1. Thumbnail Dimensions
- Keep aspect ratio of source video
- Standard sizes:
  - Small: 160×90 (16:9)
  - Medium: 320×180 (16:9)
  - Large: 640×360 (16:9)
  - HD: 1280×720 (16:9)

### 2. Format Selection
- Use JPEG for most use cases (good quality/size ratio)
- Use PNG only when transparency needed
- Use WebP for modern web applications

### 3. Method Selection
- **Interval**: Default choice for predictable results
- **Scene**: For videos with distinct scenes
- **Keyframe**: For motion-heavy content

### 4. Contact Sheet Design
- 4×4 grid works well for most videos
- Increase padding for clearer separation
- Include timestamps for navigation reference

## Error Handling

### Common Errors

1. **Invalid Time Offset**
   - Error: Time offset exceeds video duration
   - Solution: Use "auto" or verify duration first

2. **No Video Stream**
   - Error: Input file has no video
   - Solution: Verify file is video format

3. **Processing Timeout**
   - Error: Thumbnail generation timeout
   - Solution: Reduce count or dimensions

### Retry Strategy
- Jobs automatically retry on transient failures
- Maximum 3 retry attempts
- Exponential backoff between retries

## Example Workflows

### 1. Generate Video Preview Thumbnails
```python
# Generate 10 evenly-spaced thumbnails
response = await client.post("/api/v1/thumbnails/batch", json={
    "asset_id": asset_id,
    "input_path": video_path,
    "count": 10,
    "method": "interval",
    "width": 320,
    "height": 180
})
```

### 2. Create Navigation Contact Sheet
```python
# Create 6x4 contact sheet with timestamps
response = await client.post("/api/v1/thumbnails/contact-sheet", json={
    "asset_id": asset_id,
    "input_path": video_path,
    "grid_size": [6, 4],
    "include_timestamps": True,
    "thumb_width": 160,
    "thumb_height": 90
})
```

### 3. Extract Key Moments
```python
# Use scene detection for key moments
response = await client.post("/api/v1/thumbnails/batch", json={
    "asset_id": asset_id,
    "input_path": video_path,
    "count": 20,
    "method": "scene",
    "width": 640,
    "height": 360,
    "quality": 95
})
```

## Storage Structure

Thumbnails are stored with the following key structure:
```
{bucket}/assets/{asset_id}/proxies/thumbnail/{method}_{index}.{format}
```

Examples:
- `assets/123/proxies/thumbnail/single_10.5.jpg`
- `assets/123/proxies/thumbnail/interval_0.jpg`
- `assets/123/proxies/thumbnail/4x4.jpg` (contact sheet)

## Monitoring

### Metrics
- `thumbnail_generation_duration`: Processing time
- `thumbnail_generation_count`: Number generated
- `thumbnail_generation_errors`: Error count
- `thumbnail_storage_size`: Total storage used

### Logging
All thumbnail operations are logged with:
- Job ID and asset ID
- Method and parameters
- Processing duration
- Storage location
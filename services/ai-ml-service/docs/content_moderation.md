# Content Moderation Service

The Content Moderation service provides automated detection and classification of toxic, inappropriate, or harmful content in text. It's designed to help maintain safe and appropriate content within the MAMS platform.

## Features

- **Toxicity Detection**: Identifies toxic, abusive, or harmful language
- **Multi-category Classification**: Detects various types of inappropriate content:
  - Toxic language
  - Severe toxicity
  - Obscene content
  - Threats
  - Insults
  - Identity-based hate speech
- **Configurable Thresholds**: Adjustable sensitivity levels
- **Batch Processing**: Process multiple texts efficiently
- **Video Transcript Moderation**: Automatically transcribe and moderate video content
- **Caching**: Intelligent caching for improved performance
- **Comprehensive Logging**: Detailed logs for monitoring and debugging

## API Endpoints

### 1. Moderate Text Content

**Endpoint**: `POST /api/v1/moderate/content`

**Description**: Moderate a single text for inappropriate content.

**Parameters**:
- `text` (required): The text content to moderate
- `threshold` (optional): Confidence threshold (0.0-1.0, default: 0.5)
- `asset_id` (optional): Associated asset ID for tracking

**Example Request**:
```bash
curl -X POST "http://localhost:8006/api/v1/moderate/content" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "text=This is a test message&threshold=0.5"
```

**Example Response**:
```json
{
  "data": {
    "is_toxic": false,
    "severity": "low",
    "overall_score": 0.1,
    "flagged_categories": [],
    "detailed_scores": [
      {
        "category": "toxic",
        "score": 0.1,
        "flagged": false
      },
      {
        "category": "severe_toxic",
        "score": 0.05,
        "flagged": false
      },
      {
        "category": "obscene",
        "score": 0.02,
        "flagged": false
      },
      {
        "category": "threat",
        "score": 0.01,
        "flagged": false
      },
      {
        "category": "insult",
        "score": 0.03,
        "flagged": false
      },
      {
        "category": "identity_hate",
        "score": 0.02,
        "flagged": false
      }
    ],
    "threshold": 0.5,
    "model_name": "content_moderation",
    "text_length": 20
  }
}
```

### 2. Batch Content Moderation

**Endpoint**: `POST /api/v1/moderate/batch`

**Description**: Moderate multiple texts in a single request.

**Parameters**:
- `texts` (required): Array of texts to moderate
- `threshold` (optional): Confidence threshold (0.0-1.0, default: 0.5)
- `asset_ids` (optional): Comma-separated list of asset IDs

**Example Request**:
```bash
curl -X POST "http://localhost:8006/api/v1/moderate/batch" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "texts=Hello world&texts=This is another message&threshold=0.5"
```

**Example Response**:
```json
{
  "data": {
    "results": [
      {
        "is_toxic": false,
        "severity": "low",
        "overall_score": 0.1,
        "flagged_categories": [],
        "detailed_scores": [...],
        "threshold": 0.5,
        "model_name": "content_moderation",
        "text_length": 11
      },
      {
        "is_toxic": false,
        "severity": "low",
        "overall_score": 0.08,
        "flagged_categories": [],
        "detailed_scores": [...],
        "threshold": 0.5,
        "model_name": "content_moderation",
        "text_length": 23
      }
    ],
    "total_processed": 2
  }
}
```

### 3. Video Transcript Moderation

**Endpoint**: `POST /api/v1/moderate/video-transcript`

**Description**: Transcribe video content and moderate the transcript.

**Parameters**:
- `file` (required): Video file to process
- `threshold` (optional): Confidence threshold (0.0-1.0, default: 0.5)
- `language` (optional): Language for transcription
- `asset_id` (optional): Associated asset ID

**Example Request**:
```bash
curl -X POST "http://localhost:8006/api/v1/moderate/video-transcript" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@video.mp4" \
  -F "threshold=0.5"
```

**Example Response**:
```json
{
  "data": {
    "transcription": {
      "text": "Hello, this is a test video",
      "language": "en",
      "segments": [...],
      "model_name": "speech_to_text"
    },
    "moderation": {
      "is_toxic": false,
      "severity": "low",
      "overall_score": 0.1,
      "flagged_categories": [],
      "detailed_scores": [...],
      "threshold": 0.5,
      "model_name": "content_moderation",
      "text_length": 27
    },
    "asset_id": "asset_123"
  }
}
```

## Configuration

The content moderation service can be configured through environment variables:

```bash
# Enable/disable content moderation
ENABLE_CONTENT_MODERATION=true

# Model configuration
CONTENT_MODERATION_MODEL=unitary/toxic-bert

# Processing limits
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=300

# Caching
CACHE_TTL=3600
```

## Response Fields

### Main Response Fields

- `is_toxic` (boolean): Whether the content is flagged as toxic
- `severity` (string): Severity level: "low", "medium", "high"
- `overall_score` (float): Highest toxicity score across all categories
- `flagged_categories` (array): List of categories that exceeded the threshold
- `detailed_scores` (array): Detailed scores for each category
- `threshold` (float): The threshold used for classification
- `model_name` (string): Name of the model used
- `text_length` (integer): Length of the processed text

### Detailed Score Fields

- `category` (string): Toxicity category name
- `score` (float): Confidence score (0.0-1.0)
- `flagged` (boolean): Whether this category exceeded the threshold

## Categories

The content moderation service detects the following categories:

1. **Toxic**: General toxic language
2. **Severe Toxic**: Extremely toxic content
3. **Obscene**: Obscene or profane content
4. **Threat**: Threatening language
5. **Insult**: Insulting or degrading language
6. **Identity Hate**: Hate speech targeting identity groups

## Severity Levels

- **Low**: Overall score < 0.5
- **Medium**: Overall score 0.5 - 0.8
- **High**: Overall score > 0.8

## Best Practices

### 1. Threshold Selection

- **Strict (0.3-0.4)**: High sensitivity, may catch borderline cases
- **Moderate (0.5-0.6)**: Balanced approach, recommended for most use cases
- **Permissive (0.7-0.8)**: Lower sensitivity, only catches clearly toxic content

### 2. Batch Processing

- Use batch endpoints for processing multiple texts efficiently
- Limit batch size to 20 texts per request
- Consider implementing pagination for larger datasets

### 3. Caching

- The service automatically caches results for identical inputs
- Cache TTL is configurable (default: 1 hour)
- Use consistent text formatting for better cache hit rates

### 4. Error Handling

- Always handle potential errors (network issues, model loading failures)
- Implement retry logic for transient failures
- Log errors for monitoring and debugging

### 5. Performance Optimization

- Use appropriate batch sizes for your use case
- Monitor response times and adjust concurrent request limits
- Consider implementing rate limiting on client side

## Integration Examples

### Python Example

```python
import requests
import asyncio

class ContentModerationClient:
    def __init__(self, base_url="http://localhost:8006"):
        self.base_url = base_url
    
    async def moderate_text(self, text, threshold=0.5):
        """Moderate a single text."""
        url = f"{self.base_url}/api/v1/moderate/content"
        data = {
            "text": text,
            "threshold": threshold
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()
    
    async def moderate_batch(self, texts, threshold=0.5):
        """Moderate multiple texts."""
        url = f"{self.base_url}/api/v1/moderate/batch"
        data = {
            "texts": texts,
            "threshold": threshold
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()

# Usage
client = ContentModerationClient()

# Moderate single text
result = await client.moderate_text("This is a test message")
print(f"Toxic: {result['data']['is_toxic']}")
print(f"Severity: {result['data']['severity']}")

# Moderate batch
texts = ["Hello world", "This is another message"]
results = await client.moderate_batch(texts)
print(f"Processed {results['data']['total_processed']} texts")
```

### JavaScript Example

```javascript
class ContentModerationClient {
    constructor(baseUrl = 'http://localhost:8006') {
        this.baseUrl = baseUrl;
    }
    
    async moderateText(text, threshold = 0.5) {
        const url = `${this.baseUrl}/api/v1/moderate/content`;
        const formData = new FormData();
        formData.append('text', text);
        formData.append('threshold', threshold);
        
        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    async moderateVideo(file, threshold = 0.5) {
        const url = `${this.baseUrl}/api/v1/moderate/video-transcript`;
        const formData = new FormData();
        formData.append('file', file);
        formData.append('threshold', threshold);
        
        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
}

// Usage
const client = new ContentModerationClient();

// Moderate text
const result = await client.moderateText("This is a test message");
console.log(`Toxic: ${result.data.is_toxic}`);
console.log(`Severity: ${result.data.severity}`);

// Moderate video
const fileInput = document.getElementById('videoFile');
const file = fileInput.files[0];
const videoResult = await client.moderateVideo(file);
console.log('Transcription:', videoResult.data.transcription.text);
console.log('Moderation:', videoResult.data.moderation);
```

## Monitoring and Metrics

The service provides various metrics for monitoring:

- Request count and rate
- Response times
- Error rates
- Model loading times
- Cache hit rates

Use these metrics to:
- Monitor service health
- Optimize performance
- Plan capacity
- Identify issues

## Troubleshooting

### Common Issues

1. **Model Loading Errors**
   - Ensure sufficient memory is available
   - Check model paths and permissions
   - Verify PyTorch installation

2. **High Response Times**
   - Check model cache size
   - Monitor concurrent requests
   - Consider GPU acceleration

3. **Inconsistent Results**
   - Verify text preprocessing
   - Check threshold consistency
   - Review model version

### Debug Mode

Enable debug mode for detailed logging:

```bash
LOG_LEVEL=DEBUG python -m src.main
```

This will provide detailed information about:
- Model loading and initialization
- Request processing
- Cache operations
- Error details
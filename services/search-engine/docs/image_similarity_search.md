# Image Similarity Search

The Image Similarity Search feature provides comprehensive image similarity search functionality for the MAMS platform. It enables users to find visually similar images, detect duplicates, perform reverse image searches, and analyze visual content using state-of-the-art computer vision techniques.

## Overview

Image Similarity Search allows users to:
- Find visually similar images using deep learning features
- Detect exact and near-duplicate images efficiently
- Perform reverse image searches to find origins and variations
- Search by artistic style, color palette, or content themes
- Analyze image quality and visual characteristics
- Extract comprehensive features for content organization
- Identify semantic relationships between visual content

## Core Features

### 1. Multiple Search Types

#### Visual Similarity
- **Purpose**: Find images with similar overall visual appearance
- **Use Cases**: Content discovery, visual asset management, style matching
- **Technology**: Deep CNN features with cosine similarity
- **Accuracy**: High (85-95% depending on content type)

#### Content Similarity
- **Purpose**: Find images with similar objects, scenes, or subjects
- **Use Cases**: Object-based search, scene matching, thematic organization
- **Technology**: Object detection features and semantic embeddings
- **Accuracy**: Very High (90-98% for common objects)

#### Style Similarity
- **Purpose**: Find images with similar artistic style or technique
- **Use Cases**: Art collection management, style-based filtering, creative workflows
- **Technology**: Style transfer features and texture analysis
- **Accuracy**: High (80-90% for distinct styles)

#### Color Similarity
- **Purpose**: Find images with similar color palettes or dominant colors
- **Use Cases**: Brand consistency, mood-based search, color theming
- **Technology**: Color histogram analysis and palette extraction
- **Accuracy**: Very High (95%+ for color matching)

#### Texture Similarity
- **Purpose**: Find images with similar surface textures or patterns
- **Use Cases**: Material identification, texture cataloging, pattern matching
- **Technology**: Local Binary Patterns and Gabor filters
- **Accuracy**: High (85-92% for distinct textures)

#### Shape Similarity
- **Purpose**: Find images with similar geometric shapes or structures
- **Use Cases**: Architectural matching, object shape analysis, structural similarity
- **Technology**: Edge detection and contour analysis
- **Accuracy**: High (80-90% for clear shapes)

#### Semantic Similarity
- **Purpose**: Find images with similar conceptual meaning or context
- **Use Cases**: Conceptual search, meaning-based organization, context matching
- **Technology**: Vision-language models (CLIP) and semantic embeddings
- **Accuracy**: Very High (90-95% for semantic concepts)

#### Perceptual Hash Matching
- **Purpose**: Fast duplicate and near-duplicate detection
- **Use Cases**: Duplicate removal, content deduplication, quality control
- **Technology**: Perceptual hashing algorithms (pHash, aHash, dHash)
- **Speed**: Very Fast (sub-millisecond comparisons)

#### Duplicate Detection
- **Purpose**: Identify exact and near-exact duplicate images
- **Use Cases**: Storage optimization, content cleaning, rights management
- **Technology**: Combined perceptual hashing and feature matching
- **Accuracy**: Excellent (99%+ for exact duplicates, 95%+ for near-duplicates)

#### Reverse Image Search
- **Purpose**: Find all variations and usages of a reference image
- **Use Cases**: Copyright monitoring, usage tracking, source identification
- **Technology**: Multi-modal feature matching and similarity clustering
- **Coverage**: Comprehensive across all similarity types

### 2. Feature Extraction Models

#### ResNet50 (Recommended for General Use)
- **Dimensions**: 2048
- **Accuracy**: 85%
- **Speed**: Medium
- **Best For**: General-purpose image similarity
- **Use Cases**: Content discovery, visual organization, broad similarity search

#### EfficientNet (Recommended for Performance)
- **Dimensions**: 1280
- **Accuracy**: 88%
- **Speed**: Fast
- **Best For**: High-performance applications with good accuracy
- **Use Cases**: Real-time search, mobile applications, resource-constrained environments

#### CLIP (Recommended for Semantic Search)
- **Dimensions**: 512
- **Accuracy**: 90%
- **Speed**: Medium
- **Best For**: Semantic and conceptual similarity
- **Use Cases**: Text-to-image search, conceptual matching, cross-modal retrieval

#### Vision Transformer (ViT)
- **Dimensions**: 768
- **Accuracy**: 88%
- **Speed**: Medium
- **Best For**: Fine-grained visual features and attention-based analysis
- **Use Cases**: Detailed visual analysis, artistic content, complex scenes

#### VGG16/VGG19
- **Dimensions**: 4096
- **Accuracy**: 82-83%
- **Speed**: Slow
- **Best For**: Traditional CNN features, texture analysis
- **Use Cases**: Texture similarity, traditional computer vision tasks

#### MobileNet
- **Dimensions**: 1024
- **Accuracy**: 78%
- **Speed**: Very Fast
- **Best For**: Mobile and edge deployment, real-time applications
- **Use Cases**: Mobile apps, edge computing, resource-limited scenarios

#### DINO (Self-Supervised)
- **Dimensions**: 768
- **Accuracy**: 87%
- **Speed**: Medium
- **Best For**: Self-supervised features, robust representations
- **Use Cases**: Unsupervised learning, robust feature extraction

#### Swin Transformer
- **Dimensions**: 1024
- **Accuracy**: 89%
- **Speed**: Slow
- **Best For**: Hierarchical visual features, multi-scale analysis
- **Use Cases**: Complex scene analysis, hierarchical visual understanding

#### ConvNeXt
- **Dimensions**: 768
- **Accuracy**: 87%
- **Speed**: Medium
- **Best For**: Modern CNN architecture, efficient processing
- **Use Cases**: Balanced accuracy and performance requirements

#### DenseNet
- **Dimensions**: 1920
- **Accuracy**: 86%
- **Speed**: Medium
- **Best For**: Dense feature connections, comprehensive analysis
- **Use Cases**: Feature-rich analysis, comprehensive similarity

#### Inception V3
- **Dimensions**: 2048
- **Accuracy**: 84%
- **Speed**: Medium
- **Best For**: Multi-scale feature analysis, inception modules
- **Use Cases**: Multi-scale similarity, complex visual patterns

### 3. Similarity Metrics

#### Cosine Similarity (Recommended)
- **Range**: 0.0 - 1.0 (higher is better)
- **Best For**: Normalized feature vectors, angle-based similarity
- **Use Cases**: Most similarity searches, general-purpose matching
- **Speed**: Very Fast
- **Robustness**: High to vector magnitude variations

#### Euclidean Distance
- **Range**: 0.0 - ∞ (lower is better)
- **Best For**: Spatial distance in feature space
- **Use Cases**: Geometric similarity, spatial relationships
- **Speed**: Very Fast
- **Robustness**: Sensitive to vector magnitude

#### Manhattan Distance (L1)
- **Range**: 0.0 - ∞ (lower is better)
- **Best For**: Robust to outliers, city-block distance
- **Use Cases**: Robust similarity, outlier-resistant matching
- **Speed**: Very Fast
- **Robustness**: High to outliers and noise

#### Hamming Distance
- **Range**: 0 - bit_length (lower is better)
- **Best For**: Binary vectors, perceptual hashes
- **Use Cases**: Fast duplicate detection, hash comparison
- **Speed**: Extremely Fast
- **Robustness**: High for binary representations

#### Jaccard Similarity
- **Range**: 0.0 - 1.0 (higher is better)
- **Best For**: Set similarity, binary feature overlap
- **Use Cases**: Binary feature matching, set comparisons
- **Speed**: Fast
- **Robustness**: Good for sparse binary features

#### Pearson Correlation
- **Range**: -1.0 - 1.0 (higher is better)
- **Best For**: Linear relationships, correlation analysis
- **Use Cases**: Linear feature relationships, correlation-based matching
- **Speed**: Medium
- **Robustness**: Good for linear relationships

#### Structural Similarity (SSIM)
- **Range**: 0.0 - 1.0 (higher is better)
- **Best For**: Spatial structure preservation, perceptual similarity
- **Use Cases**: Perceptual similarity, image quality assessment
- **Speed**: Slow
- **Robustness**: Excellent for perceptual similarity

#### Earth Mover's Distance (EMD)
- **Range**: 0.0 - ∞ (lower is better)
- **Best For**: Distribution matching, histogram comparison
- **Use Cases**: Color distribution, texture histogram matching
- **Speed**: Slow
- **Robustness**: Excellent for distribution similarity

### 4. Perceptual Hash Algorithms

#### Perceptual Hash (pHash) - Recommended
- **Bit Length**: 64 bits
- **Speed**: Fast
- **Accuracy**: High
- **Rotation Invariant**: No
- **Scale Invariant**: Yes
- **Best For**: General duplicate detection, robust to minor modifications

#### Average Hash (aHash)
- **Bit Length**: 64 bits
- **Speed**: Very Fast
- **Accuracy**: Medium
- **Rotation Invariant**: No
- **Scale Invariant**: Yes
- **Best For**: Fast duplicate detection, basic similarity

#### Difference Hash (dHash)
- **Bit Length**: 64 bits
- **Speed**: Very Fast
- **Accuracy**: Medium-High
- **Rotation Invariant**: No
- **Scale Invariant**: Yes
- **Best For**: Gradient-based similarity, edge-sensitive matching

#### Wavelet Hash (wHash)
- **Bit Length**: 64 bits
- **Speed**: Medium
- **Accuracy**: High
- **Rotation Invariant**: No
- **Scale Invariant**: Yes
- **Best For**: Frequency domain analysis, texture-based similarity

#### Color Hash
- **Bit Length**: 288 bits
- **Speed**: Medium
- **Accuracy**: High
- **Rotation Invariant**: Yes
- **Scale Invariant**: Yes
- **Best For**: Color-based similarity, palette matching

#### Crop Resistant Hash
- **Bit Length**: 256 bits
- **Speed**: Slow
- **Accuracy**: Very High
- **Rotation Invariant**: Yes
- **Scale Invariant**: Yes
- **Best For**: Robust to cropping and partial occlusion

## API Endpoints

### 1. Image Similarity Search

**Endpoint**: `POST /search/image-similarity`

Performs comprehensive image similarity search with multiple input options and advanced filtering.

#### Request Body

```json
{
  "reference_asset_id": "asset_123",
  "reference_image_url": "https://example.com/image.jpg",
  "reference_features": [0.1, 0.2, ...],
  "reference_hash": "abcd1234efgh5678",
  
  "similarity_type": "visual_similarity",
  "feature_model": "resnet50",
  "similarity_metric": "cosine_similarity",
  
  "similarity_threshold": 0.8,
  "max_distance": 0.5,
  
  "asset_types": ["image"],
  "file_formats": ["jpg", "png", "tiff"],
  "size_range": {"min": 100000, "max": 10000000},
  "dimension_range": {
    "width": {"min": 800, "max": 4000},
    "height": {"min": 600, "max": 3000}
  },
  "date_range": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-12-31T23:59:59Z"
  },
  
  "min_quality_score": 0.6,
  "exclude_low_quality": true,
  
  "include_duplicates": false,
  "include_near_duplicates": true,
  "region_based": false,
  "multi_scale": false,
  
  "include_features": false,
  "include_analysis": false,
  "include_thumbnails": true,
  
  "page": 1,
  "limit": 20,
  "sort_by": "similarity_score",
  "sort_order": "desc"
}
```

#### Response

```json
{
  "query_id": "query_123",
  "reference_asset_id": "asset_123",
  "similarity_type": "visual_similarity",
  
  "matches": [
    {
      "asset_id": "asset_456",
      "similarity_score": 0.85,
      "distance": 0.15,
      "match_type": "visual_similarity",
      
      "asset_name": "Similar Image",
      "asset_type": "image",
      "file_path": "/storage/similar.jpg",
      "thumbnail_url": "/thumbs/similar_thumb.jpg",
      
      "matched_features": ["global_features", "color_features"],
      "feature_similarities": {
        "global_features": 0.85,
        "color_features": 0.90,
        "texture_features": 0.78
      },
      "regions_of_interest": [
        {
          "x": 100, "y": 150,
          "width": 200, "height": 240,
          "confidence": 0.92
        }
      ],
      
      "match_confidence": 0.88,
      "quality_score": 0.91
    }
  ],
  
  "total": 25,
  "page": 1,
  "limit": 20,
  "pages": 2,
  
  "max_similarity": 0.92,
  "avg_similarity": 0.81,
  "min_similarity": 0.71,
  
  "took": 150,
  "feature_extraction_time": 80,
  "search_time": 70,
  
  "search_metadata": {
    "query_id": "query_123",
    "similarity_type": "visual_similarity",
    "feature_model": "resnet50",
    "similarity_metric": "cosine_similarity",
    "similarity_threshold": 0.8,
    "filters_applied": ["asset_types", "min_quality_score"],
    "execution_time": 0.15,
    "cache_hit": true
  },
  
  "clusters": [
    {
      "cluster_id": "cluster_1",
      "cluster_center": "asset_456",
      "cluster_size": 8,
      "avg_similarity": 0.87
    }
  ],
  "cluster_count": 3
}
```

### 2. Image Analysis

**Endpoint**: `POST /search/image-similarity/analyze`

Performs comprehensive image analysis and feature extraction for an asset.

#### Request Body

```json
{
  "asset_id": "asset_123",
  
  "feature_models": ["resnet50", "efficientnet", "clip"],
  "extract_hashes": true,
  "hash_types": ["perceptual_hash", "average_hash", "difference_hash"],
  
  "analyze_color": true,
  "analyze_texture": true,
  "analyze_shape": true,
  "assess_quality": true,
  "detect_objects": true,
  
  "preprocessing": ["resize", "normalize"],
  "resize_for_analysis": true,
  "target_size": {"width": 512, "height": 512},
  
  "parallel_processing": true,
  "gpu_acceleration": false,
  "force_reanalysis": false
}
```

#### Response

```json
{
  "asset_id": "asset_123",
  "analysis_success": true,
  "processing_time_ms": 250.0,
  "models_used": ["resnet50", "efficientnet", "clip"],
  "preprocessing_applied": ["resize", "normalize"],
  "errors": [],
  "warnings": [],
  "from_cache": false,
  "cached_at": null,
  
  "analysis": {
    "asset_id": "asset_123",
    "image_path": "/storage/asset_123.jpg",
    "dimensions": {"width": 1920, "height": 1080},
    "file_size": 2456789,
    "format": "jpg",
    
    "feature_vectors": [
      {
        "model": "resnet50",
        "features": [0.1, 0.2, ...],
        "dimension": 2048,
        "layer": "avg_pool",
        "preprocessing": ["resize", "normalize"],
        "extraction_time_ms": 120.0,
        "confidence": 0.95
      }
    ],
    
    "perceptual_hashes": [
      {
        "hash_type": "perceptual_hash",
        "hash_value": "abcd1234efgh5678",
        "bit_length": 64,
        "normalized": true,
        "rotation_invariant": false,
        "scale_invariant": true
      }
    ],
    
    "color_profile": {
      "dominant_colors": ["#FF5733", "#33FF57", "#3357FF"],
      "color_palette": [
        {"color": "#FF5733", "percentage": 35.2},
        {"color": "#33FF57", "percentage": 28.7}
      ],
      "average_color": "#7F7F7F",
      "brightness": 0.72,
      "contrast": 0.85,
      "saturation": 0.68,
      "color_space": "RGB",
      "histogram": {
        "red": [12, 45, 78, ...],
        "green": [23, 56, 89, ...],
        "blue": [34, 67, 90, ...]
      }
    },
    
    "texture": {
      "lbp_histogram": [0.1, 0.2, 0.15, ...],
      "glcm_features": {
        "contrast": 45.7,
        "dissimilarity": 12.3,
        "homogeneity": 0.85,
        "energy": 0.92,
        "correlation": 0.76
      },
      "entropy": 6.2,
      "energy": 0.88,
      "homogeneity": 0.91,
      "contrast": 42.1
    },
    
    "shape": {
      "edges": 1247,
      "contours": 45,
      "corners": 128,
      "symmetry_score": 0.72,
      "complexity_score": 1.35,
      "roundness": 0.68
    },
    
    "quality": {
      "overall_score": 0.85,
      "sharpness": 0.92,
      "blur_score": 0.08,
      "noise_level": 0.15,
      "brightness": 0.72,
      "contrast": 0.85,
      "exposure": "normal",
      "artifacts": ["compression"]
    },
    
    "detected_objects": [
      {
        "class": "person",
        "confidence": 0.95,
        "bounding_box": {
          "x": 120, "y": 180,
          "width": 200, "height": 300
        }
      }
    ],
    "object_count": 3,
    
    "analyzed_at": "2024-01-15T10:30:00Z",
    "analysis_version": "1.0",
    "processing_time_ms": 250.0
  }
}
```

### 3. Similarity Statistics

**Endpoint**: `GET /search/image-similarity/stats`

Retrieves comprehensive statistics about the image similarity search system.

#### Response

```json
{
  "total_searches": 1250,
  "total_comparisons": 1250000,
  "total_matches_found": 31250,
  "unique_assets_searched": 625,
  
  "avg_search_time_ms": 125.5,
  "avg_feature_extraction_time_ms": 180.2,
  "cache_hit_rate": 0.65,
  
  "images_analyzed": 3750,
  "total_features_extracted": 12500,
  "total_hashes_computed": 6250,
  
  "feature_model_usage": {
    "resnet50": 625,
    "vgg16": 250,
    "clip": 200,
    "efficientnet": 175
  },
  
  "similarity_metric_usage": {
    "cosine_similarity": 800,
    "euclidean_distance": 250,
    "manhattan_distance": 200
  },
  
  "hash_type_usage": {
    "perceptual_hash": 500,
    "average_hash": 300,
    "difference_hash": 200
  },
  
  "search_type_distribution": {
    "visual_similarity": 600,
    "duplicate_detection": 300,
    "content_similarity": 200,
    "style_similarity": 150
  },
  
  "similarity_score_distribution": {
    "0.9-1.0": 125,
    "0.8-0.9": 375,
    "0.7-0.8": 500,
    "0.6-0.7": 250
  },
  
  "avg_image_quality": 0.78,
  "quality_distribution": {
    "excellent": 250,
    "good": 850,
    "fair": 350,
    "poor": 50
  },
  
  "feature_extraction_failures": 25,
  "search_failures": 10,
  "low_quality_images": 75
}
```

## Use Cases and Examples

### 1. Content Discovery

Find visually similar images in a large media collection:

```python
# Search for images similar to a reference asset
search_request = {
    "reference_asset_id": "hero_image_001",
    "similarity_type": "visual_similarity",
    "feature_model": "resnet50",
    "similarity_threshold": 0.75,
    "asset_types": ["image"],
    "limit": 50
}

response = await client.post("/search/image-similarity", json=search_request)
similar_images = response.json()["matches"]
```

### 2. Duplicate Detection

Identify and manage duplicate images:

```python
# Detect duplicates using perceptual hashing
duplicate_search = {
    "reference_asset_id": "original_photo",
    "similarity_type": "duplicate_detection",
    "similarity_metric": "hamming_distance",
    "similarity_threshold": 0.95,
    "include_duplicates": True,
    "exclude_low_quality": True
}

response = await client.post("/search/image-similarity", json=duplicate_search)
duplicates = response.json()["matches"]
```

### 3. Style-Based Search

Find images with similar artistic style:

```python
# Search for images with similar artistic style
style_search = {
    "reference_image_url": "https://example.com/reference_art.jpg",
    "similarity_type": "style_similarity",
    "feature_model": "vgg19",
    "similarity_threshold": 0.7,
    "file_formats": ["jpg", "png"],
    "min_quality_score": 0.8
}

response = await client.post("/search/image-similarity", json=style_search)
style_matches = response.json()["matches"]
```

### 4. Color-Based Matching

Find images with similar color palettes:

```python
# Search by color similarity
color_search = {
    "reference_asset_id": "brand_image",
    "similarity_type": "color_similarity",
    "feature_model": "efficientnet",
    "similarity_threshold": 0.8,
    "include_thumbnails": True
}

response = await client.post("/search/image-similarity", json=color_search)
color_matches = response.json()["matches"]
```

### 5. Semantic Search

Find conceptually similar images:

```python
# Semantic similarity using CLIP
semantic_search = {
    "reference_asset_id": "concept_image",
    "similarity_type": "semantic_similarity",
    "feature_model": "clip",
    "similarity_threshold": 0.65,
    "include_analysis": True
}

response = await client.post("/search/image-similarity", json=semantic_search)
semantic_matches = response.json()["matches"]
```

### 6. Comprehensive Image Analysis

Extract detailed features from an image:

```python
# Comprehensive image analysis
analysis_request = {
    "asset_id": "analyze_me",
    "feature_models": ["resnet50", "clip", "efficientnet"],
    "extract_hashes": True,
    "hash_types": ["perceptual_hash", "average_hash"],
    "analyze_color": True,
    "analyze_texture": True,
    "assess_quality": True,
    "detect_objects": True,
    "parallel_processing": True
}

response = await client.post("/search/image-similarity/analyze", json=analysis_request)
analysis = response.json()["analysis"]
```

## Performance Optimization

### 1. Model Selection

Choose the appropriate model based on your use case:

- **General Purpose**: ResNet50 or EfficientNet
- **Semantic Search**: CLIP
- **Fast Duplicate Detection**: Perceptual Hash + MobileNet
- **High Accuracy**: Combination of ResNet50 + CLIP
- **Mobile/Edge**: MobileNet
- **Artistic Content**: VGG19 or ViT

### 2. Caching Strategy

The system implements intelligent caching:

- **Feature Cache**: Extracted features are cached for 24 hours
- **Search Cache**: Recent search results cached for 1 hour
- **Hash Cache**: Perceptual hashes cached indefinitely
- **Analysis Cache**: Full analysis results cached for 7 days

### 3. Performance Tips

#### For Large Collections:
- Use perceptual hashes for initial filtering
- Combine multiple similarity metrics
- Implement progressive refinement
- Use appropriate similarity thresholds

#### For Real-Time Applications:
- Use MobileNet or EfficientNet models
- Enable GPU acceleration when available
- Implement result caching
- Use perceptual hashes for duplicate detection

#### For High Accuracy:
- Use multiple feature models
- Combine different similarity types
- Enable multi-scale analysis
- Use higher-dimensional feature models

## Quality Assessment

### Image Quality Metrics

The system provides comprehensive quality assessment:

#### Overall Quality Score (0-1)
- Composite score based on multiple factors
- Weighted combination of individual metrics
- Suitable for filtering and ranking

#### Individual Metrics:
- **Sharpness**: Focus quality and edge clarity
- **Blur**: Motion blur and focus blur detection
- **Noise**: Digital noise and artifacts
- **Brightness**: Exposure and luminance levels
- **Contrast**: Dynamic range and contrast ratio
- **Artifacts**: Compression and processing artifacts

### Quality-Based Filtering

```python
# Filter by quality
quality_search = {
    "reference_asset_id": "high_quality_ref",
    "similarity_type": "visual_similarity",
    "min_quality_score": 0.8,
    "exclude_low_quality": True
}
```

## Privacy and Security

### Data Protection
- All processed images remain on your infrastructure
- Feature vectors are anonymized numerical representations
- No image data is transmitted to external services
- Comprehensive audit logging for all operations

### Compliance Features
- GDPR-compliant data handling
- Configurable data retention policies
- Secure deletion of analysis data
- Access control and audit trails

## Integration Examples

### 1. React Component

```jsx
import { useState } from 'react';

function ImageSimilaritySearch({ referenceAssetId }) {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const searchSimilar = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/search/image-similarity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reference_asset_id: referenceAssetId,
          similarity_type: 'visual_similarity',
          feature_model: 'resnet50',
          similarity_threshold: 0.8,
          limit: 20
        })
      });
      
      const data = await response.json();
      setResults(data.matches);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button onClick={searchSimilar} disabled={loading}>
        {loading ? 'Searching...' : 'Find Similar Images'}
      </button>
      
      <div className="results-grid">
        {results.map(match => (
          <div key={match.asset_id} className="result-item">
            <img src={match.thumbnail_url} alt={match.asset_name} />
            <p>Similarity: {(match.similarity_score * 100).toFixed(1)}%</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 2. Python Client

```python
import aiohttp
import asyncio

class ImageSimilarityClient:
    def __init__(self, base_url):
        self.base_url = base_url
    
    async def search_similar(self, reference_asset_id, **kwargs):
        """Search for similar images"""
        payload = {
            'reference_asset_id': reference_asset_id,
            'similarity_type': kwargs.get('similarity_type', 'visual_similarity'),
            'feature_model': kwargs.get('feature_model', 'resnet50'),
            'similarity_threshold': kwargs.get('similarity_threshold', 0.8),
            **kwargs
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.base_url}/search/image-similarity',
                json=payload
            ) as response:
                return await response.json()
    
    async def analyze_image(self, asset_id, **kwargs):
        """Analyze an image and extract features"""
        payload = {
            'asset_id': asset_id,
            'feature_models': kwargs.get('feature_models', ['resnet50']),
            'extract_hashes': kwargs.get('extract_hashes', True),
            'analyze_color': kwargs.get('analyze_color', True),
            'assess_quality': kwargs.get('assess_quality', True),
            **kwargs
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.base_url}/search/image-similarity/analyze',
                json=payload
            ) as response:
                return await response.json()

# Usage example
async def main():
    client = ImageSimilarityClient('http://localhost:8000')
    
    # Search for similar images
    results = await client.search_similar(
        reference_asset_id='photo_001',
        similarity_type='visual_similarity',
        limit=10
    )
    
    print(f"Found {results['total']} similar images")
    for match in results['matches']:
        print(f"- {match['asset_name']}: {match['similarity_score']:.2f}")

if __name__ == '__main__':
    asyncio.run(main())
```

### 3. Batch Processing

```python
async def process_image_collection(asset_ids):
    """Process a collection of images for similarity analysis"""
    client = ImageSimilarityClient('http://localhost:8000')
    
    # Extract features for all images
    analyses = []
    for asset_id in asset_ids:
        analysis = await client.analyze_image(
            asset_id=asset_id,
            feature_models=['resnet50', 'clip'],
            extract_hashes=True,
            analyze_color=True,
            assess_quality=True
        )
        analyses.append(analysis)
    
    # Find duplicates
    duplicates = []
    for i, asset_id in enumerate(asset_ids):
        similar = await client.search_similar(
            reference_asset_id=asset_id,
            similarity_type='duplicate_detection',
            similarity_threshold=0.95
        )
        if similar['total'] > 0:
            duplicates.append({
                'original': asset_id,
                'duplicates': similar['matches']
            })
    
    return analyses, duplicates
```

## Troubleshooting

### Common Issues

#### 1. Low Similarity Scores
- **Cause**: Threshold too high, different image types
- **Solution**: Lower threshold, use appropriate model for content type
- **Check**: Image quality, feature model selection

#### 2. Slow Performance
- **Cause**: Large feature vectors, complex models
- **Solution**: Use faster models (MobileNet, EfficientNet), enable GPU
- **Check**: Model selection, hardware acceleration

#### 3. Memory Issues
- **Cause**: Large images, batch processing
- **Solution**: Enable image resizing, reduce batch size
- **Check**: Image dimensions, memory usage

#### 4. Poor Duplicate Detection
- **Cause**: Wrong hash algorithm, low threshold
- **Solution**: Use perceptual hash, adjust threshold
- **Check**: Hash type selection, similarity metric

### Performance Monitoring

```python
# Monitor search performance
async def monitor_search_performance():
    client = ImageSimilarityClient('http://localhost:8000')
    
    # Get system statistics
    stats = await client.get_stats()
    
    print(f"Average search time: {stats['avg_search_time_ms']}ms")
    print(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")
    print(f"Feature extraction failures: {stats['feature_extraction_failures']}")
    
    # Check if performance is degrading
    if stats['avg_search_time_ms'] > 500:
        print("WARNING: Search performance degraded")
    
    if stats['cache_hit_rate'] < 0.3:
        print("WARNING: Low cache hit rate")
```

## Best Practices

### 1. Model Selection
- Use ResNet50 for general-purpose similarity
- Use CLIP for semantic/conceptual similarity
- Use perceptual hashes for fast duplicate detection
- Combine multiple models for comprehensive analysis

### 2. Threshold Setting
- Start with 0.8 for visual similarity
- Use 0.95+ for duplicate detection
- Lower to 0.6-0.7 for semantic similarity
- Adjust based on content type and requirements

### 3. Performance Optimization
- Enable GPU acceleration for large-scale processing
- Use appropriate image resizing for analysis
- Implement intelligent caching strategies
- Monitor and optimize based on usage patterns

### 4. Quality Control
- Enable quality assessment for better results
- Filter out low-quality images when appropriate
- Use multiple feature models for critical applications
- Implement feedback loops for continuous improvement

### 5. Security and Privacy
- Implement proper access controls
- Monitor for unusual usage patterns
- Comply with data protection regulations
- Maintain comprehensive audit logs

## Future Enhancements

### Planned Features
- Video similarity search
- 3D model similarity
- Audio-visual cross-modal search
- Real-time similarity indexing
- Advanced clustering algorithms
- Custom model training support

### Research Areas
- Few-shot similarity learning
- Adversarial robustness
- Cross-domain similarity
- Temporal similarity in video
- Multi-modal fusion techniques
- Explainable similarity metrics

The Image Similarity Search system provides a comprehensive foundation for visual content discovery and management, with extensive customization options and enterprise-grade performance characteristics.
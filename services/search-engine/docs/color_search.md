# Color Search

The Color Search feature provides comprehensive color-based search capabilities for image and video assets, enabling users to find media content based on color properties, palettes, temperature, and visual characteristics. This is essential for creative workflows, brand consistency, and visual content discovery.

## Overview

Color Search allows users to:
- Search for assets by dominant colors
- Find images with specific color palettes
- Filter by color temperature (warm/cool)
- Search within color ranges and spaces
- Find complementary, analogous, or triadic color schemes
- Filter by brightness, saturation, and hue ranges
- Analyze color composition and diversity

## Core Features

### Color Spaces Supported

1. **RGB** (Red, Green, Blue)
   - Standard additive color model
   - Values: 0-255 for each channel
   - Most common for digital images

2. **HSV** (Hue, Saturation, Value)
   - Intuitive color selection
   - Hue: 0-360 degrees
   - Saturation: 0-1 (0% to 100%)
   - Value: 0-1 (brightness)

3. **HSL** (Hue, Saturation, Lightness)
   - Similar to HSV but with lightness
   - Hue: 0-360 degrees
   - Saturation: 0-1 (0% to 100%)
   - Lightness: 0-1 (0% to 100%)

4. **LAB** (L*a*b*)
   - Perceptually uniform color space
   - L: 0-100 (lightness)
   - a: green-red axis
   - b: blue-yellow axis

5. **XYZ** (CIE XYZ)
   - CIE standard color space
   - Mathematical color representation
   - Device-independent

6. **YUV** (Luminance, Chrominance)
   - Video encoding standard
   - Y: luminance (brightness)
   - U, V: chrominance (color)

7. **CMYK** (Cyan, Magenta, Yellow, Key)
   - Subtractive color model
   - Used in printing
   - K: black (key)

8. **HEX** (Hexadecimal)
   - Web-standard color notation
   - Format: #RRGGBB or #RGB
   - Easy for developers

### Search Types

#### 1. Dominant Color Search
Search for assets where a specific color is dominant:
```json
{
  "search_type": "dominant_color",
  "target_color": {
    "r": 255,
    "g": 140,
    "b": 0
  },
  "color_space": "rgb",
  "tolerance": 15.0,
  "min_color_percentage": 20.0
}
```

#### 2. Color Palette Search
Find assets with similar color palettes:
```json
{
  "search_type": "color_palette",
  "color_palette": {
    "colors": [
      {"r": 255, "g": 0, "b": 0, "percentage": 40.0},
      {"r": 0, "g": 255, "b": 0, "percentage": 35.0},
      {"r": 0, "g": 0, "b": 255, "percentage": 25.0}
    ],
    "palette_type": "primary",
    "confidence": 0.85
  },
  "tolerance": 20.0
}
```

#### 3. Similar Colors Search
Find colors similar to a target color:
```json
{
  "search_type": "similar_colors",
  "target_color": {
    "r": 120,
    "g": 80,
    "b": 200
  },
  "match_type": "euclidean",
  "tolerance": 25.0
}
```

#### 4. Color Range Search
Search within specific color ranges:
```json
{
  "search_type": "color_range",
  "color_range": {
    "min_color": {"r": 100, "g": 50, "b": 150},
    "max_color": {"r": 200, "g": 150, "b": 250},
    "color_space": "rgb",
    "tolerance": 15.0
  }
}
```

#### 5. Color Harmony Searches

**Complementary Colors:**
```json
{
  "search_type": "complementary_colors",
  "color_space": "hsv",
  "tolerance": 20.0
}
```

**Analogous Colors:**
```json
{
  "search_type": "analogous_colors",
  "color_space": "hsv",
  "tolerance": 15.0
}
```

**Triadic Colors:**
```json
{
  "search_type": "triadic_colors",
  "color_space": "hsv",
  "tolerance": 20.0
}
```

#### 6. Temperature-Based Searches

**Warm Colors:**
```json
{
  "search_type": "warm_colors",
  "color_space": "rgb",
  "tolerance": 10.0,
  "min_color_percentage": 30.0
}
```

**Cool Colors:**
```json
{
  "search_type": "cool_colors",
  "color_space": "rgb",
  "tolerance": 10.0,
  "min_color_percentage": 30.0
}
```

#### 7. Monochromatic Search
Find images with limited color diversity:
```json
{
  "search_type": "monochromatic",
  "color_space": "rgb",
  "tolerance": 10.0,
  "sort_by": "color_diversity",
  "sort_order": "asc"
}
```

#### 8. Range-Based Searches

**Brightness Range:**
```json
{
  "search_type": "brightness_range",
  "min_brightness": 0.6,
  "max_brightness": 0.9,
  "asset_types": ["image"]
}
```

**Saturation Range:**
```json
{
  "search_type": "saturation_range",
  "min_saturation": 0.7,
  "max_saturation": 1.0,
  "asset_types": ["image"]
}
```

**Hue Range:**
```json
{
  "search_type": "hue_range",
  "min_hue": 0.0,
  "max_hue": 60.0,
  "asset_types": ["image"]
}
```

### Color Matching Algorithms

#### 1. Exact Match
Perfect color match with no tolerance:
```json
{
  "match_type": "exact",
  "tolerance": 0.0
}
```

#### 2. Euclidean Distance
Distance in RGB color space:
```json
{
  "match_type": "euclidean",
  "tolerance": 15.0
}
```

#### 3. Manhattan Distance
City-block distance in color space:
```json
{
  "match_type": "manhattan",
  "tolerance": 20.0
}
```

#### 4. Cosine Similarity
Angle-based similarity measure:
```json
{
  "match_type": "cosine",
  "tolerance": 0.1
}
```

#### 5. Delta E (CIE76)
Perceptual color difference:
```json
{
  "match_type": "delta_e",
  "tolerance": 5.0
}
```

#### 6. Perceptual Distance
Human-perceived color difference:
```json
{
  "match_type": "perceptual",
  "tolerance": 10.0
}
```

#### 7. Weighted Distance
Custom weighted color comparison:
```json
{
  "match_type": "weighted",
  "tolerance": 12.0
}
```

### Color Clustering Methods

#### 1. K-means Clustering
Standard k-means algorithm:
```json
{
  "clustering_method": "kmeans",
  "num_clusters": 5
}
```

#### 2. DBSCAN
Density-based clustering:
```json
{
  "clustering_method": "dbscan",
  "num_clusters": 8
}
```

#### 3. Hierarchical Clustering
Tree-based clustering:
```json
{
  "clustering_method": "hierarchical",
  "num_clusters": 6
}
```

#### 4. Mean Shift
Automatic cluster detection:
```json
{
  "clustering_method": "meanshift",
  "num_clusters": 10
}
```

#### 5. Spectral Clustering
Graph-based clustering:
```json
{
  "clustering_method": "spectral",
  "num_clusters": 4
}
```

## API Endpoints

### Search by Color
```http
POST /search/color
Content-Type: application/json

{
  "search_type": "dominant_color",
  "target_color": {
    "r": 255,
    "g": 140,
    "b": 0
  },
  "color_space": "rgb",
  "match_type": "euclidean",
  "tolerance": 15.0,
  "min_color_percentage": 20.0,
  "asset_types": ["image", "video"],
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
      "asset_name": "Sunset Landscape",
      "asset_type": "image",
      "dominant_colors": [
        {
          "r": 255,
          "g": 165,
          "b": 0,
          "percentage": 45.2,
          "frequency": 0.452,
          "name": "Orange"
        },
        {
          "r": 255,
          "g": 69,
          "b": 0,
          "percentage": 32.1,
          "frequency": 0.321,
          "name": "Red Orange"
        },
        {
          "r": 135,
          "g": 206,
          "b": 235,
          "percentage": 22.7,
          "frequency": 0.227,
          "name": "Sky Blue"
        }
      ],
      "color_palette": {
        "colors": [
          {
            "r": 255,
            "g": 165,
            "b": 0,
            "percentage": 45.2,
            "frequency": 0.452
          },
          {
            "r": 255,
            "g": 69,
            "b": 0,
            "percentage": 32.1,
            "frequency": 0.321
          },
          {
            "r": 135,
            "g": 206,
            "b": 235,
            "percentage": 22.7,
            "frequency": 0.227
          }
        ],
        "palette_type": "sunset",
        "extraction_method": "kmeans",
        "confidence": 0.92
      },
      "matched_colors": [
        {
          "r": 255,
          "g": 165,
          "b": 0,
          "percentage": 45.2,
          "frequency": 0.452
        }
      ],
      "match_score": 1.8,
      "match_type": "color_similarity",
      "color_similarity": 0.92,
      "color_diversity": 0.78,
      "dominant_color_percentage": 45.2,
      "color_temperature": 3500.0,
      "brightness": 0.72,
      "contrast": 0.84,
      "saturation": 0.89,
      "file_size": 2456789,
      "dimensions": {
        "width": 1920,
        "height": 1080
      },
      "format": "jpg",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "analyzed_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 85,
  "took": 125,
  "page": 1,
  "limit": 20,
  "pages": 5,
  "aggregations": {
    "color_distribution": {
      "buckets": [
        {"key": "warm", "doc_count": 45},
        {"key": "cool", "doc_count": 25},
        {"key": "neutral", "doc_count": 15}
      ]
    },
    "brightness_distribution": {
      "buckets": [
        {"key": 0.7, "doc_count": 35},
        {"key": 0.8, "doc_count": 30},
        {"key": 0.6, "doc_count": 20}
      ]
    }
  },
  "color_distribution": {
    "warm_colors": 45,
    "cool_colors": 25,
    "neutral_colors": 15
  },
  "palette_analysis": {
    "most_common_palette": "sunset",
    "palette_diversity": 0.68,
    "color_harmony_score": 0.85
  },
  "search_metadata": {
    "search_type": "dominant_color",
    "execution_time": 0.125,
    "color_space": "rgb",
    "match_type": "euclidean"
  }
}
```

### Analyze Asset Colors
```http
POST /search/color/analyze
Content-Type: application/json

{
  "asset_id": "asset-123",
  "color_space": "rgb",
  "clustering_method": "kmeans",
  "num_colors": 5,
  "frame_interval": 30,
  "sample_frames": 10,
  "include_histogram": true,
  "include_statistics": true,
  "force_reanalysis": false
}
```

Response:
```json
{
  "asset_id": "asset-123",
  "analysis_success": true,
  "dominant_colors": [
    {
      "r": 255,
      "g": 165,
      "b": 0,
      "percentage": 45.2,
      "frequency": 0.452,
      "hex": "#FFA500",
      "hsv": {"h": 38.8, "s": 1.0, "v": 1.0},
      "hsl": {"h": 38.8, "s": 1.0, "l": 0.5}
    },
    {
      "r": 255,
      "g": 69,
      "b": 0,
      "percentage": 32.1,
      "frequency": 0.321,
      "hex": "#FF4500",
      "hsv": {"h": 16.2, "s": 1.0, "v": 1.0},
      "hsl": {"h": 16.2, "s": 1.0, "l": 0.5}
    },
    {
      "r": 135,
      "g": 206,
      "b": 235,
      "percentage": 22.7,
      "frequency": 0.227,
      "hex": "#87CEEB",
      "hsv": {"h": 197.4, "s": 0.426, "v": 0.922},
      "hsl": {"h": 197.4, "s": 0.714, "l": 0.725}
    }
  ],
  "color_palette": {
    "colors": [
      {
        "r": 255,
        "g": 165,
        "b": 0,
        "percentage": 45.2,
        "frequency": 0.452
      },
      {
        "r": 255,
        "g": 69,
        "b": 0,
        "percentage": 32.1,
        "frequency": 0.321
      },
      {
        "r": 135,
        "g": 206,
        "b": 235,
        "percentage": 22.7,
        "frequency": 0.227
      }
    ],
    "palette_type": "sunset",
    "extraction_method": "kmeans",
    "confidence": 0.92
  },
  "color_histogram": {
    "bins": 256,
    "data": [12, 18, 25, 35, 42, 38, 28, 15, 8, 3],
    "channels": ["red", "green", "blue"]
  },
  "color_diversity": 0.78,
  "color_temperature": 3500.0,
  "brightness": 0.72,
  "contrast": 0.84,
  "saturation": 0.89,
  "processing_time_ms": 2500,
  "analysis_method": "K-means clustering (kmeans)",
  "color_space_used": "rgb",
  "errors": [],
  "warnings": [],
  "analyzed_at": "2024-01-15T10:30:00Z"
}
```

### Get Color Search Statistics
```http
GET /search/color/stats
```

Response:
```json
{
  "total_searches": 1500,
  "total_assets_analyzed": 3500,
  "most_common_colors": [
    {"color": "#FF8C00", "count": 1250, "percentage": 35.7},
    {"color": "#0064C8", "count": 980, "percentage": 28.0},
    {"color": "#50C878", "count": 875, "percentage": 25.0}
  ],
  "color_diversity_stats": {
    "min": 0.1,
    "max": 0.95,
    "avg": 0.68,
    "median": 0.72,
    "std_dev": 0.18
  },
  "dominant_color_distribution": {
    "warm": 1800,
    "cool": 1200,
    "neutral": 500
  },
  "avg_search_time_ms": 125.0,
  "avg_analysis_time_ms": 2500.0,
  "cache_hit_rate": 0.72,
  "images_analyzed": 2800,
  "videos_analyzed": 700,
  "frames_analyzed": 28000,
  "color_space_usage": {
    "rgb": 2800,
    "hsv": 450,
    "lab": 250,
    "hsl": 180,
    "cmyk": 120
  },
  "clustering_method_usage": {
    "kmeans": 2200,
    "dbscan": 800,
    "hierarchical": 500,
    "meanshift": 300,
    "spectral": 200
  }
}
```

## Advanced Features

### Color Temperature Analysis

Color temperature indicates whether colors are warm or cool:

#### Warm Colors (1000K - 3500K)
- Reds, oranges, yellows
- Sunset, candlelight, incandescent
- Cozy, intimate feeling

#### Neutral Colors (3500K - 5000K)
- Balanced color temperature
- Natural daylight
- Neutral, balanced feeling

#### Cool Colors (5000K - 10000K)
- Blues, greens, purples
- Overcast sky, fluorescent
- Cool, refreshing feeling

### Color Harmony Detection

#### Complementary Colors
Colors opposite on the color wheel:
- High contrast
- Vibrant combinations
- Red-Green, Blue-Orange

#### Analogous Colors
Adjacent colors on the color wheel:
- Harmonious combinations
- Low contrast
- Blue-Green-Cyan

#### Triadic Colors
Three equally spaced colors:
- Balanced combinations
- Moderate contrast
- Red-Yellow-Blue

#### Split-Complementary
Base color + two adjacent to complement:
- Softer than complementary
- Good contrast with harmony
- Red-Blue-Green-Yellow-Green

### Video Frame Analysis

For video assets, color analysis can be performed on:

#### Frame Sampling
```json
{
  "frame_interval": 30,
  "sample_frames": 20,
  "include_frames": true
}
```

#### Timeline Analysis
```json
{
  "color_timeline": [
    {
      "timestamp": 0.0,
      "dominant_color": {"r": 255, "g": 165, "b": 0}
    },
    {
      "timestamp": 30.0,
      "dominant_color": {"r": 255, "g": 69, "b": 0}
    },
    {
      "timestamp": 60.0,
      "dominant_color": {"r": 135, "g": 206, "b": 235}
    }
  ]
}
```

### Color Histogram Analysis

Detailed color distribution analysis:

#### RGB Histogram
```json
{
  "histogram": {
    "red": [0, 5, 12, 18, 25, 35, 42, 38, 28, 15, 8, 3, 0],
    "green": [0, 3, 8, 15, 22, 28, 35, 40, 32, 22, 12, 5, 0],
    "blue": [0, 2, 6, 12, 18, 25, 32, 38, 35, 28, 18, 8, 0]
  },
  "bins": 256,
  "normalized": true
}
```

#### HSV Histogram
```json
{
  "histogram": {
    "hue": [12, 18, 25, 35, 42, 38, 28, 15, 8, 3],
    "saturation": [5, 15, 25, 35, 45, 55, 65, 75, 85, 95],
    "value": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
  },
  "bins": 360,
  "normalized": true
}
```

### Advanced Filtering

#### Color Composition Filters
```json
{
  "min_color_percentage": 10.0,
  "max_color_percentage": 80.0,
  "color_diversity_range": {
    "min": 0.3,
    "max": 0.9
  }
}
```

#### Image Quality Filters
```json
{
  "min_brightness": 0.4,
  "max_brightness": 0.95,
  "min_contrast": 0.3,
  "max_contrast": 0.95,
  "min_saturation": 0.2,
  "max_saturation": 1.0
}
```

#### Technical Filters
```json
{
  "image_formats": ["jpg", "png", "tiff", "webp"],
  "video_formats": ["mp4", "mov", "avi", "mkv"],
  "min_resolution": "1920x1080",
  "max_file_size": 10000000
}
```

## Data Model

### Color Object Schema
```json
{
  "r": 255,
  "g": 165,
  "b": 0,
  "a": 255,
  "hex": "#FFA500",
  "hsv": {
    "h": 38.8,
    "s": 1.0,
    "v": 1.0
  },
  "hsl": {
    "h": 38.8,
    "s": 1.0,
    "l": 0.5
  },
  "lab": {
    "l": 74.9,
    "a": 23.9,
    "b": 78.9
  },
  "name": "Orange",
  "frequency": 0.452,
  "percentage": 45.2
}
```

### Color Palette Schema
```json
{
  "colors": [
    {
      "r": 255,
      "g": 165,
      "b": 0,
      "percentage": 45.2,
      "frequency": 0.452
    }
  ],
  "palette_type": "sunset",
  "extraction_method": "kmeans",
  "confidence": 0.92
}
```

### Asset Color Analysis Schema
```json
{
  "asset_id": "asset-123",
  "dominant_colors": [...],
  "color_palette": {...},
  "color_histogram": {...},
  "color_diversity": 0.78,
  "color_temperature": 3500.0,
  "brightness": 0.72,
  "contrast": 0.84,
  "saturation": 0.89,
  "frame_colors": [...],
  "color_timeline": [...],
  "analyzed_at": "2024-01-15T10:30:00Z"
}
```

### Search Index Mapping
```json
{
  "mappings": {
    "properties": {
      "color_analysis": {
        "type": "object",
        "properties": {
          "dominant_colors": {
            "type": "nested",
            "properties": {
              "r": {"type": "integer"},
              "g": {"type": "integer"},
              "b": {"type": "integer"},
              "percentage": {"type": "float"},
              "frequency": {"type": "float"}
            }
          },
          "palette": {
            "type": "nested",
            "properties": {
              "r": {"type": "integer"},
              "g": {"type": "integer"},
              "b": {"type": "integer"},
              "percentage": {"type": "float"}
            }
          },
          "color_diversity": {"type": "float"},
          "color_temperature": {"type": "float"},
          "brightness": {"type": "float"},
          "contrast": {"type": "float"},
          "saturation": {"type": "float"},
          "hue": {"type": "float"}
        }
      }
    }
  }
}
```

## Use Cases

### 1. Brand Asset Management
- **Brand Color Consistency**: Find assets matching brand colors
- **Logo Variations**: Search for assets with specific color schemes
- **Campaign Materials**: Locate assets with consistent color palettes
- **Color Guidelines**: Ensure brand color compliance

### 2. Creative Workflows
- **Mood Boards**: Create collections based on color themes
- **Color Grading**: Find assets with similar color characteristics
- **Seasonal Content**: Search for warm/cool color temperatures
- **Artistic Direction**: Match color palettes across projects

### 3. Content Discovery
- **Visual Similarity**: Find visually similar content
- **Color Themes**: Discover content by color characteristics
- **Seasonal Searches**: Find content matching seasonal colors
- **Mood-Based Discovery**: Search by emotional color associations

### 4. Technical Applications
- **Color Correction**: Identify assets needing color adjustment
- **Quality Control**: Find assets with color issues
- **Batch Processing**: Group assets by color characteristics
- **Metadata Enhancement**: Automatically tag assets with color information

### 5. E-commerce Applications
- **Product Matching**: Find products with similar colors
- **Style Coordination**: Match colors across product lines
- **Trend Analysis**: Identify popular color combinations
- **Inventory Management**: Organize products by color attributes

## Performance Considerations

### Indexing Strategy
1. **Color Quantization**: Reduce color space for efficient indexing
2. **Palette Indexing**: Store dominant colors separately
3. **Histogram Compression**: Compress color histograms for storage
4. **Multi-Scale Analysis**: Index colors at multiple resolutions

### Query Optimization
1. **Color Space Conversion**: Pre-convert colors to search space
2. **Approximation Algorithms**: Use approximate nearest neighbor search
3. **Clustering**: Group similar colors for faster searches
4. **Caching**: Cache color analysis results

### Scaling Considerations
1. **Distributed Processing**: Process color analysis in parallel
2. **GPU Acceleration**: Use GPU for color calculations
3. **Incremental Updates**: Update color analysis incrementally
4. **Load Balancing**: Distribute color searches across nodes

## Integration Examples

### React Component
```jsx
import React, { useState } from 'react';
import { ColorPicker } from './ColorPicker';
import { searchByColor } from './api';

const ColorSearchComponent = () => {
  const [selectedColor, setSelectedColor] = useState({ r: 255, g: 0, b: 0 });
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    try {
      const response = await searchByColor({
        search_type: 'dominant_color',
        target_color: selectedColor,
        color_space: 'rgb',
        match_type: 'euclidean',
        tolerance: 15.0,
        asset_types: ['image'],
        page: 1,
        limit: 20
      });
      setResults(response.results);
    } catch (error) {
      console.error('Color search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="color-search">
      <ColorPicker
        color={selectedColor}
        onChange={setSelectedColor}
      />
      <button onClick={handleSearch} disabled={loading}>
        {loading ? 'Searching...' : 'Search by Color'}
      </button>
      <div className="results">
        {results.map(result => (
          <div key={result.asset_id} className="result-item">
            <img src={result.thumbnail_url} alt={result.asset_name} />
            <div className="color-info">
              <h4>{result.asset_name}</h4>
              <p>Match Score: {result.match_score}</p>
              <p>Color Similarity: {result.color_similarity}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ColorSearchComponent;
```

### Python Integration
```python
import requests
from typing import Dict, List, Optional

class ColorSearchClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def search_by_color(self, 
                       target_color: Dict[str, int],
                       search_type: str = 'dominant_color',
                       tolerance: float = 15.0,
                       asset_types: Optional[List[str]] = None) -> Dict:
        """Search for assets by color"""
        payload = {
            'search_type': search_type,
            'target_color': target_color,
            'color_space': 'rgb',
            'match_type': 'euclidean',
            'tolerance': tolerance,
            'asset_types': asset_types or ['image', 'video'],
            'page': 1,
            'limit': 20
        }
        
        response = requests.post(
            f'{self.base_url}/search/color',
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def analyze_colors(self, asset_id: str, 
                      num_colors: int = 5,
                      include_histogram: bool = True) -> Dict:
        """Analyze colors in an asset"""
        payload = {
            'asset_id': asset_id,
            'color_space': 'rgb',
            'clustering_method': 'kmeans',
            'num_colors': num_colors,
            'include_histogram': include_histogram,
            'include_statistics': True
        }
        
        response = requests.post(
            f'{self.base_url}/search/color/analyze',
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# Usage example
client = ColorSearchClient('https://api.mams.com', 'your-api-key')

# Search for orange images
results = client.search_by_color(
    target_color={'r': 255, 'g': 165, 'b': 0},
    search_type='dominant_color',
    tolerance=20.0,
    asset_types=['image']
)

# Analyze colors in a specific asset
analysis = client.analyze_colors(
    asset_id='asset-123',
    num_colors=8,
    include_histogram=True
)
```

### Adobe Photoshop Plugin
```javascript
// Photoshop CEP Panel
const ColorSearchPanel = {
    searchByColor: async function(color) {
        const response = await fetch('/search/color', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                search_type: 'dominant_color',
                target_color: {
                    r: color.red,
                    g: color.green,
                    b: color.blue
                },
                color_space: 'rgb',
                match_type: 'euclidean',
                tolerance: 15.0,
                asset_types: ['image']
            })
        });
        
        const data = await response.json();
        this.displayResults(data.results);
    },
    
    displayResults: function(results) {
        const container = document.getElementById('results');
        container.innerHTML = '';
        
        results.forEach(result => {
            const item = document.createElement('div');
            item.className = 'result-item';
            item.innerHTML = `
                <img src="${result.thumbnail_url}" alt="${result.asset_name}">
                <div class="info">
                    <h4>${result.asset_name}</h4>
                    <p>Similarity: ${(result.color_similarity * 100).toFixed(1)}%</p>
                    <div class="colors">
                        ${result.dominant_colors.map(color => 
                            `<div class="color-chip" style="background-color: rgb(${color.r}, ${color.g}, ${color.b})"></div>`
                        ).join('')}
                    </div>
                </div>
            `;
            container.appendChild(item);
        });
    }
};
```

## Error Handling

### Common Errors

1. **Invalid Color Values**
```json
{
  "error": {
    "code": "INVALID_COLOR_VALUE",
    "message": "Color values must be between 0 and 255",
    "details": {
      "field": "target_color.r",
      "value": 300,
      "valid_range": "0-255"
    }
  }
}
```

2. **Invalid Color Space**
```json
{
  "error": {
    "code": "INVALID_COLOR_SPACE",
    "message": "Unsupported color space",
    "details": {
      "provided": "invalid_space",
      "supported": ["rgb", "hsv", "hsl", "lab", "xyz", "yuv", "cmyk", "hex"]
    }
  }
}
```

3. **Color Analysis Failed**
```json
{
  "error": {
    "code": "COLOR_ANALYSIS_FAILED",
    "message": "Could not analyze colors in asset",
    "details": {
      "asset_id": "asset-123",
      "reason": "Unsupported file format"
    }
  }
}
```

4. **Too Many Colors**
```json
{
  "error": {
    "code": "TOO_MANY_COLORS",
    "message": "Color palette cannot have more than 20 colors",
    "details": {
      "provided": 25,
      "maximum": 20
    }
  }
}
```

## Best Practices

### Color Search Optimization
1. **Choose Appropriate Tolerance**: Balance between precision and recall
2. **Use Relevant Color Spaces**: HSV for intuitive searches, LAB for perceptual accuracy
3. **Combine Multiple Criteria**: Use color with brightness, saturation filters
4. **Cache Results**: Cache frequent color searches for better performance

### Color Analysis
1. **Consistent Methodology**: Use same clustering method for comparable results
2. **Appropriate Cluster Count**: Balance between detail and simplicity
3. **Quality Preprocessing**: Ensure good image quality for accurate analysis
4. **Metadata Integration**: Combine color data with other metadata

### Performance Optimization
1. **Batch Processing**: Process multiple assets together
2. **Incremental Updates**: Update color analysis incrementally
3. **Efficient Indexing**: Use optimized data structures for color searches
4. **Memory Management**: Monitor memory usage during color processing

### User Experience
1. **Visual Feedback**: Show color swatches in search results
2. **Progressive Loading**: Load results progressively for better UX
3. **Search Refinement**: Allow users to refine searches iteratively
4. **Color Picker Integration**: Provide intuitive color selection tools

This comprehensive color search system provides powerful capabilities for color-based media discovery and analysis, enabling creative professionals, brand managers, and content creators to find and organize visual content based on sophisticated color criteria.
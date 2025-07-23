# Search Result Ranking Documentation

## Overview

The Search Result Ranking feature provides flexible algorithms to rank search results based on various factors beyond just text relevance. This enables users to find the most useful content based on recency, popularity, quality indicators, and custom criteria.

## Ranking Types

### 1. Relevance Ranking (Default)
Uses the native OpenSearch relevance scores based on text matching.

**Use when**: You want traditional search behavior where the best text matches appear first.

### 2. Recency Ranking
Ranks results based on how recently they were created or updated.

**Use when**: Fresh content is more valuable than older content (e.g., news, recent productions).

**Algorithm**: Exponential decay based on age, configurable decay rate.

### 3. Popularity Ranking
Ranks results based on engagement metrics like views, downloads, shares, and ratings.

**Use when**: You want to surface content that others have found valuable.

**Metrics considered**:
- View count
- Download count
- Share count
- Ratings (average × count)

### 4. Hybrid Ranking (Recommended)
Combines multiple factors with configurable weights.

**Use when**: You want a balanced approach considering multiple factors.

**Default weights**:
- Relevance: 1.0
- Recency: 0.3
- Popularity: 0.2
- Quality: 0.1

### 5. Custom Ranking
Allows fine-grained control over ranking factors.

**Use when**: You have specific business rules for ranking.

**Factors**:
- Field boosts (title, description, tags)
- Asset type preferences
- Quality indicators

## API Usage

### Basic Search with Ranking

```bash
curl -X POST http://localhost:8005/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "production video",
    "ranking_config": {
      "ranking_type": "hybrid"
    }
  }'
```

### Custom Ranking Configuration

```bash
curl -X POST http://localhost:8005/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "tutorial",
    "ranking_config": {
      "ranking_type": "hybrid",
      "hybrid_weights": {
        "relevance": 0.5,
        "recency": 0.3,
        "popularity": 0.2,
        "quality": 0.0
      },
      "recency_decay_days": 14
    }
  }'
```

### Recency-Focused Search

```bash
curl -X POST http://localhost:8005/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "news footage",
    "ranking_config": {
      "ranking_type": "recency",
      "recency_decay_days": 7
    }
  }'
```

### Popularity-Based Search

```bash
curl -X POST http://localhost:8005/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "training",
    "ranking_config": {
      "ranking_type": "popularity",
      "popularity_weights": {
        "views": 1.0,
        "downloads": 3.0,
        "shares": 2.0,
        "ratings": 2.0
      }
    }
  }'
```

### Custom Field Boosting

```bash
curl -X POST http://localhost:8005/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "corporate video",
    "ranking_config": {
      "ranking_type": "custom",
      "field_boosts": {
        "title": 5.0,
        "description": 1.0,
        "tags": 3.0
      },
      "asset_type_boosts": {
        "video": 2.0,
        "image": 1.0,
        "audio": 0.5,
        "document": 0.3
      }
    }
  }'
```

### Getting Ranking Explanations

```bash
curl -X POST http://localhost:8005/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test",
    "ranking_config": {
      "ranking_type": "hybrid"
    },
    "include_ranking_explanation": true
  }'
```

Response includes ranking details:
```json
{
  "hits": [
    {
      "id": "asset-123",
      "score": 2.5,
      "ranking_explanation": {
        "original_score": 2.5,
        "factors": {
          "relevance": 2.5,
          "recency": 0.95,
          "popularity": 0.32,
          "quality": 0.8,
          "final_score": 3.21
        }
      }
    }
  ]
}
```

## Configuration Parameters

### RankingConfig Schema

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| ranking_type | enum | Type of ranking algorithm | "hybrid" |
| hybrid_weights | object | Weights for hybrid ranking factors | See below |
| recency_decay_days | integer | Days for exponential decay | 30 |
| popularity_weights | object | Weights for popularity metrics | See below |
| custom_weights | object | Weights for custom components | See below |
| field_boosts | object | Boost scores for field matches | See below |
| asset_type_boosts | object | Preference scores by asset type | See below |

### Default Weights

#### Hybrid Weights
```json
{
  "relevance": 1.0,
  "recency": 0.3,
  "popularity": 0.2,
  "quality": 0.1
}
```

#### Popularity Weights
```json
{
  "views": 1.0,
  "downloads": 2.0,
  "shares": 3.0,
  "ratings": 1.5
}
```

#### Field Boosts
```json
{
  "title": 2.0,
  "description": 1.0,
  "tags": 1.5
}
```

#### Asset Type Boosts
```json
{
  "video": 1.0,
  "image": 0.9,
  "audio": 0.8,
  "document": 0.7
}
```

## Quality Indicators

The quality score considers:
- Presence of comprehensive metadata
- Availability of proxies/thumbnails
- Existence of transcriptions/captions
- File size (larger files often indicate higher quality)

## Best Practices

1. **Start with Hybrid**: The hybrid ranking provides a good balance for most use cases.

2. **Adjust Weights Gradually**: Small changes to weights can have significant effects.

3. **Consider Your Use Case**:
   - News/Current Events: Increase recency weight
   - Training/Reference: Increase popularity weight
   - Production Assets: Increase quality weight

4. **Use Explicit Sorting When Needed**: If you set `sort_by` in the query, ranking is bypassed for predictable ordering.

5. **Monitor Performance**: Complex ranking algorithms add processing time. Use simpler algorithms for large result sets.

6. **Combine with Filters**: Use filters to narrow results before ranking for better performance.

## Performance Considerations

- Ranking is applied after OpenSearch returns results
- Only affects the order, not which documents match
- Adds minimal overhead for small result sets (<1000 items)
- For large result sets, consider pagination before ranking

## Integration with Other Features

- **Metadata Field Search**: Ranking works with all search types
- **Filters**: Applied before ranking
- **Aggregations**: Calculated on all results, not affected by ranking
- **Highlighting**: Works normally with ranking

## Examples by Use Case

### Recent News Footage
```json
{
  "query": "breaking news",
  "ranking_config": {
    "ranking_type": "hybrid",
    "hybrid_weights": {
      "relevance": 0.5,
      "recency": 0.4,
      "popularity": 0.1,
      "quality": 0.0
    },
    "recency_decay_days": 3
  }
}
```

### Popular Training Materials
```json
{
  "query": "safety training",
  "ranking_config": {
    "ranking_type": "hybrid",
    "hybrid_weights": {
      "relevance": 0.4,
      "recency": 0.0,
      "popularity": 0.4,
      "quality": 0.2
    }
  }
}
```

### High-Quality Production Assets
```json
{
  "query": "4K footage",
  "ranking_config": {
    "ranking_type": "custom",
    "custom_weights": {
      "field_boost": 0.5,
      "asset_type": 0.2,
      "quality": 0.3
    },
    "asset_type_boosts": {
      "video": 2.0,
      "image": 0.5
    }
  }
}
```

## Troubleshooting

### Results seem randomly ordered
- Check if `sort_by` is set (overrides ranking)
- Verify ranking_config is properly formatted
- Enable ranking explanations to see scores

### Ranking is too slow
- Reduce result set size with filters
- Use simpler ranking algorithms
- Consider caching for repeated queries

### Unexpected ranking order
- Enable `include_ranking_explanation`
- Check factor weights and scores
- Verify data quality (missing dates, metrics)
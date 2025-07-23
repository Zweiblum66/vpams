# Search Suggestions Documentation

## Overview

The Search Suggestions feature provides intelligent auto-completion and query suggestions to help users find content quickly. It uses OpenSearch's completion suggester combined with phrase and term suggesters to provide relevant suggestions even with typos or partial queries.

## Features

### 1. Auto-completion
Real-time suggestions as users type, based on indexed asset names and popular searches.

### 2. Typo Correction
Automatic correction of common typos and misspellings using fuzzy matching.

### 3. Multi-word Suggestions
Intelligent phrase suggestions for multi-word queries.

### 4. Popularity-based Ranking
Suggestions are ranked by relevance and can incorporate popularity metrics.

### 5. Index-specific Suggestions
Get suggestions from specific indices (assets, projects, metadata) or across all indices.

## API Usage

### Basic Suggestions

```bash
curl -X GET "http://localhost:8005/api/v1/search/suggestions?text=vid&size=5"
```

Response:
```json
{
  "suggestions": [
    {
      "text": "video production",
      "score": 20.0
    },
    {
      "text": "video editing",
      "score": 16.0
    },
    {
      "text": "video tutorial",
      "score": 12.0
    }
  ],
  "took": 5
}
```

### Suggestions with Specific Index

```bash
curl -X GET "http://localhost:8005/api/v1/search/suggestions?text=proj&index_type=projects"
```

### Query Parameters

| Parameter | Type | Description | Default | Constraints |
|-----------|------|-------------|---------|-------------|
| text | string | Text to get suggestions for | Required | 1-100 characters |
| size | integer | Number of suggestions to return | 5 | 1-20 |
| index_type | string | Index to search | "assets" | assets, projects, metadata, all |

## Implementation Details

### Suggestion Types

1. **Completion Suggester**
   - Used for prefix-based suggestions
   - Provides fast auto-completion
   - Supports fuzzy matching for typos

2. **Phrase Suggester**
   - Activated for multi-word queries
   - Suggests complete phrases
   - Helps with word order and missing words

3. **Term Suggester**
   - Provides spelling corrections
   - Suggests popular alternatives
   - Based on term frequency in the index

### Scoring and Ranking

Suggestions are scored based on multiple factors:
- **Relevance**: How well the suggestion matches the input
- **Popularity**: Based on document frequency
- **Fuzziness**: Penalty for fuzzy matches
- **Boost**: Completion suggestions get 2x boost, phrase suggestions get 1.5x boost

### Index Mapping

The name field in asset documents is mapped with a completion subfield:

```json
{
  "name": {
    "type": "text",
    "analyzer": "asset_name_analyzer",
    "fields": {
      "keyword": {"type": "keyword"},
      "suggest": {"type": "completion"}
    }
  }
}
```

## Advanced Features

### Fuzzy Matching

The system automatically handles typos using fuzzy matching:
- Transpositions: "vdieo" → "video"
- Missing letters: "vido" → "video"
- Extra letters: "videoo" → "video"

Configuration:
- Fuzziness: AUTO (adapts based on term length)
- Min length: 3 (no fuzzy matching for very short terms)
- Transpositions: Enabled

### Popular Searches

Get trending search terms (requires analytics data):

```python
popular_terms = await suggestion_service.get_popular_searches(size=10)
```

### Updating Suggestion Data

When assets are modified, update their suggestion data:

```python
await suggestion_service.update_suggestion_data(
    asset_id="asset-123",
    name="Updated Asset Name"
)
```

## Integration with Search

Suggestions can be used to enhance the search experience:

1. **Search-as-you-type**: Show suggestions in real-time
2. **Did you mean?**: Offer corrections for queries with no results
3. **Popular searches**: Show trending topics
4. **Query expansion**: Use suggestions to broaden searches

## Best Practices

### 1. Debouncing
Implement client-side debouncing (300-500ms) to avoid excessive API calls:

```javascript
let debounceTimer;
function getSuggestions(text) {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    fetchSuggestions(text);
  }, 300);
}
```

### 2. Minimum Query Length
Don't request suggestions for very short queries (< 2 characters) to reduce load and improve relevance.

### 3. Caching
Cache suggestion results client-side for repeated queries:

```javascript
const suggestionCache = new Map();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

async function getCachedSuggestions(text) {
  const cached = suggestionCache.get(text);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data;
  }
  
  const data = await fetchSuggestions(text);
  suggestionCache.set(text, { data, timestamp: Date.now() });
  return data;
}
```

### 4. Error Handling
Always handle suggestion errors gracefully:

```javascript
try {
  const suggestions = await getSuggestions(query);
  displaySuggestions(suggestions);
} catch (error) {
  console.error('Failed to get suggestions:', error);
  // Don't show error to user - just hide suggestions
  hideSuggestions();
}
```

## Performance Considerations

### Response Times
- Target: < 50ms for suggestion queries
- Actual: Typically 5-20ms for indexed content
- Scales well up to millions of documents

### Optimization Tips
1. Use appropriate suggestion size (5-10 is usually sufficient)
2. Index only necessary fields for suggestions
3. Regularly optimize indices for better performance
4. Consider using edge n-grams for very large datasets

## Examples

### React Component Example

```jsx
function SearchWithSuggestions() {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  
  const fetchSuggestions = useCallback(
    debounce(async (text) => {
      if (text.length < 2) {
        setSuggestions([]);
        return;
      }
      
      setLoading(true);
      try {
        const response = await fetch(
          `/api/v1/search/suggestions?text=${encodeURIComponent(text)}&size=8`
        );
        const data = await response.json();
        setSuggestions(data.suggestions);
      } catch (error) {
        console.error('Suggestion error:', error);
        setSuggestions([]);
      } finally {
        setLoading(false);
      }
    }, 300),
    []
  );
  
  useEffect(() => {
    fetchSuggestions(query);
  }, [query, fetchSuggestions]);
  
  return (
    <div className="search-container">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search for assets..."
      />
      {loading && <div className="spinner">Loading...</div>}
      {suggestions.length > 0 && (
        <ul className="suggestions">
          {suggestions.map((suggestion, index) => (
            <li
              key={index}
              onClick={() => {
                setQuery(suggestion.text);
                performSearch(suggestion.text);
              }}
            >
              {suggestion.text}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

### Python Integration Example

```python
from typing import List
import httpx

class SearchClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def get_suggestions(self, text: str, size: int = 5) -> List[str]:
        """Get search suggestions for the given text"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/search/suggestions",
                params={"text": text, "size": size}
            )
            response.raise_for_status()
            data = response.json()
            return [s["text"] for s in data["suggestions"]]
        except Exception as e:
            print(f"Failed to get suggestions: {e}")
            return []
    
    async def search_with_suggestions(self, query: str):
        """Search with fallback to suggestions if no results"""
        # First try exact search
        results = await self.search(query)
        
        if not results:
            # Get suggestions for alternative queries
            suggestions = await self.get_suggestions(query)
            if suggestions:
                print(f"No results for '{query}'. Did you mean: {suggestions[0]}?")
                # Optionally retry with suggestion
                results = await self.search(suggestions[0])
        
        return results
```

## Troubleshooting

### No Suggestions Returned
1. Check if documents are properly indexed with name field
2. Verify index mappings include completion field
3. Ensure minimum query length (usually 1 character)
4. Check if index has been refreshed after indexing

### Slow Suggestion Response
1. Check OpenSearch cluster health
2. Verify index is optimized
3. Reduce suggestion size parameter
4. Consider caching frequently requested suggestions

### Irrelevant Suggestions
1. Adjust fuzzy matching parameters
2. Implement custom scoring based on popularity
3. Filter suggestions by asset type or metadata
4. Use more specific analyzers for your content

## Future Enhancements

1. **Machine Learning Integration**
   - Learn from user selections
   - Personalized suggestions
   - Context-aware recommendations

2. **Multi-language Support**
   - Language-specific analyzers
   - Cross-language suggestions
   - Transliteration support

3. **Advanced Analytics**
   - Track suggestion usage
   - A/B testing different algorithms
   - Performance metrics dashboard

4. **Semantic Suggestions**
   - Synonym expansion
   - Concept-based suggestions
   - Related term recommendations
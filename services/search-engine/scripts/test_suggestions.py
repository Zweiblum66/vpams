#!/usr/bin/env python3
"""
Test script for search suggestions functionality
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.db.opensearch import get_opensearch_client, ensure_indices_exist
from src.services.indexing_service import IndexingService
from src.services.suggestion_service import SuggestionService
from src.models.schemas import IndexDocument, SuggestionQuery
import structlog

logger = structlog.get_logger()


async def test_suggestions():
    """Test search suggestions functionality"""
    try:
        # Get OpenSearch client
        client = await get_opensearch_client()
        print("✓ Connected to OpenSearch")
        
        # Ensure indices exist
        await ensure_indices_exist(client)
        print("✓ Indices verified")
        
        # Create services
        indexing_service = IndexingService(client)
        suggestion_service = SuggestionService(client)
        print("✓ Services initialized")
        
        # Index test documents with various names
        test_assets = [
            {
                "asset_id": "test-001",
                "name": "Corporate Training Video",
                "description": "Annual compliance training video for all employees",
                "asset_type": "video",
                "file_size": 524288000,
                "tags": ["training", "corporate", "compliance"]
            },
            {
                "asset_id": "test-002", 
                "name": "Corporate Holiday Party 2023",
                "description": "Video highlights from the company holiday party",
                "asset_type": "video",
                "file_size": 1073741824,
                "tags": ["corporate", "event", "party"]
            },
            {
                "asset_id": "test-003",
                "name": "Product Demo - Software Update",
                "description": "Demonstration of new software features",
                "asset_type": "video",
                "file_size": 268435456,
                "tags": ["demo", "product", "software"]
            },
            {
                "asset_id": "test-004",
                "name": "Video Editing Tutorial",
                "description": "Basic video editing techniques for beginners",
                "asset_type": "video",
                "file_size": 157286400,
                "tags": ["tutorial", "editing", "video"]
            },
            {
                "asset_id": "test-005",
                "name": "Marketing Campaign Video",
                "description": "Q4 2023 marketing campaign video",
                "asset_type": "video", 
                "file_size": 419430400,
                "tags": ["marketing", "campaign", "promotional"]
            }
        ]
        
        print("\nIndexing test documents...")
        for asset in test_assets:
            doc = IndexDocument(
                id=asset["asset_id"],
                document=asset,
                index_name="mams_assets"
            )
            result = await indexing_service.index_document(doc)
            print(f"  ✓ Indexed: {asset['name']}")
        
        # Refresh index for immediate search
        await client.indices.refresh(index="mams_assets")
        print("\n✓ Index refreshed")
        
        # Test various suggestion queries
        test_queries = [
            "corp",      # Should suggest "Corporate Training Video", "Corporate Holiday Party 2023"
            "video",     # Should suggest all video-related items
            "train",     # Should suggest "Corporate Training Video"
            "vido",      # Typo - should suggest "video" corrections
            "product",   # Should suggest "Product Demo - Software Update"
            "market",    # Should suggest "Marketing Campaign Video"
            "xyz",       # No matches expected
        ]
        
        print("\nTesting suggestions:")
        print("-" * 60)
        
        for query_text in test_queries:
            query = SuggestionQuery(text=query_text, size=5)
            response = await suggestion_service.get_suggestions(query)
            
            print(f"\nQuery: '{query_text}'")
            print(f"Time: {response.took}ms")
            
            if response.suggestions:
                print("Suggestions:")
                for i, suggestion in enumerate(response.suggestions, 1):
                    print(f"  {i}. {suggestion.text} (score: {suggestion.score:.2f})")
            else:
                print("  No suggestions found")
        
        # Test with different index types
        print("\n" + "=" * 60)
        print("Testing with projects index (should be empty):")
        query = SuggestionQuery(text="test", size=5, index_type="projects")
        response = await suggestion_service.get_suggestions(query)
        print(f"Suggestions found: {len(response.suggestions)}")
        
        # Test popular searches (will be empty without analytics data)
        print("\n" + "=" * 60)
        print("Testing popular searches:")
        popular = await suggestion_service.get_popular_searches(size=5)
        if popular:
            print("Popular searches:")
            for i, term in enumerate(popular, 1):
                print(f"  {i}. {term}")
        else:
            print("  No popular searches found (analytics data needed)")
        
        print("\n✅ Suggestion tests completed successfully!")
        
    except Exception as e:
        logger.error("test_error", error=str(e))
        print(f"\n❌ Error: {e}")
        raise
    finally:
        if 'client' in locals():
            await client.close()


if __name__ == "__main__":
    asyncio.run(test_suggestions())
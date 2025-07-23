#!/usr/bin/env python3
"""
Integration Test: Search Integration

Tests the search functionality across multiple services including
metadata indexing, full-text search, and AI-powered search features.
"""

import asyncio
import pytest
import httpx
import os
import tempfile
import json
from datetime import datetime, timedelta
import time
from PIL import Image
import io

# Service URLs
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")


class TestSearchIntegration:
    """Integration test for search functionality across services."""
    
    @pytest.fixture
    async def auth_headers(self):
        """Get authentication headers for test user."""
        async with httpx.AsyncClient() as client:
            timestamp = int(time.time())
            # Register
            await client.post(
                f"{API_GATEWAY_URL}/api/v1/auth/register",
                json={
                    "username": f"search_test_{timestamp}",
                    "email": f"search_{timestamp}@test.com",
                    "password": "Test123!@#",
                    "full_name": "Search Test User"
                }
            )
            
            # Login
            login_response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/auth/login",
                json={
                    "username": f"search_test_{timestamp}",
                    "password": "Test123!@#"
                }
            )
            
            token = login_response.json()["data"]["access_token"]
            return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    async def test_assets(self, auth_headers):
        """Create various test assets for search testing."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            assets = []
            
            # Create text asset
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("This is a document about artificial intelligence and machine learning.\n")
                f.write("It contains information about neural networks and deep learning.\n")
                text_path = f.name
            
            # Create image asset
            img = Image.new('RGB', (800, 600), color='blue')
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='JPEG')
            img_buffer.seek(0)
            
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                f.write(img_buffer.getvalue())
                image_path = f.name
            
            # Upload text document
            with open(text_path, 'rb') as f:
                files = {"file": ("ai_document.txt", f, "text/plain")}
                response = await client.post(
                    f"{API_GATEWAY_URL}/api/v1/assets/upload",
                    files=files,
                    data={
                        "name": "AI Research Document",
                        "description": "Document about artificial intelligence",
                        "tags": json.dumps(["ai", "machine-learning", "research"])
                    },
                    headers=auth_headers
                )
                assets.append(response.json()["data"])
            
            # Upload image
            with open(image_path, 'rb') as f:
                files = {"file": ("blue_image.jpg", f, "image/jpeg")}
                response = await client.post(
                    f"{API_GATEWAY_URL}/api/v1/assets/upload",
                    files=files,
                    data={
                        "name": "Blue Sky Image",
                        "description": "A beautiful blue sky photograph",
                        "tags": json.dumps(["blue", "sky", "nature"])
                    },
                    headers=auth_headers
                )
                assets.append(response.json()["data"])
            
            # Cleanup files
            os.unlink(text_path)
            os.unlink(image_path)
            
            yield assets
            
            # Cleanup assets
            for asset in assets:
                await client.delete(
                    f"{API_GATEWAY_URL}/api/v1/assets/{asset['id']}",
                    headers=auth_headers
                )
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_text_search(self, auth_headers, test_assets):
        """Test full-text search across asset content and metadata."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Wait for indexing
            await asyncio.sleep(3)
            
            # Search for content in document
            search_response = await client.get(
                f"{API_GATEWAY_URL}/api/v1/search",
                params={"q": "neural networks"},
                headers=auth_headers
            )
            assert search_response.status_code == 200
            results = search_response.json()["data"]["results"]
            assert len(results) > 0
            assert any(a["name"] == "AI Research Document" for a in results)
            print("✓ Full-text search in document content working")
            
            # Search by tags
            tag_search = await client.get(
                f"{API_GATEWAY_URL}/api/v1/search",
                params={"tags": ["machine-learning"]},
                headers=auth_headers
            )
            assert tag_search.status_code == 200
            results = tag_search.json()["data"]["results"]
            assert len(results) > 0
            print("✓ Tag-based search working")
            
            # Search in description
            desc_search = await client.get(
                f"{API_GATEWAY_URL}/api/v1/search",
                params={"q": "beautiful blue sky"},
                headers=auth_headers
            )
            assert desc_search.status_code == 200
            results = desc_search.json()["data"]["results"]
            assert any(a["name"] == "Blue Sky Image" for a in results)
            print("✓ Description search working")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_advanced_search_filters(self, auth_headers, test_assets):
        """Test advanced search with filters and facets."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Wait for indexing
            await asyncio.sleep(2)
            
            # Search with file type filter
            type_search = await client.get(
                f"{API_GATEWAY_URL}/api/v1/search",
                params={
                    "q": "*",
                    "file_type": "image/jpeg"
                },
                headers=auth_headers
            )
            assert type_search.status_code == 200
            results = type_search.json()["data"]["results"]
            assert all(a["mime_type"] == "image/jpeg" for a in results)
            print("✓ File type filtering working")
            
            # Search with date range
            date_search = await client.get(
                f"{API_GATEWAY_URL}/api/v1/search",
                params={
                    "q": "*",
                    "created_after": (datetime.now() - timedelta(hours=1)).isoformat(),
                    "created_before": datetime.now().isoformat()
                },
                headers=auth_headers
            )
            assert date_search.status_code == 200
            results = date_search.json()["data"]["results"]
            assert len(results) == len(test_assets)
            print("✓ Date range filtering working")
            
            # Get search facets
            facet_search = await client.get(
                f"{API_GATEWAY_URL}/api/v1/search/facets",
                params={"q": "*"},
                headers=auth_headers
            )
            assert facet_search.status_code == 200
            facets = facet_search.json()["data"]
            assert "file_types" in facets
            assert "tags" in facets
            print("✓ Search facets working")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_natural_language_search(self, auth_headers, test_assets):
        """Test natural language search capabilities."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Wait for indexing and AI processing
            await asyncio.sleep(3)
            
            # Natural language query
            nl_search = await client.get(
                f"{API_GATEWAY_URL}/api/v1/search/natural",
                params={"q": "find all documents about AI from today"},
                headers=auth_headers
            )
            assert nl_search.status_code == 200
            results = nl_search.json()["data"]
            assert "interpreted_query" in results
            assert "filters" in results
            assert len(results["results"]) > 0
            print("✓ Natural language search working")
            
            # Semantic search
            semantic_search = await client.get(
                f"{API_GATEWAY_URL}/api/v1/search/semantic",
                params={"q": "machine learning algorithms"},
                headers=auth_headers
            )
            assert semantic_search.status_code == 200
            results = semantic_search.json()["data"]["results"]
            # Should find AI document even without exact match
            assert any(a["name"] == "AI Research Document" for a in results)
            print("✓ Semantic search working")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_saved_searches(self, auth_headers):
        """Test saved search functionality."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create saved search
            saved_search = {
                "name": "Recent AI Content",
                "description": "Find recent AI-related content",
                "query": "artificial intelligence OR machine learning",
                "filters": {
                    "created_after": "now-7d",
                    "file_type": ["text/plain", "application/pdf"]
                }
            }
            
            create_response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/search/saved",
                json=saved_search,
                headers=auth_headers
            )
            assert create_response.status_code == 201
            saved_id = create_response.json()["data"]["id"]
            print("✓ Saved search created")
            
            # Execute saved search
            exec_response = await client.get(
                f"{API_GATEWAY_URL}/api/v1/search/saved/{saved_id}/execute",
                headers=auth_headers
            )
            assert exec_response.status_code == 200
            print("✓ Saved search executed")
            
            # List saved searches
            list_response = await client.get(
                f"{API_GATEWAY_URL}/api/v1/search/saved",
                headers=auth_headers
            )
            assert list_response.status_code == 200
            saved_searches = list_response.json()["data"]
            assert len(saved_searches) > 0
            print("✓ Saved searches listed")
            
            # Delete saved search
            delete_response = await client.delete(
                f"{API_GATEWAY_URL}/api/v1/search/saved/{saved_id}",
                headers=auth_headers
            )
            assert delete_response.status_code == 204
            print("✓ Saved search deleted")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_search_suggestions(self, auth_headers, test_assets):
        """Test search suggestions and autocomplete."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Wait for indexing
            await asyncio.sleep(2)
            
            # Get search suggestions
            suggest_response = await client.get(
                f"{API_GATEWAY_URL}/api/v1/search/suggest",
                params={"q": "art"},
                headers=auth_headers
            )
            assert suggest_response.status_code == 200
            suggestions = suggest_response.json()["data"]
            assert len(suggestions) > 0
            assert any("artificial" in s.lower() for s in suggestions)
            print("✓ Search suggestions working")
            
            # Get search history
            history_response = await client.get(
                f"{API_GATEWAY_URL}/api/v1/search/history",
                headers=auth_headers
            )
            assert history_response.status_code == 200
            history = history_response.json()["data"]
            # Should have entries from previous searches
            assert len(history) > 0
            print("✓ Search history working")
            
            print("\n✅ Search integration test completed successfully!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
#!/usr/bin/env python3
"""
Test script for the search engine indexing pipeline
"""

import asyncio
import json
import httpx
from datetime import datetime
from typing import List, Dict, Any

# Configuration
SEARCH_ENGINE_URL = "http://localhost:8006"
TEST_DATA_FILE = "test_data.json"


async def test_single_document_indexing():
    """Test indexing a single document"""
    print("Testing single document indexing...")
    
    test_document = {
        "id": "test-asset-001",
        "document": {
            "asset_id": "test-asset-001",
            "name": "sample_video.mp4",
            "description": "A sample video for testing search functionality",
            "file_path": "/storage/samples/sample_video.mp4",
            "file_name": "sample_video.mp4",
            "file_extension": ".mp4",
            "file_size": 1048576,
            "mime_type": "video/mp4",
            "asset_type": "video",
            "status": "active",
            "tags": ["sample", "test", "video"],
            "project_id": "proj-001",
            "created_by": "test-user",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "checksum": "abc123def456",
            "version": 1,
            "storage_location": "local",
            "is_proxy": False
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SEARCH_ENGINE_URL}/api/v1/index/document",
            json=test_document,
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Document indexed successfully: {result['document_id']}")
            return True
        else:
            print(f"❌ Document indexing failed: {response.status_code} - {response.text}")
            return False


async def test_bulk_document_indexing():
    """Test bulk document indexing"""
    print("Testing bulk document indexing...")
    
    test_documents = []
    for i in range(1, 6):
        doc = {
            "id": f"test-asset-{i:03d}",
            "document": {
                "asset_id": f"test-asset-{i:03d}",
                "name": f"test_video_{i}.mp4",
                "description": f"Test video number {i} for bulk indexing",
                "file_path": f"/storage/test/test_video_{i}.mp4",
                "file_name": f"test_video_{i}.mp4",
                "file_extension": ".mp4",
                "file_size": 1048576 * i,
                "mime_type": "video/mp4",
                "asset_type": "video",
                "status": "active",
                "tags": ["test", "bulk", f"video-{i}"],
                "project_id": "proj-001",
                "created_by": "test-user",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "checksum": f"checksum-{i}",
                "version": 1,
                "storage_location": "local",
                "is_proxy": False
            }
        }
        test_documents.append(doc)
    
    bulk_request = {
        "documents": test_documents,
        "refresh": True
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SEARCH_ENGINE_URL}/api/v1/index/bulk",
            json=bulk_request,
            timeout=60.0
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Bulk indexing successful: {result['successful_count']}/{result['total_documents']} documents")
            if result['failed_count'] > 0:
                print(f"⚠️  {result['failed_count']} documents failed")
            return True
        else:
            print(f"❌ Bulk indexing failed: {response.status_code} - {response.text}")
            return False


async def test_pipeline_asset_event():
    """Test pipeline asset event processing"""
    print("Testing pipeline asset event processing...")
    
    asset_event = {
        "event_type": "create",
        "asset_id": "pipeline-test-001",
        "name": "pipeline_test_video.mp4",
        "description": "Video created through pipeline event",
        "file_path": "/storage/pipeline/pipeline_test_video.mp4",
        "file_name": "pipeline_test_video.mp4",
        "file_extension": ".mp4",
        "file_size": 2097152,
        "mime_type": "video/mp4",
        "asset_type": "video",
        "status": "active",
        "tags": ["pipeline", "test", "event"],
        "project_id": "proj-002",
        "created_by": "pipeline-test",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "checksum": "pipeline123",
        "version": 1,
        "storage_location": "s3",
        "is_proxy": False
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SEARCH_ENGINE_URL}/api/v1/pipeline/asset/event",
            json=asset_event,
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Pipeline asset event processed: {result['message']}")
            return True
        else:
            print(f"❌ Pipeline asset event failed: {response.status_code} - {response.text}")
            return False


async def test_index_stats():
    """Test getting index statistics"""
    print("Testing index statistics...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SEARCH_ENGINE_URL}/api/v1/indices/stats",
            timeout=30.0
        )
        
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Retrieved stats for {len(stats)} indices")
            for stat in stats:
                print(f"  - {stat['index_name']}: {stat['document_count']} docs, {stat['store_size']}")
            return True
        else:
            print(f"❌ Failed to get index stats: {response.status_code} - {response.text}")
            return False


async def test_health_check():
    """Test service health check"""
    print("Testing service health check...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SEARCH_ENGINE_URL}/health",
            timeout=10.0
        )
        
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Service is healthy: {health['status']}")
            print(f"  - OpenSearch status: {health['opensearch_status']}")
            return True
        else:
            print(f"❌ Service health check failed: {response.status_code}")
            return False


async def cleanup_test_data():
    """Clean up test data"""
    print("Cleaning up test data...")
    
    test_asset_ids = [
        "test-asset-001",
        "test-asset-002", 
        "test-asset-003",
        "test-asset-004",
        "test-asset-005",
        "pipeline-test-001"
    ]
    
    async with httpx.AsyncClient() as client:
        for asset_id in test_asset_ids:
            try:
                response = await client.delete(
                    f"{SEARCH_ENGINE_URL}/api/v1/pipeline/asset/{asset_id}",
                    timeout=10.0
                )
                if response.status_code == 200:
                    print(f"  ✅ Cleaned up {asset_id}")
                else:
                    print(f"  ⚠️  Failed to clean up {asset_id}")
            except Exception as e:
                print(f"  ⚠️  Error cleaning up {asset_id}: {e}")


async def main():
    """Run all tests"""
    print("🔍 Search Engine Indexing Pipeline Tests")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health_check),
        ("Single Document Indexing", test_single_document_indexing),
        ("Bulk Document Indexing", test_bulk_document_indexing),
        ("Pipeline Asset Event", test_pipeline_asset_event),
        ("Index Statistics", test_index_stats),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
        print()
    
    print("=" * 50)
    print("Test Results:")
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print()
    cleanup = input("Clean up test data? (y/N): ")
    if cleanup.lower() == 'y':
        await cleanup_test_data()
    
    total_tests = len(results)
    passed_tests = sum(1 for _, result in results if result)
    print(f"\nSummary: {passed_tests}/{total_tests} tests passed")


if __name__ == "__main__":
    asyncio.run(main())
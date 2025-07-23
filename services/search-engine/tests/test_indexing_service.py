"""
Tests for the Indexing Service
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from src.services.indexing_service import IndexingService
from src.models.schemas import IndexDocument, BulkIndexRequest, IndexType
from src.core.exceptions import IndexingError, ValidationError


@pytest.fixture
def mock_opensearch_client():
    """Mock OpenSearch client"""
    client = AsyncMock()
    return client


@pytest.fixture
def indexing_service(mock_opensearch_client):
    """Indexing service with mocked client"""
    return IndexingService(mock_opensearch_client)


@pytest.mark.asyncio
async def test_index_document_success(indexing_service, mock_opensearch_client):
    """Test successful document indexing"""
    # Arrange
    document = IndexDocument(
        id="test-asset-123",
        document={
            "asset_id": "test-asset-123",
            "name": "test_video.mp4",
            "file_path": "/storage/test_video.mp4",
            "file_size": 1024,
            "mime_type": "video/mp4"
        }
    )
    
    mock_opensearch_client.index.return_value = {
        "result": "created",
        "_version": 1
    }
    
    # Act
    result = await indexing_service.index_document(document)
    
    # Assert
    assert result.success is True
    assert result.document_id == "test-asset-123"
    assert result.result == "created"
    assert result.version == 1
    
    # Verify OpenSearch was called
    mock_opensearch_client.index.assert_called_once()
    call_args = mock_opensearch_client.index.call_args
    assert call_args.kwargs["id"] == "test-asset-123"
    assert "indexed_at" in call_args.kwargs["body"]


@pytest.mark.asyncio
async def test_index_document_validation_error(indexing_service):
    """Test document validation error"""
    # Arrange
    document = IndexDocument(
        id="test-asset-123",
        document={}  # Empty document should fail validation
    )
    
    # Act & Assert
    with pytest.raises(ValidationError, match="Document cannot be empty"):
        await indexing_service.index_document(document)


@pytest.mark.asyncio
async def test_bulk_index_documents_success(indexing_service, mock_opensearch_client):
    """Test successful bulk indexing"""
    # Arrange
    documents = [
        IndexDocument(
            id="asset-1",
            document={
                "asset_id": "asset-1",
                "name": "video1.mp4",
                "file_path": "/storage/video1.mp4"
            }
        ),
        IndexDocument(
            id="asset-2", 
            document={
                "asset_id": "asset-2",
                "name": "video2.mp4",
                "file_path": "/storage/video2.mp4"
            }
        )
    ]
    
    request = BulkIndexRequest(documents=documents, refresh=False)
    
    # Mock the async_bulk helper
    async def mock_bulk_generator(*args, **kwargs):
        yield True, {"index": {"_id": "asset-1", "result": "created"}}
        yield True, {"index": {"_id": "asset-2", "result": "created"}}
    
    with patch('src.services.indexing_service.helpers.async_bulk', side_effect=mock_bulk_generator):
        # Act
        result = await indexing_service.bulk_index_documents(request)
    
    # Assert
    assert result.success is True
    assert result.total_documents == 2
    assert result.successful_count == 2
    assert result.failed_count == 0
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_delete_document_success(indexing_service, mock_opensearch_client):
    """Test successful document deletion"""
    # Arrange
    mock_opensearch_client.delete.return_value = {
        "result": "deleted"
    }
    
    # Act
    result = await indexing_service.delete_document("mams_assets", "test-asset-123")
    
    # Assert
    assert result.success is True
    assert result.document_id == "test-asset-123"
    assert result.index_name == "mams_assets"
    assert result.result == "deleted"
    
    mock_opensearch_client.delete.assert_called_once_with(
        index="mams_assets",
        id="test-asset-123",
        timeout="30s"
    )


@pytest.mark.asyncio
async def test_get_index_stats_success(indexing_service, mock_opensearch_client):
    """Test getting index statistics"""
    # Arrange
    mock_opensearch_client.indices.stats.return_value = {
        "indices": {
            "mams_assets": {
                "total": {
                    "docs": {"count": 100},
                    "store": {"size_in_bytes": 1024000}
                }
            }
        }
    }
    
    mock_opensearch_client.indices.get_settings.return_value = {
        "mams_assets": {
            "settings": {
                "index": {
                    "number_of_shards": "1",
                    "number_of_replicas": "0"
                }
            }
        }
    }
    
    mock_opensearch_client.cluster.health.return_value = {
        "status": "green"
    }
    
    # Act
    result = await indexing_service.get_index_stats("mams_assets")
    
    # Assert
    assert result.index_name == "mams_assets"
    assert result.document_count == 100
    assert result.store_size == "1000.0 KB"
    assert result.primary_shards == 1
    assert result.replica_shards == 0
    assert result.status == "green"


def test_auto_detect_index_asset(indexing_service):
    """Test auto-detection of asset index"""
    document = {
        "asset_id": "test-123",
        "file_path": "/storage/video.mp4",
        "mime_type": "video/mp4"
    }
    
    result = indexing_service._auto_detect_index(document)
    assert result == indexing_service.settings.assets_index_name


def test_auto_detect_index_metadata(indexing_service):
    """Test auto-detection of metadata index"""
    document = {
        "asset_id": "test-123",
        "metadata_id": "meta-456",
        "schema_id": "schema-789",
        "custom_fields": {"title": "Test Video"}
    }
    
    result = indexing_service._auto_detect_index(document)
    assert result == indexing_service.settings.metadata_index_name


def test_auto_detect_index_content(indexing_service):
    """Test auto-detection of content index"""
    document = {
        "asset_id": "test-123",
        "content": "This is the content text",
        "transcript": "This is the transcript"
    }
    
    result = indexing_service._auto_detect_index(document)
    assert result == indexing_service.settings.content_index_name


def test_validate_document_asset_missing_id(indexing_service):
    """Test validation error for asset document missing asset_id"""
    document = {
        "name": "video.mp4",
        "file_path": "/storage/video.mp4"
    }
    
    with pytest.raises(ValidationError, match="Asset documents must have an 'asset_id' field"):
        indexing_service._validate_document(document, indexing_service.settings.assets_index_name)


def test_prepare_asset_document(indexing_service):
    """Test asset document preparation"""
    document = {
        "asset_id": "test-123",
        "name": "video.mp4",
        "file_path": "/Storage/Video.MP4",
        "file_size": "1024",
        "tags": "tag1, tag2, tag3"
    }
    
    result = indexing_service._prepare_asset_document(document)
    
    assert result["file_size"] == 1024
    assert result["tags"] == ["tag1", "tag2", "tag3"]
    assert result["file_path_normalized"] == "/storage/video.mp4"


def test_prepare_metadata_document(indexing_service):
    """Test metadata document preparation"""
    document = {
        "asset_id": "test-123",
        "custom_fields": {
            "title": "Test Video",
            "duration": 120,
            "quality": "HD"
        }
    }
    
    result = indexing_service._prepare_metadata_document(document)
    
    assert result["custom_title"] == "Test Video"
    assert result["custom_duration"] == 120
    assert result["custom_quality"] == "HD"


def test_prepare_content_document(indexing_service):
    """Test content document preparation"""
    document = {
        "asset_id": "test-123",
        "content": "This is the main content",
        "transcript": "This is the transcript",
        "ocr_text": "This is OCR text"
    }
    
    result = indexing_service._prepare_content_document(document)
    
    assert result["all_text"] == "This is the main content This is the transcript This is OCR text"


def test_format_bytes(indexing_service):
    """Test byte formatting"""
    assert indexing_service._format_bytes(1024) == "1.0 KB"
    assert indexing_service._format_bytes(1048576) == "1.0 MB"
    assert indexing_service._format_bytes(1073741824) == "1.0 GB"
"""Main tests for AI/ML Service."""
import pytest
from httpx import AsyncClient
from fastapi import status


class TestHealthCheck:
    """Test health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test basic health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ai-ml-service"
    
    @pytest.mark.asyncio
    async def test_api_health_check(self, client: AsyncClient):
        """Test API health check endpoint."""
        response = await client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ai-ml-service"


class TestModels:
    """Test model management endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_models(self, client: AsyncClient):
        """Test listing available models."""
        response = await client.get("/api/v1/models")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "available_models" in data["data"]
        assert "loaded_models" in data["data"]
        assert "cache_stats" in data["data"]
    
    @pytest.mark.asyncio
    async def test_get_cache_stats(self, client: AsyncClient):
        """Test getting cache statistics."""
        response = await client.get("/api/v1/cache/stats")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data


class TestObjectDetection:
    """Test object detection functionality."""
    
    @pytest.mark.asyncio
    async def test_object_detection_missing_file(self, client: AsyncClient):
        """Test object detection with missing file."""
        response = await client.post("/api/v1/detect/objects")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_object_detection_invalid_file_type(self, client: AsyncClient):
        """Test object detection with invalid file type."""
        files = {"file": ("test.txt", b"not an image", "text/plain")}
        response = await client.post("/api/v1/detect/objects", files=files)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "File must be an image" in data["detail"]


class TestFaceDetection:
    """Test face detection functionality."""
    
    @pytest.mark.asyncio
    async def test_face_detection_missing_file(self, client: AsyncClient):
        """Test face detection with missing file."""
        response = await client.post("/api/v1/detect/faces")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_face_detection_invalid_file_type(self, client: AsyncClient):
        """Test face detection with invalid file type."""
        files = {"file": ("test.txt", b"not an image", "text/plain")}
        response = await client.post("/api/v1/detect/faces", files=files)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "File must be an image" in data["detail"]


class TestSpeechToText:
    """Test speech-to-text functionality."""
    
    @pytest.mark.asyncio
    async def test_transcription_missing_file(self, client: AsyncClient):
        """Test transcription with missing file."""
        response = await client.post("/api/v1/transcribe")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_transcription_invalid_file_type(self, client: AsyncClient):
        """Test transcription with invalid file type."""
        files = {"file": ("test.txt", b"not audio", "text/plain")}
        response = await client.post("/api/v1/transcribe", files=files)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "File must be an audio file" in data["detail"]


class TestMetrics:
    """Test metrics endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, client: AsyncClient):
        """Test getting service metrics."""
        response = await client.get("/api/v1/metrics")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "service" in data["data"]
        assert "version" in data["data"]
        assert "status" in data["data"]
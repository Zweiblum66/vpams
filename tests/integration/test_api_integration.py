"""
Integration tests for API Gateway and service communication
"""
import pytest
import asyncio
from httpx import AsyncClient
from tests.test_utils import TestDataGenerator, AuthTestUtils


@pytest.mark.integration
class TestAPIIntegration:
    """Test integration between API Gateway and other services"""
    
    @pytest.mark.asyncio
    async def test_user_registration_flow(self, test_client: AsyncClient):
        """Test complete user registration flow"""
        # 1. Register a new user
        user_data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "username": "testuser",
            "full_name": "Test User"
        }
        
        response = await test_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201
        user = response.json()
        assert user["email"] == user_data["email"]
        
        # 2. Login with the new user
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        
        response = await test_client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        tokens = response.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        
        # 3. Get user profile
        headers = AuthTestUtils.get_auth_headers(tokens["access_token"])
        response = await test_client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        profile = response.json()
        assert profile["email"] == user_data["email"]
    
    @pytest.mark.asyncio
    async def test_asset_upload_workflow(self, test_client: AsyncClient, auth_headers: dict):
        """Test complete asset upload and processing workflow"""
        # 1. Create upload request
        upload_request = {
            "filename": "test_video.mp4",
            "file_size": 104857600,  # 100MB
            "mime_type": "video/mp4"
        }
        
        response = await test_client.post(
            "/api/v1/assets/upload/request",
            json=upload_request,
            headers=auth_headers
        )
        assert response.status_code == 200
        upload_info = response.json()
        assert "upload_url" in upload_info
        assert "asset_id" in upload_info
        
        # 2. Simulate file upload (in real test, would upload to presigned URL)
        # For now, we'll confirm the upload
        confirm_data = {
            "asset_id": upload_info["asset_id"],
            "upload_complete": True
        }
        
        response = await test_client.post(
            "/api/v1/assets/upload/confirm",
            json=confirm_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # 3. Check asset processing status
        asset_id = upload_info["asset_id"]
        response = await test_client.get(
            f"/api/v1/assets/{asset_id}/status",
            headers=auth_headers
        )
        assert response.status_code == 200
        status = response.json()
        assert status["status"] in ["processing", "completed"]
        
        # 4. Get asset metadata
        response = await test_client.get(
            f"/api/v1/assets/{asset_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        asset = response.json()
        assert asset["id"] == asset_id
    
    @pytest.mark.asyncio
    async def test_search_integration(self, test_client: AsyncClient, auth_headers: dict):
        """Test search functionality across services"""
        # 1. Create test assets
        test_assets = []
        for i in range(5):
            asset_data = {
                "name": f"Test Asset {i}",
                "tags": ["test", f"category{i % 2}"],
                "description": f"This is test asset number {i}"
            }
            response = await test_client.post(
                "/api/v1/assets",
                json=asset_data,
                headers=auth_headers
            )
            assert response.status_code == 201
            test_assets.append(response.json())
        
        # Wait for indexing
        await asyncio.sleep(2)
        
        # 2. Search by text
        response = await test_client.get(
            "/api/v1/search",
            params={"q": "test asset", "limit": 10},
            headers=auth_headers
        )
        assert response.status_code == 200
        results = response.json()
        assert len(results["data"]) >= 5
        
        # 3. Search with filters
        response = await test_client.get(
            "/api/v1/search",
            params={"tags": "category1", "limit": 10},
            headers=auth_headers
        )
        assert response.status_code == 200
        results = response.json()
        assert all("category1" in item["tags"] for item in results["data"])
    
    @pytest.mark.asyncio
    async def test_workflow_execution(self, test_client: AsyncClient, auth_headers: dict):
        """Test workflow engine integration"""
        # 1. Create a workflow
        workflow_data = {
            "name": "Test Ingest Workflow",
            "type": "ingest",
            "steps": [
                {
                    "type": "validate",
                    "config": {"allowed_formats": ["mp4", "mov"]}
                },
                {
                    "type": "generate_proxy",
                    "config": {"quality": "medium"}
                },
                {
                    "type": "extract_metadata",
                    "config": {"extract_thumbnails": True}
                }
            ]
        }
        
        response = await test_client.post(
            "/api/v1/workflows",
            json=workflow_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        workflow = response.json()
        
        # 2. Trigger workflow execution
        execution_data = {
            "workflow_id": workflow["id"],
            "input": {
                "asset_id": "test-asset-123",
                "file_path": "/storage/test.mp4"
            }
        }
        
        response = await test_client.post(
            "/api/v1/workflows/execute",
            json=execution_data,
            headers=auth_headers
        )
        assert response.status_code == 202
        execution = response.json()
        assert "execution_id" in execution
        
        # 3. Check execution status
        response = await test_client.get(
            f"/api/v1/workflows/executions/{execution['execution_id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        status = response.json()
        assert status["status"] in ["running", "completed", "failed"]


@pytest.mark.integration
class TestServiceCommunication:
    """Test direct service-to-service communication"""
    
    @pytest.mark.asyncio
    async def test_storage_metadata_integration(self):
        """Test integration between storage and metadata services"""
        # This would test direct service communication
        # In a real environment, you'd set up service clients
        pass
    
    @pytest.mark.asyncio
    async def test_asset_proxy_generation(self):
        """Test asset management triggering proxy generation"""
        # This would test message queue communication
        pass
    
    @pytest.mark.asyncio
    async def test_rights_asset_integration(self):
        """Test rights management integration with assets"""
        # This would test rights checks on asset access
        pass
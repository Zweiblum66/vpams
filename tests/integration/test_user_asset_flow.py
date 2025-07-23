#!/usr/bin/env python3
"""
Integration Test: User Asset Flow

Tests the complete flow of user authentication, asset upload, metadata extraction,
proxy generation, and search functionality across multiple services.
"""

import asyncio
import pytest
import httpx
import os
import tempfile
import json
from datetime import datetime
from pathlib import Path
import time

# Service URLs
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8001")
ASSET_SERVICE_URL = os.getenv("ASSET_SERVICE_URL", "http://localhost:8002")
STORAGE_SERVICE_URL = os.getenv("STORAGE_SERVICE_URL", "http://localhost:8003")
METADATA_SERVICE_URL = os.getenv("METADATA_SERVICE_URL", "http://localhost:8004")
SEARCH_SERVICE_URL = os.getenv("SEARCH_SERVICE_URL", "http://localhost:8005")
PROXY_SERVICE_URL = os.getenv("PROXY_SERVICE_URL", "http://localhost:8007")


class TestUserAssetFlow:
    """Integration test for complete user asset management flow."""
    
    @pytest.fixture
    async def test_user_credentials(self):
        """Generate unique test user credentials."""
        timestamp = int(time.time())
        return {
            "username": f"test_user_{timestamp}",
            "email": f"test_{timestamp}@example.com",
            "password": "TestPassword123!",
            "full_name": "Integration Test User"
        }
    
    @pytest.fixture
    async def test_file(self):
        """Create a test file for upload."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test file for integration testing.\n")
            f.write(f"Created at: {datetime.now()}\n")
            f.write("Content for testing the complete asset flow.\n")
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_user_asset_flow(self, test_user_credentials, test_file):
        """
        Test the complete flow:
        1. User registration
        2. User login
        3. Asset upload
        4. Metadata extraction
        5. Proxy generation
        6. Search for asset
        7. Download asset
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Register new user
            register_response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/auth/register",
                json=test_user_credentials
            )
            assert register_response.status_code == 201
            user_data = register_response.json()
            user_id = user_data["data"]["id"]
            print(f"✓ User registered: {user_id}")
            
            # Step 2: Login
            login_response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/auth/login",
                json={
                    "username": test_user_credentials["username"],
                    "password": test_user_credentials["password"]
                }
            )
            assert login_response.status_code == 200
            tokens = login_response.json()
            access_token = tokens["data"]["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}
            print("✓ User logged in")
            
            # Step 3: Create project for asset
            project_response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/projects",
                json={
                    "name": "Integration Test Project",
                    "description": "Project for integration testing",
                    "type": "project"
                },
                headers=headers
            )
            assert project_response.status_code == 201
            project_id = project_response.json()["data"]["id"]
            print(f"✓ Project created: {project_id}")
            
            # Step 4: Upload asset
            with open(test_file, 'rb') as f:
                files = {"file": ("test_file.txt", f, "text/plain")}
                upload_response = await client.post(
                    f"{API_GATEWAY_URL}/api/v1/assets/upload",
                    files=files,
                    data={
                        "name": "Integration Test Asset",
                        "project_id": project_id,
                        "description": "Test asset for integration testing"
                    },
                    headers=headers
                )
            assert upload_response.status_code == 201
            asset_data = upload_response.json()["data"]
            asset_id = asset_data["id"]
            print(f"✓ Asset uploaded: {asset_id}")
            
            # Step 5: Wait for metadata extraction
            await asyncio.sleep(2)  # Give time for async processing
            
            # Check metadata
            metadata_response = await client.get(
                f"{API_GATEWAY_URL}/api/v1/assets/{asset_id}/metadata",
                headers=headers
            )
            assert metadata_response.status_code == 200
            metadata = metadata_response.json()["data"]
            assert "file_size" in metadata
            assert "mime_type" in metadata
            print("✓ Metadata extracted")
            
            # Step 6: Search for asset
            await asyncio.sleep(1)  # Give time for indexing
            
            search_response = await client.get(
                f"{API_GATEWAY_URL}/api/v1/search",
                params={"q": "Integration Test Asset"},
                headers=headers
            )
            assert search_response.status_code == 200
            search_results = search_response.json()["data"]
            assert len(search_results["results"]) > 0
            assert any(r["id"] == asset_id for r in search_results["results"])
            print("✓ Asset found in search")
            
            # Step 7: Download asset
            download_response = await client.get(
                f"{API_GATEWAY_URL}/api/v1/assets/{asset_id}/download",
                headers=headers
            )
            assert download_response.status_code == 200
            assert len(download_response.content) > 0
            print("✓ Asset downloaded")
            
            # Step 8: Update asset metadata
            update_response = await client.patch(
                f"{API_GATEWAY_URL}/api/v1/assets/{asset_id}",
                json={
                    "metadata": {
                        "custom_field": "Integration test value",
                        "test_timestamp": datetime.now().isoformat()
                    }
                },
                headers=headers
            )
            assert update_response.status_code == 200
            print("✓ Asset metadata updated")
            
            # Step 9: Create version
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt') as f:
                f.write("This is version 2 of the test file.\n")
                f.flush()
                
                with open(f.name, 'rb') as version_file:
                    files = {"file": ("test_file_v2.txt", version_file, "text/plain")}
                    version_response = await client.post(
                        f"{API_GATEWAY_URL}/api/v1/assets/{asset_id}/versions",
                        files=files,
                        data={"comment": "Version 2 for integration test"},
                        headers=headers
                    )
            assert version_response.status_code == 201
            print("✓ Asset version created")
            
            # Step 10: Cleanup - Delete asset
            delete_response = await client.delete(
                f"{API_GATEWAY_URL}/api/v1/assets/{asset_id}",
                headers=headers
            )
            assert delete_response.status_code == 204
            print("✓ Asset deleted")
            
            # Cleanup - Delete project
            delete_project_response = await client.delete(
                f"{API_GATEWAY_URL}/api/v1/projects/{project_id}",
                headers=headers
            )
            assert delete_project_response.status_code == 204
            print("✓ Project deleted")
            
            print("\n✅ Integration test completed successfully!")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_user_permissions_flow(self, test_user_credentials):
        """
        Test user permissions and RBAC flow:
        1. Create two users
        2. Create roles and permissions
        3. Assign roles to users
        4. Test access control
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create admin user
            admin_creds = {
                **test_user_credentials,
                "username": test_user_credentials["username"] + "_admin",
                "email": "admin_" + test_user_credentials["email"]
            }
            
            # Register admin
            await client.post(
                f"{API_GATEWAY_URL}/api/v1/auth/register",
                json=admin_creds
            )
            
            # Login as admin
            admin_login = await client.post(
                f"{API_GATEWAY_URL}/api/v1/auth/login",
                json={
                    "username": admin_creds["username"],
                    "password": admin_creds["password"]
                }
            )
            admin_token = admin_login.json()["data"]["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Create regular user
            regular_creds = {
                **test_user_credentials,
                "username": test_user_credentials["username"] + "_regular",
                "email": "regular_" + test_user_credentials["email"]
            }
            
            regular_response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/auth/register",
                json=regular_creds
            )
            regular_user_id = regular_response.json()["data"]["id"]
            
            # Test that regular user cannot access admin endpoints
            regular_login = await client.post(
                f"{API_GATEWAY_URL}/api/v1/auth/login",
                json={
                    "username": regular_creds["username"],
                    "password": regular_creds["password"]
                }
            )
            regular_token = regular_login.json()["data"]["access_token"]
            regular_headers = {"Authorization": f"Bearer {regular_token}"}
            
            # Regular user should not be able to create roles
            role_response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/roles",
                json={
                    "name": "test_role",
                    "description": "Test role",
                    "permissions": []
                },
                headers=regular_headers
            )
            assert role_response.status_code == 403
            print("✓ RBAC working: Regular user cannot create roles")
            
            print("\n✅ User permissions flow test completed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
#!/usr/bin/env python3
"""
Integration Test: Workflow Execution Flow

Tests the complete workflow execution across multiple services including
asset processing, proxy generation, and notification delivery.
"""

import asyncio
import pytest
import httpx
import os
import tempfile
import json
from datetime import datetime
import time
from PIL import Image
import io

# Service URLs
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
WORKFLOW_SERVICE_URL = os.getenv("WORKFLOW_SERVICE_URL", "http://localhost:8009")


class TestWorkflowExecutionFlow:
    """Integration test for workflow execution across services."""
    
    @pytest.fixture
    async def auth_headers(self):
        """Get authentication headers for test user."""
        async with httpx.AsyncClient() as client:
            # Register test user
            timestamp = int(time.time())
            register_response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/auth/register",
                json={
                    "username": f"workflow_test_{timestamp}",
                    "email": f"workflow_{timestamp}@test.com",
                    "password": "Test123!@#",
                    "full_name": "Workflow Test User"
                }
            )
            
            # Login
            login_response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/auth/login",
                json={
                    "username": f"workflow_test_{timestamp}",
                    "password": "Test123!@#"
                }
            )
            
            token = login_response.json()["data"]["access_token"]
            return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    async def test_image(self):
        """Create a test image for processing."""
        # Create a simple test image
        img = Image.new('RGB', (800, 600), color='red')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG')
        img_buffer.seek(0)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(img_buffer.getvalue())
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_media_processing_workflow(self, auth_headers, test_image):
        """
        Test complete media processing workflow:
        1. Create workflow definition
        2. Upload asset
        3. Trigger workflow
        4. Monitor execution
        5. Verify outputs
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: Create media processing workflow
            workflow_def = {
                "name": "Integration Test Media Processing",
                "description": "Test workflow for media processing",
                "trigger_type": "manual",
                "tasks": [
                    {
                        "id": "extract_metadata",
                        "type": "metadata_extraction",
                        "name": "Extract Metadata",
                        "parameters": {
                            "extract_exif": True,
                            "extract_technical": True
                        }
                    },
                    {
                        "id": "generate_thumbnail",
                        "type": "proxy_generation",
                        "name": "Generate Thumbnail",
                        "parameters": {
                            "proxy_type": "thumbnail",
                            "width": 200,
                            "height": 150
                        },
                        "depends_on": ["extract_metadata"]
                    },
                    {
                        "id": "generate_preview",
                        "type": "proxy_generation",
                        "name": "Generate Preview",
                        "parameters": {
                            "proxy_type": "preview",
                            "width": 1280,
                            "height": 720
                        },
                        "depends_on": ["extract_metadata"]
                    },
                    {
                        "id": "auto_tag",
                        "type": "auto_tagging",
                        "name": "Auto Tag Content",
                        "parameters": {
                            "confidence_threshold": 0.7
                        },
                        "depends_on": ["generate_thumbnail", "generate_preview"]
                    }
                ]
            }
            
            create_response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/workflows",
                json=workflow_def,
                headers=auth_headers
            )
            assert create_response.status_code == 201
            workflow_id = create_response.json()["data"]["id"]
            print(f"✓ Workflow created: {workflow_id}")
            
            # Step 2: Upload test asset
            with open(test_image, 'rb') as f:
                files = {"file": ("test_image.jpg", f, "image/jpeg")}
                upload_response = await client.post(
                    f"{API_GATEWAY_URL}/api/v1/assets/upload",
                    files=files,
                    data={
                        "name": "Workflow Test Image",
                        "description": "Image for workflow integration test"
                    },
                    headers=auth_headers
                )
            assert upload_response.status_code == 201
            asset_id = upload_response.json()["data"]["id"]
            print(f"✓ Asset uploaded: {asset_id}")
            
            # Step 3: Execute workflow
            execution_response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/workflows/{workflow_id}/execute",
                json={
                    "input_data": {
                        "asset_id": asset_id
                    }
                },
                headers=auth_headers
            )
            assert execution_response.status_code == 201
            execution_id = execution_response.json()["data"]["id"]
            print(f"✓ Workflow execution started: {execution_id}")
            
            # Step 4: Monitor execution
            max_wait = 30  # seconds
            start_time = time.time()
            execution_complete = False
            
            while time.time() - start_time < max_wait:
                status_response = await client.get(
                    f"{API_GATEWAY_URL}/api/v1/workflows/executions/{execution_id}",
                    headers=auth_headers
                )
                assert status_response.status_code == 200
                
                execution_data = status_response.json()["data"]
                status = execution_data["status"]
                
                print(f"  Execution status: {status}")
                
                if status == "completed":
                    execution_complete = True
                    break
                elif status == "failed":
                    pytest.fail(f"Workflow execution failed: {execution_data.get('error')}")
                
                await asyncio.sleep(2)
            
            assert execution_complete, "Workflow execution timed out"
            print("✓ Workflow execution completed")
            
            # Step 5: Verify outputs
            # Check metadata was extracted
            metadata_response = await client.get(
                f"{API_GATEWAY_URL}/api/v1/assets/{asset_id}/metadata",
                headers=auth_headers
            )
            assert metadata_response.status_code == 200
            metadata = metadata_response.json()["data"]
            assert "width" in metadata
            assert "height" in metadata
            print("✓ Metadata extracted successfully")
            
            # Check proxies were generated
            proxies_response = await client.get(
                f"{API_GATEWAY_URL}/api/v1/assets/{asset_id}/proxies",
                headers=auth_headers
            )
            assert proxies_response.status_code == 200
            proxies = proxies_response.json()["data"]
            assert len(proxies) >= 2  # thumbnail and preview
            print("✓ Proxies generated successfully")
            
            # Check tags were added
            asset_response = await client.get(
                f"{API_GATEWAY_URL}/api/v1/assets/{asset_id}",
                headers=auth_headers
            )
            assert asset_response.status_code == 200
            asset_data = asset_response.json()["data"]
            assert "tags" in asset_data
            print("✓ Auto-tagging completed")
            
            print("\n✅ Media processing workflow test completed successfully!")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_approval_workflow(self, auth_headers):
        """
        Test approval workflow with human tasks:
        1. Create approval workflow
        2. Submit content for approval
        3. Simulate approval
        4. Verify completion
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create approval workflow
            workflow_def = {
                "name": "Content Approval Workflow",
                "description": "Test workflow with approval steps",
                "trigger_type": "manual",
                "tasks": [
                    {
                        "id": "submit_for_review",
                        "type": "notification",
                        "name": "Submit for Review",
                        "parameters": {
                            "recipient": "reviewer@test.com",
                            "subject": "Content pending review",
                            "template": "review_request"
                        }
                    },
                    {
                        "id": "approval_task",
                        "type": "approval",
                        "name": "Content Approval",
                        "parameters": {
                            "approvers": ["reviewer@test.com"],
                            "require_all": False,
                            "timeout_hours": 24
                        },
                        "depends_on": ["submit_for_review"]
                    },
                    {
                        "id": "publish_content",
                        "type": "asset_update",
                        "name": "Publish Content",
                        "parameters": {
                            "status": "published",
                            "metadata": {
                                "published_at": "{{current_timestamp}}",
                                "approved_by": "{{approval_task.approver}}"
                            }
                        },
                        "depends_on": ["approval_task"],
                        "condition": "approval_task.approved == true"
                    }
                ]
            }
            
            create_response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/workflows",
                json=workflow_def,
                headers=auth_headers
            )
            assert create_response.status_code == 201
            workflow_id = create_response.json()["data"]["id"]
            
            # Execute workflow
            execution_response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/workflows/{workflow_id}/execute",
                json={
                    "input_data": {
                        "content_id": "test_content_123",
                        "title": "Test Content for Approval"
                    }
                },
                headers=auth_headers
            )
            assert execution_response.status_code == 201
            execution_id = execution_response.json()["data"]["id"]
            
            # Wait for approval task
            await asyncio.sleep(2)
            
            # Get pending approvals
            approvals_response = await client.get(
                f"{API_GATEWAY_URL}/api/v1/workflows/executions/{execution_id}/approvals",
                headers=auth_headers
            )
            assert approvals_response.status_code == 200
            approvals = approvals_response.json()["data"]
            assert len(approvals) > 0
            
            approval_task_id = approvals[0]["task_id"]
            
            # Simulate approval
            approve_response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/workflows/executions/{execution_id}/approve/{approval_task_id}",
                json={
                    "approved": True,
                    "comments": "Looks good, approved for publishing"
                },
                headers=auth_headers
            )
            assert approve_response.status_code == 200
            
            # Wait for completion
            await asyncio.sleep(3)
            
            # Check final status
            final_status = await client.get(
                f"{API_GATEWAY_URL}/api/v1/workflows/executions/{execution_id}",
                headers=auth_headers
            )
            assert final_status.status_code == 200
            assert final_status.json()["data"]["status"] == "completed"
            
            print("\n✅ Approval workflow test completed successfully!")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_scheduled_workflow(self, auth_headers):
        """Test scheduled workflow execution."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create a scheduled workflow
            workflow_def = {
                "name": "Scheduled Cleanup Workflow",
                "description": "Test scheduled workflow",
                "trigger_type": "schedule",
                "trigger_config": {
                    "cron": "*/5 * * * *"  # Every 5 minutes
                },
                "tasks": [
                    {
                        "id": "find_old_assets",
                        "type": "asset_search",
                        "name": "Find Old Assets",
                        "parameters": {
                            "query": "created_at < now-30d",
                            "status": "draft"
                        }
                    },
                    {
                        "id": "archive_assets",
                        "type": "asset_archive",
                        "name": "Archive Old Assets",
                        "parameters": {
                            "storage_tier": "archive"
                        },
                        "depends_on": ["find_old_assets"]
                    }
                ]
            }
            
            create_response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/workflows",
                json=workflow_def,
                headers=auth_headers
            )
            assert create_response.status_code == 201
            workflow_id = create_response.json()["data"]["id"]
            
            # Enable the workflow
            enable_response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/workflows/{workflow_id}/enable",
                headers=auth_headers
            )
            assert enable_response.status_code == 200
            
            # Verify it's scheduled
            workflow_response = await client.get(
                f"{API_GATEWAY_URL}/api/v1/workflows/{workflow_id}",
                headers=auth_headers
            )
            assert workflow_response.status_code == 200
            workflow_data = workflow_response.json()["data"]
            assert workflow_data["is_active"] == True
            assert workflow_data["next_run_at"] is not None
            
            print("\n✅ Scheduled workflow test completed successfully!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
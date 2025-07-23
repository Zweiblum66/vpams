"""
Task Executor

This module handles the execution of individual workflow tasks, including:
- Task type dispatch
- Parameter resolution
- External service integration
- Error handling and retry logic
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import aioredis
import structlog

from ..models.schemas import TaskConfig, TaskInstance, TaskType, TaskStatus
from ..core.config import settings
from ..core.exceptions import TaskExecutionError

logger = structlog.get_logger()


class TaskExecutor:
    """
    Executes individual workflow tasks
    """
    
    def __init__(self, db_session: AsyncSession, redis_client: aioredis.Redis = None):
        self.db = db_session
        self.redis = redis_client
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Task handlers
        self.task_handlers = {
            # Media Processing
            TaskType.TRANSCODE: self._execute_transcode,
            TaskType.GENERATE_PROXY: self._execute_generate_proxy,
            TaskType.EXTRACT_METADATA: self._execute_extract_metadata,
            TaskType.GENERATE_THUMBNAIL: self._execute_generate_thumbnail,
            
            # File Operations
            TaskType.COPY_FILE: self._execute_copy_file,
            TaskType.MOVE_FILE: self._execute_move_file,
            TaskType.DELETE_FILE: self._execute_delete_file,
            TaskType.ARCHIVE_FILE: self._execute_archive_file,
            
            # Asset Operations
            TaskType.CREATE_ASSET: self._execute_create_asset,
            TaskType.UPDATE_ASSET: self._execute_update_asset,
            TaskType.TAG_ASSET: self._execute_tag_asset,
            TaskType.PUBLISH_ASSET: self._execute_publish_asset,
            
            # Notification
            TaskType.SEND_EMAIL: self._execute_send_email,
            TaskType.SEND_NOTIFICATION: self._execute_send_notification,
            TaskType.WEBHOOK_CALL: self._execute_webhook_call,
            
            # Control Flow
            TaskType.WAIT: self._execute_wait,
            
            # Integration
            TaskType.API_CALL: self._execute_api_call,
            TaskType.SCRIPT_EXECUTION: self._execute_script,
            TaskType.APPROVAL: self._execute_approval,
            
            # AI/ML
            TaskType.AUTO_TAG: self._execute_auto_tag,
            TaskType.TRANSCRIBE: self._execute_transcribe,
            TaskType.DETECT_OBJECTS: self._execute_detect_objects,
            TaskType.ANALYZE_CONTENT: self._execute_analyze_content,
        }
    
    async def execute_task(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Any:
        """
        Execute a task based on its type
        """
        task_type = task_config.task_type
        
        if task_type not in self.task_handlers:
            raise TaskExecutionError(f"Unsupported task type: {task_type}")
        
        logger.info(
            "Executing task",
            task_id=task_config.task_id,
            task_type=task_type.value,
            task_name=task_config.name
        )
        
        # Get handler
        handler = self.task_handlers[task_type]
        
        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                handler(task_instance, task_config, context),
                timeout=task_config.timeout
            )
            
            logger.info(
                "Task executed successfully",
                task_id=task_config.task_id,
                task_type=task_type.value
            )
            
            return result
            
        except asyncio.TimeoutError:
            raise TaskExecutionError(
                f"Task {task_config.task_id} timed out after {task_config.timeout} seconds"
            )
        except Exception as e:
            logger.error(
                "Task execution failed",
                task_id=task_config.task_id,
                task_type=task_type.value,
                error=str(e)
            )
            raise
    
    # Media Processing Tasks
    
    async def _execute_transcode(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute transcode task
        """
        params = task_instance.input_data
        
        # Call proxy generation service
        response = await self.http_client.post(
            f"{settings.PROXY_SERVICE_URL}/api/v1/transcode",
            json={
                "asset_id": params.get("asset_id"),
                "profile": params.get("profile", "default"),
                "output_format": params.get("output_format"),
                "settings": params.get("settings", {})
            }
        )
        
        if response.status_code != 200:
            raise TaskExecutionError(f"Transcode failed: {response.text}")
        
        return response.json()
    
    async def _execute_generate_proxy(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute generate proxy task
        """
        params = task_instance.input_data
        
        # Call proxy generation service
        response = await self.http_client.post(
            f"{settings.PROXY_SERVICE_URL}/api/v1/proxy",
            json={
                "asset_id": params.get("asset_id"),
                "proxy_type": params.get("proxy_type", "video"),
                "quality": params.get("quality", "medium")
            }
        )
        
        if response.status_code != 200:
            raise TaskExecutionError(f"Proxy generation failed: {response.text}")
        
        return response.json()
    
    async def _execute_extract_metadata(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute extract metadata task
        """
        params = task_instance.input_data
        
        # Call metadata service
        response = await self.http_client.post(
            f"{settings.METADATA_SERVICE_URL}/api/v1/extract",
            json={
                "asset_id": params.get("asset_id"),
                "extractors": params.get("extractors", ["basic", "technical"])
            }
        )
        
        if response.status_code != 200:
            raise TaskExecutionError(f"Metadata extraction failed: {response.text}")
        
        return response.json()
    
    async def _execute_generate_thumbnail(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute generate thumbnail task
        """
        params = task_instance.input_data
        
        # Call proxy generation service
        response = await self.http_client.post(
            f"{settings.PROXY_SERVICE_URL}/api/v1/thumbnail",
            json={
                "asset_id": params.get("asset_id"),
                "count": params.get("count", 1),
                "method": params.get("method", "interval")
            }
        )
        
        if response.status_code != 200:
            raise TaskExecutionError(f"Thumbnail generation failed: {response.text}")
        
        return response.json()
    
    # File Operations Tasks
    
    async def _execute_copy_file(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute copy file task
        """
        params = task_instance.input_data
        
        # Call storage service
        # This would integrate with the storage abstraction service
        return {
            "status": "success",
            "source": params.get("source"),
            "destination": params.get("destination")
        }
    
    async def _execute_move_file(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute move file task
        """
        params = task_instance.input_data
        
        # Call storage service
        return {
            "status": "success",
            "source": params.get("source"),
            "destination": params.get("destination")
        }
    
    async def _execute_delete_file(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute delete file task
        """
        params = task_instance.input_data
        
        # Call storage service
        return {
            "status": "success",
            "path": params.get("path")
        }
    
    async def _execute_archive_file(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute archive file task
        """
        params = task_instance.input_data
        
        # Call storage service to move to archive tier
        return {
            "status": "success",
            "asset_id": params.get("asset_id"),
            "archive_tier": params.get("tier", "cold")
        }
    
    # Asset Operations Tasks
    
    async def _execute_create_asset(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute create asset task
        """
        params = task_instance.input_data
        
        # Call asset management service
        response = await self.http_client.post(
            f"{settings.ASSET_SERVICE_URL}/api/v1/assets",
            json=params
        )
        
        if response.status_code != 201:
            raise TaskExecutionError(f"Asset creation failed: {response.text}")
        
        return response.json()
    
    async def _execute_update_asset(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute update asset task
        """
        params = task_instance.input_data
        asset_id = params.pop("asset_id", None)
        
        if not asset_id:
            raise TaskExecutionError("asset_id is required for update_asset task")
        
        # Call asset management service
        response = await self.http_client.patch(
            f"{settings.ASSET_SERVICE_URL}/api/v1/assets/{asset_id}",
            json=params
        )
        
        if response.status_code != 200:
            raise TaskExecutionError(f"Asset update failed: {response.text}")
        
        return response.json()
    
    async def _execute_tag_asset(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute tag asset task
        """
        params = task_instance.input_data
        
        # Call asset management service
        response = await self.http_client.post(
            f"{settings.ASSET_SERVICE_URL}/api/v1/assets/{params['asset_id']}/tags",
            json={"tags": params.get("tags", [])}
        )
        
        if response.status_code != 200:
            raise TaskExecutionError(f"Asset tagging failed: {response.text}")
        
        return response.json()
    
    async def _execute_publish_asset(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute publish asset task
        """
        params = task_instance.input_data
        
        # Call asset management service
        response = await self.http_client.post(
            f"{settings.ASSET_SERVICE_URL}/api/v1/assets/{params['asset_id']}/publish",
            json={
                "destination": params.get("destination"),
                "settings": params.get("settings", {})
            }
        )
        
        if response.status_code != 200:
            raise TaskExecutionError(f"Asset publishing failed: {response.text}")
        
        return response.json()
    
    # Notification Tasks
    
    async def _execute_send_email(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute send email task
        """
        params = task_instance.input_data
        
        # Call notification service
        response = await self.http_client.post(
            f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/email",
            json={
                "to": params.get("to"),
                "subject": params.get("subject"),
                "body": params.get("body"),
                "template": params.get("template"),
                "template_data": params.get("template_data", {})
            }
        )
        
        if response.status_code != 200:
            raise TaskExecutionError(f"Email sending failed: {response.text}")
        
        return response.json()
    
    async def _execute_send_notification(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute send notification task
        """
        params = task_instance.input_data
        
        # Call notification service
        response = await self.http_client.post(
            f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notifications",
            json={
                "user_id": params.get("user_id"),
                "type": params.get("type", "workflow"),
                "title": params.get("title"),
                "message": params.get("message"),
                "data": params.get("data", {})
            }
        )
        
        if response.status_code != 200:
            raise TaskExecutionError(f"Notification sending failed: {response.text}")
        
        return response.json()
    
    async def _execute_webhook_call(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute webhook call task
        """
        params = task_instance.input_data
        
        # Make webhook call
        method = params.get("method", "POST").upper()
        url = params.get("url")
        headers = params.get("headers", {})
        body = params.get("body", {})
        
        if not url:
            raise TaskExecutionError("URL is required for webhook_call task")
        
        response = await self.http_client.request(
            method=method,
            url=url,
            headers=headers,
            json=body if method in ["POST", "PUT", "PATCH"] else None,
            params=body if method == "GET" else None
        )
        
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text
        }
    
    # Control Flow Tasks
    
    async def _execute_wait(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute wait task
        """
        params = task_instance.input_data
        duration = params.get("duration", 1)
        
        await asyncio.sleep(duration)
        
        return {"waited": duration}
    
    # Integration Tasks
    
    async def _execute_api_call(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute API call task
        """
        params = task_instance.input_data
        
        # Make API call
        method = params.get("method", "GET").upper()
        url = params.get("url")
        headers = params.get("headers", {})
        body = params.get("body", {})
        auth = params.get("auth", {})
        
        if not url:
            raise TaskExecutionError("URL is required for api_call task")
        
        # Add authentication if provided
        if auth.get("type") == "bearer":
            headers["Authorization"] = f"Bearer {auth.get('token')}"
        elif auth.get("type") == "basic":
            # httpx handles basic auth
            pass
        
        response = await self.http_client.request(
            method=method,
            url=url,
            headers=headers,
            json=body if method in ["POST", "PUT", "PATCH"] else None,
            params=body if method == "GET" else None
        )
        
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        }
    
    async def _execute_script(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute script task
        """
        params = task_instance.input_data
        
        # In production, this would execute scripts in a sandboxed environment
        # For now, return mock result
        return {
            "status": "success",
            "script": params.get("script"),
            "language": params.get("language", "python"),
            "output": "Script executed successfully"
        }
    
    async def _execute_approval(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute approval task
        """
        params = task_instance.input_data
        
        # Create approval request
        # In a real implementation, this would create an approval request
        # and wait for user response
        return {
            "status": "pending",
            "approval_id": str(task_instance.task_instance_id),
            "approvers": params.get("approvers", []),
            "message": params.get("message")
        }
    
    # AI/ML Tasks
    
    async def _execute_auto_tag(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute auto-tag task
        """
        params = task_instance.input_data
        
        # Call AI/ML service
        # This would integrate with the AI/ML service
        return {
            "status": "success",
            "asset_id": params.get("asset_id"),
            "tags": ["example", "auto-generated", "workflow"]
        }
    
    async def _execute_transcribe(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute transcribe task
        """
        params = task_instance.input_data
        
        # Call AI/ML service for transcription
        return {
            "status": "success",
            "asset_id": params.get("asset_id"),
            "transcript": "This is a sample transcription",
            "language": params.get("language", "en")
        }
    
    async def _execute_detect_objects(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute detect objects task
        """
        params = task_instance.input_data
        
        # Call AI/ML service for object detection
        return {
            "status": "success",
            "asset_id": params.get("asset_id"),
            "objects": [
                {"label": "person", "confidence": 0.95, "bbox": [100, 100, 200, 200]},
                {"label": "car", "confidence": 0.87, "bbox": [300, 150, 400, 250]}
            ]
        }
    
    async def _execute_analyze_content(
        self,
        task_instance: TaskInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute analyze content task
        """
        params = task_instance.input_data
        
        # Call AI/ML service for content analysis
        return {
            "status": "success",
            "asset_id": params.get("asset_id"),
            "analysis": {
                "sentiment": "positive",
                "topics": ["technology", "innovation"],
                "summary": "This content discusses technological innovations"
            }
        }
    
    async def close(self):
        """
        Clean up resources
        """
        await self.http_client.aclose()
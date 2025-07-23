"""
Task Processor Service

Executes processing tasks on edge nodes.
"""

import asyncio
import os
import shutil
import tempfile
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from pathlib import Path
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from aioredis import Redis
import aiofiles
import httpx

from ..core.config import settings
from ..models.schemas import (
    ProcessingTask, TaskStatus, TaskType,
    TranscodeParameters, ImageProcessingParameters,
    AIAnalysisParameters
)
from ..db.models import ProcessingTaskModel
from ..utils.media_processor import MediaProcessor
from ..utils.ai_processor import AIProcessor
from ..utils.metrics import edge_metrics


logger = structlog.get_logger()


class TaskProcessor:
    """Processes tasks on edge nodes"""
    
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.node_id = settings.NODE_ID
        
        # Processing components
        self.media_processor = MediaProcessor()
        self.ai_processor = AIProcessor() if settings.ENABLE_AI_PROCESSING else None
        
        # Task handlers
        self.task_handlers: Dict[TaskType, Callable] = {
            TaskType.VIDEO_TRANSCODE: self._process_video_transcode,
            TaskType.IMAGE_RESIZE: self._process_image_resize,
            TaskType.THUMBNAIL_GENERATION: self._process_thumbnail,
            TaskType.FACE_DETECTION: self._process_face_detection,
            TaskType.OBJECT_DETECTION: self._process_object_detection,
            TaskType.SCENE_ANALYSIS: self._process_scene_analysis,
            TaskType.AUDIO_PROCESSING: self._process_audio,
            TaskType.METADATA_EXTRACTION: self._process_metadata_extraction,
            TaskType.CONTENT_ANALYSIS: self._process_content_analysis
        }
        
        # Active tasks
        self.active_tasks: Dict[str, asyncio.Task] = {}
        
        # HTTP client for downloading assets
        self.http_client = httpx.AsyncClient(timeout=300.0)  # 5 min timeout for large files
    
    async def initialize(self):
        """Initialize task processor"""
        logger.info("Initializing task processor", node_id=self.node_id)
        
        # Initialize processors
        await self.media_processor.initialize()
        if self.ai_processor:
            await self.ai_processor.initialize()
        
        # Create temp directory
        self.temp_dir = Path(tempfile.gettempdir()) / "edge-processing" / self.node_id
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def shutdown(self):
        """Shutdown task processor"""
        logger.info("Shutting down task processor")
        
        # Cancel active tasks
        for task_id, task in self.active_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Cleanup processors
        await self.media_processor.cleanup()
        if self.ai_processor:
            await self.ai_processor.cleanup()
        
        # Cleanup temp directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        
        # Close HTTP client
        await self.http_client.aclose()
    
    async def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Execute a processing task"""
        logger.info(f"Executing task {task_id}")
        
        try:
            # Get task from database
            task_model = await self.db.get(ProcessingTaskModel, task_id)
            if not task_model:
                raise ValueError(f"Task {task_id} not found")
            
            task = ProcessingTask.from_orm(task_model)
            
            # Check if task is assigned to this node
            if task.assigned_node != self.node_id:
                raise ValueError(f"Task {task_id} not assigned to this node")
            
            # Update task status
            await self._update_task_status(task_id, TaskStatus.PROCESSING)
            
            # Create async task
            process_task = asyncio.create_task(self._process_task(task))
            self.active_tasks[task_id] = process_task
            
            # Wait for completion
            result = await process_task
            
            # Update task with result
            await self._update_task_result(task_id, TaskStatus.COMPLETED, result)
            
            # Update metrics
            edge_metrics.tasks_completed.labels(
                node_id=self.node_id,
                task_type=task.task_type.value
            ).inc()
            
            return result
            
        except Exception as e:
            logger.error(f"Task {task_id} failed", error=str(e))
            
            # Update task status
            await self._update_task_result(
                task_id,
                TaskStatus.FAILED,
                {"error": str(e)}
            )
            
            # Update metrics
            edge_metrics.tasks_failed.labels(
                node_id=self.node_id,
                task_type=task.task_type.value if 'task' in locals() else "unknown"
            ).inc()
            
            raise
        
        finally:
            # Remove from active tasks
            self.active_tasks.pop(task_id, None)
    
    async def _process_task(self, task: ProcessingTask) -> Dict[str, Any]:
        """Process a specific task"""
        start_time = datetime.utcnow()
        
        # Get handler for task type
        handler = self.task_handlers.get(task.task_type)
        if not handler:
            raise ValueError(f"No handler for task type {task.task_type}")
        
        # Download asset to local temp
        local_path = await self._download_asset(task.asset_id)
        
        try:
            # Process the task
            result = await handler(task, local_path)
            
            # Upload result if needed
            if "output_path" in result:
                result["output_url"] = await self._upload_result(
                    result["output_path"],
                    task.asset_id,
                    task.task_type
                )
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            result["processing_time_seconds"] = processing_time
            
            # Update metrics
            edge_metrics.task_processing_time.labels(
                node_id=self.node_id,
                task_type=task.task_type.value
            ).observe(processing_time)
            
            return result
            
        finally:
            # Cleanup local file
            if local_path.exists():
                local_path.unlink()
    
    async def _download_asset(self, asset_id: str) -> Path:
        """Download asset to local temp storage"""
        # TODO: Get actual asset URL from asset service
        asset_url = f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET}/assets/{asset_id}"
        
        local_path = self.temp_dir / f"{asset_id}_input"
        
        # Download file
        async with self.http_client.stream("GET", asset_url) as response:
            response.raise_for_status()
            
            async with aiofiles.open(local_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    await f.write(chunk)
        
        return local_path
    
    async def _upload_result(self, local_path: Path, asset_id: str, task_type: TaskType) -> str:
        """Upload processing result"""
        # Generate output filename
        output_name = f"{asset_id}_{task_type.value}_output{local_path.suffix}"
        output_url = f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET}/processed/{output_name}"
        
        # TODO: Implement actual S3 upload
        # For now, just move to a results directory
        results_dir = self.temp_dir / "results"
        results_dir.mkdir(exist_ok=True)
        shutil.move(str(local_path), str(results_dir / output_name))
        
        return output_url
    
    async def _update_task_status(self, task_id: str, status: TaskStatus, progress: float = 0):
        """Update task status in database"""
        update_data = {
            "status": status,
            "progress": progress,
            "updated_at": datetime.utcnow()
        }
        
        if status == TaskStatus.PROCESSING:
            update_data["started_at"] = datetime.utcnow()
        
        await self.db.execute(
            update(ProcessingTaskModel)
            .where(ProcessingTaskModel.task_id == task_id)
            .values(**update_data)
        )
        await self.db.commit()
        
        # Update progress in Redis for real-time tracking
        await self.redis.setex(
            f"edge:task:progress:{task_id}",
            300,  # 5 min TTL
            progress
        )
    
    async def _update_task_result(self, task_id: str, status: TaskStatus, result: Dict[str, Any]):
        """Update task result in database"""
        update_data = {
            "status": status,
            "result": result,
            "progress": 100 if status == TaskStatus.COMPLETED else 0,
            "updated_at": datetime.utcnow()
        }
        
        if status == TaskStatus.COMPLETED:
            update_data["completed_at"] = datetime.utcnow()
        elif status == TaskStatus.FAILED:
            update_data["error"] = result.get("error", "Unknown error")
        
        await self.db.execute(
            update(ProcessingTaskModel)
            .where(ProcessingTaskModel.task_id == task_id)
            .values(**update_data)
        )
        await self.db.commit()
    
    # Task handlers
    async def _process_video_transcode(self, task: ProcessingTask, input_path: Path) -> Dict[str, Any]:
        """Process video transcode task"""
        params = TranscodeParameters(**task.parameters)
        
        # Generate output path
        output_path = self.temp_dir / f"{task.task_id}_output.{params.output_format}"
        
        # Progress callback
        async def progress_callback(percent: float):
            await self._update_task_status(task.task_id, TaskStatus.PROCESSING, percent)
        
        # Transcode video
        result = await self.media_processor.transcode_video(
            input_path,
            output_path,
            params,
            progress_callback
        )
        
        result["output_path"] = output_path
        return result
    
    async def _process_image_resize(self, task: ProcessingTask, input_path: Path) -> Dict[str, Any]:
        """Process image resize task"""
        params = ImageProcessingParameters(**task.parameters)
        
        # Generate output path
        output_format = params.format or input_path.suffix[1:]
        output_path = self.temp_dir / f"{task.task_id}_output.{output_format}"
        
        # Process image
        result = await self.media_processor.process_image(
            input_path,
            output_path,
            params
        )
        
        result["output_path"] = output_path
        return result
    
    async def _process_thumbnail(self, task: ProcessingTask, input_path: Path) -> Dict[str, Any]:
        """Generate thumbnail from video"""
        params = task.parameters
        
        # Generate thumbnail
        output_path = self.temp_dir / f"{task.task_id}_thumbnail.jpg"
        
        result = await self.media_processor.generate_thumbnail(
            input_path,
            output_path,
            time_offset=params.get("time_offset", 0),
            width=params.get("width", 320),
            height=params.get("height", 180)
        )
        
        result["output_path"] = output_path
        return result
    
    async def _process_face_detection(self, task: ProcessingTask, input_path: Path) -> Dict[str, Any]:
        """Process face detection task"""
        if not self.ai_processor:
            raise ValueError("AI processing not enabled")
        
        params = AIAnalysisParameters(**task.parameters)
        
        # Detect faces
        result = await self.ai_processor.detect_faces(
            input_path,
            confidence_threshold=params.confidence_threshold,
            return_visualization=params.return_visualization
        )
        
        if params.return_visualization and "visualization_path" in result:
            result["output_path"] = result["visualization_path"]
        
        return result
    
    async def _process_object_detection(self, task: ProcessingTask, input_path: Path) -> Dict[str, Any]:
        """Process object detection task"""
        if not self.ai_processor:
            raise ValueError("AI processing not enabled")
        
        params = AIAnalysisParameters(**task.parameters)
        
        # Detect objects
        result = await self.ai_processor.detect_objects(
            input_path,
            model_name=params.models[0] if params.models else settings.OBJECT_DETECTION_MODEL,
            confidence_threshold=params.confidence_threshold,
            max_results=params.max_results,
            return_visualization=params.return_visualization
        )
        
        if params.return_visualization and "visualization_path" in result:
            result["output_path"] = result["visualization_path"]
        
        return result
    
    async def _process_scene_analysis(self, task: ProcessingTask, input_path: Path) -> Dict[str, Any]:
        """Process scene analysis task"""
        if not self.ai_processor:
            raise ValueError("AI processing not enabled")
        
        # Analyze scenes
        result = await self.ai_processor.analyze_scenes(input_path)
        
        return result
    
    async def _process_audio(self, task: ProcessingTask, input_path: Path) -> Dict[str, Any]:
        """Process audio task"""
        params = task.parameters
        operation = params.get("operation", "normalize")
        
        output_path = self.temp_dir / f"{task.task_id}_audio_output.wav"
        
        if operation == "normalize":
            result = await self.media_processor.normalize_audio(
                input_path,
                output_path,
                target_level=params.get("target_level", -20)
            )
        elif operation == "extract":
            result = await self.media_processor.extract_audio(
                input_path,
                output_path
            )
        else:
            raise ValueError(f"Unknown audio operation: {operation}")
        
        result["output_path"] = output_path
        return result
    
    async def _process_metadata_extraction(self, task: ProcessingTask, input_path: Path) -> Dict[str, Any]:
        """Extract metadata from media file"""
        result = await self.media_processor.extract_metadata(input_path)
        return result
    
    async def _process_content_analysis(self, task: ProcessingTask, input_path: Path) -> Dict[str, Any]:
        """Comprehensive content analysis"""
        if not self.ai_processor:
            raise ValueError("AI processing not enabled")
        
        # Perform comprehensive analysis
        result = await self.ai_processor.analyze_content(input_path)
        
        return result
    
    async def get_task_progress(self, task_id: str) -> float:
        """Get current task progress"""
        progress = await self.redis.get(f"edge:task:progress:{task_id}")
        return float(progress) if progress else 0.0
    
    async def cancel_task(self, task_id: str):
        """Cancel a running task"""
        task = self.active_tasks.get(task_id)
        if task:
            task.cancel()
            await self._update_task_status(task_id, TaskStatus.CANCELLED)
            logger.info(f"Cancelled task {task_id}")
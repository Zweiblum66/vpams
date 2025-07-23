"""
Extraction Service

This module provides metadata extraction functionality for various file types.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID, uuid4
import structlog
import asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from ..db.models import (
    ExtractionTask, TechnicalMetadata, MetadataDocument
)
from ..models.schemas import (
    ExtractionRequest, ExtractionStatus, ExtractionType
)
from ..core.exceptions import (
    NotFoundError, ValidationError, ExtractionError
)
from .exif_extractor import ExifExtractor
from .ffprobe_extractor import FFprobeExtractor
from .audio_extractor import AudioExtractor
from .document_extractor import DocumentExtractor
from .sidecar_service import SidecarService

logger = structlog.get_logger()


class ExtractionService:
    """Service for managing metadata extraction tasks"""
    
    def __init__(self, db: AsyncIOMotorDatabase, user_id: UUID):
        self.db = db
        self.user_id = user_id
        self.extraction_tasks = db.extraction_tasks
        self.technical_metadata = db.technical_metadata
        self.metadata_documents = db.metadata_documents
        self.exif_extractor = ExifExtractor()
        self.ffprobe_extractor = FFprobeExtractor()
        self.audio_extractor = AudioExtractor()
        self.document_extractor = DocumentExtractor()
        self.sidecar_service = SidecarService()
    
    async def start_extraction(
        self, 
        asset_id: UUID, 
        extraction_request: ExtractionRequest
    ) -> UUID:
        """Start metadata extraction for an asset"""
        try:
            # Create extraction task
            task = ExtractionTask(
                task_id=uuid4(),
                asset_id=asset_id,
                extraction_types=[et.value for et in extraction_request.extraction_types],
                file_path="",  # Will be populated by worker
                file_size=0,   # Will be populated by worker
                mime_type="",  # Will be populated by worker
                status="pending",
                progress=0.0,
                created_at=datetime.utcnow()
            )
            
            # Insert task into database
            result = await self.extraction_tasks.insert_one(
                task.dict(by_alias=True, exclude_none=True)
            )
            task.id = result.inserted_id
            
            logger.info(
                "extraction_task_created",
                task_id=str(task.task_id),
                asset_id=str(asset_id),
                extraction_types=extraction_request.extraction_types
            )
            
            # TODO: Queue task for background processing
            # await self._queue_extraction_task(task)
            
            return task.task_id
            
        except Exception as e:
            logger.error("extraction_start_failed", error=str(e))
            raise
    
    async def get_task_status(self, task_id: UUID) -> ExtractionStatus:
        """Get extraction task status"""
        doc = await self.extraction_tasks.find_one({"task_id": task_id})
        if not doc:
            raise NotFoundError(f"Extraction task {task_id} not found")
        
        task = ExtractionTask(**doc)
        
        return ExtractionStatus(
            task_id=task.task_id,
            asset_id=task.asset_id,
            status=task.status,
            progress=task.progress,
            extraction_types=task.extraction_types,
            results=task.results,
            errors=task.errors,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            processing_time=task.processing_time
        )
    
    async def update_task_progress(
        self, 
        task_id: UUID, 
        progress: float, 
        status: str = None
    ) -> bool:
        """Update extraction task progress"""
        update_doc = {
            "progress": progress,
            "updated_at": datetime.utcnow()
        }
        
        if status:
            update_doc["status"] = status
            if status == "processing" and not update_doc.get("started_at"):
                update_doc["started_at"] = datetime.utcnow()
            elif status in ["completed", "failed"]:
                update_doc["completed_at"] = datetime.utcnow()
        
        result = await self.extraction_tasks.update_one(
            {"task_id": task_id},
            {"$set": update_doc}
        )
        
        return result.modified_count > 0
    
    async def complete_task(
        self, 
        task_id: UUID, 
        results: Dict[str, Any], 
        errors: List[Dict[str, Any]] = None
    ) -> bool:
        """Mark extraction task as completed"""
        now = datetime.utcnow()
        
        # Calculate processing time
        task_doc = await self.extraction_tasks.find_one({"task_id": task_id})
        if not task_doc:
            raise ResourceNotFoundError(f"Extraction task {task_id} not found")
        
        task = ExtractionTask(**task_doc)
        processing_time = None
        if task.started_at:
            processing_time = (now - task.started_at).total_seconds()
        
        update_doc = {
            "status": "completed",
            "progress": 100.0,
            "results": results,
            "errors": errors or [],
            "completed_at": now,
            "processing_time": processing_time
        }
        
        result = await self.extraction_tasks.update_one(
            {"task_id": task_id},
            {"$set": update_doc}
        )
        
        logger.info(
            "extraction_task_completed",
            task_id=str(task_id),
            asset_id=str(task.asset_id),
            processing_time=processing_time
        )
        
        return result.modified_count > 0
    
    async def fail_task(
        self, 
        task_id: UUID, 
        errors: List[Dict[str, Any]]
    ) -> bool:
        """Mark extraction task as failed"""
        now = datetime.utcnow()
        
        # Calculate processing time
        task_doc = await self.extraction_tasks.find_one({"task_id": task_id})
        if not task_doc:
            raise ResourceNotFoundError(f"Extraction task {task_id} not found")
        
        task = ExtractionTask(**task_doc)
        processing_time = None
        if task.started_at:
            processing_time = (now - task.started_at).total_seconds()
        
        update_doc = {
            "status": "failed",
            "errors": errors,
            "completed_at": now,
            "processing_time": processing_time
        }
        
        result = await self.extraction_tasks.update_one(
            {"task_id": task_id},
            {"$set": update_doc}
        )
        
        logger.error(
            "extraction_task_failed",
            task_id=str(task_id),
            asset_id=str(task.asset_id),
            errors=errors
        )
        
        return result.modified_count > 0
    
    async def get_asset_extractions(self, asset_id: UUID) -> List[ExtractionStatus]:
        """Get all extraction tasks for an asset"""
        cursor = self.extraction_tasks.find({"asset_id": asset_id})
        cursor = cursor.sort("created_at", -1)
        
        tasks = []
        async for doc in cursor:
            task = ExtractionTask(**doc)
            tasks.append(ExtractionStatus(
                task_id=task.task_id,
                asset_id=task.asset_id,
                status=task.status,
                progress=task.progress,
                extraction_types=task.extraction_types,
                results=task.results,
                errors=task.errors,
                created_at=task.created_at,
                started_at=task.started_at,
                completed_at=task.completed_at,
                processing_time=task.processing_time
            ))
        
        return tasks
    
    async def store_technical_metadata(
        self, 
        asset_id: UUID,
        file_info: Dict[str, Any],
        format_metadata: Dict[str, Any] = None,
        streams: List[Dict[str, Any]] = None,
        exif_data: Dict[str, Any] = None,
        xmp_data: Dict[str, Any] = None,
        iptc_data: Dict[str, Any] = None,
        id3_data: Dict[str, Any] = None,
        extraction_tool: str = "unknown",
        extraction_version: str = "1.0"
    ) -> str:
        """Store technical metadata for an asset"""
        try:
            # Check if technical metadata already exists
            existing = await self.technical_metadata.find_one({"asset_id": asset_id})
            
            technical_meta = TechnicalMetadata(
                asset_id=asset_id,
                file_info=file_info,
                format_metadata=format_metadata or {},
                streams=streams or [],
                exif_data=exif_data,
                xmp_data=xmp_data,
                iptc_data=iptc_data,
                id3_data=id3_data,
                extracted_at=datetime.utcnow(),
                extraction_tool=extraction_tool,
                extraction_version=extraction_version
            )
            
            if existing:
                # Update existing technical metadata
                result = await self.technical_metadata.update_one(
                    {"asset_id": asset_id},
                    {"$set": technical_meta.dict(by_alias=True, exclude_none=True)}
                )
                technical_meta.id = existing["_id"]
            else:
                # Create new technical metadata
                result = await self.technical_metadata.insert_one(
                    technical_meta.dict(by_alias=True, exclude_none=True)
                )
                technical_meta.id = result.inserted_id
            
            logger.info(
                "technical_metadata_stored",
                asset_id=str(asset_id),
                metadata_id=str(technical_meta.id),
                extraction_tool=extraction_tool
            )
            
            return str(technical_meta.id)
            
        except Exception as e:
            logger.error("technical_metadata_storage_failed", error=str(e))
            raise
    
    async def get_technical_metadata(self, asset_id: UUID) -> Optional[Dict[str, Any]]:
        """Get technical metadata for an asset"""
        doc = await self.technical_metadata.find_one({"asset_id": asset_id})
        if not doc:
            return None
        
        technical_meta = TechnicalMetadata(**doc)
        return {
            "id": str(technical_meta.id),
            "asset_id": technical_meta.asset_id,
            "file_info": technical_meta.file_info,
            "format_metadata": technical_meta.format_metadata,
            "streams": technical_meta.streams,
            "exif_data": technical_meta.exif_data,
            "xmp_data": technical_meta.xmp_data,
            "iptc_data": technical_meta.iptc_data,
            "id3_data": technical_meta.id3_data,
            "extracted_at": technical_meta.extracted_at,
            "extraction_tool": technical_meta.extraction_tool,
            "extraction_version": technical_meta.extraction_version,
            "extraction_errors": technical_meta.extraction_errors
        }
    
    async def cleanup_old_tasks(self, days_old: int = 30) -> int:
        """Clean up old extraction tasks"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        result = await self.extraction_tasks.delete_many({
            "created_at": {"$lt": cutoff_date},
            "status": {"$in": ["completed", "failed"]}
        })
        
        logger.info(
            "extraction_tasks_cleaned",
            deleted_count=result.deleted_count,
            cutoff_date=cutoff_date
        )
        
        return result.deleted_count
    
    async def get_extraction_statistics(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        try:
            # Basic counts
            total_tasks = await self.extraction_tasks.count_documents({})
            completed_tasks = await self.extraction_tasks.count_documents({"status": "completed"})
            failed_tasks = await self.extraction_tasks.count_documents({"status": "failed"})
            pending_tasks = await self.extraction_tasks.count_documents({"status": "pending"})
            processing_tasks = await self.extraction_tasks.count_documents({"status": "processing"})
            
            # Extraction type statistics
            type_stats = await self.extraction_tasks.aggregate([
                {"$unwind": "$extraction_types"},
                {"$group": {
                    "_id": "$extraction_types",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}}
            ]).to_list(length=20)
            
            # Average processing time
            avg_processing_time = await self.extraction_tasks.aggregate([
                {"$match": {"processing_time": {"$ne": None}}},
                {"$group": {
                    "_id": None,
                    "avg_processing_time": {"$avg": "$processing_time"}
                }}
            ]).to_list(length=1)
            
            return {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "pending_tasks": pending_tasks,
                "processing_tasks": processing_tasks,
                "success_rate": (completed_tasks / total_tasks) if total_tasks > 0 else 0,
                "extraction_types": type_stats,
                "avg_processing_time": avg_processing_time[0]["avg_processing_time"] if avg_processing_time else 0,
                "generated_at": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error("extraction_statistics_failed", error=str(e))
            raise
    
    async def retry_failed_task(self, task_id: UUID) -> bool:
        """Retry a failed extraction task"""
        doc = await self.extraction_tasks.find_one({"task_id": task_id})
        if not doc:
            raise NotFoundError(f"Extraction task {task_id} not found")
        
        task = ExtractionTask(**doc)
        if task.status != "failed":
            raise ValidationError("Can only retry failed tasks")
        
        if task.retry_count >= task.max_retries:
            raise ValidationError("Maximum retry attempts exceeded")
        
        # Reset task for retry
        update_doc = {
            "status": "pending",
            "progress": 0.0,
            "retry_count": task.retry_count + 1,
            "started_at": None,
            "completed_at": None,
            "processing_time": None,
            "errors": []
        }
        
        result = await self.extraction_tasks.update_one(
            {"task_id": task_id},
            {"$set": update_doc}
        )
        
        if result.modified_count > 0:
            # TODO: Re-queue task for processing
            # await self._queue_extraction_task(task)
            
            logger.info(
                "extraction_task_retried",
                task_id=str(task_id),
                retry_count=task.retry_count + 1
            )
        
        return result.modified_count > 0
    
    async def extract_exif_metadata(self, asset_id: UUID, file_path: str) -> Dict[str, Any]:
        """Extract EXIF metadata from image file"""
        try:
            # Check if file format is supported
            if not self.exif_extractor.is_supported_format(file_path):
                raise ExtractionError(f"Unsupported file format for EXIF extraction: {file_path}")
            
            # Extract EXIF data
            exif_data = await self.exif_extractor.extract_exif_metadata(file_path)
            
            # Store in technical metadata
            await self.store_technical_metadata(
                asset_id=asset_id,
                file_info=exif_data.get('extraction_info', {}),
                format_metadata=exif_data.get('processed_exif', {}),
                exif_data=exif_data.get('raw_exif', {}),
                extraction_tool='exif_extractor',
                extraction_version='1.0'
            )
            
            logger.info(
                "exif_metadata_extracted",
                asset_id=str(asset_id),
                file_path=file_path,
                has_gps=exif_data.get('gps_data', {}).get('has_gps', False)
            )
            
            return exif_data
            
        except Exception as e:
            logger.error(
                "exif_extraction_failed",
                asset_id=str(asset_id),
                file_path=file_path,
                error=str(e)
            )
            raise ExtractionError(f"EXIF extraction failed: {str(e)}")
    
    async def extract_basic_image_info(self, asset_id: UUID, file_path: str) -> Dict[str, Any]:
        """Extract basic image information"""
        try:
            image_info = await self.exif_extractor.get_basic_image_info(file_path)
            
            # Store as technical metadata
            await self.store_technical_metadata(
                asset_id=asset_id,
                file_info=image_info,
                extraction_tool='basic_image_extractor',
                extraction_version='1.0'
            )
            
            logger.info(
                "basic_image_info_extracted",
                asset_id=str(asset_id),
                file_path=file_path,
                width=image_info.get('width'),
                height=image_info.get('height'),
                format=image_info.get('format')
            )
            
            return image_info
            
        except Exception as e:
            logger.error(
                "basic_image_extraction_failed",
                asset_id=str(asset_id),
                file_path=file_path,
                error=str(e)
            )
            raise ExtractionError(f"Basic image extraction failed: {str(e)}")
    
    async def extract_batch_exif(self, extractions: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Extract EXIF metadata from multiple files"""
        results = {}
        
        for extraction in extractions:
            asset_id = extraction['asset_id']
            file_path = extraction['file_path']
            
            try:
                exif_data = await self.extract_exif_metadata(asset_id, file_path)
                results[str(asset_id)] = {
                    'success': True,
                    'data': exif_data
                }
            except Exception as e:
                results[str(asset_id)] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results
    
    async def extract_video_metadata(self, asset_id: UUID, file_path: str) -> Dict[str, Any]:
        """Extract video metadata using FFprobe"""
        try:
            # Check if file format is supported
            if not self.ffprobe_extractor.is_supported_format(file_path):
                raise ExtractionError(f"Unsupported file format for video extraction: {file_path}")
            
            # Extract video metadata
            video_data = await self.ffprobe_extractor.extract_video_metadata(file_path)
            
            # Store in technical metadata
            await self.store_technical_metadata(
                asset_id=asset_id,
                file_info=video_data.get('file_info', {}),
                format_metadata=video_data.get('format', {}),
                streams=video_data.get('streams', []),
                extraction_tool='ffprobe',
                extraction_version='1.0'
            )
            
            logger.info(
                "video_metadata_extracted",
                asset_id=str(asset_id),
                file_path=file_path,
                duration=video_data.get('format', {}).get('duration'),
                streams_count=len(video_data.get('streams', []))
            )
            
            return video_data
            
        except Exception as e:
            logger.error(
                "video_extraction_failed",
                asset_id=str(asset_id),
                file_path=file_path,
                error=str(e)
            )
            raise ExtractionError(f"Video extraction failed: {str(e)}")
    
    async def extract_batch_video(self, extractions: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Extract video metadata from multiple files"""
        results = {}
        
        for extraction in extractions:
            asset_id = extraction['asset_id']
            file_path = extraction['file_path']
            
            try:
                video_data = await self.extract_video_metadata(asset_id, file_path)
                results[str(asset_id)] = {
                    'success': True,
                    'data': video_data
                }
            except Exception as e:
                results[str(asset_id)] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results
    
    async def extract_audio_metadata(self, asset_id: UUID, file_path: str) -> Dict[str, Any]:
        """Extract audio metadata using multiple audio libraries"""
        try:
            # Check if file format is supported
            if not self.audio_extractor.is_supported_format(file_path):
                raise ExtractionError(f"Unsupported file format for audio extraction: {file_path}")
            
            # Extract audio metadata
            audio_data = await self.audio_extractor.extract_audio_metadata(file_path)
            
            # Store in technical metadata
            await self.store_technical_metadata(
                asset_id=asset_id,
                file_info=audio_data.get('file_info', {}),
                format_metadata=audio_data.get('format_info', {}),
                id3_data=audio_data.get('processed_metadata', {}),
                extraction_tool='audio_extractor',
                extraction_version='1.0'
            )
            
            logger.info(
                "audio_metadata_extracted",
                asset_id=str(asset_id),
                file_path=file_path,
                duration=audio_data.get('technical_info', {}).get('duration'),
                has_tags=bool(audio_data.get('processed_metadata', {}))
            )
            
            return audio_data
            
        except Exception as e:
            logger.error(
                "audio_extraction_failed",
                asset_id=str(asset_id),
                file_path=file_path,
                error=str(e)
            )
            raise ExtractionError(f"Audio extraction failed: {str(e)}")
    
    async def extract_batch_audio(self, extractions: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Extract audio metadata from multiple files"""
        results = {}
        
        for extraction in extractions:
            asset_id = extraction['asset_id']
            file_path = extraction['file_path']
            
            try:
                audio_data = await self.extract_audio_metadata(asset_id, file_path)
                results[str(asset_id)] = {
                    'success': True,
                    'data': audio_data
                }
            except Exception as e:
                results[str(asset_id)] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results
    
    async def get_audio_summary(self, asset_id: UUID, file_path: str) -> Dict[str, Any]:
        """Get audio file summary"""
        try:
            summary = await self.audio_extractor.get_audio_summary(file_path)
            summary['asset_id'] = str(asset_id)
            return summary
        except Exception as e:
            logger.error(
                "audio_summary_failed",
                asset_id=str(asset_id),
                file_path=file_path,
                error=str(e)
            )
            raise ExtractionError(f"Audio summary failed: {str(e)}")
    
    async def extract_document_metadata(self, asset_id: UUID, file_path: str) -> Dict[str, Any]:
        """Extract document metadata using document extractor"""
        try:
            # Check if file format is supported
            if not self.document_extractor.is_supported_format(file_path):
                raise ExtractionError(f"Unsupported file format for document extraction: {file_path}")
            
            # Extract document metadata
            document_data = await self.document_extractor.extract_document_metadata(file_path)
            
            # Store in technical metadata
            await self.store_technical_metadata(
                asset_id=asset_id,
                file_info=document_data.get('file_info', {}),
                format_metadata=document_data.get('processed_metadata', {}),
                extraction_tool='document_extractor',
                extraction_version='1.0'
            )
            
            logger.info(
                "document_metadata_extracted",
                asset_id=str(asset_id),
                file_path=file_path,
                page_count=document_data.get('document_info', {}).get('page_count'),
                has_metadata=bool(document_data.get('processed_metadata', {}))
            )
            
            return document_data
            
        except Exception as e:
            logger.error(
                "document_extraction_failed",
                asset_id=str(asset_id),
                file_path=file_path,
                error=str(e)
            )
            raise ExtractionError(f"Document extraction failed: {str(e)}")
    
    async def extract_batch_documents(self, extractions: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Extract document metadata from multiple files"""
        results = {}
        
        for extraction in extractions:
            asset_id = extraction['asset_id']
            file_path = extraction['file_path']
            
            try:
                document_data = await self.extract_document_metadata(asset_id, file_path)
                results[str(asset_id)] = {
                    'success': True,
                    'data': document_data
                }
            except Exception as e:
                results[str(asset_id)] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results
    
    async def get_document_summary(self, asset_id: UUID, file_path: str) -> Dict[str, Any]:
        """Get document file summary"""
        try:
            summary = await self.document_extractor.get_document_summary(file_path)
            summary['asset_id'] = str(asset_id)
            return summary
        except Exception as e:
            logger.error(
                "document_summary_failed",
                asset_id=str(asset_id),
                file_path=file_path,
                error=str(e)
            )
            raise ExtractionError(f"Document summary failed: {str(e)}")
    
    async def find_sidecar_files(self, media_file_path: str) -> List[Dict[str, Any]]:
        """Find sidecar files for a media file"""
        try:
            return await self.sidecar_service.find_sidecar_files(media_file_path)
        except Exception as e:
            logger.error(
                "sidecar_search_failed",
                media_file=media_file_path,
                error=str(e)
            )
            raise ExtractionError(f"Sidecar search failed: {str(e)}")
    
    async def read_sidecar_metadata(self, sidecar_path: str) -> Dict[str, Any]:
        """Read metadata from sidecar file"""
        try:
            return await self.sidecar_service.read_sidecar_file(sidecar_path)
        except Exception as e:
            logger.error(
                "sidecar_read_failed",
                sidecar_path=sidecar_path,
                error=str(e)
            )
            raise ExtractionError(f"Sidecar read failed: {str(e)}")
    
    async def write_sidecar_metadata(self, asset_id: UUID, media_file_path: str, 
                                   metadata: Dict[str, Any], format_type: str = 'json') -> str:
        """Write metadata to sidecar file"""
        try:
            sidecar_path = await self.sidecar_service.write_sidecar_file(
                media_file_path, metadata, format_type
            )
            
            logger.info(
                "sidecar_metadata_written",
                asset_id=str(asset_id),
                media_file=media_file_path,
                sidecar_path=sidecar_path,
                format=format_type
            )
            
            return sidecar_path
            
        except Exception as e:
            logger.error(
                "sidecar_write_failed",
                asset_id=str(asset_id),
                media_file=media_file_path,
                error=str(e)
            )
            raise ExtractionError(f"Sidecar write failed: {str(e)}")
    
    async def sync_sidecar_files(self, asset_id: UUID, media_file_path: str, 
                               metadata: Dict[str, Any]) -> List[str]:
        """Synchronize sidecar files with current metadata"""
        try:
            updated_files = await self.sidecar_service.sync_sidecar_with_metadata(
                media_file_path, metadata
            )
            
            logger.info(
                "sidecar_sync_completed",
                asset_id=str(asset_id),
                media_file=media_file_path,
                updated_count=len(updated_files)
            )
            
            return updated_files
            
        except Exception as e:
            logger.error(
                "sidecar_sync_failed",
                asset_id=str(asset_id),
                media_file=media_file_path,
                error=str(e)
            )
            raise ExtractionError(f"Sidecar sync failed: {str(e)}")
    
    async def validate_sidecar_file(self, sidecar_path: str) -> Dict[str, Any]:
        """Validate a sidecar file"""
        try:
            return await self.sidecar_service.validate_sidecar_file(sidecar_path)
        except Exception as e:
            logger.error(
                "sidecar_validation_failed",
                sidecar_path=sidecar_path,
                error=str(e)
            )
            raise ExtractionError(f"Sidecar validation failed: {str(e)}")
    
    async def extract_sidecar_metadata(self, asset_id: UUID, media_file_path: str) -> Dict[str, Any]:
        """Extract metadata from all sidecar files for a media file"""
        try:
            # Find all sidecar files
            sidecar_files = await self.find_sidecar_files(media_file_path)
            
            if not sidecar_files:
                logger.info(
                    "no_sidecar_files_found",
                    asset_id=str(asset_id),
                    media_file=media_file_path
                )
                return {
                    'sidecar_files': [],
                    'metadata': {},
                    'extraction_info': {
                        'asset_id': str(asset_id),
                        'media_file': media_file_path,
                        'extracted_at': datetime.utcnow().isoformat(),
                        'files_found': 0
                    }
                }
            
            # Read metadata from all sidecar files
            all_metadata = {}
            sidecar_data = []
            
            for sidecar_info in sidecar_files:
                try:
                    sidecar_content = await self.read_sidecar_metadata(sidecar_info['path'])
                    
                    # Store sidecar file info and content
                    sidecar_data.append({
                        'file_info': sidecar_info,
                        'content': sidecar_content,
                        'metadata': sidecar_content.get('metadata', {})
                    })
                    
                    # Merge metadata (later files override earlier ones)
                    if sidecar_content.get('metadata'):
                        all_metadata.update(sidecar_content['metadata'])
                        
                except Exception as e:
                    logger.warning(
                        "sidecar_file_read_failed",
                        sidecar_path=sidecar_info['path'],
                        error=str(e)
                    )
                    sidecar_data.append({
                        'file_info': sidecar_info,
                        'error': str(e)
                    })
            
            # Store in technical metadata if we have content
            if all_metadata:
                await self.store_technical_metadata(
                    asset_id=asset_id,
                    file_info={'media_file': media_file_path},
                    format_metadata=all_metadata,
                    extraction_tool='sidecar_service',
                    extraction_version='1.0'
                )
            
            result = {
                'sidecar_files': sidecar_data,
                'metadata': all_metadata,
                'extraction_info': {
                    'asset_id': str(asset_id),
                    'media_file': media_file_path,
                    'extracted_at': datetime.utcnow().isoformat(),
                    'files_found': len(sidecar_files),
                    'files_processed': len([s for s in sidecar_data if 'content' in s])
                }
            }
            
            logger.info(
                "sidecar_metadata_extracted",
                asset_id=str(asset_id),
                media_file=media_file_path,
                files_found=len(sidecar_files),
                metadata_fields=len(all_metadata)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "sidecar_extraction_failed",
                asset_id=str(asset_id),
                media_file=media_file_path,
                error=str(e)
            )
            raise ExtractionError(f"Sidecar extraction failed: {str(e)}")
    
    async def process_extraction_task(self, task_id: UUID, file_path: str, file_size: int, mime_type: str):
        """Process an extraction task"""
        try:
            # Update task status
            await self.update_task_progress(task_id, 0.0, "processing")
            
            # Get task details
            doc = await self.extraction_tasks.find_one({"task_id": task_id})
            if not doc:
                raise NotFoundError(f"Extraction task {task_id} not found")
            
            task = ExtractionTask(**doc)
            results = {}
            errors = []
            
            # Update task with file information
            await self.extraction_tasks.update_one(
                {"task_id": task_id},
                {"$set": {
                    "file_path": file_path,
                    "file_size": file_size,
                    "mime_type": mime_type
                }}
            )
            
            total_types = len(task.extraction_types)
            
            for i, extraction_type in enumerate(task.extraction_types):
                try:
                    progress = (i / total_types) * 100
                    await self.update_task_progress(task_id, progress)
                    
                    if extraction_type == "exif":
                        if mime_type.startswith('image/'):
                            exif_data = await self.extract_exif_metadata(task.asset_id, file_path)
                            results["exif"] = exif_data
                        else:
                            errors.append({
                                "type": "exif",
                                "error": "EXIF extraction only supported for image files",
                                "file_type": mime_type
                            })
                    
                    elif extraction_type == "technical":
                        if mime_type.startswith('image/'):
                            image_info = await self.extract_basic_image_info(task.asset_id, file_path)
                            results["technical"] = image_info
                        else:
                            errors.append({
                                "type": "technical",
                                "error": "Technical extraction for this file type not yet implemented",
                                "file_type": mime_type
                            })
                    
                    elif extraction_type == "video":
                        if mime_type.startswith('video/') or mime_type.startswith('audio/'):
                            video_data = await self.extract_video_metadata(task.asset_id, file_path)
                            results["video"] = video_data
                        else:
                            errors.append({
                                "type": "video",
                                "error": "Video extraction only supported for video and audio files",
                                "file_type": mime_type
                            })
                    
                    elif extraction_type == "ffprobe":
                        if mime_type.startswith('video/') or mime_type.startswith('audio/'):
                            video_data = await self.extract_video_metadata(task.asset_id, file_path)
                            results["ffprobe"] = video_data
                        else:
                            errors.append({
                                "type": "ffprobe",
                                "error": "FFprobe extraction only supported for video and audio files",
                                "file_type": mime_type
                            })
                    
                    elif extraction_type == "audio":
                        if mime_type.startswith('audio/'):
                            audio_data = await self.extract_audio_metadata(task.asset_id, file_path)
                            results["audio"] = audio_data
                        else:
                            errors.append({
                                "type": "audio",
                                "error": "Audio extraction only supported for audio files",
                                "file_type": mime_type
                            })
                    
                    elif extraction_type == "id3":
                        if mime_type.startswith('audio/'):
                            audio_data = await self.extract_audio_metadata(task.asset_id, file_path)
                            results["id3"] = audio_data
                        else:
                            errors.append({
                                "type": "id3",
                                "error": "ID3 extraction only supported for audio files",
                                "file_type": mime_type
                            })
                    
                    elif extraction_type == "document":
                        if mime_type.startswith('application/') or mime_type.startswith('text/'):
                            document_data = await self.extract_document_metadata(task.asset_id, file_path)
                            results["document"] = document_data
                        else:
                            errors.append({
                                "type": "document",
                                "error": "Document extraction only supported for document files",
                                "file_type": mime_type
                            })
                    
                    elif extraction_type == "pdf":
                        if mime_type == 'application/pdf':
                            document_data = await self.extract_document_metadata(task.asset_id, file_path)
                            results["pdf"] = document_data
                        else:
                            errors.append({
                                "type": "pdf",
                                "error": "PDF extraction only supported for PDF files",
                                "file_type": mime_type
                            })
                    
                    elif extraction_type == "office":
                        if mime_type.startswith('application/vnd.openxmlformats') or mime_type.startswith('application/vnd.ms-'):
                            document_data = await self.extract_document_metadata(task.asset_id, file_path)
                            results["office"] = document_data
                        else:
                            errors.append({
                                "type": "office",
                                "error": "Office extraction only supported for Office document files",
                                "file_type": mime_type
                            })
                    
                    elif extraction_type == "sidecar":
                        sidecar_data = await self.extract_sidecar_metadata(task.asset_id, file_path)
                        results["sidecar"] = sidecar_data
                    
                    elif extraction_type == "xml":
                        sidecar_data = await self.extract_sidecar_metadata(task.asset_id, file_path)
                        results["xml"] = sidecar_data
                    
                    elif extraction_type == "json":
                        sidecar_data = await self.extract_sidecar_metadata(task.asset_id, file_path)
                        results["json"] = sidecar_data
                    
                    else:
                        errors.append({
                            "type": extraction_type,
                            "error": f"Extraction type '{extraction_type}' not yet implemented"
                        })
                        
                except Exception as e:
                    errors.append({
                        "type": extraction_type,
                        "error": str(e)
                    })
                    logger.error(
                        "extraction_type_failed",
                        task_id=str(task_id),
                        extraction_type=extraction_type,
                        error=str(e)
                    )
            
            # Complete the task
            if errors and not results:
                await self.fail_task(task_id, errors)
            else:
                await self.complete_task(task_id, results, errors)
            
        except Exception as e:
            logger.error(
                "extraction_task_processing_failed",
                task_id=str(task_id),
                error=str(e)
            )
            await self.fail_task(task_id, [{"error": str(e)}])
    
    async def _queue_extraction_task(self, task: ExtractionTask):
        """Queue extraction task for background processing"""
        # TODO: Implement message queue integration
        # This would typically send the task to a message queue
        # like RabbitMQ, Redis, or AWS SQS for background processing
        pass
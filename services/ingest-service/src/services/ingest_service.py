"""
Core ingest service for processing file ingestion
"""

import asyncio
import os
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
import structlog

from ..models.schemas import (
    IngestJob, IngestJobCreate, IngestJobUpdate, IngestJobList,
    IngestStats, IngestStatus, BulkIngestRequest, FileMetadata,
    TechnicalMetadata, CameraMetadata, ValidationResult
)
from ..core.config import settings
from ..core.exceptions import (
    IngestServiceError, FileNotFoundError, ValidationError,
    UnsupportedFormatError, FileSizeError
)
from ..core.logging import get_logger, log_ingest_event, log_performance_metric
from .validation_service import ValidationService
from .metadata_service import MetadataService
from .storage_client import StorageClient
from .queue_service import QueueService

logger = get_logger(__name__)


class IngestService:
    """Main service for handling file ingestion"""
    
    def __init__(self):
        self.validation_service = ValidationService()
        self.metadata_service = MetadataService()
        self.storage_client = StorageClient()
        self.queue_service = QueueService()
        self._jobs: Dict[str, IngestJob] = {}
        self._active_jobs = 0
        self._stats = IngestStats()
    
    async def create_job(self, job_request: IngestJobCreate) -> IngestJob:
        """Create a new ingest job"""
        start_time = time.time()
        
        try:
            # Validate source path exists
            if not os.path.exists(job_request.source_path):
                raise FileNotFoundError(job_request.source_path)
            
            # Create job instance
            job = IngestJob(
                source_path=job_request.source_path,
                destination_project_id=job_request.destination_project_id,
                ingest_type=job_request.ingest_type,
                validation_rules=job_request.validation_rules,
                metadata_override=job_request.metadata_override,
                tags=job_request.tags,
                priority=job_request.priority,
                auto_generate_proxies=job_request.auto_generate_proxies,
                preserve_folder_structure=job_request.preserve_folder_structure
            )
            
            # Calculate total files and size
            if os.path.isfile(job_request.source_path):
                job.total_files = 1
                job.total_size = os.path.getsize(job_request.source_path)
            else:
                job.total_files, job.total_size = await self._calculate_directory_stats(
                    job_request.source_path
                )
            
            # Store job
            self._jobs[job.id] = job
            
            # Queue for processing
            await self.queue_service.publish_ingest_job(job)
            
            log_ingest_event(
                logger,
                "ingest_job_created",
                job.source_path,
                job_id=job.id,
                total_files=job.total_files,
                total_size=job.total_size
            )
            
            duration_ms = (time.time() - start_time) * 1000
            log_performance_metric(
                logger,
                "create_ingest_job",
                duration_ms,
                job_id=job.id
            )
            
            return job
            
        except Exception as e:
            logger.error(
                "failed_to_create_ingest_job",
                error=str(e),
                source_path=job_request.source_path
            )
            raise IngestServiceError(f"Failed to create ingest job: {str(e)}")
    
    async def process_job(self, job_id: str) -> None:
        """Process an ingest job"""
        if job_id not in self._jobs:
            raise IngestServiceError(f"Job {job_id} not found")
        
        job = self._jobs[job_id]
        start_time = time.time()
        
        try:
            self._active_jobs += 1
            job.status = IngestStatus.PROCESSING
            job.started_at = datetime.utcnow()
            job.current_operation = "Starting processing"
            
            log_ingest_event(
                logger,
                "ingest_job_started",
                job.source_path,
                job_id=job_id
            )
            
            # Step 1: Validation
            await self._validate_job(job)
            
            # Step 2: Extract metadata
            await self._extract_metadata(job)
            
            # Step 3: Process files
            if os.path.isfile(job.source_path):
                await self._process_single_file(job)
            else:
                await self._process_directory(job)
            
            # Step 4: Generate proxies if requested
            if job.auto_generate_proxies:
                await self._generate_proxies(job)
            
            # Mark as completed
            job.status = IngestStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.progress_percentage = 100.0
            job.current_operation = "Completed"
            
            self._stats.completed_jobs += 1
            
            log_ingest_event(
                logger,
                "ingest_job_completed",
                job.source_path,
                job_id=job_id,
                processed_files=job.processed_files,
                duration_seconds=(time.time() - start_time)
            )
            
        except Exception as e:
            job.status = IngestStatus.FAILED
            job.errors.append(str(e))
            job.completed_at = datetime.utcnow()
            job.current_operation = f"Failed: {str(e)}"
            
            self._stats.failed_jobs += 1
            
            logger.error(
                "ingest_job_failed",
                error=str(e),
                job_id=job_id,
                source_path=job.source_path
            )
            
        finally:
            self._active_jobs -= 1
            duration_ms = (time.time() - start_time) * 1000
            log_performance_metric(
                logger,
                "process_ingest_job",
                duration_ms,
                job_id=job_id,
                status=job.status.value
            )
    
    async def _validate_job(self, job: IngestJob) -> None:
        """Validate files in the job"""
        job.status = IngestStatus.VALIDATING
        job.current_operation = "Validating files"
        job.progress_percentage = 10.0
        
        if os.path.isfile(job.source_path):
            validation_result = await self.validation_service.validate_file(
                job.source_path,
                job.validation_rules
            )
            job.validation_results.append(validation_result)
            
            if not validation_result.is_valid:
                raise ValidationError(
                    f"File validation failed: {', '.join(validation_result.errors)}"
                )
        else:
            # Validate directory contents
            valid_files = 0
            total_files = 0
            
            for root, _, files in os.walk(job.source_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_files += 1
                    
                    try:
                        validation_result = await self.validation_service.validate_file(
                            file_path,
                            job.validation_rules
                        )
                        job.validation_results.append(validation_result)
                        
                        if validation_result.is_valid:
                            valid_files += 1
                        else:
                            job.warnings.extend(validation_result.errors)
                            
                    except Exception as e:
                        job.warnings.append(f"Failed to validate {file_path}: {str(e)}")
            
            if valid_files == 0:
                raise ValidationError("No valid files found in directory")
            
            logger.info(
                "directory_validation_completed",
                job_id=job.id,
                total_files=total_files,
                valid_files=valid_files
            )
    
    async def _extract_metadata(self, job: IngestJob) -> None:
        """Extract metadata from files"""
        job.status = IngestStatus.EXTRACTING_METADATA
        job.current_operation = "Extracting metadata"
        job.progress_percentage = 30.0
        
        try:
            if os.path.isfile(job.source_path):
                # Extract metadata for single file
                file_metadata = await self.metadata_service.extract_file_metadata(
                    job.source_path
                )
                job.file_metadata = file_metadata
                
                # Extract technical metadata for media files
                if file_metadata.file_type in ["video", "audio", "image"]:
                    technical_metadata = await self.metadata_service.extract_technical_metadata(
                        job.source_path
                    )
                    job.technical_metadata = technical_metadata
                    
                    # Extract camera metadata if available
                    camera_metadata = await self.metadata_service.extract_camera_metadata(
                        job.source_path
                    )
                    if camera_metadata:
                        job.camera_metadata = camera_metadata
            else:
                # For directories, extract metadata for each file
                # This would be more complex and handle multiple files
                pass
                
        except Exception as e:
            # Metadata extraction failure is not critical
            job.warnings.append(f"Metadata extraction failed: {str(e)}")
            logger.warning(
                "metadata_extraction_failed",
                job_id=job.id,
                error=str(e)
            )
    
    async def _process_single_file(self, job: IngestJob) -> None:
        """Process a single file"""
        job.current_operation = "Processing file"
        job.progress_percentage = 50.0
        
        try:
            # Upload file to storage
            asset_id = await self.storage_client.upload_file(
                job.source_path,
                job.destination_project_id,
                metadata=job.metadata_override,
                tags=job.tags
            )
            
            job.created_assets.append(asset_id)
            job.processed_files = 1
            job.processed_size = job.total_size
            job.progress_percentage = 80.0
            
            logger.info(
                "file_processed",
                job_id=job.id,
                asset_id=asset_id,
                file_path=job.source_path
            )
            
        except Exception as e:
            job.failed_files += 1
            job.errors.append(f"Failed to process file: {str(e)}")
            raise
    
    async def _process_directory(self, job: IngestJob) -> None:
        """Process all files in a directory"""
        job.current_operation = "Processing directory"
        processed = 0
        
        for root, _, files in os.walk(job.source_path):
            for file in files:
                file_path = os.path.join(root, file)
                
                try:
                    # Check if file passed validation
                    file_valid = any(
                        vr.is_valid for vr in job.validation_results
                        if file_path in str(vr)  # This would need proper matching
                    )
                    
                    if not file_valid:
                        continue
                    
                    # Upload file
                    asset_id = await self.storage_client.upload_file(
                        file_path,
                        job.destination_project_id,
                        metadata=job.metadata_override,
                        tags=job.tags
                    )
                    
                    job.created_assets.append(asset_id)
                    processed += 1
                    job.processed_files = processed
                    
                    # Update progress
                    progress = 50.0 + (processed / job.total_files) * 30.0
                    job.progress_percentage = min(progress, 80.0)
                    
                except Exception as e:
                    job.failed_files += 1
                    job.errors.append(f"Failed to process {file_path}: {str(e)}")
                    logger.error(
                        "file_processing_failed",
                        job_id=job.id,
                        file_path=file_path,
                        error=str(e)
                    )
    
    async def _generate_proxies(self, job: IngestJob) -> None:
        """Generate proxies for processed assets"""
        if not job.created_assets:
            return
        
        job.current_operation = "Generating proxies"
        job.progress_percentage = 90.0
        
        try:
            # Send proxy generation requests for each asset
            for asset_id in job.created_assets:
                await self.queue_service.publish_proxy_request(
                    asset_id=asset_id,
                    job_id=job.id
                )
            
            logger.info(
                "proxy_generation_requested",
                job_id=job.id,
                asset_count=len(job.created_assets)
            )
            
        except Exception as e:
            job.warnings.append(f"Failed to request proxy generation: {str(e)}")
            logger.warning(
                "proxy_generation_request_failed",
                job_id=job.id,
                error=str(e)
            )
    
    async def _calculate_directory_stats(self, directory_path: str) -> tuple[int, int]:
        """Calculate total files and size in a directory"""
        total_files = 0
        total_size = 0
        
        for root, _, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_files += 1
                    total_size += os.path.getsize(file_path)
                except OSError:
                    # Skip files we can't access
                    pass
        
        return total_files, total_size
    
    async def get_job(self, job_id: str) -> Optional[IngestJob]:
        """Get a job by ID"""
        return self._jobs.get(job_id)
    
    async def list_jobs(
        self,
        page: int = 1,
        per_page: int = 20,
        status: Optional[IngestStatus] = None
    ) -> IngestJobList:
        """List jobs with pagination and filtering"""
        jobs = list(self._jobs.values())
        
        if status:
            jobs = [job for job in jobs if job.status == status]
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        # Paginate
        total = len(jobs)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_jobs = jobs[start:end]
        
        total_pages = (total + per_page - 1) // per_page
        
        return IngestJobList(
            jobs=paginated_jobs,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
    
    async def update_job(
        self,
        job_id: str,
        job_update: IngestJobUpdate
    ) -> Optional[IngestJob]:
        """Update a job"""
        if job_id not in self._jobs:
            return None
        
        job = self._jobs[job_id]
        
        if job_update.status:
            job.status = job_update.status
        if job_update.progress_percentage is not None:
            job.progress_percentage = job_update.progress_percentage
        if job_update.current_operation:
            job.current_operation = job_update.current_operation
        if job_update.error_message:
            job.errors.append(job_update.error_message)
        if job_update.metadata:
            job.metadata_override.update(job_update.metadata)
        
        job.updated_at = datetime.utcnow()
        
        return job
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        if job_id not in self._jobs:
            return False
        
        job = self._jobs[job_id]
        
        if job.status in [IngestStatus.COMPLETED, IngestStatus.FAILED, IngestStatus.CANCELLED]:
            return False
        
        job.status = IngestStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        job.current_operation = "Cancelled"
        
        return True
    
    async def create_bulk_jobs(self, bulk_request: BulkIngestRequest) -> List[IngestJob]:
        """Create multiple jobs from bulk request"""
        jobs = []
        
        for source_path in bulk_request.source_paths:
            job_request = IngestJobCreate(
                source_path=source_path,
                destination_project_id=bulk_request.destination_project_id,
                validation_rules=bulk_request.validation_rules,
                metadata_override=bulk_request.metadata_template,
                tags=bulk_request.tags,
                auto_generate_proxies=bulk_request.auto_generate_proxies,
                preserve_folder_structure=bulk_request.preserve_folder_structure
            )
            
            try:
                job = await self.create_job(job_request)
                jobs.append(job)
            except Exception as e:
                logger.error(
                    "bulk_job_creation_failed",
                    source_path=source_path,
                    error=str(e)
                )
        
        return jobs
    
    async def get_stats(self) -> IngestStats:
        """Get service statistics"""
        self._stats.total_jobs = len(self._jobs)
        self._stats.active_jobs = self._active_jobs
        
        # Calculate other stats from jobs
        completed_jobs = [job for job in self._jobs.values() if job.status == IngestStatus.COMPLETED]
        failed_jobs = [job for job in self._jobs.values() if job.status == IngestStatus.FAILED]
        
        self._stats.completed_jobs = len(completed_jobs)
        self._stats.failed_jobs = len(failed_jobs)
        
        if completed_jobs:
            total_processing_time = sum(
                (job.completed_at - job.started_at).total_seconds()
                for job in completed_jobs
                if job.started_at and job.completed_at
            )
            self._stats.average_processing_time = total_processing_time / len(completed_jobs)
        
        if self._stats.total_jobs > 0:
            self._stats.success_rate = self._stats.completed_jobs / self._stats.total_jobs
        
        return self._stats


# Dependency injection
_ingest_service: Optional[IngestService] = None


async def get_ingest_service() -> IngestService:
    """Get ingest service instance"""
    global _ingest_service
    
    if _ingest_service is None:
        _ingest_service = IngestService()
    
    return _ingest_service
"""
Export Service for managing export jobs and coordinating exporters
"""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.schemas import (
    NLEExportRequest, ExportJobStatus, ExportResult, 
    JobStatus, ExportStatus, User, ValidationResult,
    TimelineExportRequest, ExportFormat
)
from ..exporters.aaf_exporter import AAFExporter
from ..exporters.xml_exporter import XMLExporter
from ..exporters.edl_exporter import EDLExporter
from ..exporters.otio_exporter import OTIOExporter
from ..exporters.omf_exporter import OMFExporter
from ..core.config import settings
from ..core.logger import get_logger
from ..core.exceptions import ExportError

logger = get_logger(__name__)


class ExportService:
    """Service for managing export jobs"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.export_jobs: Dict[str, ExportJobStatus] = {}
        self.exporters = {
            ExportFormat.AAF: AAFExporter,
            ExportFormat.XML: XMLExporter,
            ExportFormat.EDL: EDLExporter,
            ExportFormat.CMX: EDLExporter,  # Uses EDL exporter with CMX method
            ExportFormat.OTIO: OTIOExporter,
            ExportFormat.OMF: OMFExporter,
        }
        
    async def start_export_job(self, request: NLEExportRequest, user: User) -> str:
        """Start a new export job"""
        job_id = str(uuid.uuid4())
        
        # Create job status
        job_status = ExportJobStatus(
            job_id=job_id,
            timeline_id=request.timeline_id,
            format=request.format.value,
            status=JobStatus.QUEUED,
            progress=0.0,
            created_at=datetime.utcnow()
        )
        
        # Store job
        self.export_jobs[job_id] = job_status
        
        logger.info(f"Started export job {job_id} for timeline {request.timeline_id}")
        
        return job_id
        
    async def process_export_job(self, job_id: str, request: NLEExportRequest, user: User):
        """Process an export job in the background"""
        try:
            # Update job status
            job = self.export_jobs.get(job_id)
            if not job:
                logger.error(f"Export job {job_id} not found")
                return
            
            job.status = JobStatus.STARTED
            job.started_at = datetime.utcnow()
            job.progress = 10.0
            
            logger.info(f"Processing export job {job_id}")
            
            # Create timeline export request
            timeline_request = TimelineExportRequest(
                timeline_id=request.timeline_id,
                format=request.format,
                include_media=request.include_media,
                include_effects=request.include_effects,
                include_audio=request.include_audio
            )
            
            # Get appropriate exporter
            exporter_class = self.exporters.get(request.format)
            if not exporter_class:
                raise ExportError(f"Unsupported export format: {request.format}")
            
            # Create exporter instance
            exporter = exporter_class(self.db)
            
            # Update progress
            job.status = JobStatus.PROCESSING
            job.progress = 30.0
            
            # Perform export
            if request.format == ExportFormat.CMX:
                # Special handling for CMX EDL
                result = await exporter.export_cmx_edl(timeline_request)
            else:
                result = await exporter.export_timeline(timeline_request)
            
            # Update progress
            job.progress = 90.0
            
            # Validate export if needed
            if hasattr(exporter, 'validate_export'):
                is_valid = await exporter.validate_export(Path(result.file_path))
                if not is_valid:
                    logger.warning(f"Export validation failed for job {job_id}")
            
            # Complete job
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.progress = 100.0
            job.result = result
            
            logger.info(f"Export job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Export job {job_id} failed: {str(e)}")
            
            # Update job with error
            job = self.export_jobs.get(job_id)
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
    
    async def get_export_job_status(self, job_id: str, user: User) -> Optional[ExportJobStatus]:
        """Get export job status"""
        return self.export_jobs.get(job_id)
    
    async def get_export_jobs(
        self, 
        user: User, 
        limit: int = 20, 
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[ExportJobStatus]:
        """Get export jobs for a user"""
        jobs = list(self.export_jobs.values())
        
        # Filter by status if provided
        if status_filter:
            jobs = [job for job in jobs if job.status.value == status_filter]
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        # Apply pagination
        return jobs[offset:offset + limit]
    
    async def cancel_export_job(self, job_id: str, user: User) -> bool:
        """Cancel an export job"""
        job = self.export_jobs.get(job_id)
        if not job:
            return False
        
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return False
        
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        job.error_message = "Job cancelled by user"
        
        logger.info(f"Export job {job_id} cancelled")
        
        return True
    
    async def validate_export_file(self, export_id: str, user: User) -> Optional[ValidationResult]:
        """Validate an export file"""
        try:
            # Find the export job
            job = None
            for j in self.export_jobs.values():
                if j.result and j.result.export_id == export_id:
                    job = j
                    break
            
            if not job or not job.result:
                return None
            
            export_path = Path(job.result.file_path)
            
            # Get appropriate exporter for validation
            format_enum = ExportFormat(job.result.format)
            exporter_class = self.exporters.get(format_enum)
            
            if not exporter_class:
                return ValidationResult(
                    is_valid=False,
                    format=job.result.format,
                    errors=[f"Unsupported format for validation: {job.result.format}"]
                )
            
            # Create exporter and validate
            exporter = exporter_class(self.db)
            
            if hasattr(exporter, 'validate_export'):
                is_valid = await exporter.validate_export(export_path)
                
                return ValidationResult(
                    is_valid=is_valid,
                    format=job.result.format,
                    errors=[] if is_valid else ["Validation failed"],
                    metadata={
                        "file_path": str(export_path),
                        "file_size": export_path.stat().st_size if export_path.exists() else 0,
                        "created_at": job.result.created_at.isoformat()
                    }
                )
            else:
                return ValidationResult(
                    is_valid=True,
                    format=job.result.format,
                    warnings=["Validation not implemented for this format"],
                    metadata={
                        "file_path": str(export_path),
                        "file_size": export_path.stat().st_size if export_path.exists() else 0
                    }
                )
                
        except Exception as e:
            logger.error(f"Export validation failed: {str(e)}")
            return ValidationResult(
                is_valid=False,
                format="unknown",
                errors=[f"Validation error: {str(e)}"]
            )
    
    async def get_export_formats(self) -> List[Dict[str, Any]]:
        """Get available export formats"""
        return [
            {
                "format": "aaf",
                "name": "AAF (Advanced Authoring Format)",
                "description": "For Avid Media Composer",
                "nle_compatibility": ["avid"],
                "supports_audio": True,
                "supports_video": True,
                "supports_effects": True,
                "file_extension": ".aaf",
                "capabilities": {
                    "max_video_tracks": 24,
                    "max_audio_tracks": 64,
                    "supports_nested_sequences": True,
                    "supports_timecode": True,
                    "supports_metadata": True
                }
            },
            {
                "format": "xml",
                "name": "FCP7 XML",
                "description": "For Adobe Premiere Pro",
                "nle_compatibility": ["premiere", "fcpx"],
                "supports_audio": True,
                "supports_video": True,
                "supports_effects": False,
                "file_extension": ".xml",
                "capabilities": {
                    "max_video_tracks": 99,
                    "max_audio_tracks": 99,
                    "supports_nested_sequences": False,
                    "supports_timecode": True,
                    "supports_metadata": True
                }
            },
            {
                "format": "edl",
                "name": "EDL (Edit Decision List)",
                "description": "Traditional edit decision list",
                "nle_compatibility": ["avid", "premiere", "resolve"],
                "supports_audio": True,
                "supports_video": True,
                "supports_effects": False,
                "file_extension": ".edl",
                "capabilities": {
                    "max_video_tracks": 4,
                    "max_audio_tracks": 8,
                    "supports_nested_sequences": False,
                    "supports_timecode": True,
                    "supports_metadata": False
                }
            },
            {
                "format": "cmx",
                "name": "CMX EDL",
                "description": "CMX format edit decision list",
                "nle_compatibility": ["avid", "premiere", "resolve"],
                "supports_audio": False,
                "supports_video": True,
                "supports_effects": False,
                "file_extension": ".edl",
                "capabilities": {
                    "max_video_tracks": 1,
                    "max_audio_tracks": 0,
                    "supports_nested_sequences": False,
                    "supports_timecode": True,
                    "supports_metadata": False
                }
            }
        ]
    
    async def get_nle_presets(self, nle_type: str) -> List[Dict[str, Any]]:
        """Get presets for specific NLE"""
        presets = {
            "avid": [
                {
                    "name": "Avid Standard",
                    "format": "aaf",
                    "settings": {
                        "include_media": True,
                        "include_effects": True,
                        "include_audio": True,
                        "frame_rate": 25.0,
                        "resolution": "1920x1080"
                    }
                },
                {
                    "name": "Avid Offline",
                    "format": "aaf",
                    "settings": {
                        "include_media": False,
                        "include_effects": True,
                        "include_audio": True,
                        "frame_rate": 25.0,
                        "resolution": "1920x1080"
                    }
                }
            ],
            "premiere": [
                {
                    "name": "Premiere Standard",
                    "format": "xml",
                    "settings": {
                        "include_media": True,
                        "include_effects": False,
                        "include_audio": True,
                        "frame_rate": 25.0,
                        "resolution": "1920x1080"
                    }
                },
                {
                    "name": "Premiere EDL",
                    "format": "edl",
                    "settings": {
                        "include_media": False,
                        "include_effects": False,
                        "include_audio": True,
                        "frame_rate": 25.0
                    }
                }
            ],
            "resolve": [
                {
                    "name": "Resolve EDL",
                    "format": "edl",
                    "settings": {
                        "include_media": False,
                        "include_effects": False,
                        "include_audio": True,
                        "frame_rate": 25.0
                    }
                },
                {
                    "name": "Resolve CMX",
                    "format": "cmx",
                    "settings": {
                        "include_media": False,
                        "include_effects": False,
                        "include_audio": False,
                        "frame_rate": 25.0
                    }
                }
            ]
        }
        
        return presets.get(nle_type.lower(), [])
    
    async def cleanup_old_exports(self, days_old: int = 30):
        """Clean up old export files and jobs"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        jobs_to_remove = []
        for job_id, job in self.export_jobs.items():
            if job.created_at < cutoff_date:
                # Remove export file if it exists
                if job.result and job.result.file_path:
                    try:
                        export_path = Path(job.result.file_path)
                        if export_path.exists():
                            export_path.unlink()
                            logger.info(f"Removed old export file: {export_path}")
                    except Exception as e:
                        logger.error(f"Failed to remove export file: {str(e)}")
                
                jobs_to_remove.append(job_id)
        
        # Remove jobs from memory
        for job_id in jobs_to_remove:
            del self.export_jobs[job_id]
            logger.info(f"Removed old export job: {job_id}")
        
        logger.info(f"Cleaned up {len(jobs_to_remove)} old export jobs")
    
    async def get_export_statistics(self) -> Dict[str, Any]:
        """Get export statistics"""
        total_jobs = len(self.export_jobs)
        completed_jobs = sum(1 for job in self.export_jobs.values() if job.status == JobStatus.COMPLETED)
        failed_jobs = sum(1 for job in self.export_jobs.values() if job.status == JobStatus.FAILED)
        
        # Format breakdown
        formats = {}
        for job in self.export_jobs.values():
            format_name = job.format
            formats[format_name] = formats.get(format_name, 0) + 1
        
        # Calculate average duration
        durations = []
        for job in self.export_jobs.values():
            if job.started_at and job.completed_at:
                duration = (job.completed_at - job.started_at).total_seconds()
                durations.append(duration)
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "total_exports": total_jobs,
            "completed_exports": completed_jobs,
            "failed_exports": failed_jobs,
            "success_rate": (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0,
            "formats_breakdown": formats,
            "average_duration_seconds": avg_duration,
            "total_duration_seconds": sum(durations)
        }
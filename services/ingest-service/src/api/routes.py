"""
API routes for the Ingest Service
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks, Request
from typing import List, Optional
import structlog

from ..models.schemas import (
    IngestJob, IngestJobCreate, IngestJobUpdate, IngestJobList,
    IngestStats, WatchFolderConfig, HotFolderConfig, ScheduledIngestConfig,
    BulkIngestRequest, ValidationResult, IngestStatus, CameraCardInfo,
    CameraCardType
)
from ..services.ingest_service import IngestService, get_ingest_service
from ..services.validation_service import ValidationService, get_validation_service
from ..services.watch_folder_service import WatchFolderService, get_watch_folder_service
from ..services.hot_folder_service import HotFolderService, get_hot_folder_service
from ..services.camera_card_service import CameraCardService, get_camera_card_service
from ..services.scheduler_service import SchedulerService, get_scheduler_service
from ..services.live_ingest_service import LiveIngestService, get_live_ingest_service
from ..services.edit_while_ingest_service import EditWhileIngestService, get_edit_while_ingest_service
from ..services.streaming_protocol_service import StreamingProtocolService, get_streaming_protocol_service
from ..services.realtime_proxy_service import RealtimeProxyService, get_realtime_proxy_service, ProxyQuality
from ..core.exceptions import IngestServiceError, ValidationError, FileNotFoundError
from ..core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/jobs", response_model=IngestJob)
async def create_ingest_job(
    job_request: IngestJobCreate,
    background_tasks: BackgroundTasks,
    ingest_service: IngestService = Depends(get_ingest_service)
) -> IngestJob:
    """
    Create a new ingest job
    
    - **source_path**: Path to the file or directory to ingest
    - **destination_project_id**: Target project ID (optional)
    - **ingest_type**: Type of ingest operation
    - **validation_rules**: Custom validation rules
    - **metadata_override**: Additional metadata to apply
    """
    try:
        logger.info(
            "creating_ingest_job",
            source_path=job_request.source_path,
            ingest_type=job_request.ingest_type,
            destination_project_id=job_request.destination_project_id
        )
        
        job = await ingest_service.create_job(job_request)
        
        # Start processing in the background
        background_tasks.add_task(
            ingest_service.process_job,
            job.id
        )
        
        logger.info(
            "ingest_job_created",
            job_id=job.id,
            source_path=job_request.source_path
        )
        
        return job
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("failed_to_create_ingest_job", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create ingest job")


@router.get("/jobs", response_model=IngestJobList)
async def list_ingest_jobs(
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: Optional[IngestStatus] = Query(default=None, description="Filter by status"),
    ingest_service: IngestService = Depends(get_ingest_service)
) -> IngestJobList:
    """
    List ingest jobs with pagination and filtering
    """
    try:
        return await ingest_service.list_jobs(
            page=page,
            per_page=per_page,
            status=status
        )
    except Exception as e:
        logger.error("failed_to_list_ingest_jobs", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list ingest jobs")


@router.get("/jobs/{job_id}", response_model=IngestJob)
async def get_ingest_job(
    job_id: str = Path(..., description="Ingest job ID"),
    ingest_service: IngestService = Depends(get_ingest_service)
) -> IngestJob:
    """
    Get a specific ingest job by ID
    """
    try:
        job = await ingest_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Ingest job not found")
        return job
    except Exception as e:
        logger.error("failed_to_get_ingest_job", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to get ingest job")


@router.put("/jobs/{job_id}", response_model=IngestJob)
async def update_ingest_job(
    job_id: str = Path(..., description="Ingest job ID"),
    job_update: IngestJobUpdate = ...,
    ingest_service: IngestService = Depends(get_ingest_service)
) -> IngestJob:
    """
    Update an ingest job
    """
    try:
        job = await ingest_service.update_job(job_id, job_update)
        if not job:
            raise HTTPException(status_code=404, detail="Ingest job not found")
        
        logger.info(
            "ingest_job_updated",
            job_id=job_id,
            status=job_update.status
        )
        
        return job
    except Exception as e:
        logger.error("failed_to_update_ingest_job", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to update ingest job")


@router.delete("/jobs/{job_id}")
async def cancel_ingest_job(
    job_id: str = Path(..., description="Ingest job ID"),
    ingest_service: IngestService = Depends(get_ingest_service)
):
    """
    Cancel an ingest job
    """
    try:
        success = await ingest_service.cancel_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Ingest job not found")
        
        logger.info("ingest_job_cancelled", job_id=job_id)
        
        return {"message": "Ingest job cancelled successfully"}
    except Exception as e:
        logger.error("failed_to_cancel_ingest_job", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to cancel ingest job")


@router.post("/jobs/bulk", response_model=List[IngestJob])
async def create_bulk_ingest_jobs(
    bulk_request: BulkIngestRequest,
    background_tasks: BackgroundTasks,
    ingest_service: IngestService = Depends(get_ingest_service)
) -> List[IngestJob]:
    """
    Create multiple ingest jobs from a list of source paths
    """
    try:
        jobs = await ingest_service.create_bulk_jobs(bulk_request)
        
        # Start processing jobs in the background
        for job in jobs:
            background_tasks.add_task(
                ingest_service.process_job,
                job.id
            )
        
        logger.info(
            "bulk_ingest_jobs_created",
            job_count=len(jobs),
            source_count=len(bulk_request.source_paths)
        )
        
        return jobs
        
    except Exception as e:
        logger.error("failed_to_create_bulk_ingest_jobs", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create bulk ingest jobs")


@router.post("/validate", response_model=ValidationResult)
async def validate_file(
    file_path: str = Query(..., description="Path to file to validate"),
    validation_service: ValidationService = Depends(get_validation_service)
) -> ValidationResult:
    """
    Validate a file without ingesting it
    """
    try:
        result = await validation_service.validate_file(file_path)
        
        logger.info(
            "file_validation_completed",
            file_path=file_path,
            is_valid=result.is_valid,
            errors=len(result.errors),
            warnings=len(result.warnings)
        )
        
        return result
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("failed_to_validate_file", error=str(e), file_path=file_path)
        raise HTTPException(status_code=500, detail="Failed to validate file")


@router.get("/stats", response_model=IngestStats)
async def get_ingest_stats(
    ingest_service: IngestService = Depends(get_ingest_service)
) -> IngestStats:
    """
    Get ingest service statistics
    """
    try:
        return await ingest_service.get_stats()
    except Exception as e:
        logger.error("failed_to_get_ingest_stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get ingest statistics")


# Watch Folder Management
@router.post("/watch-folders", response_model=WatchFolderConfig)
async def create_watch_folder(
    config: WatchFolderConfig,
    watch_folder_service: WatchFolderService = Depends(get_watch_folder_service)
) -> WatchFolderConfig:
    """
    Create a new watch folder configuration
    """
    try:
        created_config = await watch_folder_service.create_watch_folder(config)
        
        logger.info(
            "watch_folder_created",
            watch_folder_id=created_config.id,
            path=created_config.path
        )
        
        return created_config
    except Exception as e:
        logger.error("failed_to_create_watch_folder", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create watch folder")


@router.get("/watch-folders", response_model=List[WatchFolderConfig])
async def list_watch_folders(
    watch_folder_service: WatchFolderService = Depends(get_watch_folder_service)
) -> List[WatchFolderConfig]:
    """
    List all watch folder configurations
    """
    try:
        return await watch_folder_service.list_watch_folders()
    except Exception as e:
        logger.error("failed_to_list_watch_folders", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list watch folders")


@router.get("/watch-folders/{folder_id}", response_model=WatchFolderConfig)
async def get_watch_folder(
    folder_id: str = Path(..., description="Watch folder ID"),
    watch_folder_service: WatchFolderService = Depends(get_watch_folder_service)
) -> WatchFolderConfig:
    """
    Get a specific watch folder configuration
    """
    try:
        config = await watch_folder_service.get_watch_folder(folder_id)
        if not config:
            raise HTTPException(status_code=404, detail="Watch folder not found")
        return config
    except Exception as e:
        logger.error("failed_to_get_watch_folder", error=str(e), folder_id=folder_id)
        raise HTTPException(status_code=500, detail="Failed to get watch folder")


@router.put("/watch-folders/{folder_id}", response_model=WatchFolderConfig)
async def update_watch_folder(
    folder_id: str = Path(..., description="Watch folder ID"),
    config: WatchFolderConfig = ...,
    watch_folder_service: WatchFolderService = Depends(get_watch_folder_service)
) -> WatchFolderConfig:
    """
    Update a watch folder configuration
    """
    try:
        updated_config = await watch_folder_service.update_watch_folder(folder_id, config)
        if not updated_config:
            raise HTTPException(status_code=404, detail="Watch folder not found")
        
        logger.info(
            "watch_folder_updated",
            watch_folder_id=folder_id,
            enabled=updated_config.enabled
        )
        
        return updated_config
    except Exception as e:
        logger.error("failed_to_update_watch_folder", error=str(e), folder_id=folder_id)
        raise HTTPException(status_code=500, detail="Failed to update watch folder")


@router.delete("/watch-folders/{folder_id}")
async def delete_watch_folder(
    folder_id: str = Path(..., description="Watch folder ID"),
    watch_folder_service: WatchFolderService = Depends(get_watch_folder_service)
):
    """
    Delete a watch folder configuration
    """
    try:
        success = await watch_folder_service.delete_watch_folder(folder_id)
        if not success:
            raise HTTPException(status_code=404, detail="Watch folder not found")
        
        logger.info("watch_folder_deleted", watch_folder_id=folder_id)
        
        return {"message": "Watch folder deleted successfully"}
    except Exception as e:
        logger.error("failed_to_delete_watch_folder", error=str(e), folder_id=folder_id)
        raise HTTPException(status_code=500, detail="Failed to delete watch folder")


# Scheduled Ingest Management
@router.post("/scheduled-ingests", response_model=ScheduledIngestConfig)
async def create_scheduled_ingest(
    config: ScheduledIngestConfig,
    scheduler_service: SchedulerService = Depends(get_scheduler_service)
) -> ScheduledIngestConfig:
    """
    Create a new scheduled ingest configuration
    """
    try:
        created_config = await scheduler_service.create_scheduled_ingest(config)
        
        logger.info(
            "scheduled_ingest_created",
            scheduled_ingest_id=created_config.id,
            cron_expression=created_config.cron_expression
        )
        
        return created_config
    except Exception as e:
        logger.error("failed_to_create_scheduled_ingest", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create scheduled ingest")


@router.get("/scheduled-ingests", response_model=List[ScheduledIngestConfig])
async def list_scheduled_ingests(
    scheduler_service: SchedulerService = Depends(get_scheduler_service)
) -> List[ScheduledIngestConfig]:
    """
    List all scheduled ingest configurations
    """
    try:
        return await scheduler_service.list_scheduled_ingests()
    except Exception as e:
        logger.error("failed_to_list_scheduled_ingests", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list scheduled ingests")


@router.post("/scheduled-ingests/{ingest_id}/run")
async def run_scheduled_ingest(
    ingest_id: str = Path(..., description="Scheduled ingest ID"),
    background_tasks: BackgroundTasks = ...,
    scheduler_service: SchedulerService = Depends(get_scheduler_service)
):
    """
    Manually trigger a scheduled ingest
    """
    try:
        success = await scheduler_service.run_scheduled_ingest(ingest_id, background_tasks)
        if not success:
            raise HTTPException(status_code=404, detail="Scheduled ingest not found")
        
        logger.info("scheduled_ingest_triggered", ingest_id=ingest_id)
        
        return {"message": "Scheduled ingest triggered successfully"}
    except Exception as e:
        logger.error("failed_to_run_scheduled_ingest", error=str(e), ingest_id=ingest_id)
        raise HTTPException(status_code=500, detail="Failed to run scheduled ingest")


# Hot Folder Management
@router.post("/hot-folders", response_model=HotFolderConfig)
async def create_hot_folder(
    config: HotFolderConfig,
    hot_folder_service: HotFolderService = Depends(get_hot_folder_service)
) -> HotFolderConfig:
    """
    Create a new hot folder configuration for immediate processing
    """
    try:
        created_config = await hot_folder_service.create_hot_folder(config)
        
        logger.info(
            "hot_folder_created",
            hot_folder_id=created_config.id,
            path=created_config.path,
            immediate_processing=created_config.immediate_processing
        )
        
        return created_config
    except Exception as e:
        logger.error("failed_to_create_hot_folder", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create hot folder")


@router.get("/hot-folders", response_model=List[HotFolderConfig])
async def list_hot_folders(
    hot_folder_service: HotFolderService = Depends(get_hot_folder_service)
) -> List[HotFolderConfig]:
    """
    List all hot folder configurations
    """
    try:
        return await hot_folder_service.list_hot_folders()
    except Exception as e:
        logger.error("failed_to_list_hot_folders", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list hot folders")


@router.get("/hot-folders/{folder_id}", response_model=HotFolderConfig)
async def get_hot_folder(
    folder_id: str = Path(..., description="Hot folder ID"),
    hot_folder_service: HotFolderService = Depends(get_hot_folder_service)
) -> HotFolderConfig:
    """
    Get a specific hot folder configuration
    """
    try:
        config = await hot_folder_service.get_hot_folder(folder_id)
        if not config:
            raise HTTPException(status_code=404, detail="Hot folder not found")
        return config
    except Exception as e:
        logger.error("failed_to_get_hot_folder", error=str(e), folder_id=folder_id)
        raise HTTPException(status_code=500, detail="Failed to get hot folder")


@router.put("/hot-folders/{folder_id}", response_model=HotFolderConfig)
async def update_hot_folder(
    folder_id: str = Path(..., description="Hot folder ID"),
    config: HotFolderConfig = ...,
    hot_folder_service: HotFolderService = Depends(get_hot_folder_service)
) -> HotFolderConfig:
    """
    Update a hot folder configuration
    """
    try:
        updated_config = await hot_folder_service.update_hot_folder(folder_id, config)
        if not updated_config:
            raise HTTPException(status_code=404, detail="Hot folder not found")
        
        logger.info(
            "hot_folder_updated",
            hot_folder_id=folder_id,
            enabled=updated_config.enabled,
            immediate_processing=updated_config.immediate_processing
        )
        
        return updated_config
    except Exception as e:
        logger.error("failed_to_update_hot_folder", error=str(e), folder_id=folder_id)
        raise HTTPException(status_code=500, detail="Failed to update hot folder")


@router.delete("/hot-folders/{folder_id}")
async def delete_hot_folder(
    folder_id: str = Path(..., description="Hot folder ID"),
    hot_folder_service: HotFolderService = Depends(get_hot_folder_service)
):
    """
    Delete a hot folder configuration
    """
    try:
        success = await hot_folder_service.delete_hot_folder(folder_id)
        if not success:
            raise HTTPException(status_code=404, detail="Hot folder not found")
        
        logger.info("hot_folder_deleted", hot_folder_id=folder_id)
        
        return {"message": "Hot folder deleted successfully"}
    except Exception as e:
        logger.error("failed_to_delete_hot_folder", error=str(e), folder_id=folder_id)
        raise HTTPException(status_code=500, detail="Failed to delete hot folder")


@router.get("/hot-folders/{folder_id}/stats")
async def get_hot_folder_stats(
    folder_id: str = Path(..., description="Hot folder ID"),
    hot_folder_service: HotFolderService = Depends(get_hot_folder_service)
):
    """
    Get statistics for a specific hot folder
    """
    try:
        stats = await hot_folder_service.get_hot_folder_stats(folder_id)
        if not stats:
            raise HTTPException(status_code=404, detail="Hot folder not found")
        return stats
    except Exception as e:
        logger.error("failed_to_get_hot_folder_stats", error=str(e), folder_id=folder_id)
        raise HTTPException(status_code=500, detail="Failed to get hot folder statistics")


@router.post("/hot-folders/{folder_id}/scan")
async def trigger_hot_folder_scan(
    folder_id: str = Path(..., description="Hot folder ID"),
    hot_folder_service: HotFolderService = Depends(get_hot_folder_service)
):
    """
    Manually trigger a scan of a hot folder for existing files
    """
    try:
        processed_files = await hot_folder_service.trigger_folder_scan(folder_id)
        
        logger.info(
            "hot_folder_manual_scan_triggered",
            hot_folder_id=folder_id,
            files_processed=len(processed_files)
        )
        
        return {
            "message": "Hot folder scan completed",
            "files_processed": len(processed_files),
            "processed_files": processed_files
        }
    except Exception as e:
        logger.error("failed_to_scan_hot_folder", error=str(e), folder_id=folder_id)
        raise HTTPException(status_code=500, detail="Failed to scan hot folder")


@router.get("/hot-folders-stats")
async def get_hot_folders_service_stats(
    hot_folder_service: HotFolderService = Depends(get_hot_folder_service)
):
    """
    Get overall hot folder service statistics
    """
    try:
        return await hot_folder_service.get_service_stats()
    except Exception as e:
        logger.error("failed_to_get_hot_folders_service_stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get hot folder service statistics")


# Camera Card Support
@router.post("/camera-cards/detect")
async def detect_camera_card(
    card_path: str = Query(..., description="Path to camera card"),
    camera_card_service: CameraCardService = Depends(get_camera_card_service)
):
    """
    Detect the type of camera card at the specified path
    """
    try:
        card_type = await camera_card_service.detect_card_type(card_path)
        
        if card_type:
            logger.info(
                "camera_card_detected",
                card_path=card_path,
                card_type=card_type.value
            )
            
            return {
                "detected": True,
                "card_type": card_type.value,
                "card_path": card_path
            }
        else:
            return {
                "detected": False,
                "card_path": card_path,
                "message": "No supported camera card detected"
            }
    
    except Exception as e:
        logger.error("failed_to_detect_camera_card", error=str(e), card_path=card_path)
        raise HTTPException(status_code=500, detail="Failed to detect camera card")


@router.post("/camera-cards/analyze", response_model=CameraCardInfo)
async def analyze_camera_card(
    card_path: str = Query(..., description="Path to camera card"),
    camera_card_service: CameraCardService = Depends(get_camera_card_service)
) -> CameraCardInfo:
    """
    Analyze a camera card and extract detailed information about its contents
    """
    try:
        card_info = await camera_card_service.analyze_card(card_path)
        
        if not card_info:
            raise HTTPException(
                status_code=404,
                detail="No supported camera card found at the specified path"
            )
        
        logger.info(
            "camera_card_analyzed",
            card_path=card_path,
            card_type=card_info.card_type.value,
            total_clips=len(card_info.clips),
            total_size=card_info.total_size
        )
        
        return card_info
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("failed_to_analyze_camera_card", error=str(e), card_path=card_path)
        raise HTTPException(status_code=500, detail="Failed to analyze camera card")


@router.post("/camera-cards/ingest", response_model=List[IngestJob])
async def ingest_camera_card(
    card_path: str = Query(..., description="Path to camera card"),
    destination_project_id: Optional[str] = Query(None, description="Target project ID"),
    background_tasks: BackgroundTasks = ...,
    camera_card_service: CameraCardService = Depends(get_camera_card_service),
    ingest_service: IngestService = Depends(get_ingest_service)
) -> List[IngestJob]:
    """
    Analyze a camera card and create ingest jobs for all clips
    """
    try:
        # First analyze the card
        card_info = await camera_card_service.analyze_card(card_path)
        
        if not card_info:
            raise HTTPException(
                status_code=404,
                detail="No supported camera card found at the specified path"
            )
        
        # Create ingest jobs for all clips
        job_requests = await camera_card_service.create_ingest_jobs_for_card(
            card_info,
            destination_project_id
        )
        
        # Create the jobs
        created_jobs = []
        for job_request in job_requests:
            try:
                job = await ingest_service.create_job(job_request)
                created_jobs.append(job)
                
                # Start processing in background
                background_tasks.add_task(
                    ingest_service.process_job,
                    job.id
                )
                
            except Exception as e:
                logger.error(
                    "failed_to_create_camera_card_job",
                    error=str(e),
                    source_path=job_request.source_path
                )
        
        logger.info(
            "camera_card_ingest_started",
            card_path=card_path,
            card_type=card_info.card_type.value,
            total_clips=len(card_info.clips),
            jobs_created=len(created_jobs)
        )
        
        return created_jobs
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("failed_to_ingest_camera_card", error=str(e), card_path=card_path)
        raise HTTPException(status_code=500, detail="Failed to ingest camera card")


@router.get("/camera-cards/supported-types")
async def get_supported_camera_card_types():
    """
    Get list of supported camera card types
    """
    return {
        "supported_types": [
            {
                "type": "P2",
                "name": "Panasonic P2",
                "description": "Professional P2 memory cards used by Panasonic cameras",
                "file_formats": ["MXF", "MP4"],
                "structure": "CONTENTS folder with CLIP, AUDIO, PROXY, ICON subfolders"
            },
            {
                "type": "XDCAM",
                "name": "Sony XDCAM",
                "description": "Professional disc format used by Sony cameras",
                "file_formats": ["MXF", "MP4"],
                "structure": "BPAV folder with CLPR, CLIPMETA, SMLPRX, LGPRX, ICON subfolders"
            },
            {
                "type": "SXS",
                "name": "Sony SXS",
                "description": "Sony SXS memory cards for professional cameras",
                "file_formats": ["MXF", "MP4"],
                "structure": "BPAV folder with MEDIAPRO.XML"
            },
            {
                "type": "CFEXPRESS",
                "name": "CFExpress",
                "description": "High-speed CFExpress memory cards",
                "file_formats": ["MP4", "MOV", "MXF", "R3D", "BRAW", "AVI"],
                "structure": "DCIM, PRIVATE folders or direct root storage"
            }
        ]
    }


@router.post("/camera-cards/validate")
async def validate_camera_card_structure(
    card_path: str = Query(..., description="Path to camera card"),
    camera_card_service: CameraCardService = Depends(get_camera_card_service)
):
    """
    Validate camera card structure and report any issues
    """
    try:
        # Detect card type
        card_type = await camera_card_service.detect_card_type(card_path)
        
        if not card_type:
            return {
                "valid": False,
                "issues": ["No supported camera card structure detected"],
                "card_path": card_path
            }
        
        # Analyze card for validation
        card_info = await camera_card_service.analyze_card(card_path)
        
        issues = []
        warnings = []
        
        # Check for common issues
        if len(card_info.clips) == 0:
            issues.append("No video clips found on card")
        
        if card_info.total_size == 0:
            issues.append("Card appears to be empty")
        
        # Check for missing associated files (warnings only)
        for clip in card_info.clips:
            if not clip.proxy_path:
                warnings.append(f"No proxy file found for clip {clip.clip_name}")
            if not clip.thumbnail_path:
                warnings.append(f"No thumbnail found for clip {clip.clip_name}")
        
        return {
            "valid": len(issues) == 0,
            "card_type": card_type.value,
            "card_path": card_path,
            "total_clips": len(card_info.clips),
            "total_size": card_info.total_size,
            "issues": issues,
            "warnings": warnings
        }
    
    except Exception as e:
        logger.error("failed_to_validate_camera_card", error=str(e), card_path=card_path)
        raise HTTPException(status_code=500, detail="Failed to validate camera card")


# Live Ingest Support
@router.post("/live-streams", response_model=IngestJob)
async def start_live_stream_ingest(
    stream_url: str = Query(..., description="Live stream URL (rtmp, rtsp, http, etc.)"),
    destination_project_id: Optional[str] = Query(None, description="Target project ID"),
    background_tasks: BackgroundTasks = ...,
    live_ingest_service: LiveIngestService = Depends(get_live_ingest_service)
) -> IngestJob:
    """
    Start ingesting from a live stream
    """
    try:
        job = await live_ingest_service.start_live_stream_ingest(
            stream_url=stream_url,
            destination_project_id=destination_project_id,
            metadata_override={"stream_type": "live"},
            tags=["live_stream", "real_time"]
        )
        
        logger.info(
            "live_stream_ingest_started",
            job_id=job.id,
            stream_url=stream_url
        )
        
        return job
    
    except Exception as e:
        logger.error("failed_to_start_live_stream", error=str(e), stream_url=stream_url)
        raise HTTPException(status_code=500, detail="Failed to start live stream ingest")


@router.post("/growing-files", response_model=IngestJob)
async def start_growing_file_ingest(
    file_path: str = Query(..., description="Path to growing file"),
    destination_project_id: Optional[str] = Query(None, description="Target project ID"),
    timeout: int = Query(300, description="Timeout in seconds to wait for file stability"),
    background_tasks: BackgroundTasks = ...,
    live_ingest_service: LiveIngestService = Depends(get_live_ingest_service)
) -> IngestJob:
    """
    Start monitoring and ingesting a growing file
    """
    try:
        job = await live_ingest_service.start_growing_file_ingest(
            file_path=file_path,
            destination_project_id=destination_project_id,
            growing_file_timeout=timeout,
            metadata_override={"file_type": "growing"},
            tags=["growing_file", "live_capture"]
        )
        
        logger.info(
            "growing_file_ingest_started",
            job_id=job.id,
            file_path=file_path,
            timeout=timeout
        )
        
        return job
    
    except Exception as e:
        logger.error("failed_to_start_growing_file", error=str(e), file_path=file_path)
        raise HTTPException(status_code=500, detail="Failed to start growing file ingest")


@router.delete("/live-ingests/{job_id}")
async def stop_live_ingest(
    job_id: str = Path(..., description="Live ingest job ID"),
    live_ingest_service: LiveIngestService = Depends(get_live_ingest_service)
):
    """
    Stop a live ingest operation
    """
    try:
        success = await live_ingest_service.stop_live_ingest(job_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Live ingest job not found")
        
        logger.info("live_ingest_stopped", job_id=job_id)
        
        return {"message": "Live ingest stopped successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_stop_live_ingest", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to stop live ingest")


@router.get("/live-ingests/{job_id}/status")
async def get_live_ingest_status(
    job_id: str = Path(..., description="Live ingest job ID"),
    live_ingest_service: LiveIngestService = Depends(get_live_ingest_service)
):
    """
    Get status of a live ingest operation
    """
    try:
        status = await live_ingest_service.get_live_ingest_status(job_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Live ingest job not found")
        
        return status
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_get_live_ingest_status", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to get live ingest status")


@router.get("/live-ingests")
async def list_active_live_ingests(
    live_ingest_service: LiveIngestService = Depends(get_live_ingest_service)
):
    """
    List all active live ingest operations
    """
    try:
        active_ingests = await live_ingest_service.list_active_live_ingests()
        
        return {
            "active_ingests": active_ingests,
            "total_count": len(active_ingests)
        }
    
    except Exception as e:
        logger.error("failed_to_list_live_ingests", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list live ingests")


@router.get("/live-ingests/supported-protocols")
async def get_supported_live_protocols():
    """
    Get list of supported live streaming protocols
    """
    return {
        "supported_protocols": [
            {
                "protocol": "RTMP",
                "description": "Real-Time Messaging Protocol",
                "example": "rtmp://streaming-server.com/live/stream-key",
                "use_cases": ["Live streaming from software encoders", "OBS Studio", "Wirecast"]
            },
            {
                "protocol": "RTSP",
                "description": "Real Time Streaming Protocol",
                "example": "rtsp://camera-ip:554/stream1",
                "use_cases": ["IP cameras", "Security cameras", "Professional cameras"]
            },
            {
                "protocol": "HTTP/HTTPS",
                "description": "HTTP Live Streaming (HLS) and DASH",
                "example": "https://streaming-server.com/playlist.m3u8",
                "use_cases": ["Adaptive streaming", "CDN delivery", "Mobile streaming"]
            },
            {
                "protocol": "SRT",
                "description": "Secure Reliable Transport",
                "example": "srt://streaming-server.com:9999",
                "use_cases": ["Low-latency streaming", "Remote production", "Professional broadcast"]
            },
            {
                "protocol": "UDP",
                "description": "User Datagram Protocol",
                "example": "udp://multicast-address:port",
                "use_cases": ["Multicast streaming", "MPEG-TS over UDP", "Broadcast applications"]
            },
            {
                "protocol": "TCP",
                "description": "Transmission Control Protocol",
                "example": "tcp://server-address:port",
                "use_cases": ["Reliable streaming", "Point-to-point connections"]
            }
        ]
    }


# Edit-While-Ingest Support
@router.post("/edit-while-ingest/{job_id}/register")
async def register_edit_while_ingest(
    job_id: str = Path(..., description="Ingest job ID"),
    source_path: str = Query(..., description="Source file path"),
    destination_path: str = Query(..., description="Destination file path"),
    ingest_service: IngestService = Depends(get_ingest_service),
    edit_while_ingest_service: EditWhileIngestService = Depends(get_edit_while_ingest_service)
):
    """
    Register an ingest job for edit-while-ingest capability
    """
    try:
        # Get the ingest job
        job = await ingest_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Ingest job not found")
        
        # Register for edit-while-ingest
        session = await edit_while_ingest_service.register_active_ingest(
            job=job,
            source_path=source_path,
            destination_path=destination_path
        )
        
        logger.info(
            "edit_while_ingest_registered",
            job_id=job_id,
            source_path=source_path
        )
        
        return {
            "message": "Edit-while-ingest enabled",
            "job_id": job_id,
            "session_active": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_register_edit_while_ingest", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to register edit-while-ingest")


@router.get("/edit-while-ingest/{job_id}/metadata")
async def get_edit_while_ingest_metadata(
    job_id: str = Path(..., description="Ingest job ID"),
    edit_while_ingest_service: EditWhileIngestService = Depends(get_edit_while_ingest_service)
):
    """
    Get current metadata for an active edit-while-ingest session
    """
    try:
        metadata = await edit_while_ingest_service.get_ingest_metadata(job_id)
        
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail="No active edit-while-ingest session found"
            )
        
        return metadata
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_get_edit_metadata", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to get metadata")


@router.get("/edit-while-ingest/{job_id}/partial")
async def get_partial_file_access(
    job_id: str = Path(..., description="Ingest job ID"),
    start: Optional[int] = Query(None, description="Start byte offset"),
    end: Optional[int] = Query(None, description="End byte offset"),
    edit_while_ingest_service: EditWhileIngestService = Depends(get_edit_while_ingest_service)
):
    """
    Get partial access to a file being ingested
    """
    try:
        byte_range = None
        if start is not None and end is not None:
            byte_range = (start, end)
        
        data = await edit_while_ingest_service.get_partial_file_access(
            job_id=job_id,
            byte_range=byte_range
        )
        
        if data is None:
            raise HTTPException(
                status_code=404,
                detail="No data available for the requested range"
            )
        
        from fastapi.responses import Response
        
        headers = {
            "Content-Type": "application/octet-stream",
            "Accept-Ranges": "bytes"
        }
        
        if byte_range:
            headers["Content-Range"] = f"bytes {start}-{end}/*"
        
        return Response(
            content=data,
            headers=headers,
            media_type="application/octet-stream"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_get_partial_file", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to get partial file")


@router.get("/edit-while-ingest/{job_id}/segments")
async def get_editable_segments(
    job_id: str = Path(..., description="Ingest job ID"),
    edit_while_ingest_service: EditWhileIngestService = Depends(get_edit_while_ingest_service)
):
    """
    Get list of segments available for editing
    """
    try:
        segments = await edit_while_ingest_service.get_editable_segments(job_id)
        
        return {
            "job_id": job_id,
            "segments": segments,
            "total_segments": len(segments)
        }
    
    except Exception as e:
        logger.error("failed_to_get_segments", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to get segments")


@router.post("/edit-while-ingest/{job_id}/priority-chunk")
async def request_priority_chunk(
    job_id: str = Path(..., description="Ingest job ID"),
    byte_offset: int = Query(..., description="Byte offset for priority processing"),
    chunk_size: int = Query(..., description="Size of chunk to prioritize"),
    edit_while_ingest_service: EditWhileIngestService = Depends(get_edit_while_ingest_service)
):
    """
    Request priority processing of a specific chunk
    """
    try:
        success = await edit_while_ingest_service.request_priority_chunk(
            job_id=job_id,
            byte_offset=byte_offset,
            chunk_size=chunk_size
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Failed to prioritize chunk - session may not be active"
            )
        
        logger.info(
            "priority_chunk_requested",
            job_id=job_id,
            byte_offset=byte_offset,
            chunk_size=chunk_size
        )
        
        return {
            "message": "Chunk prioritized for processing",
            "job_id": job_id,
            "byte_offset": byte_offset,
            "chunk_size": chunk_size
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_prioritize_chunk", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to prioritize chunk")


@router.post("/edit-while-ingest/{job_id}/edit-session")
async def create_edit_session(
    job_id: str = Path(..., description="Ingest job ID"),
    start_time: float = Query(..., description="Start time in seconds"),
    end_time: float = Query(..., description="End time in seconds"),
    edit_while_ingest_service: EditWhileIngestService = Depends(get_edit_while_ingest_service)
):
    """
    Create an edit session for a specific time range
    """
    try:
        session_id = await edit_while_ingest_service.create_edit_session(
            job_id=job_id,
            start_time=start_time,
            end_time=end_time
        )
        
        if not session_id:
            raise HTTPException(
                status_code=404,
                detail="Failed to create edit session - ingest may not be active"
            )
        
        return {
            "session_id": session_id,
            "job_id": job_id,
            "start_time": start_time,
            "end_time": end_time,
            "status": "active"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_create_edit_session", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to create edit session")


@router.get("/edit-while-ingest/{job_id}/proxy")
async def get_partial_proxy_path(
    job_id: str = Path(..., description="Ingest job ID"),
    edit_while_ingest_service: EditWhileIngestService = Depends(get_edit_while_ingest_service)
):
    """
    Get the path to the partial proxy file
    """
    try:
        proxy_path = await edit_while_ingest_service.get_partial_proxy_path(job_id)
        
        if not proxy_path:
            raise HTTPException(
                status_code=404,
                detail="No proxy available for this ingest"
            )
        
        return {
            "job_id": job_id,
            "proxy_path": proxy_path,
            "available": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_get_proxy_path", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to get proxy path")


@router.delete("/edit-while-ingest/{job_id}")
async def unregister_edit_while_ingest(
    job_id: str = Path(..., description="Ingest job ID"),
    edit_while_ingest_service: EditWhileIngestService = Depends(get_edit_while_ingest_service)
):
    """
    Unregister an edit-while-ingest session
    """
    try:
        await edit_while_ingest_service.unregister_active_ingest(job_id)
        
        logger.info("edit_while_ingest_unregistered", job_id=job_id)
        
        return {
            "message": "Edit-while-ingest session closed",
            "job_id": job_id
        }
    
    except Exception as e:
        logger.error("failed_to_unregister_edit_while_ingest", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to unregister session")


# Streaming Protocol Support
@router.post("/streaming/ingest", response_model=IngestJob)
async def ingest_streaming_protocol(
    stream_url: str = Query(..., description="Stream URL (HLS, SRT, RTMP, etc.)"),
    protocol: Optional[str] = Query(None, description="Streaming protocol (auto-detected if not provided)"),
    destination_project_id: Optional[str] = Query(None, description="Target project ID"),
    background_tasks: BackgroundTasks = ...,
    streaming_service: StreamingProtocolService = Depends(get_streaming_protocol_service),
    ingest_service: IngestService = Depends(get_ingest_service)
) -> IngestJob:
    """
    Ingest a stream using various streaming protocols (HLS, SRT, DASH, RTMP, RTSP)
    """
    try:
        # Create a temporary destination path
        import tempfile
        temp_dir = tempfile.mkdtemp()
        destination_path = f"{temp_dir}/stream_output.mp4"
        
        # Create ingest job
        job_request = IngestJobCreate(
            source_path=stream_url,
            destination_project_id=destination_project_id,
            ingest_type="streaming",
            metadata_override={
                "stream_url": stream_url,
                "protocol": protocol or "auto-detect"
            },
            tags=["streaming", protocol] if protocol else ["streaming"]
        )
        
        job = await ingest_service.create_job(job_request)
        
        # Start streaming ingest in background
        background_tasks.add_task(
            streaming_service.ingest_stream,
            stream_url=stream_url,
            destination_path=destination_path,
            protocol=protocol
        )
        
        logger.info(
            "streaming_ingest_started",
            job_id=job.id,
            stream_url=stream_url,
            protocol=protocol
        )
        
        return job
    
    except Exception as e:
        logger.error("failed_to_start_streaming_ingest", error=str(e), stream_url=stream_url)
        raise HTTPException(status_code=500, detail="Failed to start streaming ingest")


@router.post("/streaming/convert")
async def convert_to_streaming_format(
    source_path: str = Query(..., description="Source file path"),
    output_format: str = Query(..., description="Target streaming format (hls, dash)"),
    video_codec: Optional[str] = Query("libx264", description="Video codec"),
    audio_codec: Optional[str] = Query("aac", description="Audio codec"),
    segment_duration: Optional[int] = Query(10, description="Segment duration in seconds"),
    background_tasks: BackgroundTasks = ...,
    streaming_service: StreamingProtocolService = Depends(get_streaming_protocol_service)
):
    """
    Convert a video file to streaming format (HLS or DASH)
    """
    try:
        if output_format.lower() not in ['hls', 'dash']:
            raise HTTPException(
                status_code=400,
                detail="Only HLS and DASH formats are supported for conversion"
            )
        
        options = {
            'video_codec': video_codec,
            'audio_codec': audio_codec,
            'segment_duration': segment_duration
        }
        
        # Start conversion in background
        background_tasks.add_task(
            streaming_service.convert_stream_format,
            source_path=source_path,
            output_format=output_format.lower(),
            options=options
        )
        
        logger.info(
            "streaming_conversion_started",
            source_path=source_path,
            output_format=output_format
        )
        
        return {
            "message": "Streaming format conversion started",
            "source_path": source_path,
            "output_format": output_format,
            "options": options
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_start_streaming_conversion", error=str(e), source_path=source_path)
        raise HTTPException(status_code=500, detail="Failed to start streaming conversion")


@router.get("/streaming/protocols")
async def get_supported_streaming_protocols():
    """
    Get list of supported streaming protocols with details
    """
    return {
        "supported_protocols": [
            {
                "protocol": "HLS",
                "name": "HTTP Live Streaming",
                "description": "Apple's adaptive bitrate streaming protocol",
                "file_extension": ".m3u8",
                "use_cases": [
                    "Live streaming to iOS devices",
                    "VOD with adaptive bitrate",
                    "CDN-friendly distribution"
                ],
                "features": [
                    "Adaptive bitrate streaming",
                    "Encryption support",
                    "Closed captions",
                    "Multiple audio tracks"
                ]
            },
            {
                "protocol": "SRT",
                "name": "Secure Reliable Transport",
                "description": "Low-latency video transport protocol",
                "scheme": "srt://",
                "use_cases": [
                    "Live contribution",
                    "Remote production",
                    "Point-to-point streaming"
                ],
                "features": [
                    "Low latency (sub-second)",
                    "Packet loss recovery",
                    "Encryption",
                    "Firewall traversal"
                ]
            },
            {
                "protocol": "DASH",
                "name": "Dynamic Adaptive Streaming over HTTP",
                "description": "MPEG's adaptive bitrate streaming standard",
                "file_extension": ".mpd",
                "use_cases": [
                    "Multi-platform streaming",
                    "4K/8K video delivery",
                    "DRM-protected content"
                ],
                "features": [
                    "Codec agnostic",
                    "Multi-DRM support",
                    "Low latency mode",
                    "Efficient caching"
                ]
            },
            {
                "protocol": "RTMP",
                "name": "Real-Time Messaging Protocol",
                "description": "Adobe's protocol for live streaming",
                "scheme": "rtmp://",
                "use_cases": [
                    "Live streaming to platforms",
                    "OBS/Wirecast streaming",
                    "Legacy Flash support"
                ],
                "features": [
                    "Low latency",
                    "Wide platform support",
                    "Simple implementation",
                    "Persistent connections"
                ]
            },
            {
                "protocol": "RTSP",
                "name": "Real Time Streaming Protocol",
                "description": "Protocol for controlling streaming media servers",
                "scheme": "rtsp://",
                "use_cases": [
                    "IP camera streaming",
                    "Security systems",
                    "Professional broadcast"
                ],
                "features": [
                    "Camera control (PTZ)",
                    "RTP/RTCP transport",
                    "Multicast support",
                    "Session management"
                ]
            }
        ]
    }


@router.post("/streaming/hls/generate")
async def generate_hls_stream(
    source_path: str = Query(..., description="Source video file path"),
    output_dir: str = Query(..., description="Output directory for HLS files"),
    variants: Optional[List[Dict]] = Query(None, description="Video variants for adaptive streaming"),
    segment_duration: Optional[int] = Query(10, description="Segment duration in seconds"),
    playlist_type: Optional[str] = Query("vod", description="Playlist type: vod or event"),
    background_tasks: BackgroundTasks = ...,
    streaming_service: StreamingProtocolService = Depends(get_streaming_protocol_service)
):
    """
    Generate HLS stream with multiple quality variants
    """
    try:
        # Default variants if not provided
        if not variants:
            variants = [
                {"name": "1080p", "width": 1920, "height": 1080, "bitrate": "5000k"},
                {"name": "720p", "width": 1280, "height": 720, "bitrate": "2500k"},
                {"name": "480p", "width": 854, "height": 480, "bitrate": "1000k"}
            ]
        
        options = {
            'variants': variants,
            'segment_duration': segment_duration,
            'playlist_type': playlist_type
        }
        
        # Generate HLS in background
        background_tasks.add_task(
            streaming_service.convert_stream_format,
            source_path=source_path,
            output_format='hls',
            options=options
        )
        
        logger.info(
            "hls_generation_started",
            source_path=source_path,
            output_dir=output_dir,
            variants_count=len(variants)
        )
        
        return {
            "message": "HLS generation started",
            "source_path": source_path,
            "output_dir": output_dir,
            "variants": variants,
            "playlist_type": playlist_type
        }
    
    except Exception as e:
        logger.error("failed_to_generate_hls", error=str(e), source_path=source_path)
        raise HTTPException(status_code=500, detail="Failed to generate HLS stream")


@router.post("/streaming/dash/generate")
async def generate_dash_stream(
    source_path: str = Query(..., description="Source video file path"),
    output_dir: str = Query(..., description="Output directory for DASH files"),
    profiles: Optional[List[Dict]] = Query(None, description="Video profiles for adaptive streaming"),
    segment_duration: Optional[int] = Query(10, description="Segment duration in seconds"),
    min_buffer_time: Optional[int] = Query(2, description="Minimum buffer time in seconds"),
    background_tasks: BackgroundTasks = ...,
    streaming_service: StreamingProtocolService = Depends(get_streaming_protocol_service)
):
    """
    Generate DASH stream with multiple quality profiles
    """
    try:
        # Default profiles if not provided
        if not profiles:
            profiles = [
                {"name": "high", "width": 1920, "height": 1080, "bitrate": "5000k"},
                {"name": "medium", "width": 1280, "height": 720, "bitrate": "2500k"},
                {"name": "low", "width": 854, "height": 480, "bitrate": "1000k"}
            ]
        
        options = {
            'profiles': profiles,
            'segment_duration': segment_duration,
            'min_buffer_time': min_buffer_time
        }
        
        # Generate DASH in background
        background_tasks.add_task(
            streaming_service.convert_stream_format,
            source_path=source_path,
            output_format='dash',
            options=options
        )
        
        logger.info(
            "dash_generation_started",
            source_path=source_path,
            output_dir=output_dir,
            profiles_count=len(profiles)
        )
        
        return {
            "message": "DASH generation started",
            "source_path": source_path,
            "output_dir": output_dir,
            "profiles": profiles,
            "min_buffer_time": min_buffer_time
        }
    
    except Exception as e:
        logger.error("failed_to_generate_dash", error=str(e), source_path=source_path)
        raise HTTPException(status_code=500, detail="Failed to generate DASH stream")


# Real-time Proxy Generation
@router.post("/realtime-proxy/start")
async def start_realtime_proxy(
    job_id: str = Query(..., description="Ingest job ID"),
    source_path: str = Query(..., description="Source file path"),
    destination_dir: str = Query(..., description="Destination directory for proxy files"),
    quality: str = Query("medium", description="Proxy quality: low, medium, high, edit"),
    background_tasks: BackgroundTasks = ...,
    proxy_service: RealtimeProxyService = Depends(get_realtime_proxy_service),
    ingest_service: IngestService = Depends(get_ingest_service)
):
    """
    Start real-time proxy generation for an active ingest
    """
    try:
        # Validate quality
        try:
            proxy_quality = ProxyQuality(quality.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid proxy quality. Choose from: low, medium, high, edit"
            )
        
        # Verify ingest job exists
        job = await ingest_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Ingest job not found")
        
        # Start real-time proxy generation
        session = await proxy_service.start_realtime_proxy(
            job_id=job_id,
            source_path=source_path,
            destination_dir=destination_dir,
            quality=proxy_quality
        )
        
        logger.info(
            "realtime_proxy_started",
            job_id=job_id,
            quality=quality,
            destination_dir=destination_dir
        )
        
        return {
            "message": "Real-time proxy generation started",
            "job_id": job_id,
            "quality": quality,
            "destination_dir": destination_dir,
            "proxy_profile": {
                "name": session.profile.name,
                "video_codec": session.profile.video_codec,
                "video_bitrate": session.profile.video_bitrate,
                "audio_codec": session.profile.audio_codec,
                "audio_bitrate": session.profile.audio_bitrate,
                "resolution": session.profile.resolution
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_start_realtime_proxy", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to start real-time proxy generation")


@router.delete("/realtime-proxy/{job_id}")
async def stop_realtime_proxy(
    job_id: str = Path(..., description="Ingest job ID"),
    proxy_service: RealtimeProxyService = Depends(get_realtime_proxy_service)
):
    """
    Stop real-time proxy generation for a job
    """
    try:
        await proxy_service.stop_realtime_proxy(job_id)
        
        logger.info("realtime_proxy_stopped", job_id=job_id)
        
        return {
            "message": "Real-time proxy generation stopped",
            "job_id": job_id
        }
    
    except Exception as e:
        logger.error("failed_to_stop_realtime_proxy", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to stop real-time proxy generation")


@router.get("/realtime-proxy/{job_id}/status")
async def get_realtime_proxy_status(
    job_id: str = Path(..., description="Ingest job ID"),
    proxy_service: RealtimeProxyService = Depends(get_realtime_proxy_service)
):
    """
    Get status of real-time proxy generation
    """
    try:
        status = await proxy_service.get_proxy_status(job_id)
        
        if not status:
            raise HTTPException(
                status_code=404,
                detail="No active real-time proxy generation found for this job"
            )
        
        return status
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_get_proxy_status", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to get proxy status")


@router.get("/realtime-proxy/profiles")
async def get_proxy_profiles():
    """
    Get available proxy generation profiles
    """
    return {
        "profiles": {
            "low": {
                "description": "Low quality proxy for quick preview",
                "video_codec": "libx264",
                "video_bitrate": "500k",
                "audio_codec": "aac",
                "audio_bitrate": "64k",
                "resolution": "640x360",
                "use_cases": ["Quick preview", "Mobile viewing", "Low bandwidth"]
            },
            "medium": {
                "description": "Medium quality proxy for standard editing",
                "video_codec": "libx264",
                "video_bitrate": "1500k",
                "audio_codec": "aac",
                "audio_bitrate": "128k",
                "resolution": "1280x720",
                "use_cases": ["Standard editing", "Desktop preview", "Review and approval"]
            },
            "high": {
                "description": "High quality proxy for detailed work",
                "video_codec": "libx264",
                "video_bitrate": "3000k",
                "audio_codec": "aac",
                "audio_bitrate": "192k",
                "resolution": "1920x1080",
                "use_cases": ["Detailed editing", "Color grading", "Quality control"]
            },
            "edit": {
                "description": "Edit-ready proxy with professional codec",
                "video_codec": "prores",
                "video_bitrate": "40000k",
                "audio_codec": "pcm_s16le",
                "audio_bitrate": "1536k",
                "resolution": "original",
                "use_cases": ["Professional editing", "Color correction", "Final cut"]
            }
        }
    }


@router.post("/realtime-proxy/batch")
async def start_batch_realtime_proxy(
    job_ids: List[str] = Query(..., description="List of ingest job IDs"),
    destination_dir: str = Query(..., description="Destination directory for proxy files"),
    quality: str = Query("medium", description="Proxy quality for all jobs"),
    background_tasks: BackgroundTasks = ...,
    proxy_service: RealtimeProxyService = Depends(get_realtime_proxy_service),
    ingest_service: IngestService = Depends(get_ingest_service)
):
    """
    Start real-time proxy generation for multiple ingest jobs
    """
    try:
        # Validate quality
        try:
            proxy_quality = ProxyQuality(quality.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid proxy quality. Choose from: low, medium, high, edit"
            )
        
        started_jobs = []
        failed_jobs = []
        
        for job_id in job_ids:
            try:
                # Get job details
                job = await ingest_service.get_job(job_id)
                if not job:
                    failed_jobs.append({
                        "job_id": job_id,
                        "reason": "Job not found"
                    })
                    continue
                
                # Start proxy generation
                job_dest_dir = f"{destination_dir}/{job_id}"
                
                await proxy_service.start_realtime_proxy(
                    job_id=job_id,
                    source_path=job.source_path,
                    destination_dir=job_dest_dir,
                    quality=proxy_quality
                )
                
                started_jobs.append(job_id)
                
            except Exception as e:
                failed_jobs.append({
                    "job_id": job_id,
                    "reason": str(e)
                })
        
        logger.info(
            "batch_realtime_proxy_started",
            started_count=len(started_jobs),
            failed_count=len(failed_jobs),
            quality=quality
        )
        
        return {
            "message": "Batch real-time proxy generation initiated",
            "quality": quality,
            "started_jobs": started_jobs,
            "failed_jobs": failed_jobs,
            "total_requested": len(job_ids),
            "total_started": len(started_jobs),
            "total_failed": len(failed_jobs)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_start_batch_proxy", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start batch proxy generation")


@router.get("/realtime-proxy/active")
async def list_active_proxy_generations(
    proxy_service: RealtimeProxyService = Depends(get_realtime_proxy_service)
):
    """
    List all active real-time proxy generation sessions
    """
    try:
        active_sessions = []
        
        for job_id, session in proxy_service.active_generations.items():
            status = await session.get_status()
            active_sessions.append({
                "job_id": job_id,
                "profile": status['profile'],
                "quality": status['quality'],
                "chunks_generated": status['chunks_generated'],
                "current_position": status['current_position'],
                "elapsed_time": status['elapsed_time']
            })
        
        return {
            "active_sessions": active_sessions,
            "total_active": len(active_sessions)
        }
    
    except Exception as e:
        logger.error("failed_to_list_active_proxies", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list active proxy generations")
"""
Integration Service API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from ..core.database import get_db
from ..core.auth import get_current_user
from ..core.logger import get_logger
from ..models.schemas import (
    TimelineExportRequest, 
    ExportResult, 
    ExportStatus,
    User,
    NLEExportRequest,
    NLEExportResponse,
    ExportJobStatus
)
from ..exporters.aaf_exporter import AAFExporter
from ..exporters.xml_exporter import XMLExporter
from ..exporters.edl_exporter import EDLExporter
from ..exporters.otio_exporter import OTIOExporter
from ..exporters.omf_exporter import OMFExporter
from ..services.export_service import ExportService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/integration", tags=["integration"])

# Export routes
@router.post("/export/aaf", response_model=ExportResult)
async def export_aaf(
    request: TimelineExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export timeline to AAF format for Avid Media Composer"""
    try:
        logger.info(f"AAF export requested by user {current_user.user_id} for timeline {request.timeline_id}")
        
        # Create AAF exporter
        aaf_exporter = AAFExporter(db)
        
        # Start export
        result = await aaf_exporter.export_timeline(request)
        
        # Log export completion
        logger.info(f"AAF export completed: {result.export_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"AAF export failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AAF export failed: {str(e)}"
        )


@router.post("/export/xml", response_model=ExportResult)
async def export_xml(
    request: TimelineExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export timeline to XML format for Adobe Premiere Pro"""
    try:
        logger.info(f"XML export requested by user {current_user.user_id} for timeline {request.timeline_id}")
        
        # Create XML exporter
        xml_exporter = XMLExporter(db)
        
        # Start export
        result = await xml_exporter.export_timeline(request)
        
        # Log export completion
        logger.info(f"XML export completed: {result.export_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"XML export failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"XML export failed: {str(e)}"
        )


@router.post("/export/edl", response_model=ExportResult)
async def export_edl(
    request: TimelineExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export timeline to EDL format"""
    try:
        logger.info(f"EDL export requested by user {current_user.user_id} for timeline {request.timeline_id}")
        
        # Create EDL exporter
        edl_exporter = EDLExporter(db)
        
        # Start export
        result = await edl_exporter.export_timeline(request)
        
        # Log export completion
        logger.info(f"EDL export completed: {result.export_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"EDL export failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"EDL export failed: {str(e)}"
        )


@router.post("/export/cmx", response_model=ExportResult)
async def export_cmx_edl(
    request: TimelineExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export timeline to CMX EDL format"""
    try:
        logger.info(f"CMX EDL export requested by user {current_user.user_id} for timeline {request.timeline_id}")
        
        # Create EDL exporter
        edl_exporter = EDLExporter(db)
        
        # Start export
        result = await edl_exporter.export_cmx_edl(request)
        
        # Log export completion
        logger.info(f"CMX EDL export completed: {result.export_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"CMX EDL export failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CMX EDL export failed: {str(e)}"
        )


@router.post("/export/otio", response_model=ExportResult)
async def export_otio(
    request: TimelineExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export timeline to OTIO format for DaVinci Resolve"""
    try:
        logger.info(f"OTIO export requested by user {current_user.user_id} for timeline {request.timeline_id}")
        
        # Create OTIO exporter
        otio_exporter = OTIOExporter(db)
        
        # Start export
        result = await otio_exporter.export_timeline(request)
        
        # Log export completion
        logger.info(f"OTIO export completed: {result.export_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"OTIO export failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OTIO export failed: {str(e)}"
        )


@router.post("/export/omf", response_model=ExportResult)
async def export_omf(
    request: TimelineExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export timeline to OMF format for Pro Tools"""
    try:
        logger.info(f"OMF export requested by user {current_user.user_id} for timeline {request.timeline_id}")
        
        # Create OMF exporter
        omf_exporter = OMFExporter(db)
        
        # Start export
        result = await omf_exporter.export_timeline(request)
        
        # Log export completion
        logger.info(f"OMF export completed: {result.export_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"OMF export failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OMF export failed: {str(e)}"
        )


@router.post("/export/nle", response_model=NLEExportResponse)
async def export_nle(
    request: NLEExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export timeline to specified NLE format"""
    try:
        logger.info(f"NLE export requested by user {current_user.user_id} for timeline {request.timeline_id}, format: {request.format}")
        
        # Create export service
        export_service = ExportService(db)
        
        # Start export job
        job_id = await export_service.start_export_job(request, current_user)
        
        # Schedule background export
        background_tasks.add_task(
            export_service.process_export_job,
            job_id,
            request,
            current_user
        )
        
        return NLEExportResponse(
            job_id=job_id,
            status="started",
            message=f"Export job started for format: {request.format}"
        )
        
    except Exception as e:
        logger.error(f"NLE export failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"NLE export failed: {str(e)}"
        )


@router.get("/export/job/{job_id}", response_model=ExportJobStatus)
async def get_export_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get export job status"""
    try:
        export_service = ExportService(db)
        job_status = await export_service.get_export_job_status(job_id, current_user)
        
        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export job not found"
            )
        
        return job_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get export job status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get export job status: {str(e)}"
        )


@router.get("/export/jobs", response_model=List[ExportJobStatus])
async def get_export_jobs(
    limit: int = 20,
    offset: int = 0,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get export jobs for current user"""
    try:
        export_service = ExportService(db)
        jobs = await export_service.get_export_jobs(
            current_user, 
            limit=limit, 
            offset=offset,
            status_filter=status_filter
        )
        
        return jobs
        
    except Exception as e:
        logger.error(f"Failed to get export jobs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get export jobs: {str(e)}"
        )


@router.delete("/export/job/{job_id}")
async def cancel_export_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel export job"""
    try:
        export_service = ExportService(db)
        result = await export_service.cancel_export_job(job_id, current_user)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export job not found or cannot be cancelled"
            )
        
        return {"message": "Export job cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel export job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel export job: {str(e)}"
        )


@router.get("/export/formats", response_model=List[dict])
async def get_export_formats():
    """Get available export formats"""
    formats = [
        {
            "format": "aaf",
            "name": "AAF (Advanced Authoring Format)",
            "description": "For Avid Media Composer",
            "supports_audio": True,
            "supports_video": True,
            "supports_effects": True,
            "file_extension": ".aaf"
        },
        {
            "format": "xml",
            "name": "FCP7 XML",
            "description": "For Adobe Premiere Pro",
            "supports_audio": True,
            "supports_video": True,
            "supports_effects": False,
            "file_extension": ".xml"
        },
        {
            "format": "edl",
            "name": "EDL (Edit Decision List)",
            "description": "Traditional edit decision list",
            "supports_audio": True,
            "supports_video": True,
            "supports_effects": False,
            "file_extension": ".edl"
        },
        {
            "format": "cmx",
            "name": "CMX EDL",
            "description": "CMX format edit decision list",
            "supports_audio": False,
            "supports_video": True,
            "supports_effects": False,
            "file_extension": ".edl"
        },
        {
            "format": "otio",
            "name": "OpenTimelineIO",
            "description": "For DaVinci Resolve and other OTIO-compatible NLEs",
            "supports_audio": True,
            "supports_video": True,
            "supports_effects": True,
            "file_extension": ".otio"
        },
        {
            "format": "omf",
            "name": "OMF (Open Media Framework)",
            "description": "For Pro Tools and other audio DAWs",
            "supports_audio": True,
            "supports_video": False,
            "supports_effects": False,
            "file_extension": ".omf"
        }
    ]
    
    return formats


@router.post("/validate/export", response_model=dict)
async def validate_export_file(
    export_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate an export file"""
    try:
        export_service = ExportService(db)
        validation_result = await export_service.validate_export_file(export_id, current_user)
        
        if not validation_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not found"
            )
        
        return validation_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate export file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate export file: {str(e)}"
        )


# Health check
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "integration-service",
        "version": "1.0.0"
    }


# NLE Plugin support endpoints
@router.get("/nle/plugins")
async def get_nle_plugins():
    """Get available NLE plugins"""
    plugins = [
        {
            "nle": "avid",
            "name": "Avid Media Composer",
            "supported_formats": ["aaf"],
            "version": "1.0.0",
            "status": "available"
        },
        {
            "nle": "premiere",
            "name": "Adobe Premiere Pro",
            "supported_formats": ["xml"],
            "version": "1.0.0",
            "status": "available"
        },
        {
            "nle": "resolve",
            "name": "DaVinci Resolve",
            "supported_formats": ["edl", "xml"],
            "version": "1.0.0",
            "status": "development"
        },
        {
            "nle": "fcpx",
            "name": "Final Cut Pro X",
            "supported_formats": ["xml"],
            "version": "1.0.0",
            "status": "planned"
        }
    ]
    
    return plugins


@router.get("/nle/plugin/{nle_name}/status")
async def get_nle_plugin_status(nle_name: str):
    """Get NLE plugin status"""
    plugins = {
        "avid": {"status": "available", "version": "1.0.0"},
        "premiere": {"status": "available", "version": "1.0.0"},
        "resolve": {"status": "development", "version": "0.9.0"},
        "fcpx": {"status": "planned", "version": "0.1.0"}
    }
    
    plugin = plugins.get(nle_name.lower())
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NLE plugin '{nle_name}' not found"
        )
    
    return plugin
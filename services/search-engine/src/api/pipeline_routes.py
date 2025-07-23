"""
Pipeline API routes for handling data ingestion from other services
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List, Dict, Any
import structlog

from ..services.data_pipeline import DataPipeline, get_data_pipeline
from ..core.exceptions import IndexingError

logger = structlog.get_logger()
router = APIRouter(prefix="/pipeline", tags=["data-pipeline"])


@router.post("/asset/event")
async def process_asset_event(
    event_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    pipeline: DataPipeline = Depends(get_data_pipeline)
):
    """
    Process an asset event (create/update/delete)
    
    This endpoint is called by the asset-management service when
    assets are created, updated, or deleted.
    """
    try:
        asset_id = event_data.get("asset_id")
        event_type = event_data.get("event_type", "update")
        
        logger.info("asset_event_received", asset_id=asset_id, event_type=event_type)
        
        if event_type == "delete":
            # Handle asset deletion
            background_tasks.add_task(pipeline.delete_asset_data, asset_id)
            return {"message": "Asset deletion queued", "asset_id": asset_id}
        else:
            # Handle asset creation/update
            success = await pipeline.process_asset_event(event_data)
            
            if success:
                return {"message": "Asset event processed successfully", "asset_id": asset_id}
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to process asset event"
                )
                
    except Exception as e:
        logger.error("asset_event_processing_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process asset event"
        )


@router.post("/metadata/event")
async def process_metadata_event(
    event_data: Dict[str, Any],
    pipeline: DataPipeline = Depends(get_data_pipeline)
):
    """
    Process a metadata event (create/update)
    
    This endpoint is called by the metadata service when
    metadata is created or updated.
    """
    try:
        asset_id = event_data.get("asset_id")
        
        logger.info("metadata_event_received", asset_id=asset_id)
        
        success = await pipeline.process_metadata_event(event_data)
        
        if success:
            return {"message": "Metadata event processed successfully", "asset_id": asset_id}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process metadata event"
            )
            
    except Exception as e:
        logger.error("metadata_event_processing_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process metadata event"
        )


@router.post("/content/event")
async def process_content_event(
    event_data: Dict[str, Any],
    pipeline: DataPipeline = Depends(get_data_pipeline)
):
    """
    Process a content event (transcript, OCR, etc.)
    
    This endpoint is called by the AI/ML service when
    content analysis is completed.
    """
    try:
        asset_id = event_data.get("asset_id")
        content_type = event_data.get("content_type")
        
        logger.info("content_event_received", asset_id=asset_id, content_type=content_type)
        
        success = await pipeline.process_content_event(event_data)
        
        if success:
            return {"message": "Content event processed successfully", "asset_id": asset_id}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process content event"
            )
            
    except Exception as e:
        logger.error("content_event_processing_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process content event"
        )


@router.post("/bulk/{data_type}")
async def process_bulk_data(
    data_type: str,
    data_items: List[Dict[str, Any]],
    background_tasks: BackgroundTasks,
    pipeline: DataPipeline = Depends(get_data_pipeline)
):
    """
    Process bulk data items
    
    Supported data types: asset, metadata, content
    """
    try:
        if data_type not in ["asset", "metadata", "content"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid data type: {data_type}"
            )
        
        logger.info("bulk_data_received", data_type=data_type, count=len(data_items))
        
        # Process bulk data in background for large datasets
        if len(data_items) > 100:
            background_tasks.add_task(pipeline.process_bulk_data, data_items, data_type)
            return {
                "message": f"Bulk {data_type} processing queued",
                "count": len(data_items),
                "status": "queued"
            }
        else:
            # Process immediately for smaller datasets
            result = await pipeline.process_bulk_data(data_items, data_type)
            return {
                "message": f"Bulk {data_type} processing completed",
                "result": result
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("bulk_data_processing_error", data_type=data_type, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process bulk data"
        )


@router.delete("/asset/{asset_id}")
async def delete_asset_data(
    asset_id: str,
    pipeline: DataPipeline = Depends(get_data_pipeline)
):
    """
    Delete all data related to an asset from search indices
    """
    try:
        logger.info("asset_deletion_requested", asset_id=asset_id)
        
        results = await pipeline.delete_asset_data(asset_id)
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        return {
            "message": f"Asset deletion completed ({success_count}/{total_count} successful)",
            "asset_id": asset_id,
            "results": results,
            "success": success_count == total_count
        }
        
    except Exception as e:
        logger.error("asset_deletion_error", asset_id=asset_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete asset data"
        )


@router.post("/reindex/{data_type}")
async def trigger_reindex(
    data_type: str,
    asset_ids: List[str],
    background_tasks: BackgroundTasks,
    pipeline: DataPipeline = Depends(get_data_pipeline)
):
    """
    Trigger reindexing for specific assets
    
    This endpoint can be used to reindex data when the search
    schema changes or data becomes inconsistent.
    """
    try:
        if data_type not in ["asset", "metadata", "content", "all"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid data type: {data_type}"
            )
        
        logger.info("reindex_requested", data_type=data_type, asset_count=len(asset_ids))
        
        # Queue reindexing task
        background_tasks.add_task(_perform_reindex, pipeline, data_type, asset_ids)
        
        return {
            "message": f"Reindexing queued for {len(asset_ids)} assets",
            "data_type": data_type,
            "asset_count": len(asset_ids),
            "status": "queued"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("reindex_error", data_type=data_type, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger reindexing"
        )


async def _perform_reindex(pipeline: DataPipeline, data_type: str, asset_ids: List[str]):
    """
    Background task to perform reindexing
    
    In a real implementation, this would fetch fresh data from
    the source services and reindex it.
    """
    try:
        logger.info("reindex_started", data_type=data_type, asset_count=len(asset_ids))
        
        # This is a placeholder - in reality, you would:
        # 1. Fetch fresh data from the relevant services
        # 2. Process and reindex the data
        # 3. Log the results
        
        for asset_id in asset_ids:
            try:
                # Placeholder for actual reindexing logic
                logger.info("reindexing_asset", asset_id=asset_id, data_type=data_type)
                
                # In reality:
                # - Fetch asset data from asset-management service
                # - Fetch metadata from metadata service
                # - Fetch content from AI/ML service
                # - Process and index the data
                
            except Exception as e:
                logger.error("asset_reindex_failed", asset_id=asset_id, error=str(e))
                continue
        
        logger.info("reindex_completed", data_type=data_type, asset_count=len(asset_ids))
        
    except Exception as e:
        logger.error("reindex_background_task_failed", data_type=data_type, error=str(e))
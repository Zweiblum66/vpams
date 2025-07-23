"""Spatial computing API routes"""

from fastapi import APIRouter
from ..models.schemas import SpatialAnchorRequest

router = APIRouter()

@router.post("/anchors")
async def create_spatial_anchor(request: SpatialAnchorRequest):
    """Create spatial anchor"""
    return {
        "anchor_id": f"anchor_{request.asset_id}",
        "status": "created"
    }

@router.get("/anchors/{anchor_id}")
async def get_spatial_anchor(anchor_id: str):
    """Get spatial anchor details"""
    return {
        "anchor_id": anchor_id,
        "status": "active"
    }
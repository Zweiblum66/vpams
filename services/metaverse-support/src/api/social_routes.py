"""Social features API routes"""

from fastapi import APIRouter
from ..models.schemas import VirtualEventRequest, SocialInteractionConfig

router = APIRouter()

@router.post("/events")
async def create_virtual_event(request: VirtualEventRequest):
    """Create virtual event"""
    return {
        "event_id": f"event_{request.name.replace(' ', '_')}",
        "status": "created"
    }

@router.post("/interactions/configure")
async def configure_social_interactions(config: SocialInteractionConfig):
    """Configure social interaction features"""
    return {
        "voice_chat": config.voice_chat,
        "text_chat": config.text_chat,
        "status": "configured"
    }
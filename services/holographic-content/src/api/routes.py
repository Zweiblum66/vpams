"""API routes for holographic content service"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, Any, List
import structlog

from ..models.schemas import (
    HologramCaptureRequest, HologramCaptureResponse,
    HologramProcessRequest, HologramProcessResponse,
    HologramDisplayRequest, HologramDisplayResponse,
    SpatialInteractionRequest, SpatialInteractionResponse,
    StreamingRequest, StreamingResponse,
    LightFieldProcessRequest, LightFieldDisplayRequest,
    ProjectionRequest, ProjectionResponse,
    NeuralRenderRequest, NeuralRenderResponse,
    InteractionSessionRequest, GestureInput, VoiceCommand, EyeGazeData,
    StreamMetricsResponse, ViewerInfo
)

logger = structlog.get_logger()

# Create routers
hologram_router = APIRouter()
capture_router = APIRouter()
processing_router = APIRouter()
display_router = APIRouter()
interaction_router = APIRouter()
streaming_router = APIRouter()


# Main hologram endpoints
@hologram_router.get("/devices")
async def get_supported_devices(request: Request) -> Dict[str, Any]:
    """Get list of all supported holographic devices"""
    try:
        manager = request.app.state.hologram_manager
        devices = await manager.get_supported_devices()
        return {
            "status": "success",
            "devices": devices
        }
    except Exception as e:
        logger.error("Failed to get supported devices", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@hologram_router.get("/capabilities")
async def get_holographic_capabilities(request: Request) -> Dict[str, Any]:
    """Get holographic processing capabilities"""
    try:
        manager = request.app.state.hologram_manager
        capabilities = await manager.get_processing_capabilities()
        return {
            "status": "success",
            "capabilities": capabilities
        }
    except Exception as e:
        logger.error("Failed to get capabilities", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Capture endpoints
@capture_router.post("/start", response_model=HologramCaptureResponse)
async def start_capture(
    capture_request: HologramCaptureRequest,
    request: Request
) -> HologramCaptureResponse:
    """Start volumetric capture"""
    try:
        manager = request.app.state.hologram_manager
        result = await manager.capture_hologram(capture_request.dict())
        return HologramCaptureResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Capture failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@capture_router.post("/{capture_id}/stop")
async def stop_capture(capture_id: str, request: Request) -> Dict[str, Any]:
    """Stop active capture"""
    try:
        capture_service = request.app.state.hologram_manager.services.get('volumetric_capture')
        if not capture_service:
            raise HTTPException(status_code=503, detail="Capture service not available")
        
        result = await capture_service.stop_capture(capture_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to stop capture", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@capture_router.get("/{capture_id}/status")
async def get_capture_status(capture_id: str, request: Request) -> Dict[str, Any]:
    """Get capture session status"""
    try:
        capture_service = request.app.state.hologram_manager.services.get('volumetric_capture')
        if not capture_service:
            raise HTTPException(status_code=503, detail="Capture service not available")
        
        status = await capture_service.get_capture_status(capture_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get capture status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Processing endpoints
@processing_router.post("/neural", response_model=NeuralRenderResponse)
async def process_neural_rendering(
    render_request: NeuralRenderRequest,
    request: Request
) -> NeuralRenderResponse:
    """Process hologram using neural rendering"""
    try:
        manager = request.app.state.hologram_manager
        result = await manager.process_hologram(
            render_request.hologram_id,
            render_request.dict()
        )
        return NeuralRenderResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Neural rendering failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@processing_router.post("/light-field", response_model=HologramProcessResponse)
async def process_light_field(
    process_request: LightFieldProcessRequest,
    request: Request
) -> HologramProcessResponse:
    """Process hologram for light field display"""
    try:
        light_field_service = request.app.state.hologram_manager.services.get('light_field')
        if not light_field_service:
            raise HTTPException(status_code=503, detail="Light field service not available")
        
        result = await light_field_service.process(
            process_request.hologram_id,
            process_request.dict()
        )
        return HologramProcessResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Light field processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@processing_router.get("/{render_id}/status")
async def get_render_status(render_id: str, request: Request) -> Dict[str, Any]:
    """Get rendering status"""
    try:
        neural_service = request.app.state.hologram_manager.services.get('neural_rendering')
        if not neural_service:
            raise HTTPException(status_code=503, detail="Neural rendering service not available")
        
        status = await neural_service.get_render_status(render_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get render status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@processing_router.post("/{render_id}/synthesize-view")
async def synthesize_novel_view(
    render_id: str,
    view_params: Dict[str, Any],
    request: Request
) -> Dict[str, Any]:
    """Synthesize novel view from neural model"""
    try:
        neural_service = request.app.state.hologram_manager.services.get('neural_rendering')
        if not neural_service:
            raise HTTPException(status_code=503, detail="Neural rendering service not available")
        
        result = await neural_service.synthesize_novel_view(render_id, view_params)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("View synthesis failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Display endpoints
@display_router.post("/light-field", response_model=HologramDisplayResponse)
async def display_on_light_field(
    display_request: LightFieldDisplayRequest,
    request: Request
) -> HologramDisplayResponse:
    """Display hologram on light field device"""
    try:
        manager = request.app.state.hologram_manager
        result = await manager.display_hologram(
            display_request.hologram_id,
            display_request.dict()
        )
        return HologramDisplayResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Light field display failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@display_router.post("/projection", response_model=ProjectionResponse)
async def start_projection(
    projection_request: ProjectionRequest,
    request: Request
) -> ProjectionResponse:
    """Start holographic projection"""
    try:
        projection_service = request.app.state.hologram_manager.services.get('holographic_projection')
        if not projection_service:
            raise HTTPException(status_code=503, detail="Projection service not available")
        
        result = await projection_service.project(
            projection_request.hologram_id,
            projection_request.dict()
        )
        return ProjectionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Projection failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@display_router.post("/{display_id}/stop")
async def stop_display(display_id: str, request: Request) -> Dict[str, Any]:
    """Stop active display/projection"""
    try:
        # Try light field service first
        light_field_service = request.app.state.hologram_manager.services.get('light_field')
        if light_field_service and display_id in light_field_service.active_displays:
            return await light_field_service.stop_display(display_id)
        
        # Try projection service
        projection_service = request.app.state.hologram_manager.services.get('holographic_projection')
        if projection_service and display_id in projection_service.active_projections:
            return await projection_service.stop_projection(display_id)
        
        raise ValueError(f"Display '{display_id}' not found")
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to stop display", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@display_router.put("/{projection_id}/update")
async def update_projection(
    projection_id: str,
    updates: Dict[str, Any],
    request: Request
) -> Dict[str, Any]:
    """Update projection parameters"""
    try:
        projection_service = request.app.state.hologram_manager.services.get('holographic_projection')
        if not projection_service:
            raise HTTPException(status_code=503, detail="Projection service not available")
        
        result = await projection_service.update_projection(projection_id, updates)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to update projection", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@display_router.post("/{projection_id}/anchor")
async def add_spatial_anchor(
    projection_id: str,
    anchor_data: Dict[str, Any],
    request: Request
) -> Dict[str, Any]:
    """Add spatial anchor for AR projection"""
    try:
        projection_service = request.app.state.hologram_manager.services.get('holographic_projection')
        if not projection_service:
            raise HTTPException(status_code=503, detail="Projection service not available")
        
        result = await projection_service.add_spatial_anchor(projection_id, anchor_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to add anchor", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Interaction endpoints
@interaction_router.post("/session", response_model=SpatialInteractionResponse)
async def create_interaction_session(
    session_request: InteractionSessionRequest,
    request: Request
) -> SpatialInteractionResponse:
    """Create spatial interaction session"""
    try:
        manager = request.app.state.hologram_manager
        result = await manager.enable_interaction(
            session_request.hologram_id,
            session_request.dict()
        )
        return SpatialInteractionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create interaction session", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@interaction_router.post("/{session_id}/gesture")
async def process_gesture(
    session_id: str,
    gesture: GestureInput,
    request: Request
) -> Dict[str, Any]:
    """Process hand gesture input"""
    try:
        interaction_service = request.app.state.hologram_manager.services.get('spatial_interaction')
        if not interaction_service:
            raise HTTPException(status_code=503, detail="Interaction service not available")
        
        result = await interaction_service.process_hand_gesture(session_id, gesture.dict())
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Gesture processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@interaction_router.post("/{session_id}/voice")
async def process_voice_command(
    session_id: str,
    voice_command: VoiceCommand,
    request: Request
) -> Dict[str, Any]:
    """Process voice command"""
    try:
        interaction_service = request.app.state.hologram_manager.services.get('spatial_interaction')
        if not interaction_service:
            raise HTTPException(status_code=503, detail="Interaction service not available")
        
        result = await interaction_service.process_voice_command(session_id, voice_command.dict())
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Voice command processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@interaction_router.post("/{session_id}/gaze")
async def process_eye_gaze(
    session_id: str,
    gaze_data: EyeGazeData,
    request: Request
) -> Dict[str, Any]:
    """Process eye gaze data"""
    try:
        interaction_service = request.app.state.hologram_manager.services.get('spatial_interaction')
        if not interaction_service:
            raise HTTPException(status_code=503, detail="Interaction service not available")
        
        result = await interaction_service.process_eye_gaze(session_id, gaze_data.dict())
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Eye gaze processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@interaction_router.post("/{session_id}/haptic")
async def trigger_haptic_feedback(
    session_id: str,
    haptic_event: Dict[str, Any],
    request: Request
) -> Dict[str, Any]:
    """Trigger haptic feedback"""
    try:
        interaction_service = request.app.state.hologram_manager.services.get('spatial_interaction')
        if not interaction_service:
            raise HTTPException(status_code=503, detail="Interaction service not available")
        
        result = await interaction_service.trigger_haptic(session_id, haptic_event)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Haptic trigger failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@interaction_router.get("/{session_id}/analytics")
async def get_interaction_analytics(session_id: str, request: Request) -> Dict[str, Any]:
    """Get interaction session analytics"""
    try:
        interaction_service = request.app.state.hologram_manager.services.get('spatial_interaction')
        if not interaction_service:
            raise HTTPException(status_code=503, detail="Interaction service not available")
        
        analytics = await interaction_service.get_interaction_analytics(session_id)
        return analytics
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get analytics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@interaction_router.delete("/{session_id}")
async def end_interaction_session(session_id: str, request: Request) -> Dict[str, Any]:
    """End interaction session"""
    try:
        interaction_service = request.app.state.hologram_manager.services.get('spatial_interaction')
        if not interaction_service:
            raise HTTPException(status_code=503, detail="Interaction service not available")
        
        result = await interaction_service.disable(session_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to end session", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Streaming endpoints
@streaming_router.post("/start", response_model=StreamingResponse)
async def start_streaming(
    stream_request: StreamingRequest,
    request: Request
) -> StreamingResponse:
    """Start holographic streaming"""
    try:
        manager = request.app.state.hologram_manager
        result = await manager.stream_hologram(
            stream_request.hologram_id,
            stream_request.dict()
        )
        return StreamingResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Streaming failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@streaming_router.post("/{stream_id}/viewer")
async def add_stream_viewer(
    stream_id: str,
    viewer_info: ViewerInfo,
    request: Request
) -> Dict[str, Any]:
    """Add viewer to stream"""
    try:
        streaming_service = request.app.state.hologram_manager.services.get('streaming')
        if not streaming_service:
            raise HTTPException(status_code=503, detail="Streaming service not available")
        
        result = await streaming_service.add_viewer(stream_id, viewer_info.dict())
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to add viewer", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@streaming_router.put("/{stream_id}/quality")
async def update_stream_quality(
    stream_id: str,
    quality_settings: Dict[str, Any],
    request: Request
) -> Dict[str, Any]:
    """Update stream quality settings"""
    try:
        streaming_service = request.app.state.hologram_manager.services.get('streaming')
        if not streaming_service:
            raise HTTPException(status_code=503, detail="Streaming service not available")
        
        result = await streaming_service.update_stream_quality(stream_id, quality_settings)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to update quality", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@streaming_router.get("/{stream_id}/metrics", response_model=StreamMetricsResponse)
async def get_stream_metrics(stream_id: str, request: Request) -> StreamMetricsResponse:
    """Get streaming metrics"""
    try:
        streaming_service = request.app.state.hologram_manager.services.get('streaming')
        if not streaming_service:
            raise HTTPException(status_code=503, detail="Streaming service not available")
        
        metrics = await streaming_service.get_stream_metrics(stream_id)
        return StreamMetricsResponse(**metrics)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@streaming_router.post("/{stream_id}/stop")
async def stop_streaming(stream_id: str, request: Request) -> Dict[str, Any]:
    """Stop streaming session"""
    try:
        streaming_service = request.app.state.hologram_manager.services.get('streaming')
        if not streaming_service:
            raise HTTPException(status_code=503, detail="Streaming service not available")
        
        result = await streaming_service.stop_stream(stream_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to stop stream", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
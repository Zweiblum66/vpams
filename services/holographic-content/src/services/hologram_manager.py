"""Central manager for holographic content operations"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from ..core.config import settings
from .volumetric_capture_service import VolumetricCaptureService
from .light_field_service import LightFieldService
from .holographic_projection_service import HolographicProjectionService
from .neural_rendering_service import NeuralRenderingService
from .spatial_interaction_service import SpatialInteractionService
from .hologram_streaming_service import HologramStreamingService

logger = structlog.get_logger()


class HologramManager:
    """Central coordinator for all holographic services"""
    
    def __init__(self):
        self.services: Dict[str, Any] = {}
        self.initialized = False
        self.health_status: Dict[str, Any] = {}
        
    async def initialize(self):
        """Initialize all holographic services"""
        try:
            logger.info("Initializing Hologram Manager")
            
            # Initialize volumetric capture service
            if settings.ENABLE_VOLUMETRIC_CAPTURE:
                self.services['volumetric_capture'] = VolumetricCaptureService()
                await self.services['volumetric_capture'].initialize()
                logger.info("Volumetric capture service initialized")
            
            # Initialize light field display service
            if settings.ENABLE_LIGHT_FIELD_DISPLAY:
                self.services['light_field'] = LightFieldService()
                await self.services['light_field'].initialize()
                logger.info("Light field display service initialized")
            
            # Initialize holographic projection service
            if settings.ENABLE_HOLOGRAPHIC_PROJECTION:
                self.services['holographic_projection'] = HolographicProjectionService()
                await self.services['holographic_projection'].initialize()
                logger.info("Holographic projection service initialized")
            
            # Initialize neural rendering service
            if settings.ENABLE_NEURAL_RENDERING:
                self.services['neural_rendering'] = NeuralRenderingService()
                await self.services['neural_rendering'].initialize()
                logger.info("Neural rendering service initialized")
            
            # Initialize spatial interaction service
            self.services['spatial_interaction'] = SpatialInteractionService()
            await self.services['spatial_interaction'].initialize()
            logger.info("Spatial interaction service initialized")
            
            # Initialize streaming service
            if settings.ENABLE_REAL_TIME_STREAMING:
                self.services['streaming'] = HologramStreamingService()
                await self.services['streaming'].initialize()
                logger.info("Hologram streaming service initialized")
            
            self.initialized = True
            logger.info("Hologram Manager initialized successfully")
            
            # Start background health monitoring
            asyncio.create_task(self._monitor_health())
            
        except Exception as e:
            logger.error("Failed to initialize Hologram Manager", error=str(e))
            raise
    
    async def shutdown(self):
        """Shutdown all services"""
        logger.info("Shutting down Hologram Manager")
        
        for service_name, service in self.services.items():
            try:
                if hasattr(service, 'shutdown'):
                    await service.shutdown()
                logger.info(f"Shut down {service_name} service")
            except Exception as e:
                logger.error(f"Error shutting down {service_name}", error=str(e))
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all services"""
        health = {
            "status": "healthy" if self.initialized else "unhealthy",
            "initialized": self.initialized,
            "services": {}
        }
        
        for service_name, service in self.services.items():
            try:
                if hasattr(service, 'health_check'):
                    service_health = await service.health_check()
                    health["services"][service_name] = service_health
                else:
                    health["services"][service_name] = {"status": "unknown"}
            except Exception as e:
                health["services"][service_name] = {
                    "status": "error",
                    "error": str(e)
                }
                health["status"] = "degraded"
        
        self.health_status = health
        return health
    
    async def _monitor_health(self):
        """Background task to monitor service health"""
        while self.initialized:
            try:
                await self.health_check()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error("Health monitoring error", error=str(e))
                await asyncio.sleep(60)  # Wait longer on error
    
    async def capture_hologram(self, capture_config: Dict[str, Any]) -> Dict[str, Any]:
        """Capture holographic content"""
        if 'volumetric_capture' not in self.services:
            raise ValueError("Volumetric capture service not available")
        
        return await self.services['volumetric_capture'].capture(capture_config)
    
    async def process_hologram(self, hologram_id: str, processing_config: Dict[str, Any]) -> Dict[str, Any]:
        """Process captured holographic data"""
        processing_type = processing_config.get('type', 'neural')
        
        if processing_type == 'neural' and 'neural_rendering' in self.services:
            return await self.services['neural_rendering'].process(hologram_id, processing_config)
        elif processing_type == 'light_field' and 'light_field' in self.services:
            return await self.services['light_field'].process(hologram_id, processing_config)
        else:
            raise ValueError(f"Processing type '{processing_type}' not available")
    
    async def display_hologram(self, hologram_id: str, display_config: Dict[str, Any]) -> Dict[str, Any]:
        """Display hologram on specified device"""
        display_type = display_config.get('type', 'light_field')
        
        if display_type == 'light_field' and 'light_field' in self.services:
            return await self.services['light_field'].display(hologram_id, display_config)
        elif display_type == 'projection' and 'holographic_projection' in self.services:
            return await self.services['holographic_projection'].project(hologram_id, display_config)
        else:
            raise ValueError(f"Display type '{display_type}' not available")
    
    async def stream_hologram(self, hologram_id: str, stream_config: Dict[str, Any]) -> Dict[str, Any]:
        """Stream holographic content"""
        if 'streaming' not in self.services:
            raise ValueError("Streaming service not available")
        
        return await self.services['streaming'].start_stream(hologram_id, stream_config)
    
    async def enable_interaction(self, hologram_id: str, interaction_config: Dict[str, Any]) -> Dict[str, Any]:
        """Enable spatial interaction with hologram"""
        if 'spatial_interaction' not in self.services:
            raise ValueError("Spatial interaction service not available")
        
        return await self.services['spatial_interaction'].enable(hologram_id, interaction_config)
    
    async def get_supported_devices(self) -> Dict[str, List[str]]:
        """Get list of supported capture and display devices"""
        devices = {
            "capture_devices": [],
            "display_devices": [],
            "projection_devices": []
        }
        
        if 'volumetric_capture' in self.services:
            devices['capture_devices'] = await self.services['volumetric_capture'].get_available_devices()
        
        if 'light_field' in self.services:
            devices['display_devices'] = await self.services['light_field'].get_available_displays()
        
        if 'holographic_projection' in self.services:
            devices['projection_devices'] = await self.services['holographic_projection'].get_available_projectors()
        
        return devices
    
    async def get_processing_capabilities(self) -> Dict[str, Any]:
        """Get available processing capabilities"""
        capabilities = {}
        
        if 'neural_rendering' in self.services:
            capabilities['neural_rendering'] = await self.services['neural_rendering'].get_capabilities()
        
        if 'light_field' in self.services:
            capabilities['light_field_processing'] = await self.services['light_field'].get_capabilities()
        
        return capabilities
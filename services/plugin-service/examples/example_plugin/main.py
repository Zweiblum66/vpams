"""
Example Processor Plugin for MAMS
"""

import asyncio
from typing import Dict, Any, List
from PIL import Image
import io

from plugin_base import (
    ProcessorPlugin,
    PluginType,
    PluginHook,
    PluginContext,
    PluginResult,
    PluginEvent
)


class ExampleProcessorPlugin(ProcessorPlugin):
    """Example plugin that demonstrates the MAMS plugin architecture"""
    
    async def initialize(self) -> bool:
        """Initialize the plugin"""
        self.logger = self._setup_logger()
        self.logger.info(f"Initializing {self.metadata.name} v{self.metadata.version}")
        
        # Register event handlers
        self.register_event_handler("asset.created", self._on_asset_created)
        self.register_event_handler("asset.updated", self._on_asset_updated)
        
        # Validate configuration
        if not await self.validate_config():
            self.logger.error("Invalid configuration")
            return False
        
        self.logger.info("Plugin initialized successfully")
        return True
    
    async def shutdown(self) -> bool:
        """Cleanup plugin resources"""
        self.logger.info("Shutting down plugin")
        # Cleanup any resources
        return True
    
    async def validate_config(self) -> bool:
        """Validate plugin configuration"""
        quality = self.config.settings.get("quality", 85)
        if not 1 <= quality <= 100:
            return False
        
        format = self.config.settings.get("format", "jpg")
        if format not in ["jpg", "png", "webp"]:
            return False
        
        return True
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get plugin health status"""
        return {
            "status": "healthy",
            "version": self.metadata.version,
            "uptime": self._get_uptime(),
            "processed_count": getattr(self, "_processed_count", 0),
            "error_count": getattr(self, "_error_count", 0)
        }
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats"""
        return ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff"]
    
    async def process_asset(self, asset_id: str, context: PluginContext) -> PluginResult:
        """Process an asset"""
        self.logger.info(f"Processing asset {asset_id}")
        
        try:
            # Get asset information from context
            asset_path = context.metadata.get("file_path")
            if not asset_path:
                return PluginResult(
                    success=False,
                    error="No file path provided in context"
                )
            
            # Load image
            image = Image.open(asset_path)
            
            # Apply processing based on settings
            quality = self.config.settings.get("quality", 85)
            output_format = self.config.settings.get("format", "jpg")
            enable_optimization = self.config.settings.get("enable_optimization", True)
            
            # Process image
            processed_image = await self._process_image(image, quality, enable_optimization)
            
            # Save processed image
            output_buffer = io.BytesIO()
            if output_format == "jpg":
                processed_image.save(output_buffer, format="JPEG", quality=quality, optimize=enable_optimization)
            elif output_format == "png":
                processed_image.save(output_buffer, format="PNG", optimize=enable_optimization)
            elif output_format == "webp":
                processed_image.save(output_buffer, format="WEBP", quality=quality, method=6)
            
            # Update processed count
            self._processed_count = getattr(self, "_processed_count", 0) + 1
            
            return PluginResult(
                success=True,
                data={
                    "asset_id": asset_id,
                    "output_format": output_format,
                    "output_size": output_buffer.tell(),
                    "original_size": image.size,
                    "processed": True
                },
                metadata={
                    "processing_time_ms": 100,  # Would measure actual time
                    "quality": quality,
                    "optimization": enable_optimization
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error processing asset {asset_id}: {str(e)}")
            self._error_count = getattr(self, "_error_count", 0) + 1
            
            return PluginResult(
                success=False,
                error=str(e),
                metadata={"asset_id": asset_id}
            )
    
    async def _process_image(self, image: Image.Image, quality: int, optimize: bool) -> Image.Image:
        """Apply image processing"""
        # Example processing - in real plugin would do actual processing
        # For now, just return the original image
        return image
    
    @PluginHook("pre_process", priority=10)
    async def pre_process_hook(self, context: PluginContext, **kwargs) -> PluginResult:
        """Hook called before processing"""
        asset_id = kwargs.get("asset_id")
        self.logger.info(f"Pre-processing hook for asset {asset_id}")
        
        # Validate asset
        validation_result = await self._validate_asset(asset_id, context)
        if not validation_result.success:
            return validation_result
        
        return PluginResult(success=True, data={"validated": True})
    
    @PluginHook("post_process", priority=5)
    async def post_process_hook(self, context: PluginContext, **kwargs) -> PluginResult:
        """Hook called after processing"""
        asset_id = kwargs.get("asset_id")
        self.logger.info(f"Post-processing hook for asset {asset_id}")
        
        # Could do additional processing, notifications, etc.
        return PluginResult(
            success=True,
            data={"post_processed": True},
            metadata={"timestamp": context.start_time.isoformat()}
        )
    
    @PluginHook("validate_asset")
    async def validate_asset_hook(self, context: PluginContext, **kwargs) -> PluginResult:
        """Validate an asset"""
        asset_id = kwargs.get("asset_id")
        return await self._validate_asset(asset_id, context)
    
    async def _validate_asset(self, asset_id: str, context: PluginContext) -> PluginResult:
        """Internal asset validation"""
        file_path = context.metadata.get("file_path")
        if not file_path:
            return PluginResult(
                success=False,
                error="No file path provided"
            )
        
        # Check file extension
        import os
        _, ext = os.path.splitext(file_path)
        ext = ext.lower().lstrip('.')
        
        if ext not in self.get_supported_formats():
            return PluginResult(
                success=False,
                error=f"Unsupported format: {ext}",
                data={"supported_formats": self.get_supported_formats()}
            )
        
        return PluginResult(success=True, data={"valid": True, "format": ext})
    
    async def _on_asset_created(self, event: PluginEvent) -> PluginResult:
        """Handle asset created event"""
        asset_id = event.data.get("asset_id")
        self.logger.info(f"Asset created event received for {asset_id}")
        
        # Could trigger automatic processing
        if self.config.settings.get("auto_process_new_assets", False):
            # Would queue for processing
            pass
        
        return PluginResult(success=True)
    
    async def _on_asset_updated(self, event: PluginEvent) -> PluginResult:
        """Handle asset updated event"""
        asset_id = event.data.get("asset_id")
        self.logger.info(f"Asset updated event received for {asset_id}")
        return PluginResult(success=True)
    
    def _setup_logger(self):
        """Setup plugin logger"""
        import logging
        logger = logging.getLogger(f"plugin.{self.metadata.id}")
        logger.setLevel(logging.INFO)
        return logger
    
    def _get_uptime(self) -> float:
        """Get plugin uptime in seconds"""
        from datetime import datetime
        if hasattr(self, "_start_time"):
            return (datetime.utcnow() - self._start_time).total_seconds()
        return 0.0
"""
Sample Metadata Extractor Plugin for MAMS
"""

from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
import json

from plugin_base import (
    MetadataPlugin,
    PluginHook,
    PluginResult,
    PluginContext,
    PluginEvent
)


class SampleMetadataExtractor(MetadataPlugin):
    """Sample plugin that extracts metadata from image files"""
    
    async def initialize(self) -> bool:
        """Initialize the plugin"""
        self.logger.info(
            "Initializing Sample Metadata Extractor",
            version=self.metadata.version
        )
        
        # Validate configuration
        if not await self.validate_config():
            return False
        
        # Register event handlers
        self.register_event_handler("asset.uploaded", self.on_asset_uploaded)
        
        self.logger.info("Sample Metadata Extractor initialized successfully")
        return True
    
    async def shutdown(self) -> bool:
        """Cleanup plugin resources"""
        self.logger.info("Shutting down Sample Metadata Extractor")
        return True
    
    async def validate_config(self) -> bool:
        """Validate plugin configuration"""
        # Check if required settings are present
        extract_exif = self.config.settings.get("extract_exif", True)
        extract_iptc = self.config.settings.get("extract_iptc", True)
        
        if not isinstance(extract_exif, bool) or not isinstance(extract_iptc, bool):
            self.logger.error("Invalid configuration: extract_exif and extract_iptc must be boolean")
            return False
        
        return True
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get plugin health status"""
        return {
            "status": "healthy",
            "version": self.metadata.version,
            "uptime": (datetime.utcnow() - self.metadata.created_at).total_seconds(),
            "configuration": {
                "extract_exif": self.config.settings.get("extract_exif", True),
                "extract_iptc": self.config.settings.get("extract_iptc", True)
            }
        }
    
    @PluginHook("metadata.extract", priority=10)
    async def extract_metadata_hook(self, context: PluginContext, file_path: str, **kwargs) -> PluginResult:
        """Hook for metadata extraction"""
        self.logger.info(
            "Metadata extraction requested",
            file_path=file_path,
            user_id=context.user_id
        )
        
        try:
            metadata = await self.extract_metadata(file_path, context)
            return metadata
        except Exception as e:
            self.logger.error(
                "Failed to extract metadata",
                file_path=file_path,
                error=str(e)
            )
            return PluginResult(
                success=False,
                error=f"Failed to extract metadata: {str(e)}"
            )
    
    async def extract_metadata(self, file_path: str, context: PluginContext) -> PluginResult:
        """Extract metadata from file"""
        path = Path(file_path)
        
        # Check if file exists
        if not path.exists():
            return PluginResult(
                success=False,
                error=f"File not found: {file_path}"
            )
        
        # Check if it's an image file
        if path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
            return PluginResult(
                success=True,
                data={},
                metadata={"skipped": True, "reason": "Not an image file"}
            )
        
        extracted_metadata = {}
        
        try:
            # Open image
            with Image.open(path) as img:
                # Basic image info
                extracted_metadata["image"] = {
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "width": img.width,
                    "height": img.height
                }
                
                # Extract EXIF data if enabled
                if self.config.settings.get("extract_exif", True):
                    exif_data = self._extract_exif(img)
                    if exif_data:
                        extracted_metadata["exif"] = exif_data
                
                # Extract IPTC data if enabled
                if self.config.settings.get("extract_iptc", True):
                    iptc_data = self._extract_iptc(img)
                    if iptc_data:
                        extracted_metadata["iptc"] = iptc_data
            
            # Extract custom fields
            custom_fields = self.config.settings.get("custom_fields", [])
            if custom_fields:
                extracted_metadata["custom"] = self._extract_custom_fields(
                    path, custom_fields
                )
            
            return PluginResult(
                success=True,
                data=extracted_metadata,
                metadata={
                    "extractor": self.metadata.id,
                    "version": self.metadata.version,
                    "extracted_at": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            return PluginResult(
                success=False,
                error=f"Failed to process image: {str(e)}"
            )
    
    def _extract_exif(self, img: Image) -> Dict[str, Any]:
        """Extract EXIF data from image"""
        exif_data = {}
        
        try:
            exifdata = img.getexif()
            
            for tag_id, value in exifdata.items():
                tag = TAGS.get(tag_id, tag_id)
                
                # Convert bytes to string
                if isinstance(value, bytes):
                    try:
                        value = value.decode()
                    except:
                        value = str(value)
                
                # Handle datetime objects
                elif hasattr(value, 'isoformat'):
                    value = value.isoformat()
                
                exif_data[tag] = value
                
        except Exception as e:
            self.logger.warning(f"Failed to extract EXIF data: {str(e)}")
        
        return exif_data
    
    def _extract_iptc(self, img: Image) -> Dict[str, Any]:
        """Extract IPTC data from image"""
        iptc_data = {}
        
        try:
            # This is a simplified example
            # In a real plugin, you would use a proper IPTC library
            info = img.info
            
            if "iptc" in info:
                # Parse IPTC data
                iptc_data["raw"] = str(info["iptc"])
            
        except Exception as e:
            self.logger.warning(f"Failed to extract IPTC data: {str(e)}")
        
        return iptc_data
    
    def _extract_custom_fields(self, path: Path, fields: List[str]) -> Dict[str, Any]:
        """Extract custom metadata fields"""
        custom_data = {}
        
        for field in fields:
            # Example: Extract file system metadata
            if field == "file_created":
                custom_data[field] = datetime.fromtimestamp(
                    path.stat().st_ctime
                ).isoformat()
            elif field == "file_modified":
                custom_data[field] = datetime.fromtimestamp(
                    path.stat().st_mtime
                ).isoformat()
            elif field == "file_size":
                custom_data[field] = path.stat().st_size
        
        return custom_data
    
    async def enrich_metadata(self, metadata: Dict[str, Any], context: PluginContext) -> PluginResult:
        """Enrich existing metadata"""
        enriched = metadata.copy()
        
        # Add enrichment timestamp
        enriched["enrichment"] = {
            "plugin": self.metadata.id,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": context.user_id
        }
        
        # Example: Add calculated fields
        if "image" in metadata:
            img_data = metadata["image"]
            if "width" in img_data and "height" in img_data:
                enriched["image"]["aspect_ratio"] = img_data["width"] / img_data["height"]
                enriched["image"]["megapixels"] = (img_data["width"] * img_data["height"]) / 1_000_000
        
        return PluginResult(
            success=True,
            data=enriched,
            metadata={"enriched_fields": ["aspect_ratio", "megapixels"]}
        )
    
    async def on_asset_uploaded(self, event: PluginEvent) -> PluginResult:
        """Handle asset uploaded event"""
        asset_id = event.data.get("asset_id")
        file_path = event.data.get("file_path")
        
        self.logger.info(
            "Asset uploaded event received",
            asset_id=asset_id,
            file_path=file_path
        )
        
        if not file_path:
            return PluginResult(
                success=False,
                error="No file path provided in event"
            )
        
        # Create context from event
        context = PluginContext(
            user_id=event.data.get("user_id"),
            tenant_id=event.data.get("tenant_id")
        )
        
        # Extract metadata
        return await self.extract_metadata(file_path, context)
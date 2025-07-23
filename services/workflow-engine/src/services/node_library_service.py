"""
Node Library Service

This module manages the node library for the visual workflow designer including:
- Available node types and their configurations
- Node parameter schemas and validation
- Node documentation and examples
- Node categorization and search
- Custom node registration
"""

import json
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
import structlog

from ..models.schemas import (
    NodeLibraryItem, TaskType, NodeType
)
from ..core.exceptions import (
    NodeLibraryError, NodeNotFoundError
)

logger = structlog.get_logger()


class NodeLibraryService:
    """
    Service for managing the workflow node library
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self._node_library = None
    
    async def get_available_nodes(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[NodeLibraryItem]:
        """
        Get available workflow nodes for the designer
        """
        # Initialize node library if not already loaded
        if self._node_library is None:
            self._node_library = await self._load_node_library()
        
        nodes = list(self._node_library.values())
        
        # Apply category filter
        if category:
            nodes = [node for node in nodes if node.category == category]
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            nodes = [
                node for node in nodes
                if (search_lower in node.name.lower() or
                    search_lower in node.description.lower())
            ]
        
        logger.info(
            "Node library queried",
            total_nodes=len(nodes),
            category=category,
            search=search
        )
        
        return nodes
    
    async def get_node_details(self, node_type: str) -> Optional[NodeLibraryItem]:
        """
        Get detailed information about a specific node type
        """
        # Initialize node library if not already loaded
        if self._node_library is None:
            self._node_library = await self._load_node_library()
        
        node = self._node_library.get(node_type)
        
        if node:
            logger.info(
                "Node details retrieved",
                node_type=node_type,
                node_name=node.name
            )
        else:
            logger.warning(
                "Node not found",
                node_type=node_type
            )
        
        return node
    
    async def register_custom_node(
        self,
        node: NodeLibraryItem
    ) -> str:
        """
        Register a custom node in the library
        """
        # Initialize node library if not already loaded
        if self._node_library is None:
            self._node_library = await self._load_node_library()
        
        # Validate node
        await self._validate_node(node)
        
        # Add to library
        self._node_library[node.node_type] = node
        
        # In a real implementation, this would persist to database
        logger.info(
            "Custom node registered",
            node_type=node.node_type,
            node_name=node.name
        )
        
        return node.node_type
    
    async def _load_node_library(self) -> Dict[str, NodeLibraryItem]:
        """
        Load the node library with predefined nodes
        """
        nodes = {}
        
        # Media Processing Nodes
        nodes["transcode"] = NodeLibraryItem(
            node_type="transcode",
            name="Transcode Media",
            description="Convert media files to different formats",
            category="media_processing",
            icon="video_settings",
            color="#FF6B6B",
            input_ports=[
                {"name": "input", "type": "file", "description": "Input media file"}
            ],
            output_ports=[
                {"name": "output", "type": "file", "description": "Transcoded media file"},
                {"name": "error", "type": "error", "description": "Error output"}
            ],
            parameters={
                "format": {
                    "type": "string",
                    "enum": ["mp4", "mov", "avi", "mkv", "webm"],
                    "default": "mp4",
                    "description": "Output format"
                },
                "quality": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "ultra"],
                    "default": "medium",
                    "description": "Output quality"
                },
                "resolution": {
                    "type": "string",
                    "enum": ["720p", "1080p", "2K", "4K"],
                    "default": "1080p",
                    "description": "Output resolution"
                }
            },
            configuration_schema={
                "type": "object",
                "properties": {
                    "format": {"type": "string"},
                    "quality": {"type": "string"},
                    "resolution": {"type": "string"}
                },
                "required": ["format"]
            },
            examples=[
                {
                    "name": "Convert to MP4",
                    "description": "Convert any video to MP4 format",
                    "parameters": {
                        "format": "mp4",
                        "quality": "high",
                        "resolution": "1080p"
                    }
                }
            ],
            documentation="Transcodes video files using FFmpeg. Supports various input and output formats.",
            version="1.0.0",
            dependencies=["ffmpeg"]
        )
        
        nodes["generate_proxy"] = NodeLibraryItem(
            node_type="generate_proxy",
            name="Generate Proxy",
            description="Create low-resolution proxy files for editing",
            category="media_processing",
            icon="video_library",
            color="#4ECDC4",
            input_ports=[
                {"name": "input", "type": "file", "description": "Input media file"}
            ],
            output_ports=[
                {"name": "proxy", "type": "file", "description": "Generated proxy file"},
                {"name": "error", "type": "error", "description": "Error output"}
            ],
            parameters={
                "resolution": {
                    "type": "string",
                    "enum": ["360p", "480p", "720p"],
                    "default": "480p",
                    "description": "Proxy resolution"
                },
                "format": {
                    "type": "string",
                    "enum": ["mp4", "mov", "prores_proxy"],
                    "default": "mp4",
                    "description": "Proxy format"
                }
            },
            configuration_schema={
                "type": "object",
                "properties": {
                    "resolution": {"type": "string"},
                    "format": {"type": "string"}
                }
            },
            examples=[
                {
                    "name": "Standard Proxy",
                    "description": "Create 480p MP4 proxy",
                    "parameters": {
                        "resolution": "480p",
                        "format": "mp4"
                    }
                }
            ],
            documentation="Creates low-resolution proxy files for faster editing workflows."
        )
        
        nodes["generate_thumbnail"] = NodeLibraryItem(
            node_type="generate_thumbnail",
            name="Generate Thumbnail",
            description="Extract thumbnail images from video",
            category="media_processing",
            icon="image",
            color="#45B7D1",
            input_ports=[
                {"name": "input", "type": "file", "description": "Input video file"}
            ],
            output_ports=[
                {"name": "thumbnail", "type": "file", "description": "Generated thumbnail"},
                {"name": "error", "type": "error", "description": "Error output"}
            ],
            parameters={
                "timestamp": {
                    "type": "string",
                    "default": "00:00:05",
                    "description": "Timestamp for thumbnail extraction"
                },
                "format": {
                    "type": "string",
                    "enum": ["jpg", "png", "webp"],
                    "default": "jpg",
                    "description": "Thumbnail format"
                },
                "size": {
                    "type": "string",
                    "enum": ["small", "medium", "large"],
                    "default": "medium",
                    "description": "Thumbnail size"
                }
            },
            configuration_schema={
                "type": "object",
                "properties": {
                    "timestamp": {"type": "string"},
                    "format": {"type": "string"},
                    "size": {"type": "string"}
                }
            },
            examples=[
                {
                    "name": "Extract at 5 seconds",
                    "description": "Extract thumbnail at 5 second mark",
                    "parameters": {
                        "timestamp": "00:00:05",
                        "format": "jpg",
                        "size": "medium"
                    }
                }
            ],
            documentation="Extracts thumbnail images from video files at specified timestamps."
        )
        
        # File Operation Nodes
        nodes["copy_file"] = NodeLibraryItem(
            node_type="copy_file",
            name="Copy File",
            description="Copy file to another location",
            category="file_operations",
            icon="file_copy",
            color="#96CEB4",
            input_ports=[
                {"name": "input", "type": "file", "description": "Source file"}
            ],
            output_ports=[
                {"name": "output", "type": "file", "description": "Copied file"},
                {"name": "error", "type": "error", "description": "Error output"}
            ],
            parameters={
                "destination": {
                    "type": "string",
                    "description": "Destination path"
                },
                "overwrite": {
                    "type": "boolean",
                    "default": False,
                    "description": "Overwrite existing files"
                }
            },
            configuration_schema={
                "type": "object",
                "properties": {
                    "destination": {"type": "string"},
                    "overwrite": {"type": "boolean"}
                },
                "required": ["destination"]
            },
            examples=[
                {
                    "name": "Copy to Archive",
                    "description": "Copy file to archive directory",
                    "parameters": {
                        "destination": "/archive/",
                        "overwrite": False
                    }
                }
            ],
            documentation="Copies files from source to destination with optional overwrite."
        )
        
        nodes["move_file"] = NodeLibraryItem(
            node_type="move_file",
            name="Move File",
            description="Move file to another location",
            category="file_operations",
            icon="drive_file_move",
            color="#FFEAA7",
            input_ports=[
                {"name": "input", "type": "file", "description": "Source file"}
            ],
            output_ports=[
                {"name": "output", "type": "file", "description": "Moved file"},
                {"name": "error", "type": "error", "description": "Error output"}
            ],
            parameters={
                "destination": {
                    "type": "string",
                    "description": "Destination path"
                },
                "create_directories": {
                    "type": "boolean",
                    "default": True,
                    "description": "Create destination directories if they don't exist"
                }
            },
            configuration_schema={
                "type": "object",
                "properties": {
                    "destination": {"type": "string"},
                    "create_directories": {"type": "boolean"}
                },
                "required": ["destination"]
            },
            examples=[
                {
                    "name": "Move to Processing",
                    "description": "Move file to processing directory",
                    "parameters": {
                        "destination": "/processing/",
                        "create_directories": True
                    }
                }
            ],
            documentation="Moves files from source to destination, creating directories as needed."
        )
        
        # Asset Operation Nodes
        nodes["create_asset"] = NodeLibraryItem(
            node_type="create_asset",
            name="Create Asset",
            description="Create new asset in the system",
            category="asset_operations",
            icon="add_circle",
            color="#74B9FF",
            input_ports=[
                {"name": "file", "type": "file", "description": "Asset file"}
            ],
            output_ports=[
                {"name": "asset", "type": "asset", "description": "Created asset"},
                {"name": "error", "type": "error", "description": "Error output"}
            ],
            parameters={
                "name": {
                    "type": "string",
                    "description": "Asset name"
                },
                "description": {
                    "type": "string",
                    "description": "Asset description"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Asset tags"
                }
            },
            configuration_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}}
                }
            },
            examples=[
                {
                    "name": "Create Video Asset",
                    "description": "Create asset from video file",
                    "parameters": {
                        "name": "Interview_001",
                        "description": "Interview with subject",
                        "tags": ["interview", "raw"]
                    }
                }
            ],
            documentation="Creates new assets in the media asset management system."
        )
        
        # Notification Nodes
        nodes["send_email"] = NodeLibraryItem(
            node_type="send_email",
            name="Send Email",
            description="Send email notification",
            category="notifications",
            icon="email",
            color="#FD79A8",
            input_ports=[
                {"name": "input", "type": "any", "description": "Trigger input"}
            ],
            output_ports=[
                {"name": "output", "type": "any", "description": "Success output"},
                {"name": "error", "type": "error", "description": "Error output"}
            ],
            parameters={
                "to": {
                    "type": "string",
                    "description": "Recipient email address"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject"
                },
                "body": {
                    "type": "string",
                    "description": "Email body"
                },
                "template": {
                    "type": "string",
                    "description": "Email template name"
                }
            },
            configuration_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "template": {"type": "string"}
                },
                "required": ["to", "subject"]
            },
            examples=[
                {
                    "name": "Processing Complete",
                    "description": "Notify when processing is complete",
                    "parameters": {
                        "to": "user@example.com",
                        "subject": "Processing Complete",
                        "body": "Your file has been processed successfully."
                    }
                }
            ],
            documentation="Sends email notifications using configured email service."
        )
        
        # Control Flow Nodes
        nodes["condition"] = NodeLibraryItem(
            node_type="condition",
            name="Condition",
            description="Branch workflow based on conditions",
            category="control_flow",
            icon="alt_route",
            color="#FDCB6E",
            input_ports=[
                {"name": "input", "type": "any", "description": "Input to evaluate"}
            ],
            output_ports=[
                {"name": "true", "type": "any", "description": "True condition output"},
                {"name": "false", "type": "any", "description": "False condition output"}
            ],
            parameters={
                "condition": {
                    "type": "string",
                    "description": "Condition expression"
                },
                "operator": {
                    "type": "string",
                    "enum": ["equals", "not_equals", "greater_than", "less_than", "contains"],
                    "default": "equals",
                    "description": "Comparison operator"
                },
                "value": {
                    "type": "string",
                    "description": "Value to compare against"
                }
            },
            configuration_schema={
                "type": "object",
                "properties": {
                    "condition": {"type": "string"},
                    "operator": {"type": "string"},
                    "value": {"type": "string"}
                },
                "required": ["condition"]
            },
            examples=[
                {
                    "name": "Check File Size",
                    "description": "Branch based on file size",
                    "parameters": {
                        "condition": "file.size",
                        "operator": "greater_than",
                        "value": "1000000"
                    }
                }
            ],
            documentation="Evaluates conditions and branches workflow execution accordingly."
        )
        
        # AI/ML Nodes
        nodes["auto_tag"] = NodeLibraryItem(
            node_type="auto_tag",
            name="Auto Tag",
            description="Automatically tag content using AI",
            category="ai_ml",
            icon="auto_awesome",
            color="#A29BFE",
            input_ports=[
                {"name": "input", "type": "file", "description": "Content to tag"}
            ],
            output_ports=[
                {"name": "output", "type": "asset", "description": "Tagged content"},
                {"name": "tags", "type": "array", "description": "Generated tags"}
            ],
            parameters={
                "model": {
                    "type": "string",
                    "enum": ["general", "media", "objects", "faces"],
                    "default": "general",
                    "description": "AI model to use"
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.7,
                    "description": "Minimum confidence threshold"
                }
            },
            configuration_schema={
                "type": "object",
                "properties": {
                    "model": {"type": "string"},
                    "confidence": {"type": "number"}
                }
            },
            examples=[
                {
                    "name": "Tag Video Content",
                    "description": "Automatically tag video content",
                    "parameters": {
                        "model": "media",
                        "confidence": 0.8
                    }
                }
            ],
            documentation="Uses AI models to automatically generate tags for media content."
        )
        
        logger.info(
            "Node library loaded",
            total_nodes=len(nodes),
            categories=list(set(node.category for node in nodes.values()))
        )
        
        return nodes
    
    async def _validate_node(self, node: NodeLibraryItem):
        """
        Validate a node configuration
        """
        if not node.node_type:
            raise NodeLibraryError("Node type is required")
        
        if not node.name:
            raise NodeLibraryError("Node name is required")
        
        if not node.category:
            raise NodeLibraryError("Node category is required")
        
        # Validate ports
        if not node.input_ports and not node.output_ports:
            raise NodeLibraryError("Node must have at least one input or output port")
        
        # Validate parameter schema
        if node.parameters and not node.configuration_schema:
            raise NodeLibraryError("Node with parameters must have configuration schema")
        
        logger.info(
            "Node validated",
            node_type=node.node_type,
            node_name=node.name
        )
    
    async def get_node_categories(self) -> List[str]:
        """
        Get all available node categories
        """
        # Initialize node library if not already loaded
        if self._node_library is None:
            self._node_library = await self._load_node_library()
        
        categories = list(set(node.category for node in self._node_library.values()))
        categories.sort()
        
        return categories
    
    async def get_nodes_by_category(self, category: str) -> List[NodeLibraryItem]:
        """
        Get all nodes in a specific category
        """
        return await self.get_available_nodes(category=category)
    
    async def search_nodes(self, query: str) -> List[NodeLibraryItem]:
        """
        Search nodes by name and description
        """
        return await self.get_available_nodes(search=query)
    
    async def get_node_schema(self, node_type: str) -> Optional[Dict[str, Any]]:
        """
        Get the parameter schema for a specific node type
        """
        node = await self.get_node_details(node_type)
        if node:
            return node.configuration_schema
        return None
    
    async def validate_node_parameters(
        self,
        node_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate node parameters against schema
        """
        node = await self.get_node_details(node_type)
        if not node:
            raise NodeNotFoundError(f"Node type {node_type} not found")
        
        # Basic validation - in a real implementation, use jsonschema
        schema = node.configuration_schema
        if not schema:
            return {"valid": True, "errors": []}
        
        errors = []
        
        # Check required fields
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in parameters:
                errors.append(f"Required field '{field}' is missing")
        
        # Check field types (simplified)
        properties = schema.get("properties", {})
        for field, value in parameters.items():
            if field in properties:
                field_schema = properties[field]
                expected_type = field_schema.get("type")
                
                # Simple type checking
                if expected_type == "string" and not isinstance(value, str):
                    errors.append(f"Field '{field}' must be a string")
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"Field '{field}' must be a number")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Field '{field}' must be a boolean")
                elif expected_type == "array" and not isinstance(value, list):
                    errors.append(f"Field '{field}' must be an array")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
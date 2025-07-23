"""
Live Graphics Service for real-time graphics overlay in live production
"""

import os
import json
import asyncio
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
import aiofiles
from pathlib import Path
import uuid
import tempfile
import xml.etree.ElementTree as ET

from ..core.logging import get_logger
from ..core.exceptions import ProxyGenerationError

logger = get_logger(__name__)


class GraphicsType(Enum):
    """Types of graphics elements"""
    LOWER_THIRD = "lower_third"
    FULL_SCREEN = "full_screen"
    TICKER = "ticker"
    BUG = "bug"  # Corner logo/watermark
    SCORE_BOARD = "score_board"
    COUNTDOWN = "countdown"
    CRAWL = "crawl"  # Scrolling text
    SIDEBAR = "sidebar"
    POPUP = "popup"
    TRANSITION = "transition"


class AnimationType(Enum):
    """Animation types for graphics"""
    NONE = "none"
    FADE = "fade"
    SLIDE = "slide"
    SCALE = "scale"
    ROTATE = "rotate"
    WIPE = "wipe"
    BOUNCE = "bounce"
    ELASTIC = "elastic"
    CUSTOM = "custom"


class DataSourceType(Enum):
    """Types of data sources for dynamic graphics"""
    STATIC = "static"
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    DATABASE = "database"
    API = "api"
    WEBSOCKET = "websocket"
    RSS = "rss"
    SOCIAL = "social"


class TemplateEngine(Enum):
    """Template engines for graphics rendering"""
    HTML_CSS = "html_css"
    CASPAR_CG = "caspar_cg"
    VIZRT = "vizrt"
    UNREAL = "unreal"
    AFTER_EFFECTS = "after_effects"
    CUSTOM = "custom"


class PlayoutMode(Enum):
    """Playout modes for graphics"""
    MANUAL = "manual"  # Manual control
    SCHEDULED = "scheduled"  # Time-based
    TRIGGERED = "triggered"  # Event-based
    AUTOMATED = "automated"  # Fully automated
    PLAYLIST = "playlist"  # Playlist-based


class GraphicsLayer(Enum):
    """Graphics layering system"""
    BACKGROUND = 0
    LOWER = 1
    MIDDLE = 2
    UPPER = 3
    OVERLAY = 4
    FOREGROUND = 5


class LiveGraphicsService:
    """Service for live graphics overlay and management"""
    
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"
        self.ffprobe_path = "ffprobe"
        
        # Active graphics sessions
        self.graphics_sessions = {}
        
        # Graphics templates
        self.templates = {}
        
        # Active graphics elements
        self.active_graphics = {}
        
        # Data connections
        self.data_connections = {}
        
        # Playout schedules
        self.playout_schedules = {}
        
        # Animation presets
        self.animation_presets = self._load_animation_presets()
        
        # Render engines
        self.render_engines = {}
    
    async def create_graphics_session(
        self,
        session_id: str,
        session_name: str,
        configuration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new live graphics session
        
        Args:
            session_id: Unique session identifier
            session_name: Human-readable session name
            configuration: Graphics configuration
        
        Returns:
            Session information
        """
        try:
            # Create graphics session
            session = {
                "id": session_id,
                "name": session_name,
                "created_at": datetime.utcnow(),
                "status": "initializing",
                "configuration": configuration,
                "templates": {},
                "graphics": {},
                "layers": {
                    layer.name: {
                        "index": layer.value,
                        "elements": [],
                        "opacity": 1.0,
                        "visible": True
                    }
                    for layer in GraphicsLayer
                },
                "data_sources": {},
                "playout": {
                    "mode": PlayoutMode.MANUAL.value,
                    "schedule": [],
                    "playlist": [],
                    "current_index": 0
                },
                "render": {
                    "engine": TemplateEngine.HTML_CSS.value,
                    "resolution": configuration.get("resolution", "1920x1080"),
                    "framerate": configuration.get("framerate", 30),
                    "format": configuration.get("format", "rgba"),
                    "safe_areas": configuration.get("safe_areas", {
                        "title": {"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.8},
                        "action": {"x": 0.05, "y": 0.05, "width": 0.9, "height": 0.9}
                    })
                },
                "metrics": {
                    "graphics_rendered": 0,
                    "animations_played": 0,
                    "data_updates": 0,
                    "average_render_time_ms": 0
                }
            }
            
            # Initialize template engine
            engine = configuration.get("engine", TemplateEngine.HTML_CSS.value)
            session["render"]["engine"] = engine
            
            # Store session
            self.graphics_sessions[session_id] = session
            
            # Start render engine
            session["render_task"] = asyncio.create_task(
                self._run_render_engine(session_id)
            )
            
            logger.info(
                "graphics_session_created",
                session_id=session_id,
                name=session_name
            )
            
            return {
                "session_id": session_id,
                "name": session_name,
                "status": "ready",
                "output_url": f"/graphics/{session_id}/output",
                "preview_url": f"/graphics/{session_id}/preview",
                "control_url": f"/graphics/{session_id}/control",
                "created_at": session["created_at"].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create graphics session: {str(e)}")
            raise ProxyGenerationError(f"Graphics session creation failed: {str(e)}")
    
    async def load_template(
        self,
        session_id: str,
        template_id: str,
        template_type: GraphicsType,
        template_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Load a graphics template
        
        Args:
            session_id: Session ID
            template_id: Unique template identifier
            template_type: Type of graphics template
            template_data: Template configuration and assets
        
        Returns:
            Template information
        """
        if session_id not in self.graphics_sessions:
            raise ProxyGenerationError(f"Session {session_id} not found")
        
        session = self.graphics_sessions[session_id]
        
        # Create template entry
        template = {
            "id": template_id,
            "type": template_type.value,
            "data": template_data,
            "loaded_at": datetime.utcnow(),
            "fields": template_data.get("fields", {}),
            "animations": template_data.get("animations", {}),
            "styles": template_data.get("styles", {}),
            "assets": template_data.get("assets", {}),
            "instances": []
        }
        
        # Validate template based on type
        if template_type == GraphicsType.LOWER_THIRD:
            template["fields"]["title"] = template_data.get("title_field", {})
            template["fields"]["subtitle"] = template_data.get("subtitle_field", {})
        elif template_type == GraphicsType.TICKER:
            template["fields"]["items"] = template_data.get("ticker_items", [])
            template["fields"]["speed"] = template_data.get("scroll_speed", 50)
        elif template_type == GraphicsType.COUNTDOWN:
            template["fields"]["target_time"] = template_data.get("target_time")
            template["fields"]["format"] = template_data.get("time_format", "HH:MM:SS")
        
        # Store template
        session["templates"][template_id] = template
        self.templates[template_id] = template
        
        logger.info(
            "template_loaded",
            session_id=session_id,
            template_id=template_id,
            template_type=template_type.value
        )
        
        return {
            "template_id": template_id,
            "type": template_type.value,
            "status": "loaded",
            "fields": list(template["fields"].keys())
        }
    
    async def create_graphic(
        self,
        session_id: str,
        graphic_id: str,
        template_id: str,
        layer: GraphicsLayer,
        data: Dict[str, Any],
        position: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Create a graphics instance from template
        
        Args:
            session_id: Session ID
            graphic_id: Unique graphic identifier
            template_id: Template to use
            layer: Layer to place graphic on
            data: Data to populate template
            position: Position on screen (x, y, width, height)
        
        Returns:
            Graphic information
        """
        if session_id not in self.graphics_sessions:
            raise ProxyGenerationError(f"Session {session_id} not found")
        
        session = self.graphics_sessions[session_id]
        
        if template_id not in session["templates"]:
            raise ProxyGenerationError(f"Template {template_id} not found")
        
        template = session["templates"][template_id]
        
        # Create graphic instance
        graphic = {
            "id": graphic_id,
            "template_id": template_id,
            "type": template["type"],
            "layer": layer.value,
            "created_at": datetime.utcnow(),
            "visible": False,
            "data": data,
            "position": position or self._get_default_position(template["type"]),
            "animation": {
                "in": AnimationType.FADE.value,
                "out": AnimationType.FADE.value,
                "duration_in": 500,
                "duration_out": 500
            },
            "state": "created",
            "render_cache": None
        }
        
        # Add to session
        session["graphics"][graphic_id] = graphic
        session["layers"][layer.name]["elements"].append(graphic_id)
        
        # Add to template instances
        template["instances"].append(graphic_id)
        
        # Store globally
        self.active_graphics[graphic_id] = graphic
        
        logger.info(
            "graphic_created",
            session_id=session_id,
            graphic_id=graphic_id,
            template_id=template_id,
            layer=layer.name
        )
        
        return {
            "graphic_id": graphic_id,
            "template_id": template_id,
            "layer": layer.name,
            "position": graphic["position"],
            "state": graphic["state"]
        }
    
    async def show_graphic(
        self,
        session_id: str,
        graphic_id: str,
        animation: Optional[AnimationType] = None,
        duration_ms: int = 500
    ) -> Dict[str, Any]:
        """
        Show a graphic with animation
        
        Args:
            session_id: Session ID
            graphic_id: Graphic to show
            animation: Animation type (uses default if None)
            duration_ms: Animation duration
        
        Returns:
            Show result
        """
        if session_id not in self.graphics_sessions:
            raise ProxyGenerationError(f"Session {session_id} not found")
        
        session = self.graphics_sessions[session_id]
        
        if graphic_id not in session["graphics"]:
            raise ProxyGenerationError(f"Graphic {graphic_id} not found")
        
        graphic = session["graphics"][graphic_id]
        
        # Update animation if specified
        if animation:
            graphic["animation"]["in"] = animation.value
            graphic["animation"]["duration_in"] = duration_ms
        
        # Animate in
        graphic["visible"] = True
        graphic["state"] = "animating_in"
        
        # Start animation
        asyncio.create_task(
            self._animate_graphic(
                graphic_id,
                "in",
                graphic["animation"]["in"],
                graphic["animation"]["duration_in"]
            )
        )
        
        # Update metrics
        session["metrics"]["animations_played"] += 1
        
        logger.info(
            "graphic_shown",
            session_id=session_id,
            graphic_id=graphic_id,
            animation=graphic["animation"]["in"]
        )
        
        return {
            "graphic_id": graphic_id,
            "visible": True,
            "animation": graphic["animation"]["in"],
            "duration_ms": graphic["animation"]["duration_in"]
        }
    
    async def hide_graphic(
        self,
        session_id: str,
        graphic_id: str,
        animation: Optional[AnimationType] = None,
        duration_ms: int = 500
    ) -> Dict[str, Any]:
        """
        Hide a graphic with animation
        
        Args:
            session_id: Session ID
            graphic_id: Graphic to hide
            animation: Animation type (uses default if None)
            duration_ms: Animation duration
        
        Returns:
            Hide result
        """
        if session_id not in self.graphics_sessions:
            raise ProxyGenerationError(f"Session {session_id} not found")
        
        session = self.graphics_sessions[session_id]
        
        if graphic_id not in session["graphics"]:
            raise ProxyGenerationError(f"Graphic {graphic_id} not found")
        
        graphic = session["graphics"][graphic_id]
        
        # Update animation if specified
        if animation:
            graphic["animation"]["out"] = animation.value
            graphic["animation"]["duration_out"] = duration_ms
        
        # Animate out
        graphic["state"] = "animating_out"
        
        # Start animation
        asyncio.create_task(
            self._animate_graphic(
                graphic_id,
                "out",
                graphic["animation"]["out"],
                graphic["animation"]["duration_out"]
            )
        )
        
        # Update metrics
        session["metrics"]["animations_played"] += 1
        
        logger.info(
            "graphic_hidden",
            session_id=session_id,
            graphic_id=graphic_id,
            animation=graphic["animation"]["out"]
        )
        
        return {
            "graphic_id": graphic_id,
            "visible": False,
            "animation": graphic["animation"]["out"],
            "duration_ms": graphic["animation"]["duration_out"]
        }
    
    async def update_graphic_data(
        self,
        session_id: str,
        graphic_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update graphic data dynamically
        
        Args:
            session_id: Session ID
            graphic_id: Graphic to update
            data: New data values
        
        Returns:
            Update result
        """
        if session_id not in self.graphics_sessions:
            raise ProxyGenerationError(f"Session {session_id} not found")
        
        session = self.graphics_sessions[session_id]
        
        if graphic_id not in session["graphics"]:
            raise ProxyGenerationError(f"Graphic {graphic_id} not found")
        
        graphic = session["graphics"][graphic_id]
        
        # Update data
        graphic["data"].update(data)
        graphic["render_cache"] = None  # Invalidate cache
        
        # Update metrics
        session["metrics"]["data_updates"] += 1
        
        logger.info(
            "graphic_data_updated",
            session_id=session_id,
            graphic_id=graphic_id,
            fields=list(data.keys())
        )
        
        return {
            "graphic_id": graphic_id,
            "updated_fields": list(data.keys()),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def connect_data_source(
        self,
        session_id: str,
        source_id: str,
        source_type: DataSourceType,
        connection_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Connect a data source for dynamic graphics
        
        Args:
            session_id: Session ID
            source_id: Unique source identifier
            source_type: Type of data source
            connection_params: Connection parameters
        
        Returns:
            Connection information
        """
        if session_id not in self.graphics_sessions:
            raise ProxyGenerationError(f"Session {session_id} not found")
        
        session = self.graphics_sessions[session_id]
        
        # Create data source
        data_source = {
            "id": source_id,
            "type": source_type.value,
            "params": connection_params,
            "connected_at": datetime.utcnow(),
            "status": "connecting",
            "bindings": [],  # Graphics bound to this source
            "update_interval": connection_params.get("update_interval", 1000),
            "last_update": None,
            "connection": None
        }
        
        # Connect based on type
        if source_type == DataSourceType.JSON:
            data_source["connection"] = await self._connect_json_source(connection_params)
        elif source_type == DataSourceType.API:
            data_source["connection"] = await self._connect_api_source(connection_params)
        elif source_type == DataSourceType.WEBSOCKET:
            data_source["connection"] = await self._connect_websocket_source(connection_params)
        elif source_type == DataSourceType.RSS:
            data_source["connection"] = await self._connect_rss_source(connection_params)
        
        # Start update loop
        if data_source["connection"]:
            data_source["update_task"] = asyncio.create_task(
                self._update_data_source(session_id, source_id)
            )
            data_source["status"] = "connected"
        
        # Store data source
        session["data_sources"][source_id] = data_source
        self.data_connections[source_id] = data_source
        
        logger.info(
            "data_source_connected",
            session_id=session_id,
            source_id=source_id,
            source_type=source_type.value
        )
        
        return {
            "source_id": source_id,
            "type": source_type.value,
            "status": data_source["status"],
            "update_interval": data_source["update_interval"]
        }
    
    async def create_playlist(
        self,
        session_id: str,
        playlist_id: str,
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a graphics playlist
        
        Args:
            session_id: Session ID
            playlist_id: Unique playlist identifier
            items: List of playlist items
        
        Returns:
            Playlist information
        """
        if session_id not in self.graphics_sessions:
            raise ProxyGenerationError(f"Session {session_id} not found")
        
        session = self.graphics_sessions[session_id]
        
        # Create playlist
        playlist = {
            "id": playlist_id,
            "items": items,
            "created_at": datetime.utcnow(),
            "current_index": 0,
            "loop": True,
            "auto_advance": True,
            "item_duration": 5000  # Default 5 seconds per item
        }
        
        # Validate items
        for item in items:
            if "graphic_id" not in item and "template_id" not in item:
                raise ProxyGenerationError("Playlist items must have graphic_id or template_id")
        
        # Set as active playlist
        session["playout"]["playlist"] = items
        session["playout"]["mode"] = PlayoutMode.PLAYLIST.value
        
        # Store playlist
        self.playout_schedules[playlist_id] = playlist
        
        logger.info(
            "playlist_created",
            session_id=session_id,
            playlist_id=playlist_id,
            item_count=len(items)
        )
        
        return {
            "playlist_id": playlist_id,
            "item_count": len(items),
            "mode": PlayoutMode.PLAYLIST.value
        }
    
    async def schedule_graphic(
        self,
        session_id: str,
        graphic_id: str,
        show_time: datetime,
        duration_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Schedule a graphic to show at specific time
        
        Args:
            session_id: Session ID
            graphic_id: Graphic to schedule
            show_time: When to show the graphic
            duration_seconds: How long to show (None = manual hide)
        
        Returns:
            Schedule information
        """
        if session_id not in self.graphics_sessions:
            raise ProxyGenerationError(f"Session {session_id} not found")
        
        session = self.graphics_sessions[session_id]
        
        if graphic_id not in session["graphics"]:
            raise ProxyGenerationError(f"Graphic {graphic_id} not found")
        
        # Create schedule entry
        schedule_entry = {
            "id": str(uuid.uuid4()),
            "graphic_id": graphic_id,
            "show_time": show_time,
            "duration_seconds": duration_seconds,
            "hide_time": show_time + timedelta(seconds=duration_seconds) if duration_seconds else None,
            "status": "scheduled"
        }
        
        # Add to schedule
        session["playout"]["schedule"].append(schedule_entry)
        session["playout"]["schedule"].sort(key=lambda x: x["show_time"])
        
        logger.info(
            "graphic_scheduled",
            session_id=session_id,
            graphic_id=graphic_id,
            show_time=show_time.isoformat()
        )
        
        return {
            "schedule_id": schedule_entry["id"],
            "graphic_id": graphic_id,
            "show_time": show_time.isoformat(),
            "duration_seconds": duration_seconds
        }
    
    async def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get real-time metrics for a graphics session"""
        if session_id not in self.graphics_sessions:
            raise ProxyGenerationError(f"Session {session_id} not found")
        
        session = self.graphics_sessions[session_id]
        
        # Count active graphics
        active_graphics = sum(
            1 for g in session["graphics"].values() 
            if g["visible"]
        )
        
        # Count by type
        graphics_by_type = {}
        for graphic in session["graphics"].values():
            gtype = graphic["type"]
            graphics_by_type[gtype] = graphics_by_type.get(gtype, 0) + 1
        
        return {
            "session_id": session_id,
            "status": session["status"],
            "uptime_seconds": (datetime.utcnow() - session["created_at"]).total_seconds(),
            "graphics": {
                "total": len(session["graphics"]),
                "active": active_graphics,
                "by_type": graphics_by_type
            },
            "templates": {
                "loaded": len(session["templates"])
            },
            "data_sources": {
                "connected": sum(1 for d in session["data_sources"].values() if d["status"] == "connected")
            },
            "performance": {
                "graphics_rendered": session["metrics"]["graphics_rendered"],
                "animations_played": session["metrics"]["animations_played"],
                "data_updates": session["metrics"]["data_updates"],
                "average_render_time_ms": session["metrics"]["average_render_time_ms"]
            },
            "playout": {
                "mode": session["playout"]["mode"],
                "schedule_count": len(session["playout"]["schedule"]),
                "playlist_count": len(session["playout"]["playlist"])
            }
        }
    
    def _load_animation_presets(self) -> Dict[str, Any]:
        """Load animation presets"""
        return {
            "fade": {
                "in": {"opacity": [0, 1]},
                "out": {"opacity": [1, 0]}
            },
            "slide": {
                "in": {"x": [-100, 0]},
                "out": {"x": [0, 100]}
            },
            "scale": {
                "in": {"scale": [0, 1]},
                "out": {"scale": [1, 0]}
            },
            "bounce": {
                "in": {"scale": [0, 1.2, 1]},
                "out": {"scale": [1, 1.2, 0]}
            }
        }
    
    def _get_default_position(self, graphic_type: str) -> Dict[str, float]:
        """Get default position for graphic type"""
        positions = {
            "lower_third": {"x": 0.1, "y": 0.7, "width": 0.8, "height": 0.15},
            "full_screen": {"x": 0, "y": 0, "width": 1, "height": 1},
            "ticker": {"x": 0, "y": 0.9, "width": 1, "height": 0.1},
            "bug": {"x": 0.85, "y": 0.05, "width": 0.1, "height": 0.1},
            "score_board": {"x": 0.7, "y": 0.05, "width": 0.25, "height": 0.2},
            "sidebar": {"x": 0, "y": 0, "width": 0.2, "height": 1},
            "popup": {"x": 0.3, "y": 0.3, "width": 0.4, "height": 0.4}
        }
        return positions.get(graphic_type, {"x": 0, "y": 0, "width": 1, "height": 1})
    
    async def _run_render_engine(self, session_id: str):
        """Main rendering loop for graphics"""
        session = self.graphics_sessions[session_id]
        session["status"] = "running"
        
        while session["status"] == "running":
            try:
                # Check scheduled graphics
                await self._process_schedule(session_id)
                
                # Update data sources
                await self._update_data_bindings(session_id)
                
                # Process playlist
                if session["playout"]["mode"] == PlayoutMode.PLAYLIST.value:
                    await self._process_playlist(session_id)
                
                await asyncio.sleep(0.033)  # ~30fps
                
            except Exception as e:
                logger.error(f"Render engine error: {str(e)}")
    
    async def _animate_graphic(
        self,
        graphic_id: str,
        direction: str,
        animation_type: str,
        duration_ms: int
    ):
        """Animate a graphic in or out"""
        graphic = self.active_graphics.get(graphic_id)
        if not graphic:
            return
        
        # Get animation preset
        preset = self.animation_presets.get(animation_type, {}).get(direction, {})
        
        # Apply animation (simplified)
        if direction == "in":
            graphic["state"] = "visible"
        else:
            graphic["visible"] = False
            graphic["state"] = "hidden"
    
    async def _connect_json_source(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to JSON data source"""
        return {
            "type": "json",
            "url": params.get("url"),
            "method": params.get("method", "GET"),
            "headers": params.get("headers", {})
        }
    
    async def _connect_api_source(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to API data source"""
        return {
            "type": "api",
            "endpoint": params.get("endpoint"),
            "auth": params.get("auth"),
            "query": params.get("query", {})
        }
    
    async def _connect_websocket_source(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to WebSocket data source"""
        return {
            "type": "websocket",
            "url": params.get("url"),
            "protocol": params.get("protocol")
        }
    
    async def _connect_rss_source(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to RSS feed"""
        return {
            "type": "rss",
            "feed_url": params.get("feed_url"),
            "max_items": params.get("max_items", 10)
        }
    
    async def _update_data_source(self, session_id: str, source_id: str):
        """Update data from source"""
        # This would implement actual data fetching
        pass
    
    async def _process_schedule(self, session_id: str):
        """Process scheduled graphics"""
        session = self.graphics_sessions[session_id]
        current_time = datetime.utcnow()
        
        for entry in session["playout"]["schedule"]:
            if entry["status"] == "scheduled" and entry["show_time"] <= current_time:
                # Show the graphic
                await self.show_graphic(session_id, entry["graphic_id"])
                entry["status"] = "shown"
                
                # Schedule hide if duration specified
                if entry["hide_time"] and entry["hide_time"] <= current_time:
                    await self.hide_graphic(session_id, entry["graphic_id"])
                    entry["status"] = "completed"
    
    async def _update_data_bindings(self, session_id: str):
        """Update graphics bound to data sources"""
        # This would update graphics with latest data
        pass
    
    async def _process_playlist(self, session_id: str):
        """Process playlist items"""
        # This would handle playlist advancement
        pass
    
    def get_live_graphics_capabilities(self) -> Dict[str, Any]:
        """Get live graphics capabilities"""
        return {
            "graphics_types": [t.value for t in GraphicsType],
            "animation_types": [a.value for a in AnimationType],
            "data_sources": [d.value for d in DataSourceType],
            "template_engines": [e.value for e in TemplateEngine],
            "playout_modes": [p.value for p in PlayoutMode],
            "layers": [l.name for l in GraphicsLayer],
            "features": {
                "dynamic_data": True,
                "live_updates": True,
                "scheduled_playout": True,
                "playlist_support": True,
                "data_binding": True,
                "safe_areas": True,
                "multi_layer": True,
                "animation_presets": True,
                "custom_templates": True,
                "realtime_preview": True
            },
            "supported_formats": {
                "templates": ["html", "css", "json", "xml"],
                "data": ["json", "xml", "csv", "rss"],
                "output": ["rgba", "yuva", "key_fill"],
                "resolutions": ["720p", "1080p", "4K"]
            },
            "performance": {
                "max_layers": 6,
                "max_graphics_per_layer": 100,
                "max_animations_concurrent": 20,
                "render_framerate": 60
            }
        }
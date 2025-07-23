"""
EDL (Edit Decision List) Exporter for traditional edit systems
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
import math

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.schemas import TimelineExportRequest, ExportResult
from ..core.config import settings
from ..core.exceptions import ExportError
from ..core.logger import get_logger

logger = get_logger(__name__)


class EDLEvent(BaseModel):
    """EDL Event representation"""
    event_number: int
    reel_name: str
    track_type: str  # 'V' for video, 'A', 'A2', etc. for audio
    edit_type: str  # 'C' for cut, 'D' for dissolve, 'W' for wipe
    source_in: str  # Timecode format HH:MM:SS:FF
    source_out: str  # Timecode format HH:MM:SS:FF
    record_in: str  # Timecode format HH:MM:SS:FF
    record_out: str  # Timecode format HH:MM:SS:FF
    source_file: str = ""
    speed: float = 1.0
    comments: List[str] = Field(default_factory=list)


class EDLExporter:
    """EDL Exporter for traditional edit systems"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.export_format = "edl"
        self.frame_rate = 25.0  # Default PAL
        
    async def export_timeline(self, request: TimelineExportRequest) -> ExportResult:
        """Export timeline to EDL format"""
        try:
            logger.info(f"Starting EDL export for timeline {request.timeline_id}")
            
            # Get timeline data
            timeline_data = await self._get_timeline_data(request.timeline_id)
            
            # Set frame rate from timeline
            self.frame_rate = timeline_data.get("frame_rate", 25.0)
            
            # Create EDL events
            events = await self._create_edl_events(timeline_data, request)
            
            # Generate EDL content
            edl_content = await self._generate_edl_content(events, timeline_data)
            
            # Write EDL file
            export_path = await self._write_edl_file(edl_content, request)
            
            result = ExportResult(
                export_id=str(uuid.uuid4()),
                timeline_id=request.timeline_id,
                format=self.export_format,
                file_path=str(export_path),
                status="completed",
                created_at=datetime.utcnow(),
                metadata={
                    "timeline_name": timeline_data["name"],
                    "frame_rate": self.frame_rate,
                    "total_events": len(events),
                    "duration": timeline_data["duration"]
                }
            )
            
            logger.info(f"EDL export completed successfully: {export_path}")
            return result
            
        except Exception as e:
            logger.error(f"EDL export failed: {str(e)}")
            raise ExportError(f"EDL export failed: {str(e)}")
    
    async def _get_timeline_data(self, timeline_id: str) -> Dict[str, Any]:
        """Get timeline data from database"""
        # This would query the timeline service
        # For now, return mock data structure
        return {
            "id": timeline_id,
            "name": "Timeline_001",
            "duration": 7200,  # 5 minutes at 25fps
            "frame_rate": 25.0,
            "start_timecode": "01:00:00:00",
            "tracks": [
                {
                    "id": "track_v1",
                    "name": "V1",
                    "type": "video",
                    "clips": [
                        {
                            "id": "clip_001",
                            "name": "Shot_001",
                            "reel_name": "001",
                            "asset_id": "asset_001",
                            "start_time": 0,
                            "duration": 1500,
                            "source_in": 0,
                            "source_out": 1500,
                            "file_path": "/storage/media/Shot_001.mov",
                            "speed": 1.0
                        },
                        {
                            "id": "clip_002",
                            "name": "Shot_002",
                            "reel_name": "002",
                            "asset_id": "asset_002",
                            "start_time": 1500,
                            "duration": 1200,
                            "source_in": 500,
                            "source_out": 1700,
                            "file_path": "/storage/media/Shot_002.mov",
                            "speed": 1.0
                        }
                    ]
                },
                {
                    "id": "track_a1",
                    "name": "A1",
                    "type": "audio",
                    "clips": [
                        {
                            "id": "clip_audio_001",
                            "name": "Audio_001",
                            "reel_name": "A001",
                            "asset_id": "asset_audio_001",
                            "start_time": 0,
                            "duration": 2700,
                            "source_in": 0,
                            "source_out": 2700,
                            "file_path": "/storage/media/Audio_001.wav",
                            "speed": 1.0
                        }
                    ]
                }
            ]
        }
    
    async def _create_edl_events(self, timeline_data: Dict[str, Any], request: TimelineExportRequest) -> List[EDLEvent]:
        """Create EDL events from timeline data"""
        events = []
        event_number = 1
        
        # Process each track
        for track_data in timeline_data["tracks"]:
            track_type = self._get_track_type(track_data["type"], track_data["name"])
            
            # Process clips in the track
            for clip_data in track_data["clips"]:
                event = EDLEvent(
                    event_number=event_number,
                    reel_name=clip_data.get("reel_name", "001"),
                    track_type=track_type,
                    edit_type="C",  # Cut
                    source_in=self._frames_to_timecode(clip_data["source_in"]),
                    source_out=self._frames_to_timecode(clip_data["source_out"]),
                    record_in=self._frames_to_timecode(clip_data["start_time"]),
                    record_out=self._frames_to_timecode(clip_data["start_time"] + clip_data["duration"]),
                    source_file=clip_data["file_path"],
                    speed=clip_data.get("speed", 1.0)
                )
                
                # Add comments for additional information
                if clip_data.get("name"):
                    event.comments.append(f"* FROM CLIP NAME: {clip_data['name']}")
                
                if clip_data.get("file_path"):
                    event.comments.append(f"* SOURCE FILE: {Path(clip_data['file_path']).name}")
                
                if clip_data.get("speed", 1.0) != 1.0:
                    event.comments.append(f"* SPEED: {clip_data['speed']}")
                
                events.append(event)
                event_number += 1
        
        return events
    
    def _get_track_type(self, track_type: str, track_name: str) -> str:
        """Get EDL track type designation"""
        if track_type == "video":
            return "V"
        elif track_type == "audio":
            # Try to extract audio track number from name
            if "1" in track_name or track_name.upper() == "A1":
                return "A"
            elif "2" in track_name or track_name.upper() == "A2":
                return "A2"
            elif "3" in track_name or track_name.upper() == "A3":
                return "A3"
            elif "4" in track_name or track_name.upper() == "A4":
                return "A4"
            else:
                return "A"
        else:
            return "V"
    
    def _frames_to_timecode(self, frames: int) -> str:
        """Convert frames to timecode format HH:MM:SS:FF"""
        total_seconds = frames / self.frame_rate
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        frame_remainder = int(frames % self.frame_rate)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frame_remainder:02d}"
    
    def _timecode_to_frames(self, timecode: str) -> int:
        """Convert timecode format HH:MM:SS:FF to frames"""
        parts = timecode.split(':')
        if len(parts) != 4:
            raise ValueError(f"Invalid timecode format: {timecode}")
        
        hours, minutes, seconds, frames = map(int, parts)
        total_frames = (hours * 3600 + minutes * 60 + seconds) * self.frame_rate + frames
        return int(total_frames)
    
    async def _generate_edl_content(self, events: List[EDLEvent], timeline_data: Dict[str, Any]) -> str:
        """Generate EDL content string"""
        lines = []
        
        # EDL Header
        lines.append("TITLE: " + timeline_data["name"])
        lines.append("FCM: NON-DROP FRAME")
        lines.append("")
        
        # Events
        for event in events:
            # Main event line
            event_line = f"{event.event_number:03d}  {event.reel_name:<8} {event.track_type:<2} {event.edit_type} "
            event_line += f"{event.source_in} {event.source_out} {event.record_in} {event.record_out}"
            lines.append(event_line)
            
            # Add comments
            for comment in event.comments:
                lines.append(comment)
            
            # Add blank line between events
            lines.append("")
        
        return "\n".join(lines)
    
    async def _write_edl_file(self, edl_content: str, request: TimelineExportRequest) -> Path:
        """Write EDL content to file"""
        export_dir = Path(settings.EXPORT_DIR) / "edl"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{request.timeline_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.edl"
        file_path = export_dir / filename
        
        async with asyncio.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(edl_content)
        
        return file_path
    
    async def validate_export(self, export_path: Path) -> bool:
        """Validate EDL export file"""
        try:
            if not export_path.exists():
                return False
            
            with open(export_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required EDL elements
            if "TITLE:" not in content:
                logger.error("Invalid EDL format: missing TITLE line")
                return False
            
            if "FCM:" not in content:
                logger.error("Invalid EDL format: missing FCM line")
                return False
            
            # Check for at least one event
            lines = content.split('\n')
            event_found = False
            for line in lines:
                if line.strip() and not line.startswith(('TITLE:', 'FCM:', '*')):
                    # Check if line looks like an event (starts with numbers)
                    if line.split()[0].isdigit():
                        event_found = True
                        break
            
            if not event_found:
                logger.error("Invalid EDL format: no events found")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"EDL validation failed: {str(e)}")
            return False
    
    async def export_cmx_edl(self, request: TimelineExportRequest) -> ExportResult:
        """Export timeline to CMX EDL format (alternative format)"""
        try:
            logger.info(f"Starting CMX EDL export for timeline {request.timeline_id}")
            
            # Get timeline data
            timeline_data = await self._get_timeline_data(request.timeline_id)
            
            # Create CMX EDL content
            cmx_content = await self._generate_cmx_edl_content(timeline_data)
            
            # Write CMX EDL file
            export_path = await self._write_cmx_edl_file(cmx_content, request)
            
            result = ExportResult(
                export_id=str(uuid.uuid4()),
                timeline_id=request.timeline_id,
                format="cmx_edl",
                file_path=str(export_path),
                status="completed",
                created_at=datetime.utcnow(),
                metadata={
                    "timeline_name": timeline_data["name"],
                    "frame_rate": self.frame_rate,
                    "format": "CMX EDL"
                }
            )
            
            logger.info(f"CMX EDL export completed successfully: {export_path}")
            return result
            
        except Exception as e:
            logger.error(f"CMX EDL export failed: {str(e)}")
            raise ExportError(f"CMX EDL export failed: {str(e)}")
    
    async def _generate_cmx_edl_content(self, timeline_data: Dict[str, Any]) -> str:
        """Generate CMX EDL format content"""
        lines = []
        
        # CMX EDL Header
        lines.append("TITLE: " + timeline_data["name"])
        lines.append("FCM: NON-DROP FRAME")
        lines.append("")
        
        event_number = 1
        
        # Process tracks
        for track_data in timeline_data["tracks"]:
            if track_data["type"] == "video":  # CMX EDL typically focuses on video
                for clip_data in track_data["clips"]:
                    # CMX format: Event# Reel Edit Source_In Source_Out Record_In Record_Out
                    reel_name = clip_data.get("reel_name", "001")
                    
                    line = f"{event_number:03d}  {reel_name:<8} V     C        "
                    line += f"{self._frames_to_timecode(clip_data['source_in'])} "
                    line += f"{self._frames_to_timecode(clip_data['source_out'])} "
                    line += f"{self._frames_to_timecode(clip_data['start_time'])} "
                    line += f"{self._frames_to_timecode(clip_data['start_time'] + clip_data['duration'])}"
                    
                    lines.append(line)
                    
                    # Add clip name as comment
                    if clip_data.get("name"):
                        lines.append(f"* FROM CLIP NAME: {clip_data['name']}")
                    
                    lines.append("")
                    event_number += 1
        
        return "\n".join(lines)
    
    async def _write_cmx_edl_file(self, cmx_content: str, request: TimelineExportRequest) -> Path:
        """Write CMX EDL content to file"""
        export_dir = Path(settings.EXPORT_DIR) / "edl"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{request.timeline_id}_cmx_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.edl"
        file_path = export_dir / filename
        
        async with asyncio.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(cmx_content)
        
        return file_path
"""
OpenTimelineIO (OTIO) Exporter for DaVinci Resolve and other OTIO-compatible NLEs
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

try:
    import opentimelineio as otio
    OTIO_AVAILABLE = True
except ImportError:
    OTIO_AVAILABLE = False

from ..models.schemas import TimelineExportRequest, ExportResult
from ..core.config import settings
from ..core.exceptions import ExportError
from ..core.logger import get_logger

logger = get_logger(__name__)


class OTIOExporter:
    """OpenTimelineIO Exporter for DaVinci Resolve and other OTIO-compatible NLEs"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.export_format = "otio"
        self.frame_rate = 25.0  # Default PAL
        
        if not OTIO_AVAILABLE:
            raise ExportError("OpenTimelineIO library is not installed. Install with: pip install OpenTimelineIO")
    
    async def export_timeline(self, request: TimelineExportRequest) -> ExportResult:
        """Export timeline to OTIO format"""
        try:
            logger.info(f"Starting OTIO export for timeline {request.timeline_id}")
            
            # Get timeline data
            timeline_data = await self._get_timeline_data(request.timeline_id)
            
            # Set frame rate from timeline
            self.frame_rate = timeline_data.get("frame_rate", 25.0)
            
            # Create OTIO timeline
            otio_timeline = await self._create_otio_timeline(timeline_data, request)
            
            # Write OTIO file
            export_path = await self._write_otio_file(otio_timeline, request)
            
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
                    "duration": timeline_data["duration"],
                    "video_tracks": len([t for t in timeline_data["tracks"] if t["type"] == "video"]),
                    "audio_tracks": len([t for t in timeline_data["tracks"] if t["type"] == "audio"]),
                    "total_clips": sum(len(t["clips"]) for t in timeline_data["tracks"])
                }
            )
            
            logger.info(f"OTIO export completed successfully: {export_path}")
            return result
            
        except Exception as e:
            logger.error(f"OTIO export failed: {str(e)}")
            raise ExportError(f"OTIO export failed: {str(e)}")
    
    async def _get_timeline_data(self, timeline_id: str) -> Dict[str, Any]:
        """Get timeline data from database"""
        # This would query the timeline service
        # For now, return mock data structure
        return {
            "id": timeline_id,
            "name": "Timeline_001",
            "duration": 7200,  # 5 minutes at 25fps
            "frame_rate": 25.0,
            "resolution": "1920x1080",
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
                            "asset_id": "asset_001",
                            "start_time": 0,
                            "duration": 1500,
                            "source_in": 0,
                            "source_out": 1500,
                            "file_path": "/storage/media/Shot_001.mov",
                            "speed": 1.0,
                            "effects": [],
                            "transitions": []
                        },
                        {
                            "id": "clip_002",
                            "name": "Shot_002",
                            "asset_id": "asset_002",
                            "start_time": 1500,
                            "duration": 1200,
                            "source_in": 500,
                            "source_out": 1700,
                            "file_path": "/storage/media/Shot_002.mov",
                            "speed": 1.0,
                            "effects": [],
                            "transitions": []
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
                            "asset_id": "asset_audio_001",
                            "start_time": 0,
                            "duration": 2700,
                            "source_in": 0,
                            "source_out": 2700,
                            "file_path": "/storage/media/Audio_001.wav",
                            "speed": 1.0,
                            "effects": [],
                            "transitions": []
                        }
                    ]
                }
            ]
        }
    
    async def _create_otio_timeline(self, timeline_data: Dict[str, Any], request: TimelineExportRequest) -> otio.schema.Timeline:
        """Create OTIO timeline from timeline data"""
        # Create timeline
        timeline = otio.schema.Timeline(
            name=timeline_data["name"],
            global_start_time=otio.opentime.RationalTime(
                value=self._timecode_to_frames(timeline_data.get("start_timecode", "01:00:00:00")),
                rate=self.frame_rate
            )
        )
        
        # Create tracks
        for track_data in timeline_data["tracks"]:
            if track_data["type"] == "video":
                otio_track = await self._create_video_track(track_data)
                timeline.video_tracks().append(otio_track)
            elif track_data["type"] == "audio":
                otio_track = await self._create_audio_track(track_data)
                timeline.audio_tracks().append(otio_track)
        
        return timeline
    
    async def _create_video_track(self, track_data: Dict[str, Any]) -> otio.schema.Track:
        """Create OTIO video track"""
        track = otio.schema.Track(
            name=track_data["name"],
            kind=otio.schema.TrackKind.Video
        )
        
        # Add clips to track
        for clip_data in track_data["clips"]:
            # Create media reference
            media_ref = otio.schema.ExternalReference(
                target_url=f"file://{clip_data['file_path']}",
                available_range=otio.opentime.TimeRange(
                    start_time=otio.opentime.RationalTime(0, self.frame_rate),
                    duration=otio.opentime.RationalTime(
                        clip_data["source_out"] - clip_data["source_in"],
                        self.frame_rate
                    )
                )
            )
            
            # Create clip
            clip = otio.schema.Clip(
                name=clip_data["name"],
                media_reference=media_ref,
                source_range=otio.opentime.TimeRange(
                    start_time=otio.opentime.RationalTime(clip_data["source_in"], self.frame_rate),
                    duration=otio.opentime.RationalTime(clip_data["duration"], self.frame_rate)
                )
            )
            
            # Add metadata
            clip.metadata.update({
                "MAMS": {
                    "asset_id": clip_data["asset_id"],
                    "clip_id": clip_data["id"],
                    "speed": clip_data.get("speed", 1.0)
                }
            })
            
            # Add effects if present
            if clip_data.get("effects"):
                for effect_data in clip_data["effects"]:
                    effect = otio.schema.Effect(
                        name=effect_data.get("name", "Unknown Effect"),
                        effect_name=effect_data.get("type", "unknown")
                    )
                    effect.metadata.update(effect_data.get("parameters", {}))
                    clip.effects.append(effect)
            
            track.append(clip)
            
            # Add transitions if present
            if clip_data.get("transitions"):
                for transition_data in clip_data["transitions"]:
                    transition = otio.schema.Transition(
                        name=transition_data.get("name", "Cross Dissolve"),
                        transition_type=transition_data.get("type", "SMPTE_Dissolve"),
                        in_offset=otio.opentime.RationalTime(
                            transition_data.get("duration", 25) // 2,
                            self.frame_rate
                        ),
                        out_offset=otio.opentime.RationalTime(
                            transition_data.get("duration", 25) // 2,
                            self.frame_rate
                        )
                    )
                    track.append(transition)
        
        return track
    
    async def _create_audio_track(self, track_data: Dict[str, Any]) -> otio.schema.Track:
        """Create OTIO audio track"""
        track = otio.schema.Track(
            name=track_data["name"],
            kind=otio.schema.TrackKind.Audio
        )
        
        # Add clips to track
        for clip_data in track_data["clips"]:
            # Create media reference
            media_ref = otio.schema.ExternalReference(
                target_url=f"file://{clip_data['file_path']}",
                available_range=otio.opentime.TimeRange(
                    start_time=otio.opentime.RationalTime(0, self.frame_rate),
                    duration=otio.opentime.RationalTime(
                        clip_data["source_out"] - clip_data["source_in"],
                        self.frame_rate
                    )
                )
            )
            
            # Create clip
            clip = otio.schema.Clip(
                name=clip_data["name"],
                media_reference=media_ref,
                source_range=otio.opentime.TimeRange(
                    start_time=otio.opentime.RationalTime(clip_data["source_in"], self.frame_rate),
                    duration=otio.opentime.RationalTime(clip_data["duration"], self.frame_rate)
                )
            )
            
            # Add metadata
            clip.metadata.update({
                "MAMS": {
                    "asset_id": clip_data["asset_id"],
                    "clip_id": clip_data["id"],
                    "speed": clip_data.get("speed", 1.0)
                }
            })
            
            # Add effects if present
            if clip_data.get("effects"):
                for effect_data in clip_data["effects"]:
                    effect = otio.schema.Effect(
                        name=effect_data.get("name", "Unknown Effect"),
                        effect_name=effect_data.get("type", "unknown")
                    )
                    effect.metadata.update(effect_data.get("parameters", {}))
                    clip.effects.append(effect)
            
            track.append(clip)
        
        return track
    
    def _timecode_to_frames(self, timecode: str) -> int:
        """Convert timecode format HH:MM:SS:FF to frames"""
        parts = timecode.split(':')
        if len(parts) != 4:
            raise ValueError(f"Invalid timecode format: {timecode}")
        
        hours, minutes, seconds, frames = map(int, parts)
        total_frames = (hours * 3600 + minutes * 60 + seconds) * self.frame_rate + frames
        return int(total_frames)
    
    def _frames_to_timecode(self, frames: int) -> str:
        """Convert frames to timecode format HH:MM:SS:FF"""
        total_seconds = frames / self.frame_rate
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        frame_remainder = int(frames % self.frame_rate)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frame_remainder:02d}"
    
    async def _write_otio_file(self, timeline: otio.schema.Timeline, request: TimelineExportRequest) -> Path:
        """Write OTIO timeline to file"""
        export_dir = Path(settings.EXPORT_DIR) / "otio"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{request.timeline_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.otio"
        file_path = export_dir / filename
        
        # Write OTIO file
        otio.adapters.write_to_file(timeline, str(file_path))
        
        return file_path
    
    async def validate_export(self, export_path: Path) -> bool:
        """Validate OTIO export file"""
        try:
            if not export_path.exists():
                return False
            
            # Try to read the OTIO file
            timeline = otio.adapters.read_from_file(str(export_path))
            
            if not isinstance(timeline, otio.schema.Timeline):
                logger.error("Invalid OTIO format: not a timeline")
                return False
            
            # Check for tracks
            if not timeline.video_tracks() and not timeline.audio_tracks():
                logger.error("Invalid OTIO format: no tracks found")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"OTIO validation failed: {str(e)}")
            return False
    
    async def export_with_adapters(self, request: TimelineExportRequest, adapter_name: str = "fcp_xml") -> ExportResult:
        """Export using specific OTIO adapter"""
        try:
            logger.info(f"Starting OTIO export with adapter {adapter_name} for timeline {request.timeline_id}")
            
            # Get timeline data
            timeline_data = await self._get_timeline_data(request.timeline_id)
            
            # Create OTIO timeline
            otio_timeline = await self._create_otio_timeline(timeline_data, request)
            
            # Write using specific adapter
            export_path = await self._write_with_adapter(otio_timeline, request, adapter_name)
            
            result = ExportResult(
                export_id=str(uuid.uuid4()),
                timeline_id=request.timeline_id,
                format=f"otio_{adapter_name}",
                file_path=str(export_path),
                status="completed",
                created_at=datetime.utcnow(),
                metadata={
                    "timeline_name": timeline_data["name"],
                    "adapter": adapter_name,
                    "frame_rate": self.frame_rate
                }
            )
            
            logger.info(f"OTIO export with adapter {adapter_name} completed successfully: {export_path}")
            return result
            
        except Exception as e:
            logger.error(f"OTIO export with adapter {adapter_name} failed: {str(e)}")
            raise ExportError(f"OTIO export with adapter {adapter_name} failed: {str(e)}")
    
    async def _write_with_adapter(self, timeline: otio.schema.Timeline, request: TimelineExportRequest, adapter_name: str) -> Path:
        """Write timeline using specific OTIO adapter"""
        export_dir = Path(settings.EXPORT_DIR) / "otio" / adapter_name
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Get file extension based on adapter
        extensions = {
            "fcp_xml": ".xml",
            "premiere_xml": ".xml",
            "resolve_xml": ".xml",
            "avid_log_exchange": ".ale",
            "cmx_3600": ".edl",
            "rv": ".rv"
        }
        
        extension = extensions.get(adapter_name, ".txt")
        filename = f"{request.timeline_id}_{adapter_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{extension}"
        file_path = export_dir / filename
        
        # Write using adapter
        otio.adapters.write_to_file(
            timeline, 
            str(file_path), 
            adapter_name=adapter_name
        )
        
        return file_path
    
    async def get_available_adapters(self) -> List[Dict[str, Any]]:
        """Get available OTIO adapters"""
        adapters = []
        
        try:
            # Get all available adapters
            for adapter_name in otio.adapters.available_adapter_names():
                adapter_info = {
                    "name": adapter_name,
                    "description": f"OTIO adapter for {adapter_name}",
                    "read_supported": adapter_name in otio.adapters.available_adapter_names(read=True),
                    "write_supported": adapter_name in otio.adapters.available_adapter_names(write=True),
                    "suffixes": otio.adapters.suffixes_with_defined_adapters().get(adapter_name, [])
                }
                adapters.append(adapter_info)
            
        except Exception as e:
            logger.error(f"Failed to get OTIO adapters: {str(e)}")
        
        return adapters
    
    async def convert_from_otio(self, otio_file_path: Path, target_format: str) -> ExportResult:
        """Convert an OTIO file to another format"""
        try:
            # Read OTIO file
            timeline = otio.adapters.read_from_file(str(otio_file_path))
            
            # Create export request
            request = TimelineExportRequest(
                timeline_id=str(uuid.uuid4()),
                format=target_format,
                include_media=True,
                include_effects=True,
                include_audio=True
            )
            
            # Export to target format
            if target_format == "xml":
                return await self.export_with_adapters(request, "fcp_xml")
            elif target_format == "edl":
                return await self.export_with_adapters(request, "cmx_3600")
            else:
                raise ExportError(f"Unsupported target format: {target_format}")
                
        except Exception as e:
            logger.error(f"OTIO conversion failed: {str(e)}")
            raise ExportError(f"OTIO conversion failed: {str(e)}")
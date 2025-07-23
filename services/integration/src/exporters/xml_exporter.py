"""
XML Exporter for Adobe Premiere Pro (FCP7 XML Format)
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
import xml.etree.ElementTree as ET
from xml.dom import minidom

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.schemas import TimelineExportRequest, ExportResult
from ..core.config import settings
from ..core.exceptions import ExportError
from ..core.logger import get_logger

logger = get_logger(__name__)


class XMLTrack(BaseModel):
    """XML Track representation"""
    track_id: str
    track_name: str
    track_type: str  # 'video', 'audio'
    track_number: int
    clips: List[Dict[str, Any]] = Field(default_factory=list)
    enabled: bool = True
    locked: bool = False


class XMLClip(BaseModel):
    """XML Clip representation"""
    clip_id: str
    clip_name: str
    source_file: str
    start_time: int  # in frames
    duration: int  # in frames
    source_in: int  # in frames
    source_out: int  # in frames
    speed: float = 1.0
    
    # Video specific
    width: int = 1920
    height: int = 1080
    
    # Audio specific
    audio_channels: int = 2
    audio_rate: int = 48000
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class XMLSequence(BaseModel):
    """XML Sequence representation"""
    sequence_id: str
    sequence_name: str
    duration: int  # in frames
    frame_rate: float = 25.0
    width: int = 1920
    height: int = 1080
    audio_rate: int = 48000
    video_tracks: List[XMLTrack] = Field(default_factory=list)
    audio_tracks: List[XMLTrack] = Field(default_factory=list)


class XMLExporter:
    """XML Exporter for Adobe Premiere Pro (FCP7 XML Format)"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.export_format = "xml"
        self.version = "3"
        
    async def export_timeline(self, request: TimelineExportRequest) -> ExportResult:
        """Export timeline to FCP7 XML format"""
        try:
            logger.info(f"Starting XML export for timeline {request.timeline_id}")
            
            # Get timeline data
            timeline_data = await self._get_timeline_data(request.timeline_id)
            
            # Create XML sequence
            sequence = await self._create_xml_sequence(timeline_data, request)
            
            # Generate XML structure
            xml_root = await self._generate_xml_structure(sequence)
            
            # Write XML file
            export_path = await self._write_xml_file(xml_root, request)
            
            result = ExportResult(
                export_id=str(uuid.uuid4()),
                timeline_id=request.timeline_id,
                format=self.export_format,
                file_path=str(export_path),
                status="completed",
                created_at=datetime.utcnow(),
                metadata={
                    "sequence_name": sequence.sequence_name,
                    "duration_frames": sequence.duration,
                    "frame_rate": sequence.frame_rate,
                    "resolution": f"{sequence.width}x{sequence.height}",
                    "video_tracks": len(sequence.video_tracks),
                    "audio_tracks": len(sequence.audio_tracks),
                    "total_clips": sum(len(track.clips) for track in sequence.video_tracks + sequence.audio_tracks)
                }
            )
            
            logger.info(f"XML export completed successfully: {export_path}")
            return result
            
        except Exception as e:
            logger.error(f"XML export failed: {str(e)}")
            raise ExportError(f"XML export failed: {str(e)}")
    
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
            "tracks": [
                {
                    "id": "track_v1",
                    "name": "Video 1",
                    "type": "video",
                    "clips": [
                        {
                            "id": "clip_001",
                            "name": "Shot_001.mov",
                            "asset_id": "asset_001",
                            "start_time": 0,
                            "duration": 1500,
                            "source_in": 0,
                            "source_out": 1500,
                            "file_path": "/storage/media/Shot_001.mov",
                            "width": 1920,
                            "height": 1080
                        }
                    ]
                },
                {
                    "id": "track_a1",
                    "name": "Audio 1",
                    "type": "audio",
                    "clips": [
                        {
                            "id": "clip_audio_001",
                            "name": "Audio_001.wav",
                            "asset_id": "asset_audio_001",
                            "start_time": 0,
                            "duration": 1500,
                            "source_in": 0,
                            "source_out": 1500,
                            "file_path": "/storage/media/Audio_001.wav",
                            "audio_channels": 2,
                            "audio_rate": 48000
                        }
                    ]
                }
            ]
        }
    
    async def _create_xml_sequence(self, timeline_data: Dict[str, Any], request: TimelineExportRequest) -> XMLSequence:
        """Create XML sequence from timeline data"""
        sequence_id = str(uuid.uuid4())
        sequence_name = timeline_data["name"]
        
        # Parse resolution
        resolution = timeline_data["resolution"]
        width, height = map(int, resolution.split('x'))
        
        sequence = XMLSequence(
            sequence_id=sequence_id,
            sequence_name=sequence_name,
            duration=timeline_data["duration"],
            frame_rate=timeline_data["frame_rate"],
            width=width,
            height=height
        )
        
        # Process tracks
        video_track_num = 1
        audio_track_num = 1
        
        for track_data in timeline_data["tracks"]:
            if track_data["type"] == "video":
                xml_track = await self._create_video_track(track_data, video_track_num)
                sequence.video_tracks.append(xml_track)
                video_track_num += 1
            elif track_data["type"] == "audio":
                xml_track = await self._create_audio_track(track_data, audio_track_num)
                sequence.audio_tracks.append(xml_track)
                audio_track_num += 1
        
        return sequence
    
    async def _create_video_track(self, track_data: Dict[str, Any], track_number: int) -> XMLTrack:
        """Create XML video track"""
        track = XMLTrack(
            track_id=track_data["id"],
            track_name=track_data["name"],
            track_type="video",
            track_number=track_number
        )
        
        # Process clips
        for clip_data in track_data["clips"]:
            xml_clip = XMLClip(
                clip_id=clip_data["id"],
                clip_name=clip_data["name"],
                source_file=clip_data["file_path"],
                start_time=clip_data["start_time"],
                duration=clip_data["duration"],
                source_in=clip_data["source_in"],
                source_out=clip_data["source_out"],
                width=clip_data.get("width", 1920),
                height=clip_data.get("height", 1080)
            )
            
            track.clips.append(xml_clip.dict())
        
        return track
    
    async def _create_audio_track(self, track_data: Dict[str, Any], track_number: int) -> XMLTrack:
        """Create XML audio track"""
        track = XMLTrack(
            track_id=track_data["id"],
            track_name=track_data["name"],
            track_type="audio",
            track_number=track_number
        )
        
        # Process clips
        for clip_data in track_data["clips"]:
            xml_clip = XMLClip(
                clip_id=clip_data["id"],
                clip_name=clip_data["name"],
                source_file=clip_data["file_path"],
                start_time=clip_data["start_time"],
                duration=clip_data["duration"],
                source_in=clip_data["source_in"],
                source_out=clip_data["source_out"],
                audio_channels=clip_data.get("audio_channels", 2),
                audio_rate=clip_data.get("audio_rate", 48000)
            )
            
            track.clips.append(xml_clip.dict())
        
        return track
    
    async def _generate_xml_structure(self, sequence: XMLSequence) -> ET.Element:
        """Generate FCP7 XML structure"""
        # Create root element
        root = ET.Element("xmeml")
        root.set("version", "3")
        
        # Create project element
        project = ET.SubElement(root, "project")
        project_name = ET.SubElement(project, "name")
        project_name.text = f"MAMS_Export_{sequence.sequence_name}"
        
        # Create children element
        children = ET.SubElement(project, "children")
        
        # Create sequence element
        seq_elem = ET.SubElement(children, "sequence")
        seq_elem.set("id", sequence.sequence_id)
        
        # Sequence properties
        seq_name = ET.SubElement(seq_elem, "name")
        seq_name.text = sequence.sequence_name
        
        seq_duration = ET.SubElement(seq_elem, "duration")
        seq_duration.text = str(sequence.duration)
        
        # Rate (frame rate)
        rate = ET.SubElement(seq_elem, "rate")
        timebase = ET.SubElement(rate, "timebase")
        timebase.text = str(int(sequence.frame_rate))
        ntsc = ET.SubElement(rate, "ntsc")
        ntsc.text = "FALSE"
        
        # Media
        media = ET.SubElement(seq_elem, "media")
        
        # Video tracks
        if sequence.video_tracks:
            video = ET.SubElement(media, "video")
            video_format = ET.SubElement(video, "format")
            
            # Video format properties
            samplecharacteristics = ET.SubElement(video_format, "samplecharacteristics")
            width = ET.SubElement(samplecharacteristics, "width")
            width.text = str(sequence.width)
            height = ET.SubElement(samplecharacteristics, "height")
            height.text = str(sequence.height)
            anamorphic = ET.SubElement(samplecharacteristics, "anamorphic")
            anamorphic.text = "FALSE"
            pixelaspectratio = ET.SubElement(samplecharacteristics, "pixelaspectratio")
            pixelaspectratio.text = "square"
            fielddominance = ET.SubElement(samplecharacteristics, "fielddominance")
            fielddominance.text = "none"
            
            # Video rate
            video_rate = ET.SubElement(samplecharacteristics, "rate")
            video_timebase = ET.SubElement(video_rate, "timebase")
            video_timebase.text = str(int(sequence.frame_rate))
            video_ntsc = ET.SubElement(video_rate, "ntsc")
            video_ntsc.text = "FALSE"
            
            # Video tracks
            for track in sequence.video_tracks:
                track_elem = ET.SubElement(video, "track")
                
                # Track clips
                for clip in track.clips:
                    clip_elem = ET.SubElement(track_elem, "clipitem")
                    clip_elem.set("id", clip["clip_id"])
                    
                    clip_name = ET.SubElement(clip_elem, "name")
                    clip_name.text = clip["clip_name"]
                    
                    clip_duration = ET.SubElement(clip_elem, "duration")
                    clip_duration.text = str(clip["duration"])
                    
                    clip_start = ET.SubElement(clip_elem, "start")
                    clip_start.text = str(clip["start_time"])
                    
                    clip_end = ET.SubElement(clip_elem, "end")
                    clip_end.text = str(clip["start_time"] + clip["duration"])
                    
                    clip_in = ET.SubElement(clip_elem, "in")
                    clip_in.text = str(clip["source_in"])
                    
                    clip_out = ET.SubElement(clip_elem, "out")
                    clip_out.text = str(clip["source_out"])
                    
                    # File reference
                    file_ref = ET.SubElement(clip_elem, "file")
                    file_ref.set("id", f"file_{clip['clip_id']}")
                    
                    file_name = ET.SubElement(file_ref, "name")
                    file_name.text = Path(clip["source_file"]).name
                    
                    file_pathurl = ET.SubElement(file_ref, "pathurl")
                    file_pathurl.text = f"file://{clip['source_file']}"
                    
                    # File rate
                    file_rate = ET.SubElement(file_ref, "rate")
                    file_timebase = ET.SubElement(file_rate, "timebase")
                    file_timebase.text = str(int(sequence.frame_rate))
                    file_ntsc = ET.SubElement(file_rate, "ntsc")
                    file_ntsc.text = "FALSE"
                    
                    # File duration
                    file_duration = ET.SubElement(file_ref, "duration")
                    file_duration.text = str(clip["duration"])
                    
                    # Media characteristics
                    file_media = ET.SubElement(file_ref, "media")
                    file_video = ET.SubElement(file_media, "video")
                    file_video_format = ET.SubElement(file_video, "format")
                    file_samplecharacteristics = ET.SubElement(file_video_format, "samplecharacteristics")
                    
                    file_width = ET.SubElement(file_samplecharacteristics, "width")
                    file_width.text = str(clip["width"])
                    file_height = ET.SubElement(file_samplecharacteristics, "height")
                    file_height.text = str(clip["height"])
        
        # Audio tracks
        if sequence.audio_tracks:
            audio = ET.SubElement(media, "audio")
            audio_format = ET.SubElement(audio, "format")
            
            # Audio format properties
            samplecharacteristics = ET.SubElement(audio_format, "samplecharacteristics")
            depth = ET.SubElement(samplecharacteristics, "depth")
            depth.text = "16"
            samplerate = ET.SubElement(samplecharacteristics, "samplerate")
            samplerate.text = str(sequence.audio_rate)
            
            # Audio tracks
            for track in sequence.audio_tracks:
                track_elem = ET.SubElement(audio, "track")
                
                # Track clips
                for clip in track.clips:
                    clip_elem = ET.SubElement(track_elem, "clipitem")
                    clip_elem.set("id", clip["clip_id"])
                    
                    clip_name = ET.SubElement(clip_elem, "name")
                    clip_name.text = clip["clip_name"]
                    
                    clip_duration = ET.SubElement(clip_elem, "duration")
                    clip_duration.text = str(clip["duration"])
                    
                    clip_start = ET.SubElement(clip_elem, "start")
                    clip_start.text = str(clip["start_time"])
                    
                    clip_end = ET.SubElement(clip_elem, "end")
                    clip_end.text = str(clip["start_time"] + clip["duration"])
                    
                    clip_in = ET.SubElement(clip_elem, "in")
                    clip_in.text = str(clip["source_in"])
                    
                    clip_out = ET.SubElement(clip_elem, "out")
                    clip_out.text = str(clip["source_out"])
                    
                    # File reference
                    file_ref = ET.SubElement(clip_elem, "file")
                    file_ref.set("id", f"file_{clip['clip_id']}")
                    
                    file_name = ET.SubElement(file_ref, "name")
                    file_name.text = Path(clip["source_file"]).name
                    
                    file_pathurl = ET.SubElement(file_ref, "pathurl")
                    file_pathurl.text = f"file://{clip['source_file']}"
                    
                    # File rate
                    file_rate = ET.SubElement(file_ref, "rate")
                    file_timebase = ET.SubElement(file_rate, "timebase")
                    file_timebase.text = str(int(sequence.frame_rate))
                    file_ntsc = ET.SubElement(file_rate, "ntsc")
                    file_ntsc.text = "FALSE"
                    
                    # File duration
                    file_duration = ET.SubElement(file_ref, "duration")
                    file_duration.text = str(clip["duration"])
                    
                    # Media characteristics
                    file_media = ET.SubElement(file_ref, "media")
                    file_audio = ET.SubElement(file_media, "audio")
                    file_audio_format = ET.SubElement(file_audio, "format")
                    file_samplecharacteristics = ET.SubElement(file_audio_format, "samplecharacteristics")
                    
                    file_depth = ET.SubElement(file_samplecharacteristics, "depth")
                    file_depth.text = "16"
                    file_samplerate = ET.SubElement(file_samplecharacteristics, "samplerate")
                    file_samplerate.text = str(clip["audio_rate"])
        
        return root
    
    async def _write_xml_file(self, xml_root: ET.Element, request: TimelineExportRequest) -> Path:
        """Write XML to file with proper formatting"""
        export_dir = Path(settings.EXPORT_DIR) / "xml"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{request.timeline_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xml"
        file_path = export_dir / filename
        
        # Pretty print XML
        rough_string = ET.tostring(xml_root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ")
        
        # Clean up extra whitespace
        pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
        
        async with asyncio.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(pretty_xml)
        
        return file_path
    
    async def validate_export(self, export_path: Path) -> bool:
        """Validate XML export file"""
        try:
            if not export_path.exists():
                return False
            
            # Parse XML to check for validity
            tree = ET.parse(export_path)
            root = tree.getroot()
            
            # Check for required elements
            if root.tag != "xmeml":
                logger.error("Invalid XML format: root element should be 'xmeml'")
                return False
            
            # Check for project element
            project = root.find("project")
            if project is None:
                logger.error("Invalid XML format: missing 'project' element")
                return False
            
            # Check for sequence element
            sequence = project.find("children/sequence")
            if sequence is None:
                logger.error("Invalid XML format: missing 'sequence' element")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"XML validation failed: {str(e)}")
            return False
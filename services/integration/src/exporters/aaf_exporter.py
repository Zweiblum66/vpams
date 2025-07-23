"""
AAF (Advanced Authoring Format) Exporter for Avid Media Composer Integration
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.schemas import TimelineExportRequest, ExportResult
from ..core.config import settings
from ..core.exceptions import ExportError
from ..core.logger import get_logger

logger = get_logger(__name__)


class AAFTrack(BaseModel):
    """AAF Track representation"""
    track_id: str
    track_name: str
    track_type: str  # 'video', 'audio', 'subtitle'
    media_kind: str  # 'Picture', 'Sound', 'Timecode', 'Subtitle'
    edit_rate: str = "25/1"  # Default PAL frame rate
    clips: List[Dict[str, Any]] = Field(default_factory=list)
    transitions: List[Dict[str, Any]] = Field(default_factory=list)
    enabled: bool = True
    locked: bool = False


class AAFClip(BaseModel):
    """AAF Clip representation"""
    clip_id: str
    clip_name: str
    source_file: str
    source_mob_id: str
    start_time: int  # in frames
    duration: int  # in frames
    source_in: int  # in frames
    source_out: int  # in frames
    speed: float = 1.0
    reverse: bool = False
    
    # Video specific
    video_effects: List[Dict[str, Any]] = Field(default_factory=list)
    opacity: float = 1.0
    
    # Audio specific
    audio_gain: float = 1.0
    audio_pan: float = 0.0
    audio_channels: int = 2
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    

class AAFComposition(BaseModel):
    """AAF Composition (Sequence) representation"""
    comp_id: str
    comp_name: str
    comp_length: int  # in frames
    edit_rate: str = "25/1"
    video_tracks: List[AAFTrack] = Field(default_factory=list)
    audio_tracks: List[AAFTrack] = Field(default_factory=list)
    timecode_track: Optional[AAFTrack] = None
    start_timecode: str = "01:00:00:00"


class AAFExporter:
    """AAF Exporter for Avid Media Composer"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.export_format = "aaf"
        self.version = "1.1"
        
    async def export_timeline(self, request: TimelineExportRequest) -> ExportResult:
        """Export timeline to AAF format"""
        try:
            logger.info(f"Starting AAF export for timeline {request.timeline_id}")
            
            # Get timeline data
            timeline_data = await self._get_timeline_data(request.timeline_id)
            
            # Create AAF composition
            composition = await self._create_aaf_composition(timeline_data, request)
            
            # Generate AAF XML structure
            aaf_xml = await self._generate_aaf_xml(composition)
            
            # Write AAF file
            export_path = await self._write_aaf_file(aaf_xml, request)
            
            # Create media references if requested
            if request.include_media:
                await self._create_media_references(composition, export_path)
            
            result = ExportResult(
                export_id=str(uuid.uuid4()),
                timeline_id=request.timeline_id,
                format=self.export_format,
                file_path=str(export_path),
                status="completed",
                created_at=datetime.utcnow(),
                metadata={
                    "composition_name": composition.comp_name,
                    "duration_frames": composition.comp_length,
                    "edit_rate": composition.edit_rate,
                    "video_tracks": len(composition.video_tracks),
                    "audio_tracks": len(composition.audio_tracks),
                    "total_clips": sum(len(track.clips) for track in composition.video_tracks + composition.audio_tracks)
                }
            )
            
            logger.info(f"AAF export completed successfully: {export_path}")
            return result
            
        except Exception as e:
            logger.error(f"AAF export failed: {str(e)}")
            raise ExportError(f"AAF export failed: {str(e)}")
    
    async def _get_timeline_data(self, timeline_id: str) -> Dict[str, Any]:
        """Get timeline data from database"""
        # This would query the timeline service
        # For now, return mock data structure
        return {
            "id": timeline_id,
            "name": "Timeline_001",
            "duration": 7200,  # 5 minutes at 25fps
            "frame_rate": 25,
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
                            "file_path": "/storage/media/Shot_001.mov"
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
                            "file_path": "/storage/media/Audio_001.wav"
                        }
                    ]
                }
            ]
        }
    
    async def _create_aaf_composition(self, timeline_data: Dict[str, Any], request: TimelineExportRequest) -> AAFComposition:
        """Create AAF composition from timeline data"""
        comp_id = str(uuid.uuid4())
        comp_name = timeline_data["name"]
        
        # Calculate composition length
        comp_length = timeline_data["duration"]
        
        # Create frame rate string
        frame_rate = timeline_data["frame_rate"]
        edit_rate = f"{frame_rate}/1"
        
        composition = AAFComposition(
            comp_id=comp_id,
            comp_name=comp_name,
            comp_length=comp_length,
            edit_rate=edit_rate
        )
        
        # Process tracks
        for track_data in timeline_data["tracks"]:
            if track_data["type"] == "video":
                aaf_track = await self._create_video_track(track_data, edit_rate)
                composition.video_tracks.append(aaf_track)
            elif track_data["type"] == "audio":
                aaf_track = await self._create_audio_track(track_data, edit_rate)
                composition.audio_tracks.append(aaf_track)
        
        return composition
    
    async def _create_video_track(self, track_data: Dict[str, Any], edit_rate: str) -> AAFTrack:
        """Create AAF video track"""
        track = AAFTrack(
            track_id=track_data["id"],
            track_name=track_data["name"],
            track_type="video",
            media_kind="Picture",
            edit_rate=edit_rate
        )
        
        # Process clips
        for clip_data in track_data["clips"]:
            aaf_clip = AAFClip(
                clip_id=clip_data["id"],
                clip_name=clip_data["name"],
                source_file=clip_data["file_path"],
                source_mob_id=str(uuid.uuid4()),
                start_time=clip_data["start_time"],
                duration=clip_data["duration"],
                source_in=clip_data["source_in"],
                source_out=clip_data["source_out"]
            )
            
            track.clips.append(aaf_clip.dict())
        
        return track
    
    async def _create_audio_track(self, track_data: Dict[str, Any], edit_rate: str) -> AAFTrack:
        """Create AAF audio track"""
        track = AAFTrack(
            track_id=track_data["id"],
            track_name=track_data["name"],
            track_type="audio",
            media_kind="Sound",
            edit_rate=edit_rate
        )
        
        # Process clips
        for clip_data in track_data["clips"]:
            aaf_clip = AAFClip(
                clip_id=clip_data["id"],
                clip_name=clip_data["name"],
                source_file=clip_data["file_path"],
                source_mob_id=str(uuid.uuid4()),
                start_time=clip_data["start_time"],
                duration=clip_data["duration"],
                source_in=clip_data["source_in"],
                source_out=clip_data["source_out"],
                audio_channels=2
            )
            
            track.clips.append(aaf_clip.dict())
        
        return track
    
    async def _generate_aaf_xml(self, composition: AAFComposition) -> str:
        """Generate AAF XML structure"""
        xml_header = """<?xml version="1.0" encoding="UTF-8"?>
<AAF xmlns="http://www.aafassociation.org/aafxml/1.0"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://www.aafassociation.org/aafxml/1.0 AAF.xsd">
"""
        
        xml_body = f"""  <Header>
    <ByteOrder>little</ByteOrder>
    <LastModified>{datetime.utcnow().isoformat()}Z</LastModified>
    <Version>
      <Major>1</Major>
      <Minor>1</Minor>
    </Version>
    <ObjectModelVersion>1</ObjectModelVersion>
    <MinorVersion>1</MinorVersion>
    <CreationTime>{datetime.utcnow().isoformat()}Z</CreationTime>
    <Platform>MAMS-{settings.APP_VERSION}</Platform>
    <CompanyName>MAMS</CompanyName>
    <ProductName>Digital Media Asset Management System</ProductName>
    <ProductVersion>{settings.APP_VERSION}</ProductVersion>
  </Header>
  
  <Content>
    <Mobs>
      <CompositionMob>
        <MobID>{composition.comp_id}</MobID>
        <Name>{composition.comp_name}</Name>
        <CreationTime>{datetime.utcnow().isoformat()}Z</CreationTime>
        <LastModified>{datetime.utcnow().isoformat()}Z</LastModified>
        <Slots>
"""
        
        # Add video tracks
        for i, track in enumerate(composition.video_tracks):
            xml_body += f"""          <TimelineSlot>
            <SlotID>{i + 1}</SlotID>
            <SlotName>{track.track_name}</SlotName>
            <PhysicalTrackNumber>{i + 1}</PhysicalTrackNumber>
            <Segment>
              <Sequence>
                <DataDefinition>Picture</DataDefinition>
                <Length>{composition.comp_length}</Length>
                <Components>
"""
            
            # Add clips
            for clip in track.clips:
                xml_body += f"""                  <SourceClip>
                    <DataDefinition>Picture</DataDefinition>
                    <Length>{clip['duration']}</Length>
                    <StartTime>{clip['start_time']}</StartTime>
                    <SourceID>{clip['source_mob_id']}</SourceID>
                    <SourceMobSlotID>1</SourceMobSlotID>
                  </SourceClip>
"""
            
            xml_body += """                </Components>
              </Sequence>
            </Segment>
          </TimelineSlot>
"""
        
        # Add audio tracks
        for i, track in enumerate(composition.audio_tracks):
            xml_body += f"""          <TimelineSlot>
            <SlotID>{i + 1 + len(composition.video_tracks)}</SlotID>
            <SlotName>{track.track_name}</SlotName>
            <PhysicalTrackNumber>{i + 1}</PhysicalTrackNumber>
            <Segment>
              <Sequence>
                <DataDefinition>Sound</DataDefinition>
                <Length>{composition.comp_length}</Length>
                <Components>
"""
            
            # Add clips
            for clip in track.clips:
                xml_body += f"""                  <SourceClip>
                    <DataDefinition>Sound</DataDefinition>
                    <Length>{clip['duration']}</Length>
                    <StartTime>{clip['start_time']}</StartTime>
                    <SourceID>{clip['source_mob_id']}</SourceID>
                    <SourceMobSlotID>1</SourceMobSlotID>
                  </SourceClip>
"""
            
            xml_body += """                </Components>
              </Sequence>
            </Segment>
          </TimelineSlot>
"""
        
        xml_footer = """        </Slots>
      </CompositionMob>
    </Mobs>
  </Content>
</AAF>"""
        
        return xml_header + xml_body + xml_footer
    
    async def _write_aaf_file(self, aaf_xml: str, request: TimelineExportRequest) -> Path:
        """Write AAF XML to file"""
        export_dir = Path(settings.EXPORT_DIR) / "aaf"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{request.timeline_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.aaf"
        file_path = export_dir / filename
        
        async with asyncio.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(aaf_xml)
        
        return file_path
    
    async def _create_media_references(self, composition: AAFComposition, export_path: Path):
        """Create media reference files for AAF export"""
        # Create media folder structure
        media_dir = export_path.parent / f"{export_path.stem}_media"
        media_dir.mkdir(exist_ok=True)
        
        # Create reference files or copy media
        all_tracks = composition.video_tracks + composition.audio_tracks
        
        for track in all_tracks:
            for clip in track.clips:
                source_file = Path(clip["source_file"])
                if source_file.exists():
                    # Create symbolic link or copy file
                    target_file = media_dir / source_file.name
                    if not target_file.exists():
                        try:
                            target_file.symlink_to(source_file)
                        except OSError:
                            # If symlink fails, copy the file
                            import shutil
                            shutil.copy2(source_file, target_file)
                        
                        logger.info(f"Created media reference: {target_file}")
    
    async def validate_export(self, export_path: Path) -> bool:
        """Validate AAF export file"""
        try:
            if not export_path.exists():
                return False
            
            # Basic XML validation
            with open(export_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required AAF elements
            required_elements = [
                '<AAF',
                '<Header>',
                '<Content>',
                '<Mobs>',
                '<CompositionMob>'
            ]
            
            for element in required_elements:
                if element not in content:
                    logger.error(f"Missing required AAF element: {element}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"AAF validation failed: {str(e)}")
            return False
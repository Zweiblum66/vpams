"""
OMF (Open Media Framework) Exporter for Pro Tools and other audio DAWs
"""

import asyncio
import struct
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import wave
import math

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.schemas import TimelineExportRequest, ExportResult
from ..core.config import settings
from ..core.exceptions import ExportError
from ..core.logger import get_logger

logger = get_logger(__name__)


class OMFTrack(BaseModel):
    """OMF Track representation"""
    track_id: str
    track_name: str
    track_number: int
    clips: List[Dict[str, Any]] = Field(default_factory=list)
    volume: float = 1.0
    pan: float = 0.0
    mute: bool = False
    solo: bool = False


class OMFClip(BaseModel):
    """OMF Clip representation"""
    clip_id: str
    clip_name: str
    source_file: str
    start_time: float  # in seconds
    duration: float  # in seconds
    source_in: float  # in seconds
    source_out: float  # in seconds
    volume: float = 1.0
    pan: float = 0.0
    fade_in: float = 0.0
    fade_out: float = 0.0
    
    # Audio specific
    sample_rate: int = 48000
    channels: int = 2
    bit_depth: int = 16


class OMFComposition(BaseModel):
    """OMF Composition representation"""
    comp_id: str
    comp_name: str
    duration: float  # in seconds
    sample_rate: int = 48000
    tracks: List[OMFTrack] = Field(default_factory=list)
    start_timecode: str = "01:00:00:00"
    frame_rate: float = 25.0


class OMFExporter:
    """OMF Exporter for Pro Tools and other audio DAWs"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.export_format = "omf"
        self.sample_rate = 48000
        self.frame_rate = 25.0
        
    async def export_timeline(self, request: TimelineExportRequest) -> ExportResult:
        """Export timeline to OMF format"""
        try:
            logger.info(f"Starting OMF export for timeline {request.timeline_id}")
            
            # Get timeline data
            timeline_data = await self._get_timeline_data(request.timeline_id)
            
            # Create OMF composition
            composition = await self._create_omf_composition(timeline_data, request)
            
            # Generate OMF file
            export_path = await self._write_omf_file(composition, request)
            
            # Copy audio files if requested
            if request.include_media:
                await self._copy_audio_files(composition, export_path)
            
            result = ExportResult(
                export_id=str(uuid.uuid4()),
                timeline_id=request.timeline_id,
                format=self.export_format,
                file_path=str(export_path),
                status="completed",
                created_at=datetime.utcnow(),
                metadata={
                    "composition_name": composition.comp_name,
                    "duration_seconds": composition.duration,
                    "sample_rate": composition.sample_rate,
                    "audio_tracks": len(composition.tracks),
                    "total_clips": sum(len(track.clips) for track in composition.tracks),
                    "frame_rate": composition.frame_rate
                }
            )
            
            logger.info(f"OMF export completed successfully: {export_path}")
            return result
            
        except Exception as e:
            logger.error(f"OMF export failed: {str(e)}")
            raise ExportError(f"OMF export failed: {str(e)}")
    
    async def _get_timeline_data(self, timeline_id: str) -> Dict[str, Any]:
        """Get timeline data from database"""
        # This would query the timeline service
        # For now, return mock data structure focused on audio
        return {
            "id": timeline_id,
            "name": "Audio_Timeline_001",
            "duration": 300.0,  # 5 minutes
            "frame_rate": 25.0,
            "sample_rate": 48000,
            "start_timecode": "01:00:00:00",
            "tracks": [
                {
                    "id": "track_a1",
                    "name": "Audio 1",
                    "type": "audio",
                    "track_number": 1,
                    "clips": [
                        {
                            "id": "clip_audio_001",
                            "name": "Voice_Over",
                            "asset_id": "asset_audio_001",
                            "start_time": 0.0,
                            "duration": 120.0,
                            "source_in": 0.0,
                            "source_out": 120.0,
                            "file_path": "/storage/media/Voice_Over.wav",
                            "volume": 1.0,
                            "pan": 0.0,
                            "sample_rate": 48000,
                            "channels": 2,
                            "bit_depth": 16
                        }
                    ]
                },
                {
                    "id": "track_a2",
                    "name": "Audio 2",
                    "type": "audio",
                    "track_number": 2,
                    "clips": [
                        {
                            "id": "clip_audio_002",
                            "name": "Background_Music",
                            "asset_id": "asset_audio_002",
                            "start_time": 30.0,
                            "duration": 180.0,
                            "source_in": 10.0,
                            "source_out": 190.0,
                            "file_path": "/storage/media/Background_Music.wav",
                            "volume": 0.6,
                            "pan": 0.0,
                            "sample_rate": 48000,
                            "channels": 2,
                            "bit_depth": 16
                        }
                    ]
                }
            ]
        }
    
    async def _create_omf_composition(self, timeline_data: Dict[str, Any], request: TimelineExportRequest) -> OMFComposition:
        """Create OMF composition from timeline data"""
        comp_id = str(uuid.uuid4())
        comp_name = timeline_data["name"]
        
        composition = OMFComposition(
            comp_id=comp_id,
            comp_name=comp_name,
            duration=timeline_data["duration"],
            sample_rate=timeline_data.get("sample_rate", 48000),
            frame_rate=timeline_data.get("frame_rate", 25.0),
            start_timecode=timeline_data.get("start_timecode", "01:00:00:00")
        )
        
        # Process audio tracks only
        for track_data in timeline_data["tracks"]:
            if track_data["type"] == "audio":
                omf_track = await self._create_audio_track(track_data)
                composition.tracks.append(omf_track)
        
        return composition
    
    async def _create_audio_track(self, track_data: Dict[str, Any]) -> OMFTrack:
        """Create OMF audio track"""
        track = OMFTrack(
            track_id=track_data["id"],
            track_name=track_data["name"],
            track_number=track_data.get("track_number", 1),
            volume=track_data.get("volume", 1.0),
            pan=track_data.get("pan", 0.0),
            mute=track_data.get("mute", False),
            solo=track_data.get("solo", False)
        )
        
        # Process clips
        for clip_data in track_data["clips"]:
            omf_clip = OMFClip(
                clip_id=clip_data["id"],
                clip_name=clip_data["name"],
                source_file=clip_data["file_path"],
                start_time=clip_data["start_time"],
                duration=clip_data["duration"],
                source_in=clip_data["source_in"],
                source_out=clip_data["source_out"],
                volume=clip_data.get("volume", 1.0),
                pan=clip_data.get("pan", 0.0),
                fade_in=clip_data.get("fade_in", 0.0),
                fade_out=clip_data.get("fade_out", 0.0),
                sample_rate=clip_data.get("sample_rate", 48000),
                channels=clip_data.get("channels", 2),
                bit_depth=clip_data.get("bit_depth", 16)
            )
            
            track.clips.append(omf_clip.dict())
        
        return track
    
    async def _write_omf_file(self, composition: OMFComposition, request: TimelineExportRequest) -> Path:
        """Write OMF file (simplified implementation)"""
        export_dir = Path(settings.EXPORT_DIR) / "omf"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{request.timeline_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.omf"
        file_path = export_dir / filename
        
        # Create OMF structure (simplified version)
        # In a real implementation, this would use the OMF specification
        omf_data = await self._create_omf_structure(composition)
        
        with open(file_path, 'wb') as f:
            f.write(omf_data)
        
        return file_path
    
    async def _create_omf_structure(self, composition: OMFComposition) -> bytes:
        """Create OMF binary structure (simplified)"""
        # This is a very simplified OMF structure
        # Real OMF files are much more complex and follow the OMF specification
        
        header = b'OMF2'  # OMF version 2 identifier
        
        # Composition header
        comp_header = struct.pack('<I', len(composition.comp_name.encode('utf-8')))
        comp_header += composition.comp_name.encode('utf-8')
        comp_header += struct.pack('<f', composition.duration)
        comp_header += struct.pack('<I', composition.sample_rate)
        comp_header += struct.pack('<I', len(composition.tracks))
        
        # Track data
        track_data = b''
        for track in composition.tracks:
            # Track header
            track_header = struct.pack('<I', len(track.track_name.encode('utf-8')))
            track_header += track.track_name.encode('utf-8')
            track_header += struct.pack('<I', track.track_number)
            track_header += struct.pack('<f', track.volume)
            track_header += struct.pack('<f', track.pan)
            track_header += struct.pack('<I', len(track.clips))
            
            # Clip data
            clip_data = b''
            for clip in track.clips:
                clip_header = struct.pack('<I', len(clip["clip_name"].encode('utf-8')))
                clip_header += clip["clip_name"].encode('utf-8')
                clip_header += struct.pack('<I', len(clip["source_file"].encode('utf-8')))
                clip_header += clip["source_file"].encode('utf-8')
                clip_header += struct.pack('<f', clip["start_time"])
                clip_header += struct.pack('<f', clip["duration"])
                clip_header += struct.pack('<f', clip["source_in"])
                clip_header += struct.pack('<f', clip["source_out"])
                clip_header += struct.pack('<f', clip["volume"])
                clip_header += struct.pack('<f', clip["pan"])
                clip_header += struct.pack('<I', clip["sample_rate"])
                clip_header += struct.pack('<I', clip["channels"])
                clip_header += struct.pack('<I', clip["bit_depth"])
                
                clip_data += clip_header
            
            track_data += track_header + clip_data
        
        return header + comp_header + track_data
    
    async def _copy_audio_files(self, composition: OMFComposition, export_path: Path):
        """Copy audio files to export directory"""
        audio_dir = export_path.parent / f"{export_path.stem}_audio"
        audio_dir.mkdir(exist_ok=True)
        
        for track in composition.tracks:
            for clip in track.clips:
                source_file = Path(clip["source_file"])
                if source_file.exists():
                    # Copy audio file
                    target_file = audio_dir / source_file.name
                    if not target_file.exists():
                        import shutil
                        shutil.copy2(source_file, target_file)
                        logger.info(f"Copied audio file: {target_file}")
                    
                    # Create trimmed version if needed
                    if clip["source_in"] > 0 or clip["source_out"] < self._get_audio_duration(source_file):
                        trimmed_file = audio_dir / f"{source_file.stem}_trimmed{source_file.suffix}"
                        await self._create_trimmed_audio(
                            source_file, 
                            trimmed_file, 
                            clip["source_in"], 
                            clip["source_out"]
                        )
    
    def _get_audio_duration(self, audio_file: Path) -> float:
        """Get audio file duration in seconds"""
        try:
            with wave.open(str(audio_file), 'r') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                duration = frames / float(rate)
                return duration
        except Exception as e:
            logger.warning(f"Could not get duration for {audio_file}: {str(e)}")
            return 0.0
    
    async def _create_trimmed_audio(self, source_file: Path, target_file: Path, start_time: float, end_time: float):
        """Create trimmed version of audio file"""
        try:
            # This is a simplified implementation
            # In practice, you'd use FFmpeg or similar tool
            with wave.open(str(source_file), 'r') as source_wav:
                params = source_wav.getparams()
                rate = params.framerate
                
                # Calculate frame positions
                start_frame = int(start_time * rate)
                end_frame = int(end_time * rate)
                
                # Read audio data
                source_wav.setpos(start_frame)
                audio_data = source_wav.readframes(end_frame - start_frame)
                
                # Write trimmed audio
                with wave.open(str(target_file), 'w') as target_wav:
                    target_wav.setparams(params)
                    target_wav.writeframes(audio_data)
                
                logger.info(f"Created trimmed audio: {target_file}")
                
        except Exception as e:
            logger.error(f"Failed to create trimmed audio: {str(e)}")
    
    async def validate_export(self, export_path: Path) -> bool:
        """Validate OMF export file"""
        try:
            if not export_path.exists():
                return False
            
            # Check file size
            if export_path.stat().st_size < 8:  # Minimum size for header
                logger.error("OMF file too small")
                return False
            
            # Check OMF header
            with open(export_path, 'rb') as f:
                header = f.read(4)
                if header != b'OMF2':
                    logger.error("Invalid OMF header")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"OMF validation failed: {str(e)}")
            return False
    
    async def export_aaf_to_omf(self, aaf_file: Path, request: TimelineExportRequest) -> ExportResult:
        """Convert AAF file to OMF format"""
        try:
            logger.info(f"Converting AAF to OMF: {aaf_file}")
            
            # This would parse the AAF file and extract audio information
            # For now, we'll create a mock conversion
            
            # Create mock composition from AAF
            composition = OMFComposition(
                comp_id=str(uuid.uuid4()),
                comp_name=f"Converted_{aaf_file.stem}",
                duration=300.0,
                sample_rate=48000,
                frame_rate=25.0
            )
            
            # Write OMF file
            export_path = await self._write_omf_file(composition, request)
            
            result = ExportResult(
                export_id=str(uuid.uuid4()),
                timeline_id=request.timeline_id,
                format="omf",
                file_path=str(export_path),
                status="completed",
                created_at=datetime.utcnow(),
                metadata={
                    "source_aaf": str(aaf_file),
                    "conversion_type": "aaf_to_omf"
                }
            )
            
            logger.info(f"AAF to OMF conversion completed: {export_path}")
            return result
            
        except Exception as e:
            logger.error(f"AAF to OMF conversion failed: {str(e)}")
            raise ExportError(f"AAF to OMF conversion failed: {str(e)}")
    
    async def create_audio_session_xml(self, composition: OMFComposition) -> str:
        """Create Pro Tools session XML alongside OMF"""
        session_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ProToolsSession version="10.0">
    <SessionName>{composition.comp_name}</SessionName>
    <SessionLength>{composition.duration}</SessionLength>
    <SampleRate>{composition.sample_rate}</SampleRate>
    <TimecodeRate>{composition.frame_rate}</TimecodeRate>
    <StartTimecode>{composition.start_timecode}</StartTimecode>
    
    <Tracks>
"""
        
        for track in composition.tracks:
            session_xml += f"""        <Track>
            <Name>{track.track_name}</Name>
            <Number>{track.track_number}</Number>
            <Volume>{track.volume}</Volume>
            <Pan>{track.pan}</Pan>
            <Mute>{str(track.mute).lower()}</Mute>
            <Solo>{str(track.solo).lower()}</Solo>
            
            <Clips>
"""
            
            for clip in track.clips:
                session_xml += f"""                <Clip>
                    <Name>{clip['clip_name']}</Name>
                    <SourceFile>{clip['source_file']}</SourceFile>
                    <StartTime>{clip['start_time']}</StartTime>
                    <Duration>{clip['duration']}</Duration>
                    <SourceIn>{clip['source_in']}</SourceIn>
                    <SourceOut>{clip['source_out']}</SourceOut>
                    <Volume>{clip['volume']}</Volume>
                    <Pan>{clip['pan']}</Pan>
                    <SampleRate>{clip['sample_rate']}</SampleRate>
                    <Channels>{clip['channels']}</Channels>
                    <BitDepth>{clip['bit_depth']}</BitDepth>
                </Clip>
"""
            
            session_xml += """            </Clips>
        </Track>
"""
        
        session_xml += """    </Tracks>
</ProToolsSession>"""
        
        return session_xml
    
    async def get_omf_info(self, omf_file: Path) -> Dict[str, Any]:
        """Get information about an OMF file"""
        try:
            if not omf_file.exists():
                return {"error": "File not found"}
            
            with open(omf_file, 'rb') as f:
                # Read header
                header = f.read(4)
                if header != b'OMF2':
                    return {"error": "Invalid OMF format"}
                
                # Read composition info
                name_len = struct.unpack('<I', f.read(4))[0]
                name = f.read(name_len).decode('utf-8')
                duration = struct.unpack('<f', f.read(4))[0]
                sample_rate = struct.unpack('<I', f.read(4))[0]
                track_count = struct.unpack('<I', f.read(4))[0]
                
                return {
                    "name": name,
                    "duration": duration,
                    "sample_rate": sample_rate,
                    "track_count": track_count,
                    "file_size": omf_file.stat().st_size,
                    "format": "OMF2"
                }
                
        except Exception as e:
            return {"error": str(e)}
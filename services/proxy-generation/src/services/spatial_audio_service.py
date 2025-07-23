"""
Spatial Audio Service for 3D/immersive audio processing
"""

import os
import json
import asyncio
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from datetime import datetime
import aiofiles
import numpy as np
from pathlib import Path
import math

from ..core.logging import get_logger
from ..core.exceptions import ProxyGenerationError

logger = get_logger(__name__)


class SpatialAudioFormat(Enum):
    """Spatial audio format types"""
    STEREO = "stereo"
    SURROUND_51 = "5.1"
    SURROUND_71 = "7.1"
    SURROUND_714 = "7.1.4"  # Dolby Atmos
    SURROUND_916 = "9.1.6"  # Extended Atmos
    AMBISONIC_FOA = "ambisonic_foa"  # First Order Ambisonics (4 channels)
    AMBISONIC_HOA = "ambisonic_hoa"  # Higher Order Ambisonics (9+ channels)
    BINAURAL = "binaural"
    OBJECT_BASED = "object_based"  # Dolby Atmos, DTS:X


class AmbisonicOrder(Enum):
    """Ambisonic order levels"""
    FIRST = 1   # 4 channels (W, X, Y, Z)
    SECOND = 2  # 9 channels
    THIRD = 3   # 16 channels
    FOURTH = 4  # 25 channels
    FIFTH = 5   # 36 channels


class SpatialCodec(Enum):
    """Spatial audio codecs"""
    AAC_SPATIAL = "aac_spatial"
    EAC3_ATMOS = "eac3_atmos"  # Dolby Digital Plus with Atmos
    TRUEHD_ATMOS = "truehd_atmos"  # Dolby TrueHD with Atmos
    DTS_X = "dts_x"
    OPUS_SPATIAL = "opus_spatial"
    FLAC_SPATIAL = "flac_spatial"
    PCM = "pcm"


class HRTFProfile(Enum):
    """Head-Related Transfer Function profiles"""
    GENERIC = "generic"
    KEMAR = "kemar"  # KEMAR dummy head
    CIPIC = "cipic"  # CIPIC database
    LISTEN = "listen"  # LISTEN database
    ARI = "ari"  # ARI database
    CUSTOM = "custom"


class RoomAcoustics(Enum):
    """Room acoustic presets"""
    ANECHOIC = "anechoic"  # No reflections
    STUDIO = "studio"
    LIVING_ROOM = "living_room"
    CONCERT_HALL = "concert_hall"
    CATHEDRAL = "cathedral"
    OUTDOOR = "outdoor"
    CUSTOM = "custom"


class SpatialAudioService:
    """Service for processing spatial and 3D audio"""
    
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"
        self.ffprobe_path = "ffprobe"
        self.sofa_conv_path = "sofa-conv"  # For HRTF processing
        
        # Channel layouts for different formats
        self.channel_layouts = {
            SpatialAudioFormat.STEREO: "stereo",
            SpatialAudioFormat.SURROUND_51: "5.1",
            SpatialAudioFormat.SURROUND_71: "7.1",
            SpatialAudioFormat.SURROUND_714: "7.1.4",
            SpatialAudioFormat.AMBISONIC_FOA: "4.0",
            SpatialAudioFormat.BINAURAL: "stereo"
        }
        
        # Ambisonic channel counts
        self.ambisonic_channels = {
            AmbisonicOrder.FIRST: 4,
            AmbisonicOrder.SECOND: 9,
            AmbisonicOrder.THIRD: 16,
            AmbisonicOrder.FOURTH: 25,
            AmbisonicOrder.FIFTH: 36
        }
        
        # Room acoustic parameters
        self.room_presets = {
            RoomAcoustics.ANECHOIC: {
                "reverb_level": 0,
                "room_size": 0,
                "damping": 1.0,
                "early_reflection": 0
            },
            RoomAcoustics.STUDIO: {
                "reverb_level": 0.1,
                "room_size": 0.3,
                "damping": 0.8,
                "early_reflection": 0.05
            },
            RoomAcoustics.LIVING_ROOM: {
                "reverb_level": 0.2,
                "room_size": 0.4,
                "damping": 0.6,
                "early_reflection": 0.1
            },
            RoomAcoustics.CONCERT_HALL: {
                "reverb_level": 0.4,
                "room_size": 0.8,
                "damping": 0.4,
                "early_reflection": 0.2
            },
            RoomAcoustics.CATHEDRAL: {
                "reverb_level": 0.6,
                "room_size": 1.0,
                "damping": 0.2,
                "early_reflection": 0.3
            }
        }
    
    async def analyze_spatial_audio(self, input_path: str) -> Dict[str, Any]:
        """
        Analyze audio file for spatial characteristics
        
        Args:
            input_path: Path to audio file
            
        Returns:
            Analysis results with spatial audio properties
        """
        try:
            # Get basic audio info
            audio_info = await self._get_audio_info(input_path)
            
            # Detect spatial format
            spatial_format = await self._detect_spatial_format(audio_info)
            
            # Analyze channel configuration
            channel_config = await self._analyze_channel_configuration(audio_info)
            
            # Check for object-based metadata
            object_metadata = await self._extract_object_metadata(input_path)
            
            # Analyze spatial characteristics
            spatial_analysis = await self._analyze_spatial_characteristics(
                input_path, audio_info["channels"]
            )
            
            return {
                "format": spatial_format.value,
                "channels": audio_info["channels"],
                "channel_layout": audio_info.get("channel_layout", "unknown"),
                "sample_rate": audio_info["sample_rate"],
                "bit_depth": audio_info.get("bit_depth", 16),
                "duration": audio_info["duration"],
                "channel_configuration": channel_config,
                "has_object_metadata": object_metadata is not None,
                "object_metadata": object_metadata,
                "spatial_analysis": spatial_analysis
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze spatial audio: {e}")
            raise ProxyGenerationError(
                "SPATIAL_AUDIO_ANALYSIS_FAILED",
                f"Failed to analyze spatial audio: {str(e)}"
            )
    
    async def convert_to_spatial_format(
        self,
        input_path: str,
        output_path: str,
        target_format: SpatialAudioFormat,
        codec: Optional[SpatialCodec] = None,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert audio to spatial format
        
        Args:
            input_path: Path to input audio
            output_path: Path for output audio
            target_format: Target spatial format
            codec: Optional spatial codec
            custom_params: Custom conversion parameters
            
        Returns:
            Conversion results
        """
        try:
            # Determine codec if not specified
            if not codec:
                codec = self._get_default_codec(target_format)
            
            # Build conversion command
            cmd = await self._build_spatial_conversion_command(
                input_path, output_path, target_format, codec, custom_params
            )
            
            # Execute conversion
            start_time = datetime.utcnow()
            await self._execute_ffmpeg_command(cmd)
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Verify output
            output_info = await self._get_audio_info(output_path)
            
            return {
                "target_format": target_format.value,
                "codec": codec.value,
                "output_channels": output_info["channels"],
                "output_layout": output_info.get("channel_layout", ""),
                "sample_rate": output_info["sample_rate"],
                "processing_time": processing_time,
                "file_size": os.path.getsize(output_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to convert to spatial format: {e}")
            raise ProxyGenerationError(
                "SPATIAL_FORMAT_CONVERSION_FAILED",
                f"Failed to convert to spatial format: {str(e)}"
            )
    
    async def encode_ambisonic(
        self,
        input_path: str,
        output_path: str,
        order: AmbisonicOrder = AmbisonicOrder.FIRST,
        normalize: bool = True
    ) -> Dict[str, Any]:
        """
        Encode audio to Ambisonic format
        
        Args:
            input_path: Path to input audio
            output_path: Path for Ambisonic output
            order: Ambisonic order (1-5)
            normalize: Whether to normalize output
            
        Returns:
            Encoding results
        """
        try:
            channels = self.ambisonic_channels[order]
            
            # Build Ambisonic encoding command
            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-af", f"pan={channels}c|"
            ]
            
            # Create channel mapping based on order
            if order == AmbisonicOrder.FIRST:
                # W, X, Y, Z channels
                cmd[-1] += "c0=c0|c1=c1|c2=c0|c3=c1"  # Simple stereo to FOA
            else:
                # Higher order requires more complex mapping
                cmd[-1] += self._generate_hoa_mapping(order)
            
            if normalize:
                cmd.extend(["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"])
            
            cmd.extend([
                "-c:a", "pcm_s24le",  # High quality PCM
                "-y", output_path
            ])
            
            # Execute encoding
            await self._execute_ffmpeg_command(cmd)
            
            # Add Ambisonic metadata
            await self._add_ambisonic_metadata(output_path, order)
            
            return {
                "ambisonic_order": order.value,
                "channels": channels,
                "normalized": normalize,
                "file_size": os.path.getsize(output_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to encode Ambisonic: {e}")
            raise ProxyGenerationError(
                "AMBISONIC_ENCODING_FAILED",
                f"Failed to encode Ambisonic: {str(e)}"
            )
    
    async def decode_ambisonic_to_binaural(
        self,
        input_path: str,
        output_path: str,
        hrtf_profile: HRTFProfile = HRTFProfile.GENERIC,
        head_tracking: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Decode Ambisonic to binaural using HRTF
        
        Args:
            input_path: Path to Ambisonic audio
            output_path: Path for binaural output
            hrtf_profile: HRTF profile to use
            head_tracking: Optional head tracking data (yaw, pitch, roll)
            
        Returns:
            Decoding results
        """
        try:
            # Build binaural decoding command
            filters = []
            
            # Apply head tracking if provided
            if head_tracking:
                rotation_filter = self._build_rotation_filter(head_tracking)
                filters.append(rotation_filter)
            
            # Apply HRTF convolution
            hrtf_filter = self._build_hrtf_filter(hrtf_profile)
            filters.append(hrtf_filter)
            
            # Build complete command
            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-af", ",".join(filters),
                "-ac", "2",  # Binaural is stereo
                "-c:a", "aac",
                "-b:a", "256k",
                "-y", output_path
            ]
            
            # Execute decoding
            await self._execute_ffmpeg_command(cmd)
            
            return {
                "hrtf_profile": hrtf_profile.value,
                "head_tracking_applied": head_tracking is not None,
                "output_format": "binaural",
                "file_size": os.path.getsize(output_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to decode Ambisonic to binaural: {e}")
            raise ProxyGenerationError(
                "BINAURAL_DECODING_FAILED",
                f"Failed to decode Ambisonic to binaural: {str(e)}"
            )
    
    async def apply_room_acoustics(
        self,
        input_path: str,
        output_path: str,
        room_preset: RoomAcoustics = RoomAcoustics.STUDIO,
        custom_params: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Apply room acoustics simulation
        
        Args:
            input_path: Path to input audio
            output_path: Path for processed output
            room_preset: Room acoustic preset
            custom_params: Custom room parameters
            
        Returns:
            Processing results
        """
        try:
            # Get room parameters
            if room_preset == RoomAcoustics.CUSTOM and custom_params:
                params = custom_params
            else:
                params = self.room_presets[room_preset]
            
            # Build reverb filter
            reverb_filter = (
                f"aecho=0.8:0.9:{params['early_reflection']*1000}:0.3,"
                f"reverb={params['reverb_level']*100}:"
                f"{params['room_size']*100}:"
                f"{params['damping']*100}:"
                f"{params.get('wet_gain', 0)}:"
                f"{params.get('dry_gain', -2)}"
            )
            
            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-af", reverb_filter,
                "-c:a", "aac",
                "-b:a", "320k",
                "-y", output_path
            ]
            
            # Execute processing
            await self._execute_ffmpeg_command(cmd)
            
            return {
                "room_preset": room_preset.value,
                "reverb_level": params["reverb_level"],
                "room_size": params["room_size"],
                "damping": params["damping"],
                "file_size": os.path.getsize(output_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to apply room acoustics: {e}")
            raise ProxyGenerationError(
                "ROOM_ACOUSTICS_FAILED",
                f"Failed to apply room acoustics: {str(e)}"
            )
    
    async def create_spatial_mix(
        self,
        input_files: List[Dict[str, Any]],
        output_path: str,
        output_format: SpatialAudioFormat = SpatialAudioFormat.SURROUND_51
    ) -> Dict[str, Any]:
        """
        Create spatial mix from multiple audio sources
        
        Args:
            input_files: List of input files with position data
                Each dict should have: path, azimuth, elevation, distance
            output_path: Path for mixed output
            output_format: Output spatial format
            
        Returns:
            Mixing results
        """
        try:
            # Build complex filter graph for spatial mixing
            filter_complex = []
            inputs = []
            
            for i, source in enumerate(input_files):
                inputs.extend(["-i", source["path"]])
                
                # Calculate panning based on position
                pan_filter = self._calculate_spatial_panning(
                    source.get("azimuth", 0),
                    source.get("elevation", 0),
                    source.get("distance", 1),
                    output_format
                )
                
                filter_complex.append(f"[{i}:a]{pan_filter}[a{i}]")
            
            # Mix all sources
            mix_inputs = "".join(f"[a{i}]" for i in range(len(input_files)))
            filter_complex.append(
                f"{mix_inputs}amix=inputs={len(input_files)}:duration=longest[out]"
            )
            
            # Build command
            cmd = [self.ffmpeg_path]
            cmd.extend(inputs)
            cmd.extend([
                "-filter_complex", ";".join(filter_complex),
                "-map", "[out]",
                "-c:a", "aac",
                "-b:a", "448k",
                "-y", output_path
            ])
            
            # Execute mixing
            await self._execute_ffmpeg_command(cmd)
            
            return {
                "sources_count": len(input_files),
                "output_format": output_format.value,
                "file_size": os.path.getsize(output_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to create spatial mix: {e}")
            raise ProxyGenerationError(
                "SPATIAL_MIX_FAILED",
                f"Failed to create spatial mix: {str(e)}"
            )
    
    async def extract_spatial_objects(
        self,
        input_path: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Extract individual objects from object-based audio
        
        Args:
            input_path: Path to object-based audio (e.g., Atmos)
            output_dir: Directory for extracted objects
            
        Returns:
            Extraction results
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Analyze input for object tracks
            audio_info = await self._get_audio_info(input_path)
            
            extracted_objects = []
            
            # Extract bed channels (base surround mix)
            bed_output = os.path.join(output_dir, "bed_channels.wav")
            bed_cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-map", "0:a:0",  # Main audio stream
                "-c:a", "pcm_s24le",
                "-y", bed_output
            ]
            
            await self._execute_ffmpeg_command(bed_cmd)
            extracted_objects.append({
                "type": "bed",
                "path": bed_output,
                "channels": audio_info["channels"]
            })
            
            # Extract object tracks if present
            # This is simplified - real Atmos extraction requires specialized tools
            for i in range(1, min(audio_info.get("streams", 1), 10)):
                object_output = os.path.join(output_dir, f"object_{i}.wav")
                object_cmd = [
                    self.ffmpeg_path,
                    "-i", input_path,
                    "-map", f"0:a:{i}",
                    "-c:a", "pcm_s24le",
                    "-y", object_output
                ]
                
                try:
                    await self._execute_ffmpeg_command(object_cmd)
                    extracted_objects.append({
                        "type": "object",
                        "index": i,
                        "path": object_output
                    })
                except:
                    break  # No more object tracks
            
            return {
                "extracted_count": len(extracted_objects),
                "objects": extracted_objects,
                "output_directory": output_dir
            }
            
        except Exception as e:
            logger.error(f"Failed to extract spatial objects: {e}")
            raise ProxyGenerationError(
                "SPATIAL_OBJECT_EXTRACTION_FAILED",
                f"Failed to extract spatial objects: {str(e)}"
            )
    
    async def create_immersive_preview(
        self,
        input_path: str,
        output_path: str,
        preview_type: str = "rotating",
        duration: int = 60
    ) -> Dict[str, Any]:
        """
        Create immersive audio preview with movement
        
        Args:
            input_path: Path to spatial audio
            output_path: Path for preview output
            preview_type: Type of preview (rotating, flythrough, static)
            duration: Preview duration in seconds
            
        Returns:
            Preview creation results
        """
        try:
            if preview_type == "rotating":
                # Create rotating soundfield preview
                filter_chain = []
                
                # Generate rotation over time
                for t in range(0, duration, 5):
                    angle = (t / duration) * 360
                    filter_chain.append(
                        f"[0:a]aeval=val(0)*cos({angle}*PI/180)"
                        f"|val(1)*sin({angle}*PI/180)[a{t}]"
                    )
                
                # Concatenate segments
                concat_filter = "".join(f"[a{t}]" for t in range(0, duration, 5))
                filter_chain.append(f"{concat_filter}concat=n={duration//5}:v=0:a=1[out]")
                
            elif preview_type == "flythrough":
                # Create movement through space
                filter_chain = [
                    "[0:a]apulsator=hz=0.1:amount=0.5[mod]",
                    "[mod]aphaser=in_gain=0.4:out_gain=0.74:delay=2:decay=0.4[out]"
                ]
                
            else:  # static
                filter_chain = ["[0:a]anull[out]"]
            
            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-t", str(duration),
                "-filter_complex", ";".join(filter_chain),
                "-map", "[out]",
                "-c:a", "aac",
                "-b:a", "256k",
                "-y", output_path
            ]
            
            await self._execute_ffmpeg_command(cmd)
            
            return {
                "preview_type": preview_type,
                "duration": duration,
                "file_size": os.path.getsize(output_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to create immersive preview: {e}")
            raise ProxyGenerationError(
                "IMMERSIVE_PREVIEW_FAILED",
                f"Failed to create immersive preview: {str(e)}"
            )
    
    async def analyze_soundfield(
        self,
        input_path: str
    ) -> Dict[str, Any]:
        """
        Analyze spatial soundfield characteristics
        
        Args:
            input_path: Path to spatial audio
            
        Returns:
            Soundfield analysis results
        """
        try:
            # Get audio data for analysis
            audio_info = await self._get_audio_info(input_path)
            
            # Analyze energy distribution
            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-af", "astats=metadata=1:reset=1",
                "-f", "null",
                "-"
            ]
            
            # Execute analysis
            result = await self._execute_command(cmd)
            
            # Parse statistics
            stats = self._parse_audio_stats(result)
            
            # Calculate spatial metrics
            spatial_metrics = {
                "channel_balance": self._calculate_channel_balance(stats),
                "spatial_width": self._calculate_spatial_width(stats),
                "surround_coherence": self._calculate_surround_coherence(stats),
                "height_activity": self._calculate_height_activity(stats, audio_info)
            }
            
            return {
                "format": audio_info.get("channel_layout", "unknown"),
                "channels": audio_info["channels"],
                "spatial_metrics": spatial_metrics,
                "channel_statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze soundfield: {e}")
            raise ProxyGenerationError(
                "SOUNDFIELD_ANALYSIS_FAILED",
                f"Failed to analyze soundfield: {str(e)}"
            )
    
    async def _detect_spatial_format(self, audio_info: Dict[str, Any]) -> SpatialAudioFormat:
        """Detect spatial audio format from audio info"""
        channels = audio_info.get("channels", 2)
        layout = audio_info.get("channel_layout", "").lower()
        
        if channels == 2:
            return SpatialAudioFormat.STEREO
        elif channels == 6 and "5.1" in layout:
            return SpatialAudioFormat.SURROUND_51
        elif channels == 8 and "7.1" in layout:
            return SpatialAudioFormat.SURROUND_71
        elif channels >= 12 and "atmos" in layout:
            return SpatialAudioFormat.SURROUND_714
        elif channels in [4, 9, 16, 25, 36]:
            # Likely Ambisonic
            if channels == 4:
                return SpatialAudioFormat.AMBISONIC_FOA
            else:
                return SpatialAudioFormat.AMBISONIC_HOA
        
        return SpatialAudioFormat.STEREO  # Default
    
    async def _analyze_channel_configuration(self, audio_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze channel configuration"""
        channels = audio_info.get("channels", 2)
        layout = audio_info.get("channel_layout", "")
        
        # Standard configurations
        configs = {
            "stereo": ["L", "R"],
            "5.1": ["L", "R", "C", "LFE", "Ls", "Rs"],
            "7.1": ["L", "R", "C", "LFE", "Ls", "Rs", "Lrs", "Rrs"],
            "7.1.4": ["L", "R", "C", "LFE", "Ls", "Rs", "Lrs", "Rrs", 
                      "Ltf", "Rtf", "Ltr", "Rtr"]
        }
        
        # Try to match configuration
        for config_name, config_channels in configs.items():
            if len(config_channels) == channels or config_name in layout.lower():
                return {
                    "configuration": config_name,
                    "channels": config_channels,
                    "has_lfe": "LFE" in config_channels,
                    "has_height": any("tf" in ch or "tr" in ch for ch in config_channels)
                }
        
        return {
            "configuration": "custom",
            "channel_count": channels,
            "layout_string": layout
        }
    
    async def _extract_object_metadata(self, input_path: str) -> Optional[Dict[str, Any]]:
        """Extract object-based audio metadata"""
        try:
            # This is simplified - real implementation would parse Atmos metadata
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-show_format",
                input_path
            ]
            
            result = await self._execute_command(cmd)
            probe_data = json.loads(result)
            
            # Look for object metadata in format tags
            format_tags = probe_data.get("format", {}).get("tags", {})
            
            if any("atmos" in k.lower() or "object" in k.lower() for k in format_tags):
                return {
                    "format": "dolby_atmos",
                    "objects_present": True,
                    "metadata": format_tags
                }
            
            return None
            
        except Exception:
            return None
    
    async def _analyze_spatial_characteristics(
        self,
        input_path: str,
        channels: int
    ) -> Dict[str, Any]:
        """Analyze spatial characteristics of audio"""
        try:
            # Use FFmpeg to get detailed channel statistics
            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-af", "astats=metadata=0",
                "-f", "null",
                "-"
            ]
            
            result = await self._execute_command(cmd)
            
            # Parse output for spatial metrics
            return {
                "channels_active": channels,
                "spatial_complexity": "medium",  # Would be calculated from actual analysis
                "dynamic_range": "normal",
                "movement_detected": False
            }
            
        except Exception as e:
            logger.warning(f"Could not analyze spatial characteristics: {e}")
            return {}
    
    async def _build_spatial_conversion_command(
        self,
        input_path: str,
        output_path: str,
        target_format: SpatialAudioFormat,
        codec: SpatialCodec,
        custom_params: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Build FFmpeg command for spatial format conversion"""
        cmd = [self.ffmpeg_path, "-i", input_path]
        
        # Channel layout conversion
        if target_format in self.channel_layouts:
            layout = self.channel_layouts[target_format]
            cmd.extend(["-channel_layout", layout])
        
        # Codec-specific parameters
        if codec == SpatialCodec.EAC3_ATMOS:
            cmd.extend([
                "-c:a", "eac3",
                "-b:a", "640k",
                "-dialnorm", "-31"
            ])
        elif codec == SpatialCodec.OPUS_SPATIAL:
            cmd.extend([
                "-c:a", "libopus",
                "-b:a", "256k",
                "-vbr", "on",
                "-mapping_family", "1"  # Ambisonic mapping
            ])
        elif codec == SpatialCodec.FLAC_SPATIAL:
            cmd.extend([
                "-c:a", "flac",
                "-compression_level", "8"
            ])
        else:
            cmd.extend(["-c:a", "aac", "-b:a", "320k"])
        
        # Apply custom parameters
        if custom_params:
            for key, value in custom_params.items():
                cmd.extend([f"-{key}", str(value)])
        
        cmd.extend(["-y", output_path])
        
        return cmd
    
    def _get_default_codec(self, format: SpatialAudioFormat) -> SpatialCodec:
        """Get default codec for spatial format"""
        codec_map = {
            SpatialAudioFormat.STEREO: SpatialCodec.AAC_SPATIAL,
            SpatialAudioFormat.SURROUND_51: SpatialCodec.AAC_SPATIAL,
            SpatialAudioFormat.SURROUND_71: SpatialCodec.EAC3_ATMOS,
            SpatialAudioFormat.SURROUND_714: SpatialCodec.EAC3_ATMOS,
            SpatialAudioFormat.AMBISONIC_FOA: SpatialCodec.OPUS_SPATIAL,
            SpatialAudioFormat.AMBISONIC_HOA: SpatialCodec.OPUS_SPATIAL,
            SpatialAudioFormat.BINAURAL: SpatialCodec.AAC_SPATIAL
        }
        return codec_map.get(format, SpatialCodec.AAC_SPATIAL)
    
    def _generate_hoa_mapping(self, order: AmbisonicOrder) -> str:
        """Generate Higher Order Ambisonic channel mapping"""
        # Simplified HOA mapping - real implementation would be more complex
        channels = self.ambisonic_channels[order]
        mapping = []
        
        for i in range(channels):
            # Simple mapping from stereo to HOA channels
            if i < 2:
                mapping.append(f"c{i}=c{i}")
            else:
                # Decorrelate and distribute to higher order channels
                mapping.append(f"c{i}=0.5*c0+0.5*c1")
        
        return "|".join(mapping)
    
    async def _add_ambisonic_metadata(self, file_path: str, order: AmbisonicOrder) -> None:
        """Add Ambisonic metadata to file"""
        try:
            # Add metadata tags for Ambisonic identification
            metadata_cmd = [
                self.ffmpeg_path,
                "-i", file_path,
                "-c", "copy",
                "-metadata", f"ambisonic_order={order.value}",
                "-metadata", "ambisonic_type=periphonic",
                "-metadata", "ambisonic_norm=SN3D",
                "-metadata", "ambisonic_channel_order=ACN",
                "-y", file_path + ".tmp"
            ]
            
            await self._execute_ffmpeg_command(metadata_cmd)
            
            # Replace original file
            os.replace(file_path + ".tmp", file_path)
            
        except Exception as e:
            logger.warning(f"Could not add Ambisonic metadata: {e}")
    
    def _build_rotation_filter(self, head_tracking: Dict[str, float]) -> str:
        """Build rotation filter for head tracking"""
        yaw = head_tracking.get("yaw", 0)
        pitch = head_tracking.get("pitch", 0)
        roll = head_tracking.get("roll", 0)
        
        # Simplified rotation - real implementation would use proper ambisonic rotation
        return f"aeval=val(0)*cos({yaw}*PI/180)|val(1)*sin({yaw}*PI/180)"
    
    def _build_hrtf_filter(self, profile: HRTFProfile) -> str:
        """Build HRTF filter for binaural rendering"""
        # Simplified HRTF - real implementation would use SOFA files
        if profile == HRTFProfile.GENERIC:
            return "earwax"  # FFmpeg's built-in HRTF filter
        else:
            # Would load and apply specific HRTF dataset
            return "earwax"
    
    def _calculate_spatial_panning(
        self,
        azimuth: float,
        elevation: float,
        distance: float,
        format: SpatialAudioFormat
    ) -> str:
        """Calculate panning for spatial positioning"""
        # Convert spherical coordinates to channel gains
        if format == SpatialAudioFormat.STEREO:
            # Simple stereo panning
            left_gain = (1 + math.cos(math.radians(azimuth))) / 2
            right_gain = (1 - math.cos(math.radians(azimuth))) / 2
            
            # Apply distance attenuation
            attenuation = 1 / max(distance, 0.1)
            
            return f"pan=stereo|c0={left_gain*attenuation}*c0|c1={right_gain*attenuation}*c0"
        
        elif format == SpatialAudioFormat.SURROUND_51:
            # 5.1 panning - simplified
            return "pan=5.1|c0=c0|c1=c0|c2=c0|c3=0|c4=c0|c5=c0"
        
        # Add more format support as needed
        return "anull"
    
    def _parse_audio_stats(self, stats_output: str) -> Dict[str, Any]:
        """Parse audio statistics from FFmpeg output"""
        stats = {}
        
        # Parse channel statistics
        lines = stats_output.split('\n')
        for line in lines:
            if "RMS level" in line:
                parts = line.split()
                if len(parts) >= 4:
                    channel = parts[1].strip(':')
                    value = float(parts[3])
                    stats[f"rms_{channel}"] = value
        
        return stats
    
    def _calculate_channel_balance(self, stats: Dict[str, Any]) -> float:
        """Calculate channel balance metric"""
        # Simplified balance calculation
        left_rms = stats.get("rms_L", 0)
        right_rms = stats.get("rms_R", 0)
        
        if left_rms + right_rms > 0:
            balance = abs(left_rms - right_rms) / (left_rms + right_rms)
            return 1.0 - balance  # 1.0 = perfect balance
        
        return 0.5
    
    def _calculate_spatial_width(self, stats: Dict[str, Any]) -> float:
        """Calculate spatial width metric"""
        # Simplified width calculation based on surround activity
        surround_channels = ["rms_Ls", "rms_Rs", "rms_Lrs", "rms_Rrs"]
        surround_energy = sum(stats.get(ch, 0) for ch in surround_channels)
        front_energy = stats.get("rms_L", 0) + stats.get("rms_R", 0)
        
        if front_energy > 0:
            return min(surround_energy / front_energy, 1.0)
        
        return 0.0
    
    def _calculate_surround_coherence(self, stats: Dict[str, Any]) -> float:
        """Calculate surround coherence metric"""
        # Simplified coherence - would use correlation in real implementation
        return 0.7  # Placeholder
    
    def _calculate_height_activity(
        self,
        stats: Dict[str, Any],
        audio_info: Dict[str, Any]
    ) -> float:
        """Calculate height channel activity"""
        # Check for height channels
        height_channels = ["rms_Ltf", "rms_Rtf", "rms_Ltr", "rms_Rtr"]
        height_energy = sum(stats.get(ch, 0) for ch in height_channels)
        
        if height_energy > 0:
            total_energy = sum(v for k, v in stats.items() if k.startswith("rms_"))
            return height_energy / max(total_energy, 0.001)
        
        return 0.0
    
    async def _get_audio_info(self, file_path: str) -> Dict[str, Any]:
        """Get audio file information"""
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            file_path
        ]
        
        result = await self._execute_command(cmd)
        probe_data = json.loads(result)
        
        # Extract audio stream info
        audio_stream = next(
            (s for s in probe_data.get("streams", []) if s["codec_type"] == "audio"),
            {}
        )
        
        format_info = probe_data.get("format", {})
        
        return {
            "channels": audio_stream.get("channels", 2),
            "channel_layout": audio_stream.get("channel_layout", ""),
            "sample_rate": int(audio_stream.get("sample_rate", 48000)),
            "bit_depth": audio_stream.get("bits_per_sample", 16),
            "duration": float(format_info.get("duration", 0)),
            "bitrate": int(format_info.get("bit_rate", 0)),
            "codec": audio_stream.get("codec_name", ""),
            "streams": len(probe_data.get("streams", []))
        }
    
    async def _execute_command(self, cmd: List[str]) -> str:
        """Execute command and return output"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Command failed: {stderr.decode()}")
        
        return stdout.decode()
    
    async def _execute_ffmpeg_command(self, cmd: List[str]) -> None:
        """Execute FFmpeg command"""
        logger.info(f"Executing FFmpeg command: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode()
            logger.error(f"FFmpeg command failed: {error_msg}")
            raise RuntimeError(f"FFmpeg failed: {error_msg}")
        
        logger.info("FFmpeg command completed successfully")
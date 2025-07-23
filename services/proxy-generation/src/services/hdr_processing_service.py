"""
HDR Processing Service for Advanced High Dynamic Range Video Processing
"""

import os
import asyncio
import json
import tempfile
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
from enum import Enum
import platform
import math
from datetime import datetime

from ..core.config import settings
from ..core.exceptions import FFmpegError, InvalidMediaError, ProcessingTimeoutError
from ..core.logging import get_logger
from .ffmpeg_service import FFmpegService

logger = get_logger(__name__)


class HDRStandard(str, Enum):
    """HDR standards and formats"""
    HDR10 = "hdr10"
    HDR10_PLUS = "hdr10_plus"
    DOLBY_VISION = "dolby_vision"
    HLG = "hlg"  # Hybrid Log-Gamma


class ColorSpace(str, Enum):
    """Color spaces for HDR processing"""
    BT2020 = "bt2020nc"
    BT709 = "bt709"
    BT601 = "bt601"
    DCI_P3 = "dci-p3"


class TransferFunction(str, Enum):
    """Transfer functions for HDR"""
    PQ = "smpte2084"  # Perceptual Quantizer (HDR10)
    HLG = "arib-std-b67"  # Hybrid Log-Gamma
    BT709 = "bt709"  # Standard Dynamic Range
    GAMMA22 = "gamma22"
    GAMMA28 = "gamma28"


class ToneMappingAlgorithm(str, Enum):
    """Tone mapping algorithms"""
    NONE = "none"
    HABLE = "hable"
    REINHARD = "reinhard"
    MOBIUS = "mobius"
    CLIP = "clip"
    LINEAR = "linear"
    GAMMA = "gamma"


class HDRMetadata:
    """HDR metadata management"""
    
    @staticmethod
    def create_hdr10_metadata(
        max_cll: int = 1000,  # Maximum Content Light Level (nits)
        max_fall: int = 400,  # Maximum Frame Average Light Level (nits)
        master_display_primaries: Optional[str] = None,
        master_display_white_point: Optional[str] = None,
        master_display_luminance: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create HDR10 metadata"""
        
        # Default Rec. 2020 primaries if not specified
        if not master_display_primaries:
            master_display_primaries = "G(13250,34500)B(7500,3000)R(34000,16000)"
        
        if not master_display_white_point:
            master_display_white_point = "WP(15635,16450)"
        
        if not master_display_luminance:
            master_display_luminance = f"L({max_cll},{max_fall})"
        
        return {
            "max_cll": max_cll,
            "max_fall": max_fall,
            "master_display_primaries": master_display_primaries,
            "master_display_white_point": master_display_white_point,
            "master_display_luminance": master_display_luminance,
            "master_display": f"{master_display_primaries}{master_display_white_point}{master_display_luminance}"
        }
    
    @staticmethod
    def create_hlg_metadata(
        system_gamma: float = 1.2
    ) -> Dict[str, Any]:
        """Create HLG (Hybrid Log-Gamma) metadata"""
        return {
            "system_gamma": system_gamma,
            "transfer_characteristics": "arib-std-b67"
        }


class HDRProcessingService:
    """Service for advanced HDR video processing"""
    
    def __init__(self, ffmpeg_service: FFmpegService):
        self.ffmpeg_service = ffmpeg_service
        self.supported_standards = [HDRStandard.HDR10, HDRStandard.HLG]
        
        # Check for advanced HDR support in FFmpeg
        self.dolby_vision_support = self._check_dolby_vision_support()
        self.hdr10_plus_support = self._check_hdr10_plus_support()
        
        if self.dolby_vision_support:
            self.supported_standards.append(HDRStandard.DOLBY_VISION)
        if self.hdr10_plus_support:
            self.supported_standards.append(HDRStandard.HDR10_PLUS)
        
        logger.info(
            "hdr_processing_service_initialized",
            supported_standards=[s.value for s in self.supported_standards],
            dolby_vision_support=self.dolby_vision_support,
            hdr10_plus_support=self.hdr10_plus_support
        )
    
    def _check_dolby_vision_support(self) -> bool:
        """Check if Dolby Vision processing is supported"""
        try:
            # This would typically check for libdovi or x265 Dolby Vision support
            # For now, we'll assume it's not supported unless explicitly configured
            return False
        except Exception:
            return False
    
    def _check_hdr10_plus_support(self) -> bool:
        """Check if HDR10+ processing is supported"""
        try:
            # This would check for HDR10+ metadata processing support
            return False
        except Exception:
            return False
    
    async def analyze_hdr_content(self, input_path: str) -> Dict[str, Any]:
        """Analyze HDR characteristics of input video"""
        try:
            # Get detailed media info
            cmd = [
                self.ffmpeg_service.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                "-show_frames",
                "-select_streams", "v:0",
                "-read_intervals", "%+#1",  # Read first frame only
                input_path
            ]
            
            result = await self.ffmpeg_service.run_ffmpeg_command(cmd)
            probe_data = json.loads(result.stdout)
            
            # Find video stream
            video_stream = None
            for stream in probe_data.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_stream = stream
                    break
            
            if not video_stream:
                raise InvalidMediaError("No video stream found")
            
            # Analyze HDR characteristics
            analysis = {
                "is_hdr": False,
                "hdr_standard": None,
                "color_space": video_stream.get("color_space"),
                "color_primaries": video_stream.get("color_primaries"),
                "color_transfer": video_stream.get("color_trc"),
                "color_range": video_stream.get("color_range"),
                "bit_depth": self._extract_bit_depth(video_stream),
                "peak_luminance": None,
                "max_cll": None,
                "max_fall": None,
                "master_display": None,
                "recommendations": []
            }
            
            # Determine if content is HDR
            color_transfer = analysis["color_transfer"]
            color_primaries = analysis["color_primaries"]
            
            if color_transfer in ["smpte2084", "arib-std-b67"]:
                analysis["is_hdr"] = True
                
                if color_transfer == "smpte2084":
                    analysis["hdr_standard"] = HDRStandard.HDR10
                elif color_transfer == "arib-std-b67":
                    analysis["hdr_standard"] = HDRStandard.HLG
            
            # Extract HDR metadata if available
            if analysis["is_hdr"]:
                hdr_metadata = await self._extract_hdr_metadata(input_path)
                analysis.update(hdr_metadata)
            
            # Generate recommendations
            analysis["recommendations"] = self._generate_hdr_recommendations(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error("hdr_analysis_failed", error=str(e), input_path=input_path)
            raise
    
    def _extract_bit_depth(self, video_stream: Dict) -> Optional[int]:
        """Extract bit depth from video stream info"""
        pix_fmt = video_stream.get("pix_fmt", "")
        
        # Common HDR pixel formats
        if "10le" in pix_fmt or "10be" in pix_fmt:
            return 10
        elif "12le" in pix_fmt or "12be" in pix_fmt:
            return 12
        elif "16le" in pix_fmt or "16be" in pix_fmt:
            return 16
        else:
            return 8
    
    async def _extract_hdr_metadata(self, input_path: str) -> Dict[str, Any]:
        """Extract HDR metadata from video file"""
        metadata = {
            "peak_luminance": None,
            "max_cll": None,
            "max_fall": None,
            "master_display": None
        }
        
        try:
            # Use ffprobe to extract HDR metadata
            cmd = [
                self.ffmpeg_service.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_frames",
                "-select_streams", "v:0",
                "-read_intervals", "%+#1",
                input_path
            ]
            
            result = await self.ffmpeg_service.run_ffmpeg_command(cmd)
            probe_data = json.loads(result.stdout)
            
            frames = probe_data.get("frames", [])
            if frames:
                frame = frames[0]
                side_data = frame.get("side_data_list", [])
                
                for data in side_data:
                    if data.get("side_data_type") == "Mastering display metadata":
                        metadata["master_display"] = data
                    elif data.get("side_data_type") == "Content light level metadata":
                        metadata["max_cll"] = data.get("max_content")
                        metadata["max_fall"] = data.get("max_average")
            
        except Exception as e:
            logger.warning("hdr_metadata_extraction_failed", error=str(e))
        
        return metadata
    
    def _generate_hdr_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate processing recommendations based on HDR analysis"""
        recommendations = []
        
        if not analysis["is_hdr"]:
            recommendations.append({
                "type": "info",
                "message": "Content is Standard Dynamic Range (SDR). Consider HDR upconversion if targeting HDR displays."
            })
            return recommendations
        
        # HDR content recommendations
        if analysis["hdr_standard"] == HDRStandard.HDR10:
            recommendations.extend([
                {
                    "type": "processing",
                    "message": "HDR10 content detected. Preserve HDR metadata for HDR displays."
                },
                {
                    "type": "compatibility", 
                    "message": "Create SDR version using tone mapping for SDR displays."
                },
                {
                    "type": "codec",
                    "message": "Use H.265 Main10 profile for optimal HDR compression."
                }
            ])
        
        elif analysis["hdr_standard"] == HDRStandard.HLG:
            recommendations.extend([
                {
                    "type": "processing",
                    "message": "HLG content detected. Backward compatible with SDR displays."
                },
                {
                    "type": "distribution",
                    "message": "HLG is ideal for broadcast distribution."
                }
            ])
        
        # Bit depth recommendations
        if analysis["bit_depth"] == 8:
            recommendations.append({
                "type": "warning",
                "message": "8-bit HDR content may show banding. Consider 10-bit processing."
            })
        
        return recommendations
    
    async def convert_hdr_to_sdr(
        self,
        input_path: str,
        output_path: str,
        tone_mapping: ToneMappingAlgorithm = ToneMappingAlgorithm.HABLE,
        target_nits: int = 100,
        preserve_colors: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Convert HDR content to SDR using tone mapping"""
        
        try:
            start_time = datetime.utcnow()
            
            # Analyze input
            hdr_analysis = await self.analyze_hdr_content(input_path)
            
            if not hdr_analysis["is_hdr"]:
                raise InvalidMediaError("Input is not HDR content")
            
            # Build FFmpeg command
            cmd = [self.ffmpeg_service.ffmpeg_path, "-i", input_path]
            
            # Add hardware acceleration if available
            if self.ffmpeg_service.enable_gpu:
                cmd.extend(self._get_gpu_args())
            
            # Build tone mapping filter chain
            filters = []
            
            if tone_mapping == ToneMappingAlgorithm.HABLE:
                filters.extend([
                    f"zscale=t=linear:npl={target_nits}",
                    "format=gbrpf32le",
                    "zscale=p=bt709:t=bt709:m=bt709:r=tv",
                    "format=yuv420p"
                ])
            
            elif tone_mapping == ToneMappingAlgorithm.REINHARD:
                filters.append(f"tonemap=tonemap=reinhard:param=0.5:desat=0")
                if preserve_colors:
                    filters.append("colorspace=bt709:iall=bt2020")
            
            elif tone_mapping == ToneMappingAlgorithm.MOBIUS:
                filters.append(f"tonemap=tonemap=mobius:param=0.3:desat=0")
                if preserve_colors:
                    filters.append("colorspace=bt709:iall=bt2020")
            
            elif tone_mapping == ToneMappingAlgorithm.CLIP:
                filters.extend([
                    f"zscale=npl={target_nits}",
                    "format=yuv420p"
                ])
            
            # Apply filters
            if filters:
                cmd.extend(["-vf", ",".join(filters)])
            
            # Output color space settings
            cmd.extend([
                "-colorspace", "bt709",
                "-color_primaries", "bt709", 
                "-color_trc", "bt709",
                "-color_range", "tv"
            ])
            
            # Codec settings
            codec = kwargs.get("codec", "libx264")
            cmd.extend(["-c:v", codec])
            
            if codec == "libx264":
                cmd.extend(["-profile:v", "high", "-level", "4.1"])
            elif codec == "libx265":
                cmd.extend(["-profile:v", "main"])
            
            # Quality settings
            crf = kwargs.get("crf", 23)
            cmd.extend(["-crf", str(crf)])
            
            # Audio settings
            cmd.extend(["-c:a", kwargs.get("audio_codec", "aac")])
            
            cmd.append(output_path)
            
            # Execute conversion
            await self.ffmpeg_service.run_ffmpeg_command(cmd)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Analyze output
            output_analysis = await self.analyze_hdr_content(output_path)
            
            return {
                "processing_time_seconds": processing_time,
                "tone_mapping_algorithm": tone_mapping.value,
                "target_nits": target_nits,
                "input_analysis": hdr_analysis,
                "output_analysis": output_analysis,
                "input_size_mb": os.path.getsize(input_path) / (1024 * 1024),
                "output_size_mb": os.path.getsize(output_path) / (1024 * 1024),
                "compression_ratio": os.path.getsize(input_path) / os.path.getsize(output_path)
            }
            
        except Exception as e:
            logger.error("hdr_to_sdr_conversion_failed", error=str(e))
            raise
    
    async def convert_sdr_to_hdr(
        self,
        input_path: str,
        output_path: str,
        target_standard: HDRStandard = HDRStandard.HDR10,
        peak_luminance: int = 1000,
        **kwargs
    ) -> Dict[str, Any]:
        """Convert SDR content to HDR (upconversion)"""
        
        try:
            start_time = datetime.utcnow()
            
            # Analyze input
            input_analysis = await self.analyze_hdr_content(input_path)
            
            if input_analysis["is_hdr"]:
                raise InvalidMediaError("Input is already HDR content")
            
            # Build FFmpeg command
            cmd = [self.ffmpeg_service.ffmpeg_path, "-i", input_path]
            
            # Add hardware acceleration if available
            if self.ffmpeg_service.enable_gpu:
                cmd.extend(self._get_gpu_args())
            
            # Build HDR upconversion filter chain
            filters = []
            
            if target_standard == HDRStandard.HDR10:
                # Convert to HDR10
                filters.extend([
                    "colorspace=bt2020:iall=bt709",
                    "format=yuv420p10le",
                    f"zscale=t=smpte2084:npl={peak_luminance}"
                ])
                
                # Output color space settings
                cmd.extend([
                    "-colorspace", "bt2020nc",
                    "-color_primaries", "bt2020",
                    "-color_trc", "smpte2084",
                    "-color_range", "tv"
                ])
                
            elif target_standard == HDRStandard.HLG:
                # Convert to HLG
                filters.extend([
                    "colorspace=bt2020:iall=bt709",
                    "format=yuv420p10le",
                    "zscale=t=arib-std-b67"
                ])
                
                # Output color space settings
                cmd.extend([
                    "-colorspace", "bt2020nc",
                    "-color_primaries", "bt2020",
                    "-color_trc", "arib-std-b67",
                    "-color_range", "tv"
                ])
            
            # Apply filters
            if filters:
                cmd.extend(["-vf", ",".join(filters)])
            
            # Codec settings - HDR requires 10-bit
            codec = kwargs.get("codec", "libx265")
            cmd.extend(["-c:v", codec])
            
            if codec == "libx265":
                cmd.extend([
                    "-profile:v", "main10",
                    "-tier", "high",
                    "-level", "5.1"
                ])
            
            # Add HDR metadata for HDR10
            if target_standard == HDRStandard.HDR10:
                hdr_metadata = HDRMetadata.create_hdr10_metadata(
                    max_cll=peak_luminance,
                    max_fall=int(peak_luminance * 0.4)
                )
                cmd.extend([
                    "-x265-params",
                    f"hdr-opt=1:repeat-headers=1:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:master-display={hdr_metadata['master_display']}:max-cll={hdr_metadata['max_cll']},{hdr_metadata['max_fall']}"
                ])
            
            # Quality settings
            crf = kwargs.get("crf", 20)  # Lower CRF for HDR
            cmd.extend(["-crf", str(crf)])
            
            # Audio settings
            cmd.extend(["-c:a", kwargs.get("audio_codec", "aac")])
            
            cmd.append(output_path)
            
            # Execute conversion
            await self.ffmpeg_service.run_ffmpeg_command(cmd)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Analyze output
            output_analysis = await self.analyze_hdr_content(output_path)
            
            return {
                "processing_time_seconds": processing_time,
                "target_standard": target_standard.value,
                "peak_luminance": peak_luminance,
                "input_analysis": input_analysis,
                "output_analysis": output_analysis,
                "input_size_mb": os.path.getsize(input_path) / (1024 * 1024),
                "output_size_mb": os.path.getsize(output_path) / (1024 * 1024),
                "compression_ratio": os.path.getsize(input_path) / os.path.getsize(output_path)
            }
            
        except Exception as e:
            logger.error("sdr_to_hdr_conversion_failed", error=str(e))
            raise
    
    async def optimize_hdr_delivery(
        self,
        input_path: str,
        output_dir: str,
        create_sdr_version: bool = True,
        create_mobile_version: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Create optimized HDR delivery versions"""
        
        try:
            results = {}
            base_name = Path(input_path).stem
            
            # Analyze input
            input_analysis = await self.analyze_hdr_content(input_path)
            
            if not input_analysis["is_hdr"]:
                raise InvalidMediaError("Input must be HDR content")
            
            # Create HDR master (optimized)
            hdr_master_path = os.path.join(output_dir, f"{base_name}_hdr_master.mp4")
            hdr_result = await self._create_hdr_master(input_path, hdr_master_path, **kwargs)
            results["hdr_master"] = {
                "path": hdr_master_path,
                "result": hdr_result
            }
            
            # Create SDR version if requested
            if create_sdr_version:
                sdr_path = os.path.join(output_dir, f"{base_name}_sdr.mp4")
                sdr_result = await self.convert_hdr_to_sdr(
                    input_path, sdr_path,
                    tone_mapping=ToneMappingAlgorithm.HABLE,
                    target_nits=100,
                    **kwargs
                )
                results["sdr_version"] = {
                    "path": sdr_path,
                    "result": sdr_result
                }
            
            # Create mobile-optimized version if requested
            if create_mobile_version:
                mobile_path = os.path.join(output_dir, f"{base_name}_mobile.mp4")
                mobile_result = await self.convert_hdr_to_sdr(
                    input_path, mobile_path,
                    tone_mapping=ToneMappingAlgorithm.MOBIUS,
                    target_nits=100,
                    codec="libx264",
                    crf=28,
                    **kwargs
                )
                results["mobile_version"] = {
                    "path": mobile_path,
                    "result": mobile_result
                }
            
            return {
                "input_analysis": input_analysis,
                "delivery_versions": results,
                "total_versions": len(results)
            }
            
        except Exception as e:
            logger.error("hdr_delivery_optimization_failed", error=str(e))
            raise
    
    async def _create_hdr_master(self, input_path: str, output_path: str, **kwargs) -> Dict[str, Any]:
        """Create optimized HDR master"""
        
        start_time = datetime.utcnow()
        
        cmd = [self.ffmpeg_service.ffmpeg_path, "-i", input_path]
        
        # Add hardware acceleration if available
        if self.ffmpeg_service.enable_gpu:
            cmd.extend(self._get_gpu_args())
        
        # Preserve HDR metadata and optimize
        cmd.extend([
            "-c:v", "libx265",
            "-profile:v", "main10",
            "-tier", "high",
            "-crf", str(kwargs.get("crf", 18)),
            "-preset", kwargs.get("preset", "slow"),
            "-c:a", kwargs.get("audio_codec", "aac"),
            "-map_metadata", "0",  # Preserve metadata
            output_path
        ])
        
        await self.ffmpeg_service.run_ffmpeg_command(cmd)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "processing_time_seconds": processing_time,
            "input_size_mb": os.path.getsize(input_path) / (1024 * 1024),
            "output_size_mb": os.path.getsize(output_path) / (1024 * 1024),
            "compression_ratio": os.path.getsize(input_path) / os.path.getsize(output_path)
        }
    
    def _get_gpu_args(self) -> List[str]:
        """Get GPU acceleration arguments for HDR processing"""
        if self.ffmpeg_service.gpu_type.value == "nvidia":
            return ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
        elif self.ffmpeg_service.gpu_type.value == "intel":
            return ["-hwaccel", "qsv"]
        elif self.ffmpeg_service.gpu_type.value == "amd":
            return ["-hwaccel", "d3d11va"]
        else:
            return []
    
    async def get_hdr_processing_capabilities(self) -> Dict[str, Any]:
        """Get HDR processing capabilities"""
        return {
            "supported_standards": [s.value for s in self.supported_standards],
            "tone_mapping_algorithms": [a.value for a in ToneMappingAlgorithm],
            "color_spaces": [c.value for c in ColorSpace],
            "transfer_functions": [t.value for t in TransferFunction],
            "dolby_vision_support": self.dolby_vision_support,
            "hdr10_plus_support": self.hdr10_plus_support,
            "gpu_acceleration": self.ffmpeg_service.enable_gpu,
            "supported_bit_depths": [8, 10, 12],
            "features": {
                "hdr_to_sdr_conversion": True,
                "sdr_to_hdr_upconversion": True,
                "metadata_preservation": True,
                "delivery_optimization": True,
                "content_analysis": True
            }
        }


# Service instance
_hdr_processing_service: Optional[HDRProcessingService] = None


async def get_hdr_processing_service() -> HDRProcessingService:
    """Get or create HDR processing service instance"""
    global _hdr_processing_service
    
    if _hdr_processing_service is None:
        from .ffmpeg_service import get_ffmpeg_service
        ffmpeg_service = await get_ffmpeg_service()
        _hdr_processing_service = HDRProcessingService(ffmpeg_service)
    
    return _hdr_processing_service
"""
Camera card support service for professional video cards
"""

import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime
import structlog

from ..models.schemas import (
    CameraCardInfo, CameraCardType, IngestJobCreate, IngestType,
    CameraMetadata, FileMetadata, IngestPriority
)
from ..core.config import settings
from ..core.exceptions import CameraCardError, FileNotFoundError
from ..core.logging import get_logger, log_ingest_event

logger = get_logger(__name__)


class CameraCardService:
    """Service for handling professional camera card formats"""
    
    def __init__(self):
        self.supported_cards = {
            CameraCardType.P2: P2CardHandler(),
            CameraCardType.XDCAM: XDCAMCardHandler(),
            CameraCardType.SXS: SXSCardHandler(),
            CameraCardType.CFEXPRESS: CFExpressCardHandler()
        }
    
    async def detect_card_type(self, card_path: str) -> Optional[CameraCardType]:
        """Detect the type of camera card at the given path"""
        try:
            if not os.path.exists(card_path) or not os.path.isdir(card_path):
                return None
            
            # Check for P2 card structure
            if await self._is_p2_card(card_path):
                return CameraCardType.P2
            
            # Check for XDCAM card structure
            if await self._is_xdcam_card(card_path):
                return CameraCardType.XDCAM
            
            # Check for SXS card structure
            if await self._is_sxs_card(card_path):
                return CameraCardType.SXS
            
            # Check for CFExpress card structure
            if await self._is_cfexpress_card(card_path):
                return CameraCardType.CFEXPRESS
            
            return None
            
        except Exception as e:
            logger.error(
                "card_detection_failed",
                error=str(e),
                card_path=card_path
            )
            return None
    
    async def analyze_card(self, card_path: str) -> Optional[CameraCardInfo]:
        """Analyze a camera card and extract metadata"""
        try:
            card_type = await self.detect_card_type(card_path)
            if not card_type:
                return None
            
            handler = self.supported_cards[card_type]
            return await handler.analyze_card(card_path)
            
        except Exception as e:
            logger.error(
                "card_analysis_failed",
                error=str(e),
                card_path=card_path
            )
            raise CameraCardError(f"Failed to analyze camera card: {str(e)}")
    
    async def create_ingest_jobs_for_card(
        self,
        card_info: CameraCardInfo,
        destination_project_id: Optional[str] = None
    ) -> List[IngestJobCreate]:
        """Create ingest jobs for all clips on a camera card"""
        try:
            handler = self.supported_cards[card_info.card_type]
            return await handler.create_ingest_jobs(card_info, destination_project_id)
            
        except Exception as e:
            logger.error(
                "card_ingest_job_creation_failed",
                error=str(e),
                card_path=card_info.card_path
            )
            raise CameraCardError(f"Failed to create ingest jobs: {str(e)}")
    
    async def _is_p2_card(self, card_path: str) -> bool:
        """Check if path contains P2 card structure"""
        p2_indicators = [
            "CONTENTS/CLIP",
            "CONTENTS/AUDIO",
            "CONTENTS/VOICE",
            "CONTENTS/PROXY",
            "CONTENTS/ICON"
        ]
        
        return any(
            os.path.exists(os.path.join(card_path, indicator))
            for indicator in p2_indicators
        )
    
    async def _is_xdcam_card(self, card_path: str) -> bool:
        """Check if path contains XDCAM card structure"""
        xdcam_indicators = [
            "BPAV",
            "BPAV/CLPR",
            "XDROOT.XML"
        ]
        
        return any(
            os.path.exists(os.path.join(card_path, indicator))
            for indicator in xdcam_indicators
        )
    
    async def _is_sxs_card(self, card_path: str) -> bool:
        """Check if path contains SXS card structure"""
        sxs_indicators = [
            "BPAV",
            "MEDIAPRO.XML"
        ]
        
        return any(
            os.path.exists(os.path.join(card_path, indicator))
            for indicator in sxs_indicators
        )
    
    async def _is_cfexpress_card(self, card_path: str) -> bool:
        """Check if path contains CFExpress card structure"""
        # CFExpress cards typically contain various camera-specific structures
        # This is a simplified detection method
        cfexpress_indicators = [
            "DCIM",
            "PRIVATE",
            "MISC"
        ]
        
        return any(
            os.path.exists(os.path.join(card_path, indicator))
            for indicator in cfexpress_indicators
        )


class BaseCardHandler:
    """Base class for camera card handlers"""
    
    async def analyze_card(self, card_path: str) -> CameraCardInfo:
        """Analyze a camera card and return card info"""
        raise NotImplementedError
    
    async def create_ingest_jobs(
        self,
        card_info: CameraCardInfo,
        destination_project_id: Optional[str] = None
    ) -> List[IngestJobCreate]:
        """Create ingest jobs for card contents"""
        raise NotImplementedError


class P2CardHandler(BaseCardHandler):
    """Handler for Panasonic P2 cards"""
    
    async def analyze_card(self, card_path: str) -> CameraCardInfo:
        """Analyze P2 card structure and contents"""
        try:
            logger.info("analyzing_p2_card", card_path=card_path)
            
            card_info = CameraCardInfo(
                card_path=card_path,
                card_type=CameraCardType.P2,
                detected_at=datetime.utcnow(),
                clips=[],
                metadata={}
            )
            
            # Analyze P2 structure
            contents_path = os.path.join(card_path, "CONTENTS")
            if not os.path.exists(contents_path):
                raise CameraCardError("Invalid P2 card structure - CONTENTS folder not found")
            
            # Read card metadata from CARDINFO.XML
            card_info.metadata = await self._read_card_metadata(contents_path)
            
            # Find all clips
            clip_path = os.path.join(contents_path, "CLIP")
            if os.path.exists(clip_path):
                card_info.clips = await self._find_p2_clips(clip_path, contents_path)
            
            # Calculate total size and file count
            card_info.total_size = sum(clip.file_size for clip in card_info.clips)
            card_info.total_files = len(card_info.clips)
            
            logger.info(
                "p2_card_analyzed",
                card_path=card_path,
                total_clips=len(card_info.clips),
                total_size=card_info.total_size
            )
            
            return card_info
            
        except Exception as e:
            logger.error(
                "p2_card_analysis_failed",
                error=str(e),
                card_path=card_path
            )
            raise CameraCardError(f"Failed to analyze P2 card: {str(e)}")
    
    async def _read_card_metadata(self, contents_path: str) -> Dict[str, Any]:
        """Read P2 card metadata from XML files"""
        metadata = {}
        
        try:
            # Read CARDINFO.XML
            cardinfo_path = os.path.join(contents_path, "CARDINFO.XML")
            if os.path.exists(cardinfo_path):
                tree = ET.parse(cardinfo_path)
                root = tree.getroot()
                
                # Extract card information
                for elem in root.iter():
                    if elem.text and elem.text.strip():
                        metadata[elem.tag] = elem.text.strip()
            
            # Read VOLINFO.XML for volume information
            volinfo_path = os.path.join(contents_path, "VOLINFO.XML")
            if os.path.exists(volinfo_path):
                tree = ET.parse(volinfo_path)
                root = tree.getroot()
                
                for elem in root.iter():
                    if elem.text and elem.text.strip():
                        metadata[f"vol_{elem.tag}"] = elem.text.strip()
        
        except Exception as e:
            logger.warning(
                "p2_metadata_read_failed",
                error=str(e),
                contents_path=contents_path
            )
        
        return metadata
    
    async def _find_p2_clips(
        self,
        clip_path: str,
        contents_path: str
    ) -> List[CameraCardInfo.ClipInfo]:
        """Find all clips on P2 card"""
        clips = []
        
        try:
            for clip_file in os.listdir(clip_path):
                if clip_file.endswith('.MXF'):
                    clip_info = await self._analyze_p2_clip(
                        clip_file,
                        clip_path,
                        contents_path
                    )
                    if clip_info:
                        clips.append(clip_info)
        
        except Exception as e:
            logger.error(
                "p2_clip_scan_failed",
                error=str(e),
                clip_path=clip_path
            )
        
        return clips
    
    async def _analyze_p2_clip(
        self,
        clip_filename: str,
        clip_path: str,
        contents_path: str
    ) -> Optional[CameraCardInfo.ClipInfo]:
        """Analyze individual P2 clip"""
        try:
            clip_name = Path(clip_filename).stem
            mxf_path = os.path.join(clip_path, clip_filename)
            
            if not os.path.exists(mxf_path):
                return None
            
            # Get file info
            file_stat = os.stat(mxf_path)
            
            # Look for associated XML metadata
            xml_path = os.path.join(clip_path, f"{clip_name}.XML")
            metadata = {}
            
            if os.path.exists(xml_path):
                metadata = await self._read_clip_metadata(xml_path)
            
            # Look for proxy file
            proxy_path = os.path.join(contents_path, "PROXY", f"{clip_name}.MP4")
            
            # Look for audio files
            audio_path = os.path.join(contents_path, "AUDIO", f"{clip_name}.MXF")
            
            # Look for icon/thumbnail
            icon_path = os.path.join(contents_path, "ICON", f"{clip_name}.BMP")
            
            clip_info = CameraCardInfo.ClipInfo(
                clip_name=clip_name,
                file_path=mxf_path,
                file_size=file_stat.st_size,
                created_at=datetime.fromtimestamp(file_stat.st_ctime),
                duration=metadata.get('duration'),
                resolution=metadata.get('resolution'),
                frame_rate=metadata.get('frame_rate'),
                codec=metadata.get('codec', 'AVC-Intra'),
                metadata=metadata,
                proxy_path=proxy_path if os.path.exists(proxy_path) else None,
                audio_path=audio_path if os.path.exists(audio_path) else None,
                thumbnail_path=icon_path if os.path.exists(icon_path) else None
            )
            
            return clip_info
            
        except Exception as e:
            logger.error(
                "p2_clip_analysis_failed",
                error=str(e),
                clip_filename=clip_filename
            )
            return None
    
    async def _read_clip_metadata(self, xml_path: str) -> Dict[str, Any]:
        """Read P2 clip metadata from XML"""
        metadata = {}
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Extract relevant metadata
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    # Convert common P2 metadata fields
                    tag = elem.tag.lower()
                    value = elem.text.strip()
                    
                    if 'duration' in tag:
                        metadata['duration'] = value
                    elif 'framerate' in tag or 'fps' in tag:
                        metadata['frame_rate'] = value
                    elif 'width' in tag or 'height' in tag:
                        if 'resolution' not in metadata:
                            metadata['resolution'] = {}
                        metadata['resolution'][tag] = value
                    elif 'codec' in tag:
                        metadata['codec'] = value
                    else:
                        metadata[tag] = value
        
        except Exception as e:
            logger.warning(
                "p2_clip_metadata_read_failed",
                error=str(e),
                xml_path=xml_path
            )
        
        return metadata
    
    async def create_ingest_jobs(
        self,
        card_info: CameraCardInfo,
        destination_project_id: Optional[str] = None
    ) -> List[IngestJobCreate]:
        """Create ingest jobs for P2 clips"""
        jobs = []
        
        try:
            for clip in card_info.clips:
                # Create main video ingest job
                job = IngestJobCreate(
                    source_path=clip.file_path,
                    destination_project_id=destination_project_id,
                    ingest_type=IngestType.CAMERA_CARD,
                    metadata_override={
                        "camera_card_type": "P2",
                        "clip_name": clip.clip_name,
                        "card_metadata": card_info.metadata,
                        "clip_metadata": clip.metadata,
                        "original_card_path": card_info.card_path
                    },
                    tags=["P2", "camera_card", "professional"],
                    priority=IngestPriority.HIGH,
                    auto_generate_proxies=True,
                    preserve_folder_structure=False
                )
                jobs.append(job)
                
                # Create separate jobs for associated files if they exist
                if clip.proxy_path and os.path.exists(clip.proxy_path):
                    proxy_job = IngestJobCreate(
                        source_path=clip.proxy_path,
                        destination_project_id=destination_project_id,
                        ingest_type=IngestType.CAMERA_CARD,
                        metadata_override={
                            "camera_card_type": "P2",
                            "clip_name": clip.clip_name,
                            "file_type": "proxy",
                            "parent_clip": clip.clip_name
                        },
                        tags=["P2", "proxy", "camera_card"],
                        priority=IngestPriority.NORMAL,
                        auto_generate_proxies=False,
                        preserve_folder_structure=False
                    )
                    jobs.append(proxy_job)
                
                if clip.audio_path and os.path.exists(clip.audio_path):
                    audio_job = IngestJobCreate(
                        source_path=clip.audio_path,
                        destination_project_id=destination_project_id,
                        ingest_type=IngestType.CAMERA_CARD,
                        metadata_override={
                            "camera_card_type": "P2",
                            "clip_name": clip.clip_name,
                            "file_type": "audio",
                            "parent_clip": clip.clip_name
                        },
                        tags=["P2", "audio", "camera_card"],
                        priority=IngestPriority.NORMAL,
                        auto_generate_proxies=False,
                        preserve_folder_structure=False
                    )
                    jobs.append(audio_job)
        
        except Exception as e:
            logger.error(
                "p2_ingest_job_creation_failed",
                error=str(e),
                card_path=card_info.card_path
            )
            raise CameraCardError(f"Failed to create P2 ingest jobs: {str(e)}")
        
        return jobs


class XDCAMCardHandler(BaseCardHandler):
    """Handler for Sony XDCAM cards"""
    
    async def analyze_card(self, card_path: str) -> CameraCardInfo:
        """Analyze XDCAM card structure and contents"""
        try:
            logger.info("analyzing_xdcam_card", card_path=card_path)
            
            card_info = CameraCardInfo(
                card_path=card_path,
                card_type=CameraCardType.XDCAM,
                detected_at=datetime.utcnow(),
                clips=[],
                metadata={}
            )
            
            # Analyze XDCAM structure
            bpav_path = os.path.join(card_path, "BPAV")
            if not os.path.exists(bpav_path):
                raise CameraCardError("Invalid XDCAM card structure - BPAV folder not found")
            
            # Read card metadata from XDROOT.XML
            card_info.metadata = await self._read_xdcam_metadata(card_path)
            
            # Find all clips in CLPR folder
            clpr_path = os.path.join(bpav_path, "CLPR")
            if os.path.exists(clpr_path):
                card_info.clips = await self._find_xdcam_clips(clpr_path, bpav_path)
            
            # Calculate total size and file count
            card_info.total_size = sum(clip.file_size for clip in card_info.clips)
            card_info.total_files = len(card_info.clips)
            
            logger.info(
                "xdcam_card_analyzed",
                card_path=card_path,
                total_clips=len(card_info.clips),
                total_size=card_info.total_size
            )
            
            return card_info
            
        except Exception as e:
            logger.error(
                "xdcam_card_analysis_failed",
                error=str(e),
                card_path=card_path
            )
            raise CameraCardError(f"Failed to analyze XDCAM card: {str(e)}")
    
    async def _read_xdcam_metadata(self, card_path: str) -> Dict[str, Any]:
        """Read XDCAM card metadata from XML files"""
        metadata = {}
        
        try:
            # Read XDROOT.XML
            xdroot_path = os.path.join(card_path, "XDROOT.XML")
            if os.path.exists(xdroot_path):
                tree = ET.parse(xdroot_path)
                root = tree.getroot()
                
                # Extract card information
                for elem in root.iter():
                    if elem.text and elem.text.strip():
                        metadata[elem.tag] = elem.text.strip()
            
            # Read DISCMETA.XML for disc information
            discmeta_path = os.path.join(card_path, "DISCMETA.XML")
            if os.path.exists(discmeta_path):
                tree = ET.parse(discmeta_path)
                root = tree.getroot()
                
                for elem in root.iter():
                    if elem.text and elem.text.strip():
                        metadata[f"disc_{elem.tag}"] = elem.text.strip()
        
        except Exception as e:
            logger.warning(
                "xdcam_metadata_read_failed",
                error=str(e),
                card_path=card_path
            )
        
        return metadata
    
    async def _find_xdcam_clips(
        self,
        clpr_path: str,
        bpav_path: str
    ) -> List[CameraCardInfo.ClipInfo]:
        """Find all clips on XDCAM card"""
        clips = []
        
        try:
            for clip_file in os.listdir(clpr_path):
                if clip_file.endswith('.MXF'):
                    clip_info = await self._analyze_xdcam_clip(
                        clip_file,
                        clpr_path,
                        bpav_path
                    )
                    if clip_info:
                        clips.append(clip_info)
        
        except Exception as e:
            logger.error(
                "xdcam_clip_scan_failed",
                error=str(e),
                clpr_path=clpr_path
            )
        
        return clips
    
    async def _analyze_xdcam_clip(
        self,
        clip_filename: str,
        clpr_path: str,
        bpav_path: str
    ) -> Optional[CameraCardInfo.ClipInfo]:
        """Analyze individual XDCAM clip"""
        try:
            clip_name = Path(clip_filename).stem
            mxf_path = os.path.join(clpr_path, clip_filename)
            
            if not os.path.exists(mxf_path):
                return None
            
            # Get file info
            file_stat = os.stat(mxf_path)
            
            # Look for associated XML metadata in CLIPMETA folder
            clipmeta_path = os.path.join(bpav_path, "CLIPMETA")
            xml_path = os.path.join(clipmeta_path, f"{clip_name}.XML")
            metadata = {}
            
            if os.path.exists(xml_path):
                metadata = await self._read_xdcam_clip_metadata(xml_path)
            
            # Look for low-res proxy in SMLPRX folder
            smlprx_path = os.path.join(bpav_path, "SMLPRX")
            proxy_path = os.path.join(smlprx_path, f"{clip_name}.MP4")
            
            # Look for high-res proxy in LGPRX folder
            if not os.path.exists(proxy_path):
                lgprx_path = os.path.join(bpav_path, "LGPRX")
                proxy_path = os.path.join(lgprx_path, f"{clip_name}.MP4")
            
            # Look for thumbnail in ICON folder
            icon_path = os.path.join(bpav_path, "ICON", f"{clip_name}.BMP")
            
            clip_info = CameraCardInfo.ClipInfo(
                clip_name=clip_name,
                file_path=mxf_path,
                file_size=file_stat.st_size,
                created_at=datetime.fromtimestamp(file_stat.st_ctime),
                duration=metadata.get('duration'),
                resolution=metadata.get('resolution'),
                frame_rate=metadata.get('frame_rate'),
                codec=metadata.get('codec', 'XDCAM'),
                metadata=metadata,
                proxy_path=proxy_path if os.path.exists(proxy_path) else None,
                audio_path=None,  # XDCAM audio is typically embedded in MXF
                thumbnail_path=icon_path if os.path.exists(icon_path) else None
            )
            
            return clip_info
            
        except Exception as e:
            logger.error(
                "xdcam_clip_analysis_failed",
                error=str(e),
                clip_filename=clip_filename
            )
            return None
    
    async def _read_xdcam_clip_metadata(self, xml_path: str) -> Dict[str, Any]:
        """Read XDCAM clip metadata from XML"""
        metadata = {}
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Extract relevant metadata
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    # Convert common XDCAM metadata fields
                    tag = elem.tag.lower()
                    value = elem.text.strip()
                    
                    if 'duration' in tag:
                        metadata['duration'] = value
                    elif 'framerate' in tag or 'fps' in tag:
                        metadata['frame_rate'] = value
                    elif 'width' in tag or 'height' in tag:
                        if 'resolution' not in metadata:
                            metadata['resolution'] = {}
                        metadata['resolution'][tag] = value
                    elif 'codec' in tag or 'essence' in tag:
                        metadata['codec'] = value
                    else:
                        metadata[tag] = value
        
        except Exception as e:
            logger.warning(
                "xdcam_clip_metadata_read_failed",
                error=str(e),
                xml_path=xml_path
            )
        
        return metadata
    
    async def create_ingest_jobs(
        self,
        card_info: CameraCardInfo,
        destination_project_id: Optional[str] = None
    ) -> List[IngestJobCreate]:
        """Create ingest jobs for XDCAM clips"""
        jobs = []
        
        try:
            for clip in card_info.clips:
                # Create main video ingest job
                job = IngestJobCreate(
                    source_path=clip.file_path,
                    destination_project_id=destination_project_id,
                    ingest_type=IngestType.CAMERA_CARD,
                    metadata_override={
                        "camera_card_type": "XDCAM",
                        "clip_name": clip.clip_name,
                        "card_metadata": card_info.metadata,
                        "clip_metadata": clip.metadata,
                        "original_card_path": card_info.card_path
                    },
                    tags=["XDCAM", "camera_card", "professional", "sony"],
                    priority=IngestPriority.HIGH,
                    auto_generate_proxies=True,
                    preserve_folder_structure=False
                )
                jobs.append(job)
                
                # Create separate job for proxy if it exists
                if clip.proxy_path and os.path.exists(clip.proxy_path):
                    proxy_job = IngestJobCreate(
                        source_path=clip.proxy_path,
                        destination_project_id=destination_project_id,
                        ingest_type=IngestType.CAMERA_CARD,
                        metadata_override={
                            "camera_card_type": "XDCAM",
                            "clip_name": clip.clip_name,
                            "file_type": "proxy",
                            "parent_clip": clip.clip_name
                        },
                        tags=["XDCAM", "proxy", "camera_card"],
                        priority=IngestPriority.NORMAL,
                        auto_generate_proxies=False,
                        preserve_folder_structure=False
                    )
                    jobs.append(proxy_job)
        
        except Exception as e:
            logger.error(
                "xdcam_ingest_job_creation_failed",
                error=str(e),
                card_path=card_info.card_path
            )
            raise CameraCardError(f"Failed to create XDCAM ingest jobs: {str(e)}")
        
        return jobs


class SXSCardHandler(BaseCardHandler):
    """Handler for Sony SXS cards"""
    
    async def analyze_card(self, card_path: str) -> CameraCardInfo:
        """Analyze SXS card structure and contents"""
        try:
            logger.info("analyzing_sxs_card", card_path=card_path)
            
            card_info = CameraCardInfo(
                card_path=card_path,
                card_type=CameraCardType.SXS,
                detected_at=datetime.utcnow(),
                clips=[],
                metadata={}
            )
            
            # Analyze SXS structure (similar to XDCAM but with MEDIAPRO.XML)
            bpav_path = os.path.join(card_path, "BPAV")
            if not os.path.exists(bpav_path):
                raise CameraCardError("Invalid SXS card structure - BPAV folder not found")
            
            # Read card metadata from MEDIAPRO.XML
            card_info.metadata = await self._read_sxs_metadata(card_path)
            
            # Find all clips in CLPR folder
            clpr_path = os.path.join(bpav_path, "CLPR")
            if os.path.exists(clpr_path):
                card_info.clips = await self._find_sxs_clips(clpr_path, bpav_path)
            
            # Calculate total size and file count
            card_info.total_size = sum(clip.file_size for clip in card_info.clips)
            card_info.total_files = len(card_info.clips)
            
            logger.info(
                "sxs_card_analyzed",
                card_path=card_path,
                total_clips=len(card_info.clips),
                total_size=card_info.total_size
            )
            
            return card_info
            
        except Exception as e:
            logger.error(
                "sxs_card_analysis_failed",
                error=str(e),
                card_path=card_path
            )
            raise CameraCardError(f"Failed to analyze SXS card: {str(e)}")
    
    async def _read_sxs_metadata(self, card_path: str) -> Dict[str, Any]:
        """Read SXS card metadata from XML files"""
        metadata = {}
        
        try:
            # Read MEDIAPRO.XML
            mediapro_path = os.path.join(card_path, "MEDIAPRO.XML")
            if os.path.exists(mediapro_path):
                tree = ET.parse(mediapro_path)
                root = tree.getroot()
                
                # Extract card information
                for elem in root.iter():
                    if elem.text and elem.text.strip():
                        metadata[elem.tag] = elem.text.strip()
            
            # Check for CARDINFO.XML (some SXS cards have this)
            cardinfo_path = os.path.join(card_path, "CARDINFO.XML")
            if os.path.exists(cardinfo_path):
                tree = ET.parse(cardinfo_path)
                root = tree.getroot()
                
                for elem in root.iter():
                    if elem.text and elem.text.strip():
                        metadata[f"card_{elem.tag}"] = elem.text.strip()
        
        except Exception as e:
            logger.warning(
                "sxs_metadata_read_failed",
                error=str(e),
                card_path=card_path
            )
        
        return metadata
    
    async def _find_sxs_clips(
        self,
        clpr_path: str,
        bpav_path: str
    ) -> List[CameraCardInfo.ClipInfo]:
        """Find all clips on SXS card"""
        clips = []
        
        try:
            for clip_file in os.listdir(clpr_path):
                if clip_file.endswith('.MXF'):
                    clip_info = await self._analyze_sxs_clip(
                        clip_file,
                        clpr_path,
                        bpav_path
                    )
                    if clip_info:
                        clips.append(clip_info)
        
        except Exception as e:
            logger.error(
                "sxs_clip_scan_failed",
                error=str(e),
                clpr_path=clpr_path
            )
        
        return clips
    
    async def _analyze_sxs_clip(
        self,
        clip_filename: str,
        clpr_path: str,
        bpav_path: str
    ) -> Optional[CameraCardInfo.ClipInfo]:
        """Analyze individual SXS clip"""
        try:
            clip_name = Path(clip_filename).stem
            mxf_path = os.path.join(clpr_path, clip_filename)
            
            if not os.path.exists(mxf_path):
                return None
            
            # Get file info
            file_stat = os.stat(mxf_path)
            
            # Look for associated XML metadata in CLIPMETA folder
            clipmeta_path = os.path.join(bpav_path, "CLIPMETA")
            xml_path = os.path.join(clipmeta_path, f"{clip_name}.XML")
            metadata = {}
            
            if os.path.exists(xml_path):
                metadata = await self._read_sxs_clip_metadata(xml_path)
            
            # Look for proxy in SMLPRX folder (SXS typically uses low-res proxies)
            smlprx_path = os.path.join(bpav_path, "SMLPRX")
            proxy_path = os.path.join(smlprx_path, f"{clip_name}.MP4")
            
            # Look for thumbnail in ICON folder
            icon_path = os.path.join(bpav_path, "ICON", f"{clip_name}.BMP")
            
            clip_info = CameraCardInfo.ClipInfo(
                clip_name=clip_name,
                file_path=mxf_path,
                file_size=file_stat.st_size,
                created_at=datetime.fromtimestamp(file_stat.st_ctime),
                duration=metadata.get('duration'),
                resolution=metadata.get('resolution'),
                frame_rate=metadata.get('frame_rate'),
                codec=metadata.get('codec', 'SXS'),
                metadata=metadata,
                proxy_path=proxy_path if os.path.exists(proxy_path) else None,
                audio_path=None,  # SXS audio is typically embedded in MXF
                thumbnail_path=icon_path if os.path.exists(icon_path) else None
            )
            
            return clip_info
            
        except Exception as e:
            logger.error(
                "sxs_clip_analysis_failed",
                error=str(e),
                clip_filename=clip_filename
            )
            return None
    
    async def _read_sxs_clip_metadata(self, xml_path: str) -> Dict[str, Any]:
        """Read SXS clip metadata from XML"""
        metadata = {}
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Extract relevant metadata
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    # Convert common SXS metadata fields
                    tag = elem.tag.lower()
                    value = elem.text.strip()
                    
                    if 'duration' in tag:
                        metadata['duration'] = value
                    elif 'framerate' in tag or 'fps' in tag:
                        metadata['frame_rate'] = value
                    elif 'width' in tag or 'height' in tag:
                        if 'resolution' not in metadata:
                            metadata['resolution'] = {}
                        metadata['resolution'][tag] = value
                    elif 'codec' in tag or 'essence' in tag:
                        metadata['codec'] = value
                    else:
                        metadata[tag] = value
        
        except Exception as e:
            logger.warning(
                "sxs_clip_metadata_read_failed",
                error=str(e),
                xml_path=xml_path
            )
        
        return metadata
    
    async def create_ingest_jobs(
        self,
        card_info: CameraCardInfo,
        destination_project_id: Optional[str] = None
    ) -> List[IngestJobCreate]:
        """Create ingest jobs for SXS clips"""
        jobs = []
        
        try:
            for clip in card_info.clips:
                # Create main video ingest job
                job = IngestJobCreate(
                    source_path=clip.file_path,
                    destination_project_id=destination_project_id,
                    ingest_type=IngestType.CAMERA_CARD,
                    metadata_override={
                        "camera_card_type": "SXS",
                        "clip_name": clip.clip_name,
                        "card_metadata": card_info.metadata,
                        "clip_metadata": clip.metadata,
                        "original_card_path": card_info.card_path
                    },
                    tags=["SXS", "camera_card", "professional", "sony"],
                    priority=IngestPriority.HIGH,
                    auto_generate_proxies=True,
                    preserve_folder_structure=False
                )
                jobs.append(job)
                
                # Create separate job for proxy if it exists
                if clip.proxy_path and os.path.exists(clip.proxy_path):
                    proxy_job = IngestJobCreate(
                        source_path=clip.proxy_path,
                        destination_project_id=destination_project_id,
                        ingest_type=IngestType.CAMERA_CARD,
                        metadata_override={
                            "camera_card_type": "SXS",
                            "clip_name": clip.clip_name,
                            "file_type": "proxy",
                            "parent_clip": clip.clip_name
                        },
                        tags=["SXS", "proxy", "camera_card"],
                        priority=IngestPriority.NORMAL,
                        auto_generate_proxies=False,
                        preserve_folder_structure=False
                    )
                    jobs.append(proxy_job)
        
        except Exception as e:
            logger.error(
                "sxs_ingest_job_creation_failed",
                error=str(e),
                card_path=card_info.card_path
            )
            raise CameraCardError(f"Failed to create SXS ingest jobs: {str(e)}")
        
        return jobs


class CFExpressCardHandler(BaseCardHandler):
    """Handler for CFExpress cards"""
    
    async def analyze_card(self, card_path: str) -> CameraCardInfo:
        """Analyze CFExpress card structure and contents"""
        try:
            logger.info("analyzing_cfexpress_card", card_path=card_path)
            
            card_info = CameraCardInfo(
                card_path=card_path,
                card_type=CameraCardType.CFEXPRESS,
                detected_at=datetime.utcnow(),
                clips=[],
                metadata={}
            )
            
            # CFExpress cards can have various structures depending on camera manufacturer
            # Check for common structures: DCIM, PRIVATE, MISC
            card_info.metadata = await self._read_cfexpress_metadata(card_path)
            
            # Find clips in various possible locations
            clips = []
            
            # Check DCIM folder (common for consumer cameras)
            dcim_path = os.path.join(card_path, "DCIM")
            if os.path.exists(dcim_path):
                clips.extend(await self._find_dcim_clips(dcim_path))
            
            # Check PRIVATE folder (some professional cameras)
            private_path = os.path.join(card_path, "PRIVATE")
            if os.path.exists(private_path):
                clips.extend(await self._find_private_clips(private_path))
            
            # Check for direct video files in root
            clips.extend(await self._find_root_clips(card_path))
            
            card_info.clips = clips
            
            # Calculate total size and file count
            card_info.total_size = sum(clip.file_size for clip in card_info.clips)
            card_info.total_files = len(card_info.clips)
            
            logger.info(
                "cfexpress_card_analyzed",
                card_path=card_path,
                total_clips=len(card_info.clips),
                total_size=card_info.total_size
            )
            
            return card_info
            
        except Exception as e:
            logger.error(
                "cfexpress_card_analysis_failed",
                error=str(e),
                card_path=card_path
            )
            raise CameraCardError(f"Failed to analyze CFExpress card: {str(e)}")
    
    async def _read_cfexpress_metadata(self, card_path: str) -> Dict[str, Any]:
        """Read CFExpress card metadata"""
        metadata = {"card_type": "CFExpress", "format": "High-Speed"}
        
        try:
            # Check for various metadata files that might exist
            metadata_files = [
                "INFO.TXT",
                "CARDINFO.XML",
                "MISC/INFO.XML",
                "PRIVATE/INFO.XML"
            ]
            
            for meta_file in metadata_files:
                meta_path = os.path.join(card_path, meta_file)
                if os.path.exists(meta_path):
                    if meta_file.endswith('.XML'):
                        try:
                            tree = ET.parse(meta_path)
                            root = tree.getroot()
                            
                            for elem in root.iter():
                                if elem.text and elem.text.strip():
                                    metadata[elem.tag] = elem.text.strip()
                        except ET.ParseError:
                            logger.warning(f"Failed to parse XML metadata file: {meta_path}")
                    
                    elif meta_file.endswith('.TXT'):
                        try:
                            with open(meta_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                # Simple key=value parsing
                                for line in content.split('\n'):
                                    if '=' in line:
                                        key, value = line.split('=', 1)
                                        metadata[key.strip()] = value.strip()
                        except Exception:
                            logger.warning(f"Failed to parse TXT metadata file: {meta_path}")
        
        except Exception as e:
            logger.warning(
                "cfexpress_metadata_read_failed",
                error=str(e),
                card_path=card_path
            )
        
        return metadata
    
    async def _find_dcim_clips(self, dcim_path: str) -> List[CameraCardInfo.ClipInfo]:
        """Find clips in DCIM folder structure"""
        clips = []
        
        try:
            # DCIM typically has numbered folders like 100MEDIA, 101MEDIA, etc.
            for folder_name in os.listdir(dcim_path):
                folder_path = os.path.join(dcim_path, folder_name)
                if os.path.isdir(folder_path):
                    clips.extend(await self._scan_folder_for_clips(folder_path))
        
        except Exception as e:
            logger.error(
                "dcim_clip_scan_failed",
                error=str(e),
                dcim_path=dcim_path
            )
        
        return clips
    
    async def _find_private_clips(self, private_path: str) -> List[CameraCardInfo.ClipInfo]:
        """Find clips in PRIVATE folder structure"""
        clips = []
        
        try:
            # Recursively scan PRIVATE folder
            clips.extend(await self._scan_folder_for_clips(private_path, recursive=True))
        
        except Exception as e:
            logger.error(
                "private_clip_scan_failed",
                error=str(e),
                private_path=private_path
            )
        
        return clips
    
    async def _find_root_clips(self, card_path: str) -> List[CameraCardInfo.ClipInfo]:
        """Find clips directly in card root"""
        clips = []
        
        try:
            clips.extend(await self._scan_folder_for_clips(card_path, recursive=False))
        
        except Exception as e:
            logger.error(
                "root_clip_scan_failed",
                error=str(e),
                card_path=card_path
            )
        
        return clips
    
    async def _scan_folder_for_clips(
        self,
        folder_path: str,
        recursive: bool = False
    ) -> List[CameraCardInfo.ClipInfo]:
        """Scan a folder for video clips"""
        clips = []
        
        # Common video file extensions for CFExpress cards
        video_extensions = ['.MP4', '.MOV', '.MXF', '.R3D', '.BRAW', '.AVI', '.MKV']
        
        try:
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                
                if os.path.isfile(item_path):
                    # Check if it's a video file
                    if any(item.upper().endswith(ext) for ext in video_extensions):
                        clip_info = await self._analyze_cfexpress_clip(item_path)
                        if clip_info:
                            clips.append(clip_info)
                
                elif os.path.isdir(item_path) and recursive:
                    # Recursively scan subdirectories
                    clips.extend(await self._scan_folder_for_clips(item_path, recursive=True))
        
        except Exception as e:
            logger.error(
                "folder_clip_scan_failed",
                error=str(e),
                folder_path=folder_path
            )
        
        return clips
    
    async def _analyze_cfexpress_clip(self, clip_path: str) -> Optional[CameraCardInfo.ClipInfo]:
        """Analyze individual CFExpress clip"""
        try:
            clip_name = Path(clip_path).stem
            
            if not os.path.exists(clip_path):
                return None
            
            # Get file info
            file_stat = os.stat(clip_path)
            
            # CFExpress cards typically don't have separate metadata files
            # Basic metadata extraction would need external tools like ffprobe
            metadata = {
                "file_extension": Path(clip_path).suffix.lower(),
                "folder_location": str(Path(clip_path).parent)
            }
            
            clip_info = CameraCardInfo.ClipInfo(
                clip_name=clip_name,
                file_path=clip_path,
                file_size=file_stat.st_size,
                created_at=datetime.fromtimestamp(file_stat.st_ctime),
                duration=None,  # Would need ffprobe to extract
                resolution=None,  # Would need ffprobe to extract
                frame_rate=None,  # Would need ffprobe to extract
                codec=None,  # Would need ffprobe to extract
                metadata=metadata,
                proxy_path=None,  # CFExpress typically doesn't have embedded proxies
                audio_path=None,  # Audio is typically embedded
                thumbnail_path=None  # Thumbnails are typically generated by camera software
            )
            
            return clip_info
            
        except Exception as e:
            logger.error(
                "cfexpress_clip_analysis_failed",
                error=str(e),
                clip_path=clip_path
            )
            return None
    
    async def create_ingest_jobs(
        self,
        card_info: CameraCardInfo,
        destination_project_id: Optional[str] = None
    ) -> List[IngestJobCreate]:
        """Create ingest jobs for CFExpress clips"""
        jobs = []
        
        try:
            for clip in card_info.clips:
                # Create main video ingest job
                job = IngestJobCreate(
                    source_path=clip.file_path,
                    destination_project_id=destination_project_id,
                    ingest_type=IngestType.CAMERA_CARD,
                    metadata_override={
                        "camera_card_type": "CFExpress",
                        "clip_name": clip.clip_name,
                        "card_metadata": card_info.metadata,
                        "clip_metadata": clip.metadata,
                        "original_card_path": card_info.card_path,
                        "file_extension": clip.metadata.get("file_extension"),
                        "folder_location": clip.metadata.get("folder_location")
                    },
                    tags=["CFExpress", "camera_card", "high_speed"],
                    priority=IngestPriority.HIGH,
                    auto_generate_proxies=True,  # Important for high-res CFExpress files
                    preserve_folder_structure=True  # Preserve original folder structure
                )
                jobs.append(job)
        
        except Exception as e:
            logger.error(
                "cfexpress_ingest_job_creation_failed",
                error=str(e),
                card_path=card_info.card_path
            )
            raise CameraCardError(f"Failed to create CFExpress ingest jobs: {str(e)}")
        
        return jobs


# Dependency injection
_camera_card_service: Optional[CameraCardService] = None


async def get_camera_card_service() -> CameraCardService:
    """Get camera card service instance"""
    global _camera_card_service
    
    if _camera_card_service is None:
        _camera_card_service = CameraCardService()
    
    return _camera_card_service
"""
Tests for the Camera Card Service
"""

import pytest
import os
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from unittest.mock import Mock, patch

from src.services.camera_card_service import CameraCardService, P2CardHandler
from src.models.schemas import CameraCardType, CameraCardInfo, IngestType, IngestPriority
from src.core.exceptions import CameraCardError


@pytest.fixture
def mock_p2_card_structure():
    """Create a mock P2 card directory structure"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create P2 directory structure
        contents_dir = os.path.join(temp_dir, "CONTENTS")
        os.makedirs(contents_dir)
        
        # Create subdirectories
        for subdir in ["CLIP", "AUDIO", "PROXY", "ICON", "VOICE"]:
            os.makedirs(os.path.join(contents_dir, subdir))
        
        # Create sample CARDINFO.XML
        cardinfo_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <CardInfo>
            <SerialNumber>P2001234</SerialNumber>
            <Model>AJ-P2E064FG</Model>
            <Manufacturer>Panasonic</Manufacturer>
            <Capacity>64GB</Capacity>
        </CardInfo>"""
        
        with open(os.path.join(contents_dir, "CARDINFO.XML"), "w") as f:
            f.write(cardinfo_xml)
        
        # Create sample VOLINFO.XML
        volinfo_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VolumeInfo>
            <Label>P2_001</Label>
            <CreationDate>2025-01-15T10:30:00Z</CreationDate>
        </VolumeInfo>"""
        
        with open(os.path.join(contents_dir, "VOLINFO.XML"), "w") as f:
            f.write(volinfo_xml)
        
        # Create sample clip files
        clip_dir = os.path.join(contents_dir, "CLIP")
        
        # Create MXF files
        for i in range(3):
            clip_name = f"0001AB{i:02d}"
            mxf_file = os.path.join(clip_dir, f"{clip_name}.MXF")
            with open(mxf_file, "wb") as f:
                f.write(b"fake_mxf_data" * 1000)  # Create some fake data
            
            # Create associated XML metadata
            clip_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
            <ClipMetadata>
                <ClipName>{clip_name}</ClipName>
                <Duration>00:01:30:00</Duration>
                <FrameRate>29.97</FrameRate>
                <VideoFormat>1920x1080</VideoFormat>
                <Codec>AVC-Intra100</Codec>
            </ClipMetadata>"""
            
            with open(os.path.join(clip_dir, f"{clip_name}.XML"), "w") as f:
                f.write(clip_xml)
            
            # Create proxy files
            proxy_file = os.path.join(contents_dir, "PROXY", f"{clip_name}.MP4")
            with open(proxy_file, "wb") as f:
                f.write(b"fake_proxy_data" * 100)
            
            # Create thumbnail files
            icon_file = os.path.join(contents_dir, "ICON", f"{clip_name}.BMP")
            with open(icon_file, "wb") as f:
                f.write(b"fake_thumbnail_data" * 50)
            
            # Create audio files
            audio_file = os.path.join(contents_dir, "AUDIO", f"{clip_name}.MXF")
            with open(audio_file, "wb") as f:
                f.write(b"fake_audio_data" * 200)
        
        yield temp_dir


@pytest.fixture
def camera_card_service():
    """Create a camera card service instance"""
    return CameraCardService()


class TestCameraCardService:
    """Test suite for camera card service"""
    
    @pytest.mark.asyncio
    async def test_detect_p2_card(self, camera_card_service, mock_p2_card_structure):
        """Test P2 card detection"""
        card_type = await camera_card_service.detect_card_type(mock_p2_card_structure)
        assert card_type == CameraCardType.P2
    
    @pytest.mark.asyncio
    async def test_detect_no_card(self, camera_card_service):
        """Test detection with no card present"""
        with tempfile.TemporaryDirectory() as temp_dir:
            card_type = await camera_card_service.detect_card_type(temp_dir)
            assert card_type is None
    
    @pytest.mark.asyncio
    async def test_detect_nonexistent_path(self, camera_card_service):
        """Test detection with nonexistent path"""
        card_type = await camera_card_service.detect_card_type("/nonexistent/path")
        assert card_type is None
    
    @pytest.mark.asyncio
    async def test_analyze_p2_card(self, camera_card_service, mock_p2_card_structure):
        """Test P2 card analysis"""
        card_info = await camera_card_service.analyze_card(mock_p2_card_structure)
        
        assert card_info is not None
        assert card_info.card_type == CameraCardType.P2
        assert card_info.card_path == mock_p2_card_structure
        assert len(card_info.clips) == 3
        assert card_info.total_files == 3
        assert card_info.total_size > 0
        
        # Check metadata
        assert "SerialNumber" in card_info.metadata
        assert card_info.metadata["SerialNumber"] == "P2001234"
        
        # Check first clip
        first_clip = card_info.clips[0]
        assert first_clip.clip_name.startswith("0001AB")
        assert first_clip.file_path.endswith(".MXF")
        assert first_clip.file_size > 0
        assert first_clip.proxy_path is not None
        assert first_clip.audio_path is not None
        assert first_clip.thumbnail_path is not None
    
    @pytest.mark.asyncio
    async def test_create_ingest_jobs_for_p2_card(
        self,
        camera_card_service,
        mock_p2_card_structure
    ):
        """Test creating ingest jobs for P2 card"""
        # First analyze the card
        card_info = await camera_card_service.analyze_card(mock_p2_card_structure)
        
        # Create ingest jobs
        jobs = await camera_card_service.create_ingest_jobs_for_card(
            card_info,
            destination_project_id="test-project-123"
        )
        
        # Should have multiple jobs (main + proxy + audio for each clip)
        assert len(jobs) > 3  # At least one job per clip, likely more with associated files
        
        # Check first job (main clip)
        main_job = jobs[0]
        assert main_job.ingest_type == IngestType.CAMERA_CARD
        assert main_job.destination_project_id == "test-project-123"
        assert main_job.priority == IngestPriority.HIGH
        assert "P2" in main_job.tags
        assert "camera_card" in main_job.tags
        assert main_job.metadata_override["camera_card_type"] == "P2"
        assert "clip_name" in main_job.metadata_override
    
    @pytest.mark.asyncio
    async def test_analyze_invalid_card(self, camera_card_service):
        """Test analyzing invalid card structure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create fake P2 structure but without proper contents
            contents_dir = os.path.join(temp_dir, "CONTENTS")
            os.makedirs(contents_dir)
            
            with pytest.raises(CameraCardError, match="Invalid P2 card structure"):
                await camera_card_service.analyze_card(temp_dir)


class TestP2CardHandler:
    """Test suite for P2 card handler specifically"""
    
    @pytest.mark.asyncio
    async def test_p2_metadata_extraction(self, mock_p2_card_structure):
        """Test P2 metadata extraction from XML files"""
        handler = P2CardHandler()
        contents_path = os.path.join(mock_p2_card_structure, "CONTENTS")
        
        metadata = await handler._read_card_metadata(contents_path)
        
        assert "SerialNumber" in metadata
        assert metadata["SerialNumber"] == "P2001234"
        assert "Model" in metadata
        assert metadata["Model"] == "AJ-P2E064FG"
        
        # Volume info should be prefixed with 'vol_'
        assert "vol_Label" in metadata
        assert metadata["vol_Label"] == "P2_001"
    
    @pytest.mark.asyncio
    async def test_p2_clip_detection(self, mock_p2_card_structure):
        """Test P2 clip detection and analysis"""
        handler = P2CardHandler()
        clip_path = os.path.join(mock_p2_card_structure, "CONTENTS", "CLIP")
        contents_path = os.path.join(mock_p2_card_structure, "CONTENTS")
        
        clips = await handler._find_p2_clips(clip_path, contents_path)
        
        assert len(clips) == 3
        
        for clip in clips:
            assert clip.clip_name.startswith("0001AB")
            assert clip.file_path.endswith(".MXF")
            assert clip.file_size > 0
            assert clip.proxy_path is not None
            assert os.path.exists(clip.proxy_path)
            assert clip.audio_path is not None
            assert os.path.exists(clip.audio_path)
            assert clip.thumbnail_path is not None
            assert os.path.exists(clip.thumbnail_path)
    
    @pytest.mark.asyncio
    async def test_p2_clip_metadata_parsing(self, mock_p2_card_structure):
        """Test P2 clip metadata parsing from XML"""
        handler = P2CardHandler()
        clip_path = os.path.join(mock_p2_card_structure, "CONTENTS", "CLIP")
        xml_files = [f for f in os.listdir(clip_path) if f.endswith('.XML')]
        
        assert len(xml_files) > 0
        
        xml_path = os.path.join(clip_path, xml_files[0])
        metadata = await handler._read_clip_metadata(xml_path)
        
        assert "clipname" in metadata or "ClipName" in metadata
        assert "duration" in metadata or "Duration" in metadata
    
    @pytest.mark.asyncio
    async def test_p2_complete_analysis_flow(self, mock_p2_card_structure):
        """Test complete P2 analysis flow"""
        handler = P2CardHandler()
        
        card_info = await handler.analyze_card(mock_p2_card_structure)
        
        # Verify card info structure
        assert card_info.card_type == CameraCardType.P2
        assert card_info.card_path == mock_p2_card_structure
        assert isinstance(card_info.detected_at, datetime)
        assert len(card_info.clips) == 3
        assert card_info.total_files == 3
        assert card_info.total_size > 0
        
        # Verify metadata
        assert isinstance(card_info.metadata, dict)
        assert len(card_info.metadata) > 0
        
        # Verify each clip
        for i, clip in enumerate(card_info.clips):
            assert clip.clip_name is not None
            assert clip.file_path.endswith(".MXF")
            assert clip.file_size > 0
            assert isinstance(clip.created_at, datetime)
            
            # Verify associated files exist
            assert clip.proxy_path is not None
            assert os.path.exists(clip.proxy_path)
            assert clip.audio_path is not None  
            assert os.path.exists(clip.audio_path)
            assert clip.thumbnail_path is not None
            assert os.path.exists(clip.thumbnail_path)
    
    @pytest.mark.asyncio
    async def test_p2_job_creation(self, mock_p2_card_structure):
        """Test P2 ingest job creation"""
        handler = P2CardHandler()
        
        # First analyze the card
        card_info = await handler.analyze_card(mock_p2_card_structure)
        
        # Create jobs
        jobs = await handler.create_ingest_jobs(card_info, "test-project")
        
        # Should have jobs for main clips plus associated files
        # 3 clips * (1 main + 1 proxy + 1 audio) = 9 jobs
        assert len(jobs) == 9
        
        # Group jobs by type
        main_jobs = [j for j in jobs if "file_type" not in j.metadata_override]
        proxy_jobs = [j for j in jobs if j.metadata_override.get("file_type") == "proxy"]
        audio_jobs = [j for j in jobs if j.metadata_override.get("file_type") == "audio"]
        
        assert len(main_jobs) == 3
        assert len(proxy_jobs) == 3  
        assert len(audio_jobs) == 3
        
        # Verify main job properties
        main_job = main_jobs[0]
        assert main_job.source_path.endswith(".MXF")
        assert main_job.destination_project_id == "test-project"
        assert main_job.ingest_type == IngestType.CAMERA_CARD
        assert main_job.priority == IngestPriority.HIGH
        assert main_job.auto_generate_proxies == True
        assert "P2" in main_job.tags
        
        # Verify metadata
        assert main_job.metadata_override["camera_card_type"] == "P2"
        assert "clip_name" in main_job.metadata_override
        assert "card_metadata" in main_job.metadata_override
        assert "clip_metadata" in main_job.metadata_override
        
        # Verify proxy job properties
        proxy_job = proxy_jobs[0]
        assert proxy_job.source_path.endswith(".MP4")
        assert proxy_job.priority == IngestPriority.NORMAL
        assert proxy_job.auto_generate_proxies == False
        assert proxy_job.metadata_override["file_type"] == "proxy"


class TestCameraCardIntegration:
    """Integration tests for camera card functionality"""
    
    @pytest.mark.asyncio
    async def test_full_p2_card_workflow(self, mock_p2_card_structure):
        """Test complete P2 card workflow from detection to job creation"""
        service = CameraCardService()
        
        # Step 1: Detect card type
        card_type = await service.detect_card_type(mock_p2_card_structure)
        assert card_type == CameraCardType.P2
        
        # Step 2: Analyze card
        card_info = await service.analyze_card(mock_p2_card_structure)
        assert card_info is not None
        assert card_info.card_type == CameraCardType.P2
        assert len(card_info.clips) == 3
        
        # Step 3: Create ingest jobs
        jobs = await service.create_ingest_jobs_for_card(
            card_info,
            destination_project_id="integration-test-project"
        )
        
        assert len(jobs) > 0
        assert all(job.destination_project_id == "integration-test-project" for job in jobs)
        assert all(job.ingest_type == IngestType.CAMERA_CARD for job in jobs)
        
        # Verify all clips are covered
        main_jobs = [j for j in jobs if "file_type" not in j.metadata_override]
        clip_names = [j.metadata_override["clip_name"] for j in main_jobs]
        assert len(set(clip_names)) == 3  # Three unique clips
    
    @pytest.mark.asyncio
    async def test_unsupported_card_type_handling(self):
        """Test handling of unsupported card types"""
        service = CameraCardService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some random directory structure
            os.makedirs(os.path.join(temp_dir, "RANDOM_FOLDER"))
            
            # Should not detect any card type
            card_type = await service.detect_card_type(temp_dir)
            assert card_type is None
            
            # Analysis should return None
            card_info = await service.analyze_card(temp_dir)
            assert card_info is None
    
    @pytest.mark.asyncio
    async def test_error_handling_during_analysis(self):
        """Test error handling during card analysis"""
        service = CameraCardService()
        
        # Test with nonexistent path
        with pytest.raises(CameraCardError):
            await service.analyze_card("/nonexistent/path")
    
    @pytest.mark.asyncio
    async def test_p2_card_with_missing_associated_files(self, mock_p2_card_structure):
        """Test P2 card analysis when some associated files are missing"""
        # Remove some proxy and audio files to test graceful handling
        contents_dir = os.path.join(mock_p2_card_structure, "CONTENTS")
        proxy_dir = os.path.join(contents_dir, "PROXY")
        audio_dir = os.path.join(contents_dir, "AUDIO")
        
        # Remove one proxy file and one audio file
        proxy_files = os.listdir(proxy_dir)
        audio_files = os.listdir(audio_dir)
        
        if proxy_files:
            os.remove(os.path.join(proxy_dir, proxy_files[0]))
        if audio_files:
            os.remove(os.path.join(audio_dir, audio_files[0]))
        
        service = CameraCardService()
        card_info = await service.analyze_card(mock_p2_card_structure)
        
        # Should still work, but some clips won't have all associated files
        assert card_info is not None
        assert len(card_info.clips) == 3
        
        # Check that missing files are handled gracefully
        clips_with_proxy = [c for c in card_info.clips if c.proxy_path and os.path.exists(c.proxy_path)]
        clips_with_audio = [c for c in card_info.clips if c.audio_path and os.path.exists(c.audio_path)]
        
        assert len(clips_with_proxy) == 2  # One missing
        assert len(clips_with_audio) == 2  # One missing


@pytest.mark.asyncio
async def test_camera_card_service_initialization():
    """Test camera card service initialization"""
    service = CameraCardService()
    
    # Should have handlers for all supported card types
    assert CameraCardType.P2 in service.supported_cards
    assert CameraCardType.XDCAM in service.supported_cards
    assert CameraCardType.SXS in service.supported_cards
    assert CameraCardType.CFEXPRESS in service.supported_cards
    
    # All handlers should be instances of BaseCardHandler
    from src.services.camera_card_service import BaseCardHandler
    for handler in service.supported_cards.values():
        assert isinstance(handler, BaseCardHandler)
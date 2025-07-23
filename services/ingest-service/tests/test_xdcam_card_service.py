"""
Tests for the XDCAM Camera Card Handler
"""

import pytest
import os
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from unittest.mock import Mock, patch

from src.services.camera_card_service import CameraCardService, XDCAMCardHandler
from src.models.schemas import CameraCardType, CameraCardInfo, IngestType, IngestPriority
from src.core.exceptions import CameraCardError


@pytest.fixture
def mock_xdcam_card_structure():
    """Create a mock XDCAM card directory structure"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create XDCAM directory structure
        bpav_dir = os.path.join(temp_dir, "BPAV")
        os.makedirs(bpav_dir)
        
        # Create subdirectories
        for subdir in ["CLPR", "CLIPMETA", "SMLPRX", "LGPRX", "ICON"]:
            os.makedirs(os.path.join(bpav_dir, subdir))
        
        # Create sample XDROOT.XML
        xdroot_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <XDCAMRoot>
            <SerialNumber>XDCAM001234</SerialNumber>
            <Model>PMW-F5</Model>
            <Manufacturer>Sony</Manufacturer>
            <Capacity>128GB</Capacity>
        </XDCAMRoot>"""
        
        with open(os.path.join(temp_dir, "XDROOT.XML"), "w") as f:
            f.write(xdroot_xml)
        
        # Create sample DISCMETA.XML
        discmeta_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <DiscMeta>
            <Label>XDCAM_001</Label>
            <CreationDate>2025-01-15T10:30:00Z</CreationDate>
            <Format>XDCAM HD</Format>
        </DiscMeta>"""
        
        with open(os.path.join(temp_dir, "DISCMETA.XML"), "w") as f:
            f.write(discmeta_xml)
        
        # Create sample clip files
        clpr_dir = os.path.join(bpav_dir, "CLPR")
        clipmeta_dir = os.path.join(bpav_dir, "CLIPMETA")
        
        # Create MXF files
        for i in range(3):
            clip_name = f"C{i:04d}001"
            mxf_file = os.path.join(clpr_dir, f"{clip_name}.MXF")
            with open(mxf_file, "wb") as f:
                f.write(b"fake_xdcam_mxf_data" * 1000)  # Create some fake data
            
            # Create associated XML metadata
            clip_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
            <ClipMetadata>
                <ClipName>{clip_name}</ClipName>
                <Duration>00:02:15:00</Duration>
                <FrameRate>25.00</FrameRate>
                <VideoFormat>1920x1080</VideoFormat>
                <EssenceType>XDCAM HD422</EssenceType>
                <Codec>MPEG-2 HD422</Codec>
            </ClipMetadata>"""
            
            with open(os.path.join(clipmeta_dir, f"{clip_name}.XML"), "w") as f:
                f.write(clip_xml)
            
            # Create low-res proxy files
            smlprx_file = os.path.join(bpav_dir, "SMLPRX", f"{clip_name}.MP4")
            with open(smlprx_file, "wb") as f:
                f.write(b"fake_proxy_data" * 100)
            
            # Create high-res proxy files
            lgprx_file = os.path.join(bpav_dir, "LGPRX", f"{clip_name}.MP4")
            with open(lgprx_file, "wb") as f:
                f.write(b"fake_hires_proxy_data" * 200)
            
            # Create thumbnail files
            icon_file = os.path.join(bpav_dir, "ICON", f"{clip_name}.BMP")
            with open(icon_file, "wb") as f:
                f.write(b"fake_thumbnail_data" * 50)
        
        yield temp_dir


@pytest.fixture
def xdcam_handler():
    """Create an XDCAM card handler instance"""
    return XDCAMCardHandler()


class TestXDCAMCardHandler:
    """Test suite for XDCAM card handler"""
    
    @pytest.mark.asyncio
    async def test_detect_xdcam_card(self, mock_xdcam_card_structure):
        """Test XDCAM card detection"""
        service = CameraCardService()
        card_type = await service.detect_card_type(mock_xdcam_card_structure)
        assert card_type == CameraCardType.XDCAM
    
    @pytest.mark.asyncio
    async def test_analyze_xdcam_card(self, xdcam_handler, mock_xdcam_card_structure):
        """Test XDCAM card analysis"""
        card_info = await xdcam_handler.analyze_card(mock_xdcam_card_structure)
        
        assert card_info is not None
        assert card_info.card_type == CameraCardType.XDCAM
        assert card_info.card_path == mock_xdcam_card_structure
        assert len(card_info.clips) == 3
        assert card_info.total_files == 3
        assert card_info.total_size > 0
        
        # Check metadata
        assert "SerialNumber" in card_info.metadata
        assert card_info.metadata["SerialNumber"] == "XDCAM001234"
        assert "disc_Label" in card_info.metadata
        assert card_info.metadata["disc_Label"] == "XDCAM_001"
        
        # Check first clip
        first_clip = card_info.clips[0]
        assert first_clip.clip_name.startswith("C")
        assert first_clip.file_path.endswith(".MXF")
        assert first_clip.file_size > 0
        assert first_clip.proxy_path is not None
        assert first_clip.audio_path is None  # XDCAM audio is embedded
        assert first_clip.thumbnail_path is not None
    
    @pytest.mark.asyncio
    async def test_xdcam_metadata_extraction(self, xdcam_handler, mock_xdcam_card_structure):
        """Test XDCAM metadata extraction from XML files"""
        metadata = await xdcam_handler._read_xdcam_metadata(mock_xdcam_card_structure)
        
        assert "SerialNumber" in metadata
        assert metadata["SerialNumber"] == "XDCAM001234"
        assert "Model" in metadata
        assert metadata["Model"] == "PMW-F5"
        
        # Disc info should be prefixed with 'disc_'
        assert "disc_Label" in metadata
        assert metadata["disc_Label"] == "XDCAM_001"
        assert "disc_Format" in metadata
        assert metadata["disc_Format"] == "XDCAM HD"
    
    @pytest.mark.asyncio
    async def test_xdcam_clip_detection(self, xdcam_handler, mock_xdcam_card_structure):
        """Test XDCAM clip detection and analysis"""
        clpr_path = os.path.join(mock_xdcam_card_structure, "BPAV", "CLPR")
        bpav_path = os.path.join(mock_xdcam_card_structure, "BPAV")
        
        clips = await xdcam_handler._find_xdcam_clips(clpr_path, bpav_path)
        
        assert len(clips) == 3
        
        for clip in clips:
            assert clip.clip_name.startswith("C")
            assert clip.file_path.endswith(".MXF")
            assert clip.file_size > 0
            assert clip.proxy_path is not None
            assert os.path.exists(clip.proxy_path)
            assert clip.thumbnail_path is not None
            assert os.path.exists(clip.thumbnail_path)
            assert clip.audio_path is None  # XDCAM audio is embedded
    
    @pytest.mark.asyncio
    async def test_xdcam_clip_metadata_parsing(self, xdcam_handler, mock_xdcam_card_structure):
        """Test XDCAM clip metadata parsing from XML"""
        clipmeta_path = os.path.join(mock_xdcam_card_structure, "BPAV", "CLIPMETA")
        xml_files = [f for f in os.listdir(clipmeta_path) if f.endswith('.XML')]
        
        assert len(xml_files) > 0
        
        xml_path = os.path.join(clipmeta_path, xml_files[0])
        metadata = await xdcam_handler._read_xdcam_clip_metadata(xml_path)
        
        assert "clipname" in metadata or "ClipName" in metadata
        assert "duration" in metadata or "Duration" in metadata
        assert "codec" in metadata or "EssenceType" in metadata
    
    @pytest.mark.asyncio
    async def test_xdcam_proxy_preference(self, xdcam_handler, mock_xdcam_card_structure):
        """Test XDCAM proxy file preference (SMLPRX over LGPRX)"""
        bpav_path = os.path.join(mock_xdcam_card_structure, "BPAV")
        
        # Test with both SMLPRX and LGPRX existing
        clip_info = await xdcam_handler._analyze_xdcam_clip(
            "C0000001.MXF",
            os.path.join(bpav_path, "CLPR"),
            bpav_path
        )
        
        assert clip_info is not None
        assert clip_info.proxy_path is not None
        # Should prefer SMLPRX
        assert "SMLPRX" in clip_info.proxy_path
        
        # Test fallback to LGPRX when SMLPRX doesn't exist
        smlprx_file = os.path.join(bpav_path, "SMLPRX", "C0000001.MP4")
        os.remove(smlprx_file)
        
        clip_info = await xdcam_handler._analyze_xdcam_clip(
            "C0000001.MXF",
            os.path.join(bpav_path, "CLPR"),
            bpav_path
        )
        
        assert clip_info is not None
        assert clip_info.proxy_path is not None
        # Should fall back to LGPRX
        assert "LGPRX" in clip_info.proxy_path
    
    @pytest.mark.asyncio
    async def test_create_xdcam_ingest_jobs(self, xdcam_handler, mock_xdcam_card_structure):
        """Test creating ingest jobs for XDCAM card"""
        # First analyze the card
        card_info = await xdcam_handler.analyze_card(mock_xdcam_card_structure)
        
        # Create ingest jobs
        jobs = await xdcam_handler.create_ingest_jobs(card_info, "test-project-123")
        
        # Should have jobs for main clips plus proxy files
        # 3 clips * (1 main + 1 proxy) = 6 jobs
        assert len(jobs) == 6
        
        # Group jobs by type
        main_jobs = [j for j in jobs if "file_type" not in j.metadata_override]
        proxy_jobs = [j for j in jobs if j.metadata_override.get("file_type") == "proxy"]
        
        assert len(main_jobs) == 3
        assert len(proxy_jobs) == 3
        
        # Verify main job properties
        main_job = main_jobs[0]
        assert main_job.source_path.endswith(".MXF")
        assert main_job.destination_project_id == "test-project-123"
        assert main_job.ingest_type == IngestType.CAMERA_CARD
        assert main_job.priority == IngestPriority.HIGH
        assert main_job.auto_generate_proxies == True
        assert "XDCAM" in main_job.tags
        assert "sony" in main_job.tags
        
        # Verify metadata
        assert main_job.metadata_override["camera_card_type"] == "XDCAM"
        assert "clip_name" in main_job.metadata_override
        assert "card_metadata" in main_job.metadata_override
        assert "clip_metadata" in main_job.metadata_override
        
        # Verify proxy job properties
        proxy_job = proxy_jobs[0]
        assert proxy_job.source_path.endswith(".MP4")
        assert proxy_job.priority == IngestPriority.NORMAL
        assert proxy_job.auto_generate_proxies == False
        assert proxy_job.metadata_override["file_type"] == "proxy"
    
    @pytest.mark.asyncio
    async def test_analyze_invalid_xdcam_card(self, xdcam_handler):
        """Test analyzing invalid XDCAM card structure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create fake XDCAM structure but without proper BPAV folder
            os.makedirs(os.path.join(temp_dir, "FAKE_FOLDER"))
            
            with pytest.raises(CameraCardError, match="Invalid XDCAM card structure"):
                await xdcam_handler.analyze_card(temp_dir)
    
    @pytest.mark.asyncio
    async def test_xdcam_missing_metadata_files(self, xdcam_handler, mock_xdcam_card_structure):
        """Test XDCAM card analysis when metadata files are missing"""
        # Remove XDROOT.XML
        xdroot_path = os.path.join(mock_xdcam_card_structure, "XDROOT.XML")
        if os.path.exists(xdroot_path):
            os.remove(xdroot_path)
        
        # Should still work but with limited metadata
        card_info = await xdcam_handler.analyze_card(mock_xdcam_card_structure)
        
        assert card_info is not None
        assert card_info.card_type == CameraCardType.XDCAM
        assert len(card_info.clips) == 3
        
        # Should have disc metadata but not card metadata
        assert "disc_Label" in card_info.metadata
        assert "SerialNumber" not in card_info.metadata
    
    @pytest.mark.asyncio
    async def test_xdcam_missing_proxy_files(self, xdcam_handler, mock_xdcam_card_structure):
        """Test XDCAM card analysis when proxy files are missing"""
        # Remove some proxy files to test graceful handling
        bpav_dir = os.path.join(mock_xdcam_card_structure, "BPAV")
        smlprx_dir = os.path.join(bpav_dir, "SMLPRX")
        lgprx_dir = os.path.join(bpav_dir, "LGPRX")
        
        # Remove one low-res and one high-res proxy file
        smlprx_files = os.listdir(smlprx_dir)
        lgprx_files = os.listdir(lgprx_dir)
        
        if smlprx_files:
            os.remove(os.path.join(smlprx_dir, smlprx_files[0]))
        if lgprx_files:
            os.remove(os.path.join(lgprx_dir, lgprx_files[0]))
        
        card_info = await xdcam_handler.analyze_card(mock_xdcam_card_structure)
        
        # Should still work, but some clips won't have proxy files
        assert card_info is not None
        assert len(card_info.clips) == 3
        
        # Check that missing files are handled gracefully
        clips_with_proxy = [c for c in card_info.clips if c.proxy_path and os.path.exists(c.proxy_path)]
        assert len(clips_with_proxy) >= 1  # At least some should have proxies


class TestXDCAMIntegration:
    """Integration tests for XDCAM functionality"""
    
    @pytest.mark.asyncio
    async def test_full_xdcam_workflow(self, mock_xdcam_card_structure):
        """Test complete XDCAM card workflow from detection to job creation"""
        service = CameraCardService()
        
        # Step 1: Detect card type
        card_type = await service.detect_card_type(mock_xdcam_card_structure)
        assert card_type == CameraCardType.XDCAM
        
        # Step 2: Analyze card
        card_info = await service.analyze_card(mock_xdcam_card_structure)
        assert card_info is not None
        assert card_info.card_type == CameraCardType.XDCAM
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
    async def test_xdcam_vs_p2_detection(self):
        """Test that XDCAM and P2 cards are distinguished correctly"""
        service = CameraCardService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create XDCAM structure
            xdcam_dir = os.path.join(temp_dir, "xdcam")
            os.makedirs(os.path.join(xdcam_dir, "BPAV"))
            with open(os.path.join(xdcam_dir, "XDROOT.XML"), "w") as f:
                f.write("<root></root>")
            
            # Create P2 structure
            p2_dir = os.path.join(temp_dir, "p2")
            os.makedirs(os.path.join(p2_dir, "CONTENTS", "CLIP"))
            
            # Test detection
            xdcam_type = await service.detect_card_type(xdcam_dir)
            p2_type = await service.detect_card_type(p2_dir)
            
            assert xdcam_type == CameraCardType.XDCAM
            assert p2_type == CameraCardType.P2
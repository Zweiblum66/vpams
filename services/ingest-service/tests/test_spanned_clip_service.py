"""
Tests for the Spanned Clip Service
"""

import pytest
import os
import tempfile
from datetime import datetime
from pathlib import Path

from src.services.spanned_clip_service import SpannedClipService
from src.models.schemas import SpannedClipInfo, FileMetadata, FileType
from src.core.exceptions import SpannedClipError


@pytest.fixture
def spanned_clip_service():
    """Create a spanned clip service instance"""
    return SpannedClipService()


@pytest.fixture
def mock_spanned_files():
    """Create mock spanned clip files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a set of spanned files with different patterns
        test_files = []
        
        # Pattern 1: filename_001.ext, filename_002.ext
        for i in range(1, 4):
            file_path = os.path.join(temp_dir, f"clip_A_{i:03d}.MXF")
            with open(file_path, "wb") as f:
                f.write(b"fake_video_data" * 1000)  # Create some fake data
            test_files.append(file_path)
        
        # Pattern 2: filenameA001.ext, filenameA002.ext
        for i in range(1, 3):
            file_path = os.path.join(temp_dir, f"clipB{i:03d}.MOV")
            with open(file_path, "wb") as f:
                f.write(b"fake_video_data" * 800)
            test_files.append(file_path)
        
        # Pattern 3: Professional camera pattern C0001A01.MXF
        for i in range(1, 5):
            file_path = os.path.join(temp_dir, f"C0001A{i:02d}.MXF")
            with open(file_path, "wb") as f:
                f.write(b"fake_mxf_data" * 1200)
            test_files.append(file_path)
        
        # Pattern 4: Incomplete sequence (missing middle file)
        file_path = os.path.join(temp_dir, "incomplete_001.MP4")
        with open(file_path, "wb") as f:
            f.write(b"fake_data" * 500)
        test_files.append(file_path)
        
        file_path = os.path.join(temp_dir, "incomplete_003.MP4")
        with open(file_path, "wb") as f:
            f.write(b"fake_data" * 500)
        test_files.append(file_path)
        
        # Single file (should not be detected as spanned)
        file_path = os.path.join(temp_dir, "single_file.MOV")
        with open(file_path, "wb") as f:
            f.write(b"single_file_data" * 600)
        test_files.append(file_path)
        
        # Non-video file (should be ignored)
        file_path = os.path.join(temp_dir, "document_001.txt")
        with open(file_path, "w") as f:
            f.write("This is a text document")
        test_files.append(file_path)
        
        yield test_files


class TestSpannedClipService:
    """Test suite for spanned clip service"""
    
    @pytest.mark.asyncio
    async def test_detect_spanned_clips(self, spanned_clip_service, mock_spanned_files):
        """Test basic spanned clip detection"""
        spanned_clips = await spanned_clip_service.detect_spanned_clips(mock_spanned_files)
        
        # Should detect multiple spanned clips
        assert len(spanned_clips) >= 3
        
        # Check specific clips
        clip_names = list(spanned_clips.keys())
        
        # Should find the clip_A pattern
        clip_a_found = any("clip_a" in name.lower() for name in clip_names)
        assert clip_a_found
        
        # Should find the C0001A pattern
        c0001_found = any("c0001a" in name.lower() for name in clip_names)
        assert c0001_found
    
    @pytest.mark.asyncio
    async def test_complete_vs_incomplete_sequences(self, spanned_clip_service, mock_spanned_files):
        """Test detection of complete vs incomplete sequences"""
        spanned_clips = await spanned_clip_service.detect_spanned_clips(mock_spanned_files)
        
        # Find the incomplete sequence
        incomplete_clip = None
        for clip_name, clip_info in spanned_clips.items():
            if "incomplete" in clip_name.lower():
                incomplete_clip = clip_info
                break
        
        # Should detect incomplete sequence
        assert incomplete_clip is not None
        assert incomplete_clip.is_complete == False
        assert incomplete_clip.total_spans > len(incomplete_clip.related_files)
    
    @pytest.mark.asyncio
    async def test_spanned_clip_info_structure(self, spanned_clip_service, mock_spanned_files):
        """Test that SpannedClipInfo objects are properly structured"""
        spanned_clips = await spanned_clip_service.detect_spanned_clips(mock_spanned_files)
        
        for clip_name, clip_info in spanned_clips.items():
            # Basic structure validation
            assert isinstance(clip_info, SpannedClipInfo)
            assert isinstance(clip_info.clip_id, str)
            assert isinstance(clip_info.span_index, int)
            assert isinstance(clip_info.total_spans, int)
            assert isinstance(clip_info.is_complete, bool)
            assert isinstance(clip_info.related_files, list)
            
            # Logical validation
            assert clip_info.total_spans > 0
            assert len(clip_info.related_files) > 0
            assert clip_info.total_spans >= len(clip_info.related_files)
            
            # File existence validation
            for file_path in clip_info.related_files:
                assert os.path.exists(file_path)
    
    @pytest.mark.asyncio
    async def test_pattern_recognition(self, spanned_clip_service):
        """Test different span pattern recognition"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test different patterns
            patterns_to_test = [
                ["video_001.MXF", "video_002.MXF", "video_003.MXF"],  # underscore
                ["clipA001.MOV", "clipA002.MOV"],  # letter+number
                ["test-001.MP4", "test-002.MP4"],  # dash
                ["file(001).AVI", "file(002).AVI"],  # parentheses
                ["shot.001.MKV", "shot.002.MKV"],  # dots
                ["C0001A01.MXF", "C0001A02.MXF", "C0001A03.MXF"],  # professional pattern
                ["CLIP001_01.R3D", "CLIP001_02.R3D"]  # underscore with prefix
            ]
            
            all_files = []
            for pattern in patterns_to_test:
                for filename in pattern:
                    file_path = os.path.join(temp_dir, filename)
                    with open(file_path, "wb") as f:
                        f.write(b"test_data" * 100)
                    all_files.append(file_path)
            
            spanned_clips = await spanned_clip_service.detect_spanned_clips(all_files)
            
            # Should detect all patterns
            assert len(spanned_clips) == len(patterns_to_test)
    
    @pytest.mark.asyncio
    async def test_validate_spanned_clip(self, spanned_clip_service, mock_spanned_files):
        """Test spanned clip validation"""
        spanned_clips = await spanned_clip_service.detect_spanned_clips(mock_spanned_files)
        
        for clip_name, clip_info in spanned_clips.items():
            is_valid = await spanned_clip_service.validate_spanned_clip(clip_info)
            
            if clip_info.is_complete:
                assert is_valid == True
            # Note: incomplete clips can still be valid if all existing files are present
    
    @pytest.mark.asyncio
    async def test_get_primary_file(self, spanned_clip_service, mock_spanned_files):
        """Test getting primary file from spanned clip"""
        spanned_clips = await spanned_clip_service.detect_spanned_clips(mock_spanned_files)
        
        for clip_name, clip_info in spanned_clips.items():
            primary_file = await spanned_clip_service.get_primary_file(clip_info)
            
            assert primary_file is not None
            assert primary_file in clip_info.related_files
            assert os.path.exists(primary_file)
            
            # Primary file should be the first in sorted order
            sorted_files = sorted(clip_info.related_files)
            assert primary_file == sorted_files[0]
    
    @pytest.mark.asyncio
    async def test_merge_spanned_metadata(self, spanned_clip_service):
        """Test merging metadata from spanned clips"""
        # Create mock FileMetadata objects
        file_metadata_list = [
            FileMetadata(
                filename="clip_001.MXF",
                file_size=1000000,
                file_type=FileType.VIDEO,
                mime_type="application/mxf",
                extension=".MXF",
                created_at=datetime.now(),
                modified_at=datetime.now()
            ),
            FileMetadata(
                filename="clip_002.MXF",
                file_size=950000,
                file_type=FileType.VIDEO,
                mime_type="application/mxf",
                extension=".MXF",
                created_at=datetime.now(),
                modified_at=datetime.now()
            )
        ]
        
        span_info = SpannedClipInfo(
            clip_id="test_clip_001",
            span_index=1,
            total_spans=2,
            is_complete=True,
            related_files=["/path/to/clip_001.MXF", "/path/to/clip_002.MXF"]
        )
        
        merged_metadata = await spanned_clip_service.merge_spanned_metadata(
            span_info,
            file_metadata_list
        )
        
        # Validate merged metadata structure
        assert merged_metadata["clip_id"] == "test_clip_001"
        assert merged_metadata["total_spans"] == 2
        assert merged_metadata["is_complete"] == True
        assert merged_metadata["total_size"] == 1950000
        assert len(merged_metadata["span_metadata"]) == 2
        
        # Check span metadata
        for i, span_meta in enumerate(merged_metadata["span_metadata"]):
            assert span_meta["span_index"] == i + 1
            assert span_meta["filename"] == file_metadata_list[i].filename
            assert span_meta["file_size"] == file_metadata_list[i].file_size
    
    @pytest.mark.asyncio
    async def test_empty_file_list(self, spanned_clip_service):
        """Test handling empty file list"""
        spanned_clips = await spanned_clip_service.detect_spanned_clips([])
        assert len(spanned_clips) == 0
    
    @pytest.mark.asyncio
    async def test_non_video_files_ignored(self, spanned_clip_service):
        """Test that non-video files are ignored"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create non-video files with span patterns
            test_files = []
            for i in range(1, 4):
                file_path = os.path.join(temp_dir, f"document_{i:03d}.txt")
                with open(file_path, "w") as f:
                    f.write("This is a text document")
                test_files.append(file_path)
            
            spanned_clips = await spanned_clip_service.detect_spanned_clips(test_files)
            assert len(spanned_clips) == 0
    
    @pytest.mark.asyncio
    async def test_mixed_extensions_not_grouped(self, spanned_clip_service):
        """Test that files with different extensions are not grouped together"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_files = []
            
            # Create files with same base name but different extensions
            file_path1 = os.path.join(temp_dir, "clip_001.MXF")
            with open(file_path1, "wb") as f:
                f.write(b"mxf_data" * 100)
            test_files.append(file_path1)
            
            file_path2 = os.path.join(temp_dir, "clip_002.MOV")
            with open(file_path2, "wb") as f:
                f.write(b"mov_data" * 100)
            test_files.append(file_path2)
            
            spanned_clips = await spanned_clip_service.detect_spanned_clips(test_files)
            
            # Should not group files with different extensions
            assert len(spanned_clips) == 0
    
    @pytest.mark.asyncio
    async def test_single_span_not_detected(self, spanned_clip_service):
        """Test that single files are not detected as spanned clips"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create single file with span-like name
            file_path = os.path.join(temp_dir, "clip_001.MXF")
            with open(file_path, "wb") as f:
                f.write(b"single_file_data" * 100)
            
            spanned_clips = await spanned_clip_service.detect_spanned_clips([file_path])
            assert len(spanned_clips) == 0


class TestSpannedClipPatterns:
    """Test specific span pattern recognition"""
    
    @pytest.mark.asyncio
    async def test_professional_camera_patterns(self, spanned_clip_service):
        """Test patterns commonly used by professional cameras"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # RED camera pattern
            red_files = []
            for i in range(1, 4):
                file_path = os.path.join(temp_dir, f"A001_C001_{i:06d}.R3D")
                with open(file_path, "wb") as f:
                    f.write(b"red_data" * 500)
                red_files.append(file_path)
            
            # Blackmagic pattern
            braw_files = []
            for i in range(1, 3):
                file_path = os.path.join(temp_dir, f"shot_{i:03d}.BRAW")
                with open(file_path, "wb") as f:
                    f.write(b"braw_data" * 400)
                braw_files.append(file_path)
            
            all_files = red_files + braw_files
            spanned_clips = await spanned_clip_service.detect_spanned_clips(all_files)
            
            # Should detect at least the BRAW sequence
            assert len(spanned_clips) >= 1
    
    @pytest.mark.asyncio
    async def test_edge_cases(self, spanned_clip_service):
        """Test edge cases in pattern recognition"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Very high span numbers
            high_span_files = []
            for i in [1, 999, 1000]:
                file_path = os.path.join(temp_dir, f"clip_{i:03d}.MXF")
                with open(file_path, "wb") as f:
                    f.write(b"data" * 100)
                high_span_files.append(file_path)
            
            spanned_clips = await spanned_clip_service.detect_spanned_clips(high_span_files)
            
            # Should handle high span numbers
            for clip_info in spanned_clips.values():
                assert clip_info.total_spans > 900  # Large gap in sequence
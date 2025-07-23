"""
Tests for FFprobe Extractor

Test cases for the FFprobe video metadata extraction functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from src.services.ffprobe_extractor import FFprobeExtractor
from src.core.exceptions import ExtractionError


class TestFFprobeExtractor:
    """Test cases for FFprobeExtractor"""

    @pytest.fixture
    def extractor(self):
        """Create an FFprobeExtractor instance"""
        return FFprobeExtractor()

    @pytest.fixture
    def mock_ffprobe_result(self):
        """Mock FFprobe result data"""
        return {
            "format": {
                "filename": "/test/video.mp4",
                "nb_streams": 2,
                "nb_programs": 0,
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                "format_long_name": "QuickTime / MOV",
                "start_time": "0.000000",
                "duration": "10.000000",
                "size": "1048576",
                "bit_rate": "838860",
                "probe_score": 100,
                "tags": {
                    "major_brand": "isom",
                    "minor_version": "512",
                    "compatible_brands": "isomiso2avc1mp41",
                    "creation_time": "2024-01-01T12:00:00.000000Z",
                    "encoder": "Lavf58.76.100"
                }
            },
            "streams": [
                {
                    "index": 0,
                    "codec_name": "h264",
                    "codec_long_name": "H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
                    "profile": "High",
                    "codec_type": "video",
                    "codec_tag_string": "avc1",
                    "codec_tag": "0x31637661",
                    "width": 1920,
                    "height": 1080,
                    "coded_width": 1920,
                    "coded_height": 1080,
                    "closed_captions": 0,
                    "film_grain": 0,
                    "has_b_frames": 2,
                    "sample_aspect_ratio": "1:1",
                    "display_aspect_ratio": "16:9",
                    "pix_fmt": "yuv420p",
                    "level": 40,
                    "color_range": "tv",
                    "color_space": "bt709",
                    "color_transfer": "bt709",
                    "color_primaries": "bt709",
                    "chroma_location": "left",
                    "field_order": "progressive",
                    "refs": 1,
                    "r_frame_rate": "30/1",
                    "avg_frame_rate": "30/1",
                    "time_base": "1/15360",
                    "start_pts": 0,
                    "start_time": "0.000000",
                    "duration_ts": 153600,
                    "duration": "10.000000",
                    "bit_rate": "716800",
                    "nb_frames": "300",
                    "disposition": {
                        "default": 1,
                        "dub": 0,
                        "original": 0,
                        "comment": 0,
                        "lyrics": 0,
                        "karaoke": 0,
                        "forced": 0,
                        "hearing_impaired": 0,
                        "visual_impaired": 0,
                        "clean_effects": 0,
                        "attached_pic": 0,
                        "timed_thumbnails": 0
                    },
                    "tags": {
                        "language": "und",
                        "handler_name": "VideoHandler",
                        "vendor_id": "[0][0][0][0]"
                    }
                },
                {
                    "index": 1,
                    "codec_name": "aac",
                    "codec_long_name": "AAC (Advanced Audio Coding)",
                    "profile": "LC",
                    "codec_type": "audio",
                    "codec_tag_string": "mp4a",
                    "codec_tag": "0x6134706d",
                    "sample_fmt": "fltp",
                    "sample_rate": "48000",
                    "channels": 2,
                    "channel_layout": "stereo",
                    "bits_per_sample": 0,
                    "r_frame_rate": "0/0",
                    "avg_frame_rate": "0/0",
                    "time_base": "1/48000",
                    "start_pts": 0,
                    "start_time": "0.000000",
                    "duration_ts": 480000,
                    "duration": "10.000000",
                    "bit_rate": "122060",
                    "nb_frames": "469",
                    "disposition": {
                        "default": 1,
                        "dub": 0,
                        "original": 0,
                        "comment": 0,
                        "lyrics": 0,
                        "karaoke": 0,
                        "forced": 0,
                        "hearing_impaired": 0,
                        "visual_impaired": 0,
                        "clean_effects": 0,
                        "attached_pic": 0,
                        "timed_thumbnails": 0
                    },
                    "tags": {
                        "language": "und",
                        "handler_name": "SoundHandler",
                        "vendor_id": "[0][0][0][0]"
                    }
                }
            ],
            "chapters": []
        }

    def test_is_supported_format(self, extractor):
        """Test format support detection"""
        # Video formats
        assert extractor.is_supported_format("test.mp4") == True
        assert extractor.is_supported_format("test.avi") == True
        assert extractor.is_supported_format("test.MOV") == True
        assert extractor.is_supported_format("test.mkv") == True
        assert extractor.is_supported_format("test.webm") == True
        
        # Audio formats
        assert extractor.is_supported_format("test.mp3") == True
        assert extractor.is_supported_format("test.aac") == True
        assert extractor.is_supported_format("test.WAV") == True
        assert extractor.is_supported_format("test.flac") == True
        
        # Unsupported formats
        assert extractor.is_supported_format("test.jpg") == False
        assert extractor.is_supported_format("test.txt") == False
        assert extractor.is_supported_format("test.pdf") == False

    @pytest.mark.asyncio
    async def test_check_ffprobe_availability(self, extractor):
        """Test FFprobe availability check"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock successful FFprobe check
            mock_process = Mock()
            mock_process.wait = AsyncMock(return_value=None)
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            result = await extractor.check_ffprobe_availability()
            assert result == True
            
            # Mock failed FFprobe check
            mock_process.returncode = 1
            result = await extractor.check_ffprobe_availability()
            assert result == False

    @pytest.mark.asyncio
    async def test_extract_video_metadata_success(self, extractor, mock_ffprobe_result):
        """Test successful video metadata extraction"""
        test_file = "/test/video.mp4"
        
        with patch('os.path.exists', return_value=True), \
             patch.object(extractor, 'check_ffprobe_availability', return_value=True), \
             patch.object(extractor, '_extract_metadata_sync', return_value=mock_ffprobe_result):
            
            result = await extractor.extract_video_metadata(test_file)
            
            # Check structure
            assert isinstance(result, dict)
            assert 'file_info' in result
            assert 'format' in result
            assert 'streams' in result
            assert 'video_streams' in result
            assert 'audio_streams' in result
            assert 'derived_info' in result
            assert 'technical_summary' in result
            
            # Check format info
            format_info = result['format']
            assert format_info['duration'] == 10.0
            assert format_info['size'] == 1048576
            assert format_info['bit_rate'] == 838860
            
            # Check streams
            assert len(result['streams']) == 2
            assert len(result['video_streams']) == 1
            assert len(result['audio_streams']) == 1
            
            # Check video stream
            video_stream = result['video_streams'][0]
            assert video_stream['codec_name'] == 'h264'
            assert video_stream['width'] == 1920
            assert video_stream['height'] == 1080
            assert video_stream['resolution'] == '1920x1080'
            assert video_stream['frame_rate'] == 30.0
            
            # Check audio stream
            audio_stream = result['audio_streams'][0]
            assert audio_stream['codec_name'] == 'aac'
            assert audio_stream['sample_rate'] == 48000
            assert audio_stream['channels'] == 2
            
            # Check derived info
            derived_info = result['derived_info']
            assert derived_info['is_video'] == True
            assert derived_info['has_audio'] == True
            assert derived_info['has_video'] == True
            assert derived_info['stream_count']['video'] == 1
            assert derived_info['stream_count']['audio'] == 1

    @pytest.mark.asyncio
    async def test_extract_video_metadata_file_not_found(self, extractor):
        """Test extraction with non-existent file"""
        with patch('os.path.exists', return_value=False):
            with pytest.raises(ExtractionError) as exc_info:
                await extractor.extract_video_metadata("/nonexistent/file.mp4")
            
            assert "File not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_video_metadata_unsupported_format(self, extractor):
        """Test extraction with unsupported format"""
        with patch('os.path.exists', return_value=True):
            with pytest.raises(ExtractionError) as exc_info:
                await extractor.extract_video_metadata("/test/file.txt")
            
            assert "Unsupported file format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_video_metadata_ffprobe_unavailable(self, extractor):
        """Test extraction when FFprobe is not available"""
        with patch('os.path.exists', return_value=True), \
             patch.object(extractor, 'check_ffprobe_availability', return_value=False):
            
            with pytest.raises(ExtractionError) as exc_info:
                await extractor.extract_video_metadata("/test/video.mp4")
            
            assert "FFprobe not available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_batch(self, extractor, mock_ffprobe_result):
        """Test batch video metadata extraction"""
        file_paths = ["/test/video1.mp4", "/test/video2.mp4"]
        
        with patch('os.path.exists', return_value=True), \
             patch.object(extractor, 'check_ffprobe_availability', return_value=True), \
             patch.object(extractor, '_extract_metadata_sync', return_value=mock_ffprobe_result):
            
            results = await extractor.extract_batch(file_paths)
            
            assert isinstance(results, dict)
            assert len(results) == 2
            
            # Check successful extractions
            for file_path in file_paths:
                assert file_path in results
                result = results[file_path]
                assert 'file_info' in result
                assert 'format' in result
                assert 'streams' in result

    @pytest.mark.asyncio
    async def test_extract_batch_with_errors(self, extractor, mock_ffprobe_result):
        """Test batch extraction with some files failing"""
        file_paths = ["/test/video1.mp4", "/nonexistent/video2.mp4"]
        
        def mock_exists(path):
            return path == "/test/video1.mp4"
        
        with patch('os.path.exists', side_effect=mock_exists), \
             patch.object(extractor, 'check_ffprobe_availability', return_value=True), \
             patch.object(extractor, '_extract_metadata_sync', return_value=mock_ffprobe_result):
            
            results = await extractor.extract_batch(file_paths)
            
            assert isinstance(results, dict)
            assert len(results) == 2
            
            # Check successful extraction
            assert 'file_info' in results["/test/video1.mp4"]
            
            # Check failed extraction
            failed_result = results["/nonexistent/video2.mp4"]
            assert 'error' in failed_result
            assert failed_result['file_info']['success'] == False

    def test_process_format_info(self, extractor, mock_ffprobe_result):
        """Test format information processing"""
        format_data = mock_ffprobe_result['format']
        
        result = extractor._process_format_info(format_data)
        
        assert result['filename'] == '/test/video.mp4'
        assert result['nb_streams'] == 2
        assert result['format_name'] == 'mov,mp4,m4a,3gp,3g2,mj2'
        assert result['duration'] == 10.0
        assert result['size'] == 1048576
        assert result['bit_rate'] == 838860
        assert 'metadata' in result

    def test_process_video_stream(self, extractor, mock_ffprobe_result):
        """Test video stream processing"""
        video_stream = mock_ffprobe_result['streams'][0]
        
        result = extractor._process_video_stream(video_stream)
        
        assert result['width'] == 1920
        assert result['height'] == 1080
        assert result['resolution'] == '1920x1080'
        assert result['aspect_ratio'] == 1.78
        assert result['frame_rate'] == 30.0
        assert result['total_pixels'] == 1920 * 1080
        assert result['pix_fmt'] == 'yuv420p'
        assert result['color_space'] == 'bt709'

    def test_process_audio_stream(self, extractor, mock_ffprobe_result):
        """Test audio stream processing"""
        audio_stream = mock_ffprobe_result['streams'][1]
        
        result = extractor._process_audio_stream(audio_stream)
        
        assert result['sample_rate'] == 48000
        assert result['channels'] == 2
        assert result['channel_layout'] == 'stereo'
        assert result['sample_fmt'] == 'fltp'

    def test_calculate_derived_info(self, extractor):
        """Test derived information calculation"""
        format_info = {'duration': 10.0, 'size': 1048576, 'nb_streams': 2}
        video_streams = [{'codec_name': 'h264', 'resolution': '1920x1080', 'frame_rate': 30.0}]
        audio_streams = [{'codec_name': 'aac', 'sample_rate': 48000, 'channels': 2}]
        
        result = extractor._calculate_derived_info(format_info, video_streams, audio_streams)
        
        assert result['is_video'] == True
        assert result['is_audio_only'] == False
        assert result['has_audio'] == True
        assert result['has_video'] == True
        assert result['stream_count']['video'] == 1
        assert result['stream_count']['audio'] == 1
        assert result['primary_video']['codec'] == 'h264'
        assert result['primary_video']['resolution'] == '1920x1080'
        assert result['primary_audio']['codec'] == 'aac'
        assert result['primary_audio']['sample_rate'] == 48000

    def test_safe_float(self, extractor):
        """Test safe float conversion"""
        assert extractor._safe_float("10.5") == 10.5
        assert extractor._safe_float(15) == 15.0
        assert extractor._safe_float("invalid") is None
        assert extractor._safe_float(None) is None

    def test_safe_int(self, extractor):
        """Test safe integer conversion"""
        assert extractor._safe_int("10") == 10
        assert extractor._safe_int(15.7) == 15
        assert extractor._safe_int("invalid") is None
        assert extractor._safe_int(None) is None

    def test_parse_frame_rate(self, extractor):
        """Test frame rate parsing"""
        assert extractor._parse_frame_rate("30/1") == 30.0
        assert extractor._parse_frame_rate("24000/1001") == pytest.approx(23.976, rel=1e-3)
        assert extractor._parse_frame_rate("29.97") == 29.97
        assert extractor._parse_frame_rate("invalid") is None
        assert extractor._parse_frame_rate("30/0") is None

    def test_format_duration(self, extractor):
        """Test duration formatting"""
        assert extractor._format_duration(3661.5) == "01:01:01"
        assert extractor._format_duration(125.0) == "00:02:05"
        assert extractor._format_duration(45.0) == "00:00:45"
        assert extractor._format_duration("invalid") == "00:00:00"

    def test_format_file_size(self, extractor):
        """Test file size formatting"""
        assert extractor._format_file_size(1024) == "1.0 KB"
        assert extractor._format_file_size(1048576) == "1.0 MB"
        assert extractor._format_file_size(1073741824) == "1.0 GB"
        assert extractor._format_file_size(500) == "500.0 B"
        assert extractor._format_file_size("invalid") == "0 B"

    def test_create_technical_summary(self, extractor):
        """Test technical summary creation"""
        format_info = {
            'format_name': 'mov,mp4',
            'duration': 10.0,
            'size': 1048576,
            'bit_rate': 838860
        }
        
        streams = [
            {'codec_type': 'video', 'codec_name': 'h264', 'resolution': '1920x1080', 'frame_rate': 30.0, 'bit_rate': 716800},
            {'codec_type': 'audio', 'codec_name': 'aac', 'sample_rate': 48000, 'channels': 2, 'bit_rate': 122060}
        ]
        
        result = extractor._create_technical_summary(format_info, streams)
        
        assert result['container'] == 'mov,mp4'
        assert result['duration'] == 10.0
        assert result['size'] == 1048576
        assert result['streams'] == 2
        assert result['video']['codec'] == 'h264'
        assert result['video']['resolution'] == '1920x1080'
        assert result['audio']['codec'] == 'aac'
        assert result['audio']['sample_rate'] == 48000

    @pytest.mark.asyncio
    async def test_get_video_thumbnail(self, extractor):
        """Test video thumbnail extraction (placeholder)"""
        # This is a placeholder method in the current implementation
        result = await extractor.get_video_thumbnail("/test/video.mp4", 1.0)
        assert result is None  # Current implementation returns None

    def test_process_metadata_tags(self, extractor):
        """Test metadata tags processing"""
        tags = {
            'title': 'Test Video',
            'ARTIST': 'Test Artist',
            'Creation_Time': '2024-01-01T12:00:00Z',
            'custom_tag': 'custom_value'
        }
        
        result = extractor._process_metadata_tags(tags)
        
        assert result['title'] == 'Test Video'
        assert result['artist'] == 'Test Artist'
        assert result['creation_time'] == '2024-01-01T12:00:00+00:00'
        assert result['custom_tag'] == 'custom_value'

    def test_process_chapters(self, extractor):
        """Test chapters processing"""
        chapters = [
            {
                'id': 0,
                'time_base': '1/1000',
                'start': 0,
                'start_time': '0.000',
                'end': 5000,
                'end_time': '5.000',
                'tags': {'title': 'Chapter 1'}
            },
            {
                'id': 1,
                'time_base': '1/1000',
                'start': 5000,
                'start_time': '5.000',
                'end': 10000,
                'end_time': '10.000',
                'tags': {'title': 'Chapter 2'}
            }
        ]
        
        result = extractor._process_chapters(chapters)
        
        assert len(result) == 2
        assert result[0]['id'] == 0
        assert result[0]['start_time'] == 0.0
        assert result[0]['end_time'] == 5.0
        assert result[0]['duration'] == 5.0
        assert result[0]['tags']['title'] == 'Chapter 1'
        assert result[1]['duration'] == 5.0
"""
Test Streaming Protocol Service

Tests for handling various streaming protocols (HLS, SRT, DASH, RTMP, RTSP).
"""

import pytest
import asyncio
import os
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import m3u8

from src.services.streaming_protocol_service import (
    StreamingProtocolService,
    HLSHandler,
    SRTHandler,
    DASHHandler,
    RTMPHandler,
    RTSPHandler
)
from src.core.exceptions import StreamingProtocolError


class TestStreamingProtocolService:
    """Test cases for StreamingProtocolService."""
    
    @pytest.fixture
    def service(self):
        """Create StreamingProtocolService instance."""
        return StreamingProtocolService()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def test_init(self, service):
        """Test service initialization."""
        assert 'hls' in service.supported_protocols
        assert 'srt' in service.supported_protocols
        assert 'dash' in service.supported_protocols
        assert 'rtmp' in service.supported_protocols
        assert 'rtsp' in service.supported_protocols
        
        assert service.segment_duration == 10
        assert service.playlist_size == 5
        assert service.buffer_size == 1024 * 1024
        assert service.timeout == 30
    
    async def test_ingest_stream_success(self, service, temp_dir):
        """Test successful stream ingestion."""
        stream_url = "http://example.com/stream.m3u8"
        destination_path = os.path.join(temp_dir, "output.mp4")
        
        # Mock HLS handler
        mock_result = {
            'protocol': 'hls',
            'status': 'completed',
            'output_path': destination_path
        }
        
        with patch.object(service.supported_protocols['hls'], 'ingest', return_value=mock_result):
            result = await service.ingest_stream(
                stream_url=stream_url,
                destination_path=destination_path,
                protocol='hls'
            )
            
            assert result == mock_result
    
    async def test_ingest_stream_auto_detect_protocol(self, service, temp_dir):
        """Test stream ingestion with automatic protocol detection."""
        stream_url = "http://example.com/stream.m3u8"
        destination_path = os.path.join(temp_dir, "output.mp4")
        
        # Mock HLS handler
        mock_result = {'protocol': 'hls', 'status': 'completed'}
        
        with patch.object(service, '_detect_protocol', return_value='hls'):
            with patch.object(service.supported_protocols['hls'], 'ingest', return_value=mock_result):
                result = await service.ingest_stream(
                    stream_url=stream_url,
                    destination_path=destination_path
                )
                
                assert result == mock_result
                service._detect_protocol.assert_called_once_with(stream_url)
    
    async def test_ingest_stream_unsupported_protocol(self, service, temp_dir):
        """Test stream ingestion with unsupported protocol."""
        stream_url = "unknown://example.com/stream"
        destination_path = os.path.join(temp_dir, "output.mp4")
        
        with pytest.raises(StreamingProtocolError, match="Unsupported protocol"):
            await service.ingest_stream(
                stream_url=stream_url,
                destination_path=destination_path,
                protocol='unknown'
            )
    
    async def test_ingest_stream_exception(self, service, temp_dir):
        """Test stream ingestion with exception."""
        stream_url = "http://example.com/stream.m3u8"
        destination_path = os.path.join(temp_dir, "output.mp4")
        
        with patch.object(
            service.supported_protocols['hls'],
            'ingest',
            side_effect=Exception("Ingest error")
        ):
            with pytest.raises(StreamingProtocolError, match="Stream ingest failed"):
                await service.ingest_stream(
                    stream_url=stream_url,
                    destination_path=destination_path,
                    protocol='hls'
                )
    
    async def test_convert_stream_format_success(self, service, temp_dir):
        """Test successful stream format conversion."""
        source_path = os.path.join(temp_dir, "input.mp4")
        output_format = 'hls'
        
        # Create source file
        Path(source_path).touch()
        
        expected_output = os.path.join(temp_dir, "output.m3u8")
        
        with patch.object(
            service.supported_protocols['hls'],
            'convert',
            return_value=expected_output
        ):
            result = await service.convert_stream_format(
                source_path=source_path,
                output_format=output_format
            )
            
            assert result == expected_output
    
    async def test_convert_stream_format_unsupported(self, service, temp_dir):
        """Test stream format conversion with unsupported format."""
        source_path = os.path.join(temp_dir, "input.mp4")
        
        with pytest.raises(StreamingProtocolError, match="Unsupported output format"):
            await service.convert_stream_format(
                source_path=source_path,
                output_format='unknown'
            )
    
    def test_detect_protocol_rtmp(self, service):
        """Test protocol detection for RTMP."""
        assert service._detect_protocol("rtmp://example.com/live/stream") == 'rtmp'
        assert service._detect_protocol("rtmps://example.com/live/stream") == 'rtmp'
    
    def test_detect_protocol_rtsp(self, service):
        """Test protocol detection for RTSP."""
        assert service._detect_protocol("rtsp://example.com:554/stream") == 'rtsp'
        assert service._detect_protocol("rtsps://example.com:554/stream") == 'rtsp'
    
    def test_detect_protocol_srt(self, service):
        """Test protocol detection for SRT."""
        assert service._detect_protocol("srt://example.com:9000") == 'srt'
    
    def test_detect_protocol_hls(self, service):
        """Test protocol detection for HLS."""
        assert service._detect_protocol("http://example.com/stream.m3u8") == 'hls'
        assert service._detect_protocol("https://example.com/stream.m3u8") == 'hls'
    
    def test_detect_protocol_dash(self, service):
        """Test protocol detection for DASH."""
        assert service._detect_protocol("http://example.com/manifest.mpd") == 'dash'
    
    def test_detect_protocol_default_http(self, service):
        """Test protocol detection default for HTTP."""
        assert service._detect_protocol("http://example.com/stream") == 'hls'
        assert service._detect_protocol("https://example.com/stream") == 'hls'
    
    def test_detect_protocol_unknown(self, service):
        """Test protocol detection for unknown URL."""
        with pytest.raises(StreamingProtocolError, match="Cannot detect protocol"):
            service._detect_protocol("unknown://example.com/stream")


class TestHLSHandler:
    """Test cases for HLSHandler."""
    
    @pytest.fixture
    def handler(self):
        """Create HLSHandler instance."""
        return HLSHandler()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_playlist(self):
        """Create mock M3U8 playlist."""
        playlist = Mock(spec=m3u8.M3U8)
        playlist.is_variant = False
        
        # Create mock segments
        segment1 = Mock()
        segment1.uri = "segment1.ts"
        segment1.duration = 10.0
        
        segment2 = Mock()
        segment2.uri = "segment2.ts"
        segment2.duration = 10.0
        
        playlist.segments = [segment1, segment2]
        return playlist
    
    @pytest.fixture
    def mock_variant_playlist(self):
        """Create mock variant playlist."""
        playlist = Mock(spec=m3u8.M3U8)
        playlist.is_variant = True
        
        # Create mock variant
        variant = Mock()
        variant.uri = "variant_720p.m3u8"
        variant.stream_info = Mock()
        variant.stream_info.bandwidth = 2000000
        
        playlist.playlists = [variant]
        return playlist
    
    async def test_ingest_media_playlist(self, handler, temp_dir, mock_playlist):
        """Test ingesting media playlist."""
        stream_url = "http://example.com/stream.m3u8"
        destination_path = os.path.join(temp_dir, "output.mp4")
        
        with patch('m3u8.load', return_value=mock_playlist):
            with patch.object(handler, '_download_segment', return_value=True):
                with patch.object(handler, '_concatenate_segments', new_callable=AsyncMock):
                    result = await handler.ingest(
                        stream_url=stream_url,
                        destination_path=destination_path,
                        options={'concatenate': True}
                    )
                    
                    assert result['protocol'] == 'hls'
                    assert result['segments_count'] == 2
                    assert result['total_duration'] == 20.0
                    assert result['output_path'] == destination_path
                    handler._concatenate_segments.assert_called_once()
    
    async def test_ingest_variant_playlist(self, handler, temp_dir, mock_variant_playlist, mock_playlist):
        """Test ingesting variant playlist."""
        stream_url = "http://example.com/master.m3u8"
        destination_path = os.path.join(temp_dir, "output.mp4")
        
        with patch('m3u8.load', side_effect=[mock_variant_playlist, mock_playlist]):
            with patch.object(handler, '_download_segment', return_value=True):
                with patch.object(handler, '_concatenate_segments', new_callable=AsyncMock):
                    result = await handler.ingest(
                        stream_url=stream_url,
                        destination_path=destination_path,
                        options={}
                    )
                    
                    assert result['protocol'] == 'hls'
                    assert result['segments_count'] == 2
    
    async def test_download_segment_success(self, handler, temp_dir):
        """Test successful segment download."""
        segment_url = "http://example.com/segment1.ts"
        destination = os.path.join(temp_dir, "segment1.ts")
        
        # Mock httpx response
        mock_response = Mock()
        mock_response.content = b"segment data"
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            with patch('aiofiles.open', new_callable=AsyncMock):
                result = await handler._download_segment(segment_url, destination)
                
                assert result is True
                mock_client.get.assert_called_once_with(segment_url, timeout=30.0)
    
    async def test_download_segment_failure(self, handler, temp_dir):
        """Test segment download failure."""
        segment_url = "http://example.com/segment1.ts"
        destination = os.path.join(temp_dir, "segment1.ts")
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Network error")
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await handler._download_segment(segment_url, destination)
            
            assert result is False
    
    async def test_concatenate_segments_success(self, handler, temp_dir):
        """Test successful segment concatenation."""
        segments = [
            {'path': os.path.join(temp_dir, 'seg1.ts'), 'duration': 10},
            {'path': os.path.join(temp_dir, 'seg2.ts'), 'duration': 10}
        ]
        output_path = os.path.join(temp_dir, "output.mp4")
        
        # Mock subprocess
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('aiofiles.open', new_callable=AsyncMock):
                with patch('pathlib.Path.unlink'):
                    await handler._concatenate_segments(segments, output_path)
    
    async def test_concatenate_segments_failure(self, handler, temp_dir):
        """Test segment concatenation failure."""
        segments = [{'path': 'seg1.ts', 'duration': 10}]
        output_path = os.path.join(temp_dir, "output.mp4")
        
        # Mock subprocess with error
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"FFmpeg error"))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('aiofiles.open', new_callable=AsyncMock):
                with pytest.raises(StreamingProtocolError, match="FFmpeg concatenation failed"):
                    await handler._concatenate_segments(segments, output_path)
    
    async def test_convert_to_hls(self, handler, temp_dir):
        """Test converting video to HLS format."""
        source_path = os.path.join(temp_dir, "input.mp4")
        Path(source_path).touch()
        
        # Mock subprocess
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await handler.convert(source_path, {})
            
            assert result.endswith("playlist.m3u8")
            assert "hls_output" in result


class TestSRTHandler:
    """Test cases for SRTHandler."""
    
    @pytest.fixture
    def handler(self):
        """Create SRTHandler instance."""
        return SRTHandler()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def test_ingest_success(self, handler, temp_dir):
        """Test successful SRT stream ingestion."""
        stream_url = "srt://example.com:9000"
        destination_path = os.path.join(temp_dir, "output.mp4")
        
        # Mock subprocess
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('datetime.datetime') as mock_datetime:
                mock_datetime.utcnow.side_effect = [
                    datetime(2024, 1, 1, 12, 0, 0),  # start
                    datetime(2024, 1, 1, 12, 0, 10)  # end
                ]
                
                result = await handler.ingest(
                    stream_url=stream_url,
                    destination_path=destination_path,
                    options={}
                )
                
                assert result['protocol'] == 'srt'
                assert result['status'] == 'completed'
                assert result['duration'] == 10.0
                assert result['output_path'] == destination_path
    
    async def test_ingest_with_options(self, handler, temp_dir):
        """Test SRT ingestion with options."""
        stream_url = "srt://example.com:9000"
        destination_path = os.path.join(temp_dir, "output.mp4")
        options = {
            'latency': 200,
            'passphrase': 'secret123'
        }
        
        # Mock subprocess
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
            result = await handler.ingest(
                stream_url=stream_url,
                destination_path=destination_path,
                options=options
            )
            
            # Verify options were included in command
            call_args = mock_exec.call_args[0]
            assert '-latency' in call_args
            assert '200' in call_args
            assert '-passphrase' in call_args
            assert 'secret123' in call_args
    
    async def test_ingest_timeout(self, handler, temp_dir):
        """Test SRT ingestion with timeout."""
        stream_url = "srt://example.com:9000"
        destination_path = os.path.join(temp_dir, "output.mp4")
        
        # Mock subprocess
        mock_process = Mock()
        mock_process.terminate = Mock()
        mock_process.wait = AsyncMock()
        mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
                result = await handler.ingest(
                    stream_url=stream_url,
                    destination_path=destination_path,
                    options={'timeout': 1}
                )
                
                assert result['protocol'] == 'srt'
                assert result['status'] == 'timeout'
                mock_process.terminate.assert_called_once()
    
    async def test_ingest_failure(self, handler, temp_dir):
        """Test SRT ingestion failure."""
        stream_url = "srt://example.com:9000"
        destination_path = os.path.join(temp_dir, "output.mp4")
        
        # Mock subprocess with error
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"SRT error"))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with pytest.raises(StreamingProtocolError, match="SRT ingest failed"):
                await handler.ingest(
                    stream_url=stream_url,
                    destination_path=destination_path,
                    options={}
                )
    
    async def test_convert_not_supported(self, handler):
        """Test that SRT conversion is not supported."""
        with pytest.raises(StreamingProtocolError, match="SRT is for live streaming only"):
            await handler.convert("/test/input.mp4", {})


class TestDASHHandler:
    """Test cases for DASHHandler."""
    
    @pytest.fixture
    def handler(self):
        """Create DASHHandler instance."""
        return DASHHandler()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def test_ingest_success(self, handler, temp_dir):
        """Test successful DASH stream ingestion."""
        stream_url = "http://example.com/manifest.mpd"
        destination_path = os.path.join(temp_dir, "output.mp4")
        
        # Mock subprocess
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await handler.ingest(
                stream_url=stream_url,
                destination_path=destination_path,
                options={}
            )
            
            assert result['protocol'] == 'dash'
            assert result['status'] == 'completed'
            assert result['output_path'] == destination_path
    
    async def test_ingest_failure(self, handler, temp_dir):
        """Test DASH ingestion failure."""
        stream_url = "http://example.com/manifest.mpd"
        destination_path = os.path.join(temp_dir, "output.mp4")
        
        # Mock subprocess with error
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"DASH error"))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with pytest.raises(StreamingProtocolError, match="DASH ingest failed"):
                await handler.ingest(
                    stream_url=stream_url,
                    destination_path=destination_path,
                    options={}
                )
    
    async def test_convert_to_dash(self, handler, temp_dir):
        """Test converting video to DASH format."""
        source_path = os.path.join(temp_dir, "input.mp4")
        Path(source_path).touch()
        
        # Mock subprocess
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await handler.convert(source_path, {})
            
            assert result.endswith("manifest.mpd")
            assert "dash_output" in result
    
    async def test_convert_failure(self, handler, temp_dir):
        """Test DASH conversion failure."""
        source_path = os.path.join(temp_dir, "input.mp4")
        
        # Mock subprocess with error
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Conversion error"))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with pytest.raises(StreamingProtocolError, match="DASH conversion failed"):
                await handler.convert(source_path, {})
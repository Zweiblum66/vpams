"""
Tests for GPU acceleration functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.services.ffmpeg_service import FFmpegService, GPUType, GPUCodec


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    settings = Mock()
    settings.ffmpeg_path = "ffmpeg"
    settings.ffprobe_path = "ffprobe"
    settings.ffmpeg_threads = 4
    settings.enable_gpu_acceleration = True
    settings.gpu_device = "0"
    settings.default_video_codec = "libx264"
    settings.default_audio_codec = "aac"
    settings.processing_timeout = 300
    settings.video_presets = {
        "medium": {
            "width": 1280,
            "height": 720,
            "video_bitrate": "1500k",
            "audio_bitrate": "128k",
            "framerate": 25,
            "preset": "fast",
            "gpu_preset": "p4",
            "max_bitrate": "2250k",
            "buffer_size": "3M"
        }
    }
    return settings


class TestGPUDetection:
    """Test GPU detection functionality"""
    
    @patch('shutil.which', return_value='/usr/bin/ffmpeg')
    @patch('src.services.ffmpeg_service.settings')
    def test_nvidia_gpu_detection(self, mock_settings_global, mock_which, mock_settings):
        """Test NVIDIA GPU detection"""
        mock_settings_global.ffmpeg_path = mock_settings.ffmpeg_path
        mock_settings_global.ffprobe_path = mock_settings.ffprobe_path
        mock_settings_global.ffmpeg_threads = mock_settings.ffmpeg_threads
        mock_settings_global.enable_gpu_acceleration = mock_settings.enable_gpu_acceleration
        mock_settings_global.gpu_device = mock_settings.gpu_device
        
        with patch('subprocess.run') as mock_run:
            # Mock nvidia-smi output
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "NVIDIA GeForce RTX 3080, 10240 MiB, 470.57.02"
            
            service = FFmpegService()
            service._detect_nvidia_gpu()
            
            assert service.gpu_type == GPUType.NVIDIA
            assert service.gpu_info["name"] == "NVIDIA GeForce RTX 3080"
            assert service.gpu_info["memory"] == "10240 MiB"
            assert service.gpu_info["driver_version"] == "470.57.02"
    
    @patch('shutil.which', return_value='/usr/bin/ffmpeg')
    @patch('src.services.ffmpeg_service.settings')
    def test_intel_gpu_detection(self, mock_settings_global, mock_which, mock_settings):
        """Test Intel GPU detection"""
        mock_settings_global.ffmpeg_path = mock_settings.ffmpeg_path
        mock_settings_global.ffprobe_path = mock_settings.ffprobe_path
        mock_settings_global.ffmpeg_threads = mock_settings.ffmpeg_threads
        mock_settings_global.enable_gpu_acceleration = mock_settings.enable_gpu_acceleration
        mock_settings_global.gpu_device = mock_settings.gpu_device
        
        with patch('subprocess.run') as mock_run:
            # Mock FFmpeg encoders output
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "h264_qsv Intel Quick Sync Video H.264 encoder"
            
            service = FFmpegService()
            result = service._detect_intel_gpu()
            
            assert result == True
            assert service.gpu_type == GPUType.INTEL
            assert service.gpu_info["name"] == "Intel Quick Sync"
    
    @patch('shutil.which', return_value='/usr/bin/ffmpeg')
    @patch('platform.system', return_value='Darwin')
    @patch('src.services.ffmpeg_service.settings')
    def test_apple_gpu_detection(self, mock_settings_global, mock_platform, mock_which, mock_settings):
        """Test Apple GPU detection"""
        mock_settings_global.ffmpeg_path = mock_settings.ffmpeg_path
        mock_settings_global.ffprobe_path = mock_settings.ffprobe_path
        mock_settings_global.ffmpeg_threads = mock_settings.ffmpeg_threads
        mock_settings_global.enable_gpu_acceleration = mock_settings.enable_gpu_acceleration
        mock_settings_global.gpu_device = mock_settings.gpu_device
        
        with patch('subprocess.run') as mock_run:
            # Mock FFmpeg encoders output
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "h264_videotoolbox VideoToolbox H.264 Encoder"
            
            service = FFmpegService()
            service._detect_apple_gpu()
            
            assert service.gpu_type == GPUType.APPLE
            assert service.gpu_info["type"] == "Apple VideoToolbox"


class TestGPUEncoding:
    """Test GPU encoding functionality"""
    
    @patch('shutil.which', return_value='/usr/bin/ffmpeg')
    @patch('src.services.ffmpeg_service.settings')
    def test_get_gpu_encoder_nvidia(self, mock_settings_global, mock_which, mock_settings):
        """Test getting NVIDIA GPU encoder"""
        mock_settings_global.ffmpeg_path = mock_settings.ffmpeg_path
        mock_settings_global.ffprobe_path = mock_settings.ffprobe_path
        mock_settings_global.ffmpeg_threads = mock_settings.ffmpeg_threads
        mock_settings_global.enable_gpu_acceleration = mock_settings.enable_gpu_acceleration
        mock_settings_global.gpu_device = mock_settings.gpu_device
        
        service = FFmpegService()
        service.gpu_type = GPUType.NVIDIA
        service.available_gpu_codecs = [
            {"encoder": "h264_nvenc", "name": "NVIDIA H.264"},
            {"encoder": "hevc_nvenc", "name": "NVIDIA H.265/HEVC"}
        ]
        
        # Test H.264 mapping
        encoder = service._get_gpu_encoder("libx264")
        assert encoder == "h264_nvenc"
        
        # Test H.265 mapping
        encoder = service._get_gpu_encoder("libx265")
        assert encoder == "hevc_nvenc"
        
        # Test unavailable codec
        encoder = service._get_gpu_encoder("vp9")
        assert encoder is None
    
    @patch('shutil.which', return_value='/usr/bin/ffmpeg')
    @patch('src.services.ffmpeg_service.settings')
    def test_gpu_acceleration_params(self, mock_settings_global, mock_which, mock_settings):
        """Test GPU acceleration parameters"""
        mock_settings_global.ffmpeg_path = mock_settings.ffmpeg_path
        mock_settings_global.ffprobe_path = mock_settings.ffprobe_path
        mock_settings_global.ffmpeg_threads = mock_settings.ffmpeg_threads
        mock_settings_global.enable_gpu_acceleration = mock_settings.enable_gpu_acceleration
        mock_settings_global.gpu_device = mock_settings.gpu_device
        
        service = FFmpegService()
        
        # Test NVIDIA params
        service.gpu_type = GPUType.NVIDIA
        service.gpu_device = "0"
        params = service._get_gpu_acceleration_params()
        assert "-hwaccel" in params
        assert "cuda" in params
        assert "-hwaccel_device" in params
        assert "0" in params
        
        # Test Intel params
        service.gpu_type = GPUType.INTEL
        params = service._get_gpu_acceleration_params()
        assert "-hwaccel" in params
        assert "qsv" in params
        
        # Test Apple params
        service.gpu_type = GPUType.APPLE
        params = service._get_gpu_acceleration_params()
        assert "-hwaccel" in params
        assert "videotoolbox" in params
    
    @patch('shutil.which', return_value='/usr/bin/ffmpeg')
    @patch('src.services.ffmpeg_service.settings')
    def test_gpu_scaling_filters(self, mock_settings_global, mock_which, mock_settings):
        """Test GPU-optimized scaling filters"""
        mock_settings_global.ffmpeg_path = mock_settings.ffmpeg_path
        mock_settings_global.ffprobe_path = mock_settings.ffprobe_path
        mock_settings_global.ffmpeg_threads = mock_settings.ffmpeg_threads
        mock_settings_global.enable_gpu_acceleration = mock_settings.enable_gpu_acceleration
        mock_settings_global.gpu_device = mock_settings.gpu_device
        
        service = FFmpegService()
        
        # Test NVIDIA CUDA scaling
        service.gpu_type = GPUType.NVIDIA
        filter_str = service._get_gpu_scaling_filter(1920, 1080)
        assert "scale_cuda" in filter_str
        assert "1920:1080" in filter_str
        
        # Test Intel QSV scaling
        service.gpu_type = GPUType.INTEL
        filter_str = service._get_gpu_scaling_filter(1920, 1080)
        assert "scale_qsv" in filter_str
        assert "1920:1080" in filter_str
        
        # Test software scaling fallback
        service.gpu_type = GPUType.NONE
        filter_str = service._get_gpu_scaling_filter(1920, 1080)
        assert "scale=" in filter_str
        assert "scale_cuda" not in filter_str


@pytest.mark.asyncio
class TestGPUProxyGeneration:
    """Test GPU-accelerated proxy generation"""
    
    @patch('shutil.which', return_value='/usr/bin/ffmpeg')
    @patch('asyncio.create_subprocess_exec')
    @patch('src.services.ffmpeg_service.settings')
    async def test_generate_video_proxy_with_gpu(self, mock_settings_global, mock_subprocess, mock_which, mock_settings):
        """Test video proxy generation with GPU acceleration"""
        mock_settings_global.ffmpeg_path = mock_settings.ffmpeg_path
        mock_settings_global.ffprobe_path = mock_settings.ffprobe_path
        mock_settings_global.ffmpeg_threads = mock_settings.ffmpeg_threads
        mock_settings_global.enable_gpu_acceleration = mock_settings.enable_gpu_acceleration
        mock_settings_global.gpu_device = mock_settings.gpu_device
        mock_settings_global.default_video_codec = mock_settings.default_video_codec
        mock_settings_global.default_audio_codec = mock_settings.default_audio_codec
        mock_settings_global.processing_timeout = mock_settings.processing_timeout
        mock_settings_global.video_presets = mock_settings.video_presets
        
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b'', b''))
        mock_subprocess.return_value = mock_process
        
        service = FFmpegService()
        service.gpu_type = GPUType.NVIDIA
        service.available_gpu_codecs = [
            {"encoder": "h264_nvenc", "name": "NVIDIA H.264"}
        ]
        
        # Mock get_media_info
        async def mock_get_media_info(path):
            return {
                "duration": 60.0,
                "size": 1000000,
                "streams": [{"codec_type": "video"}]
            }
        
        service.get_media_info = mock_get_media_info
        
        result = await service.generate_video_proxy(
            input_path="/test/input.mp4",
            output_path="/test/output.mp4",
            preset="medium",
            force_gpu=True
        )
        
        # Verify FFmpeg was called with GPU parameters
        args = mock_subprocess.call_args[0]
        assert "-hwaccel" in args
        assert "cuda" in args
        assert "-c:v" in args
        assert "h264_nvenc" in args
        
        # Verify result
        assert result["output_duration"] == 60.0
        assert result["output_size"] == 1000000


@pytest.mark.asyncio
class TestGPUBenchmark:
    """Test GPU benchmarking functionality"""
    
    @patch('shutil.which', return_value='/usr/bin/ffmpeg')
    @patch('os.remove')
    @patch('src.services.ffmpeg_service.settings')
    async def test_benchmark_gpu_performance(self, mock_settings_global, mock_remove, mock_which, mock_settings):
        """Test GPU performance benchmarking"""
        mock_settings_global.ffmpeg_path = mock_settings.ffmpeg_path
        mock_settings_global.ffprobe_path = mock_settings.ffprobe_path
        mock_settings_global.ffmpeg_threads = mock_settings.ffmpeg_threads
        mock_settings_global.enable_gpu_acceleration = mock_settings.enable_gpu_acceleration
        mock_settings_global.gpu_device = mock_settings.gpu_device
        
        service = FFmpegService()
        service.gpu_type = GPUType.NVIDIA
        service.gpu_info = {"name": "NVIDIA GeForce RTX 3080"}
        
        # Mock generate_video_proxy to simulate different performance
        async def mock_generate_proxy(input_path, output_path, **kwargs):
            # Simulate GPU being faster than CPU
            if kwargs.get('force_gpu', True):
                await asyncio.sleep(0.1)  # GPU: 100ms
            else:
                await asyncio.sleep(0.5)  # CPU: 500ms
            
            return {
                "processing_time": 0.1 if kwargs.get('force_gpu', True) else 0.5
            }
        
        service.generate_video_proxy = mock_generate_proxy
        
        # Mock subprocess for test file creation
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b'', b''))
            mock_subprocess.return_value = mock_process
            
            result = await service.benchmark_gpu_performance()
            
            assert result["gpu_type"] == "nvidia"
            assert "benchmark_results" in result
            
            # Check that GPU shows speedup over CPU
            for test_name, test_result in result["benchmark_results"].items():
                if "error" not in test_result:
                    assert test_result["speedup"] > 1.0  # GPU should be faster
                    assert test_result["gpu_fps"] > test_result["cpu_fps"]
# GPU Acceleration Guide for Proxy Generation Service

## Overview

The Proxy Generation Service supports GPU acceleration for video encoding, providing significant performance improvements over CPU-based encoding. This guide covers the supported GPU types, configuration, and best practices.

## Supported GPU Types

### 1. NVIDIA GPUs (NVENC)
- **Supported Cards**: GeForce GTX 1050+, RTX series, Quadro, Tesla
- **Codecs**: H.264, H.265/HEVC, AV1 (RTX 40 series), VP9
- **Features**: 
  - CUDA-accelerated scaling
  - Multiple concurrent encoding sessions
  - B-frame support
  - Constant quality mode

### 2. Intel GPUs (Quick Sync)
- **Supported CPUs**: Intel CPUs with integrated graphics (6th gen+)
- **Codecs**: H.264, H.265/HEVC, AV1 (Arc GPUs), VP9
- **Features**:
  - Hardware-accelerated scaling
  - Low power consumption
  - Good for basic proxy generation

### 3. AMD GPUs (AMF)
- **Supported Cards**: RX 400 series and newer
- **Codecs**: H.264, H.265/HEVC, AV1 (RX 7000 series)
- **Features**:
  - VCE (Video Coding Engine) acceleration
  - Windows and Linux support

### 4. Apple Silicon (VideoToolbox)
- **Supported Devices**: M1, M2, M3 Macs
- **Codecs**: H.264, H.265/HEVC, ProRes
- **Features**:
  - Highly efficient encoding
  - Native ProRes support
  - Low power consumption

## Configuration

### Environment Variables

```bash
# Enable GPU acceleration
PROXY_ENABLE_GPU_ACCELERATION=true

# Specify GPU device (for multi-GPU systems)
PROXY_GPU_DEVICE=0

# FFmpeg paths
PROXY_FFMPEG_PATH=ffmpeg
PROXY_FFPROBE_PATH=ffprobe
```

### Docker GPU Support

#### NVIDIA GPUs
```yaml
services:
  proxy-generation:
    image: mams/proxy-generation
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,video
      - PROXY_ENABLE_GPU_ACCELERATION=true
```

#### Intel GPUs (Linux)
```yaml
services:
  proxy-generation:
    image: mams/proxy-generation
    devices:
      - /dev/dri:/dev/dri
    environment:
      - PROXY_ENABLE_GPU_ACCELERATION=true
```

## API Endpoints

### Get GPU Information
```http
GET /api/v1/gpu/info
Authorization: Bearer {token}
```

Response:
```json
{
  "gpu_enabled": true,
  "gpu_type": "nvidia",
  "gpu_info": {
    "name": "NVIDIA GeForce RTX 3080",
    "memory": "10240 MiB",
    "driver_version": "470.57.02",
    "device": "0"
  },
  "available_encoders": [
    {"encoder": "h264_nvenc", "name": "NVIDIA H.264"},
    {"encoder": "hevc_nvenc", "name": "NVIDIA H.265/HEVC"},
    {"encoder": "av1_nvenc", "name": "NVIDIA AV1"}
  ],
  "performance_metrics": {
    "gpu_utilization": "45%",
    "memory_utilization": "23%",
    "temperature": "65°C",
    "power_draw": "180W"
  }
}
```

### Benchmark GPU Performance
```http
POST /api/v1/gpu/benchmark
Authorization: Bearer {token}
```

Response:
```json
{
  "gpu_type": "nvidia",
  "gpu_info": {
    "name": "NVIDIA GeForce RTX 3080"
  },
  "benchmark_results": {
    "1080p_h264": {
      "gpu_time": 2.5,
      "cpu_time": 15.3,
      "speedup": 6.12,
      "gpu_fps": 40,
      "cpu_fps": 6.5
    },
    "720p_h264": {
      "gpu_time": 1.2,
      "cpu_time": 8.7,
      "speedup": 7.25,
      "gpu_fps": 83.3,
      "cpu_fps": 11.5
    }
  }
}
```

## Quality Presets with GPU Support

The service automatically optimizes encoding parameters based on the detected GPU:

### NVIDIA NVENC Settings
```json
{
  "low": {
    "gpu_preset": "p4",      // Performance preset (p1-p7)
    "tune": "hq",           // High quality tuning
    "rc": "vbr",           // Rate control mode
    "cq": "28"             // Constant quality
  },
  "medium": {
    "gpu_preset": "p4",
    "tune": "hq",
    "rc": "vbr",
    "cq": "23"
  },
  "high": {
    "gpu_preset": "p5",
    "tune": "hq",
    "rc": "vbr",
    "cq": "19"
  }
}
```

### Intel QSV Settings
```json
{
  "medium": {
    "preset": "medium",
    "global_quality": "23",
    "look_ahead": "1"
  }
}
```

## Performance Optimization

### 1. GPU Selection
For systems with multiple GPUs:
```bash
# Use specific GPU
PROXY_GPU_DEVICE=0  # First GPU
PROXY_GPU_DEVICE=1  # Second GPU
```

### 2. Concurrent Encoding
NVIDIA consumer GPUs support 3 concurrent encoding sessions. Professional GPUs (Quadro, Tesla) have no limit.

### 3. Memory Management
- Monitor GPU memory usage
- Reduce resolution for limited VRAM
- Use appropriate batch sizes

### 4. Scaling Performance
GPU-accelerated scaling provides significant benefits:
- NVIDIA: `scale_cuda` filter
- Intel: `scale_qsv` filter
- Software fallback when GPU scaling unavailable

## Troubleshooting

### Common Issues

#### 1. GPU Not Detected
```bash
# Check NVIDIA GPU
nvidia-smi

# Check Intel GPU (Linux)
vainfo

# Check FFmpeg GPU support
ffmpeg -encoders | grep -E '(nvenc|qsv|amf|videotoolbox)'
```

#### 2. Driver Issues
- NVIDIA: Requires driver 418.81+ for NVENC
- Intel: Requires Intel Media Driver
- AMD: Requires AMD Pro drivers on Linux

#### 3. Docker GPU Access
```bash
# Test NVIDIA GPU in Docker
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
```

### Performance Monitoring

#### NVIDIA GPUs
```bash
# Real-time monitoring
nvidia-smi dmon -i 0

# Encoding statistics
nvidia-smi -q -d ENCODER_STATS
```

#### Intel GPUs
```bash
# Intel GPU Top (Linux)
intel_gpu_top
```

## Best Practices

1. **Quality vs Speed Trade-off**
   - Use appropriate presets for your use case
   - Higher GPU presets (p5-p7) provide better quality but slower encoding
   - Lower presets (p1-p3) maximize speed

2. **Resource Management**
   - Monitor GPU memory usage
   - Leave headroom for other GPU tasks
   - Consider dedicated encoding GPUs for high-volume workflows

3. **Fallback Strategy**
   - Always implement CPU fallback
   - Test GPU availability before processing
   - Handle GPU errors gracefully

4. **Codec Selection**
   - H.264: Best compatibility, good performance
   - H.265/HEVC: Better compression, higher GPU load
   - AV1: Best compression, limited GPU support

## Example: Force GPU Usage

```python
# Python client example
import httpx

async def create_gpu_proxy(asset_id: str, input_path: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://proxy-service/api/v1/jobs",
            json={
                "asset_id": asset_id,
                "input_path": input_path,
                "job_type": "video_proxy",
                "parameters": {
                    "quality": "medium",
                    "force_gpu": True  # Force GPU usage
                },
                "priority": "high"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

## Benchmarking Results

Typical performance improvements with GPU acceleration:

| Resolution | Codec | CPU (fps) | GPU (fps) | Speedup |
|------------|-------|-----------|-----------|---------|
| 1080p      | H.264 | 25        | 150       | 6x      |
| 1080p      | H.265 | 12        | 80        | 6.7x    |
| 4K         | H.264 | 6         | 45        | 7.5x    |
| 4K         | H.265 | 3         | 25        | 8.3x    |

*Results vary based on GPU model and system configuration*
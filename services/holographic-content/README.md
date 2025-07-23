# MAMS Holographic Content Service

Next-generation holographic content management service for the Digital Media Asset Management System (MAMS). This service provides comprehensive support for volumetric capture, neural rendering, light field displays, holographic projection, and spatial interaction.

## Features

### Volumetric Capture
- **Depth Cameras**: Azure Kinect, Intel RealSense support
- **Professional Systems**: Depthkit, Evercoast, Scatter integration
- **Multi-camera Arrays**: Synchronized capture from multiple viewpoints
- **Real-time Preview**: Live volumetric preview during capture
- **Edit-while-capture**: Start processing while still capturing

### Neural Rendering
- **NVIDIA Instant NGP**: Real-time neural radiance fields
- **NeRF Variants**: Classic NeRF, Mip-NeRF 360, Nerfacto
- **3D Gaussian Splatting**: Ultra-fast rendering with explicit representation
- **Neural Volumes**: Volumetric representation with texture synthesis
- **Neural Actor**: Human-specific neural rendering with animation

### Light Field Displays
- **Looking Glass**: Portrait and 8K display support
- **Leia Displays**: Lightfield tablets and monitors
- **Holoxica**: Medical-grade volumetric displays
- **Quilt Generation**: Automatic multi-view image generation
- **Real-time Conversion**: On-the-fly light field conversion

### Holographic Projection
- **AR Headsets**: Microsoft HoloLens 2, Magic Leap 2
- **Pyramid Displays**: Realfiction Dreamoc holographic displays
- **Pepper's Ghost**: Large-scale holographic stages
- **Spatial Anchors**: Persistent hologram placement
- **Multi-user Support**: Shared holographic experiences

### Spatial Interaction
- **Hand Tracking**: Gesture recognition with sub-millimeter accuracy
- **Eye Tracking**: Gaze-based selection and attention mapping
- **Voice Control**: Natural language commands
- **6DOF Controllers**: Spatial controller support
- **Haptic Feedback**: Mid-air haptics (when available)

### Real-time Streaming
- **WebRTC**: Ultra-low latency P2P streaming
- **Pixel Streaming**: Cloud-rendered holographic content
- **Adaptive Bitrate**: Quality adjustment based on bandwidth
- **Multi-protocol**: HLS/DASH for CDN delivery
- **Progressive Loading**: Quality levels from base to full

## API Endpoints

### Capture
- `POST /api/v1/holographic/capture/start` - Start volumetric capture
- `POST /api/v1/holographic/capture/{id}/stop` - Stop capture
- `GET /api/v1/holographic/capture/{id}/status` - Get capture status

### Processing
- `POST /api/v1/holographic/processing/neural` - Neural rendering
- `POST /api/v1/holographic/processing/light-field` - Light field processing
- `GET /api/v1/holographic/processing/{id}/status` - Processing status
- `POST /api/v1/holographic/processing/{id}/synthesize-view` - Novel view synthesis

### Display
- `POST /api/v1/holographic/display/light-field` - Display on light field device
- `POST /api/v1/holographic/display/projection` - Start holographic projection
- `PUT /api/v1/holographic/display/{id}/update` - Update display parameters
- `POST /api/v1/holographic/display/{id}/stop` - Stop display

### Interaction
- `POST /api/v1/holographic/interaction/session` - Create interaction session
- `POST /api/v1/holographic/interaction/{id}/gesture` - Process hand gesture
- `POST /api/v1/holographic/interaction/{id}/voice` - Process voice command
- `POST /api/v1/holographic/interaction/{id}/gaze` - Process eye gaze
- `GET /api/v1/holographic/interaction/{id}/analytics` - Get interaction analytics

### Streaming
- `POST /api/v1/holographic/streaming/start` - Start streaming
- `POST /api/v1/holographic/streaming/{id}/viewer` - Add viewer
- `PUT /api/v1/holographic/streaming/{id}/quality` - Update quality
- `GET /api/v1/holographic/streaming/{id}/metrics` - Get stream metrics
- `POST /api/v1/holographic/streaming/{id}/stop` - Stop streaming

## Supported Formats

### Input Formats
- **Point Clouds**: PLY, PCD, LAS/LAZ, E57
- **Mesh Files**: OBJ, FBX, GLTF/GLB, USD/USDZ
- **Volumetric Video**: Depthkit, Evercoast, 4DViews
- **Image Sequences**: For photogrammetry processing
- **Depth + Color**: Raw sensor data from depth cameras

### Output Formats
- **Neural Models**: NeRF checkpoints, Gaussian splats
- **Light Field**: Quilt images, Looking Glass native
- **AR/VR**: GLTF/GLB for headsets, USDZ for ARKit
- **Streaming**: WebRTC, HLS/DASH manifests
- **Point Clouds**: Compressed and optimized

## Configuration

### Environment Variables

```bash
# Service Configuration
SERVICE_NAME=holographic-content
SERVICE_PORT=8023
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0

# Capture Devices
AZURE_KINECT_ENABLED=true
INTEL_REALSENSE_ENABLED=true
DEPTHKIT_ENABLED=false
EVERCOAST_URL=https://api.evercoast.com
SCATTER_SDK_KEY=your_scatter_key

# Display Devices
LOOKING_GLASS_ENABLED=true
LOOKING_GLASS_SDK_PATH=/opt/lookingglass
LEIA_SDK_ENABLED=false
HOLOXICA_ENABLED=false

# AR/MR Devices
MICROSOFT_HOLOLENS_ENABLED=true
MAGIC_LEAP_ENABLED=true
REALFICTION_DREAMOC_ENABLED=false

# Neural Processing
NVIDIA_INSTANT_NGP_ENABLED=true
NEURAL_RADIANCE_FIELDS=true
GAUSSIAN_SPLATTING_ENABLED=true
GPU_ACCELERATION=true
CUDA_DEVICE_ID=0

# Streaming
WEBRTC_ENABLED=true
PIXEL_STREAMING_URL=https://pixel.example.com
LOW_LATENCY_MODE=true
MAX_STREAMING_BITRATE=50000000

# Feature Flags
ENABLE_VOLUMETRIC_CAPTURE=true
ENABLE_LIGHT_FIELD_DISPLAY=true
ENABLE_HOLOGRAPHIC_PROJECTION=true
ENABLE_NEURAL_RENDERING=true
ENABLE_REAL_TIME_STREAMING=true
ENABLE_HAPTIC_FEEDBACK=false
```

## Installation

### Docker Compose

```bash
# Start the service with dependencies
docker-compose up -d

# View logs
docker-compose logs -f holographic-content

# Stop the service
docker-compose down
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn src.main:app --reload --port 8023
```

### GPU Support

For neural rendering and processing, GPU support is highly recommended:

```yaml
# docker-compose.yml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

## Usage Examples

### Capture Volumetric Content

```python
import httpx

async def capture_volumetric():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8023/api/v1/holographic/capture/start",
            json={
                "device": "azure_kinect",
                "duration": 30,
                "fps": 30,
                "quality": "high"
            }
        )
        capture_data = response.json()
        capture_id = capture_data["capture_id"]
        
        # Check status
        status = await client.get(
            f"http://localhost:8023/api/v1/holographic/capture/{capture_id}/status"
        )
        return status.json()
```

### Process with Neural Rendering

```python
async def process_with_nerf(hologram_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8023/api/v1/holographic/processing/neural",
            json={
                "hologram_id": hologram_id,
                "model": "gaussian_splatting",
                "quality": "ultra",
                "enable_relighting": True
            }
        )
        return response.json()
```

### Display on HoloLens

```python
async def display_on_hololens(hologram_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8023/api/v1/holographic/display/projection",
            json={
                "hologram_id": hologram_id,
                "device": "hololens2",
                "position": [0, 1.5, 2],
                "scale": [1, 1, 1],
                "persistence": True
            }
        )
        return response.json()
```

### Enable Spatial Interaction

```python
async def enable_interaction(hologram_id: str):
    async with httpx.AsyncClient() as client:
        # Create interaction session
        response = await client.post(
            "http://localhost:8023/api/v1/holographic/interaction/session",
            json={
                "hologram_id": hologram_id,
                "methods": ["hand_tracking", "voice_control", "eye_tracking"],
                "haptic_enabled": True
            }
        )
        session_id = response.json()["session_id"]
        
        # Process gesture
        gesture_response = await client.post(
            f"http://localhost:8023/api/v1/holographic/interaction/{session_id}/gesture",
            json={
                "gesture_type": "pinch",
                "hand": "right",
                "parameters": {"distance": 0.05}
            }
        )
        return gesture_response.json()
```

### Stream Holographic Content

```python
async def stream_hologram(hologram_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8023/api/v1/holographic/streaming/start",
            json={
                "hologram_id": hologram_id,
                "protocol": "webrtc",
                "quality": "high",
                "adaptive_bitrate": True
            }
        )
        stream_data = response.json()
        
        # Get WebRTC endpoints
        websocket_url = stream_data["endpoints"]["websocket"]
        ice_servers = stream_data["endpoints"]["ice_servers"]
        
        return {
            "stream_id": stream_data["stream_id"],
            "websocket": websocket_url,
            "ice_servers": ice_servers
        }
```

## Performance Optimization

### Neural Rendering
- Use Instant NGP for real-time applications
- Use Gaussian Splatting for best quality/performance ratio
- Enable GPU acceleration for all neural models
- Batch process multiple views for efficiency

### Streaming
- Use WebRTC for lowest latency (<50ms)
- Enable adaptive bitrate for varying network conditions
- Use progressive loading for large holograms
- Implement view-dependent streaming

### Capture
- Use hardware sync for multi-camera setups
- Enable compression for storage efficiency
- Process during capture for reduced latency
- Use appropriate resolution for target display

## Troubleshooting

### Common Issues

1. **GPU Not Detected**
   - Ensure NVIDIA drivers are installed
   - Check CUDA_VISIBLE_DEVICES environment variable
   - Verify Docker GPU support is configured

2. **Capture Device Not Found**
   - Install device-specific SDKs
   - Check USB connections and permissions
   - Verify device firmware is up to date

3. **Streaming Latency**
   - Use WebRTC instead of HLS/DASH
   - Enable low latency mode
   - Check network bandwidth
   - Reduce quality settings if needed

4. **Processing Failures**
   - Check available GPU memory
   - Reduce batch size or resolution
   - Ensure sufficient disk space
   - Check logs for specific errors

## Development

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test
pytest tests/test_holographic_content.py::TestCaptureEndpoints
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff src/ tests/

# Type checking
mypy src/
```

## Architecture

The service follows a modular architecture:

- **HologramManager**: Central coordinator for all services
- **VolumetricCaptureService**: Handles all capture devices
- **NeuralRenderingService**: Neural processing and rendering
- **LightFieldService**: Light field display management
- **HolographicProjectionService**: AR/MR projection
- **SpatialInteractionService**: User interaction handling
- **HologramStreamingService**: Real-time streaming

## Contributing

1. Follow the MAMS coding standards
2. Add tests for new features
3. Update documentation
4. Submit PR with clear description

## License

Part of the MAMS project. See main project license.
# MAMS Metaverse Support Service

Comprehensive metaverse integration service for the Digital Media Asset Management System (MAMS). This service provides seamless integration with various virtual worlds, VR/AR platforms, avatar systems, and blockchain technologies.

## Features

### Virtual World Integration
- **Unity & Unreal Engine**: Direct integration with custom world servers
- **VRChat**: Asset deployment with performance optimization
- **Horizon Worlds**: Meta's social VR platform support
- **Roblox**: Game asset integration with format conversion
- **Minecraft & Fortnite Creative**: Specialized content deployment

### VR Platform Support
- **Oculus/Meta Quest**: Native Quest app integration
- **SteamVR**: Universal VR headset compatibility
- **HTC Vive, Valve Index**: High-end VR support
- **Comfort Features**: Teleportation, vignetting, snap-turn

### AR Platform Integration
- **Apple ARKit**: iOS AR experiences with USDZ format
- **Google ARCore**: Android AR with GLB/GLTF support
- **Microsoft HoloLens**: Mixed reality applications
- **Magic Leap**: Enterprise AR platform support

### Avatar Systems
- **Ready Player Me**: Realistic avatar creation
- **VRoid Studio**: Anime-style avatar generation
- **Adobe Mixamo**: Auto-rigging and animations
- **Cross-platform optimization**: Avatar compatibility across platforms

### Spatial Computing
- **Spatial Anchors**: Persistent AR anchor placement
- **Azure Spatial Anchors**: Cloud-synchronized anchors
- **3D World Mapping**: Environmental understanding
- **Hand & Eye Tracking**: Advanced interaction support

### Blockchain Integration
- **NFT Minting**: Convert media assets to NFTs
- **Virtual Economies**: Integration with platform currencies
- **Smart Contracts**: Automated ownership and licensing
- **Multi-chain Support**: Ethereum, Polygon, and more

## API Endpoints

### Virtual Worlds
- `POST /api/v1/metaverse/worlds/deploy` - Deploy asset to virtual world
- `POST /api/v1/metaverse/worlds/deploy-multi` - Multi-platform deployment
- `GET /api/v1/metaverse/worlds/platforms` - List available platforms

### VR Integration
- `POST /api/v1/metaverse/vr/deploy` - Deploy VR experience
- `GET /api/v1/metaverse/vr/compatibility` - Check VR compatibility

### AR Integration  
- `POST /api/v1/metaverse/ar/deploy` - Deploy AR experience
- `POST /api/v1/metaverse/ar/experience` - Create interactive AR experience

### Avatar System
- `POST /api/v1/metaverse/avatars/create` - Create new avatar
- `POST /api/v1/metaverse/avatars/animate` - Add animations
- `POST /api/v1/metaverse/avatars/optimize` - Platform optimization

### Spatial Computing
- `POST /api/v1/metaverse/spatial/anchors` - Create spatial anchors
- `GET /api/v1/metaverse/spatial/anchors/{id}` - Get anchor details

### Blockchain
- `POST /api/v1/metaverse/blockchain/nft/mint` - Mint asset as NFT
- `POST /api/v1/metaverse/blockchain/economy/integrate` - Virtual economy integration

## Configuration

### Environment Variables

#### Service Configuration
```bash
SERVICE_NAME=metaverse-support
SERVICE_PORT=8022
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
```

#### VR/AR Platforms
```bash
OCULUS_APP_ID=your_oculus_app_id
STEAMVR_SDK_PATH=/path/to/steamvr
APPLE_ARKIT_TEAM_ID=your_apple_team_id
ANDROID_ARCORE_API_KEY=your_arcore_key
HOLOLENS_DEVICE_PORTAL=https://hololens:10080
MAGIC_LEAP_SDK_KEY=your_magic_leap_key
```

#### Virtual World Platforms
```bash
UNITY_SERVER_URL=http://unity-server:7777
UNREAL_SERVER_URL=http://unreal-server:7778
VRCHAT_SDK_KEY=your_vrchat_key
HORIZON_WORLDS_TOKEN=your_horizon_token
ROBLOX_API_KEY=your_roblox_key
```

#### Avatar Platforms
```bash
READY_PLAYER_ME_APP_ID=your_rpm_app_id
VROID_SDK_KEY=your_vroid_key
MIXAMO_API_KEY=your_mixamo_key
```

#### Blockchain Configuration
```bash
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_PROJECT_ID
POLYGON_RPC_URL=https://polygon-mainnet.infura.io/v3/YOUR_PROJECT_ID
WEB3_SERVICE_URL=http://web3-integration:8021
```

#### Feature Flags
```bash
ENABLE_VR_SUPPORT=true
ENABLE_AR_SUPPORT=true
ENABLE_BLOCKCHAIN_FEATURES=true
ENABLE_SOCIAL_FEATURES=true
ENABLE_AI_AVATAR_GENERATION=false
```

## Deployment

### Docker Compose
```bash
# Start the service with dependencies
docker-compose up -d

# View logs
docker-compose logs -f metaverse-support

# Scale for high availability
docker-compose up -d --scale metaverse-support=3
```

### Kubernetes
```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -l app=metaverse-support
```

## Performance Optimization

### Asset Optimization
- **Polygon Reduction**: Automatic LOD generation
- **Texture Compression**: Platform-specific formats
- **Shader Optimization**: Performance-first rendering
- **Batch Processing**: Concurrent asset conversions

### Platform Limits
- **VRChat**: 32k polygons, 150MB textures, "Good" performance rank
- **Horizon Worlds**: 10k polygons, 25MB limit, mobile optimization
- **AR Platforms**: Lightweight assets, <50MB, environmental lighting

### Monitoring
- **Health Checks**: Service and platform status monitoring
- **Performance Metrics**: Conversion times, success rates
- **Resource Usage**: CPU, memory, disk utilization
- **Platform Analytics**: User engagement, session duration

## Development

### Local Setup
```bash
# Clone repository
git clone <repository-url>
cd services/metaverse-support

# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn src.main:app --reload --port 8022
```

### Testing
```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test category
pytest tests/test_vr_integration.py -v
```

### Adding New Platforms

1. **Create Platform Class**: Extend base platform class
2. **Implement Integration**: Add platform-specific deployment logic
3. **Update Configuration**: Add environment variables
4. **Add API Routes**: Create platform-specific endpoints
5. **Write Tests**: Ensure platform compatibility
6. **Update Documentation**: Document new capabilities

## Supported File Formats

### 3D Models
- **Universal**: GLTF 2.0, GLB, FBX, OBJ
- **VR Optimized**: Compressed GLTF, Draco geometry
- **AR Specific**: USDZ (iOS), SFB (Android)
- **Platform Native**: Unity Asset Bundles, Unreal Packages

### Textures
- **Standard**: PNG, JPEG, TGA
- **HDR**: EXR, HDR for environmental lighting
- **Compressed**: KTX2, ASTC for mobile/VR
- **Platform**: Unity Texture2D, Unreal UTexture

### Animations
- **Standard**: FBX animations, BVH motion capture
- **Web**: GLTF animations with morph targets
- **Advanced**: USD for complex animation workflows

## Integration Examples

### Deploy to VRChat
```python
import httpx

async def deploy_to_vrchat(asset_id: str):
    response = await httpx.post(
        "http://localhost:8022/api/v1/metaverse/worlds/deploy",
        json={
            "asset_id": asset_id,
            "platform": "vrchat",
            "deployment_config": {
                "world_id": "wrld_12345",
                "position": {"x": 0, "y": 1, "z": 0},
                "optimization_level": "medium"
            }
        }
    )
    return response.json()
```

### Create AR Experience
```python
async def create_ar_experience(asset_id: str):
    response = await httpx.post(
        "http://localhost:8022/api/v1/metaverse/ar/deploy",
        json={
            "asset_id": asset_id,
            "ar_platform": "arkit",
            "anchor_type": "plane",
            "scale_factor": 1.0,
            "interaction_enabled": True
        }
    )
    return response.json()
```

### Generate Avatar
```python
async def create_avatar():
    response = await httpx.post(
        "http://localhost:8022/api/v1/metaverse/avatars/create",
        json={
            "style": "realistic",
            "platform": "ready_player_me",
            "customizations": {
                "hair_color": "#8B4513",
                "eye_color": "#654321",
                "clothing": "casual"
            }
        }
    )
    return response.json()
```

## Troubleshooting

### Common Issues
1. **Platform Connection Failed**: Check API keys and network connectivity
2. **Asset Too Large**: Reduce polygon count or texture resolution
3. **Format Not Supported**: Use cross-platform conversion
4. **Performance Issues**: Enable asset optimization features

### Debug Mode
Set `DEBUG=true` to enable detailed logging and error information.

### Health Monitoring
```bash
# Check service health
curl http://localhost:8022/health

# View metrics
curl http://localhost:8022/metrics
```

## Security

- **API Authentication**: JWT token validation
- **Input Validation**: Comprehensive request sanitization
- **Rate Limiting**: Platform-specific API limits
- **Asset Scanning**: Malware and content validation
- **Network Security**: HTTPS/TLS for all external communications

## License

This project is part of the MAMS ecosystem and follows the project's licensing terms.